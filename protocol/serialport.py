# -*- coding: utf-8 -*-

import ctypes
import serial

from .crc16 import crc16
from ..core.datatype import BasicTypeLE


__all__ = ['SerialPort', 'SerialTransfer', 'ReadAckMsg']


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


class SerialTransfer(object):
    def __init__(self, port, baudrate, timeout=1, verbose=False):
        """"Init a serial port transfer object

        :param port: Serial port name
        :param baudrate: comm baudrate
        :param timeout: peer byte timeout value
        :param verbose: verbose message output
        :return:
        """

        self.__verbose = verbose
        self.__port = SerialPort(port, baudrate, timeout)

    @staticmethod
    def calc_package_size(data):
        return 0 if not isinstance(data, str) else len(data) / WriteReqMsg.PAYLOAD_SIZE

    @staticmethod
    def get_package_data(idx, data):
        if not isinstance(idx, int) or not isinstance(data, str):
            return ""

        size = SerialTransfer.calc_package_size(data)
        if not 0 <= idx < size:
            return ""

        return data[idx * WriteReqMsg.PAYLOAD_SIZE: (idx + 1) * WriteReqMsg.PAYLOAD_SIZE]

    def read(self, callback=None):
        # Send r_init request
        result, data = self.__r_init()
        if not result:
            return result, data

        # Get package size and global data
        package_size, global_data = data[0], data[1]

        # Verbose
        if self.__verbose:
            print "Read init success, package size:{0:d}".format(package_size)

        # Read package data
        package_data = ""
        for package_index in range(package_size):
            result, data = self.__r_data(package_index)
            if not result:
                return False, data
            else:
                package_data += data

            if self.__verbose:
                print "Read data package[{0:03d}] success".format(package_index)

            if callback and hasattr(callback, "__call__"):
                callback((package_index + 1) / (package_size * 1.0) * 100)

        return True, (global_data, package_data)

    def write(self, global_data, package_data, callback=None):
        """Write data

        :param global_data: global data
        :param package_data:  package data
        :param callback: update write percent callback function
        :return:
        """
        package_size = self.calc_package_size(package_data)

        # Send write init request with package total size and global data
        result, error = self.__w_init(package_size, global_data)
        if not result:
            return False, error

        # Verbose
        if self.__verbose:
            print "Write init success, package size: {0:d}".format(package_size)

        # Write all data
        for package_index in range(package_size):
            result, data = self.__w_data(package_index, self.get_package_data(package_index, package_data))
            if not result:
                return False, data

            if self.__verbose:
                print "Write data package[{0:03d}] success".format(package_index)

            if callback and hasattr(callback, "__call__"):
                callback((package_index + 1) / (package_size * 1.0) * 100)

        return True, ""

    def __basic_transfer(self, req):
        """Basic transfer

        :param req: will send request data
        :return: result, ack data or error
        """
        # Type check
        if isinstance(req, ReadReqMsg):
            ack = ReadAckMsg()
        elif isinstance(req, WriteReqMsg):
            ack = WriteAckMsg()
        else:
            return False, "Request message type error:{0:s}".format(type(req))

        # Send request
        result, error = self.__port.send(req.cdata())
        if not result:
            return result, error

        # Receive ack
        result, data = self.__port.recv(ctypes.sizeof(ack))
        if not result:
            return result, data

        # Check ack data
        return ack.init_and_check(data)

    def __r_init(self):
        """Launch a read transfer section

        :return: result, data(package_size, global_data) or error
        """
        req = ReadReqMsg(ReadReqMsg.INIT_REQ, 0)

        # Send read init request and get ack
        result, data = self.__basic_transfer(req)
        if not result or not isinstance(data, ReadAckMsg):
            return result, data
        else:
            return True, (int(data.args), data.get_data_payload())

    def __r_data(self, package_index):
        """Read package_index specified package index

        :param package_index:  will read package data
        :return: result, package_data or error
        """
        req = ReadReqMsg(ReadReqMsg.DATA_REQ, package_index)

        # Send read init request and get ack
        result, data = self.__basic_transfer(req)
        if not result or not isinstance(data, ReadAckMsg):
            return result, data
        else:
            return True, data.get_data_payload()

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
    def __init__(self, port, baudrate, timeout=None):
        self.__port = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
        self.__port.flushInput()
        self.__port.flushOutput()

    def __del__(self):
        if self.__port.isOpen():
            self.__port.flushInput()
            self.__port.flushOutput()
            self.__port.close()

    def __str__(self):
        return "{0:s}, baudrate:{1:d}}".format(self.__port.port, self.__port.baudrate)

    @property
    def raw_port(self):
        return self.__port

    def send(self, data):
        """Basic send data

        :param data: will send data
        :return: result, error
        """

        try:

            if len(data) == 0:
                return False, "Sending Data length error"

            if not self.__port.isOpen():
                return False, "Serial port: {0:x} is not opened".format(self.__port.port)

            if self.__port.write(data) != len(data):
                return False, "Send data error: data sent is not completed"

            return True, ""

        except serial.SerialException, e:
            return False, "Send data exception: {0:s}".format(e)

    def recv(self, size, timeout=None):
        """Basic receive data

        :param size: receive data size
        :param timeout: receive data timeout
        :return: result/receive data
        """

        data = ""

        try:

            if size == 0:
                return False, "Receive data length error"

            if not self.__port.isOpen():
                return False, "Serial port: {0:x} is not opened".format(self.__port.port)

            if isinstance(timeout, (int, float)):
                self.__port.timeout = timeout

            while len(data) != size:
                tmp = self.__port.read(size - len(data))

                if len(tmp) == 0:
                    return False, "Receive data timeout!"

                data += tmp

            return True, data

        except serial.SerialException, e:
            return False, "Receive data exception: {0:s}".format(e)
