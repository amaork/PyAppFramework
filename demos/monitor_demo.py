# -*- coding: utf-8 -*-
import sys
import random
from PySide.QtGui import *
from PySide.QtCore import *
from ..dashboard.monitor import *
from ..gui.widget import BasicWidget
from ..gui.container import ComponentManager


class DemoWidget(BasicWidget):
    def __init__(self, parent=None):
        super(DemoWidget, self).__init__(parent)

    def _initUi(self):
        layout = QHBoxLayout()
        self.ui_temp1 = TemperatureMonitor("温度1", 100, parent=self)
        self.ui_temp2 = TemperatureMonitor("温度2", 100, unit_id=1, parent=self)
        self.ui_pressure1 = PressureMonitor("压力1", parent=self)
        self.ui_pressure2 = PressureMonitor("压力2", unit_id=0, parent=self)
        self.ui_pressure3 = PressureMonitor("压力3", unit_id=1, parent=self)

        for element in (self.ui_temp1, self.ui_temp2, self.ui_pressure1, self.ui_pressure2, self.ui_pressure3):
            layout.addWidget(element)

        self.ui_manager = ComponentManager(layout)

        # for pressure in self.ui_manager.getByType(PressureMonitor):
        #     pressure.setSV(1000)

        self.setLayout(layout)
        self.setWindowTitle("温度/压力监控")

    # def _initStyle(self):
    #     self.setMinimumSize(QSize(900, 300))

    def _initSignalAndSlots(self):
        self.startTimer(500)

    def timerEvent(self, ev):
        temperature = random.randint(0, self.ui_temp1.getSV())
        temperature += random.choice(range(0, 11)) / 10.0 + random.choice(range(0, 11)) / 100.0
        pressure = random.randint(0, 600) + random.choice(range(0, 11)) / 10.0 + random.choice(range(0, 11)) / 100.0

        for pressure_monitor in self.ui_manager.getByType(PressureMonitor):
            pressure_monitor.setRV(pressure)

        for temperature_monitor in self.ui_manager.getByType(TemperatureMonitor):
            temperature_monitor.setRV(temperature)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    QTextCodec.setCodecForTr(QTextCodec.codecForName("UTF-8"))
    widget = DemoWidget()
    widget.show()
    sys.exit(app.exec_())
