# -*- coding: utf-8 -*-
import os
import hashlib
from PySide.QtGui import *
from PySide.QtCore import *
from .msgbox import *
from .button import RectButton
from ..network.utility import *
from ..misc.settings import UiLayout
from ..protocol.serialport import SerialPort
from ..misc.windpi import get_program_scale_factor
from .widget import SerialPortSettingWidget, BasicJsonSettingWidget, \
    JsonSettingWidget, MultiJsonSettingsWidget, MultiTabJsonSettingsWidget, MultiGroupJsonSettingsWidget

__all__ = ['SimpleColorDialog',
           'SerialPortSettingDialog',
           'ProgressDialog', 'PasswordDialog', 'OptionDialog',
           'SerialPortSelectDialog', 'NetworkAddressSelectDialog', 'NetworkInterfaceSelectDialog',
           'JsonSettingDialog', 'MultiJsonSettingsDialog', 'MultiTabJsonSettingsDialog', 'MultiGroupJsonSettingsDialog',
           'showFileImportDialog', 'showFileExportDialog']


class SimpleColorDialog(QDialog):
    # This signal is emitted just after the user has clicked OK to select a color to use
    colorSelected = Signal(QColor)
    # This signal is emitted just after the user selected a color
    currentColorChanged = Signal(QColor)

    def __init__(self, basic=False, color=Qt.black, button_box=False, parent=None):
        """Simple color dialog

        :param basic: if basic is true, only allow red, greed, blue, cyan, yellow, magenta, black, white color
        :param color: init color
        :param button_box: with or without ok cancel button box
        :param parent:
        :return:
        """
        super(SimpleColorDialog, self).__init__(parent)
        if not isinstance(color, (QColor, Qt.GlobalColor)):
            raise TypeError("color expect a 'QColor' or 'Qt.GlobalColor' not '{}'".format(color.__class__.__name__))

        self.__initUi(button_box)
        self.__basic = basic
        self.__color = QColor(color)
        self.__updateColor(self.__color)

    def __initUi(self, without_buttons):
        # Color select buttons
        colorLayout = QGridLayout()
        colors = (Qt.black, Qt.red, Qt.blue, Qt.magenta, Qt.yellow, Qt.green, Qt.cyan, Qt.white)
        for row, depth in enumerate((255, 127, 64)):
            colorLayout.addWidget(QLabel("{0:d}".format(depth)), row, 0)
            for column, color in enumerate(colors):
                c = QColor(color)
                r, g, b = (depth if x else x for x in self.convertToRgb(c))
                c = QColor(r, g, b)
                button = RectButton(32, 24, color=(c, c))
                button.clicked.connect(self.slotChangeColor)
                colorLayout.addWidget(button, row, column + 1)

        # Color depth slider
        depthLayout = QHBoxLayout()
        self.__depth = QSlider(Qt.Horizontal)
        self.__depth.setRange(0, 255)
        self.__depth.setTickInterval(10)
        self.__depth.setTickPosition(QSlider.TicksBelow)
        self.__depth.valueChanged.connect(self.slotChangeDepth)
        depthLayout.addWidget(QLabel(self.tr("Luminance")))
        depthLayout.addWidget(self.__depth)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # Label for preview color
        self.__preview = QLabel()

        # Color value spinbox
        self.__red = QSpinBox()
        self.__green = QSpinBox()
        self.__blue = QSpinBox()
        valueLayout = QHBoxLayout()
        for text, spinbox in (
                (self.tr("Red"), self.__red), (self.tr("Green"), self.__green), (self.tr("Blue"), self.__blue)
        ):
            valueLayout.addWidget(QLabel(text))
            valueLayout.addWidget(spinbox)
            spinbox.setRange(0, 255)
            spinbox.valueChanged.connect(self.slotChangeDepth)
            if spinbox != self.__blue:
                valueLayout.addWidget(QSplitter())

        # Dialog button
        layout = QVBoxLayout()
        layout.addLayout(colorLayout)
        layout.addLayout(depthLayout)
        layout.addWidget(self.__preview)
        layout.addLayout(valueLayout)
        layout.addWidget(QSplitter())
        layout.addWidget(QSplitter())
        if not without_buttons:
            button = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            button.accepted.connect(self.accept)
            button.rejected.connect(self.reject)
            layout.addWidget(button)

        self.setLayout(layout)
        self.setWindowTitle(self.tr("Please select color"))

    def __getColor(self):
        """Get select color setting

        :return: r, g, b
        """
        return self.__color.red(), self.__color.green(), self.__color.blue()

    def __setColor(self, color):
        """Save color and update spinbox color

        :param color: select color
        :return: true or false
        """
        if not isinstance(color, QColor):
            return False

        self.__color = color
        self.__red.setValue(color.red())
        self.__blue.setValue(color.blue())
        self.__green.setValue(color.green())
        return True

    def __getCurrentColor(self):
        """Get ui spinbox color setting

        :return: r, g, b
        """
        r = self.__red.value()
        b = self.__blue.value()
        g = self.__green.value()
        return r, g, b

    def __updateColor(self, color):
        """Update ui elements setting

        :param color:
        :return:
        """
        if not isinstance(color, QColor):
            return

        self.__setColor(color)
        value = max(self.convertToRgb(color))
        self.slotChangeDepth(value)
        self.__depth.setValue(value)

        # Basic mode
        if self.__basic:
            r, g, b = self.__getColor()
            self.__red.setEnabled(r)
            self.__blue.setEnabled(b)
            self.__green.setEnabled(g)

    def slotChangeColor(self):
        btn = self.sender()
        if not isinstance(btn, RectButton):
            return

        # Update select color
        color = btn.getBrush().color()
        self.__updateColor(color)
        self.currentColorChanged.emit(color)

    def slotChangeDepth(self, value):
        if self.__basic or self.sender() == self.__depth:
            r, g, b = self.__getColor()
            if r:
                self.__red.setValue(value)

            if g:
                self.__green.setValue(value)

            if b:
                self.__blue.setValue(value)

        if self.__basic:
            self.__depth.setValue(value)
        r, g, b = self.__getCurrentColor()
        self.currentColorChanged.emit(QColor(r, g, b))
        self.__preview.setStyleSheet("background:rgb({0:d},{1:d},{2:d})".format(r, g, b))

    def getSelectColor(self):
        if self.result():
            r, g, b = self.__getCurrentColor()
            self.colorSelected.emit(QColor(r, g, b))
            return QColor(r, g, b)
        else:
            return self.__color

    @classmethod
    def getColor(cls, parent, color=Qt.red):
        panel = cls(color=color, parent=parent)
        panel.exec_()
        return panel.getSelectColor()

    @classmethod
    def getBasicColor(cls, parent, color=Qt.red):
        panel = cls(True, color, False, parent)
        panel.exec_()
        return panel.getSelectColor()

    @staticmethod
    def convertToRgb(color):
        if not isinstance(color, QColor):
            return 0, 0, 0

        return color.red(), color.green(), color.blue()

    @staticmethod
    def convertToIndexColor(color):
        if not isinstance(color, QColor):
            return 0, 0

        index = 0
        r, g, b = SimpleColorDialog.convertToRgb(color)

        if r:
            index |= 4

        if g:
            index |= 2

        if b:
            index |= 1

        return index, max(r, g, b)


