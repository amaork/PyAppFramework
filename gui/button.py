# -*- coding: utf-8 -*-

"""
Class Tree

BaseButton
    |------TextButton
    |------IconButton
    |------RectButton
                |------RoundButton
                            |------StateButton
"""
import types
import os.path
from PySide.QtCore import Signal, Qt, QSize
from PySide.QtGui import QPushButton, QKeySequence, QImageReader, QPixmap, QPainter, QFont, QColor, QBrush, QPen


__all__ = ['TextButton', 'IconButton', 'RectButton', 'RoundButton', 'StateButton']


class BaseButton(QPushButton):
    def __init__(self, width=0, height=0, shortCut="", styleSheet="", tips="", parent=None):
        super(BaseButton, self).__init__(parent)
        if isinstance(shortCut, types.StringTypes) and len(shortCut):
            self.setShortcut(QKeySequence(self.tr(shortCut)))

        if isinstance(styleSheet, types.StringTypes) and len(styleSheet):
            self.setStyleSheet(styleSheet)

        if isinstance(width, int) and isinstance(height, int):
            self.setMinimumSize(width, height)

        self.setToolTip(tips)
        self.setStatusTip(tips)

    def getState(self):
        return self.isChecked() if self.isCheckable() else False

    def slotChangeView(self, ck):
        """Change button view

        :param ck:
        :return:
        """
        self.setChecked(ck)
        self.update()


class TextButton(BaseButton):
    def __init__(self, width=0, height=0, text=("", ""), shortCut="", styleSheet="", tips="", parent=None):
        super(TextButton, self).__init__(width, height, shortCut, styleSheet, tips, parent)
        self.setCheckable(True)
        self.toggled.connect(self.slotChangeView)

        self.text = ("", "")
        if isinstance(text, (tuple, list)) and len(text) == 2:
            self.text = text
            self.setText(self.tr(text[0]))

    def slotChangeView(self, ck):
        """When button is clicked, change button text

        :param ck: Button clicked
        :return:
        """
        self.setChecked(ck)
        self.setText(self.tr(self.text[ck]))


class IconButton(BaseButton):
    def __init__(self, icons, shortCut="", tips="", parent=None):
        if not isinstance(icons, (list, tuple)):
            raise TypeError("icons require a list or tuple type")

        if len(icons) not in (1, 2):
            raise ValueError("icons require one or two icon path")

        super(IconButton, self).__init__(0, 0, shortCut, tips=tips, parent=parent)
        self.setCheckable(True)

        self.iconData = []
        self.iconSize = QSize(-1, -1)
        icons = (icons[0], icons[0]) if len(icons) == 1 else icons

        # Get icon size
        icon1 = QImageReader(icons[0])
        icon2 = QImageReader(icons[1])

        if icon1.size() == icon2.size() and icon1.size() != QSize(-1, -1):
            self.iconSize = icon1.size()
            self.setMinimumSize(self.iconSize)
            self.setMaximumSize(self.iconSize)

            # Load icon data to memory
            for i in range(len(icons)):
                if os.path.isfile(icons[i]):
                    with open(icons[i], "rb") as fp:
                        self.iconData.append(fp.read())
                else:
                    print("Icon size mismatched or icon is not a image!")

    def paintEvent(self, ev):
        pixmap = QPixmap()
        painter = QPainter(self)
        idx = self.isChecked()

        if self.iconSize != QSize(-1, -1):
            pixmap.loadFromData(self.iconData[idx])
            painter.drawPixmap(self.rect(), pixmap)


class RectButton(BaseButton):
    def __init__(self, width=0, height=0, text=("", ""), shortCut="", color=(Qt.red, Qt.green), tips="", parent=None):
        super(RectButton, self).__init__(width, height, shortCut, tips=tips, parent=parent)
        self.setCheckable(True)

        # Default setting
        self.text = ("", "")
        self.drawColor = (Qt.red, Qt.green)
        self.textColor = self.drawColor[1], self.drawColor[0]

        self.setText(text)
        self.setColor(color)
        self.textLength = max(len(self.text[0]), len(self.text[1]), 1)

    def draw(self, painter, rect):
        painter.setPen(self.textColor[self.getState()])
        painter.setFont(QFont("Times New Roman", min(rect.width() / self.textLength / 0.618, rect.height() * 0.618)))
        painter.drawText(rect, Qt.AlignCenter, self.tr(self.text[self.getState()]))

    def setText(self, text):
        if not isinstance(text, (list, tuple)) or len(text) != 2:
            return False

        if not isinstance(text[0], types.StringTypes) or not isinstance(text[1], types.StringTypes):
            return False

        self.text = text
        self.update()
        return True

    def setColor(self, colors):
        if not isinstance(colors, (list, tuple)) or len(colors) != 2:
            return False

        if not isinstance(colors[0], (QColor, Qt.GlobalColor)) or not isinstance(colors[1], (QColor, Qt.GlobalColor)):
            return False

        self.drawColor = colors
        self.textColor = self.drawColor[1], self.drawColor[0]
        self.update()

    def getBrush(self):
        return QBrush(self.drawColor[self.getState()], Qt.SolidPattern)

    def paintEvent(self, ev):
        painter = QPainter(self)
        rect = self.rect()

        # Draw background
        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(self.getBrush())
        painter.drawRect(rect)

        # Draw text
        self.draw(painter, rect)


class RoundButton(RectButton):
    def __init__(self, diameter=0, text=("", ""), shortCut="", color=(Qt.red, Qt.green), tips="", parent=None):
        super(RoundButton, self).__init__(diameter, diameter, text, shortCut, color, tips, parent)

    def paintEvent(self, ev):
        painter = QPainter(self)
        rect = self.rect()

        # Draw background
        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(self.getBrush())
        width = min(self.size().width(), self.size().height())
        rect.setWidth(width)
        rect.setHeight(width)
        painter.drawEllipse(rect)

        # Draw text
        self.draw(painter, rect)


class StateButton(RoundButton):
    # Single when state changed
    stateChanged = Signal(bool)

    def __init__(self, diameter=0, text=("", ""), shortCut="", color=(Qt.red, Qt.green), tips="", parent=None):
        super(StateButton, self).__init__(diameter, text, shortCut, color, tips, parent)
        self.setCheckable(False)

        # Internal state
        self.state = False

    def getState(self):
        return self.state

    def turnOn(self):
        self.state = True
        self.stateChanged.emit(True)
        self.update()

    def turnOff(self):
        self.state = False
        self.stateChanged.emit(False)
        self.update()

    def slotChangeView(self, ck):
        if ck:
            self.turnOn()
        else:
            self.turnOff()
