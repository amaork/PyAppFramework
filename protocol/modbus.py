# -*- coding: utf-8 -*-
import time
import ping3
import queue
import struct
import typing
import threading
import collections
import pyModbusTCP.client as modbus_client

from .crc16 import crc16
from ..core.timer import Task, Tasklet
from .template import CommunicationEvent, CommunicationSection
from ..core.threading import ThreadSafeBool, ThreadLockAndDataWrap
from .transmit import UARTTransmit, TransmitWarning, TransmitException
from ..core.datatype import DynamicObject, CustomEvent, enum_property, str2number
__all__ = ['FuncCode', 'ExceptionCode', 'DataTypeFuncCode',
           'Region', 'Address', 'Table',
           'WriteRequest', 'ReadRequest', 'ReadResponse',
           'WatchEventRequest', 'WatchEventResponse',
           'DataType', 'DataFormat', 'DataPresent', 'DataConvert',
           'ModbusServer', 'ModbusTCPClientEvent', 'ModbusTCPClient',
           'helper_data2bits', 'helper_bits2data', 'helper_get_bytesize', 'helper_get_func_code']

FuncCode = collections.namedtuple(
    'FuncCode', 'ReadCoils WriteSingleCoil WriteMultipleCoils ReadRegs WriteSingleReg WriteMultipleRegs'
)(*(1, 5, 15, 3, 6, 16))


ExceptionCode = collections.namedtuple(
    'ExceptionCode', 'IllegalFunction IllegalDataAddress IllegalDataValue SlaveDeviceFailure SlaveDeviceBusy'
)(*(0x1, 0x2, 0x3, 0x4, 0x6))

# Bit means register sub bit
DataType = collections.namedtuple('DataType', 'Coil Register Bit')(*'coil register bit'.split())

DataFormat = collections.namedtuple('DataFormat', 'float uint16 uint32 bit')(*'float uint16 uint32 bit'.split())

DataPresent = collections.namedtuple('DataPresent', 'auto btn checkbox')(*'auto btn checkbox'.split())

# Read, write, multiple-write
DataTypeFuncCode = collections.namedtuple('DataTypeFuncCode', 'rd wr mwr')

# Write request: data type(register/coil/bit), address, write data
WriteRequest = collections.namedtuple('WriteRequest', 'type address data')

# Read request: start address, read count
ReadRequest = collections.namedtuple('ReadRequest', 'start count event')

# Read response: read request, response data
ReadResponse = collections.namedtuple('ReadResponse', 'request data')

# Read data watch: name, type, read request
WatchEventResponse = collections.namedtuple('ReadDataWatchResponse', 'name type address data event')


class Table(DynamicObject):
    _properties = {'name', 'type', 'endian', 'auto_flush', 'base_reg', 'address_list'}

    def __init__(self, **kwargs):
        kwargs.setdefault('endian', '>>')
        kwargs.setdefault('auto_flush', 0)
        kwargs.setdefault('base_reg', None)
        kwargs.setdefault('address_list', collections.OrderedDict())
        super().__init__(**kwargs)


class Address(DynamicObject):
    _properties = {'ma', 'ro', 'format', 'present', 'name', 'annotate'}

    @staticmethod
    def pack_bit_address(base_reg: int, bit: int) -> str:
        return f'{base_reg}/{bit}' if bit < 16 else f'invalid bit: {bit}'

    @staticmethod
    def unpack_bit_address(bit_address: str) -> typing.Tuple[int, int]:
        temp = bit_address.split('/')
        return str2number(temp[0]), str2number(temp[1])


class Region(DynamicObject):
    CoilState = collections.namedtuple('CoilState', 'ON OFF')(*(0xff00, 0x0000))

    _properties = {'type', 'list', 'setter', 'getter', 'callback'}
    _check = {
        'setter': callable,
        'getter': callable,
        'callback': callable,
        'type': lambda x: x in DataType,
        'list': lambda x: isinstance(x, dict) and all([isinstance(k, int) for k in x])
    }

    def __init__(self, **kwargs):
        kwargs.setdefault('setter', lambda x: x)
        kwargs.setdefault('getter', lambda x: x)
        kwargs.setdefault('callback', lambda *x: x)
        super().__init__(**kwargs)
        self.__lock = threading.Lock()

    def __repr__(self):
        type_name = {v: k for k, v in DataType._asdict().items()}.get(self.type)
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
            data = self.is_on(data) if self.type == DataType.Coil else data

        callable(self.callback) and self.callback(self, address, data)
        return True

    @classmethod
    def create_regs(cls, **kwargs):
        kwargs.setdefault('type', DataType.Register)
        return Region(**kwargs)

    @classmethod
    def create_coils(cls, **kwargs):
        kwargs.setdefault('type', DataType.Coil)
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


