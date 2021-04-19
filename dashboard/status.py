# -*- coding: utf-8 -*-
from PySide.QtGui import *
from PySide.QtCore import *
from typing import Union, Optional, Sequence
from ..misc.windpi import get_program_scale_factor
__all__ = ['DashboardStatusIcon']


class DashboardStatusIcon(QWidget):
    DEF_RADIUS = 6
    DEF_FONT_NAME = "Vrinda"
    DEF_FG_COLOR = QColor(14, 11, 54)
    DEF_BG_COLOR = QColor(Qt.white)
    HOVER_COLOR = QColor(240, 154, 55)
    DEF_FONT_COLOR = QColor(240, 240, 240)

    clicked = Signal(object)
    doubleClicked = Signal(object)

    def __init__(self, parent: QWidget, name: str, status: Sequence[str],
                 tips: str = "", size: Optional[QSize] = None, differ_font_size: bool = False):
        super(DashboardStatusIcon, self).__init__(parent)
        if not isinstance(name, str):
            raise TypeError("name require a str")

        if not isinstance(status, (list, tuple)) or len(status) == 0:
            raise TypeError("states require a list or tuple")

        self._name = name
        self._current = 0
        self._status = status
        self._display = status[0]
        self._bg_color = self.DEF_BG_COLOR
        self._fg_color = self.DEF_FG_COLOR
        self._hover_color = self.HOVER_COLOR
        self._font_color = self.DEF_FONT_COLOR
        self._font_color_bk = self.DEF_FONT_COLOR
        self._scale_factor = max(get_program_scale_factor())
        self._scale_x, self._scale_y = get_program_scale_factor()
        self._radius = self.DEF_RADIUS * self._scale_factor
        self._differ_font_size = differ_font_size
        self._font = QFont(self.DEF_FONT_NAME, 15)
        self._display_font = QFont(self.DEF_FONT_NAME, 15)
        if isinstance(size, QSize):
            self.setMinimumSize(self.__scaleSize(size))
        self.setToolTip(tips)

    def __repr__(self):
        return "{}: {}".format(self.name, self.status())

    def __scaleSize(self, size: QSize) -> QSize:
        return QSize(self._scale_x * size.width(), self._scale_y * size.height()) if isinstance(size, QSize) else size

    def __getFontSize(self) -> float:
        try:
            return self.width() / 10 / self._scale_factor
        except ZeroDivisionError:
            print("Max number must greater than zero")

    def sizeHint(self) -> QSize:
        meter = QFontMetrics(self._font)
        return QSize(meter.width(self._name) * 1.2, meter.height() * 3)

    @property
    def name(self) -> str:
        return self._name[:]

    @property
    def font(self) -> QFont:
        return self._font

    @property
    def font_size(self) -> int:
        return self._display_font.pixelSize()

    @font_size.setter
    def font_size(self, size: int):
        if isinstance(size, int):
            self._display_font.setPointSize(size)
            self.update()

    @property
    def bg_color(self) -> QColor:
        return self._bg_color

    @property
    def fg_color(self) -> QColor:
        return self._fg_color

    @bg_color.setter
    def bg_color(self, color: Union[QColor, Qt.GlobalColor]):
        if isinstance(color, (QColor, Qt.GlobalColor)):
            self._bg_color = color
            self.update()

    @fg_color.setter
    def fg_color(self, color: Union[QColor, Qt.GlobalColor]):
        if isinstance(color, (QColor, Qt.GlobalColor)):
            self._fg_color = color
            self.update()

    @property
    def font_color(self) -> QColor:
        return self._font_color

    @font_color.setter
    def font_color(self, color: Union[QColor, Qt.GlobalColor]):
        if isinstance(color, (QColor, Qt.GlobalColor)):
            self._font_color = color
            self.update()

    @property
    def hover_color(self) -> QColor:
        return self._hover_color

    @hover_color.setter
    def hover_color(self, color: Union[QColor, Qt.GlobalColor]):
        if isinstance(color, (QColor, Qt.GlobalColor)):
            self._hover_color = color
            self.update()

    def reset(self):
        self._current = 0
        self._display = self._status[self._current]
        self.update()

    def status(self) -> str:
        return self._display

    def switchStatus(self):
        self._current += 1
        self._current %= len(self._status)
        self._display = self._status[self._current]
        self.update()

    def changeStatus(self, st: str):
        if st in self._status:
            self._current = self._status.index(st)
            self._display = self._status[self._current]
            self.update()
        elif isinstance(st, str):
            self._display = st
            self.update()

    def enterEvent(self, ev: QEvent):
        self._font_color_bk = self._font_color
        self._font_color = self._hover_color
        self.update()

    def leaveEvent(self, ev: QEvent):
        self._font_color = self._font_color_bk
        self.update()

    def resizeEvent(self, ev: QResizeEvent):
        self._font = QFont(self.DEF_FONT_NAME, self.__getFontSize())
        self.update()

    def mousePressEvent(self, ev: QMouseEvent):
        self.clicked.emit(self._display)

    def mouseDoubleClickEvent(self, ev: QMouseEvent):
        self.doubleClicked.emit(self._display)

    def paintEvent(self, ev: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        x_radius = self._radius
        y_radius = self._radius

        # Draw background
        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(self._bg_color, Qt.SolidPattern))
        painter.drawRoundedRect(QRectF(0.0, 0.0, self.width(), self.height()), x_radius, y_radius)

        # Draw status name
        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(self._fg_color, Qt.SolidPattern))
        painter.drawRect(QRectF(0.0, self.height() / 2, self.width(), self.height() / 2 - y_radius))
        painter.drawRoundedRect(QRectF(0.0, self.height() / 2, self.width(), self.height() / 2), x_radius, y_radius)

        # Draw status name
        rect = self.rect()
        rect.moveTop(self.height() / 4)
        painter.setFont(self.font)
        painter.setPen(QPen(QColor(self._font_color)))
        painter.drawText(rect, Qt.AlignCenter, self._name)

        rect = self.rect()
        rect.setBottom(self.height() / 2)
        painter.setFont(self._display_font if self._differ_font_size else self.font)
        painter.setPen(QPen(QColor(self._fg_color)))
        painter.drawText(rect, Qt.AlignCenter, self._display)
