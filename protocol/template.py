# -*- coding: utf-8 -*-
import abc
import time
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
    def print_log(self) -> bool:
        return True

    def is_periodic(self) -> bool:
        return False

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
                 event_callback: typing.Callable[[CommunicationEvent], None], print_ts: bool = False, retry: int = 1):
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
        self._retry_times = retry
        self._enable_sim = False
        self._queue = queue.Queue()
        self._exit = ThreadSafeBool(False)
        self._timeout = ThreadSafeBool(False)
        self._timeout_cnt = ThreadSafeInteger(0)
        self._section_seq = ThreadSafeInteger(0)
        self._latest_section = CommunicationSection(None, None)

        self._event_cls = event_cls
        self._response_cls = response_cls
        self._exception_cls = exception_cls
        self._event_callback = event_callback
        self._response_max_length = response_max_length

    def __del__(self):
        self.disconnect()

    @property
    def name(self) -> str:
        return type(self).__name__

    @property
    def connected(self) -> bool:
        return self._transmit.connected

    @property
    def address(self) -> Transmit.Address:
        return self._transmit.address

    def is_timeout(self) -> bool:
        return self._timeout.is_set()

    def is_comm_idle(self, remain: int = 1) -> bool:
        return self._queue.qsize() <= remain

    def disconnect(self):
        self._exit.set()
        self._transmit.disconnect()
        self.send_event(self._event_cls.disconnected('user cancel'))

    def reset_section(self, sid: int = 0):
        self._section_seq.assign(sid)

    def connect(self, address: Transmit.Address, timeout: float, enable_sim: bool = False) -> bool:
        try:
            self._enable_sim = enable_sim
            self._transmit.connect(address, timeout)
        except Exception as e:
            self.send_event(self._event_cls(CommunicationEvent.Type.Exception, data=f'{e}'))
            raise self._exception_cls(e)
        else:
            self._exit.clear()
            self._timeout.clear()
            self._timeout_cnt.reset()
            self._section_seq.reset()
            threading.Thread(target=self.thread_comm_with_device, daemon=True).start()
            self.info_msg(f'Serial port connected: {address}, timeout:{timeout}')
            self.send_event(self._event_cls.connected(address, timeout))
            return True

    def info_msg(self, msg: str):
        self.send_event(self._event_cls.info(self._format_log(msg)))

    def error_msg(self, msg: str):
        self.send_event(self._event_cls.error(self._format_log(msg)))

    def debug_msg(self, msg: str):
        self.send_event(self._event_cls.debug(self._format_log(msg)))

    def send_event(self, event: CommunicationEvent):
        if callable(self._event_callback):
            self._event_callback(event)

    def send_request(self, request: CommunicationObject, priority: typing.Optional[int] = None) -> bool:
        if not self._transmit.connected:
            return False

        if not isinstance(request, CommunicationObject):
            return False

        try:
            priority = time.perf_counter() if priority is None else priority
            self._queue.put((priority, request))
        except (queue.Full, TypeError) as e:
            self.error_msg(f'Send request exception: {e}')
            return False
        else:
            return True

    def _format_log(self, msg: str) -> str:
        return f'{get_debug_timestamp()} {msg}' if self._print_ts else msg

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
        self.send_event(self._event_cls.section_start(self._section_seq.data))
        if request.print_log():
            self.debug_msg(f'[Section: {self._section_seq.data: 07d}]')
        try:
            yield
        except (TransmitWarning, TransmitException) as e:
            # Exception CommunicationSection.response filled with exception
            self._latest_section = CommunicationSection(request, e)
            raise e
        finally:
            self.send_event(self._event_cls.section_end(self._section_seq.data, self._latest_section))
            if request.print_log():
                self.debug_msg('>>>\r\n')
            self._section_seq.increase()

    def thread_comm_with_device(self):
        while not self._exit:
            try:
                _, request = self._queue.get()
            except (queue.Empty, TypeError):
                continue

            if not isinstance(request, CommunicationObject):
                continue

            if self._enable_sim and self._simulate_handle(request):
                continue

            retry = 0
            max_retry_times = 1 if request.is_periodic() else self._retry_times
            with self.section(request):
                while retry < max_retry_times:
                    try:
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

                        # Communication restored
                        self._timeout.clear()
                        self._timeout_cnt.reset()
                        if self._timeout.is_falling_edge():
                            self.send_event(self._event_cls(type_=CommunicationEvent.Type.Restore))

                        self._response_handle(request, response)
                        self._latest_section = CommunicationSection(request, response)
                        break
                    except TransmitWarning as e:
                        type_ = CommunicationEvent.Type.Warning

                        if e.is_timeout():
                            retry += 1
                            if retry < max_retry_times:
                                time.sleep(retry * 0.3)
                                continue
                            else:
                                self._timeout.set()
                                self._timeout_cnt.increase()
                                type_ = CommunicationEvent.Type.Timeout

                        self.send_event(self._event_cls(type_=type_, data=f'{e}'))
                        self.error_msg(f'Communication warning: {e}')
                        self._transmit.flush()

                        if self._timeout_cnt.great(3, equal=True):
                            msg = 'The number of timeouts exceeds the upper limit'
                            self.disconnect()
                            self.error_msg(msg)
                            self.send_event(self._event_cls(type_=CommunicationEvent.Type.Exception, data=msg))
                    except (AttributeError, TransmitException) as e:
                        self.send_event(self._event_cls(type_=CommunicationEvent.Type.Exception, data=f'{e}'))
                        self.error_msg(f'Communication exception: {e}')
                        self.disconnect()
                        break

        print(f'[{self.__class__.__name__}]: thread_comm_with_device exit({self._exit.is_set()})!!!')
