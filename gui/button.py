#!/usr/bin/python
# -*- coding: utf-8 -*-
from PySide.QtCore import *
from PySide.QtGui import *
import sys
import os


class BaseButton(QPushButton):
    def __init__(self, width, height, turnOn=False, shortCut=""):
        super(BaseButton, self).__init__()
        self.on = turnOn
        self.setCheckable(True)
        self.setChecked(turnOn)
        self.setMinimumSize(width, height)
        self.setShortcut(QKeySequence(self.tr(shortCut)))

    def turnOn(self):
        self.on = True
        self.setChecked(True)
        self.update()

    def turnOff(self):
        self.on = False
        self.setChecked(False)

    @Slot(int)
    def control(self, ck):
        if ck:
            self.turnOn()
        else:
            self.turnOff()

        self.update()


class TextButton(BaseButton):
    def __init__(self, width, height, turnOn=False, text=("", ""), shortCut=""):
        super(TextButton, self).__init__(width, height, turnOn, shortCut)
        self.text = text
        self.drawColor = (Qt.red, Qt.green)
        self.textColor = (Qt.white, Qt.black)
        self.textLength = max(len(self.text[0]), len(self.text[1]), 1)

    def drawText(self, painter, rect):
        painter.setPen(self.textColor[self.getState()])
        painter.setFont(QFont("Arial", min(rect.width() / self.textLength / 0.618, rect.height() * 0.618)))
        painter.drawText(rect, Qt.AlignCenter, self.tr(self.text[self.getState()]))

    def getBrush(self):
        return QBrush(self.drawColor[self.getState()], Qt.SolidPattern)

    def getState(self):
        return self.isChecked() if self.isCheckable() else self.on


class RectButton(TextButton):
    def __init__(self, width, height, turnOn=False, text=("", ""), shortCut=""):
        super(RectButton, self).__init__(width, height, turnOn, text, shortCut)

    def paintEvent(self, ev):
        painter = QPainter(self)
        rect = self.rect()

        # Draw background
        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(self.getBrush())
        painter.drawRect(rect)

        # Draw text
        self.drawText(painter, rect)


class RoundButton(TextButton):
    def __init__(self, dia, turnOn=False, text=("", ""), shortCut=""):
        super(RoundButton, self).__init__(dia, dia, turnOn, text, shortCut)

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
        self.drawText(painter, rect)


class IconButton(BaseButton):
    __supportFormat = ["jpg", "jpeg", "png", "bmp"]

    def __init__(self, width, height, turnOn=False, icon=("", ""), shortCut=""):
        super(IconButton, self).__init__(width, height, turnOn, shortCut)

        self.icon = icon
        self.width = width
        self.height = height
        self.iconData = []
        self.iconFormat = [fname.split(".")[-1] for fname in icon]

        # Load icon data to memory
        if isinstance(icon, tuple) and len(icon) == 2:
            for i in range(len(icon)):
                if os.path.isfile(icon[i]) and self.iconFormat[i] in self.__supportFormat:
                    with open(icon[i], "rb") as fp:
                        data = fp.read(os.path.getsize(icon[i]))
                        self.iconData.append(data)

    def paintEvent(self, ev):
        pixmap = QPixmap()
        painter = QPainter(self)
        idx = self.isChecked()

        if len(self.iconData) == 2 and len(self.iconData[idx]):
            pixmap.loadFromData(self.iconData[idx], self.iconFormat[idx])
            painter.drawPixmap(self.rect(), pixmap)


class LedButton(RoundButton):
    def __init__(self, dia, turnOn=False, text=("", ""), shortCut=""):
        super(LedButton, self).__init__(dia, turnOn, text, shortCut)
        self.setCheckable(False)


class RectLedButton(RectButton):
    def __init__(self, width, height, turnOn=False, text=("", ""), shortCut=""):
        super(RectLedButton, self).__init__(width, height, turnOn, text, shortCut)
        self.setCheckable(False)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    QTextCodec.setCodecForTr(QTextCodec.codecForName("UTF-8"))
    widget = QWidget()
    widget.setMinimumSize(400, 120)
    widget.setMaximumSize(400, 150)

    # Button
    rButton = RectButton(50, 50, False, ["R", "R"])
    gButton = RectButton(50, 50, False, ["G", "G"])
    bButton = RectButton(50, 50, False, ["B", "B"])
    signalButton = RectButton(200, 50, False, ["Signal", "Signal"])
    buttonGroup = (signalButton, rButton, gButton, bButton)

    # Led
    rLed = LedButton(50, False, ["R", "R"])
    gLed = LedButton(50, False, ["G", "G"])
    bLed = LedButton(50, False, ["B", "B"])
    signalLed = RectLedButton(200, 50, False, ["Signal", "Signal"])
    ledGroup = (signalLed, rLed, gLed, bLed)

    # Layout
    layout = QVBoxLayout()
    ledLayout = QHBoxLayout()
    buttonLayout = QHBoxLayout()

    for button, led in zip(buttonGroup, ledGroup):
        ledLayout.addWidget(led)
        buttonLayout.addWidget(button)
        button.toggled.connect(led.control)

    layout.addLayout(buttonLayout)
    layout.addLayout(ledLayout)
    widget.setLayout(layout)

    widget.show()
    app.exec_()
