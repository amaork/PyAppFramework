# -*- coding: utf-8 -*-

import ctypes
import serial
from threading import Thread
from raspi_io import Serial as WebsocketSerial, RaspiSocketError

from .crc16 import crc16
from ..core.datatype import BasicTypeLE


__all__ = ['SerialPort',
           'ReadAckMsg', 'SerialPortProtocolSimulate',
           'SerialTransferProtocol', 'SerialTransferError', 'SerialTransferProtocolReadSimulate']


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
    def get_desc(code):
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
    def calc_crc(self):
        return crc16(self.cdata()[1:ctypes.sizeof(self) - 2])

    def calc_len(self):
        return ctypes.sizeof(self) - 1

    def init_and_check(self, data):
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

        return True, self


class ReadReqMsg(BasicMsg):
    # Read init request
    INIT_REQ = 0xa

    # Read data request
    DATA_REQ = 0xb

    # Read done request
    DATA_DONE = 0xe

    _fields_ = [
        ('len',     ctypes.c_ubyte),
        ('req',     ctypes.c_ubyte),
        ('args',    ctypes.c_ushort),
        ('crc16',   ctypes.c_ushort),
    ]

    def __init__(self, req, args):
        super(ReadReqMsg, self).__init__()
        self.req = req
        self.args = args
        self.len = self.calc_len()
        self.crc16 = self.calc_crc()

    def is_init_request(self):
        return self.req == self.INIT_REQ

    def is_data_request(self):
        return self.req == self.DATA_REQ

    def is_done_request(self):
        return self.req == self.DATA_DONE


class ReadAckMsg(BasicMsg):
    # Message payload size
    PAYLOAD_SIZE = 128

    _fields_ = [
        ('len',     ctypes.c_ubyte),
        ('ack',     ctypes.c_ubyte),
        ('args',    ctypes.c_ushort),
        ('payload', ctypes.c_ubyte * PAYLOAD_SIZE),
        ('crc16',   ctypes.c_ushort),
    ]

    @property
    def args(self):
        return self.args

    @staticmethod
    def create(ack, args, payload):
        instance = ReadAckMsg()
        instance.ack = ack
        instance.args = args
        instance.len = instance.calc_len()
        instance.set_data_payload(payload)
        instance.crc16 = instance.calc_crc()
        return instance

    # Get payload data
    def get_data_payload(self):
        return buffer(self)[4: 4 + self.PAYLOAD_SIZE]

    # Set payload data
    def set_data_payload(self, cdata):
        size = min(len(cdata), ctypes.sizeof(self.payload))
        ctypes.memmove(ctypes.addressof(self.payload), cdata, size)


class WriteReqMsg(BasicMsg):
    # Write init command
    INIT_REQ = 0xc

    # Write data command
    DATA_REQ = 0xd

    PAYLOAD_SIZE = 128

    _fields_ = [

        ('len',     ctypes.c_ubyte),
        ('req',     ctypes.c_ubyte),
        ('args',    ctypes.c_ushort),
        ('payload', ctypes.c_ubyte * PAYLOAD_SIZE),
        ('crc16',   ctypes.c_ushort),
    ]

    def __init__(self, req, args, payload):
        super(WriteReqMsg, self).__init__()
        self.req = req
        self.args = args
        self.len = self.calc_len()
        self.set_payload_data(payload)
        self.crc16 = self.calc_crc()

    def set_payload_data(self, cdata):
        size = min(len(cdata), ctypes.sizeof(self.payload))
        ctypes.memmove(ctypes.addressof(self.payload), cdata, size)


class WriteAckMsg(BasicMsg):

    _fields_ = [

        ('len',     ctypes.c_ubyte),
        ('ack',     ctypes.c_ubyte),
        ('args',    ctypes.c_ushort),
        ('crc16',   ctypes.c_ushort),
    ]

    @property
    def args(self):
        return self.args


class SerialTransferError(Exception):
    """SerialTransferProtocol error will raise this exception"""
    pass


class SerialTransferProtocol(object):
    PAYLOAD_SIZE = 128

    def __init__(self, send, recv):
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
    def calc_package_size(data):
        return len(data) / SerialTransferProtocol.PAYLOAD_SIZE

    @staticmethod
    def get_package_data(idx, data):
        size = SerialTransferProtocol.calc_package_size(data)
        if not 0 <= idx < size:
            return ""

        return data[idx * SerialTransferProtocol.PAYLOAD_SIZE: (idx + 1) * SerialTransferProtocol.PAYLOAD_SIZE]

    def recv(self, callback=None):
        """Receive data

        :param callback: update recv percentage callback callback(percentage)
        :return: (global data and  package data)
        """
        # Send r_init request, get package_size and global data
        package_size, global_data = self.__r_init()

        # Read package data
        package_data = ""
        for package_index in range(package_size):
            package_data += self.__r_data(package_index)

            if callback and hasattr(callback, "__call__"):
                callback((package_index + 1) / (package_size * 1.0) * 100)

        return global_data, package_data

    def send(self, global_data, package_data, callback=None):
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

    def __basic_transfer(self, req):
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
                    raise SerialTransferError(ErrorCode.get_desc(ack.args))
                return ack
            else:
                raise SerialTransferError(error)
        except serial.SerialException as error:
            raise SerialTransferError(error)

    def __r_init(self):
        """Launch a read transfer session

        :return: total package_size and global_data
        """
        req = ReadReqMsg(ReadReqMsg.INIT_REQ, 0)

        # Send read init request and get ack
        ack = self.__basic_transfer(req)

        # Return package size data global data
        return int(ack.args), ack.get_data_payload()

    def __r_data(self, package_index):
        """Read package_index specified package index

        :param package_index:  will read package data
        :return: result, package_data or error
        """
        req = ReadReqMsg(ReadReqMsg.DATA_REQ, package_index)

        # Send read init request and get ack
        ack = self.__basic_transfer(req)
        return ack.get_data_payload()

    def __w_init(self, package_size, global_data):
        """Launch a write transfer section

        :param package_size: will write total package size
        :param global_data: global data
        :return:result/error
        """
        return self.__basic_transfer(WriteReqMsg(WriteReqMsg.INIT_REQ, package_size, global_data))

    def __w_data(self, package_index, package_data):
        """Write data

        :param package_index: data package index number
        :param package_data: will write data
        :return:
        """
        return self.__basic_transfer(WriteReqMsg(WriteReqMsg.DATA_REQ, package_index, package_data))


