# -*- coding: utf-8 -*-
import sys
import math
from PySide.QtGui import *
from PySide.QtCore import *
from ..gui.widget import BasicWidget
from ..gui.container import ComponentManager
from ..dashboard.input import VirtualNumberInput


class DemoDashboardInput(BasicWidget):
    def __init__(self, parent=None):
        super(DemoDashboardInput, self).__init__(parent)

    def _initUi(self):
        layout = QGridLayout()
        self.ui_int_input = VirtualNumberInput(0, -100, 100, 0, self)
        self.ui_double_input = VirtualNumberInput(0.0, -100.0, 100.0, 2, self)

        self.ui_int_min = QSpinBox(self)
        self.ui_int_max = QSpinBox(self)
        self.ui_double_decimals = QSpinBox(self)
        self.ui_double_min = QDoubleSpinBox(self)
        self.ui_double_max = QDoubleSpinBox(self)
        self.ui_theme_color = QPushButton("键盘主题色")

        layout.addWidget(QLabel("Integer"), 0, 0)
        layout.addWidget(self.ui_int_input, 0, 1)
        layout.addWidget(QLabel("Min"), 0, 2)
        layout.addWidget(self.ui_int_min, 0, 3)
        layout.addWidget(QLabel("Max"), 0, 4)
        layout.addWidget(self.ui_int_max, 0, 5)
        layout.addWidget(QLabel("Theme"), 0, 6)
        layout.addWidget(self.ui_theme_color, 0, 7)

        layout.addWidget(QLabel("Double"), 1, 0)
        layout.addWidget(self.ui_double_input, 1, 1)
        layout.addWidget(QLabel("Min"), 1, 2)
        layout.addWidget(self.ui_double_min, 1, 3)
        layout.addWidget(QLabel("Max"), 1, 4)
        layout.addWidget(self.ui_double_max, 1, 5)
        layout.addWidget(QLabel("Decimals"), 1, 6)
        layout.addWidget(self.ui_double_decimals, 1, 7)

        self.setLayout(layout)
        self.ui_manager = ComponentManager(layout)
        self.setWindowTitle(self.tr("Dashboard 虚拟键盘输入测试"))

    def _initData(self):
        self.ui_double_min.setDecimals(1)
        self.ui_double_max.setDecimals(1)
        self.ui_double_max.setSingleStep(0.1)
        self.ui_double_min.setSingleStep(0.1)

        for item in (self.ui_int_min, self.ui_int_max, self.ui_double_min, self.ui_double_max):
            item.setRange(-99999999, 99999999)

        self.ui_int_max.setValue(100)
        self.ui_int_min.setValue(-100)
        self.ui_double_max.setValue(100)
        self.ui_double_min.setValue(-100)
        self.ui_double_decimals.setValue(2)

    def _initStyle(self):
        self.setStyleSheet('#QLabel{font: 30pt "宋体"}')
        for item in self.ui_manager.getByType(VirtualNumberInput):
            item.setSizePolicy(QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred))

    def _initSignalAndSlots(self):
        for item in self.ui_manager.getByType(QAbstractSpinBox):
            item.valueChanged.connect(self.slotInputRangeChanged)
        self.ui_theme_color.clicked.connect(self.slotChangeKeyboardThemeColor)

    def slotInputRangeChanged(self, value):
        if self.sender() == self.ui_int_min:
            self.ui_int_input.setProperty("min", value)
        elif self.sender() == self.ui_int_max:
            self.ui_int_input.setProperty("max", value)
        elif self.sender() == self.ui_double_min:
            self.ui_double_input.setProperty("min", value)
        elif self.sender() == self.ui_double_max:
            self.ui_double_input.setProperty("max", value)
        elif self.sender() == self.ui_double_decimals:
            self.ui_double_min.setDecimals(value)
            self.ui_double_max.setDecimals(value)
            self.ui_double_input.setProperty("decimals", value)
            self.ui_double_min.setSingleStep(1 / math.pow(10, value))
            self.ui_double_max.setSingleStep(1 / math.pow(10, value))

    def slotChangeKeyboardThemeColor(self):
        color = QColorDialog.getColor(VirtualNumberInput.themeColor, self, "请选择主题色")
        if isinstance(color, QColor):
            VirtualNumberInput.setThemeColor(color)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    QTextCodec.setCodecForTr(QTextCodec.codecForName("UTF-8"))
    widget = DemoDashboardInput()
    widget.show()
    sys.exit(app.exec_())
