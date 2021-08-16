# -*- coding: utf-8 -*-
import time
import glob
import ctypes
import serial
import platform
from threading import Thread
import serial.tools.list_ports
from raspi_io.utility import scan_server
from typing import Callable, Optional, Union, Tuple, List, Any
from raspi_io import Serial as WebsocketSerial, RaspiSocketError, Query

from .crc16 import crc16
from ..core.datatype import BasicTypeLE, ip4_check


__all__ = ['SerialPort',
           'ReadAckMsg', 'ReadReqMsg',
           'SerialPortProtocolSimulate',
           'SerialTransferProtocol', 'SerialTransferError', 'SerialTransferProtocolReadSimulate']

PrintMsgCallback = Callable[[str], None]
SerialSendCallback = Callable[[bytes], int]
SerialRecvCallback = Callable[[int], bytes]
SimulatorRequestHandle = Callable[[Any], bytes]


class ErrorCode(object):
    E_OK = 0x0
    E_LEN = 0x1
    E_CRC = 0x2
    E_FUNC = 0x3
    E_DATA = 0x4
    E_MODE = 0x5
    E_PROC = 0x6
    E_UNKNOWN = 0x7

    @staticmethod
    def get_desc(code: int) -> str:
        return {
            ErrorCode.E_OK: "OK",
            ErrorCode.E_LEN: "E_LEN",
            ErrorCode.E_CRC: "E_CRC",
            ErrorCode.E_FUNC: "E_FUNC",
            ErrorCode.E_DATA: "E_DATA",
            ErrorCode.E_MODE: "E_MODE",
            ErrorCode.E_PROC: "E_PROC",
            ErrorCode.E_UNKNOWN: "E_UNKNOWN",
        }.get(code, "Unknown")


class BasicMsg(BasicTypeLE):
    def calc_crc(self) -> int:
        return crc16(self.cdata()[1:ctypes.sizeof(self) - 2])

    def calc_len(self) -> int:
        return ctypes.sizeof(self) - 1

    def init_and_check(self, data: bytes) -> Tuple[bool, str]:
        """Init self and check data illegal

        :param data: data
        :return: result or data
        """
        # Init self
        if not self.set_cdata(data):
            return False, ErrorCode.get_desc(ErrorCode.E_LEN)

        # Crc check
        if crc16(self.cdata()[1:]):
            return False, ErrorCode.get_desc(ErrorCode.E_CRC)

        return True, ""


class ReadReqMsg(BasicMsg):
    # Read init request
    INIT_REQ = 0xa

    # Read data request
    DATA_REQ = 0xb

    # Read done request
    DATA_DONE = 0xe

    _fields_ = [
        ('len', ctypes.c_ubyte),
        ('req', ctypes.c_ubyte),
        ('arg', ctypes.c_ushort),
        ('crc16', ctypes.c_ushort),
    ]

    def __init__(self, req: int, arg: int):
        super(ReadReqMsg, self).__init__()
        self.req = req
        self.arg = arg
        self.len = self.calc_len()
        self.crc16 = self.calc_crc()

    def is_init_request(self) -> bool:
        return self.req == self.INIT_REQ

    def is_data_request(self) -> bool:
        return self.req == self.DATA_REQ

    def is_done_request(self) -> bool:
        return self.req == self.DATA_DONE


class ReadAckMsg(BasicMsg):
    # Message payload size
    PAYLOAD_SIZE = 128

    _fields_ = [
        ('len', ctypes.c_ubyte),
        ('ack', ctypes.c_ubyte),
        ('arg', ctypes.c_ushort),
        ('payload', ctypes.c_ubyte * PAYLOAD_SIZE),
        ('crc16', ctypes.c_ushort),
    ]

    @staticmethod
    def create(ack: int, arg: int, payload: bytes) -> BasicMsg:
        instance = ReadAckMsg()
        instance.ack = ack
        instance.arg = arg
        instance.len = instance.calc_len()
        instance.set_data_payload(payload)
        instance.crc16 = instance.calc_crc()
        return instance

    # Get payload data
    def get_data_payload(self) -> bytes:
        return ctypes.string_at(ctypes.addressof(self.payload), ctypes.sizeof(self.payload))

    # Set payload data
    def set_data_payload(self, cdata: bytes):
        size = min(len(cdata), ctypes.sizeof(self.payload))
        ctypes.memmove(ctypes.addressof(self.payload), cdata, size)


