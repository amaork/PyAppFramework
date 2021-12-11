# -*- coding: utf-8 -*-
import time
import queue
from threading import Thread
import google.protobuf.message as message
from typing import Callable, Optional, Tuple


from ..misc.settings import LoggingMsgCallback, UiLogMessage
from .transmit import Transmit, TransmitTimeout, TransmitException
__all__ = ['ProtoBufSdk', 'ProtoBufSdkRequestCallback',
           'ProtoBufSdkTimeoutCallback', 'ProtoBufSdkExceptionCallback', 'LoggingMsgCallback',
           'ProtoBufHandle', 'ProtoBufHandleCallback']

# callback(request message, response raw bytes)
ProtoBufSdkRequestCallback = Callable[[message.Message, bytes], None]

ProtoBufSdkTimeoutCallback = Callable[[bool], None]
ProtoBufSdkExceptionCallback = Callable[[Exception], None]

# callback(request raw bytes) ->  response message
ProtoBufHandleCallback = Callable[[bytes], Optional[message.Message]]


class ProtoBufSdk(object):
    def __init__(self,
                 transmit: Transmit,
                 max_msg_length: int,
                 timeout_callback: ProtoBufSdkTimeoutCallback,
                 exception_callback: ProtoBufSdkExceptionCallback,
                 logging_callback: Optional[LoggingMsgCallback] = None):
        """
        Init a protocol buffers sdk
        :param transmit: Data transmit (TCPTransmit or UDPTransmit or self-defined TCPTransmit)
        :param max_msg_length: protocol buffers maximum message length
        :param timeout_callback: when transmit timeout will call this callback
        :param exception_callback: when transmit exception will call this callback
        :param logging_callback: communicate logging callback
        """
        if not isinstance(transmit, Transmit):
            raise TypeError('{!r} required {!r}'.format('transmit', Transmit.__name__))

        self._transmit = transmit
        self._max_msg_length = max_msg_length
        self._comm_queue = queue.PriorityQueue()

        self._timeout = False
        self._logging_callback = logging_callback
        self._timeout_callback = timeout_callback
        self._exception_callback = exception_callback
        Thread(target=self.threadCommunicationHandle, daemon=True).start()

    def __del__(self):
        self._transmit.disconnect()

    @property
    def name(self) -> str:
        return type(self).__name__

    @property
    def connected(self) -> bool:
        return self._transmit.connected

    @property
    def isCommIdle(self, remain: int = 1) -> bool:
        return self._comm_queue.qsize() <= remain

    def _loggingCallback(self, msg: UiLogMessage):
        if callable(self._logging_callback):
            self._logging_callback(msg)

    def _infoLogging(self, msg: str):
        self._loggingCallback(UiLogMessage.genDefaultInfoMessage(msg))

    def _debugLogging(self, msg: str):
        self._loggingCallback(UiLogMessage.genDefaultDebugMessage(msg))

    def _errorLogging(self, msg: str):
        self._loggingCallback(UiLogMessage.genDefaultErrorMessage(msg))

    def disconnect(self):
        self._transmit.disconnect()

    def connect(self, address: Tuple[str, int], timeout: float) -> bool:
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

    def sendRequestToQueue(self,
                           msg: message.Message,
                           callback: Optional[ProtoBufSdkRequestCallback] = None,
                           priority: Optional[int] = None, periodic: bool = True) -> bool:
        """
        Send request to queue
        :param msg: request message
        :param callback: after receive response will call this callback
        :param priority: message priority if set as None using it as normal queue
        :param periodic: it this message is periodic request(do not need retry if send failed)
        :return:
        """
        try:
            if not self.connected or not isinstance(msg, message.Message):
                return False

            priority = time.perf_counter() if priority is None else priority
            self._comm_queue.put((priority, (msg, callback, periodic)))
            return True
        except (queue.Full, TypeError) as e:
            self._errorLogging("{!r} sendRequestToQueue error: {}({})".format(self.name, e, msg))
            return False

    def threadCommunicationHandle(self):
        while True:
            if not self.connected:
                time.sleep(0.05)
                continue

            try:
                _, msg = self._comm_queue.get()
            except (queue.Empty, TypeError):
                continue

            request, callback, periodic = msg
            if not isinstance(request, message.Message):
                continue

            retry = 0
            while retry < 3:
                try:
                    # Send request
                    req_data = request.SerializeToString()
                    if not self._transmit.tx(req_data):
                        raise TransmitTimeout

                    if not periodic:
                        self._debugLogging("Tx[{0:02d}]: {1}[Raw: {2}]".format(len(req_data), request, req_data.hex()))

                    # Receive response
                    res_data = self._transmit.rx(self._max_msg_length)
                    if not res_data:
                        raise TransmitTimeout

                    if not periodic:
                        self._debugLogging("Rx[{0:02d}]: {1}[Raw: {1}]".format(len(res_data), res_data.hex()))

                    # Callback
                    if callable(callback):
                        callback(request, res_data)

                    # Clear timeout flag
                    if self._timeout:
                        self._timeout = False
                        self._timeout_callback(self._timeout)

                    break
                except message.DecodeError as e:
                    self._errorLogging("Decode msg error: {}".format(e))
                except TransmitException as e:
                    self._errorLogging("Comm error: {}".format(e))
                    self._exception_callback(e)
                    break
                except TransmitTimeout:
                    retry += 1
                    time.sleep(retry * 0.3)

                    if retry >= 3:
                        # Set timeout flag
                        if callable(self._timeout_callback):
                            self._infoLogging("{!r}: Timeout".format(self.name))
                            self._timeout = True
                            self._timeout_callback(self._timeout)


class ProtoBufHandle(object):
    def __init__(self,
                 transmit: Transmit,
                 max_msg_length: int,
                 handle_callback: ProtoBufHandleCallback,
                 logging_callback: Optional[LoggingMsgCallback] = None, verbose: bool = False):
        """
        Init a protocol buffers handle for protocol buffer comm simulator
        :param transmit: Data transmit (TCPTransmit or UDPTransmit or self-defined TCPTransmit)
        :param max_msg_length: protocol buffers maximum message length
        :param handle_callback: when received an request will callback this
        :param logging_callback: communicate logging callback
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
        self._logging_callback = logging_callback
        Thread(target=self.threadCommunicationHandle, daemon=True).start()

    def __del__(self):
        self._transmit.disconnect()

    def _loggingCallback(self, msg: UiLogMessage):
        if callable(self._logging_callback):
            self._logging_callback(msg)

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

    def connect(self, address: Tuple[str, int], timeout: float) -> bool:
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

    def threadCommunicationHandle(self):
        while True:
            if not self.connected:
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
                response = self._callback(request)
                if not isinstance(response, message.Message):
                    continue

                response = response.SerializeToString()

                if not self._transmit.tx(response):
                    raise TransmitException("send response error")

                if self._verbose:
                    print(">>> {:.2f}: [{}] {}".format(time.perf_counter(), len(response), response.hex()))
            except AttributeError:
                break
            except message.DecodeError as e:
                self._errorLogging("Decode msg error: {}".format(e))
                continue
            except TransmitException as e:
                self._errorLogging("Comm error: {}".format(e))
                self._transmit.disconnect()
                continue
            except TransmitTimeout:
                continue
