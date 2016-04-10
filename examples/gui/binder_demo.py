# -*- coding: utf-8 -*-

import sys
import inspect
sys.path.append("../../")
from gui.binder import *
from PySide.QtGui import *
from PySide.QtCore import *


def func1(a):
    pass

def func2(b):
    pass

def func3():
    pass


class Demo(QWidget):
    def __init__(self, parent=None):
        super(Demo, self).__init__(parent)

        layout = QGridLayout()
        celsius = QDoubleSpinBox()
        fahrenheit = QDoubleSpinBox()
        temperature = QLabel()
        self.celsius_temperature = SpinBoxBinder(celsius)
        self.fahrenheit_temperature = SpinBoxBinder(fahrenheit)
        self.celsius_temperature.bindLabel(temperature, lambda c: c * 9.0 / 5 + 32)
        self.celsius_temperature.bindSpinBox(fahrenheit, lambda c: c * 9.0 / 5 + 32)
        self.fahrenheit_temperature.bindSpinBox(celsius, lambda f: (f - 32) * 5.0 / 9)

        layout.addWidget(QLabel("SpinBoxBinder"), 0, 0)
        layout.addWidget(celsius, 0, 1)
        layout.addWidget(QLabel(self.tr("°C")), 0, 2)
        layout.addWidget(fahrenheit, 0, 3)
        layout.addWidget(QLabel(self.tr("°F")), 0, 4)
        layout.addWidget(temperature, 0, 5)

        combobox1 = QComboBox()
        combobox2 = QComboBox()
        combobox1.addItems(("Celsius", "Fahrenheit"))
        combobox2.addItems(("Celsius", "Fahrenheit"))
        combobox_label1 = QLabel()
        combobox_label2 = QLabel()
        self.combobox = ComboBoxBinder(combobox1)
        self.combobox.bindComboBox(combobox2, True)
        self.combobox.bindLabel(combobox_label1, (self.tr("°C"), self.tr("°F")))
        self.combobox.bindLabel(combobox_label2, (self.tr("°F"), self.tr("°C")))

        layout.addWidget(QLabel("ComboBoxBinder"), 1, 0)
        layout.addWidget(combobox1, 1, 1)
        layout.addWidget(combobox_label1, 1, 2)
        layout.addWidget(combobox2, 1, 3)
        layout.addWidget(combobox_label2, 1, 4)


        limit = QComboBox()
        limit.addItem("100 - 300, 10")
        limit.addItem("400 - 600, 50")
        limit.addItem("1000")
        spinbox = QSpinBox()
        self.limitBinder = ComboBoxBinder(limit)
        self.limitBinder.bindSpinBox(spinbox, ((100, 300, 10), (400, 600, 50), 1000))

        layout.addWidget(QLabel("ComboBox bind SpinBox"), 2, 0)
        layout.addWidget(limit, 2, 1)
        layout.addWidget(spinbox, 2, 3)





        self.setLayout(layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    QTextCodec.setCodecForTr(QTextCodec.codecForName("UTF-8"))
    demo = Demo()
    demo.show()
    sys.exit(app.exec_())