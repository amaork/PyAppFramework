# -*- coding: utf-8 -*-
import os
import sys
import time
import struct
import typing

import serial
import selectors
import collections
from threading import Thread
from .serialport import SerialPort
from ..core.timer import Task, Tasklet
from ..misc.settings import UiLogMessage
from ..core.datatype import DynamicObject
from ..core.threading import ThreadSafeBool
from ..misc.debug import JsonSettingsWithDebugCode, LoggerWrap
from .transmit import TransmitException, TransmitWarning, TCPServerTransmitHandle, TCPClientTransmit, TCPSocketTransmit
__all__ = ['SerialPortSwitch', 'SerialPortSwitchSettings']


class SerialPortSwitchSettings(JsonSettingsWithDebugCode):
    Rule = collections.namedtuple('Rule', 'rx_mask tx_dest')
    _default_path = os.path.join('config', 'serial_port_switch.json')
    _properties = {'up_stream', 'down_stream', 'comm_params', 'rule', 'msg_interval'}

    def get_rule(self, name: str) -> Rule:
        try:
            return self.Rule(**self.rule.get(name))
        except TypeError:
            return self.Rule(rx_mask=0x1, tx_dest=0)

    @classmethod
    def default(cls) -> DynamicObject:
        return SerialPortSwitchSettings(
            msg_interval=0.05,
            up_stream='COM3', down_stream='COM6, COM9',
            rule=dict(
                COM3=dict(rx_mask=0x2, tx_dest=0x6),
                COM6=dict(rx_mask=0x1, tx_dest=0x1),
                COM9=dict(rx_mask=0x1, tx_dest=0x1)
            ),
            comm_params=dict(baudrate=115200, bytesize=8, parity='N', stopbits=1, timeout=0.1)
        )


class SerialPortSwitch:
    Port = 56789
    # src_port, dest_port, dest_serial, payload
    ProcessFunc = typing.Callable[[int, int, SerialPort, bytes], None]

    def __init__(self):
        self._rules = dict()
        self._cached_msg = bytes()
        self._previous_port = -1
        self._msg_interval = 0.05
        self._serial_list = list()
        self._client_list = list()
        self._exit = ThreadSafeBool(False)
        self._selector = selectors.DefaultSelector()
        self._tasklet = Tasklet(schedule_interval=0.01)
        self._log = LoggerWrap(f'{self.__class__.__name__}.log')
        self._server = TCPServerTransmitHandle(self.handle, length_fmt=TCPSocketTransmit.DefaultLengthFormat)

    def stop(self):
        self._exit.set()

    def start(self, port: int = Port) -> bool:
        settings = SerialPortSwitchSettings.get()
        self._server.start(('127.0.0.1', port))
        self._msg_interval = settings.msg_interval
        Thread(target=self.thread_switch, daemon=True).start()
        self._log.logging(UiLogMessage.genDefaultDebugMessage(f'{settings.dict}'))

        for index, name in enumerate(f'{settings.up_stream}, {settings.down_stream}'.split(',')):
            try:
                name = name.strip()
                ser = SerialPort(name, **settings.comm_params)
            except serial.SerialException as e:
                print(f'Open serial {name!r} error: {e}')
                return False
            else:
                self._serial_list.append(ser)
                self._rules[index] = settings.get_rule(name)
                Thread(target=self.thread_rx_serial, args=(ser, index), daemon=True).start()

        return True

    def handle(self, transmit: TCPSocketTransmit):
        self._client_list.append(transmit)
        port = struct.unpack('>L', transmit.rx(0))[0]
        self._selector.register(transmit.raw_socket, selectors.EVENT_READ, data=port)

    def get_port_name(self, port: int) -> str:
        return self._serial_list[port].raw_port.port

    def rule_process(self, src_port: int, payload: bytes, process: ProcessFunc):
        tx_mask = (1 << src_port)
        src_rule = self._rules.get(src_port)
        if not src_rule:
            return

        for dest_port, ser in enumerate(self._serial_list):
            dest_rule = self._rules.get(dest_port)
            if src_rule.tx_dest & (1 << dest_port):
                if dest_rule.rx_mask & tx_mask:
                    process(src_port, dest_port, ser, payload)

    def relay(self, client: TCPSocketTransmit, port: int):
        try:
            payload = client.rx(0)
        except TransmitWarning:
            return
        except (BrokenPipeError, ConnectionResetError, TransmitException) as e:
            print(client.raw_socket.getsockname(), f'{e}')
            payload = b''

        if payload:
            # Source changed, write cached to log
            if self._previous_port != port and self._cached_msg:
                self.task_write_log()

            self._previous_port = port
            self._cached_msg += payload
            # Match rule and process relay data
            self.rule_process(port, payload, lambda _s, d_, ser, data: ser.write(data))
            self._tasklet.add_task(Task(func=self.task_write_log, timeout=self._msg_interval))

    def thread_switch(self):
        while not self._exit:
            if not self._selector.get_map():
                time.sleep(0.01)
                continue

            for key, mask in self._selector.select():
                for client in self._client_list:
                    if client.raw_socket == key.fileobj:
                        self.relay(client, key.data)

    def task_write_log(self):
        if self._previous_port < 0 or not self._cached_msg:
            return

        self.rule_process(
            self._previous_port, self._cached_msg,
            lambda s, d, _, data: self._log.logging(UiLogMessage.genDefaultInfoMessage(
                f'{self.get_port_name(s)} ==> {self.get_port_name(d)}: {data.hex()}'
            ))
        )

        self._cached_msg = bytes()

    def thread_rx_serial(self, ser: SerialPort, index: int):
        client = TCPClientTransmit(TCPSocketTransmit.DefaultLengthFormat)

        try:
            client.connect(('127.0.0.1', self.Port))
        except TransmitException as e:
            print(f'Connect server error: {e}')
            sys.exit(-2)
        else:
            client.tx(struct.pack('>L', index))

        while not self._exit:
            try:
                client.tx(ser.read(1, timeout=0.001))
            except serial.SerialException:
                continue

        print(f'thread_rx_serial exit, index: {index}')