def helper_get_func_code(t: DataType) -> DataTypeFuncCode:
    return {
        DataType.Coil: DataTypeFuncCode(
            rd=FuncCode.ReadCoils, wr=FuncCode.WriteSingleCoil, mwr=FuncCode.WriteMultipleCoils
        ),

        DataType.Register: DataTypeFuncCode(
            rd=FuncCode.ReadRegs, wr=FuncCode.WriteSingleReg, mwr=FuncCode.WriteMultipleRegs
        ),

        DataType.Bit: DataTypeFuncCode(
            rd=FuncCode.ReadRegs, wr=FuncCode.WriteSingleReg, mwr=FuncCode.WriteMultipleRegs
        )
    }.get(t)


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


class DataConvert:
    def __init__(self, endian: str):
        if not isinstance(endian, str):
            raise TypeError(f"endian required 'str' not {endian.__class__.__name__!r}")

        if len(endian) != 2:
            raise ValueError(f"endian length be 2")

        if any(x not in '><!@=' for x in endian):
            raise ValueError(f"invalid endian format: {endian!r}")

        self.__endian = endian

    def get_plc_float_format(self) -> typing.Tuple[str, str]:
        return self.__endian[0], self.__endian[1]

    def remap_int2list(self, i: int) -> typing.Tuple[int, ...]:
        pf, uf = self.get_plc_float_format()
        return struct.unpack(f'{uf}2H', struct.pack(f'{pf}I', i))

    def remap_list2int(self, i: typing.Tuple[int, ...]) -> int:
        pf, uf = self.get_plc_float_format()
        return struct.unpack(f'{pf}I', struct.pack(f'{uf}2H', *i))[0]

    def remap_float2list(self, f: float) -> typing.Tuple[int, ...]:
        pf, uf = self.get_plc_float_format()
        return struct.unpack(f'{uf}2H', struct.pack(f'{pf}f', f))

    def remap_list2float(self, i: typing.Tuple[int, ...]) -> float:
        pf, uf = self.get_plc_float_format()
        return struct.unpack(f'{pf}f', struct.pack(f'{uf}2H', *i))[0]

    def python2plc(self, data: typing.Union[int, float], fmt: str) -> typing.Union[int, typing.Tuple[int, ...]]:
        return {
            DataFormat.uint32: self.remap_int2list,
            DataFormat.float: self.remap_float2list
        }.get(fmt, lambda x: x)(data)

    def plc2python(self, data: typing.Tuple[int, ...], fmt: str) -> typing.Union[float, int]:
        return {
            DataFormat.uint32: self.remap_list2int,
            DataFormat.float: self.remap_list2float,
        }.get(fmt, lambda x: x[0])(data)

    @classmethod
    def get_format_size(cls, fmt: DataFormat) -> int:
        return {
            DataFormat.bit: 1,
            DataFormat.float: 2,
            DataFormat.uint16: 1,
            DataFormat.uint32: 2,
        }.get(fmt, 1)

    @classmethod
    def merge_read_request(cls, address_list: typing.Sequence[DynamicObject]) -> typing.List[ReadRequest]:
        start = 0
        count = 0
        latest = 0
        request_list = list()
        for address in address_list:
            if not count:
                start = address.ma
                count = cls.get_format_size(address.format)
            elif latest + 1 == address.ma:
                count += cls.get_format_size(address.format)
            else:
                request_list.append(ReadRequest(start=start, count=count, event=None))
                start = address.ma
                count = cls.get_format_size(address.format)

            latest = address.ma

        request_list.append(ReadRequest(start=start, count=count, event=None))
        return request_list


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
        return self.find_region(DataType.Register, address)

    def find_coil(self, address: int) -> typing.Optional[Region]:
        return self.find_region(DataType.Coil, address)

    def find_region(self, t: DataType, address: int) -> typing.Optional[Region]:
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


