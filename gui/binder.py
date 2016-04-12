# -*- coding: utf-8 -*-

import types
from PySide.QtGui import *
from PySide.QtCore import *


__all__ = ['SpinBoxBinder', 'ComboBoxBinder']


class SpinBoxBinder(QObject):

    def __init__(self, spinbox, parent=None):
        super(SpinBoxBinder, self).__init__(parent)

        assert isinstance(spinbox, (QSpinBox, QDoubleSpinBox)), "TypeError:{0:s}".format(type(spinbox))

        self.__binding = list()
        self.__spinbox = spinbox
        self.__spinbox.valueChanged.connect(self.eventProcess)

    def __remap(self, factor, value):
        if isinstance(factor, (int, float)):
            return value * factor
        elif hasattr(factor, "__call__"):
            return factor(value)
        else:
            return value

    def bindLabel(self, obj, factor):
        if not isinstance(obj, QLabel):
            print "Bind error, object type error:{0:s}".format(type(obj))
            return False

        if not isinstance(factor, (int, float)) and not hasattr(factor, "__call__"):
            print "Bind error, factor type error{0:s}".format(type(factor))
            return False

        self.__binding.append((obj, factor))
        return True

    def bindSpinBox(self, obj, factor):
        if not isinstance(obj, (QSpinBox, QDoubleSpinBox)):
            print "Bind error, object type error:{0:s}".format(type(obj))
            return False

        if not isinstance(factor, (int, float)) and not hasattr(factor, "__call__"):
            print "Bind error, factor type error{0:s}".format(type(factor))
            return False

        # Set spinbox range and single step
        minimum = factor(self.__spinbox.minimum()) if hasattr(factor, "__call__") else self.__spinbox.minimum() * factor
        maximum = factor(self.__spinbox.maximum()) if hasattr(factor, "__call__") else self.__spinbox.maximum() * factor
        obj.setRange(minimum, maximum)

        # Set dst SpinBox decimals
        if isinstance(obj, QDoubleSpinBox) and isinstance(factor, float):
            obj.setDecimals(len(str(factor).split('.')[-1]))
            obj.setSingleStep(factor)

        # Add object to binging list
        self.__binding.append((obj, factor))
        return True

    def eventProcess(self, value):
        if not isinstance(value, (int, float)):
            return

        for receiver, factor in self.__binding:
            # QSpinBox or QDoubleSpinBox
            if isinstance(receiver, (QSpinBox, QDoubleSpinBox)):
                receiver.setValue(self.__remap(factor, value))

            # QLabel
            elif isinstance(receiver, QLabel):
                receiver.setText("{0:.2f}".format(self.__remap(factor, value)))


class ComboBoxBinder(QObject):
    def __init__(self, combobox, parent=None):
        super(ComboBoxBinder, self).__init__(parent)

        assert isinstance(combobox, QComboBox), "TypeError:{0:s}".format(type(combobox))

        self.__combobox = combobox
        self.__binding = list()
        self.__combobox.currentIndexChanged.connect(self.eventProcess)

    def bindLabel(self, obj, text):
        if not self.__combobox:
            return False

        if not isinstance(obj, QLabel):
            print "Bind error, object type error:{0:s}".format(type(obj))
            return False

        if not isinstance(text, tuple) and len(text) != self.__combobox.count():
            print "Bind error, text type or count error"
            return False

        self.__binding.append((obj, text))
        self.eventProcess(self.__combobox.currentIndex())
        return True

    def bindSpinBox(self, obj, limit):
        if not isinstance(obj, (QSpinBox, QDoubleSpinBox)):
            print "Bind error, object type error:{0:s}".format(type(obj))
            return False

        if not isinstance(limit, tuple) and len(limit) != self.__combobox.count():
            print "Bind error, text type or count error"
            return False

        self.__binding.append((obj, limit))
        self.eventProcess(self.__combobox.currentIndex())
        return True

    def bindComboBox(self, obj, reverse=False):
        if not isinstance(obj, QComboBox):
            print "Bind error, object type error:{0:s}".format(type(obj))
            return False

        if obj.count() != self.__combobox.count():
            print "Bind error, two ComboBox count number should be same!"
            return False

        self.__binding.append((obj, reverse))
        self.eventProcess(self.__combobox.currentIndex())
        return True

    def eventProcess(self, index):
        if not isinstance(index, int) or index >= self.__combobox.count():
            return

        for receiver, data in self.__binding:

            # QCombobox
            if isinstance(receiver, QComboBox):
                if data:
                    receiver.setCurrentIndex(self.__combobox.count() - index - 1)
                else:
                    receiver.setCurrentIndex(index)

            # QLabel
            elif isinstance(receiver, QLabel) and isinstance(data[index], types.StringTypes):
                    receiver.setText(data[index])

            # QSpinBox
            elif isinstance(receiver, (QSpinBox, QDoubleSpinBox)):
                setting = data[index]

                # Setting data is a tuple
                if isinstance(setting, tuple):
                    for num in setting:
                        if not isinstance(num, (int, float)):
                            return

                    # Setting range and limit
                    if len(setting) == 3:
                        receiver.setSingleStep(setting[2])
                        receiver.setRange(setting[0], setting[1])
                    # Setting range
                    elif len(setting) == 2:
                        receiver.setRange(setting[0], setting[1])

                # Setting value
                elif isinstance(setting, (int, float)):
                    receiver.setRange(setting, setting)
