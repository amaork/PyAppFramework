# -*- coding: utf-8 -*-
import sys
import random
from PySide2.QtGui import QColor
from PySide2.QtWidgets import QPushButton, QHBoxLayout, QGridLayout, QApplication, QColorDialog

from ..gui.widget import BasicWidget
from ..gui.container import ComponentManager
from ..dashboard.status import DashboardStatusIcon


class DemoDashboardStatus(BasicWidget):
    def __init__(self, parent=None):
        super(DemoDashboardStatus, self).__init__(parent)

    def _initUi(self):
        layout = QHBoxLayout()

        self.ui_on = QPushButton("打开")
        self.ui_off = QPushButton("关闭")
        self.ui_bg_color = QPushButton("前景色")
        self.ui_fg_color = QPushButton("背景色")

        self.ui_voltage = DashboardStatusIcon(self, "Voltage(V)", ("---",), self.tr("电压"))
        self.ui_current = DashboardStatusIcon(self, "Current(A)", ("---",), self.tr("电流"))
        self.ui_switch = DashboardStatusIcon(self, "SWITCH", ("NONE", "ON", "OFF"), self.tr("开关状态"))

        btn_layout = QGridLayout()
        btn_layout.addWidget(self.ui_on, 0, 0)
        btn_layout.addWidget(self.ui_off, 1, 0)
        btn_layout.addWidget(self.ui_bg_color, 0, 1)
        btn_layout.addWidget(self.ui_fg_color, 1, 1)

        for item in (self.ui_switch, self.ui_voltage, self.ui_current):
            layout.addWidget(item)

        layout.addLayout(btn_layout)
        self.setLayout(layout)
        layout.setStretchFactor(self.ui_switch, 2)
        layout.setStretchFactor(self.ui_current, 2)
        layout.setStretchFactor(self.ui_voltage, 2)
        self.setWindowTitle(self.tr("开关状态演示"))
        self.ui_manager = ComponentManager(layout)

    def _initSignalAndSlots(self):
        self.ui_on.clicked.connect(self.slotOn)
        self.ui_off.clicked.connect(self.slotOff)
        self.ui_bg_color.clicked.connect(self.slotSelectBackgroundColor)
        self.ui_fg_color.clicked.connect(self.slotSelectForegroundColor)

    def _initThreadAndTimer(self):
        self.startTimer(300)

    def slotOn(self):
        self.ui_switch.changeStatus("ON")

    def slotOff(self):
        self.ui_current.reset()
        self.ui_voltage.reset()
        self.ui_switch.changeStatus("OFF")

    def slotSelectBackgroundColor(self):
        color = QColorDialog.getColor(DashboardStatusIcon.DEF_BG_COLOR, self, "请选择背景色")
        if isinstance(color, QColor):
            for item in self.ui_manager.getByType(DashboardStatusIcon):
                item.bg_color = color

    def slotSelectForegroundColor(self):
        color = QColorDialog.getColor(DashboardStatusIcon.DEF_FG_COLOR, self, "请选择前景色")
        if isinstance(color, QColor):
            for item in self.ui_manager.getByType(DashboardStatusIcon):
                item.fg_color = color

    def timerEvent(self, ev):
        if not self.ui_switch.status() == "ON":
            return

        voltage = random.randint(0, 100) + random.choice(range(0, 11)) / 10.0 + random.choice(range(0, 11)) / 100.0
        current = random.randint(0, 100) + random.choice(range(0, 11)) / 10.0 + random.choice(range(0, 11)) / 100.0

        self.ui_current.changeStatus("{0:.02f}".format(current))
        self.ui_voltage.changeStatus("{0:.02f}".format(voltage))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    widget = DemoDashboardStatus()
    widget.show()
    sys.exit(app.exec_())
