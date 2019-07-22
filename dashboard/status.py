# -*- coding: utf-8 -*-
from PySide.QtGui import *
from PySide.QtCore import *
__all__ = ['DashboardStatusIcon']


class DashboardStatusIcon(QLabel):
    DEF_FONT = QFont("Vrinda", 15)
    DEF_FG_COLOR = QColor(14, 11, 54)
    DEF_BG_COLOR = QColor(Qt.white)
    DEF_FONT_COLOR = QColor(240, 240, 240)

    def __init__(self, parent, name, status, tips="", size=QSize(64, 64)):
        super(DashboardStatusIcon, self).__init__(parent)
        if not isinstance(name, str):
            raise TypeError("name require a str")

        if not isinstance(size, QSize):
            raise TypeError("size require a QSize")

        if not isinstance(status, (list, tuple)) or len(status) == 0:
            raise TypeError("states require a list or tuple")

        self._name = name
        self._current = 0
        self._status = status
        self._font = self.DEF_FONT
        self._bg_color = self.DEF_BG_COLOR
        self._fg_color = self.DEF_FG_COLOR
        self._font_color = self.DEF_FONT_COLOR
        self.setFixedSize(size)
        self.setToolTip(tips)

    @property
    def font(self):
        return self._font

    @font.setter
    def font(self, font):
        if isinstance(font, QFont):
            self._font = font
            self.update()

    @property
    def bg_color(self):
        return self._bg_color

    @property
    def fg_color(self):
        return self._fg_color

    @bg_color.setter
    def bg_color(self, color):
        if isinstance(color, (QColor, Qt.GlobalColor)):
            self._bg_color = color
            self.update()

    @fg_color.setter
    def fg_color(self, color):
        if isinstance(color, (QColor, Qt.GlobalColor)):
            self._fg_color = color
            self.update()

    @property
    def font_color(self):
        return self._font_color

    @font_color.setter
    def font_color(self, color):
        if isinstance(color, (QColor, Qt.GlobalColor)):
            self._font_color = color
            self.update()

    def reset(self):
        self._current = 0
        self.update()

    def status(self):
        return self._status[self._current]

    def switchStatus(self):
        self._current += 1
        self._current %= len(self._status)
        self.update()

    def changeStatus(self, st):
        if st in self._status:
            self._current = self._status.index(st)
            self.update()

    def paintEvent(self, ev):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        x_radius = self.width() / 10
        y_radius = self.height() / 10

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
        painter.setFont(self._font)
        painter.setPen(QPen(QColor(self._font_color)))
        painter.drawText(rect, Qt.AlignCenter, self._name)

        rect = self.rect()
        rect.setBottom(self.height() / 2)
        painter.setFont(self._font)
        painter.setPen(QPen(QColor(self._fg_color)))
        painter.drawText(rect, Qt.AlignCenter, self._status[self._current])



