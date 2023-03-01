# -*- coding: utf-8 -*-
import abc
import queue
import typing
import threading
import contextlib
import collections
from ..misc.settings import UiLogMessage
from ..misc.debug import get_debug_timestamp
from ..core.threading import ThreadSafeBool, ThreadSafeInteger
from .transmit import Transmit, TransmitException, TransmitWarning
from ..core.datatype import CustomEvent, enum_property, DynamicObject
__all__ = ['CommunicationEvent', 'CommunicationEventHandle',
           'CommunicationObject', 'CommunicationController', 'CommunicationSection']


CommunicationSection = collections.namedtuple('CommunicationSection', 'request response')


class CommunicationEvent(CustomEvent):
    Type = collections.namedtuple(
        'Type', 'Timeout Restore Warning Exception Logging Connected Disconnected SectionStart SectionEnd Customize'
    )(*('timeout', 'restore', 'warning', 'exception', 'logging', 'connect', 'disconnected', 'ss', 'se', 'customize'))

    type = enum_property('type', Type)

    def __init__(self, type_: Type, data: typing.Any = '', source: typing.Any = None):
        kwargs = dict(type=type_, data=data, source=source)
        super(CommunicationEvent, self).__init__(**kwargs)

    @classmethod
    def info(cls, msg: str):
        return cls(cls.Type.Logging, data=UiLogMessage.genDefaultInfoMessage(msg))

    @classmethod
    def debug(cls, msg: str):
        return cls(cls.Type.Logging, data=UiLogMessage.genDefaultDebugMessage(msg))

    @classmethod
    def error(cls, msg: str):
        return cls(cls.Type.Logging, data=UiLogMessage.genDefaultErrorMessage(msg))

    @classmethod
    def section_end(cls, sid: int, section: CommunicationSection):
        return cls(cls.Type.SectionEnd, data=DynamicObject(sid=sid, section=section))

    @classmethod
    def section_start(cls, sid: int):
        return cls(cls.Type.SectionStart, data=sid)

    @classmethod
    def connected(cls, address: Transmit.Address, timeout: float):
        return cls(cls.Type.Connected, source=address, data=DynamicObject(timeout=timeout))

    @classmethod
    def disconnected(cls, desc: str):
        return cls(cls.Type.Disconnected, data=desc)


class CommunicationEventHandle:
    def __call__(self, event: CommunicationEvent):
        handle = {
            CommunicationEvent.Type.Logging: self.handleCommEventLogging,
            CommunicationEvent.Type.Timeout: self.handleCommEventTimeout,
            CommunicationEvent.Type.Restore: self.handleCommEventRestore,
            CommunicationEvent.Type.Exception: self.handleCommEventException,
            CommunicationEvent.Type.Connected: self.handleCommEventConnected,
            CommunicationEvent.Type.Disconnected: self.handleCommEventDisconnected,
        }.get(event.type)

        if callable(handle):
            handle(event.data)
        else:
            print(f'Unregistered type: {event.type}')

    @abc.abstractmethod
    def handleCommEventLogging(self, msg: UiLogMessage):
        pass

    @abc.abstractmethod
    def handleCommEventTimeout(self, exp: Exception):
        pass

    @abc.abstractmethod
    def handleCommEventRestore(self, arg: typing.Any):
        pass

    @abc.abstractmethod
    def handleCommEventException(self, exp: Exception):
        pass

    @abc.abstractmethod
    def handleCommEventConnected(self, arg: typing.Any):
        pass

    @abc.abstractmethod
    def handleCommEventDisconnected(self, exp: Exception):
        pass


class CommunicationObject:
    @abc.abstractmethod
    def print_log(self) -> bool:
        pass

    @abc.abstractmethod
    def to_bytes(self) -> bytes:
        """Get binary data from obj"""
        pass

    @classmethod
    @abc.abstractmethod
    def from_bytes(cls, obj, data: bytes):
        """Get object from bytes"""
        pass


