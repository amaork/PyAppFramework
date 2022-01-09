# -*- coding: utf-8 -*-
import abc
import time
import socket
import serial
import struct
from threading import Thread
from typing import Callable, List, Optional, Tuple
from google.protobuf.message import Message, DecodeError


from .crc16 import crc16
from .serialport import SerialPort
from ..network.utility import create_socket_and_connect, set_keepalive
__all__ = ['Transmit', 'TransmitTimeout', 'TransmitException',
           'UARTTransmit', 'TCPClientTransmit', 'TCPServerTransmit', 'UartTransmitWithProtobufEndingCheck']


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

    def __repr__(self):
        return str(
            dict(name=type(self).__name__, address=self._address, timeout=self._timeout, connected=self._connected)
        )

    @property
    def timeout(self) -> float:
        return self._timeout

    @property
    def connected(self) -> bool:
        return self._connected

    @abc.abstractmethod
    def tx(self, data: bytes) -> bool:
        pass

    @abc.abstractmethod
    def rx(self, size: int, timeout: float = 0.0) -> bytes:
        pass

    @abc.abstractmethod
    def disconnect(self):
        pass

    @abc.abstractmethod
    def connect(self, address: Tuple[str, int], timeout: float) -> bool:
        pass

    def _update(self, address: Tuple[str, int], timeout: float, connected: bool = False) -> bool:
        self._address = address
        self._timeout = timeout
        self._connected = connected
        return self._connected


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
            self._connected = False
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
            return self._update(address, timeout, True)
        except serial.SerialException as err:
            raise TransmitException(err)

    @staticmethod
    def hex_convert(data: bytes) -> List[str] or bytes:
        if not isinstance(data, bytes):
            return data
        return ["{}".format(data.hex()[x: x + 2]) for x in range(0, len(data.hex()), 2)]


class TCPClientTransmit(Transmit):
    DEFAULT_TIMEOUT = 0.1

    def __init__(self):
        super(TCPClientTransmit, self).__init__()
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def tx(self, data: bytes) -> bool:
        try:
            return self._socket.send(data) == len(data)
        except socket.timeout as err:
            raise TransmitTimeout(err)
        except socket.error as err:
            raise TransmitException(err)

    def rx(self, size: int, timeout: float = 0) -> bytes:
        try:
            timeout = timeout or self.timeout
            self._socket.settimeout(timeout)
            return self._socket.recv(size)
        except socket.timeout as err:
            raise TransmitTimeout(err)
        except socket.error as err:
            raise TransmitException(err)

    def disconnect(self):
        try:
            self._socket.close()
            self._connected = False
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
            timeout = timeout or self.DEFAULT_TIMEOUT
            self._socket = create_socket_and_connect(address[0], address[1], timeout)
            return self._update(address, timeout, True)
        except RuntimeError as err:
            raise TransmitException(err)


class TCPServerTransmit(Transmit):
    def __init__(self):
        super(TCPServerTransmit, self).__init__()
        self._client_address = ('', -1)
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    @property
    def client(self) -> Tuple[str, int]:
        return self._client_address

    def handle(self, listen_socket: socket.socket):
        while True:
            self._socket, self._client_address = listen_socket.accept()

            # Set keepalive to detect client lost connection
            set_keepalive(self._socket, after_idle_sec=1, interval_sec=1, max_fails=3)
            self._socket.setblocking(True)
            self._connected = True

            # Waiting client disconnect
            while self._connected:
                time.sleep(0.1)

    def connect(self, address: Tuple[str, int], _timeout: float = 0.0) -> bool:
        listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        listen_socket.bind(address)
        listen_socket.listen(1)
        Thread(target=self.handle, args=(listen_socket,), name=self.__class__.__name__, daemon=True).start()
        return self._update(address, _timeout, False)

    def disconnect(self):
        try:
            self._socket.close()
            self._connected = False
        except AttributeError:
            pass

    def tx(self, data: bytes) -> bool:
        try:
            return self._socket.send(data) == len(data)
        except socket.timeout as err:
            raise TransmitTimeout(err)
        except socket.error as err:
            raise TransmitException(err)

    def rx(self, size: int, timeout: float = 0) -> bytes:
        try:
            return self._socket.recv(size)
        except socket.timeout as err:
            raise TransmitTimeout(err)
        except socket.error as err:
            raise TransmitException(err)


class UartTransmitWithProtobufEndingCheck(UARTTransmit):
    def __init__(self, msg_cls, with_crc16: bool = False):
        if not issubclass(msg_cls, Message):
            raise TypeError(f"'msg_cls' must be and {Message.__name__} type")
        self.__msg_cls = msg_cls
        self.__with_crc16 = with_crc16
        super(UartTransmitWithProtobufEndingCheck, self).__init__(ending_check=self.ending_check)

    def ending_check(self, data: bytes) -> bool:
        try:
            if not data:
                return False

            if self.__with_crc16 and crc16(data):
                return False

            self.__msg_cls.FromString(data[0:-2])
            return True
        except DecodeError:
            return False