class SerialPortSelectDialog(QDialog):
    def __init__(self, timeout=0.04, parent=None):
        super(SerialPortSelectDialog, self).__init__(parent)
        layout = QVBoxLayout()
        self._ports = QComboBox(self)
        self._ports.addItems(SerialPort.get_serial_list(timeout))
        button = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button.accepted.connect(self.accept)
        button.rejected.connect(self.reject)

        layout.addWidget(self._ports)
        layout.addWidget(QSplitter())
        layout.addWidget(button)
        self.setLayout(layout)
        self.setFixedSize(self.sizeHint())
        self.setWindowTitle(self.tr("Please select serial port"))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def getPort(self):
        return self._ports.currentText() if self.result() else None

    @classmethod
    def getSerialPort(cls, timeout=0.04, parent=None):
        dialog = cls(timeout, parent)
        dialog.exec_()
        return dialog.getPort()


class SerialPortSettingDialog(QDialog):
    def __init__(self, settings=SerialPortSettingWidget.DEFAULTS, parent=None):
        """Serial port configure dialog

        :param settings: serial port settings
        :param parent:
        """
        settings = settings or self.DEFAULTS
        super(SerialPortSettingDialog, self).__init__(parent)

        layout = QVBoxLayout()
        self.__widget = SerialPortSettingWidget(settings)
        button = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button.accepted.connect(self.accept)
        button.rejected.connect(self.reject)

        layout.addWidget(self.__widget)
        layout.addWidget(QSplitter())
        layout.addWidget(button)

        self.setLayout(layout)
        self.setFixedSize(self.sizeHint())
        self.setWindowTitle(self.tr("Serial Configuration Dialog"))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def getSerialSetting(self):
        if not self.result():
            return None

        return self.__widget.getSetting()

    @classmethod
    def getSetting(cls, parent, settings=SerialPortSettingWidget.DEFAULTS):
        dialog = cls(settings, parent)
        dialog.exec_()
        return dialog.getSerialSetting()


