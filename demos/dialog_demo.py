# -*- coding: utf-8 -*-
import sys
import hashlib
from ..gui.dialog import *
from ..misc.settings import UiInputSetting
from ..gui.container import ComponentManager
from PySide2.QtWidgets import QApplication, QPushButton, QSpinBox, QLabel, QHBoxLayout, QVBoxLayout, QWidget, QLineEdit


class DialogTest(QWidget):
    def __init__(self, parent=None):
        super(DialogTest, self).__init__(parent)

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
        self.ui_serial_settings = QLineEdit()
        self.ui_get_serial = QPushButton(self.tr("获取串口设置"))
        serial.addWidget(self.ui_get_serial)
        serial.addWidget(self.ui_serial_settings)

        json = QHBoxLayout()
        self.ui_json_settings = QLineEdit()
        self.ui_get_json = QPushButton(self.tr("获取 JSON 设置"))
        json.addWidget(self.ui_get_json)
        json.addWidget(self.ui_json_settings)

        interface = QHBoxLayout()
        self.ui_interface = QLineEdit()
        self.ui_get_interface = QPushButton(self.tr("获取网卡"))
        interface.addWidget(self.ui_get_interface)
        interface.addWidget(self.ui_interface)

        network = QHBoxLayout()
        self.ui_network = QLineEdit()
        self.ui_get_network = QPushButton(self.tr("获取网络"))
        network.addWidget(self.ui_get_network)
        network.addWidget(self.ui_network)

        address = QHBoxLayout()
        self.ui_address = QLineEdit()
        self.ui_get_address = QPushButton(self.tr("获取地址"))
        address.addWidget(self.ui_get_address)
        address.addWidget(self.ui_address)

        reset_password = QHBoxLayout()
        self.ui_reset_new_password = QLineEdit()
        self.ui_reset_password = QPushButton(self.tr("重置密码"))
        reset_password.addWidget(self.ui_reset_password)
        reset_password.addWidget(self.ui_reset_new_password)

        change_password = QHBoxLayout()
        self.ui_new_password = QLineEdit()
        self.ui_change_password = QPushButton(self.tr("更改密码"))
        change_password.addWidget(self.ui_change_password)
        change_password.addWidget(self.ui_new_password)

        layout = QVBoxLayout()
        layout.addLayout(same)
        layout.addLayout(diff)
        layout.addLayout(json)
        layout.addLayout(serial)
        layout.addLayout(interface)
        layout.addLayout(network)
        layout.addLayout(address)
        layout.addLayout(reset_password)
        layout.addLayout(change_password)
        self.setLayout(layout)
        self.setWindowTitle(self.tr("选择颜色"))
        self.setFixedSize(self.sizeHint())

    def __initSignalAndSlots(self):
        self.__same.clicked.connect(self.__slotSelectSameColor)
        self.__diff.clicked.connect(self.__slotSelectDiffColor)
        self.ui_get_json.clicked.connect(self.__slotGetJsonSettings)
        self.ui_get_serial.clicked.connect(self.__slotGetSerialSetting)
        self.ui_reset_password.clicked.connect(self.__slotResetPassword)
        self.ui_change_password.clicked.connect(self.__slotChangePassword)

        self.ui_get_network.clicked.connect(lambda: self.ui_network.setText("{}".format(
            NetworkInterfaceSelectDialog.getInterfaceNetwork(parent=self)
        )))

        self.ui_get_address.clicked.connect(lambda: self.ui_address.setText("{}".format(
            NetworkInterfaceSelectDialog.getAddress(parent=self)
        )))

        self.ui_get_interface.clicked.connect(lambda: self.ui_interface.setText("{}".format(
            NetworkInterfaceSelectDialog.getInterface()
        )))

    def __slotResetPassword(self):
        self.ui_reset_new_password.setText("{}".format(PasswordDialog.resetPassword(
            hash_function=lambda x: hashlib.sha256(x).hexdigest(),
            parent=self
        )))

    def __slotChangePassword(self):
        old_password = hashlib.md5(b"123456789").hexdigest()
        self.ui_new_password.setText("{}".format(PasswordDialog.changePassword(old_password, parent=self)))

    def __slotGetSerialSetting(self):
        self.ui_serial_settings.setText("{}".format(SerialPortSettingDialog.getSetting(self)))

    def __slotGetJsonSettings(self):
        self.ui_json_settings.setText("{}".format(JsonSettingDialog.getData(UiInputSetting.getDemoSettings(True))))

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
    window = DialogTest()
    window.show()
    sys.exit(app.exec_())
