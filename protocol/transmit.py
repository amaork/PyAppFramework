# -*- coding: utf-8 -*-
import abc
import time
import socket
import typing
import serial
import struct
import threading
import multiprocessing
from typing import Callable, List, Optional
from google.protobuf.message import Message, DecodeError


from .serialport import SerialPort
from ..misc.debug import get_stack_info
from ..core.threading import ThreadSafeBool
from ..network.utility import create_socket_and_connect, set_keepalive, tcp_socket_recv_data, tcp_socket_send_data
__all__ = ['Transmit', 'TransmitWarning', 'TransmitException',
           'UARTTransmit', 'UartTransmitCustomize', 'UartTransmitWithProtobufEndingCheck',
           'TCPClientTransmit', 'TCPServerTransmit', 'TCPSocketTransmit', 'TCPServerTransmitHandle']


class TransmitException(Exception):
    pass


class TransmitWarning(Exception):
    def is_timeout(self):
        return 'timeout' in f'{self}'


class Transmit(object):
    DEFAULT_TIMEOUT = 0.1
    Address = typing.Tuple[str, int]

    def __init__(self, processing: bool = False):
        self._timeout = 0.0
        self._address = ('', 0)
        self._connected = ThreadSafeBool(False, processing=processing)

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
    def address(self) -> Address:
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

    def flush(self):
        pass

    @abc.abstractmethod
    def disconnect(self):
        pass

    @abc.abstractmethod
    def connect(self, address: Address, timeout: float) -> bool:
        pass

    def _update(self, address: Address, timeout: float, connected: bool = False) -> bool:
        self._address = address
        self._timeout = timeout
        self._connected.assign(connected)
        return self._connected.is_set()


class UARTTransmit(Transmit):
    VERBOSE = False
    RESPONSE_MIN_LEN = 1
    DEFAULT_TIMEOUT = 0.1

    def __init__(self, length_fmt: str = '',
                 checksum: Optional[Callable[[bytes], int]] = None,
                 ending_check: Optional[Callable[[bytes], bool]] = None,
                 verbose: bool = False, processing: bool = False):
        """
        UARTTransmit
        :param length_fmt: msg header length struct pack format
        :param checksum: msg tail checksum algo
        :param ending_check: msg ending check
        :param verbose:  print verbose message
        """
        self.__serial = None
        self.__checksum = checksum
        self.__length_fmt = length_fmt
        self.__ending_check = ending_check
        self.__verbose = verbose or UARTTransmit.VERBOSE
        super(UARTTransmit, self).__init__(processing)

    def tx(self, data: bytes) -> bool:
        try:
            header = b''
            checksum = struct.pack("<H", self.__checksum(data)) if callable(self.__checksum) else b''
            self.print_msg('tx: {0:03d} {1} (crc16:{2})'.format(len(data), self.hex_convert(data), checksum.hex()))

            if self.__length_fmt:
                header = struct.pack(self.__length_fmt, len(data) + struct.calcsize(self.__length_fmt))

            msg = header + data + checksum
            if self.__serial.write(msg) != len(msg):
                raise TransmitException('tx error')
            return True
        except serial.SerialException as err:
            raise TransmitException(err)

    def rx(self, size: int, timeout: float = None) -> bytes:
        try:
            # Receive length first, without ending check
            if self.__length_fmt:
                header = self.__serial.read(struct.calcsize(self.__length_fmt), timeout)
                if not header:
                    raise TransmitWarning('Read length error')

                # Get length from header
                size = struct.unpack(self.__length_fmt, header)[0]

            data = self.__serial.read(size, timeout)
            self.print_msg(('rx: {0:03d} {1}'.format(len(data), self.hex_convert(data))))

            # Check received data length
            if len(data) < self.RESPONSE_MIN_LEN:
                raise TransmitWarning("Too short:{}".format(len(data)))

            # Check data checksum
            if callable(self.__checksum) and self.__checksum(data):
                raise TransmitWarning("Crc16 verify failed")

            # Return payload
            return data[0:-2] if callable(self.__checksum) else data
        except serial.SerialTimeoutException as err:
            raise TransmitWarning(err)
        except (struct.error, serial.SerialException, MemoryError) as err:
            raise TransmitException(err)

    def flush(self):
        self.__serial.flush()

    def print_msg(self, msg: str):
        if self.__verbose:
            print(f'[{self._address[0]}] {msg}')

    def disconnect(self):
        try:
            self.__serial.flush()
            self.__serial.close()
            self._connected.clear()
        except (serial.SerialException, AttributeError):
            pass

    def connect(self, address: Transmit.Address, timeout: float) -> bool:
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
    DefaultLengthFormat = '>L'

    def __init__(self, sock: socket.socket, address: Transmit.Address = ('', -1),
                 length_fmt: str = '', processing: bool = False, disconnect_callback: Optional[Callable] = None):
        """
        TCPSocketTransmit
        :param sock: socket instance
        :param address: self address
        :param length_fmt: msg header length struct pack format
        :param processing: is multiple processing env
        :param disconnect_callback: disconnect callback
        """
        super(TCPSocketTransmit, self).__init__(processing)
        self._socket = sock
        self._address = address
        self._length_fmt = length_fmt
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
            msg = struct.pack(self._length_fmt, len(data)) + data if self._length_fmt else data
            return sum(tcp_socket_send_data(self._socket, msg)) == len(msg)
        except socket.timeout as err:
            raise TransmitWarning(err)
        except (socket.error, ConnectionError) as err:
            raise TransmitException(err)

    def rx(self, size: int, timeout: float = 0.0) -> bytes:
        timeout = timeout or self._timeout
        if timeout:
            self._socket.settimeout(timeout)

        try:
            if self._length_fmt:
                header = self._socket.recv(struct.calcsize(self._length_fmt))
                # Peer closed
                if not header:
                    self.disconnect()
                    return header

                # Get message length first
                size = struct.unpack(self._length_fmt, header)[0]

            # Read payload data
            data = tcp_socket_recv_data(self._socket, size)

            # Peer closed
            if not self._length_fmt and not data:
                self.disconnect()
                
            return data
        except socket.timeout as err:
            raise TransmitWarning(err)
        except BlockingIOError as err:
            raise TransmitWarning(err)
        except (socket.error, IndexError, struct.error, MemoryError, ConnectionError) as err:
            raise TransmitException(err)

    def disconnect(self):
        if callable(self._disconnect_callback):
            self._disconnect_callback()

        self._socket.close()
        self._connected.clear()

    def connect(self, address: Transmit.Address, timeout: float) -> bool:
        self._socket.settimeout(timeout)
        self._update(address, timeout, True)
        return True


