# -*- coding: utf-8 -*-
import abc
import time
import typing
from threading import Thread
import google.protobuf.message as message

from ..core.timer import Task, Tasklet
from ..misc.settings import UiLogMessage
from .template import CommunicationEvent, CommunicationObject
from .transmit import Transmit, TransmitWarning, TransmitException
__all__ = ['ProtoBufSdkRequestCallback', 'ProtoBufHandle', 'ProtoBufHandleCallback', 'PBMessageWrap']

# callback(request message, response raw bytes)
ProtoBufSdkRequestCallback = typing.Callable[[message.Message, bytes], None]

# callback(request raw bytes) ->  response message
ProtoBufHandleCallback = typing.Callable[[bytes, typing.Tuple[str, int]], typing.Optional[message.Message]]


class PBMessageWrap(CommunicationObject):
    def __init__(self, msg: message.Message):
        if not isinstance(msg, message.Message):
            raise TypeError(f"'msg' must be a instance of {message.Message.__name__!r}")

        self.raw = msg

    def __repr__(self):
        return f'{self.raw}({self.to_bytes().hex()})'

    def to_bytes(self) -> bytes:
        return self.raw.SerializeToString()

    @classmethod
    @abc.abstractmethod
    def from_bytes(cls, obj, data: bytes):
        pass


class ProtoBufHandle(object):
    def __init__(self,
                 transmit: Transmit,
                 max_msg_length: int,
                 handle_callback: ProtoBufHandleCallback,
                 event_callback: typing.Callable[[CommunicationEvent], None], verbose: bool = False):
        """
        Init a protocol buffers handle for protocol buffer comm simulator
        :param transmit: Data transmit (TCPTransmit or UDPTransmit or self-defined TCPTransmit)
        :param max_msg_length: protocol buffers maximum message length
        :param handle_callback: when received a request will call back this
        :param event_callback: communicate event callback
        :param verbose: show communicate verbose detail
        """
        if not isinstance(transmit, Transmit):
            raise TypeError('{!r} required {!r}'.format('transmit', Transmit.__name__))

        if not callable(handle_callback):
            raise TypeError('{!r} required {!r}'.format('handle_callback', 'callable object'))

        self._verbose = verbose
        self._transmit = transmit
        self._callback = handle_callback
        self._max_msg_length = max_msg_length
        self._event_callback = event_callback
        self._tasklet = Tasklet(schedule_interval=0.1, name=self.__class__.__name__)
        self._tasklet.add_task(Task(func=self.taskDetectConnection, timeout=0.1), immediate=True)
        Thread(target=self.threadCommunicationHandle, name=f'ProtoBufHandle_{transmit.address}', daemon=True).start()

    def __del__(self):
        self._transmit.disconnect()

    def event_callback(self, type_: CommunicationEvent.Type, data: typing.Any = ''):
        self._event_callback(CommunicationEvent(type_=type_, source=self._transmit.address, data=data))

    def _loggingCallback(self, msg: UiLogMessage):
        self.event_callback(CommunicationEvent.Type.Logging, msg)

    def _infoLogging(self, msg: str):
        self._loggingCallback(UiLogMessage.genDefaultInfoMessage(msg))

    def _debugLogging(self, msg: str):
        self._loggingCallback(UiLogMessage.genDefaultDebugMessage(msg))

    def _errorLogging(self, msg: str):
        self._loggingCallback(UiLogMessage.genDefaultErrorMessage(msg))

    @property
    def name(self) -> str:
        return type(self).__name__

    @property
    def connected(self) -> bool:
        return self._transmit.connected

    def disconnect(self):
        self._transmit.disconnect()

    def connect(self, address: typing.Tuple[str, int], timeout: float) -> bool:
        """
        Init transmit
        :param address: for TCPTransmit is (host, port) for UARTTransmit is (port, baudrate)
        :param timeout: transmit communicate timeout is seconds
        :return: success return true, failed return false
        """
        result = self._transmit.connect(address=address, timeout=timeout)
        msg = "{!r} connect {}({})".format(self.name, "success" if result else "failed", address)
        self._infoLogging(msg) if result else self._errorLogging(msg)
        return result

    def taskDetectConnection(self, task: Task):
        if not self._transmit.connected:
            task.reschedule()
        else:
            self.event_callback(CommunicationEvent.Type.Connected)

    def threadCommunicationHandle(self):
        while True:
            if not self.connected:
                self.event_callback(CommunicationEvent.Type.Disconnected)
                time.sleep(0.01)
                continue

            try:
                # Receive request
                request = self._transmit.rx(self._max_msg_length)
                if not request:
                    continue

                if self._verbose:
                    print("<<< {:.2f}: [{}] {}".format(time.perf_counter(), len(request), request.hex()))

                # Call callback get response
                response = self._callback(request, self._transmit.address)
                if not isinstance(response, message.Message):
                    continue

                response = response.SerializeToString()

                if not self._transmit.tx(response):
                    raise TransmitException("send response error")

                if self._verbose:
                    print(">>> {:.2f}: [{}] {}".format(time.perf_counter(), len(response), response.hex()))
            except AttributeError as e:
                self.event_callback(CommunicationEvent.Type.Exception, e)
                break
            except message.DecodeError as e:
                self._errorLogging("Decode msg error: {}".format(e))
                continue
            except TransmitException as e:
                self.event_callback(CommunicationEvent.Type.Disconnected, f'e')
                self._tasklet.add_task(Task(func=self.taskDetectConnection, timeout=0.1))
                self._errorLogging("Comm error: {}".format(e))
                self._transmit.disconnect()
                continue
            except TransmitWarning:
                continue
