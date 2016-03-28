# -*- coding: utf-8 -*-

import sys
import ctypes
import serial
sys.path.append("../")

from protocol.crc16 import crc16
from core.datatype import BasicTypeLE


__all__ = ['SerialTransfer']


class BasicMsg(BasicTypeLE):
    # Error ack
    __ERR_ACK = 0xff

    # Error code
    __ERR_CODE = {

        "E_OK": (0x0, "Ok"),
        "E_LEN": (0x1, "Frame length error"),
        "E_CRC": (0x2, "Frame data crc error"),
        "E_CODE": (0x3, "Function code error"),
        "E_DATA": (0x4, "Function data error"),
        "E_MODE": (0x5, "Peer work mode error"),
        "E_PROC": (0x6, "Peer process error"),
        "E_UNKNOWN": (0x7, "Unknown error"),
    }

    def get_error_desc(self, code):
        if code in self.__ERR_CODE.keys():
            return self.__ERR_CODE.get(code)[1]
        else:
            return self.get_error_desc("E_UNKNOWN")

    def get_error_code(self, code):
        if code in self.__ERR_CODE.keys():
            return self.__ERR_CODE.get(code)[0]
        else:
            return self.get_error_code("E_UNKNOWN")

    def calc_crc(self):
        return crc16(self.cdata()[1:ctypes.sizeof(self) - 2])

    def calc_len(self):
        return ctypes.sizeof(self) - 1

    def init_and_check(self, data, size):
        """Init self and check data illegal

        :param data: data
        :param size: data size
        :return: Init result, error code
        """
        if size != ctypes.sizeof(self):
            return False, self.get_error_desc("E_LEN")

        # Init self
        self.set_cdata(data, size)

        # Crc check
        if crc16(self.cdata()[1:]):
            return False, self.get_error_desc("E_CRC")

        # Ack check
        if self.ack == self.__ERR_ACK:
            if self.args in [err[0] for err in self.__ERR_CODE.values()]:
                return False, self.get_error_desc(self.args)
            else:
                return False, self.get_error_desc("E_UNKNOWN")

        # Ack check
        return True, self.get_error_desc("E_OK")


class ReadReqMsg(BasicMsg):

    # Read init request
    INIT_REQ = 0xa

    # Read data request
    DATA_REQ = 0xb

    _fields_ = [
        ('len',     ctypes.c_ubyte),
        ('req',     ctypes.c_ubyte),
        ('args',    ctypes.c_ushort),
        ('crc16',   ctypes.c_ushort),
    ]

    def __init__(self, req, args):
        super(ReadReqMsg, self).__init__()
        self.len = self.calc_len()
        self.req = req
        self.args = args
        self.crc16 = self.calc_crc()


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

    # Get payload data
    def get_data_payload(self):
        return buffer(self)[4: 4 + self.PAYLOAD_SIZE]


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
        self.len = self.calc_len()
        self.req = req
        self.args = args
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


class ErrorAckMsg(WriteAckMsg):
    pass