class SerialPort(object):
    def __init__(self, port, baudrate, timeout=0):
        """Serial port

        :param port: local serial port("COM1" , "/dev/ttyS1"), or WebsocketSerial("xxx.xxx.xxx.xxx", "/dev/ttyS1")
        :param baudrate:  serial port baudrate
        :param timeout: serial port timeout
        """
        try:

            self.__port = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
        except (AttributeError, ValueError, TypeError):
            try:
                self.__port = WebsocketSerial(host=port[0], port=port[1], baudrate=baudrate, timeout=timeout, verbose=0)
            except ValueError:
                raise serial.SerialException("Open websocket serial port:{} error".format(port))
            except RaspiSocketError:
                raise serial.SerialException("Open websocket serial port:{} timeout".format(port))
            except RuntimeError as err:
                raise serial.SerialException(err)

        self.__port.flushInput()
        self.__port.flushOutput()

    def __str__(self):
        return "{0:s}, baudrate:{1:d}}".format(self.__port.port, self.__port.baudrate)

    @property
    def raw_port(self):
        return self.__port

    def close(self):
        self.__port.close()

    def flush(self):
        self.__port.flushInput()
        self.__port.flushOutput()

    def write(self, data):
        """Basic send data

        :param data: will send data
        :return: return write data length
        """

        if len(data) == 0:
            raise serial.SerialException("Sending Data length error")

        if not self.__port.isOpen():
            raise serial.SerialException("Serial port: {0:x} is not opened".format(self.__port.port))

        if self.__port.write(data) != len(data):
            raise serial.SerialException("Send data error: data sent is not completed")

        return len(data)

    def read(self, size):
        """Basic receive data

        :param size: receive data size
        :return: received data or timeout exception
        """

        if size == 0:
            raise serial.SerialException("Receive data length error")

        if not self.__port.isOpen():
            raise serial.SerialException("Serial port: {0:x} is not opened".format(self.__port.port))

        data = ""
        while len(data) != size:
            tmp = self.__port.read(size - len(data))
            if len(tmp) == 0:
                raise serial.SerialException("Receive data timeout!")

            data += tmp

        return data


class SerialPortProtocolSimulate(object):
    def __init__(self, send, recv, error_handle=print):
        if not hasattr(send, "__call__"):
            raise AttributeError("{} send function is not callable".format(self.__class__.__name__))

        if not hasattr(recv, "__call__"):
            raise AttributeError("{} recv function is not callable".format(self.__class__.__name__))

        self.__running = False
        self.__sim_thread = Thread()
        self.__handle = error_handle
        self.__send, self.__recv = send, recv

    def _get_request_size(self):
        pass

    def _check_request(self, req):
        return False, "Unknown request"

    def _get_req_handle(self, req):
        pass

    def _error_request(self, req):
        pass

    def __error_handle(self, error):
        if hasattr(self.__handle, "__call__"):
            self.__handle(error)

    def __simulate(self):
        while self.__running:
            try:

                # Wait request message from serial port
                try:
                    data = self.__recv(self._get_request_size())
                except serial.SerialException as error:
                    self.__error_handle("Receive request error:{0:s}".format(error))
                    continue

                # Check request message
                result, err_or_req = self._check_request(data)
                if not result:
                    error = err_or_req
                    self.__error_handle("Check request error:{0:s}".format(error))
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
                self.__error_handle("SerialPort error:{0:s}".format(type(self).__name__, error))

    def start(self):
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
    def __init__(self, send, recv, data, error_handle=print):
        super(SerialTransferProtocolReadSimulate, self).__init__(send, recv, error_handle)
        self.__global_data, self.__config_data = data
        self.__total_package = SerialTransferProtocol.calc_package_size(self.__config_data)

    def _get_request_size(self):
        return ctypes.sizeof(ReadReqMsg)

    def _check_request(self, data):
        if not isinstance(data, str):
            return False, "Request data type error!"

        return ReadReqMsg(0, 0).init_and_check(data)

    def _get_req_handle(self, req):
        if not isinstance(req, ReadReqMsg):
            return self._check_request

        return {

            ReadReqMsg.INIT_REQ: self.read_init,
            ReadReqMsg.DATA_REQ: self.read_data,

        }.get(req.req, self._error_request)

    def _error_request(self, req):
        return ""

    def read_init(self, req):
        return ReadAckMsg.create(req.req, self.__total_package, self.__global_data).cdata()

    def read_data(self, req):
        data = SerialTransferProtocol.get_package_data(req.args, self.__config_data)
        return ReadAckMsg.create(req.req, req.args, data).cdata()