class NetworkAddressSelectDialog(QDialog):
    def __init__(self, port, timeout=0.04, parent=None):
        super(NetworkAddressSelectDialog, self).__init__(parent)
        layout = QVBoxLayout()
        self._address_list = QComboBox(self)
        self._address_list.addItems(scan_lan_port(port, timeout))
        button = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button.accepted.connect(self.accept)
        button.rejected.connect(self.reject)

        layout.addWidget(self._address_list)
        layout.addWidget(QSplitter())
        layout.addWidget(button)
        self.setLayout(layout)
        self.setFixedSize(self.sizeHint())
        self.setWindowTitle(self.tr("Please select address"))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def getSelectedAddress(self):
        return self._address_list.currentText() if self.result() else None

    @classmethod
    def getAddress(cls, port, timeout=0.04, parent=None):
        dialog = NetworkAddressSelectDialog(port, timeout, parent)
        dialog.exec_()
        return dialog.getSelectedAddress()


class NetworkInterfaceSelectDialog(QDialog):
    def __init__(self, name: str = "", address: str = "", network: str = "", ignore_loopback: bool = True, parent=None):
        super(NetworkInterfaceSelectDialog, self).__init__(parent)
        layout = QVBoxLayout()
        self._nic_list = QComboBox(self)
        button = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button.accepted.connect(self.accept)
        button.rejected.connect(self.reject)

        idx = 0
        for nic_name, nic_attr in get_system_nic(ignore_loopback).items():
            if name == nic_name or address == nic_attr.ip or network == nic_attr.network:
                idx = self._nic_list.count()
            self._nic_list.addItem("{}: {}".format(nic_name, nic_attr.ip), nic_attr.network)

        self._nic_list.setCurrentIndex(idx)

        layout.addWidget(self._nic_list)
        layout.addWidget(QSplitter())
        layout.addWidget(button)
        self.setLayout(layout)
        self.setFixedSize(self.sizeHint())
        self.setWindowTitle(self.tr("Please Select Network Interface"))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def getSelectedInterfaceAddress(self) -> str:
        return self._nic_list.currentText().split(":")[-1].strip() if self.result() else ""

    def getSelectedInterfaceNetwork(self) -> str:
        idx = self._nic_list.currentIndex()
        return self._nic_list.itemData(idx) if self.result() else ""

    def getSelectedNetworkInterface(self) -> str:
        return self._nic_list.currentText() if self.result() else ""

    @classmethod
    def getAddress(cls, name: str = "",
                   address: str = "", network: str = "",
                   ignore_loopback: bool = True, parent=None) -> str:
        dialog = NetworkInterfaceSelectDialog(name=name, address=address, network=network,
                                              ignore_loopback=ignore_loopback, parent=parent)
        dialog.exec_()
        return dialog.getSelectedInterfaceAddress()

    @classmethod
    def getInterface(cls, name: str = "",
                     address: str = "", network: str = "",
                     ignore_loopback: bool = True, parent=None) -> str:
        dialog = NetworkInterfaceSelectDialog(name=name, address=address, network=network,
                                              ignore_loopback=ignore_loopback, parent=parent)
        dialog.exec_()
        return dialog.getSelectedNetworkInterface()

    @classmethod
    def getInterfaceNetwork(cls, name: str = "",
                            address: str = "", network: str = "",
                            ignore_loopback: bool = True, parent=None) -> str:
        dialog = NetworkInterfaceSelectDialog(name=name, address=address, network=network,
                                              ignore_loopback=ignore_loopback, parent=parent)
        dialog.exec_()
        return dialog.getSelectedInterfaceNetwork()