class TCPClientTransmit(Transmit):
    DEFAULT_TIMEOUT = 0.1

    def __init__(self, length_fmt: str = '', processing: bool = False):
        super(TCPClientTransmit, self).__init__(processing)
        self._server_address = ('', -1)
        self._socket = TCPSocketTransmit(
            socket.socket(socket.AF_INET, socket.SOCK_STREAM), length_fmt=length_fmt, processing=processing
        )

    def tx(self, data: bytes) -> bool:
        return self._socket.tx(data)

    def rx(self, size: int, timeout: float = 0) -> bytes:
        return self._socket.rx(size, timeout)

    def disconnect(self):
        self._connected.clear()
        self._socket.disconnect()

    @property
    def server(self) -> Transmit.Address:
        return self._server_address

    def connect(self, address: Transmit.Address, timeout: float = DEFAULT_TIMEOUT) -> bool:
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
    def __init__(self, length_fmt: str = '', processing: bool = False):
        super(TCPServerTransmit, self).__init__(processing)
        self._client_address = ('', -1)
        self._stopped = multiprocessing.Event() if processing else threading.Event()
        self._socket = TCPSocketTransmit(
            socket.socket(socket.AF_INET, socket.SOCK_STREAM), length_fmt=length_fmt, processing=processing
        )

    def __del__(self):
        self._stopped.set()
        self._socket.disconnect()

    @property
    def client(self) -> Transmit.Address:
        return self._client_address

    def stop(self):
        self._stopped.set()

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

    def connect(self, address: Transmit.Address, backlog: int = 1) -> bool:
        try:
            listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            listen_socket.bind(address)
        except OSError as e:
            raise TransmitException(f'{self.__class__.__name__}.connect error: {e}')
        else:
            listen_socket.listen(backlog)
            threading.Thread(target=self.accept_handle, args=(listen_socket,), daemon=True).start()
            return self._update(address, 0.0, False)

    def disconnect(self):
        self._connected.clear()
        self._socket.disconnect()

    def tx(self, data: bytes) -> bool:
        return self._socket.tx(data)

    def rx(self, size: int, timeout: float = 0) -> bytes:
        return self._socket.rx(size, timeout)


