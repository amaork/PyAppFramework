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
import typing
import os.path
from PySide2.QtWidgets import QPushButton, QWidget
from PySide2.QtCore import Signal, Qt, QSize, QRect
from typing import Optional, Union, Tuple, Sequence
from PySide2.QtGui import QKeySequence, QImageReader, QPixmap, QPainter, QFont, QColor, QBrush, QPen, QPaintEvent
__all__ = ['TextButton', 'IconButton', 'RectButton', 'RoundButton', 'StateButton']
StateColor = typing.Union[Qt.GlobalColor, QColor]


class BaseButton(QPushButton):
    def __init__(self, width: int = 0, height: int = 0, shortCut: str = "",
                 styleSheet: str = "", tips: str = "", parent: Optional[QWidget] = None):
        super(BaseButton, self).__init__(parent)
        if isinstance(shortCut, str) and len(shortCut):
            self.setShortcut(QKeySequence(self.tr(shortCut)))

        if isinstance(styleSheet, str) and len(styleSheet):
            self.setStyleSheet(styleSheet)

        if isinstance(width, int) and isinstance(height, int):
            self.setMinimumSize(width, height)

        self.setToolTip(tips)
        self.setStatusTip(tips)

    def getState(self) -> bool:
        return self.isChecked() if self.isCheckable() else False

    def slotChangeView(self, ck: bool):
        """Change button view

        :param ck:
        :return:
        """
        self.setChecked(ck)
        self.update()


class TextButton(BaseButton):
    def __init__(self, width: int = 0, height: int = 0, text: Tuple[str, str] = ("", ""),
                 shortCut: str = "", styleSheet: str = "", tips: str = "", parent: Optional[QWidget] = None):
        super(TextButton, self).__init__(width, height, shortCut, styleSheet, tips, parent)
        self.setCheckable(True)
        self.toggled.connect(self.slotChangeView)

        self.text = ("", "")
        if isinstance(text, (tuple, list)) and len(text) == 2:
            self.text = text
            self.setText(self.tr(text[0]))

    def slotChangeView(self, ck: bool):
        """When button is clicked, change button text

        :param ck: Button clicked
        :return:
        """
        self.setChecked(ck)
        self.setText(self.tr(self.text[ck]))


class IconButton(BaseButton):
    def __init__(self, icons: Sequence[str], shortCut: str = "", tips: str = "", parent: Optional[QWidget] = None):
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

    def paintEvent(self, ev: QPaintEvent):
        pixmap = QPixmap()
        painter = QPainter(self)
        idx = self.isChecked()

        if self.iconSize != QSize(-1, -1):
            # noinspection PyTypeChecker
            pixmap.loadFromData(self.iconData[idx])
            painter.drawPixmap(self.rect(), pixmap)


class RectButton(BaseButton):
    def __init__(self, width: int = 0, height: int = 0, text: Tuple[str, str] = ("", ""), shortCut: str = "",
                 color: Sequence[Union[Qt.GlobalColor, QColor]] = (Qt.red, Qt.green),
                 tips: str = "", width_factor: float = 0.618, parent: Optional[QWidget] = None):
        super(RectButton, self).__init__(width, height, shortCut, tips=tips, parent=parent)
        self.setCheckable(True)

        # Default setting
        self.text = ("", "")
        self.drawColor = (Qt.red, Qt.green)
        self.width_factor = width_factor or 0.618
        self.textColor = self.drawColor[1], self.drawColor[0]

        self.setText(text)
        self.setColor(color)
        self.textLength = max(len(self.text[0]), len(self.text[1]), 1)

    def draw(self, painter: QPainter, rect: QRect):
        painter.setPen(self.textColor[self.getState()])
        painter.setFont(
            QFont("Times New Roman", min(rect.width() / self.textLength / self.width_factor, rect.height() * 0.618))
        )
        painter.drawText(rect, Qt.AlignCenter, self.tr(self.text[self.getState()]))

    def setText(self, text: Sequence[str]):
        if not isinstance(text, (list, tuple)) or len(text) != 2:
            return False

        if not isinstance(text[0], str) or not isinstance(text[1], str):
            return False

        self.text = text
        self.update()
        return True

    def setColor(self, colors: Sequence[Union[Qt.GlobalColor, QColor]]):
        if not isinstance(colors, (list, tuple)) or len(colors) != 2:
            return False

        if not isinstance(colors[0], (QColor, Qt.GlobalColor)) or not isinstance(colors[1], (QColor, Qt.GlobalColor)):
            return False

        self.drawColor = colors
        self.textColor = self.drawColor[1], self.drawColor[0]
        self.update()

    def getBrush(self) -> QBrush:
        return QBrush(self.drawColor[self.getState()], Qt.SolidPattern)

    def paintEvent(self, ev: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()

        # Draw background
        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(self.getBrush())
        painter.drawRect(rect)

        # Draw text
        self.draw(painter, rect)


class RoundButton(RectButton):
    def __init__(self, diameter: int = 0, text: Tuple[str, str] = ("", ""),
                 shortCut: str = "", color: Sequence[Union[Qt.GlobalColor, QColor]] = (Qt.red, Qt.green),
                 tips: str = "", width_factor: float = 0.618, parent: Optional[QWidget] = None):
        super(RoundButton, self).__init__(diameter, diameter, text, shortCut, color, tips, width_factor, parent)

    def paintEvent(self, ev: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
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

    def __init__(self, diameter: int = 0, text: Tuple[str, str] = ("", ""),
                 shortCut: str = "", color: Sequence[Union[Qt.GlobalColor, QColor]] = (Qt.red, Qt.green),
                 tips: str = "", width_factor: float = 0.618, parent: Optional[QWidget] = None):
        super(StateButton, self).__init__(diameter, text, shortCut, color, tips, width_factor, parent)
        self.setCheckable(False)

        # Internal state
        self.state = False
        self.toggled.connect(self.slotChangeView)

    def toggle(self):
        self.toggled.emit(not self.state)

    def getState(self) -> bool:
        return self.state

    def setState(self, st: bool):
        self.state = True if st else False
        self.update()

    def turnOn(self):
        self.state = True
        self.stateChanged.emit(True)
        self.update()

    def turnOff(self):
        self.state = False
        self.stateChanged.emit(False)
        self.update()

    def slotChangeView(self, ck: bool):
        if ck:
            self.turnOn()
        else:
            self.turnOff()