class WriteReqMsg(BasicMsg):
    # Write init command
    INIT_REQ = 0xc

    # Write data command
    DATA_REQ = 0xd

    PAYLOAD_SIZE = 128

    _fields_ = [
        ('len', ctypes.c_ubyte),
        ('req', ctypes.c_ubyte),
        ('arg', ctypes.c_ushort),
        ('payload', ctypes.c_ubyte * PAYLOAD_SIZE),
        ('crc16', ctypes.c_ushort),
    ]

    def __init__(self, req: int, arg: int, payload: bytes):
        super(WriteReqMsg, self).__init__()
        self.req = req
        self.arg = arg
        self.len = self.calc_len()
        self.set_payload_data(payload)
        self.crc16 = self.calc_crc()

    def set_payload_data(self, cdata: bytes):
        size = min(len(cdata), ctypes.sizeof(self.payload))
        ctypes.memmove(ctypes.addressof(self.payload), cdata, size)


class WriteAckMsg(BasicMsg):
    _fields_ = [
        ('len', ctypes.c_ubyte),
        ('ack', ctypes.c_ubyte),
        ('arg', ctypes.c_ushort),
        ('crc16', ctypes.c_ushort),
    ]


class SerialTransferError(Exception):
    """SerialTransferProtocol error will raise this exception"""
    pass


class SerialTransferProtocol(object):
    PAYLOAD_SIZE = 128

    def __init__(self, send: SerialSendCallback, recv: SerialRecvCallback):
        """"Init a serial port transfer protocol object

        :param send: serial port send function
        :param recv: serial port receive function
        :return:
        """
        if not hasattr(send, "__call__"):
            raise AttributeError("{} send function is not callable".format(self.__class__.__name__))

        if not hasattr(recv, "__call__"):
            raise AttributeError("{} recv function is not callable".format(self.__class__.__name__))

        self.__send, self.__recv = send, recv

    @staticmethod
    def calc_package_size(data: bytes) -> int:
        return len(data) // SerialTransferProtocol.PAYLOAD_SIZE

    @staticmethod
    def get_package_data(idx: int, data: bytes) -> bytes:
        size = SerialTransferProtocol.calc_package_size(data)
        if not 0 <= idx < size:
            return bytes()

        return data[idx * SerialTransferProtocol.PAYLOAD_SIZE: (idx + 1) * SerialTransferProtocol.PAYLOAD_SIZE]

    def recv(self, callback: Optional[Callable[[float], None]] = None) -> Tuple[bytes, bytes]:
        """Receive data

        :param callback: update recv percentage callback callback(percentage)
        :return: (global data and  package data)
        """
        # Send r_init request, get package_size and global data
        package_size, global_data = self.__r_init()

        # Read package data
        package_data = bytes()
        for package_index in range(package_size):
            package_data += self.__r_data(package_index)

            if callback and hasattr(callback, "__call__"):
                callback((package_index + 1) / (package_size * 1.0) * 100)

        return global_data, package_data

    def send(self, global_data: bytes, package_data: bytes, callback: Optional[Callable[[float], None]] = None) -> bool:
        """Write data

        :param global_data: global data
        :param package_data:  package data
        :param callback: update write percent callback function
        :return: success return true
        """
        package_size = self.calc_package_size(package_data)

        # Send write init request with package total size and global data
        self.__w_init(package_size, global_data)

        # Write all data
        for package_index in range(package_size):
            self.__w_data(package_index, self.get_package_data(package_index, package_data))

            if callback and hasattr(callback, "__call__"):
                callback((package_index + 1) / (package_size * 1.0) * 100)

        return True

    def __basic_transfer(self, req: Union[ReadReqMsg, WriteReqMsg]) -> Union[ReadAckMsg, WriteAckMsg]:
        """Basic transfer

        :param req: will send request data
        :return: ack data
        """
        # Type check
        if isinstance(req, ReadReqMsg):
            ack = ReadAckMsg()
        elif isinstance(req, WriteReqMsg):
            ack = WriteAckMsg()
        else:
            raise SerialTransferError("Request message type error:'{0:s}'".format(req.__class__.__name__))

        try:
            self.__send(req.cdata())
            data = self.__recv(ctypes.sizeof(ack))
            success, error = ack.init_and_check(data)
            if success:
                if ack.ack != req.req:
                    raise SerialTransferError(ErrorCode.get_desc(ack.arg))
                return ack
            else:
                raise SerialTransferError(error)
        except serial.SerialException as error:
            raise SerialTransferError(error)

    def __r_init(self) -> Tuple[int, bytes]:
        """Launch a read transfer session

        :return: total package_size and global_data
        """
        req = ReadReqMsg(ReadReqMsg.INIT_REQ, 0)

        # Send read init request and get ack
        ack = self.__basic_transfer(req)

        # Return package size data global data
        return int(ack.arg), ack.get_data_payload()

    def __r_data(self, package_index: int) -> bytes:
        """Read package_index specified package index

        :param package_index:  will read package data
        :return: result, package_data or error
        """
        req = ReadReqMsg(ReadReqMsg.DATA_REQ, package_index)

        # Send read init request and get ack
        ack = self.__basic_transfer(req)
        return ack.get_data_payload()

    def __w_init(self, package_size: int, global_data: bytes) -> WriteAckMsg:
        """Launch a write transfer section

        :param package_size: will write total package size
        :param global_data: global data
        :return:result/error
        """
        return self.__basic_transfer(WriteReqMsg(WriteReqMsg.INIT_REQ, package_size, global_data))

    def __w_data(self, package_index: int, package_data: bytes) -> WriteAckMsg:
        """Write data

        :param package_index: data package index number
        :param package_data: will write data
        :return:
        """
        return self.__basic_transfer(WriteReqMsg(WriteReqMsg.DATA_REQ, package_index, package_data))


