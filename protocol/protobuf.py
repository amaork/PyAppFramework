# -*- coding: utf-8 -*-
import time
import queue
import socket
import serial
import struct
from threading import Thread
import google.protobuf.message as message
from typing import Callable, List, Optional, Tuple


from .crc16 import crc16
from .serialport import SerialPort
from ..misc.settings import UiLogMessage
from ..network.utility import create_socket_and_connect
__all__ = ['TransmitException', 'TransmitTimeout',
           'TCPTransmit', 'UARTTransmit',
           'ProtoBufSdk', 'ProtoBufSdkCallback',
           'ProtoBufHandle', 'ProtoBufHandleCallback']

# callback(request message, response raw bytes)
ProtoBufSdkCallback = Callable[[message.Message, bytes], None]

# callback(request raw bytes) ->  response message
ProtoBufHandleCallback = Callable[[bytes], Optional[message.Message]]


class TransmitException(Exception):
    pass


class TransmitTimeout(Exception):
    pass


class Transmit(object):
    DEFAULT_TIMEOUT = 0.1

    def __init__(self):
        self._timeout = 0.0
        self._address = ('', 0)
        self._connected = False

    def __del__(self):
        self.disconnect()
        self._connected = False

    def tx(self, data: bytes) -> bool:
        pass

    def rx(self, size: int, timeout: float = 0) -> bytes:
        pass

    def disconnect(self):
        pass

    def connect(self, address: Tuple[str, int], timeout: float) -> bool:
        pass

    @property
    def timeout(self) -> float:
        return self._timeout

    @property
    def connected(self) -> bool:
        return self._connected


class TCPTransmit(Transmit):
    DEFAULT_TIMEOUT = 0.1

    def __init__(self):
        super(TCPTransmit, self).__init__()
        self.__socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def tx(self, data: bytes) -> bool:
        try:
            return self.__socket.send(data) == len(data)
        except socket.timeout as err:
            raise TransmitTimeout(err)
        except socket.error as err:
            raise TransmitException(err)

    def rx(self, size: int, timeout: float = 0) -> bytes:
        try:
            timeout = timeout or self.timeout
            self.__socket.settimeout(timeout)
            return self.__socket.recv(size)
        except socket.timeout as err:
            raise TransmitTimeout(err)
        except socket.error as err:
            raise TransmitException(err)

    def disconnect(self):
        try:
            self.__socket.close()
        except AttributeError:
            pass

    def connect(self, address: Tuple[str, int], timeout: float = DEFAULT_TIMEOUT) -> bool:
        """
        Connect tcp server
        :param address: (host, port)
        :param timeout: socket timeout in seconds
        :return:
        """
        try:
            self._address = address
            self._timeout = timeout or self.DEFAULT_TIMEOUT
            self.__socket = create_socket_and_connect(address[0], address[1], timeout)
            self._connected = True
            return self.connected
        except RuntimeError as err:
            raise TransmitException(err)


class UARTTransmit(Transmit):
    VERBOSE = False
    RESPONSE_MIN_LEN = 4
    DEFAULT_TIMEOUT = 0.1

    def __init__(self, ending_check: Optional[Callable[[bytes], bool]] = None):
        super(UARTTransmit, self).__init__()
        self.__serial = None
        self.__ending_check = ending_check

    def tx(self, data: bytes) -> bool:
        try:
            data += struct.pack("<H", crc16(data))
            if self.VERBOSE:
                print('tx: {0:03d} {1}'.format(len(data), self.hex_convert(data)))
            return self.__serial.write(data) == len(data)
        except serial.SerialException as err:
            raise TransmitException(err)

    def rx(self, size: int, timeout: float = 0) -> bytes:
        try:
            data = self.__serial.read(size)
            if self.VERBOSE:
                print('rx: {0:03d} {1}'.format(len(data), self.hex_convert(data)))

            # Check received data length
            if len(data) < self.RESPONSE_MIN_LEN:
                raise TransmitTimeout("Too short:{}".format(len(data)))

            # Check data checksum
            if crc16(data):
                raise TransmitException("Crc16 verify failed")

            # Return payload
            return data[0:-2]
        except serial.SerialTimeoutException as err:
            raise TransmitTimeout(err)
        except serial.SerialException as err:
            raise TransmitException(err)

    def disconnect(self):
        try:
            self.__serial.flush()
            self.__serial.close()
        except AttributeError:
            pass

    def connect(self, address: Tuple[str, int], timeout: float) -> bool:
        """
        Open serial port
        :param address: (port name, baudrate)
        :param timeout: serial timeout in seconds
        :return:
        """
        try:
            self._timeout = timeout or self.DEFAULT_TIMEOUT
            self.__serial = SerialPort(port=address[0], baudrate=address[1],
                                       timeout=self._timeout, ending_check=self.__ending_check)
            self.__serial.flush()
            self._connected = True
            return self.connected
        except serial.SerialException as err:
            raise TransmitException(err)

    @staticmethod
    def hex_convert(data: bytes) -> List[str] or bytes:
        if not isinstance(data, bytes):
            return data
        return ["{}".format(data.hex()[x: x + 2]) for x in range(0, len(data.hex()), 2)]


class ProtoBufSdk(object):
    def __init__(self,
                 transmit: Transmit,
                 max_msg_length: int,
                 timeout_callback: Callable,
                 logging_callback: Optional[Callable[[UiLogMessage], None]] = None):
        """
        Init a protocol buffers sdk
        :param transmit: Data transmit (TCPTransmit or UDPTransmit or self-defined TCPTransmit)
        :param max_msg_length: protocol buffers maximum message length
        :param timeout_callback: when transmit timeout will call this callback
        :param logging_callback: communicate logging callback
        """
        if not isinstance(transmit, Transmit):
            raise TypeError('{!r} required {!r}'.format('transmit', Transmit.__name__))

        self._transmit = transmit
        self._max_msg_length = max_msg_length
        self._comm_queue = queue.PriorityQueue()

        self._logging_callback = logging_callback
        self._timeout_callback = timeout_callback
        Thread(target=self.threadCommunicationHandle, daemon=True).start()

    def __del__(self):
        self._transmit.disconnect()

    @property
    def name(self) -> str:
        return type(self).__name__

    @property
    def connected(self) -> bool:
        return self._transmit.connected

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
                           callback: Optional[ProtoBufSdkCallback] = None,
                           priority: Optional[int] = None, periodic: bool = True):
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
                return

            priority = time.perf_counter() if priority is None else priority
            self._comm_queue.put((priority, (msg, callback, periodic)))
        except (queue.Full, TypeError) as e:
            self._errorLogging("{!r} sendRequestToQueue error: {}({})".format(self.name, e, msg))

    def threadCommunicationHandle(self):
        while True:
            if not self.connected:
                time.sleep(0.1)
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

                    break
                except message.DecodeError as e:
                    self._errorLogging("Decode msg error: {}".format(e))
                except TransmitException as e:
                    self._errorLogging("Comm error: {}".format(e))
                    break
                except TransmitTimeout:
                    retry += 1
                    time.sleep(retry * 0.3)

                    if retry >= 3:
                        if callable(self._timeout_callback):
                            self._infoLogging("{!r}: Timeout".format(self.name))
                            self._timeout_callback()


class ProtoBufHandle(object):
    def __init__(self,
                 transmit: Transmit,
                 max_msg_length: int,
                 handle_callback: ProtoBufHandleCallback,
                 logging_callback: Optional[Callable[[UiLogMessage], None]] = None, verbose: bool = False):
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
                continue
            except TransmitTimeout:
                continue