class SerialTransfer(object):
    def __init__(self, timeout=1, verbose=False):
        """"Init a serial port transfer object

        :param timeout: peer byte timeout value
        :param verbose: verbose message output
        :return:
        """

        self.port_name = ""
        self.verbose = verbose
        self.timeout = timeout
        self.port = serial.Serial()

    def init(self, port, baudrate, timeout):
        """Serial port init

        :param port: Serial port name
        :param baudrate: comm baudrate
        :param timeout: timeout value
        :return: result, error
        """

        try:

            if self.port.isOpen():
                return False, "Error, duplicate init"

            # Open serial port and flush input/output
            self.port = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
            self.port.flushInput()
            self.port.flushOutput()
            self.port_name = port

        except serial.SerialException, e:
            error = "Serial: {0:s} open failed: {1:s}".format(port, e)
            print error
            return False, error

        return True, port

    def read(self):
        # Send r_init request
        result, data = self.__r_init()
        if not result:
            return result, data

        # Get package size and global data
        package_size, global_data = data[0], data[1]

        # Verbose
        if self.verbose:
            print "Read init success, package size:{0:d}".format(package_size)

        # Read package data
        package_data = ""
        for package_index in range(package_size):
            result, data = self.__r_data(package_index)
            if not result:
                return False, data
            else:
                package_data += data

            if self.verbose:
                print "Read data package[{0:03d}] success".format(package_index)

        return True, (global_data, package_data)

    def write(self, global_data, package_data):
        """Write data

        :param global_data: global data
        :param package_data:  package data
        :return:
        """

        payload_size = WriteReqMsg.PAYLOAD_SIZE
        package_size = len(package_data) / payload_size

        # Write init
        result, error = self.__w_init(package_size, global_data)
        if not result:
            return False, error

        # Verbose
        if self.verbose:
            print "Write init success, package size: {0:d}".format(package_size)

        # Write all data
        for package_index in range(package_size):
            temp_data = package_data[package_index * payload_size: (package_index + 1) * payload_size]
            result, data = self.__w_data(package_index, temp_data)
            if not result:
                return False, data

            if self.verbose:
                print "Write data package[{0:03d}] success".format(package_index)

        return True, ""

    def set_timeout(self, timeout):
        if not isinstance(timeout, int):
            print "Timeout value type error"
            return False

        self.timeout = timeout
        return True

    def get_timeout(self):
        return self.timeout

    def __basic_send(self, data):
        """Basic send data

        :param data: will send data
        :return: result/error
        """

        try:

            if len(data) == 0:
                return False, "Send Data length error"

            if not self.port.isOpen():
                return False, "Serial port: {0:x} is not opened".format(self.port_name)

            if self.port.write(data) != len(data):
                return False, "Send data error: data sent is not completed"

        except serial.SerialException, e:
            return False, "Send data exception: {0:s}".format(e)

        return True, ""

    def __basic_receive(self, size):
        """Basic receive data

        :param size: receive data size
        :return: result/receive data
        """

        data = ""
        receive_count = 0

        try:

            if size == 0:
                return False, "Receive data length error"

            if not self.port.isOpen():
                return False, "Serial port: {0:x} is not opened".format(self.port_name)

            while len(data) != size:

                tmp = self.port.read(size - len(data))
                data += tmp

                # Timeout check
                receive_count += 1
                if receive_count >= size * self.timeout:
                    break

            return True, data

        except serial.SerialException, e:
            return False, "Send data exception: {0:s}".format(e)

    def __basic_transfer(self, req, ack):
        """Basic transfer

        :param req: will send request data
        :param ack: will received ack data
        :return: result, ack/error
        """

        error_ack = ErrorAckMsg()

        # Type check
        if not issubclass(req.__class__, BasicMsg) or not issubclass(ack.__class__, BasicMsg):
            return False, "TypeCheckError:{0:s}, {1:s}".format(type(req), type(ack))

        # Send request
        result, error = self.__basic_send(req.cdata())
        if not result:
            return result, error

        # Receive ack
        result, data = self.__basic_receive(ctypes.sizeof(ack))
        if not result:
            return result, data

        # Check ack data
        result, error = ack.init_and_check(data, len(data))
        if not result:
            # Peer replay a error ack message
            if error == error_ack.get_error_code("E_LEN") and len(data) == ctypes.sizeof(error_ack):
                return error_ack.init_and_check(data, len(data))

            return result, error

        # Return ack data
        return True, ack

    def __r_init(self):
        """Launch a read transfer section

        :return:
        """

        ack = ReadAckMsg()
        req = ReadReqMsg(ReadReqMsg.INIT_REQ, 0)

        # Send read init request and get ack
        result, data = self.__basic_transfer(req, ack)
        if not result:
            return result, data
        else:
            return True, (int(data.args), data.get_data_payload())

    def __r_data(self, package_index):
        """Read package_index specified package index

        :param package_index:  will read package data
        :return: result/(package_index, package_data)
        """

        ack = ReadAckMsg()
        req = ReadReqMsg(ReadReqMsg.DATA_REQ, package_index)

        # Send read init request and get ack
        result, data = self.__basic_transfer(req, ack)
        if not result:
            return result, data
        else:
            return True, ack.get_data_payload()

    def __w_init(self, package_size, global_data):
        """Launch a write transfer section

        :param package_size: will write total package size
        :param global_data: global data
        :return:result/error
        """

        ack = WriteAckMsg()
        req = WriteReqMsg(WriteReqMsg.INIT_REQ, package_size, global_data)

        result, error = self.__basic_transfer(req, ack)
        if not result:
            return result, error
        else:
            return True, ""

    def __w_data(self, package_index, package_data):
        """Write data

        :param package_index: data package index number
        :param package_data: will write data
        :return:
        """

        ack = WriteAckMsg()
        req = WriteReqMsg(WriteReqMsg.DATA_REQ, package_index, package_data)

        result, error = self.__basic_transfer(req, ack)
        if not result:
            return result, error
        else:
            return True, ""