class WatchEventRequest(DynamicObject):
    _properties = {'name', 'type', 'rd'}
    _fc_filter = {DataType.Coil: FuncCode.ReadCoils, DataType.Register: FuncCode.ReadRegs}

    def __hash__(self):
        return sum(self.read_request_to_set(self.rd))

    @staticmethod
    def read_request_to_set(req: ReadRequest) -> typing.Set[int]:
        return {x for x in range(req.start, req.start + req.count)}

    def is_matched(self, fc: FuncCode, request: ReadRequest) -> typing.Tuple[int, int]:
        if self._fc_filter.get(self.type) != fc:
            return -1, 0

        needle = self.read_request_to_set(self.rd)
        haystack = self.read_request_to_set(request)
        found = haystack.intersection(needle)
        if not found:
            return -1, 0

        count = len(found)
        first = found.pop()
        return list(haystack).index(first), count

    def gen_response(self, address: int, data: typing.Sequence[int]) -> WatchEventResponse:
        return WatchEventResponse(name=self.name, type=self.type, address=address, data=data, event=self.rd.event)


class ModbusTCPClientEvent(CommunicationEvent):
    ExtendType = collections.namedtuple('ExtendType', 'WatchEventOccurred')(*'watch_event_occurred'.split())
    type = enum_property('type', CommunicationEvent.Type + ExtendType)

    @classmethod
    def watch_event_occurred(cls, response: WatchEventResponse):
        return cls(cls.ExtendType.WatchEventOccurred, data=response)


class ModbusTCPClient:
    def __init__(self, host: str, event_callback: typing.Callable[[ModbusTCPClientEvent], None], **kwargs):
        self.queue = queue.Queue()
        self.event_callback = event_callback
        self.is_alive = ThreadSafeBool(False)
        self.tasklet = Tasklet(schedule_interval=1)
        self.rd_watch_list = ThreadLockAndDataWrap(set())
        self.modbus_client = modbus_client.ModbusClient(host=host, **kwargs)
        threading.Thread(target=self.thread_comm_with_plc, daemon=True).start()
        self.tasklet.add_task(Task(self.task_check_connection, timeout=1.0, periodic=True))

    def send_request(self, *args):
        if not self.is_alive:
            return

        self.queue.put(args)
        name, fc, requests = args
        if fc not in (FuncCode.ReadCoils, FuncCode.ReadRegs):
            self.event_callback(ModbusTCPClientEvent.debug(f'TX:[{name}] >>> {requests}'))

    def request_watch(self, watch: WatchEventRequest):
        self.rd_watch_list.data.add(watch)

    def task_check_connection(self):
        host = self.modbus_client.host
        self.is_alive.assign(ping3.ping(host) is not None)
        if self.is_alive and self.modbus_client.open():
            self.event_callback(ModbusTCPClientEvent.connected(
                (host, self.modbus_client.port), self.modbus_client.timeout)
            )
        else:
            self.event_callback(ModbusTCPClientEvent.disconnected('not alive or not opened'))

    def thread_comm_with_plc(self):
        functions = {
            FuncCode.ReadCoils: self.modbus_client.read_coils,
            FuncCode.WriteSingleCoil: self.modbus_client.write_single_coil,
            FuncCode.WriteMultipleCoils: self.modbus_client.write_multiple_coils,

            FuncCode.ReadRegs: self.modbus_client.read_holding_registers,
            FuncCode.WriteSingleReg: self.modbus_client.write_single_register,
            FuncCode.WriteMultipleRegs: self.modbus_client.write_multiple_registers
        }

        while True:
            if not self.is_alive or not self.modbus_client.is_open:
                time.sleep(0.1)
                continue

            name, fc, request = self.queue.get()
            func = functions.get(fc)
            if not callable(func):
                self.event_callback(ModbusTCPClientEvent.error('invalid function code'))
                continue

            # print(name, fc, request)
            if isinstance(request, WriteRequest):
                func(request.address, request.data)
            elif isinstance(request, list):
                for req in request:
                    data = func(req.start, req.count)
                    if data is None:
                        continue

                    for watch in self.rd_watch_list.data:
                        index, length = watch.is_matched(fc, req)
                        if 0 <= index < len(data) and length:
                            response = watch.gen_response(req.start + index, data[index: index + length])
                            self.event_callback(ModbusTCPClientEvent.watch_event_occurred(response))

                    section = CommunicationSection(req, data)
                    self.event_callback(ModbusTCPClientEvent.section_end(name, section))
