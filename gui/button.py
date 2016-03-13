#!/usr/bin/python
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

from PySide.QtCore import *
from PySide.QtGui import *
import types
import sys
import os


__all__ = ['TextButton', 'IconButton', 'RectButton', 'RoundButton', 'StateButton']


class BaseButton(QPushButton):
    def __init__(self, width=0, height=0, shortCut="", styleSheet="", parent=None):
        super(BaseButton, self).__init__(parent)
        if isinstance(shortCut, types.StringTypes) and len(shortCut):
            self.setShortcut(QKeySequence(self.tr(shortCut)))

        if isinstance(styleSheet, types.StringTypes) and len(styleSheet):
            self.setStyleSheet(styleSheet)

        if isinstance(width, int) and isinstance(height, int):
            self.setMinimumSize(width, height)

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
    def __init__(self, width=0, height=0, text=("", ""), shortCut="", styleSheet="", parent=None):
        super(TextButton, self).__init__(width, height, shortCut, styleSheet, parent)
        self.setCheckable(True)
        self.toggled.connect(self.slotChangeView)

        self.text = ("", "")
        if isinstance(text, tuple) and len(text) == 2:
            self.text = text
            self.setText(self.tr(text[0]))

    def slotChangeView(self, ck):
        """When button is clicked, change button text

        :return:
        """
        self.setChecked(ck)
        self.setText(self.tr(self.text[ck]))


class IconButton(BaseButton):
    def __init__(self, width=0, height=0, icon=("", ""), shortCut="", parent=None):
        super(IconButton, self).__init__(width, height, shortCut, parent=parent)
        self.setCheckable(True)

        self.iconData = []
        self.iconSize = QSize(-1, -1)

        if isinstance(icon, tuple) and len(icon) == 2:
            # Get icon size
            icon1 = QImageReader(icon[0])
            icon2 = QImageReader(icon[1])

            if icon1.size() == icon2.size() and icon1.size() != QSize(-1, -1):
                self.iconSize = icon1.size()
                self.setMinimumSize(self.iconSize)
                self.setMaximumSize(self.iconSize)

                # Load icon data to memory
                for i in range(len(icon)):
                    if os.path.isfile(icon[i]):
                        with open(icon[i], "rb") as fp:
                            self.iconData.append(fp.read())
            else:
                print "Icon size mismatched or icon is not a image!"

    def paintEvent(self, ev):
        pixmap = QPixmap()
        painter = QPainter(self)
        idx = self.isChecked()

        if self.iconSize != QSize(-1, -1):
            pixmap.loadFromData(self.iconData[idx])
            painter.drawPixmap(self.rect(), pixmap)


class RectButton(BaseButton):
    def __init__(self, width=0, height=0, text=("", ""), shortCut="", color=(Qt.red, Qt.green), parent=None):
        super(RectButton, self).__init__(width, height, shortCut, parent=parent)
        self.setCheckable(True)

        # Default setting
        self.text = ("", "")
        self.drawColor = (Qt.red, Qt.green)
        self.textColor = self.drawColor[1], self.drawColor[0]

        if isinstance(text, tuple) and len(text) == 2:
            self.text = text

        if isinstance(color, tuple) and len(color) == 2:
            self.drawColor = color
            self.textColor = self.drawColor[1], self.drawColor[0]

        self.textLength = max(len(self.text[0]), len(self.text[1]), 1)

    def draw(self, painter, rect):
        painter.setPen(self.textColor[self.getState()])
        painter.setFont(QFont("Times New Roman", min(rect.width() / self.textLength / 0.618, rect.height() * 0.618)))
        painter.drawText(rect, Qt.AlignCenter, self.tr(self.text[self.getState()]))

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
    def __init__(self, diameter=0, text=("", ""), shortCut="", color=(Qt.red, Qt.green), parent=None):
        super(RoundButton, self).__init__(diameter, diameter, text, shortCut, color, parent)

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

    def __init__(self, diameter=0, text=("", ""), shortCut="", color=(Qt.red, Qt.green), parent=None):
        super(StateButton, self).__init__(diameter, text, shortCut, color, parent)
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

class DemoWidget(QWidget):
    def __init__(self, parent=None):
        super(DemoWidget, self).__init__(parent)
        self.buttonType = [TextButton, RectButton, RoundButton]
        self.buttonList = ["TextButton", "RectButton", "RoundButton", "IconButton"]

        self.addButton = QPushButton("Add a button")
        self.buttonSelect = QComboBox()
        self.buttonSelect.addItems(self.buttonList)
        self.addButton.clicked.connect(self.slotAddButton)

        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("Button type"))
        h_layout.addWidget(self.buttonSelect)
        h_layout.addWidget(self.addButton)

        self.g_layout = QGridLayout()
        layout = QVBoxLayout()
        layout.addLayout(h_layout)
        layout.addLayout(self.g_layout)

        self.setLayout(layout)

    def slotAddButton(self):
        buttonText = self.buttonSelect.currentText().encode("ascii")
        typeIndex = self.buttonList.index(buttonText)
        buttonTextGroup = ("{0:s} ON".format(buttonText), "{0:s} OFF".format(buttonText))

        state = StateButton(50)
        if buttonText == "RoundButton":
            button = RoundButton(200, text=buttonTextGroup)
        elif buttonText == "IconButton":
            files, _ = QFileDialog.getOpenFileNames(self, "Select icon images", "", "All Files (*)")
            if len(files) == 2:
                button = IconButton(icon=(files[0], files[1]))
        else:
            button = self.buttonType[typeIndex](200, 50, text=buttonTextGroup)

        button.toggled.connect(state.slotChangeView)
        self.g_layout.addWidget(QLabel(buttonText), typeIndex, 0)
        self.g_layout.addWidget(button, typeIndex, 1)
        self.g_layout.addWidget(state, typeIndex, 2)

        self.buttonSelect.removeItem(self.buttonSelect.currentIndex())
        if self.buttonSelect.count() == 0:
            self.addButton.setDisabled(True)
            self.buttonSelect.setDisabled(True)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    QTextCodec.setCodecForTr(QTextCodec.codecForName("UTF-8"))
    widget = DemoWidget()
    widget.show()
    sys.exit(app.exec_())