class SerialPort(object):
    def __init__(self, port: str, baudrate: int,
                 bytesize: int = 8, parity: str = 'N', stopbits: int = 1,
                 timeout: float = 0, ending_check: Optional[Callable[[bytes], bool]] = None):
        """Serial port

        :param port: local serial port("COM1" , "/dev/ttyS1"), or WebsocketSerial("xxx.xxx.xxx.xxx", "/dev/ttyS1")
        :param baudrate:  serial port baudrate
        :param bytesize:  number of data bits. Possible values: 5, 6, 7, 8
        :param parity: enable parity checking. Possible values: 'N', 'E', 'O'
        :param stopbits: number of stop bits. Possible values: 1, 2
        :param timeout: serial port timeout
        :param ending_check: dynamic check if receive is ending or not
        """
        self.__timeout = timeout
        self.__ending_check = ending_check

        try:
            # xxx.xxx.xxx.xxx/ttyXXX
            if ip4_check(port.split("/")[0]):
                address = port.split("/")[0]
                remote_port = port.replace(address, "/dev")
                port = (address, remote_port)
                raise AttributeError

            self.__port = serial.Serial(port=port, baudrate=baudrate,
                                        bytesize=bytesize, parity=parity, stopbits=stopbits,
                                        timeout=0.01 if hasattr(ending_check, "__call__") else timeout)
        except (AttributeError, ValueError, TypeError):
            try:
                self.__port = WebsocketSerial(host=port[0], port=port[1], baudrate=baudrate,
                                              bytesize=bytesize, parity=parity, stopbits=stopbits,
                                              timeout=timeout, verbose=0)
            except IndexError:
                raise serial.SerialException("Unknown port type:{}".format(port))
            except ValueError:
                raise serial.SerialException("Open websocket serial port:{} error".format(port))
            except RaspiSocketError:
                raise serial.SerialException("Open websocket serial port:{} timeout".format(port))
            except RuntimeError as err:
                raise serial.SerialException(err)

        self.__port.flushInput()
        self.__port.flushOutput()

    def __repr__(self):
        return "{0:s}, baudrate:{1:d}}".format(self.__port.port, self.__port.baudrate)

    @property
    def raw_port(self) -> Union[serial.Serial, WebsocketSerial]:
        return self.__port

    def close(self):
        self.__port.close()

    def flush(self):
        self.__port.flushInput()
        self.__port.flushOutput()

    def write(self, data: bytes) -> int:
        """Basic send data

        :param data: will send data
        :return: return write data length
        """

        if len(data) == 0:
            raise serial.SerialException("Sending Data length error")

        if not self.__port.isOpen():
            raise serial.SerialException("Serial port: {} is not opened".format(self.__port.port))

        if self.__port.write(data) != len(data):
            raise serial.SerialException("Send data error: data sent is not completed")

        return len(data)

    def read(self, size: int, timeout: Optional[float] = None) -> bytes:
        """Basic receive data

        :param size: receive data size
        :param timeout: receive data timeout(s)
        :return: received data or timeout exception
        """
        start = time.time()
        timeout = timeout if timeout else self.__timeout

        if size == 0:
            raise serial.SerialException("Receive data length error")

        if not self.__port.isOpen():
            raise serial.SerialException("Serial port: {} is not opened".format(self.__port.port))

        data = bytes()
        while len(data) < size and time.time() - start < timeout:
            data += self.__port.read(size - len(data))
            if data and hasattr(self.__ending_check, "__call__") and self.__ending_check(data):
                break

        if not data:
            raise serial.SerialTimeoutException("Receive data timeout!")

        return data

    @staticmethod
    def get_serial_list(timeout: float = 0.04) -> List[str]:
        port_list = list()
        system = platform.system().lower()

        # Scan local port
        if system == "linux":
            for index, port in enumerate(glob.glob("/dev/tty[A-Za-z]*")):
                port_list.append("{}".format(port))
        else:
            for index, port in enumerate(list(serial.tools.list_ports.comports())):
                # Windows serial port is a object linux is a tuple
                device = port.device
                desc = "{0:s}".format(device).split(" - ")[-1]
                port_list.append("{0:s}".format(desc))

        # Scan LAN raspberry serial port
        try:
            for raspberry in scan_server(timeout):
                for port in Query(raspberry).get_serial_list():
                    port_list.append("{}/{}".format(raspberry, port.split("/")[-1]))
        except (RaspiSocketError, IndexError, ValueError, OSError):
            pass

        return port_list


