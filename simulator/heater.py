# -*- coding: utf-8 -*-
import typing
import random
import collections
from PySide2 import QtCore

from ..core.timer import SwTimer
from ..protocol.modbus import Region, ModbusServer
__all__ = ['ModbusHeaterSimulator']


# IDAQ-8094 Modbus Heater
class ModbusHeaterSimulator(QtCore.QObject):
    signalRVChanged = QtCore.Signal(int, float)
    signalSVChanged = QtCore.Signal(int, float)
    Address = collections.namedtuple('Address', 'GetTemp SetTemp SubCtrl MainCtrl')(*(0x0, 0x40, 0x60, 0x30))

    def __init__(self, dev_id: int = 0x1, max_channel: int = 2, env_temp: float = 20.0, sim_step_factor: int = 10):
        super().__init__()
        self.dev_id = dev_id
        self.env_temp = env_temp * 10
        self.max_channel = max_channel
        self.sim_step_factor = sim_step_factor

        self.rv = Region.create_regs(
            setter=lambda x: x / 10, getter=lambda x: int(x * 10),
            list={self.Address.GetTemp + ch: 0.0 for ch in range(self.max_channel)},
        )

        self.sv = Region.create_regs(
            setter=lambda x: x / 10, getter=lambda x: int(x * 10),
            list={self.Address.SetTemp + ch: 0.0 for ch in range(self.max_channel)}
        )

        self.sub_ctrl = Region.create_coils(
            list={self.Address.SubCtrl + ch: False for ch in range(self.max_channel)}
        )

        self.main_ctrl = Region.create_coils(list={self.Address.MainCtrl: False})

        self.modbus = ModbusServer(dev_id=0x1, callback=self.callbackRegionWrite)
        self.modbus.register_region([self.sv, self.rv, self.sub_ctrl, self.main_ctrl])
        self.timer = SwTimer(0.3, callback=self.timerTempSimulate, auto_start=True)

    def isChannelEnabled(self, ch: int) -> bool:
        if not 0 <= ch < self.max_channel:
            return False

        return self.main_ctrl.get(self.Address.MainCtrl) and self.sub_ctrl.get(self.Address.SubCtrl + ch)

    def timerTempSimulate(self):
        for ch in range(self.max_channel):
            rv = self.rv.get(self.Address.GetTemp + ch)
            sv = self.sv.get(self.Address.SetTemp + ch)

            if not sv:
                continue

            v = random.randint(0, 100) / self.sim_step_factor
            if self.isChannelEnabled(ch):
                # Heating up to set temperature
                if rv <= sv:
                    rv += v
                else:
                    rv -= v
            else:
                # Cooling down to env temperature
                if rv >= self.env_temp:
                    rv -= v
                else:
                    rv += v

            self.rv.set(self.Address.GetTemp + ch, rv)

    def callbackRegionWrite(self, region: Region, address: int, data: typing.Any):
        if region == self.sv:
            self.signalSVChanged.emit(address - self.Address.SetTemp, data)
        elif region == self.rv:
            self.signalRVChanged.emit(address - self.Address.GetTemp, data)
