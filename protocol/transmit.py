# -*- coding: utf-8 -*-
import abc
import time
import socket
import serial
import struct
import threading
from typing import Callable, List, Optional, Tuple
from google.protobuf.message import Message, DecodeError


from .crc16 import crc16
from .serialport import SerialPort
from ..core.threading import ThreadSafeBool
from ..network.utility import create_socket_and_connect, set_keepalive, tcp_socket_recv_data, tcp_socket_send_data
__all__ = ['Transmit', 'TransmitWarning', 'TransmitException',
           'UARTTransmit', 'UartTransmitWithProtobufEndingCheck',
           'TCPClientTransmit', 'TCPServerTransmit', 'TCPSocketTransmit', 'TCPServerTransmitHandle']


class TransmitException(Exception):
    pass


class TransmitWarning(Exception):
    pass


class Transmit(object):
    DEFAULT_TIMEOUT = 0.1

    def __init__(self):
        self._timeout = 0.0
        self._address = ('', 0)
        self._connected = ThreadSafeBool(False)

    def __del__(self):
        self.disconnect()
        self._connected.clear()

    def __repr__(self):
        return str(
            dict(name=type(self).__name__, address=self._address, timeout=self._timeout, connected=self._connected.data)
        )

    @property
    def timeout(self) -> float:
        return self._timeout

    @property
    def address(self) -> Tuple[str, int]:
        return self._address

    @property
    def connected(self) -> bool:
        return self._connected.is_set()

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
        self._connected.assign(connected)
        return self._connected.is_set()


class UARTTransmit(Transmit):
    VERBOSE = False
    RESPONSE_MIN_LEN = 4
    DEFAULT_TIMEOUT = 0.1

    def __init__(self, length_fmt: str = '',
                 checksum: Optional[Callable[[bytes], int]] = None,
                 ending_check: Optional[Callable[[bytes], bool]] = None, verbose: bool = False):
        """
        UARTTransmit
        :param length_fmt: msg header length struct pack format
        :param checksum: msg tail checksum algo
        :param ending_check: msg ending check
        :param verbose:  print verbose message
        """
        self.__serial = None
        self.__length_fmt = length_fmt
        self.__ending_check = ending_check
        self.__verbose = verbose or UARTTransmit.VERBOSE
        self.__checksum = checksum if callable(checksum) else crc16
        super(UARTTransmit, self).__init__()

    def tx(self, data: bytes) -> bool:
        try:
            header = ''
            checksum = struct.pack("<H", self.__checksum(data))
            self.print_msg('tx: {0:03d} {1} {2}'.format(len(data), self.hex_convert(data), checksum.hex()))

            if self.__length_fmt:
                header = struct.pack(self.__length_fmt, len(data) + struct.calcsize(self.__length_fmt))

            msg = header + data + checksum
            return self.__serial.write(msg) == len(msg)
        except serial.SerialException as err:
            raise TransmitException(err)

    def rx(self, size: int, timeout: float = 0) -> bytes:
        try:
            # Receive length first
            if self.__length_fmt:
                header = self.__serial.read(struct.calcsize(self.__length_fmt))
                if not header:
                    raise TransmitWarning('Read length error')

                # Get length from header
                size = struct.unpack(self.__length_fmt, header)[0]

            data = self.__serial.read(size)
            self.print_msg(('rx: {0:03d} {1}'.format(len(data), self.hex_convert(data))))

            # Check received data length
            if len(data) < self.RESPONSE_MIN_LEN:
                raise TransmitWarning("Too short:{}".format(len(data)))

            # Check data checksum
            if self.__checksum(data):
                raise TransmitWarning("Crc16 verify failed")

            # Return payload
            return data[0:-2]
        except serial.SerialTimeoutException as err:
            raise TransmitWarning(err)
        except (struct.error, serial.SerialException, MemoryError) as err:
            raise TransmitException(err)

    def print_msg(self, msg: str):
        if self.__verbose:
            print(f'[{self._address[0]}] {msg}')

    def disconnect(self):
        try:
            self.__serial.flush()
            self.__serial.close()
            self._connected.clear()
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


class TCPSocketTransmit(Transmit):
    MSG_LEN_FMT = '>L'

    def __init__(self, sock: socket.socket, with_length: bool = False, disconnect_callback: Optional[Callable] = None):
        super(TCPSocketTransmit, self).__init__()
        self._socket = sock
        self._with_length = with_length
        self._disconnect_callback = disconnect_callback

    @property
    def raw_socket(self) -> socket.socket:
        return self._socket

    @raw_socket.setter
    def raw_socket(self, sock: socket.socket):
        if isinstance(sock, socket.socket):
            self._socket = sock

    def tx(self, data: bytes) -> bool:
        try:
            msg = struct.pack(self.MSG_LEN_FMT, len(data)) + data if self._with_length else data
            return sum(tcp_socket_send_data(self._socket, msg)) == len(msg)
        except socket.timeout as err:
            raise TransmitWarning(err)
        except (socket.error, ConnectionError) as err:
            raise TransmitException(err)

    def rx(self, size: int, timeout: float = 0.0) -> bytes:
        try:
            if self._with_length:
                header = self._socket.recv(struct.calcsize(self.MSG_LEN_FMT))
                # Peer disconnected
                if not header:
                    self.disconnect()
                    return header

                # Get message length first
                size = struct.unpack(self.MSG_LEN_FMT, header)[0]

            # Read payload data
            data = tcp_socket_recv_data(self._socket, size)

            # Peer disconnected
            if not data:
                self.disconnect()
            return data
        except socket.timeout as err:
            raise TransmitWarning(err)
        except (socket.error, IndexError, struct.error, MemoryError, ConnectionError) as err:
            raise TransmitException(err)

    def disconnect(self):
        if callable(self._disconnect_callback):
            self._disconnect_callback()

        self._socket.close()
        self._connected.clear()

    def connect(self, address: Tuple[str, int], timeout: float) -> bool:
        self._socket.settimeout(timeout)
        self._update(address, timeout, True)
        return True


