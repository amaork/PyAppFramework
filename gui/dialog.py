# -*- coding: utf-8 -*-

from PySide.QtGui import *
from PySide.QtCore import *
from .button import RectButton


__all__ = ['SimpleColorDialog']


class SimpleColorDialog(QDialog):
    def __init__(self, same=False, parent=None):
        """Simple color dialog

        :param same: if same is true, only allow red, greed, blue, cyan, yellow, magenta, black, white color
        :param parent:
        :return:
        """
        super(SimpleColorDialog, self).__init__(parent)

        self.__initUi()
        self.__color = ""
        self.__same = same
        self.__selected = False
        self.__updateColor(QColor(Qt.red))

    def __initUi(self):
        # Color select buttons
        colorLayout = QHBoxLayout()
        colorLayout.addWidget(QLabel(self.tr("颜色")))
        for color in (Qt.black, Qt.red, Qt.blue, Qt.magenta, Qt.yellow, Qt.green, Qt.cyan, Qt.white):
            button = RectButton(32, 24, color=(color, color))
            button.clicked.connect(self.slotChangeColor)
            colorLayout.addWidget(button)

        # Color depth slider
        depthLayout = QHBoxLayout()
        self.__depth = QSlider(Qt.Horizontal)
        self.__depth.setRange(0, 255)
        self.__depth.setTickInterval(10)
        self.__depth.setTickPosition(QSlider.TicksBelow)
        self.__depth.valueChanged.connect(self.slotChangeDepth)
        depthLayout.addWidget(QLabel(self.tr("亮度")))
        depthLayout.addWidget(self.__depth)

        # Label for preview color
        self.__preview = QLabel()

        # Color value spinbox
        self.__red = QSpinBox()
        self.__green = QSpinBox()
        self.__blue = QSpinBox()
        valueLayout = QHBoxLayout()
        for text, spinbox in (("Red", self.__red), ("Green", self.__green), ("Blue", self.__blue)):
            valueLayout.addWidget(QLabel(text))
            valueLayout.addWidget(spinbox)
            spinbox.setRange(0, 255)
            spinbox.valueChanged.connect(self.slotChangeDepth)
            if text != "Blue":
                valueLayout.addWidget(QSplitter())

        # Dialog button
        self.__ok = QPushButton(self.tr("确定"))
        self.__ok.clicked.connect(self.slotClose)
        self.__cancel = QPushButton(self.tr("取消"))
        self.__cancel.clicked.connect(self.slotClose)
        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(QSplitter())
        buttonLayout.addWidget(self.__ok)
        buttonLayout.addWidget(self.__cancel)

        layout = QVBoxLayout()
        layout.addLayout(colorLayout)
        layout.addLayout(depthLayout)
        layout.addWidget(self.__preview)
        layout.addLayout(valueLayout)
        layout.addWidget(QSplitter())
        layout.addWidget(QSplitter())
        layout.addLayout(buttonLayout)

        self.setLayout(layout)
        self.setWindowTitle(self.tr("请选择颜色"))

    def __getColor(self):
        return self.__color.red(), self.__color.green(), self.__color.blue()

    def __setColor(self, color):
        if not isinstance(color, QColor):
            return False

        self.__color = color
        self.__red.setValue(color.red())
        self.__blue.setValue(color.blue())
        self.__green.setValue(color.green())
        return True

    def __getCurrentColor(self):
        r = self.__red.value()
        b = self.__blue.value()
        g = self.__green.value()
        return r, g, b

    def __updateColor(self, color):
        if not isinstance(color, QColor):
            return

        self.__setColor(color)
        self.__depth.setValue(255)
        if self.__same:
            r, g, b = self.__getColor()
            self.__red.setEnabled(r)
            self.__blue.setEnabled(b)
            self.__green.setEnabled(g)

    def slotClose(self):
        self.__selected = self.sender() == self.__ok
        self.close()

    def slotChangeColor(self):
        btn = self.sender()
        if not isinstance(btn, RectButton):
            return

        self.__updateColor(btn.getBrush().color())

    def slotChangeDepth(self, value):
        if self.__same or self.sender() == self.__depth:
            r, g, b = self.__getColor()
            if r:
                self.__red.setValue(value)

            if g:
                self.__green.setValue(value)

            if b:
                self.__blue.setValue(value)

        r, g, b = self.__getCurrentColor()
        self.__preview.setStyleSheet("background:rgb({0:d},{1:d},{2:d})".format(r, g, b))

    def getSelectColor(self):
        if self.__selected:
            r, g, b = self.__getCurrentColor()
            return QColor(r, g, b)
        else:
            return QColor(Qt.black)

    @staticmethod
    def getColor(parent):
        panel = SimpleColorDialog(parent=parent)
        panel.exec_()
        return panel.getSelectColor()

    @staticmethod
    def getSameColor(parent):
        panel = SimpleColorDialog(True, parent)
        panel.exec_()
        return panel.getSelectColor()

    @staticmethod
    def convertToIndexColor(color):
        if not isinstance(color, QColor):
            return 0, 0

        index = 0
        r = color.red()
        g = color.green()
        b = color.blue()

        if r:
            index |= 4

        if g:
            index |= 2

        if b:
            index |= 1

        return index, max(r, g, b)
