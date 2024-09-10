# -*- coding: utf-8 -*-
import abc
import time
import queue
import typing
import logging
import threading
import contextlib
import collections
from ..core.timer import Tasklet
from ..misc.settings import UiLogMessage
from ..misc.debug import get_debug_timestamp
from .transmit import Transmit, TransmitException, TransmitWarning
from ..core.datatype import CustomEvent, enum_property, DynamicObject
from ..core.threading import ThreadSafeBool, ThreadSafeInteger, ThreadConditionWrap, ThreadLockAndDataWrap

__all__ = ['CommunicationEvent', 'CommunicationEventHandle',
           'CommunicationController', 'CommunicationControllerConnectError',
           'CommunicationObject', 'CommunicationObjectDecodeError', 'CommunicationSection']

CommunicationSection = collections.namedtuple('CommunicationSection', 'request response')


class CommunicationEvent(CustomEvent):
    Type = collections.namedtuple(
        'Type', 'Timeout Restore Warning Exception Logging '
                'Connected Disconnected SectionStart SectionEnd Customize StateChanged AckError'
    )(*('timeout', 'restore', 'warning', 'exception', 'logging',
        'connect', 'disconnected', 'ss', 'se', 'customize', 'state_changed', 'ack_error'))

    type = enum_property('type', Type)

    def __init__(self, type_: Type, data: typing.Any = '', source: typing.Any = None):
        kwargs = dict(type=type_, data=data, source=source)
        super(CommunicationEvent, self).__init__(**kwargs)

    @classmethod
    def info(cls, msg: str, color: str = ''):
        return cls(cls.Type.Logging, data=UiLogMessage.genDefaultInfoMessage(msg, color))

    @classmethod
    def warn(cls, msg: str, color: str = ''):
        return cls(cls.Type.Logging, data=UiLogMessage.genDefaultWarnMessage(msg, color))

    @classmethod
    def debug(cls, msg: str, color: str = ''):
        return cls(cls.Type.Logging, data=UiLogMessage.genDefaultDebugMessage(msg, color))

    @classmethod
    def error(cls, msg: str, color: str = ''):
        return cls(cls.Type.Logging, data=UiLogMessage.genDefaultErrorMessage(msg, color))

    @classmethod
    def exception(cls, msg: str):
        return cls(cls.Type.Exception, data=msg)

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

    @classmethod
    def state_changed(cls, state: typing.Any):
        return cls(cls.Type.StateChanged, data=state)

    @classmethod
    def ack_error(cls, err: typing.Any, request: typing.Any):
        return cls(cls.Type.AckError, data=err, source=request)


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
    def __init__(self, msg: typing.Any):
        self.raw = msg
        self._cond = ThreadConditionWrap()

    def print_log(self) -> bool:
        return not self.is_periodic()

    def is_periodic(self) -> bool:
        return False

    def set_response(self, response):
        self._cond.finished(response)

    def wait_response(self, timeout: float):
        return self._cond.wait(timeout)

    @abc.abstractmethod
    def to_bytes(self) -> bytes:
        """Get binary data from obj"""
        pass

    @classmethod
    @abc.abstractmethod
    def from_bytes(cls, obj, data: bytes):
        """Get object from bytes"""
        pass


class CommunicationControllerConnectError(Exception):
    pass


class CommunicationObjectDecodeError(Exception):
    pass


