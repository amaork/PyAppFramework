# -*- coding: utf-8 -*-
import math
from PySide.QtGui import *
from PySide.QtCore import *
from ..gui.widget import BasicWidget
__all__ = ['NumberMonitor', 'TemperatureMonitor', 'PressureMonitor']


class NumberMonitor(BasicWidget):
    DEF_FONT_SIZE = 20
    DEF_RV_FONT = "等线 Light"
    DEF_BG_COLOR = QColor(0x5d, 0x4e, 0x60)

    DISPLAY_UNITS = ("", "")
    SETTINGS_UNITS = ("", "")

    def __init__(self, title, unit_id=0, sv=None, max_numbers=4, decimal=True, parent=None):
        """
        Number monitor
        :param title: Number meaning label
        :param unit_id: Default unit index
        :param sv: Set value
        :param max_numbers: Maximum display number don't include decimal (9999 => 4)
        :param decimal: Enable / disable decimal display
        :param parent:
        """
        assert isinstance(title, str), "title must be a string"
        assert max_numbers > 0, "max_number must greater than zero"
        self._sv = sv
        self._current = -1.0 if decimal else -1
        self._title = title
        self._unit_id = unit_id
        self._bg_color = self.DEF_BG_COLOR
        self._decimal_display = True if decimal else False
        self._max_number = max_numbers + 1 if decimal else 0
        super(NumberMonitor, self).__init__(parent)

    def _initUi(self):
        self.ui_title = QLabel("\n".join(self._title))
        left_layout = QVBoxLayout()
        left_layout.addWidget(QSplitter())
        left_layout.addWidget(self.ui_title)
        left_layout.addWidget(QSplitter())

        layout = QHBoxLayout()
        layout.addLayout(left_layout)
        layout.addWidget(QSplitter())
        self.setLayout(layout)

    def _initStyle(self):
        self.setStyleSheet('color: rgb(255, 255, 255);font: {}pt "宋体";'.format(self.DEF_FONT_SIZE))

    def getSV(self):
        return self._sv

    def setSV(self, sv):
        self._sv = self.unitConvert(sv)
        self.update()

    def getRV(self):
        return self._current

    def setRV(self, rv):
        self._current = self.unitConvert(rv)
        self.update()

    def setUnit(self, unit_setting):
        try:
            self._unit_id = self.SETTINGS_UNITS.index(unit_setting)
        except ValueError:
            self._unit_id = 0

        self._sv = self.unitConvert(self.getSV())
        self._current = self.unitConvert(self.getRV())
        self.update()

    def setMaximumNumber(self, number):
        self._max_number = number + 1 if self._decimal_display else number
        self.update()

    def setDecimalDisplay(self, display):
        display = True if display else False
        if self._decimal_display == display:
            return

        self._decimal_display = display
        self.setMaximumNumber(self._max_number + 1 if display else self._max_number - 1)

    def unitConvert(self, data):
        return data

    def setThemeColor(self, color):
        if not isinstance(color, QColor):
            return

        self._bg_color = color
        self.update()

    def __getFontSize(self):
        try:
            return self.width() / self._max_number
        except ZeroDivisionError:
            print("Max number must greater than zero")

    def __getNoneState(self):
        return "-" * (self._max_number - 1)

    def paintEvent(self, ev):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw background
        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(self._bg_color, Qt.SolidPattern))
        painter.drawRoundedRect(QRectF(0.0, 0.0, self.width(), self.height()), 5.0, 5.0)

        # Get value integer part and decimal part
        decimal, integer = math.modf(self.getRV())
        decimal = int(decimal * 100)
        integer = int(integer)

        # Draw real time value
        location = self.rect()
        if not self._decimal_display or self._current < 0:
            location.moveLeft(self.width() / 10)
        painter.setPen(QPen(QColor(Qt.white)))

        # Integer part
        painter.setFont(QFont(self.DEF_RV_FONT, self.__getFontSize()))
        current_str = "{}".format(integer if self.getRV() >= 0 else self.__getNoneState())
        painter.drawText(location, Qt.AlignCenter, current_str)

        # Decimal part
        if self.getRV() >= 0 and self._decimal_display:
            decimal_font = QFont(self.DEF_RV_FONT, self.__getFontSize() / 2)
            painter.setFont(decimal_font)
            space = 3 * (self._max_number - len(current_str))
            if len(current_str) > 2:
                space = 0 - space
            location.moveLeft(len(current_str) * decimal_font.pointSize() + space)
            location.moveTop(decimal_font.pointSize() / 2)
            painter.drawText(location, Qt.AlignCenter, ".{0:02d}".format(decimal))

        # Draw data unit
        location = self.rect()
        location.moveTop(self.width() / 4)
        painter.setFont(QFont("宋体", self.DEF_FONT_SIZE))
        location.moveLeft(self.width() / 3 + self.DEF_FONT_SIZE / 2 - len(self.DISPLAY_UNITS[self._unit_id]) * 3)
        painter.drawText(location, Qt.AlignCenter, self.DISPLAY_UNITS[self._unit_id])

        # Draw set value
        location = self.rect()
        location.moveTop(self.height() / 2 - self.DEF_FONT_SIZE)
        painter.setFont(QFont("宋体", self.DEF_FONT_SIZE))
        painter.setPen(QPen(QColor(Qt.lightGray)))
        sv_str = "SV: {}".format(self._sv if self._sv >= 0 else "-" * self._max_number) if self._sv else ""
        painter.drawText(location, Qt.AlignCenter, sv_str)


class PressureMonitor(NumberMonitor):
    DISPLAY_UNITS = ("psi", "kPa", "bar")
    SETTINGS_UNITS = ("psi", "kPa", "bar")

    def __init__(self, title, unit_id=2, max_numbers=3, parent=None):
        super(PressureMonitor, self).__init__(title=title, unit_id=unit_id, max_numbers=max_numbers, parent=parent)

    def unitConvert(self, data):
        def bar2psi(bar):
            self.setMaximumNumber(4)
            self.setDecimalDisplay(True)
            return bar * 14.5

        def bar2kpa(bar):
            self.setMaximumNumber(6)
            self.setDecimalDisplay(False)
            return bar * 100

        if self._unit_id == 2:
            self.setMaximumNumber(3)
            self.setDecimalDisplay(True)
            return data

        try:
            convert_func = bar2psi if self._unit_id == 0 else bar2kpa
            return convert_func(data)
        except TypeError:
            return None


class TemperatureMonitor(NumberMonitor):
    DISPLAY_UNITS = ("℃", "℉")
    SETTINGS_UNITS = ("摄氏温度℃", "华氏温度℉")

    def __init__(self, title, sv=None, unit_id=0, max_number=3, parent=None):
        super(TemperatureMonitor, self).__init__(title, unit_id=unit_id, sv=sv, max_numbers=max_number, parent=parent)

    def unitConvert(self, data):
        if self._unit_id == 0:
            return data

        try:
            return data * 9.0 / 5 + 32
        except TypeError:
            return None
