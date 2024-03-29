# -*- coding: utf-8 -*-
import math
import typing
import collections
from PySide2 import QtWidgets, QtGui
from typing import Union, Optional, Tuple
from PySide2.QtCore import QPoint, Qt, Signal, QRect, QEvent, QSize, QRectF, QTimerEvent

from ..core.datatype import *
from ..misc.settings import *
from ..misc import windpi as dpi
from ..gui.container import ComponentManager
__all__ = ['SampleSelectInput', 'VirtualNumberKeyboard', 'VirtualNumberInput', 'VolumeSelectInput']


class SampleSelectInput(QtWidgets.QWidget):
    MARGIN = 5
    DEFAULT_FONT = "Times New Roman"
    DEFAULT_OVER_COLOR = Qt.lightGray
    DEFAULT_BG_COLOR = QtGui.QColor(0x5d, 0x4e, 0x60)

    sampleSelected = Signal(object)

    def __init__(self, diameter: int = 400, numbers: int = 12,
                 font_name: str = DEFAULT_FONT, parent: Optional[QtWidgets.QWidget] = None):
        super(SampleSelectInput, self).__init__(parent)

        self.state = ""
        self.numbers = numbers
        self.move_over_idx = -1
        self.current_selected = 0
        self.font_name = font_name
        self.bg_color = self.DEFAULT_BG_COLOR
        self.__updatePanelDiameter(diameter)
        self.sample_poses = dict()
        self.__scale_factor = max(dpi.get_program_scale_factor())
        self.__scale_x, self.__scale_y = dpi.get_program_scale_factor()
        self.sample_angles = [0]
        single_sample_angle = 360 / numbers
        for i in range(1, numbers):
            self.sample_angles.append(360 - single_sample_angle * i)
        self.setMouseTracking(True)

    def __updatePanelDiameter(self, diameter: int):
        self.outer_ring_diameter = diameter - self.MARGIN * 2
        self.outer_ring_radius = self.outer_ring_diameter // 2

        self.inner_ring_diameter = self.outer_ring_diameter * 0.618
        self.inner_ring_radius = self.inner_ring_diameter / 2

        self.middle_ring_diameter = self.inner_ring_diameter + (self.outer_ring_diameter - self.inner_ring_diameter) / 2
        self.middle_ring_radius = self.middle_ring_diameter / 2

        self.sample_diameter = int(math.pi * self.middle_ring_diameter / (self.numbers + 2))
        self.sample_radius = int(self.sample_diameter / 2)

        self.center = QPoint(self.MARGIN + self.outer_ring_radius, self.MARGIN + self.outer_ring_radius)
        self.update()

    @staticmethod
    def angle_to_pos(radius: float, angle: float) -> Tuple[float, float]:
        pg = angle * math.pi / 180.0
        return radius * math.cos(pg), radius * math.sin(pg)

    def get_font_size(self, diameter: float, number: int):
        number_text_length = len("{}".format(number))
        return min(diameter / number_text_length / 0.618, diameter * 0.618) / self.__scale_factor

    def setState(self, st: str):
        if isinstance(st, str):
            self.state = st
            self.update()

    def getState(self) -> str:
        return self.state

    def setThemeColor(self, color: QtGui.QColor):
        if not isinstance(color, QtGui.QColor):
            return

        self.bg_color = color
        self.update()

    def getSelectLocation(self) -> int:
        return self.current_selected + 1

    def setSelectLocation(self, loc: int):
        if 1 <= loc <= 12:
            self.current_selected = loc - 1
            self.update()

    def getSelectedNumber(self, point: QRect) -> int:
        for number, rect in self.sample_poses.items():
            if rect.contains(point):
                return number - 1

        return -1

    def paintEvent(self, ev: QtGui.QPaintEvent):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        font = QtGui.QFont(self.font_name, int(self.get_font_size(self.sample_diameter, self.numbers)))

        # Draw outer ring
        painter.setPen(QtGui.QPen(Qt.NoPen))
        painter.setBrush(QtGui.QBrush(self.bg_color, Qt.SolidPattern))
        painter.drawEllipse(self.MARGIN, self.MARGIN, self.outer_ring_diameter, self.outer_ring_diameter)

        # Draw inner-ring
        painter.setPen(QtGui.QPen(Qt.NoPen))
        painter.setBrush(QtGui.QBrush(Qt.white, Qt.SolidPattern))
        painter.drawEllipse(self.center, self.inner_ring_radius, self.inner_ring_radius)

        if self.state:
            fm = QtGui.QFontMetrics(font)
            painter.setPen(self.bg_color)
            painter.setFont(font)
            painter.drawText(self.MARGIN + self.outer_ring_diameter // 2 - fm.width(self.state) // 2,
                             self.MARGIN + self.outer_ring_diameter // 2 + fm.height() // 3,
                             self.tr(self.state))

        # Draw sample
        self.sample_poses.clear()
        w = int(self.inner_ring_diameter)
        s = int(self.MARGIN + self.sample_diameter)
        self.sample_poses[0] = QRect(s, s, w, w)
        for idx, angel in enumerate(self.sample_angles):
            r = self.middle_ring_radius
            x, y = self.angle_to_pos(r, angel)
            x = self.center.x() + x - self.sample_radius
            y = self.center.y() + y - self.sample_radius
            self.sample_poses[idx + 1] = QRect(x, y, self.sample_diameter, self.sample_diameter)

            # Draw sample
            if self.move_over_idx == idx or self.current_selected == idx:
                color = self.DEFAULT_OVER_COLOR
            else:
                color = self.bg_color.darker()

            # rg = QRadialGradient()
            # rg.setColorAt(0.0, Qt.white)
            # rg.setColorAt(0.2, Qt.green)
            # rg.setColorAt(0.8, Qt.gray)
            # painter.setBrush(QBrush(rg))
            painter.setBrush(QtGui.QBrush(color, Qt.SolidPattern))
            painter.drawEllipse(x, y, self.sample_diameter, self.sample_diameter)

            # Draw sample text
            painter.setPen(self.bg_color)
            painter.setFont(font)
            painter.drawText(x, y, self.sample_diameter, self.sample_diameter, Qt.AlignCenter, "{}".format(idx + 1))

    def resizeEvent(self, ev: QtGui.QResizeEvent):
        width = ev.size().width()
        height = ev.size().height()
        self.__updatePanelDiameter(min(width, height))

    def mouseMoveEvent(self, ev: QtGui.QMouseEvent):
        self.move_over_idx = self.getSelectedNumber(ev.pos())
        self.update()

    def mouseReleaseEvent(self, ev: QtGui.QMouseEvent):
        if ev.button() != Qt.LeftButton:
            return

        number = self.getSelectedNumber(ev.pos())
        if number != -1:
            self.current_selected = number
            self.sampleSelected.emit(number + 1)
            # TODO: Add animation
            # print(number + 1)
            self.update()

    def enterEvent(self, ev: QEvent):
        pass

    def leaveEvent(self, ev: QEvent):
        self.move_over_idx = -1
        self.update()


