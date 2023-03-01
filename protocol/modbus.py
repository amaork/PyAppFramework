# -*- coding: utf-8 -*-
import time
import struct
import typing
import threading
import collections

from .crc16 import crc16
from ..core.datatype import DynamicObject, CustomEvent
from .transmit import UARTTransmit, TransmitWarning, TransmitException

__all__ = ['FuncCode', 'ExceptionCode', 'Region', 'ModbusServer',
           'helper_data2bits', 'helper_bits2data', 'helper_get_bytesize']

FuncCode = collections.namedtuple(
    'FuncCode', 'ReadCoils WriteSingleCoil WriteMultipleCoils ReadRegs WriteSingleReg WriteMultipleRegs'
)(*(1, 5, 15, 3, 6, 16))

ExceptionCode = collections.namedtuple(
    'ExceptionCode', 'IllegalFunction IllegalDataAddress IllegalDataValue SlaveDeviceFailure SlaveDeviceBusy'
)(*(0x1, 0x2, 0x3, 0x4, 0x6))


class Region(DynamicObject):
    Type = collections.namedtuple('Type', 'Coil Register')(*range(2))
    CoilState = collections.namedtuple('CoilState', 'ON OFF')(*(0xff00, 0x0000))

    _properties = {'type', 'list', 'setter', 'getter', 'callback'}
    _check = {
        'setter': callable,
        'getter': callable,
        'callback': callable,
        'type': lambda x: x in Region.Type,
        'list': lambda x: isinstance(x, dict) and all([isinstance(k, int) for k in x])
    }

    def __init__(self, **kwargs):
        kwargs.setdefault('setter', lambda x: x)
        kwargs.setdefault('getter', lambda x: x)
        kwargs.setdefault('callback', lambda *x: x)
        super().__init__(**kwargs)
        self.__lock = threading.Lock()

    def __repr__(self):
        type_name = {v: k for k, v in self.Type._asdict().items()}.get(self.type)
        with self.__lock:
            return f'{type_name}: {self.list}'

    def contains(self, address: int) -> bool:
        return address in self.list

    def get(self, address: int) -> int:
        if not self.contains(address):
            raise ValueError(f'invalid address: {address}')

        with self.__lock:
            return self.getter(self.list[address])

    def set(self, address: int, value: int) -> bool:
        if not self.contains(address):
            return False

        with self.__lock:
            data = self.setter(value)
            self.list[address] = data
            # If it's coil convert state to true/false
            data = self.is_on(data) if self.type == self.Type.Coil else data

        callable(self.callback) and self.callback(self, address, data)
        return True

    @classmethod
    def create_regs(cls, **kwargs):
        kwargs.setdefault('type', cls.Type.Register)
        return Region(**kwargs)

    @classmethod
    def create_coils(cls, **kwargs):
        kwargs.setdefault('type', cls.Type.Coil)
        return Region(**kwargs)

    @staticmethod
    def is_on(state: int) -> bool:
        return state == Region.CoilState.ON

    @staticmethod
    def is_off(state: int) -> bool:
        return state == Region.CoilState.OFF


class ModbusEvent(CustomEvent):
    Type = collections.namedtuple('Type', 'DataChanged Logging')(*range(2))


class ModbusException(Exception):
    def __init__(self, dev_id: int, fc: int, code: int):
        super().__init__()
        self.fc = fc
        self.code = code
        self.dev_id = dev_id

    def bytes(self) -> bytes:
        return struct.pack('>BBB', self.dev_id, self.fc + 0x80, self.code)


def helper_get_bytesize(count: int) -> int:
    return count // 8 + (1 if count % 8 else 0)


def helper_data2bits(data: typing.Sequence[int], msb_first: bool = True) -> bytes:
    array = bytearray(helper_get_bytesize(len(data)))

    for index, value in enumerate(data):
        byte_offset = index // 8
        bit_offset = 7 - index % 8 if msb_first else index % 8
        array[byte_offset] |= (value & 0x1) << bit_offset

    return bytes(array)


def helper_bits2data(bits: bytes, msb_first: bool = True) -> typing.Sequence[int]:
    data = list()
    for value in bits:
        for index in range(8):
            offset = 7 - index if msb_first else index
            data.append(True if (value & (1 << offset)) else False)

    return data