class CommunicationController:
    def __init__(self,
                 event_cls,
                 response_cls,
                 exception_cls,
                 transmit: Transmit,
                 response_max_length: int,
                 event_callback: typing.Callable[[CommunicationEvent], None], print_ts: bool = False):
        if not isinstance(transmit, Transmit):
            raise TypeError(f"'transmit' must be a instance of {Transmit.__name__}")

        if not issubclass(event_cls, CommunicationEvent):
            raise TypeError(f"'event_cls' must be a subclass of {CommunicationEvent.__name__}")

        if not issubclass(response_cls, CommunicationObject):
            raise TypeError(f"'response_cls' must be a subclass of {CommunicationObject.__name__}")

        if not issubclass(exception_cls, Exception):
            raise TypeError(f"'exception_cls' must be a subclass of {Exception.__name__}")

        if not callable(event_callback):
            raise TypeError("'event_callback must be callable'")

        self._transmit = transmit
        self._print_ts = print_ts
        self._enable_sim = False
        self._queue = queue.Queue()
        self._exit = ThreadSafeBool(False)
        self._section_seq = ThreadSafeInteger(0)
        self._latest_section = CommunicationSection(None, None)

        self._event_cls = event_cls
        self._response_cls = response_cls
        self._exception_cls = exception_cls
        self._event_callback = event_callback
        self._response_max_length = response_max_length
        threading.Thread(target=self.thread_comm_with_device, daemon=True).start()

    def disconnect(self):
        self._exit.set()
        self._transmit.disconnect()
        self._event_callback(self._event_cls.disconnected('user cancel'))

    def reset_section(self, sid: int = 0):
        self._section_seq.assign(sid)

    def connect(self, address: Transmit.Address, timeout: float, enable_sim: bool = False):
        try:
            self._enable_sim = enable_sim
            self._transmit.connect(address, timeout)
        except Exception as e:
            self._event_callback(self._event_cls(CommunicationEvent.Type.Exception, data=f'{e}'))
            raise self._exception_cls(e)
        else:
            self._section_seq.reset()
            self.info_msg(f'Serial port connected: {address}, timeout:{timeout}')
            self._event_callback(self._event_cls.connected(address, timeout))

    def _format_log(self, msg: str) -> str:
        return f'{get_debug_timestamp()} {msg}' if self._print_ts else msg

    def _send_event(self, event: CommunicationEvent):
        if callable(self._event_callback):
            self._event_callback(event)

    def info_msg(self, msg: str):
        self._event_callback(self._event_cls.info(self._format_log(msg)))

    def error_msg(self, msg: str):
        self._event_callback(self._event_cls.error(self._format_log(msg)))

    def debug_msg(self, msg: str):
        self._event_callback(self._event_cls.debug(self._format_log(msg)))

    def send_request(self, request: CommunicationObject) -> bool:
        if not self._transmit.connected:
            return False

        if not isinstance(request, CommunicationObject):
            return False

        self._queue.put(request)
        return True

    @abc.abstractmethod
    def _simulate_handle(self, request: CommunicationObject) -> bool:
        """Simulator device communication, return true means already handle"""
        pass

    @abc.abstractmethod
    def _response_handle(self, request: CommunicationObject, response: CommunicationObject):
        """Handle device returned response"""
        pass

    @abc.abstractmethod
    def _section_check(self, request: CommunicationObject, response: CommunicationObject) -> bool:
        """Check if section is valid"""
        pass

    @contextlib.contextmanager
    def section(self, request: CommunicationObject):
        self._event_callback(self._event_cls.section_start(self._section_seq.data))
        self.debug_msg(f'[Section: {self._section_seq.data: 07d}]')
        try:
            yield
        except (TransmitWarning, TransmitException) as e:
            # Exception CommunicationSection.response filled with exception
            self._latest_section = CommunicationSection(request, e)
            raise e
        finally:
            self._event_callback(self._event_cls.section_end(self._section_seq.data, self._latest_section))
            self.debug_msg('>>>\r\n')
            self._section_seq.increase()

    def thread_comm_with_device(self):
        while not self._exit:
            request = self._queue.get()
            if not isinstance(request, CommunicationObject):
                continue

            if self._enable_sim and self._simulate_handle(request):
                continue

            try:
                with self.section(request):
                    # Send request
                    self._transmit.tx(request.to_bytes())

                    if request.print_log():
                        self.debug_msg(f'TX {"=" * 16}>: {request}')

                    # Receive response
                    data = self._transmit.rx(self._response_max_length)

                    # Decode and check response
                    try:
                        response = self._response_cls.from_bytes(request, data)
                    except ValueError as e:
                        raw = ' '.join([f'{x:02X}' for x in data])
                        self.error_msg(f'Decode {request} response error: {e}, (Raw: {raw})')
                        self._transmit.flush()
                        continue
                    else:
                        if request.print_log():
                            self.debug_msg(f'RX <{"=" * 16}: {response}')

                    if not self._section_check(request, response):
                        self.error_msg(f'Section check failed: {request!r} {response!r}')
                        continue

                    self._response_handle(request, response)
                    self._latest_section = CommunicationSection(request, response)
            except TransmitWarning as e:
                type_ = CommunicationEvent.Type.Timeout if e.is_timeout() else CommunicationEvent.Type.Warning
                self._event_callback(self._event_cls(type_=type_, data=f'{e}'))
                self.error_msg(f'Communication warning: {e}')
                self._transmit.flush()
            except (AttributeError, TransmitException) as e:
                self._event_callback(self._event_cls(type_=CommunicationEvent.Type.Exception, data=f'{e}'))
                self.error_msg(f'Communication exception: {e}')
                break

        print(f'[{self.__class__.__name__}]: thread_comm_with_device exit({self._exit.is_set()})!!!')