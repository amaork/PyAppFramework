# -*- coding: utf-8 -*-
from __future__ import print_function
import ctypes
import serial
from threading import Thread
from raspi_io import Serial as WebsocketSerial, RaspiSocketTError

from .crc16 import crc16
from ..core.datatype import BasicTypeLE


__all__ = ['SerialPort', 'SerialTransactionProtocol', 'ReadAckMsg', 'SerialPortProtocolSimulate',
           'SerialTransactionProtocolReadSimulate']


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


class SerialTransactionProtocol(object):
    PAYLOAD_SIZE = 128

    def __init__(self, send, recv):
        """"Init a serial port transfer object

        :param send: serial port send function
        :param recv: serial port receive function
        :return:
        """
        assert hasattr(send, "__call__"), "{} send function is not callable".format(self.__class__.__name__)
        assert hasattr(recv, "__call__"), "{} recv function is not callable".format(self.__class__.__name__)
        self.__send, self.__recv = send, recv

    @staticmethod
    def calc_package_size(data):
        return len(data) / SerialTransactionProtocol.PAYLOAD_SIZE

    @staticmethod
    def get_package_data(idx, data):
        size = SerialTransactionProtocol.calc_package_size(data)
        if not 0 <= idx < size:
            return ""

        return data[idx * SerialTransactionProtocol.PAYLOAD_SIZE: (idx + 1) * SerialTransactionProtocol.PAYLOAD_SIZE]

    def read(self, callback=None):
        # Send r_init request
        result, data = self.__r_init()
        if not result:
            return result, data

        # Get package size and global data
        package_size, global_data = data[0], data[1]

        # Read package data
        package_data = ""
        for package_index in range(package_size):
            result, data = self.__r_data(package_index)
            if not result:
                return False, data
            else:
                package_data += data

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

        # Write all data
        for package_index in range(package_size):
            result, data = self.__w_data(package_index, self.get_package_data(package_index, package_data))
            if not result:
                return False, data

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
        result, error = self.__send(req.cdata())
        if not result:
            return result, error

        # Receive ack
        result, data = self.__recv(ctypes.sizeof(ack))
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
        return (True, (int(data.args), data.get_data_payload())) if isinstance(data, ReadAckMsg) else (False, data)

    def __r_data(self, package_index):
        """Read package_index specified package index

        :param package_index:  will read package data
        :return: result, package_data or error
        """
        req = ReadReqMsg(ReadReqMsg.DATA_REQ, package_index)

        # Send read init request and get ack
        result, data = self.__basic_transfer(req)
        return (True, data.get_data_payload()) if isinstance(data, ReadAckMsg) else (False, data)

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
                self.__port = WebsocketSerial(host=port[0], port=port[1], baudrate=baudrate, timeout=timeout)
            except ValueError:
                raise serial.SerialException("Open websocket serial port:{} error".format(port))
            except RaspiSocketTError:
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

    def send(self, data):
        """Basic send data

        :param data: will send data
        :return: result, error
        """

        try:

            if len(data) == 0:
                raise RuntimeError("Sending Data length error")

            if not self.__port.isOpen():
                raise RuntimeError("Serial port: {0:x} is not opened".format(self.__port.port))

            if self.__port.write(data) != len(data):
                raise RuntimeError("Send data error: data sent is not completed")

            return True, ""

        except serial.SerialException as e:
            return False, "Send data exception: {0:s}".format(e)
        except RuntimeError as error:
            return False, error

    def recv(self, size):
        """Basic receive data

        :param size: receive data size
        :return: result/receive data
        """

        data = ""

        try:

            if size == 0:
                raise RuntimeError("Receive data length error")

            if not self.__port.isOpen():
                raise RuntimeError("Serial port: {0:x} is not opened".format(self.__port.port))

            while len(data) != size:
                tmp = self.__port.read(size - len(data))
                if len(tmp) == 0:
                    raise RuntimeError("Receive data timeout!")

                data += tmp

            return True, data

        except serial.SerialException as e:
            return False, "Receive data exception: {0:s}".format(e)
        except RuntimeError as error:
            return False, error


class SerialPortProtocolSimulate(object):
    def __init__(self, send, recv, error_handle=print):
        assert hasattr(send, "__call__"), "{} send function is not callable".format(self.__class__.__name__)
        assert hasattr(recv, "__call__"), "{} recv function is not callable".format(self.__class__.__name__)
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
                result, data = self.__recv(self._get_request_size())
                if not result:
                    self.__error_handle("Receive request error:{0:s}".format(data))
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


class SerialTransactionProtocolReadSimulate(SerialPortProtocolSimulate):
    def __init__(self, send, recv, data, error_handle=print):
        super(SerialTransactionProtocolReadSimulate, self).__init__(send, recv, error_handle)
        self.__global_data, self.__config_data = data
        self.__total_package = SerialTransactionProtocol.calc_package_size(self.__config_data)

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
        data = SerialTransactionProtocol.get_package_data(req.args, self.__config_data)
        return ReadAckMsg.create(req.req, req.args, data).cdata()
