# -*- coding: utf-8 -*-
import time
import queue
import socket
import serial
import struct
import logging
import collections
from threading import Thread
import google.protobuf.message as message
from typing import Callable, List, Optional, Union, Tuple


from .crc16 import crc16
from .serialport import SerialPort
from ..misc.settings import UiLogMessage
from ..network.utility import create_socket_and_connect
__all__ = ['ProtoBufSdkCallback',
           'TransmitException', 'TransmitTimeout',
           'TCPTransmit', 'UARTTransmit', 'ProtoBufSdk']

ProtoBufSdkCallback = Callable[[message.Message, bytes], None]


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
        try:
            self._timeout = timeout or self.DEFAULT_TIMEOUT
            self.__serial = SerialPort(port=address[0], baudrate=address[1],
                                       timeout=timeout, ending_check=self.__ending_check)
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
    INFO_LOGGING_COLOR = '#FFFFFF'
    DEBUG_LOGGING_COLOR = '#BF00BF'
    ERROR_LOGGING_COLOR = '#FF0000'
    PRIORITY = collections.namedtuple('PRIORITY', ['VERY_HIGH', 'HIGH', 'MEDIUM', 'LOW'])(*range(4))

    def __init__(self,
                 transmit: Transmit,
                 max_msg_length: int,
                 timeout_callback: Callable,
                 logging_callback: Optional[Callable[[UiLogMessage], None]] = None):
        if not isinstance(transmit, Transmit):
            raise TypeError('{!r} required {!r}'.format('transmit', Transmit.__name__))

        self._transmit = transmit
        self._max_msg_length = max_msg_length
        self._comm_queue = queue.PriorityQueue()
        self._logging_callback = logging_callback
        self._timeout_callback = timeout_callback
        self._th = Thread(target=self.threadCommunicationHandle)
        self._th.setDaemon(True)
        self._th.start()

    def __del__(self):
        self._transmit.disconnect()
        self._th.join(1)

    @property
    def connected(self):
        return self._transmit.connected

    def _timeoutCallback(self):
        if callable(self._timeout_callback):
            self._timeout_callback()

    def _loggingCallback(self, msg: UiLogMessage):
        if callable(self._logging_callback):
            self._logging_callback(msg)

    def _infoLogging(self, text: str):
        self._loggingCallback(UiLogMessage(content=text, level=logging.INFO, color=self.INFO_LOGGING_COLOR))

    def _debugLogging(self, text: str):
        self._loggingCallback(UiLogMessage(content=text, level=logging.INFO, color=self.DEBUG_LOGGING_COLOR))

    def _errorLogging(self, text: str):
        self._loggingCallback(UiLogMessage(content=text, level=logging.INFO, color=self.ERROR_LOGGING_COLOR))

    def disconnect(self):
        self._transmit.disconnect()

    def connect(self, address: Tuple[str, int], timeout: float) -> bool:
        return self._transmit.connect(address=address, timeout=timeout)

    def sendRequestToQueue(self, msg: message.Message,
                           callback: Optional[ProtoBufSdkCallback] = None,
                           priority: Union[int, float] = PRIORITY.LOW, periodic: bool = True):
        try:
            if not self.connected or not isinstance(msg, message.Message):
                return

            self._comm_queue.put((priority, (msg, callback, periodic)))
        except (queue.Full, TypeError) as e:
            print("sendRequestToQueue error: {}".format(e))

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
                except AttributeError:
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
                        self._timeoutCallback()
