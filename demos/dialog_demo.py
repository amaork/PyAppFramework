# -*- coding: utf-8 -*-
import sys
from PySide.QtCore import QTextCodec
from ..gui.container import ComponentManager
from ..gui.dialog import SimpleColorDialog, SerialPortSettingDialog
from PySide.QtGui import QApplication, QPushButton, QSpinBox, QLabel, QHBoxLayout, QVBoxLayout, QWidget, QLineEdit


class ColorDialogTest(QWidget):
    def __init__(self, parent=None):
        super(ColorDialogTest, self).__init__(parent)

        self.__initUi()
        self.__initSignalAndSlots()
        self.__uiManager = ComponentManager(self.layout())

    def __initUi(self):
        diff = QHBoxLayout()
        self.__diff = QPushButton(self.tr("获取颜色（RGB 不同）"))
        self.__diffColor = QLabel()
        self.__diffColor.setMinimumSize(32, 15)
        diff.addWidget(self.__diff)
        diff.addWidget(self.__diffColor)
        for color in ("r", "g", "b"):
            spinbox = QSpinBox()
            spinbox.setRange(0, 255)
            spinbox.setProperty("tag", color)
            diff.addWidget(QLabel(self.tr(color.upper())))
            diff.addWidget(spinbox)

        same = QHBoxLayout()
        self.__sameColor = QLabel()
        self.__sameColor.setMinimumSize(32, 15)
        self.__same = QPushButton(self.tr("获取颜色（RGB 相同）"))
        color = QSpinBox()
        color.setRange(0, 7)
        color.setProperty("tag", "color")
        depth = QSpinBox()
        depth.setRange(0, 255)
        depth.setProperty("tag", "depth")
        same.addWidget(self.__same)
        same.addWidget(self.__sameColor)
        same.addWidget(QLabel(self.tr("Color")))
        same.addWidget(color)
        same.addWidget(QLabel(self.tr("Depth")))
        same.addWidget(depth)

        serial = QHBoxLayout()
        self.__setting = QLineEdit()
        self.__serial = QPushButton(self.tr("获取串口设置"))
        serial.addWidget(self.__serial)
        serial.addWidget(self.__setting)

        layout = QVBoxLayout()
        layout.addLayout(same)
        layout.addLayout(diff)
        layout.addLayout(serial)
        self.setLayout(layout)
        self.setWindowTitle(self.tr("选择颜色"))
        self.setFixedSize(self.sizeHint())

    def __initSignalAndSlots(self):
        self.__same.clicked.connect(self.__slotSelectSameColor)
        self.__diff.clicked.connect(self.__slotSelectDiffColor)
        self.__serial.clicked.connect(self.__slotGetSerialSetting)

    def __slotGetSerialSetting(self):
        self.__setting.setText("{}".format(SerialPortSettingDialog.getSetting(self)))

    def __slotSelectDiffColor(self):
        color = SimpleColorDialog.getColor(self)
        r = color.red()
        g = color.green()
        b = color.blue()
        self.__uiManager.setData("tag", {"r": r, "g": g, "b": b})
        self.__diffColor.setStyleSheet("background:rgb({0:d}, {1:d}, {2:d})".format(r, g, b))

    def __slotSelectSameColor(self):
        color = SimpleColorDialog.getBasicColor(self)
        r = color.red()
        g = color.green()
        b = color.blue()
        color, depth = SimpleColorDialog.convertToIndexColor(color)
        self.__uiManager.setData("tag", {"color": color, "depth": depth})
        self.__sameColor.setStyleSheet("background:rgb({0:d}, {1:d}, {2:d})".format(r, g, b))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    QTextCodec.setCodecForTr(QTextCodec.codecForName("UTF-8"))
    window = ColorDialogTest()
    window.show()
    sys.exit(app.exec_())
