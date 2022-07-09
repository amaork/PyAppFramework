# -*- coding: utf-8 -*-
from PySide2.QtGui import QColor, QFont, QFontMetrics, QPaintEvent, QPen, QBrush, QPainter
from PySide2.QtWidgets import QLabel, QWidget, QVBoxLayout, QSplitter, QHBoxLayout
from PySide2.QtCore import QSize, Qt, QRectF
from typing import Union, Optional
import collections

from ..gui.widget import BasicWidget
from ..core.datatype import resolve_number
from ..misc.windpi import get_program_scale_factor
__all__ = ['NumberMonitor', 'TemperatureMonitor', 'PressureMonitor', 'FlowMonitor', 'PercentageMonitor']


class NumberMonitor(BasicWidget):
    DEF_FONT_SIZE = 20
    DEF_RV_FONT = "等线 Light"
    DEF_BG_COLOR = QColor(0x5d, 0x4e, 0x60)

    Unit = ()
    DISPLAY_UNITS = ("", "")

    def __init__(self, title: str, unit_id: int = 0, sv: Optional[Union[int, float]] = None,
                 max_numbers: int = 4, decimal: bool = True, parent: Optional[QWidget] = None):
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
        self.__scale_factor = max(get_program_scale_factor())
        super(NumberMonitor, self).__init__(parent)

    def __repr__(self):
        return self._title

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

    def getSV(self) -> Union[int, float]:
        return self._sv

    def setSV(self, sv: Union[int, float]):
        self._sv = self.unitConvert(sv)
        self.update()

    def getRV(self) -> Union[int, float]:
        return self._current

    def setRV(self, rv: Union[int, float]):
        self._current = self.unitConvert(rv)
        self.update()

    def setUnit(self, unit: int):
        self._unit_id = unit if unit in self.Unit else 0
        self._sv = self.unitConvert(self.getSV())
        self._current = self.unitConvert(self.getRV())
        self.update()

    def setMaximumNumber(self, number: int):
        self._max_number = number + 1 if self._decimal_display else number
        self.update()

    def setDecimalDisplay(self, display: bool):
        display = True if display else False
        if self._decimal_display == display:
            return

        self._decimal_display = display
        self.setMaximumNumber(self._max_number + 1 if display else self._max_number - 1)

    def unitConvert(self, data: Union[int, float]) -> Union[int, float]:
        return data

    def setThemeColor(self, color: QColor):
        if not isinstance(color, QColor):
            return

        self._bg_color = color
        self.update()

    def __getFontSize(self) -> float:
        try:
            return self.width() / self._max_number / self.__scale_factor
        except ZeroDivisionError:
            print("Max number must greater than zero")

    def __getNoneState(self) -> str:
        return "-" * (self._max_number - 1)

    def sizeHint(self) -> QSize:
        meter1 = QFontMetrics(QFont("宋体", self.DEF_FONT_SIZE))
        meter2 = QFontMetrics(QFont(self.DEF_RV_FONT, int(self.__getFontSize())))
        meter3 = QFontMetrics(QFont(self.DEF_RV_FONT, int(self.__getFontSize() / 2)))

        min_height = meter1.height() * len(self._title) * 1.5 * 1.5
        min_width = meter1.width("中") + meter2.width(self._max_number * "0") + meter3.width(".00") * 2.5
        return QSize(min_width, min_height)

    def paintEvent(self, ev: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw background
        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(self._bg_color, Qt.SolidPattern))
        painter.drawRoundedRect(QRectF(0.0, 0.0, self.width(), self.height()), 5.0, 5.0)

        # Get value integer part and decimal part
        integer, fractional = resolve_number(self.getRV(), 2)

        # Draw real time value
        location = self.rect()
        if not self._decimal_display or self._current < 0:
            location.moveLeft(self.width() / 10)
        painter.setPen(QPen(QColor(Qt.white)))

        # Integer part
        painter.setFont(QFont(self.DEF_RV_FONT, int(self.__getFontSize())))
        current_str = "{}".format(integer if self.getRV() >= 0 else self.__getNoneState())
        painter.drawText(location, Qt.AlignCenter, current_str)

        # Decimal part
        if self.getRV() >= 0 and self._decimal_display:
            decimal_font = QFont(self.DEF_RV_FONT, int(self.__getFontSize() / 2))
            painter.setFont(decimal_font)
            space = 3 * (self._max_number - len(current_str))
            if len(current_str) > 2:
                space = 0 - space
            location.moveLeft((len(current_str) * decimal_font.pointSize() + space) * self.__scale_factor)
            location.moveTop(decimal_font.pointSize() / 2 * self.__scale_factor)
            painter.drawText(location, Qt.AlignCenter, ".{0:02d}".format(fractional))

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
        if self._sv is not None:
            # sv_str = "SV: {}".format(self._sv if self._sv >= 0 else "-" * self._max_number)
            sv_str = "SV: {}".format(self._sv)
        else:
            sv_str = ""
        painter.drawText(location, Qt.AlignCenter, sv_str)


class FlowMonitor(NumberMonitor):
    DISPLAY_UNITS = ('mL/min', 'mL/hour')
    Unit = collections.namedtuple('Unit', 'ml_min ml_hour')(*range(len(DISPLAY_UNITS)))

    def __init__(self, title: str, unit_id: int = Unit.ml_min, max_numbers: int = 3, parent: Optional[QWidget] = None):
        super(FlowMonitor, self).__init__(title=title, unit_id=unit_id, max_numbers=max_numbers, parent=parent)

    def unitConvert(self, data: Union[int, float]) -> Union[int, float, None]:
        if self._unit_id == 0:
            return data

        try:
            return data * 60
        except TypeError:
            return None


class PressureMonitor(NumberMonitor):
    DISPLAY_UNITS = ("psi", "kPa", "bar")
    Unit = collections.namedtuple('Unit', DISPLAY_UNITS)(*range(len(DISPLAY_UNITS)))

    def __init__(self, title: str, unit_id: int = 2, max_numbers: int = 3, parent: Optional[QWidget] = None):
        super(PressureMonitor, self).__init__(title=title, unit_id=unit_id, max_numbers=max_numbers, parent=parent)

    def unitConvert(self, data: Union[int, float]) -> Union[int, float, None]:
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


class PercentageMonitor(NumberMonitor):
    DISPLAY_UNITS = ('%',)

    def __init__(self, title: str, max_numbers: int = 3, parent: Optional[QWidget] = None):
        super(PercentageMonitor, self).__init__(title=title, unit_id=0, max_numbers=max_numbers, parent=parent)


class TemperatureMonitor(NumberMonitor):
    DISPLAY_UNITS = ("℃", "℉")
    Unit = collections.namedtuple('Unit', 'C F')(*range(len(DISPLAY_UNITS)))

    def __init__(self, title: str, sv: Optional[Union[int, float]] = None,
                 unit_id: int = 0, max_number: int = 3, parent: Optional[QWidget] = None):
        super(TemperatureMonitor, self).__init__(title, unit_id=unit_id, sv=sv, max_numbers=max_number, parent=parent)

    def unitConvert(self, data: Union[int, float]) -> Union[int, float, None]:
        if self._unit_id == 0:
            return data

        try:
            return data * 9.0 / 5 + 32
        except TypeError:
            return None