class ProgressDialog(QProgressDialog):
    progressCanceled = Signal(bool)
    DEF_TITLE = QApplication.translate("ProgressDialog", "Operation progress", None, QApplication.UnicodeUTF8)

    def __init__(self, parent: QWidget, title: str = DEF_TITLE, max_width: int = 350,
                 cancel_button: str or None = None, closeable: bool = True, cancelable: bool = False):
        super(ProgressDialog, self).__init__(parent)

        self.__canceled = False
        self.__closeable = closeable
        self.__cancelable = cancelable
        self.setFixedWidth(max_width)
        self.setWindowModality(Qt.WindowModal)
        self.setWindowTitle(self.tr(title))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        if cancel_button is None:
            self.setCancelButton(None)
        else:
            self.setCancelButtonText(self.tr(cancel_button))

    def closeEvent(self, ev):
        if not self.__closeable and not self.__cancelable:
            ev.ignore()

        if self.__cancelable:
            if showQuestionBox(self, self.tr("Cancel") + self.windowTitle() + " ?"):
                self.setLabelText(self.tr("Canceling please wait..."))
                self.setCancelState(True)

            ev.ignore()

    def showEvent(self, ev):
        self.setCancelState(False)
        x = self.parent().geometry().x() + self.parent().width() / 2 - self.width() / 2
        y = self.parent().geometry().y() + self.parent().height() / 2 - self.height() / 2
        self.move(QPoint(x, y))

    @Slot()
    def slotHidden(self):
        self.setProgress(self.maximum())

    def isCanceled(self) -> bool:
        return self.__canceled if self.__cancelable else False

    def setCloseable(self, en: bool):
        self.__closeable = True if en else False

    def setCancelable(self, en: bool):
        self.__cancelable = True if en else False

    def setCancelState(self, st: bool):
        self.__canceled = True if st else False
        self.progressCanceled.emit(self.__canceled)

    def setLabelText(self, text: str):
        if self.isCanceled():
            return

        self.setWhatsThis(text)
        super(ProgressDialog, self).setLabelText(text)

    @Slot(int)
    def setProgress(self, value: int):
        self.setValue(value)
        if value != self.maximum():
            self.show()
        x = self.parent().geometry().x() + self.parent().width() / 2 - self.width() / 2
        y = self.parent().geometry().y() + self.parent().height() / 2 - self.height() / 2
        self.move(QPoint(x, y))


class BasicJsonSettingDialog(QDialog):
    def __init__(self, widget_cls, settings, data=None, reset=True, apply=None, parent=None):
        super(BasicJsonSettingDialog, self).__init__(parent)

        if not issubclass(widget_cls, (BasicJsonSettingWidget, MultiTabJsonSettingsWidget)):
            raise TypeError("widget_cls require {!r} or {!r} not {!r}".format(
                BasicJsonSettingWidget.__name__, MultiTabJsonSettingsWidget.__name__, widget_cls.__name__
            ))

        self.apply = apply if hasattr(apply, "__call__") else None
        dialog_buttons = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        dialog_buttons = dialog_buttons | QDialogButtonBox.Reset if reset else dialog_buttons
        dialog_buttons = dialog_buttons | QDialogButtonBox.Apply if self.apply else dialog_buttons

        layout = QVBoxLayout()
        self.ui_widget = widget_cls(settings, data, parent)
        self.ui_widget.settingChanged.connect(self.slotSettingChanged)

        self.ui_buttons = QDialogButtonBox(dialog_buttons)
        self.ui_buttons.accepted.connect(self.accept)
        self.ui_buttons.rejected.connect(self.reject)
        self.apply and self.ui_buttons.button(QDialogButtonBox.Apply).clicked.connect(self.applySetting)
        reset and self.ui_buttons.button(QDialogButtonBox.Reset).clicked.connect(self.ui_widget.resetDefaultData)

        layout.addWidget(self.ui_widget)
        layout.addWidget(QSplitter())
        layout.addWidget(self.ui_buttons)

        try:
            title = settings.layout.get_name() if isinstance(settings.layout, UiLayout) else settings.layout.get("name")
        except AttributeError:
            title = self.tr("Configuration Dialog")

        self.setLayout(layout)
        self.setWindowTitle(self.tr(title))
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def tr(self, text):
        return QApplication.translate("BasicJsonSettingDialog", text, None, QApplication.UnicodeUTF8)

    def getJsonData(self):
        if not self.result():
            return None

        return self.ui_widget.getData()

    def applySetting(self):
        if not self.apply:
            return

        try:
            self.setResult(1)
            self.apply(self.getJsonData())
        except TypeError as error:
            return showMessageBox(self, MB_TYPE_ERR, self.tr("Apply settings error") + " : {}".format(error))

    def slotSettingChanged(self):
        pass

    def getJsonDataWithoutConfirm(self):
        return self.ui_widget.getData()

    def setJsonData(self, data: dict):
        return self.ui_widget.setData(data)

    @classmethod
    def getData(cls, settings, data=None, reset=True, apply=None, parent=None):
        dialog = cls(settings, data, reset, apply, parent)
        dialog.exec_()
        return dialog.getJsonData()


