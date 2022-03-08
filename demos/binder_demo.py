# -*- coding: utf-8 -*-
import sys
from ..gui.binder import SpinBoxBinder, ComboBoxBinder
from PySide2.QtWidgets import QWidget, QGridLayout, QSpinBox, QDoubleSpinBox, QLabel, QComboBox, QApplication, QLineEdit


class Demo(QWidget):
    def __init__(self, parent=None):
        super(Demo, self).__init__(parent)

        layout = QGridLayout()
        celsius = QDoubleSpinBox()
        fahrenheit = QDoubleSpinBox()

        edit = QLineEdit()
        edit.setReadOnly(True)

        temperature = QLabel()
        temperature.setProperty('format', '{:.2f}')
        self.celsius_temperature = SpinBoxBinder(celsius)
        self.fahrenheit_temperature = SpinBoxBinder(fahrenheit)
        self.celsius_temperature.bindTextBox(temperature, lambda c: c * 9.0 / 5 + 32)
        self.celsius_temperature.bindSpinBox(fahrenheit, lambda c: c * 9.0 / 5 + 32)
        self.fahrenheit_temperature.bindSpinBox(celsius, lambda f: (f - 32) * 5.0 / 9)
        self.celsius_temperature.bindTextBox(edit, lambda x: "Above 37.5" if x >= 37.5 else "Below 37.5")

        layout.addWidget(QLabel("SpinBoxBinder"), 0, 0)
        layout.addWidget(celsius, 0, 1)
        layout.addWidget(QLabel(self.tr("°C")), 0, 2)
        layout.addWidget(fahrenheit, 0, 3)
        layout.addWidget(QLabel(self.tr("°F")), 0, 4)
        layout.addWidget(temperature, 0, 5)
        layout.addWidget(edit, 0, 6)

        combobox1 = QComboBox()
        combobox2 = QComboBox()
        combobox1.addItems(("Celsius", "Fahrenheit"))
        combobox2.addItems(("Celsius", "Fahrenheit"))
        combobox_label1 = QLabel()
        combobox_label2 = QLabel()
        combobox_edit = QLineEdit()
        combobox_edit.setReadOnly(True)
        self.combobox = ComboBoxBinder(combobox1)
        self.combobox.bindComboBox(combobox2, True)
        self.combobox.bindTextBox(combobox_label1, (self.tr("°C"), self.tr("°F")))
        self.combobox.bindTextBox(combobox_label2, (self.tr("°F"), self.tr("°C")))
        self.combobox.bindTextBox(combobox_edit, (self.tr("Fahrenheit(°F)"), self.tr("Celsius(°C)")))

        layout.addWidget(QLabel("ComboBoxBinder"), 1, 0)
        layout.addWidget(combobox1, 1, 1)
        layout.addWidget(combobox_label1, 1, 2)
        layout.addWidget(combobox2, 1, 3)
        layout.addWidget(combobox_label2, 1, 4)
        layout.addWidget(combobox_edit, 1, 6)

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
    demo = Demo()
    demo.show()
    sys.exit(app.exec_())