class CommunicationController:
    MsgPriority = collections.namedtuple('MsgPriority', 'High Middle Low')(*range(3))

    def __init__(self,
                 event_cls,
                 request_cls,
                 response_cls,
                 transmit: Transmit,
                 response_max_length: int,
                 event_callback: typing.Callable[[CommunicationEvent], None],
                 print_ts: bool = False, retry: int = 3, tasklet_interval: float = 0.05, debug_mode: bool = False):
        if not isinstance(transmit, Transmit):
            raise TypeError(f"'transmit' must be a instance of {Transmit.__name__}")

        if not issubclass(event_cls, CommunicationEvent):
            raise TypeError(f"'event_cls' must be a subclass of {CommunicationEvent.__name__}")

        if not issubclass(request_cls, CommunicationObject):
            raise TypeError(f"'request_cls' must be a subclass of {CommunicationObject.__name__}")

        if not issubclass(response_cls, CommunicationObject):
            raise TypeError(f"'response_cls' must be a subclass of {CommunicationObject.__name__}")

        if not callable(event_callback):
            raise TypeError("'event_callback must be callable'")

        self._transmit = transmit
        self._print_ts = print_ts
        self._retry_times = retry
        self._enable_sim = False
        self._queue = queue.PriorityQueue()
        self._exit = ThreadSafeBool(False)
        self._timeout = ThreadSafeBool(False)
        self._timeout_cnt = ThreadSafeInteger(0)
        self._section_seq = ThreadSafeInteger(0)
        self._latest_section = CommunicationSection(None, None)

        self._cur_state = ThreadLockAndDataWrap(None)
        self._prev_state = ThreadLockAndDataWrap(None)
        self._tasklet = Tasklet(schedule_interval=tasklet_interval, name=self.__class__.__name__)

        self._event_cls = event_cls
        self._request_cls = request_cls
        self._response_cls = response_cls
        self._event_callback = event_callback
        self._response_max_length = response_max_length
        self._catch_exception = (TransmitException,) if debug_mode else (AttributeError, TransmitException)

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

    @property
    def timeout(self) -> float:
        return self._transmit.timeout

    def is_timeout(self) -> bool:
        return self._timeout.is_set()

    def is_comm_idle(self, remain: int = 1) -> bool:
        return self._queue.qsize() <= remain

    def wait_comm_idle(self, interval: float = 0.01, remain: int = 1,
                       condition: typing.Callable[[], bool] = lambda: True) -> bool:
        """Wait communication idle

        :param interval: wait interval
        :param remain: comm queue remain request count
        :param condition: if condition is not fulfilled return false
        :return: condition not fulfilled return false, otherwise return true
        """
        while not self.is_comm_idle(remain=remain):
            if not condition():
                return False
            time.sleep(interval)

        return condition()

    def disconnect(self, send_event: bool = False):
        self._exit.set()
        self._transmit.disconnect()
        while self._queue.qsize():
            self._queue.get()

        self._disconnect_callback()

        if send_event:
            self.send_event(self._event_cls.disconnected('active disconnect'))

    def reset_section(self, sid: int = 0):
        self._section_seq.assign(sid)

    def connect(self, address: Transmit.Address, timeout: float, enable_sim: bool = False) -> bool:
        try:
            self._enable_sim = enable_sim
            self._transmit.connect(address, timeout)
        except Exception as e:
            raise CommunicationControllerConnectError(e)
        else:
            self._exit.clear()
            self._timeout.clear()
            self._timeout_cnt.reset()
            self._section_seq.reset()
            threading.Thread(target=self.thread_comm_with_device, daemon=True).start()
            self._connect_callback()
            self.info_msg(f'Connected: {address}, timeout:{timeout}')
            self.send_event(self._event_cls.connected(address, timeout))
            return True

    def info_msg(self, msg: str):
        self.send_event(self._event_cls.info(self._format_log(msg), self._log_color(logging.INFO)))

    def warn_msg(self, msg: str):
        self.send_event(self._event_cls.warn(self._format_log(msg), self._log_color(logging.WARN)))

    def error_msg(self, msg: str):
        self.send_event(self._event_cls.error(self._format_log(msg), self._log_color(logging.ERROR)))

    def debug_msg(self, msg: str):
        self.send_event(self._event_cls.debug(self._format_log(msg), self._log_color(logging.DEBUG)))

    def update_state(self, state: typing.Any) -> bool:
        """Update state if state changed, return true"""
        self._prev_state.assign(self._cur_state.data)
        self._cur_state.assign(state)
        if self._prev_state.equal(state):
            return False

        self.send_event(CommunicationEvent.state_changed(state))
        return True

    def send_event(self, event: CommunicationEvent):
        if callable(self._event_callback):
            self._event_callback(event)

    def send_async_request(self, request: typing.Any, pr: typing.Optional[int] = None) -> bool:
        """Send request do not wait response"""
        return self.send_request_wrap(self._request_cls(request), pr)

    def send_sync_request(self, request: typing.Any, timeout: float = 0.0, pr: typing.Optional[int] = None):
        """Send request and wait response"""
        wrap = self._request_cls(request)
        return wrap.wait_response(timeout or self.timeout) if self.send_request_wrap(wrap, pr) else None

    def send_request_wrap(self, request: CommunicationObject, priority: typing.Optional[int] = None) -> bool:
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

    # noinspection PyMethodMayBeStatic
    # noinspection PyUnusedLocal
    def _log_color(self, level: int) -> str:
        return ''

    def _connect_callback(self):
        pass

    def _disconnect_callback(self):
        pass

    @abc.abstractmethod
    def _simulate_handle(self, request: CommunicationObject) -> bool:
        """Simulator device communication, return true means already handle"""
        pass

    @abc.abstractmethod
    def _response_handle(self, request: CommunicationObject, response: CommunicationObject):
        """Handle device returned response"""
        pass

    @abc.abstractmethod
    def _section_check(self, request: CommunicationObject, response: CommunicationObject, cost_time: float) -> bool:
        """Check if section is valid"""
        pass

    @contextlib.contextmanager
    def section(self, request: CommunicationObject):
        self.send_event(self._event_cls.section_start(self._section_seq.data))
        if request.print_log():
            self.debug_msg(f'[Section: {self._section_seq.data: 07d}]')
        try:
            yield
        except Exception as e:
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
                _, request = self._queue.get(timeout=0.01)
            except (queue.Empty, TypeError) as e:
                if not isinstance(e, queue.Empty):
                    self.send_event(CommunicationEvent.exception(f'{e}'))
                continue

            if not isinstance(request, CommunicationObject):
                continue

            if self._enable_sim and self._simulate_handle(request):
                continue

            retry = 0
            max_retry_times = 1 if request.is_periodic() else self._retry_times
            with self.section(request):
                while retry < max_retry_times and not self._exit:
                    try:
                        # Send request
                        start_time = time.perf_counter()
                        self._transmit.tx(request.to_bytes())

                        if request.print_log():
                            self.debug_msg(f'TX {"=" * 16}>: {request}')

                        # Receive response
                        data = self._transmit.rx(self._response_max_length)
                        cost_time = time.perf_counter() - start_time

                        # Decode and check response
                        try:
                            response = self._response_cls.from_bytes(request, data)
                        except CommunicationObjectDecodeError as e:
                            raw = ' '.join([f'{x:02X}' for x in data])
                            self.error_msg(f'Decode {request} response error: {e}, (Raw: {raw})')
                            self._transmit.flush()
                            continue
                        else:
                            if request.print_log():
                                self.debug_msg(f'RX <{"=" * 16}: {response}')

                            if not self._section_check(request, response, cost_time):
                                self.error_msg(f'Section check failed: {request!r} {response!r}')
                                self._transmit.flush()
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
                                self.warn_msg(f'[{self.__class__.__name__}] retry[{retry}]: {e}({request})')
                                time.sleep(retry * 0.3)
                                self._transmit.flush()
                                continue
                            else:
                                self._timeout.set()
                                self._timeout_cnt.increase()
                                type_ = CommunicationEvent.Type.Timeout
                                self._latest_section = CommunicationSection(request, e)

                        self.send_event(self._event_cls(type_=type_, data=f'{e}'))
                        self.error_msg(f'[{self.__class__.__name__}] Communication warning: {e}({request})')
                        self._transmit.flush()

                        if self._timeout_cnt.great(3, equal=True):
                            msg = 'The number of timeouts exceeds the upper limit'
                            self.error_msg(msg)
                            self.send_event(self._event_cls.disconnected(msg))
                            break
                    except self._catch_exception as e:
                        self.disconnect(send_event=True)
                        self.error_msg(f'[{self.__class__.__name__}] Communication exception: {e}({request})')
                        self._latest_section = CommunicationSection(request, e)
                        self.send_event(self._event_cls.exception(f'Communication exception：{e}'))
                        break

        print(f'[{self.__class__.__name__}]: thread_comm_with_device exit({self._exit.is_set()})!!!')