class JsonSettingDialog(BasicJsonSettingDialog):
    def __init__(self, settings, data=None, reset=True, apply=None, parent=None):
        super(JsonSettingDialog, self).__init__(JsonSettingWidget, settings, data, reset, apply, parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def getJsonSettings(self):
        if not self.result():
            return None

        return self.ui_widget.getSettings()

    @classmethod
    def getSettings(cls, settings, data=None, reset=True, apply=None, parent=None):
        dialog = cls(settings, data, reset, apply, parent)
        dialog.exec_()
        return dialog.getJsonSettings()


class MultiJsonSettingsDialog(BasicJsonSettingDialog):
    def __init__(self, settings, data=None, reset=True, apply=None, parent=None):
        super(MultiJsonSettingsDialog, self).__init__(MultiJsonSettingsWidget,
                                                      settings, data, reset, apply, parent=parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)


class MultiGroupJsonSettingsDialog(BasicJsonSettingDialog):
    def __init__(self, settings, data=None, reset=True, apply=None, parent=None):
        super(MultiGroupJsonSettingsDialog, self).__init__(MultiGroupJsonSettingsWidget,
                                                           settings, data, reset, apply, parent=parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)


class MultiTabJsonSettingsDialog(BasicJsonSettingDialog):
    def __init__(self, settings, data, reset=True, apply=None, parent=None):
        super(MultiTabJsonSettingsDialog, self).__init__(MultiTabJsonSettingsWidget,
                                                         settings, data, reset, apply, parent)
        scale_x, _ = get_program_scale_factor()
        self.setMinimumWidth(len(settings.layout.layout) * 120 * scale_x)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def getJsonSettings(self):
        if not self.result():
            return None

        return self.ui_widget.getSettings()

    def insertCustomTabWidget(self, name, widget, position=None):
        return self.ui_widget.insertCustomTabWidget(name, widget, position)

    @classmethod
    def getSettings(cls, settings, data=None, reset=True, apply=None, parent=None):
        dialog = cls(settings, data, reset, apply, parent)
        dialog.exec_()
        return dialog.getJsonSettings()


class PasswordDialog(QDialog):
    DefaultHashFunction = lambda x: hashlib.md5(x).hexdigest()

    def __init__(self, password=None, hash_function=DefaultHashFunction, style='font: 75 16pt "Arial"', parent=None):
        super(PasswordDialog, self).__init__(parent)
        if not hasattr(hash_function, "__call__"):
            raise TypeError("hash_function must be a callable object}")

        self.__new_password = ""
        self.__password = password
        self.__hash_function = hash_function

        self.__initUi()
        self.__initSignalAndSlots()
        self.setStyleSheet(style)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def __initUi(self):
        # Ui elements
        self.ui_old_password = QLineEdit()
        self.ui_old_password.setPlaceholderText(self.tr("Please input old password"))

        self.ui_new_password = QLineEdit()
        self.ui_new_password.setPlaceholderText(self.tr("Please input new password"))

        self.ui_show_password = QCheckBox()

        self.ui_confirm_password = QLineEdit()
        self.ui_confirm_password.setPlaceholderText(self.tr("Confirm new password"))

        self.ui_old_password_label = QLabel(self.tr("Old password"))
        self.ui_buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)

        # Ui layout
        item_layout = QGridLayout()
        item_layout.addWidget(self.ui_old_password_label, 0, 0)
        item_layout.addWidget(self.ui_old_password, 0, 1)

        item_layout.addWidget(QLabel(self.tr("New password")), 1, 0)
        item_layout.addWidget(self.ui_new_password, 1, 1)

        item_layout.addWidget(QLabel(self.tr("Confirm new password")), 2, 0)
        item_layout.addWidget(self.ui_confirm_password, 2, 1)

        sub_layout = QHBoxLayout()
        sub_layout.addWidget(self.ui_show_password)
        self.ui_show_password.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        sub_layout.addWidget(QLabel(self.tr("Show password")))
        item_layout.addLayout(sub_layout, 3, 1)

        for item in (self.ui_old_password, self.ui_new_password, self.ui_confirm_password):
            item.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))
            item.setInputMethodHints(Qt.ImhHiddenText | Qt.ImhNoAutoUppercase | Qt.ImhNoPredictiveText)
            item.setMaxLength(32)
            item.setEchoMode(QLineEdit.Password)

        # Mode switch
        if self.__password:
            self.setWindowTitle(self.tr("Change password"))
        else:
            self.setWindowTitle(self.tr("Reset password"))
            self.ui_old_password.setHidden(True)
            self.ui_old_password_label.setHidden(True)

        layout = QVBoxLayout()
        layout.addLayout(item_layout)
        layout.addWidget(QSplitter())
        layout.addWidget(self.ui_buttons)
        self.setMinimumWidth(320)
        self.setLayout(layout)

    def __initSignalAndSlots(self):
        self.ui_buttons.accepted.connect(self.accept)
        self.ui_buttons.rejected.connect(self.reject)
        self.ui_show_password.stateChanged.connect(self.slotShowPassword)

    def slotShowPassword(self, ck):
        for item in (self.ui_old_password, self.ui_new_password, self.ui_confirm_password):
            item.setEchoMode(QLineEdit.Normal if ck else QLineEdit.Password)
            item.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))
            item.setInputMethodHints(Qt.ImhHiddenText | Qt.ImhNoAutoUppercase | Qt.ImhNoPredictiveText)

    def accept(self, *args, **kwargs):
        old = self.__hash_function(self.ui_old_password.text().encode())
        new = self.__hash_function(self.ui_new_password.text().encode())
        confirm = self.__hash_function(self.ui_confirm_password.text().encode())

        if self.__password and old != self.__password:
            return showMessageBox(self, MB_TYPE_ERR, self.tr("Old password error, please retry"))

        if new != confirm:
            return showMessageBox(self, MB_TYPE_ERR, self.tr("New password mismatch, please retry"))

        if len(self.ui_new_password.text()) == 0 or len(self.ui_confirm_password.text()) == 0:
            return showMessageBox(self, MB_TYPE_ERR, self.tr("Password can't be empty, please retry!"))

        self.__new_password = new
        self.setResult(1)
        self.close()
        return True

    def getNewPassword(self):
        return self.__new_password

    @staticmethod
    def resetPassword(hash_function=DefaultHashFunction, style='', parent=None):
        dialog = PasswordDialog(hash_function=hash_function, style=style, parent=parent)
        dialog.exec_()
        return dialog.getNewPassword()

    @staticmethod
    def changePassword(password=None, hash_function=DefaultHashFunction, style='', parent=None):
        dialog = PasswordDialog(password, hash_function, style, parent)
        dialog.exec_()
        return dialog.getNewPassword()


