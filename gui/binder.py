# -*- coding: utf-8 -*-
from PySide.QtCore import QObject
from typing import Optional, Union, Callable, Sequence
from PySide.QtGui import QSpinBox, QDoubleSpinBox, QLabel, QComboBox, QWidget


__all__ = ['SpinBoxBinder', 'ComboBoxBinder']
BinderFactor = Union[int, float, Callable[[Union[int, float]], Union[int, float, str]]]


class SpinBoxBinder(QObject):
    def __init__(self, spinbox, parent: Optional[QWidget] = None):
        super(SpinBoxBinder, self).__init__(parent)
        if not isinstance(spinbox, (QSpinBox, QDoubleSpinBox)):
            raise TypeError("spinbox require a {!r} or {!r} not {!r}".format(
                QSpinBox.__name__, QDoubleSpinBox.__name__, spinbox.__class__.__name__))

        self.__binding = list()
        self.__spinbox = spinbox
        self.__spinbox.valueChanged.connect(self.eventProcess)

    @staticmethod
    def __remap(factor: BinderFactor, value: Union[int, float]) -> Union[int, float, str]:
        if isinstance(factor, (int, float)):
            return value * factor
        elif hasattr(factor, "__call__"):
            return factor(value)
        else:
            return value

    def bindLabel(self, obj: QLabel, factor: BinderFactor) -> bool:
        if not isinstance(obj, QLabel):
            print("Bind error, object type error:{!r}".format(obj.__class__.__name__))
            return False

        if not isinstance(factor, (int, float)) and not hasattr(factor, "__call__"):
            print("Bind error, factor type error, require: {!r}".format(BinderFactor))
            return False

        self.__binding.append((obj, factor))
        return True

    def bindSpinBox(self, obj: Union[QSpinBox, QDoubleSpinBox], factor: BinderFactor) -> bool:
        if not isinstance(obj, (QSpinBox, QDoubleSpinBox)):
            print("Bind error, object type error:{!r}".format(obj.__class__.__name__))
            return False

        if not isinstance(factor, (int, float)) and not hasattr(factor, "__call__"):
            print("Bind error, factor type error, require: {!r}".format(BinderFactor))
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

    def eventProcess(self, value: Union[int, float]):
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
    def __init__(self, combobox: QComboBox, parent: Optional[QWidget] = None):
        super(ComboBoxBinder, self).__init__(parent)
        if not isinstance(combobox, QComboBox):
            raise TypeError("combobox require {!r} not {!r}".format(QComboBox.__name__, combobox.__class__.__name__))

        self.__combobox = combobox
        self.__binding = list()
        self.__combobox.currentIndexChanged.connect(self.eventProcess)

    def bindLabel(self, obj: QLabel, text: Sequence[str]) -> bool:
        if not self.__combobox:
            return False

        if not isinstance(obj, QLabel):
            print("Bind error, object type error:{!r}".format(obj.__class__.__name__))
            return False

        if not isinstance(text, (tuple, list)) and len(text) != self.__combobox.count():
            print("Bind error, text type or count error")
            return False

        self.__binding.append((obj, text))
        self.eventProcess(self.__combobox.currentIndex())
        return True

    def bindSpinBox(self, obj: Union[QSpinBox, QDoubleSpinBox], limit: Union[list, tuple]) -> bool:
        if not isinstance(obj, (QSpinBox, QDoubleSpinBox)):
            print("Bind error, object type error:{!r}".format(obj.__class__.__name__))
            return False

        if not isinstance(limit, (tuple, list)) and len(limit) != self.__combobox.count():
            print("Bind error, text type or count error")
            return False

        self.__binding.append((obj, limit))
        self.eventProcess(self.__combobox.currentIndex())
        return True

    def bindCallback(self, obj: Callable, *args):
        if not hasattr(obj, "__call__"):
            print("Bind error, object must be callable object not 'Callable'")
            return False

        self.__binding.append((obj, *args))
        self.eventProcess(self.__combobox.currentIndex())

    def bindComboBox(self, obj: QComboBox, reverse: bool = False) -> bool:
        if not isinstance(obj, QComboBox):
            print("Bind error, object type error:{!r}".format(obj.__class__.__name__))
            return False

        if obj.count() != self.__combobox.count():
            print("Bind error, two ComboBox count number should be same!")
            return False

        self.__binding.append((obj, reverse))
        self.eventProcess(self.__combobox.currentIndex())
        return True

    def eventProcess(self, index: int):
        if not isinstance(index, int) or index >= self.__combobox.count():
            return

        for receiver, data in self.__binding:
            if hasattr(receiver, "__call__"):
                receiver(self.__combobox, *data)
            # QCombobox
            elif isinstance(receiver, QComboBox):
                if data:
                    receiver.setCurrentIndex(self.__combobox.count() - index - 1)
                else:
                    receiver.setCurrentIndex(index)
            # QLabel
            elif isinstance(receiver, QLabel) and isinstance(data[index], str):
                receiver.setText(data[index])
            # QSpinBox
            elif isinstance(receiver, (QSpinBox, QDoubleSpinBox)):
                setting = data[index]

                # Setting data is a tuple
                if isinstance(setting, (tuple, list)):
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
