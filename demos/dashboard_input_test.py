# -*- coding: utf-8 -*-
import sys
import math
from PySide2.QtWidgets import QPushButton, QLabel, QSpinBox, QColorDialog, QApplication, QSizePolicy, \
    QAbstractSpinBox, QGridLayout, QDoubleSpinBox

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
        self.ui_text_color = QPushButton("键盘文字颜色")
        self.ui_hover_color = QPushButton("键盘滑动颜色")

        layout.addWidget(QLabel("Integer"), 0, 0)
        layout.addWidget(self.ui_int_input, 0, 1)
        layout.addWidget(QLabel("Min"), 0, 2)
        layout.addWidget(self.ui_int_min, 0, 3)
        layout.addWidget(QLabel("Max"), 0, 4)
        layout.addWidget(self.ui_int_max, 0, 5)
        layout.addWidget(QLabel("Theme"), 0, 6)
        layout.addWidget(self.ui_theme_color, 0, 7)
        layout.addWidget(self.ui_text_color, 0, 8)

        layout.addWidget(QLabel("Double"), 1, 0)
        layout.addWidget(self.ui_double_input, 1, 1)
        layout.addWidget(QLabel("Min"), 1, 2)
        layout.addWidget(self.ui_double_min, 1, 3)
        layout.addWidget(QLabel("Max"), 1, 4)
        layout.addWidget(self.ui_double_max, 1, 5)
        layout.addWidget(QLabel("Decimals"), 1, 6)
        layout.addWidget(self.ui_double_decimals, 1, 7)
        layout.addWidget(self.ui_hover_color, 1, 8)

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

        self.ui_text_color.clicked.connect(self.slotChangeKeyboardTextColor)
        self.ui_theme_color.clicked.connect(self.slotChangeKeyboardThemeColor)
        self.ui_hover_color.clicked.connect(self.slotChangeKeyboardHoverColor)

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

    def slotChangeKeyboardTextColor(self):
        VirtualNumberInput.setTextColor(QColorDialog.getColor(VirtualNumberInput.getTextColor(), self, "请选择文字颜色"))

    def slotChangeKeyboardHoverColor(self):
        VirtualNumberInput.setHoverColor(QColorDialog.getColor(VirtualNumberInput.getHoverColor(), self, "请选择滑动颜色"))

    def slotChangeKeyboardThemeColor(self):
        VirtualNumberInput.setThemeColor(QColorDialog.getColor(VirtualNumberInput.getThemeColor(), self, "请选择主题色"))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    widget = DemoDashboardInput()
    widget.show()
    sys.exit(app.exec_())