class TCPClientTransmit(Transmit):
    DEFAULT_TIMEOUT = 0.1

    def __init__(self, with_length: bool = False):
        super(TCPClientTransmit, self).__init__()
        self._server_address = ('', -1)
        self._socket = TCPSocketTransmit(socket.socket(socket.AF_INET, socket.SOCK_STREAM), with_length=with_length)

    def tx(self, data: bytes) -> bool:
        return self._socket.tx(data)

    def rx(self, size: int, timeout: float = 0) -> bytes:
        return self._socket.rx(size, timeout)

    def disconnect(self):
        self._connected.clear()
        self._socket.disconnect()

    @property
    def server(self) -> Tuple[str, int]:
        return self._server_address

    def connect(self, address: Tuple[str, int], timeout: float = DEFAULT_TIMEOUT) -> bool:
        """
        Connect tcp server
        :param address: (host, port)
        :param timeout: socket timeout in seconds
        :return:
        """
        try:
            self._server_address = address
            timeout = timeout or self.DEFAULT_TIMEOUT
            self._socket.raw_socket = create_socket_and_connect(address[0], address[1], timeout)
            return self._update(self._socket.raw_socket.getsockname(), timeout, True)
        except RuntimeError as err:
            raise TransmitException(err)


class TCPServerTransmit(Transmit):
    def __init__(self, with_length: bool = False):
        super(TCPServerTransmit, self).__init__()
        self._client_address = ('', -1)
        self._stopped = threading.Event()
        self._socket = TCPSocketTransmit(socket.socket(socket.AF_INET, socket.SOCK_STREAM), with_length=with_length)

    def __del__(self):
        self._stopped.set()
        self._socket.disconnect()

    @property
    def client(self) -> Tuple[str, int]:
        return self._client_address

    def accept_handle(self, listen_socket: socket.socket):
        while not self._stopped.is_set():
            self._socket.raw_socket, self._client_address = listen_socket.accept()

            # Set keepalive to detect client lost connection
            set_keepalive(self._socket.raw_socket, after_idle_sec=1, interval_sec=1, max_fails=3)
            self._socket.raw_socket.setblocking(True)
            self._connected.set()

            # Waiting client disconnect
            while self._connected.is_set():
                time.sleep(0.1)

    def connect(self, address: Tuple[str, int], _timeout: float = 0.0) -> bool:
        try:
            listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            listen_socket.bind(address)
        except OSError as e:
            raise TransmitException(f'{self.__class__.__name__}.connect error: {e}')
        else:
            listen_socket.listen(1)
            threading.Thread(target=self.accept_handle, args=(listen_socket,), daemon=True).start()
            return self._update(address, _timeout, False)

    def disconnect(self):
        self._connected.clear()
        self._socket.disconnect()

    def tx(self, data: bytes) -> bool:
        return self._socket.tx(data)

    def rx(self, size: int, timeout: float = 0) -> bytes:
        return self._socket.rx(size, timeout)


class TCPServerTransmitHandle:
    def __init__(self, new_connection_callback: Callable[[TCPSocketTransmit], None],
                 timeout: float = 0.3, with_length: bool = False):
        self._timeout = timeout
        self._with_length = with_length
        self._stopped = threading.Event()
        self._new_connection_callback = new_connection_callback
        self._listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)

    def __del__(self):
        self._stopped.set()
        self._listen_socket.close()

    def start(self, address: Tuple[str, int], backlog: int = 1):
        try:
            self._listen_socket.bind(address)
        except OSError as e:
            raise TransmitException(f'{self.__class__.__name__}.connect error: {e}')
        else:
            self._listen_socket.listen(backlog)
            threading.Thread(target=self.accept_handle, args=(self._listen_socket,), daemon=True).start()

    def accept_handle(self, listen_socket: socket.socket):
        while not self._stopped.is_set():
            try:
                client_socket, client_address = listen_socket.accept()
            except OSError:
                break

            # Set keepalive to detect client lost connection
            set_keepalive(client_socket, after_idle_sec=1, interval_sec=1, max_fails=3)
            client_socket.setblocking(True)

            # Create TCPSocketTransmit and call callback
            transmit = TCPSocketTransmit(client_socket, with_length=self._with_length)
            transmit.connect(client_address, self._timeout)

            self._new_connection_callback(transmit)


class UartTransmitWithProtobufEndingCheck(UARTTransmit):
    def __init__(self, msg_cls, with_crc16: bool = False, length_fmt: str = ''):
        if not issubclass(msg_cls, Message):
            raise TypeError(f"'msg_cls' must be and {Message.__name__} type")
        self.__msg_cls = msg_cls
        self.__with_crc16 = with_crc16
        super().__init__(ending_check=self.ending_check, length_fmt=length_fmt)

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