class TCPServerTransmitHandle:
    def __init__(self, new_connection_callback: Callable[[TCPSocketTransmit, typing.Any], None],
                 length_fmt: str = '', processing: bool = False, verbose: bool = False):
        self._verbose = verbose
        self._processing = processing
        self._length_fmt = length_fmt
        self._new_connection_callback = new_connection_callback
        self._listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self._stopped = multiprocessing.Event() if processing else threading.Event()

    def __del__(self):
        self._stopped.set()
        self._listen_socket.close()

    def stop(self):
        self._stopped.set()

    def is_running(self) -> bool:
        return not self._stopped.is_set()

    def wait_stop(self, timeout: float = None):
        self._stopped.wait(timeout)

    def print_debug_msg(self, msg: str, force: bool = False):
        if self._verbose or force:
            print(f'{get_stack_info()}: {msg}')

    def start(self, address: Transmit.Address, backlog: int = 1, timeout: float = None, kwargs: dict = None):
        try:
            self._listen_socket.bind(address)
        except OSError as e:
            raise TransmitException(f'{self.__class__.__name__}.connect error: {e}')
        else:
            self._listen_socket.listen(backlog)
            args = (self._listen_socket, timeout, kwargs or dict())
            threading.Thread(target=self.accept_handle, args=args, daemon=True).start()

    def accept_handle(self, listen_socket: socket.socket, timeout: typing.Optional[float], kwargs: dict):
        while not self._stopped.is_set():
            try:
                self.print_debug_msg('Before')
                client_socket, client_address = listen_socket.accept()
            except OSError as e:
                self.print_debug_msg(f'{e}', force=True)
                break
            else:
                self.print_debug_msg(f'After: {client_address}')

            # Set keepalive to detect client lost connection
            client_socket.setblocking(True)
            set_keepalive(client_socket, after_idle_sec=1, interval_sec=1, max_fails=3)

            # Create TCPSocketTransmit
            transmit = TCPSocketTransmit(
                client_socket, client_address, length_fmt=self._length_fmt, processing=bool(self._processing)
            )
            # Mark TCPSocketTransmit is connected and set timeout
            transmit.connect(client_address, timeout)

            # Callback with TCPSocketTransmit and custom args
            self._new_connection_callback(transmit, **kwargs)

        self.print_debug_msg('Sopped, exit', force=True)


class UartTransmitCustomize(UARTTransmit):
    def __init__(self, length_fmt: str = '',
                 msg_check: Optional[Callable[[bytes], bool]] = None,
                 checksum: Optional[Callable[[bytes], int]] = None, checksum_len: int = None, **kwargs):
        """UartTransmitCustomize

        :param length_fmt: msg header length struct format
        :param msg_check:  check if msg is complete
        :param checksum: msg tail checksum
        :param checksum_len: checksum length
        """

        self.__msg_check = msg_check
        self.__checksum = checksum
        self.__checksum_len = checksum_len
        super().__init__(ending_check=self.ending_check, length_fmt=length_fmt, checksum=checksum, **kwargs)

    def ending_check(self, data: bytes) -> bool:
        try:
            if not data:
                return False

            if callable(self.__checksum) and self.__checksum(data):
                return False

            payload = data[:-self.__checksum_len] if callable(self.__checksum) and self.__checksum_len else data
            if callable(self.__msg_check) and not self.__msg_check(payload):
                return False

            return True
        except TypeError:
            return False


class UartTransmitWithProtobufEndingCheck(UartTransmitCustomize):
    def __init__(self, msg_cls, length_fmt: str = '',
                 checksum: Optional[Callable[[bytes], int]] = None, checksum_len: int = None, **kwargs):
        if not issubclass(msg_cls, Message):
            raise TypeError(f"'msg_cls' must be and {Message.__name__} type")

        self.__msg_cls = msg_cls
        super().__init__(
            msg_check=self.msg_check, length_fmt=length_fmt, checksum=checksum, checksum_len=checksum_len, **kwargs
        )

    def msg_check(self, data: bytes) -> bool:
        try:
            self.__msg_cls.FromString(data)
        except DecodeError:
            return False
        else:
            return True