class OptionDialog(QDialog):
    DEF_TITLE = QApplication.translate("OptionDialog", "Please select", None, QApplication.UnicodeUTF8)

    def __init__(self, options, title=DEF_TITLE, parent=None):
        super(OptionDialog, self).__init__(parent)

        self.selection = ""
        self.options = options

        layout = QVBoxLayout()
        for option in options:
            btn = QPushButton(option)
            layout.addWidget(btn)
            btn.clicked.connect(self.slotSelected)

        cancel = QPushButton(self.tr("Cancel"))
        cancel.clicked.connect(self.reject)
        layout.addWidget(cancel)

        self.setLayout(layout)
        self.setWindowTitle(title)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def slotSelected(self):
        sender = self.sender()
        if not sender:
            return

        self.selection = sender.text()
        self.accept()

    def getSelectionText(self):
        return self.selection

    def getSelectionIndex(self):
        try:
            return self.options.index(self.selection)
        except IndexError:
            return -1

    @classmethod
    def getOptionText(cls, options, title=DEF_TITLE, parent=None):
        dialog = cls(options, title, parent)
        dialog.exec_()
        return dialog.getSelectionText()

    @classmethod
    def getOptionIndex(cls, options, title=DEF_TITLE, parent=None):
        dialog = cls(options, title, parent)
        dialog.exec_()
        return dialog.getSelectionIndex()


def showFileExportDialog(parent, fmt, name="",
                         title=QApplication.translate("dialog",
                                                      "Please select export file save path",
                                                      None, QApplication.UnicodeUTF8)):
    path, ret = QFileDialog.getSaveFileName(parent, parent.tr(title), name, parent.tr(fmt))
    if not ret or len(path) == 0:
        return ""

    return path


def showFileImportDialog(parent, fmt, path="",
                         title=QApplication.translate("dialog",
                                                      "Please select import file",
                                                      None, QApplication.UnicodeUTF8)):
    path, ret = QFileDialog.getOpenFileName(parent, parent.tr(title), path, parent.tr(fmt))
    if not ret or not os.path.isfile(path):
        return ""

    return path