class SerialPortProtocolSimulate(object):
    def __init__(self, send: SerialSendCallback, recv: SerialRecvCallback, error_handle: PrintMsgCallback = print):
        if not hasattr(send, "__call__"):
            raise AttributeError("{} send function is not callable".format(self.__class__.__name__))

        if not hasattr(recv, "__call__"):
            raise AttributeError("{} recv function is not callable".format(self.__class__.__name__))

        self.__running = False
        self.__sim_thread = Thread()
        self.__handle = error_handle
        self.__send, self.__recv = send, recv

    def _get_request_size(self) -> int:
        pass

    def _check_request(self, req: Any) -> Tuple[bool, str]:
        return False, "Unknown request"

    def _get_req_handle(self, req: Any) -> SimulatorRequestHandle:
        pass

    def _error_request(self, req: Any) -> bytes:
        pass

    def __error_handle(self, error: str):
        if hasattr(self.__handle, "__call__"):
            self.__handle(error)

    def __simulate(self):
        while self.__running:
            try:

                # Wait request message from serial port
                try:
                    data = self.__recv(self._get_request_size())
                except serial.SerialException as error:
                    self.__error_handle("Receive request error:{}".format(error))
                    continue

                # Check request message
                result, err_or_req = self._check_request(data)
                if not result:
                    error = err_or_req
                    self.__error_handle("Check request error:{}".format(error))
                    continue

                # Process request and get ack
                req = err_or_req
                handle = self._get_req_handle(req)
                if callable(handle):
                    ack = handle(req)
                else:
                    ack = self._error_request(req)

                # Ack peer
                self.__send(ack)

            except serial.SerialException as error:
                self.__error_handle("SerialPort error:{}".format(error))

    def start(self) -> bool:
        if self.__running:
            print("{} is running!".format(self.__class__.__name__))
            return False

        self.__running = True
        self.__sim_thread = Thread(target=self.__simulate, name="{}".format(self.__class__.__name__))
        self.__sim_thread.setDaemon(True)
        print("{} start running".format(type(self).__name__))
        self.__sim_thread.start()
        return True

    def stop(self):
        self.__running = False
        self.__sim_thread.join()
        print("{} is stopped".format(self.__class__.__name__))


class SerialTransferProtocolReadSimulate(SerialPortProtocolSimulate):
    def __init__(self, send: SerialSendCallback, recv: SerialRecvCallback,
                 data: Tuple[bytes, bytes], error_handle: PrintMsgCallback = print):
        super(SerialTransferProtocolReadSimulate, self).__init__(send, recv, error_handle)
        self.__global_data, self.__config_data = data
        self.__total_package = SerialTransferProtocol.calc_package_size(self.__config_data)

    def _get_request_size(self) -> int:
        return ctypes.sizeof(ReadReqMsg)

    def _check_request(self, data: bytes) -> Tuple[bool, str]:
        if not isinstance(data, bytes):
            return False, "Request data type error!"

        return ReadReqMsg(0, 0).init_and_check(data)

    def _get_req_handle(self, req: ReadReqMsg) -> SimulatorRequestHandle:
        return {
            ReadReqMsg.INIT_REQ: self.read_init,
            ReadReqMsg.DATA_REQ: self.read_data,

        }.get(req.req, self._error_request)

    def _error_request(self, req) -> bytes:
        return bytes()

    def read_init(self, req: ReadReqMsg) -> bytes:
        return ReadAckMsg.create(req.req, self.__total_package, self.__global_data).cdata()

    def read_data(self, req: ReadReqMsg) -> bytes:
        data = SerialTransferProtocol.get_package_data(req.arg, self.__config_data)
        return ReadAckMsg.create(req.req, req.arg, data).cdata()