class VolumeSelectInput(QtWidgets.QRadioButton):
    DEFAULT_FG_COLOR = Qt.lightGray
    DEFAULT_BG_COLOR = QtGui.QColor(0x5d, 0x4e, 0x60)

    def __init__(self, text: str, width: int = 60, height: int = 150,
                 cap_height: int = 25, parent: Optional[QtWidgets.QWidget] = None):
        super(VolumeSelectInput, self).__init__(parent)
        self.clicked.connect(self.slotChecked)

        self.text = text
        self.__fg_color = self.DEFAULT_FG_COLOR
        self.__bg_color = self.DEFAULT_BG_COLOR
        self.__scale_factor = max(dpi.get_program_scale_factor())
        self.__scale_x, self.__scale_y = dpi.get_program_scale_factor()
        self.__updateSize(width, height, cap_height)

    def sizeHint(self) -> QSize:
        return QSize(self.__width, self.__height + self.__cap_height * 2)

    def __updateSize(self, width: int, height: int, cap_height: int):
        self.__width = int(width * self.__scale_x)
        self.__height = int(height * self.__scale_y)
        self.__cap_height = cap_height
        self.__neck_height = self.__cap_height - 5
        self.__neck_width = self.__width * 0.618
        self.__neck_y_start = self.__neck_height
        self.update()

    def paintEvent(self, ev: QtGui.QPaintEvent):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        if self.isChecked():
            bg, fg = self.__bg_color, self.__fg_color
        else:
            bg, fg = self.__fg_color, self.__bg_color

        painter.setPen(QtGui.QPen(Qt.NoPen))
        painter.setBrush(QtGui.QBrush(bg, Qt.SolidPattern))
        painter.drawRoundedRect(0, 0, self.__width, self.__cap_height, 5.0, 5.0)
        painter.drawRoundedRect(self.__width // 5, self.__cap_height - 10,
                                self.__width // 5 * 3, self.__neck_height * 2, 5.0, 5.0)
        painter.drawRoundedRect(QRectF(0.0, self.__cap_height * 1.5, self.__width, self.__height), 5.0, 5.0)

        painter.setPen(QtGui.QPen(QtGui.QColor(fg)))
        painter.setFont(QtGui.QFont("Times New Roman", int(self.__width / 3 / self.__scale_factor)))
        painter.drawText(self.rect(), Qt.AlignLeft | Qt.AlignVCenter, self.text)

    def slotChecked(self):
        self.setChecked(True)

    def mousePressEvent(self, ev: QtGui.QMouseEvent):
        self.clicked.emit()

    def setThemeColor(self, color: QtGui.QColor):
        if not isinstance(color, QtGui.QColor):
            return

        self.__bg_color = color
        self.update()

    # def resizeEvent(self, ev: QResizeEvent):
    #     print(ev.size())
    #     self.__updateSize(ev.size().width(), ev.size().height())


class VirtualNumberInput(QtWidgets.QLineEdit):
    numberChanged = Signal(object)
    ThemeColor = QtGui.QColor(93, 78, 96)
    TextColor = QtGui.QColor(255, 255, 255)
    HoverColor = QtGui.QColor(0x96, 0xf7, 0x51)
    SpecialProperties = collections.namedtuple('SpecialProperties', 'Min Max Decimals')(*'min max decimals'.split())

    def __init__(self, initial_value: Union[int, float] = 0,
                 min_: Union[int, float] = 0, max_: Union[int, float] = 9999, decimals: int = 0,
                 theme: QtGui.QColor = ThemeColor, text: QtGui.QColor = TextColor, hover: QtGui.QColor = HoverColor,
                 parent: Optional[QtWidgets.QWidget] = None):
        super(VirtualNumberInput, self).__init__(parent)
        self.setReadOnly(True)

        self.setTextColor(text)
        self.setThemeColor(theme)
        self.setHoverColor(hover)

        self.setRange(min_, max_)
        self.setDecimals(decimals)

        self.setValidator(QtGui.QIntValidator(min_, max_))
        self.setText("{}".format(initial_value))
        # self.setStyleSheet("VirtualNumberInput:hover{{{}}}".format(self.hoverStylesheet()))

    @classmethod
    def getTextColor(cls):
        return cls.TextColor

    @classmethod
    def getHoverColor(cls):
        return cls.HoverColor

    @classmethod
    def getThemeColor(cls):
        return cls.ThemeColor

    @classmethod
    def setThemeColor(cls, color: QtGui.QColor):
        if not isinstance(color, QtGui.QColor):
            return

        cls.ThemeColor = color

    @classmethod
    def setTextColor(cls, color: QtGui.QColor):
        if not isinstance(color, QtGui.QColor):
            return

        cls.TextColor = color

    @classmethod
    def setHoverColor(cls, color: QtGui.QColor):
        if not isinstance(color, QtGui.QColor):
            return

        cls.HoverColor = color

    @staticmethod
    def color2Tuple(color: QtGui.QColor) -> Color:
        if not isinstance(color, QtGui.QColor):
            return 0, 0, 0

        return color.red(), color.green(), color.blue()

    @classmethod
    def hoverStylesheet(cls):
        return UiColorInput.get_color_stylesheet(cls.color2Tuple(cls.getHoverColor())) +\
               UiColorInput.get_bg_color_stylesheet(cls.color2Tuple(cls.getThemeColor()))

    def value(self) -> typing.Union[int, float]:
        decimals = self.property(self.SpecialProperties.Decimals)
        return str2float(self.text()) if decimals else str2number(self.text())

    def showKeyboard(self):
        input_min = self.property(self.SpecialProperties.Min)
        input_max = self.property(self.SpecialProperties.Max)
        decimals = self.property(self.SpecialProperties.Decimals)
        if not decimals:
            value = VirtualNumberKeyboard.getInt(
                initial_value=str2number(self.text()), min_=input_min, max_=input_max, parent=self
            )
        else:
            value = VirtualNumberKeyboard.getDouble(
                initial_value=str2float(self.text()), min_=input_min, max_=input_max, decimals=decimals, parent=self
            )
        if value is not None:
            self.setText(str(value))
            self.numberChanged.emit(value)

    def setDecimals(self, decimals: int):
        self.setProperty(self.SpecialProperties.Decimals, decimals)
        self.setProperty(
            ComponentManager.FormatPropertyKey,
            ComponentManager.DataFormat.Float if decimals else ComponentManager.DataFormat.Integer
        )

    def setValue(self, value: Union[int, float]):
        number_decimals = self.property(self.SpecialProperties.Decimals)
        self.setText("{0:.{1}f}".format(value, number_decimals) if number_decimals else str(value))

    def setRange(self, min_: typing.Union[int, float], max_: typing.Union[int,float]):
        self.setProperty(self.SpecialProperties.Min, min_)
        self.setProperty(self.SpecialProperties.Max, max_)

    def mousePressEvent(self, ev):
        if ev.button() != Qt.LeftButton:
            return

        self.showKeyboard()


class VirtualKeyboard(QtWidgets.QDialog):
    KEY_MAP = ()
    KeyPressed = Signal(object)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super(VirtualKeyboard, self).__init__(parent)


class VirtualNumberKeyboard(VirtualKeyboard):
    CLEAR_KEY, SIGN_KEY, DOT_KEY, DEL_KEY = "C", "+/-", ".", "<-"
    OK_KEY, CANCEL_KEY, MIN_KEY, MAX_KEY = "OK", "Cancel", "Min", "Max"

    KEY_MAP = (
        (MIN_KEY, MAX_KEY, CLEAR_KEY),
        ("7", "8", "9"),
        ("4", "5", "6"),
        ("1", "2", "3"),
        ("0", DOT_KEY, SIGN_KEY),
        ("<-", OK_KEY, CANCEL_KEY),
    )

    INT_KEY_MAP = (
        (MIN_KEY, MAX_KEY, SIGN_KEY),
        ("7", "8", "9"),
        ("4", "5", "6"),
        ("1", "2", "3"),
        ("0", OK_KEY, CANCEL_KEY),
    )

    MIN_WIDTH = 250
    MIN_HEIGHT = 324
    FONT_BASE_SIZE = 20
    DEF_FONT_NAME = "等线 Light"
    DISPLAY_FONT_SIZE = FONT_BASE_SIZE * 1.5

    def __init__(self,
                 min_: Union[int, float] = 0,
                 max_: Union[int, float] = 100,
                 title: str = '', password_mode: bool = False,
                 initial_value: Union[int, float] = 0, decimals: int = 0,
                 key_map: Union[list, tuple] = KEY_MAP, parent: Optional[QtWidgets.QWidget] = None):
        super(VirtualNumberKeyboard, self).__init__(parent)

        self.timer_cnt = 0
        self.min_number = min_
        self.max_number = max_
        self.key_map = key_map
        self.number_decimals = decimals

        self.old_display = ""
        self.current_display = ""
        self.overflow_flag = False
        self.initial_value = initial_value
        self.__password_mode = password_mode
        self.__scale_factor = max(dpi.get_program_scale_factor())

        try:
            self.fg_color = VirtualNumberInput.color2Tuple(VirtualNumberInput.getTextColor())
            self.rg_color = VirtualNumberInput.color2Tuple(VirtualNumberInput.getHoverColor())
            self.bg_color = VirtualNumberInput.color2Tuple(VirtualNumberInput.getThemeColor())
        except AttributeError:
            self.fg_color = VirtualNumberInput.TextColor
            self.rg_color = VirtualNumberInput.HoverColor
            self.bg_color = VirtualNumberInput.ThemeColor

        self.rg_color = UiColorInput.get_color_stylesheet(self.rg_color)
        self.fg_color = UiColorInput.get_color_stylesheet(self.fg_color)
        self.bg_color = UiColorInput.get_bg_color_stylesheet(self.bg_color)
        self.overflow_color = UiColorInput.get_color_stylesheet((255, 0, 0))

        self.__initUi()
        self.__initData()
        self.__initStyle()
        self.__initSignalAndSlots()
        self.clrOverflow()
        self.startTimer(100)

        if title:
            self.ui_display.setText(title)

    def __initUi(self):
        self.ui_display = QtWidgets.QLineEdit()

        key_layout = QtWidgets.QGridLayout()
        for row, row_keys in enumerate(self.key_map):
            for column, key in enumerate(row_keys):
                key = {
                    self.OK_KEY: self.tr("OK"),
                    self.CANCEL_KEY: self.tr("Cancel")
                }.get(key, key)
                btn = QtWidgets.QPushButton(key)
                btn.clicked.connect(self.slotNumberClicked)
                btn.setProperty("name", key)
                btn.setProperty("value", key)
                btn.setMinimumHeight(int(50 * self.__scale_factor))
                btn.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
                key_layout.addWidget(btn, row, column)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.ui_display)
        layout.addLayout(key_layout)
        self.setLayout(layout)
        self.ui_manager = ComponentManager(layout)

    def __initData(self):
        self.ui_display.setText(self.__numStr(self.initial_value))
        self.ui_min = self.ui_manager.getByValue("name", self.MIN_KEY, QtWidgets.QPushButton)
        self.ui_max = self.ui_manager.getByValue("name", self.MAX_KEY, QtWidgets.QPushButton)
        self.ui_min.setText(self.__minStr())
        self.ui_max.setText(self.__maxStr())

    def __initStyle(self):
        self.ui_display.setReadOnly(True)
        self.ui_display.setAlignment(Qt.AlignRight)
        self.ui_display.setMinimumHeight(int(self.FONT_BASE_SIZE * 4 * self.__scale_factor))
        self.ui_display.setMaxLength(len("{}".format(self.max_number)) + self.number_decimals + 1)

        meter = QtGui.QFontMetrics(QtGui.QFont("等线 Light", int(self.DISPLAY_FONT_SIZE * self.__scale_factor)))
        self.ui_display.setMinimumWidth(meter.width("0" * self.ui_display.maxLength() + "-.") * 3)

        [item.setStyleSheet(self.rg_color) for item in (self.ui_min, self.ui_max)]
        # self.setStyleSheet('QWidget{{{}}} QPushButton{{{}}} QPushButton:hover{{{}}}'.format(
        #     self.bg_color + 'font: {}pt "宋体"'.format(self.FONT_BASE_SIZE),
        #     self.bg_color + self.fg_color, self.rg_color,
        # ))

        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)

    def __initSignalAndSlots(self):
        ok = self.ui_manager.getByValue("name", self.tr(self.OK_KEY), QtWidgets.QPushButton)
        cancel = self.ui_manager.getByValue("name", self.tr(self.CANCEL_KEY), QtWidgets.QPushButton)
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)

    def __minStr(self) -> str:
        return self.__numStr(self.min_number)

    def __maxStr(self) -> str:
        return self.__numStr(self.max_number)

    def __numStr(self, num: Union[int, float]) -> str:
        return "{0:.{1}f}".format(num, self.number_decimals) if self.number_decimals else str(num)

    def __flush(self):
        self.ui_display.setText(self.current_display)

    def __checkValue(self) -> bool:
        return self.min_number <= str2float(self.current_display) <= self.max_number

    # def sizeHint(self) -> QSize:
    #     meter = QtGui.QFontMetrics(QtGui.QFont(self.DEF_FONT_NAME, self.FONT_BASE_SIZE))
    #     width = meter.width(str(self.min_number) + str(self.max_number) + "  C  ")
    #     return QSize(int(width * self.__scale_factor), int(meter.height() * len(self.key_map) * self.__scale_factor))

    def setOverflow(self):
        self.overflow_flag = True
        self.ui_display.setStyleSheet("font: {}pt '等线 Light'; {};{};".format(
            self.DISPLAY_FONT_SIZE * self.__scale_factor, self.ui_display.styleSheet(), self.overflow_color)
        )

    def clrOverflow(self):
        self.overflow_flag = False
        self.ui_display.setStyleSheet("font: {}pt '等线 Light'; {};{};".format(
            self.DISPLAY_FONT_SIZE * self.__scale_factor, self.ui_display.styleSheet(), self.fg_color)
        )

    def callbackCheckOverflow(self):
        v = str2float(self.ui_display.text())
        if v > self.max_number or v < self.min_number and v != 0:
            self.current_display = self.old_display
            self.setOverflow()
            self.__flush()
            return

    def slotNumberClicked(self):
        key = self.sender()
        value = key.property("value")
        new_value = self.current_display

        # Backup old display
        if not self.current_display:
            self.old_display = self.ui_display.text()

            if self.__password_mode:
                self.ui_display.setEchoMode(QtWidgets.QLineEdit.Password)

        if value in map(str, range(0, 10)):
            if value == "0" and self.current_display == "0":
                return

            try:
                new_value += value
                dot_pos = self.current_display.index(".")
                if len(new_value[dot_pos + 1:]) > self.number_decimals:
                    return
            except ValueError:
                pass

        elif value == self.MAX_KEY:
            new_value = self.__maxStr()
        elif value == self.MIN_KEY:
            new_value = self.__minStr()
        elif value == self.CLEAR_KEY:
            new_value = ""
            self.old_display = ""
        elif value == self.DOT_KEY:
            if self.number_decimals <= 0:
                return

            if "." in self.current_display:
                return

            if len(self.current_display) == 0:
                new_value = "0."
            else:
                new_value += "."

        elif value == self.SIGN_KEY:
            if self.current_display.startswith("-"):
                new_value = self.current_display[1:]
            else:
                new_value = "-" + self.current_display
        elif value == self.DEL_KEY:
            if not len(self.current_display):
                return

            new_value = self.current_display[:-1]
        else:
            return

        self.current_display = new_value

        self.__flush()

    def getIntValue(self) -> int:
        if self.result():
            try:
                v = int(self.current_display, 10)
            except ValueError:
                v = 0
            return v if self.min_number <= v <= self.max_number else str2number(self.old_display)

    def getDoubleValue(self) -> float:
        if self.result():
            v = str2float(self.current_display)
            return v if self.min_number <= v <= self.max_number else str2float(self.old_display)

    def timerEvent(self, ev: QTimerEvent):
        self.timer_cnt += 1

        if self.overflow_flag:
            if self.__checkValue():
                self.clrOverflow()
            return

        if self.timer_cnt % 2 == 0:
            v = str2float(self.current_display)
            if (v > self.max_number and not math.isclose(v, self.max_number)) or \
                    (v < self.min_number and not math.isclose(v, self.min_number)) and v != 0:
                self.setOverflow()
                return

    @classmethod
    def getInt(cls, **kwargs) -> int:
        kwargs['decimals'] = 0
        dialog = cls(**kwargs)
        dialog.exec_()
        return dialog.getIntValue()

    @classmethod
    def getDouble(cls, **kwargs) -> float:
        kwargs.setdefault('decimals', 1)
        dialog = cls(**kwargs)
        dialog.exec_()
        return dialog.getDoubleValue()