class ModbusServer:
    def __init__(self, dev_id: int, callback: typing.Callable[[Region, int, typing.Any], None], verbose: bool = False):
        self.dev_id = dev_id
        self.regions = list()
        self.verbose = verbose
        self.callback = callback
        self.transmit = UARTTransmit(ending_check=lambda x: crc16(x) == 0, checksum=crc16)

        self.fc_handle = {
            FuncCode.ReadRegs: self.handleReadRegs,
            FuncCode.WriteSingleReg: self.handleWriteSingleReg,
            FuncCode.WriteMultipleRegs: self.handleWriteMultipleRegs,

            FuncCode.ReadCoils: self.handleReadCoils,
            FuncCode.WriteSingleCoil: self.handleWriteSingleCoil,
            FuncCode.WriteMultipleCoils: self.handleWriteMultipleCoils,
        }

        self.th = threading.Thread(target=self.threadHandle, daemon=True)
        self.th.start()

    def __del__(self):
        self.transmit.disconnect()
        self.th.join()

    def start(self, port: str, baudrate: int, timeout: float) -> bool:
        if self.transmit.connected:
            return True

        return self.transmit.connect((port, baudrate), timeout)

    def find_reg(self, address: int) -> typing.Optional[Region]:
        return self.find_region(Region.Type.Register, address)

    def find_coil(self, address: int) -> typing.Optional[Region]:
        return self.find_region(Region.Type.Coil, address)

    def find_region(self, t: int, address: int) -> typing.Optional[Region]:
        for region in self.regions:
            if region.type == t and region.contains(address):
                return region

        return None

    def register_region(self, regions: typing.Sequence[Region]):
        for region in regions:
            region.callback = self.callback
            self.regions.append(region)

    def handleReadRegs(self, payload: bytes) -> bytes:
        addr, count = struct.unpack('>2H', payload)
        data = [self.find_reg(addr + idx).get(addr) for idx in range(count)]
        return bytes([count * 2]) + struct.pack(f'>{count}H', *tuple(data))

    def handleWriteSingleReg(self, payload: bytes) -> bytes:
        addr, value = struct.unpack('>2H', payload)
        self.find_reg(addr).set(addr, value)
        return payload

    def handleWriteMultipleRegs(self, payload: bytes) -> bytes:
        header_fmt = '>2HB'
        header_len = struct.calcsize(header_fmt)

        # Get address, quantity of regs and byte count
        start_addr, count, size = struct.unpack(header_fmt, payload[:header_len])
        if size != len(payload[header_len:]):
            raise IndexError('byte size mismatch')

        # Get data and process
        data = struct.unpack(f'>{count}H', payload[header_len: header_len + size])
        for offset in range(count):
            address = start_addr + offset
            self.find_reg(address).set(address, data[offset])

        return struct.pack('>HH', start_addr, count)

    def handleReadCoils(self, payload: bytes) -> bytes:
        header_fmt = '>2H'
        header_len = struct.calcsize(header_fmt)
        start_addr, count = struct.unpack(header_fmt, payload[:header_len])
        data = [self.find_coil(start_addr + offset).get(start_addr + offset) for offset in range(count)]
        return helper_data2bits(data)

    def handleWriteSingleCoil(self, payload: bytes) -> bytes:
        addr, state = struct.unpack('>HH', payload)
        self.find_coil(addr).set(addr, state)
        return payload

    def handleWriteMultipleCoils(self, payload: bytes) -> bytes:
        header_fmt = '>2HB'
        header_len = struct.calcsize(header_fmt)

        # Get address, quantity of coils and byte count
        start_addr, count, size = struct.unpack(header_fmt, payload[:header_len])
        if size != helper_get_bytesize(count):
            raise IndexError('byte size mismatch')

        # Get coils and convert to int
        data = helper_bits2data(payload[header_len: header_len + size])

        for offset in range(count):
            address = start_addr + offset
            self.find_coil(address).set(address, Region.CoilState.ON if data[offset] else Region.CoilState.OFF)

        return struct.pack('>HH', start_addr, count)

    def threadHandle(self):
        while True:
            if not self.transmit.connected:
                time.sleep(0.1)
                continue

            try:
                request = self.transmit.rx(256)
                dev_id, func_code, *payload = request

                if dev_id != self.dev_id:
                    continue

                if func_code not in FuncCode:
                    raise ModbusException(dev_id, func_code, ExceptionCode.IllegalFunction)

                handle = self.fc_handle.get(func_code)
                if not callable(handle):
                    raise ModbusException(dev_id, func_code, ExceptionCode.SlaveDeviceFailure)

                try:
                    response = bytes([self.dev_id, func_code]) + handle(bytes(payload))
                except (struct.error, IndexError):
                    raise ModbusException(dev_id, func_code, ExceptionCode.IllegalDataValue)
                except AttributeError:
                    raise ModbusException(dev_id, func_code, ExceptionCode.IllegalDataAddress)

                self.transmit.tx(response)

                if self.verbose:
                    print(f'{request.hex()} ==> {response.hex()}')

            except (IndexError, ValueError):
                continue
            except TransmitException:
                break
            except TransmitWarning:
                continue
            except ModbusException as err:
                self.transmit.tx(err.bytes())
