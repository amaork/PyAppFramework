# -*- coding: utf-8 -*-
import os
import sys
import time
import typing
import hashlib
import ipaddress
import collections
from typing import Optional, Union, Sequence, Callable, Any
from PySide2.QtWidgets import QApplication, QWidget, QDialog, QGridLayout, QHBoxLayout, QVBoxLayout, QLabel, QSlider, \
    QSpinBox, QSplitter, QComboBox, QDialogButtonBox, QLineEdit, QPushButton, QCheckBox, QSizePolicy, QFileDialog, \
    QProgressDialog

from PySide2 import QtWidgets, QtCore, QtGui
from PySide2.QtCore import Qt, Signal, QPoint, QLocale, QSize
from PySide2.QtGui import QColor, QCloseEvent, QShowEvent, QFont

from .msgbox import *
from .button import RectButton
from .misc import CustomSpinBox, ServicePortSelector

from ..network.utility import *
from ..protocol.serialport import SerialPort
from .canvas import ScalableCanvasWidget, canvas_init_helper
from ..network.discovery import ServiceDiscovery, DiscoveryEvent

from ..misc.settings import UiLayout, Color, IndexColor
from ..misc.windpi import get_program_scale_factor, system_open_file

from ..core.datatype import DynamicObject
from .widget import SerialPortSettingWidget, BasicJsonSettingWidget, \
    JsonSettingWidget, MultiJsonSettingsWidget, MultiTabJsonSettingsWidget, MultiGroupJsonSettingsWidget

__all__ = ['BasicDialog',
           'SimpleColorDialog', 'AboutDialog',
           'TextInputDialog', 'TextDisplayDialog',
           'SerialPortSettingDialog', 'FileDialog', 'ScalableCanvasImageDialog',
           'ProgressDialog', 'PasswordDialog', 'OptionDialog', 'ServiceDiscoveryDialog', 'ServicePortSelectDialog',
           'SerialPortSelectDialog', 'NetworkAddressSelectDialog', 'NetworkInterfaceSelectDialog',
           'JsonSettingDialog', 'MultiJsonSettingsDialog', 'MultiTabJsonSettingsDialog', 'MultiGroupJsonSettingsDialog',
           'showFileImportDialog', 'showFileExportDialog', 'showPasswordAuthDialog', 'checkSocketSingleInstanceLock']

__showFileImportDialogRecentPathDict = dict()
DialogApplyFunction = Callable[[dict], None]
PasswordHashFunction = Callable[[Union[bytes, bytearray, memoryview]], str]


class BasicDialog(QDialog):
    def __init__(self, parent: Optional[QWidget], **kwargs):
        super(BasicDialog, self).__init__(parent)

        dialog_buttons = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.ui_buttons = QDialogButtonBox(dialog_buttons)
        self.ui_buttons.accepted.connect(self.accept)
        self.ui_buttons.rejected.connect(self.reject)

        self._initUi()
        self._initData()
        self._initStyle()
        self._initThreadAndTimer()
        self._initSignalAndSlots()

    def _initUi(self):
        pass

    def _initData(self):
        pass

    def _initStyle(self):
        pass

    def _initThreadAndTimer(self):
        pass

    def _initSignalAndSlots(self):
        pass

    def getData(self) -> typing.Union[DynamicObject, dict, None]:
        pass

    @classmethod
    def getSettings(cls, parent: Optional[QWidget], **kwargs):
        dialog = cls(parent=parent, **kwargs)
        # For virtual keyboard
        dialog.setWindowModality(Qt.WindowModal)
        dialog.exec_()
        return dialog.getData()


class SimpleColorDialog(QDialog):
    # This signal is emitted just after the user has clicked OK to select a color to use
    colorSelected = Signal(QColor)
    # This signal is emitted just after the user selected a color
    currentColorChanged = Signal(QColor)

    def __init__(self, basic: bool = False,
                 color: Union[QColor, Qt.GlobalColor] = Qt.black,
                 button_box: bool = False, title: str = '', parent: Optional[QWidget] = None):
        """Simple color dialog

        :param basic: if basic is true, only allow red, greed, blue, cyan, yellow, magenta, black, white color
        :param color: init color
        :param button_box: with or without ok cancel button box
        :param title: dialog title
        :param parent:
        :return:
        """
        super(SimpleColorDialog, self).__init__(parent)
        if not isinstance(color, (QColor, Qt.GlobalColor)):
            raise TypeError("color expect a 'QColor' or 'Qt.GlobalColor' not '{}'".format(color.__class__.__name__))

        self.__initUi(button_box, title)
        self.__basic = basic
        self.__color = QColor(color)
        self.__updateColor(self.__color)

    def __initUi(self, without_buttons: bool, title: str):
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
        # noinspection PyUnresolvedReferences
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
        self.setWindowTitle(title or self.tr('Please select color'))

    def __getColor(self) -> Color:
        """Get select color setting

        :return: r, g, b
        """
        return self.__color.red(), self.__color.green(), self.__color.blue()

    def __setColor(self, color: QColor):
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

    def __getCurrentColor(self) -> Color:
        """Get ui spinbox color setting

        :return: r, g, b
        """
        r = self.__red.value()
        b = self.__blue.value()
        g = self.__green.value()
        return r, g, b

    def __updateColor(self, color: QColor):
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
            self.__red.setEnabled(bool(r))
            self.__blue.setEnabled(bool(b))
            self.__green.setEnabled(bool(g))

    def slotChangeColor(self):
        btn = self.sender()
        if not isinstance(btn, RectButton):
            return

        # Update select color
        color = btn.getBrush().color()
        self.__updateColor(color)
        self.currentColorChanged.emit(color)

    def slotChangeDepth(self, value: int):
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

    def getSelectColor(self) -> QColor:
        if self.result():
            r, g, b = self.__getCurrentColor()
            self.colorSelected.emit(QColor(r, g, b))
            return QColor(r, g, b)
        else:
            return self.__color

    @classmethod
    def getColor(cls, *args, **kwargs) -> QColor:
        panel = cls(*args, **kwargs)
        panel.exec_()
        return panel.getSelectColor()

    @classmethod
    def getBasicColor(cls, *args, **kwargs) -> QColor:
        kwargs['basic'] = True
        panel = cls(*args, **kwargs)
        panel.exec_()
        return panel.getSelectColor()

    @staticmethod
    def convertToRgb(color: QColor) -> Color:
        if not isinstance(color, QColor):
            return 0, 0, 0

        return color.red(), color.green(), color.blue()

    @staticmethod
    def convertToIndexColor(color: QColor) -> IndexColor:
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
    def __init__(self, timeout: float = 0.04, port: str = '',
                 title: str = '', parent: Optional[QWidget] = None):
        super(SerialPortSelectDialog, self).__init__(parent)
        layout = QVBoxLayout()
        self._ports = QComboBox(self)
        self._ports.addItems(SerialPort.get_serial_list(timeout))
        self._ports.setCurrentText(port)

        button = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button.accepted.connect(self.accept)
        button.rejected.connect(self.reject)

        layout.addWidget(self._ports)
        layout.addWidget(QSplitter())
        layout.addWidget(button)
        self.setLayout(layout)
        self.setFixedSize(self.sizeHint())
        self.setWindowTitle(title or self.tr('Please select serial port'))
        self.setMinimumWidth(self.fontMetrics().horizontalAdvance(self.windowTitle()) * 1.5)
        # noinspection PyUnresolvedReferences
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def getPort(self) -> Union[str, None]:
        return self._ports.currentText() if self.result() else None

    @classmethod
    def getSerialPort(cls, *args, **kwargs) -> Union[str, None]:
        dialog = cls(*args, **kwargs)
        # For virtual keyboard
        dialog.setWindowModality(Qt.WindowModal)
        dialog.exec_()
        return dialog.getPort()


class SerialPortSettingDialog(QDialog):
    def __init__(self, settings: dict = SerialPortSettingWidget.DEFAULTS, flush_timeout: float = 0.04,
                 parent: Optional[QWidget] = None):
        """Serial port configure dialog

        :param settings: serial port settings
        :param parent:
        """
        settings = settings or SerialPortSettingWidget.DEFAULTS
        super(SerialPortSettingDialog, self).__init__(parent)

        layout = QVBoxLayout()
        self.__widget = SerialPortSettingWidget(settings, flush_timeout)
        button = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button.accepted.connect(self.accept)
        button.rejected.connect(self.reject)

        layout.addWidget(self.__widget)
        layout.addWidget(QSplitter())
        layout.addWidget(button)

        self.setLayout(layout)
        self.setFixedSize(self.sizeHint())
        self.setWindowTitle(self.tr("Serial Configuration Dialog"))
        # noinspection PyUnresolvedReferences
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def getSerialSetting(self) -> Union[dict, None]:
        if not self.result():
            return None

        return self.__widget.getSetting()

    @classmethod
    def getSetting(cls, *args, **kwargs) -> Union[dict, None]:
        dialog = cls(*args, **kwargs)
        # For virtual keyboard
        dialog.setWindowModality(Qt.WindowModal)
        dialog.exec_()
        return dialog.getSerialSetting()


class ServiceDiscoveryDialog(BasicDialog):
    signalEvent = Signal(object)

    def __init__(self, service: str, port: int,
                 network: str = get_default_network(),
                 title: str = '', timeout: float = 0.0, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.signalEvent.connect(self.eventHandle)
        self._discovery = ServiceDiscovery(
            service=service, port=port, network=network,
            event_callback=self.signalEvent.emit, auto_stop=False, discovery_timeout=timeout
        )
        self.setWindowTitle(title or self.tr('Please select'))

    def _initUi(self):
        self.ui_address = QComboBox()
        label = QLabel(self.tr('Address'))
        label.setMaximumWidth(40)
        content = QHBoxLayout()
        content.addWidget(label)
        content.addWidget(self.ui_address)

        layout = QVBoxLayout()
        layout.addLayout(content)
        layout.addWidget(QLabel(' ' * 35))
        layout.addWidget(QSplitter())
        layout.addWidget(self.ui_buttons)
        self.setLayout(layout)

    def sizeHint(self) -> QSize:
        return QSize(210, 80)

    def getDeviceList(self):
        return [self.ui_address.itemText(x) for x in range(self.ui_address.count())]

    def pauseDiscovery(self):
        self._discovery.pause()

    def resumeDiscovery(self):
        self.ui_address.clear()
        self._discovery.resume()

    def setNetwork(self, network: str):
        try:
            network = str(ipaddress.IPv4Network(network))
            ifc = get_network_ifc(network)
            if not ifc:
                raise ValueError(f'invalid network: {network}')
        except ValueError as e:
            showMessageBox(self, MB_TYPE_WARN, f'{e}', self.tr('Invalid network'))
        else:
            self.ui_address.setEditable(False)
            self._discovery.setNetwork(network)

    def eventHandle(self, ev: DiscoveryEvent):
        # Has error occupied, enabled address can be manual input
        if ev.isEvent(DiscoveryEvent.Type.Error):
            self.ui_address.setEditable(True)
        if ev.isEvent(DiscoveryEvent.Type.Online):
            if ev.data not in self.getDeviceList():
                self.ui_address.addItem(ev.data)
        elif ev.isEvent(DiscoveryEvent.Type.Offline):
            if ev.data in self.getDeviceList():
                self.ui_address.removeItem(self.getDeviceList().index(ev.data))

    def getAddress(self) -> str:
        self.exec_()
        data = self.getData()
        return data.address if data else ''

    def getData(self) -> typing.Union[DynamicObject, dict, None]:
        if not self.result():
            return None
        return DynamicObject(address=self.ui_address.currentText())


class ServicePortSelectDialog(BasicDialog):
    def __init__(self, port: int, network: str, title: Optional[str] = '',
                 timeout: float = 0.04, parent: Optional[QtWidgets.QWidget] = None):
        self._kwargs = dict(port=port, network=network, timeout=timeout, parent=self)
        super(ServicePortSelectDialog, self).__init__(parent)
        self.setWindowTitle(title or self.tr('Please select device'))

    def _initUi(self):
        self.ui_combox = ServicePortSelector(**self._kwargs)

        layout = QVBoxLayout()
        layout.addWidget(self.ui_combox)
        layout.addWidget(QSplitter())
        layout.addWidget(self.ui_buttons)

        self.setLayout(layout)

    def sizeHint(self) -> QtCore.QSize:
        return QSize(265, 80)

    def getData(self) -> typing.Union[DynamicObject, dict, None]:
        if not self.result():
            return None

        return DynamicObject(address=self.ui_combox.getSelectedAddress())


class NetworkAddressSelectDialog(QDialog):
    def __init__(self, port: int, timeout: float = 0.04, network: str = '',
                 title: str = '', parent: Optional[QWidget] = None):
        super(NetworkAddressSelectDialog, self).__init__(parent)
        layout = QVBoxLayout()
        self._address_list = QComboBox(self)
        try:
            self._address_list.addItems(scan_lan_port(port=port, network=network, timeout=timeout))
        except OSError as e:
            print(f'{self.__class__.__name__}: {e}')

        button = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button.accepted.connect(self.accept)
        button.rejected.connect(self.reject)

        layout.addWidget(self._address_list)
        layout.addWidget(QSplitter())
        layout.addWidget(button)
        self.setLayout(layout)
        self.setWindowTitle(title or self.tr('Please select address'))
        self.setMinimumWidth(self.fontMetrics().horizontalAdvance(self.windowTitle()) * 1.5)
        # noinspection PyUnresolvedReferences
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def getSelectedAddress(self) -> Union[str, None]:
        return self._address_list.currentText() if self.result() else None

    @classmethod
    def getAddress(cls, *args, **kwargs) -> Union[str, None]:
        dialog = NetworkAddressSelectDialog(*args, **kwargs)
        # For virtual keyboard
        dialog.setWindowModality(Qt.WindowModal)
        dialog.exec_()
        return dialog.getSelectedAddress()


class NetworkInterfaceSelectDialog(QDialog):
    def __init__(self, name: str = "", address: str = "", network: str = "",
                 ignore_loopback: bool = True, parent: Optional[QWidget] = None):
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
        # noinspection PyUnresolvedReferences
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def getSelectedInterfaceAddress(self) -> str:
        return self._nic_list.currentText().split(":")[-1].strip() if self.result() else ""

    def getSelectedInterfaceNetwork(self) -> str:
        idx = self._nic_list.currentIndex()
        return self._nic_list.itemData(idx) if self.result() else ""

    def getSelectedNetworkInterface(self) -> str:
        return self._nic_list.currentText() if self.result() else ""

    @classmethod
    def getAddress(cls, *args, **kwargs) -> str:
        dialog = NetworkInterfaceSelectDialog(*args, **kwargs)
        # For virtual keyboard
        dialog.setWindowModality(Qt.WindowModal)
        dialog.exec_()
        return dialog.getSelectedInterfaceAddress()

    @classmethod
    def getInterface(cls, *args, **kwargs) -> str:
        dialog = NetworkInterfaceSelectDialog(*args, **kwargs)
        # For virtual keyboard
        dialog.setWindowModality(Qt.WindowModal)
        dialog.exec_()
        return dialog.getSelectedNetworkInterface()

    @classmethod
    def getInterfaceNetwork(cls, *args, **kwargs) -> str:
        dialog = NetworkInterfaceSelectDialog(*args, **kwargs)
        # For virtual keyboard
        dialog.setWindowModality(Qt.WindowModal)
        dialog.exec_()
        return dialog.getSelectedInterfaceNetwork()


class ProgressDialog(QProgressDialog):
    progressCanceled = Signal(bool)

    def __init__(self, parent: QWidget, title: str = '', max_width: int = 350,
                 cancel_button: Optional[str] = None, closeable: bool = True, cancelable: bool = False):
        super(ProgressDialog, self).__init__(parent)
        # fix ProgressDialog sometimes will auto popup issue
        self.reset()
        self.__canceled = False
        self.__closeable = closeable
        self.__cancelable = cancelable
        self.__canceled_callback = None

        self.setFixedWidth(max_width)
        self.setWindowModality(Qt.WindowModal)
        self.setWindowTitle(title or self.tr('Operation progress'))
        # noinspection PyUnresolvedReferences
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        if cancel_button is None:
            # noinspection PyTypeChecker
            self.setCancelButton(None)
        else:
            self.setCancelButtonText(self.tr(cancel_button))

    def closeEvent(self, ev: QCloseEvent):
        if not self.__closeable and not self.__cancelable:
            ev.ignore()

        if self.__cancelable:
            if showQuestionBox(self, self.tr("Cancel") + " " + self.windowTitle() + " ?"):
                self.setLabelText(self.tr("Canceling please wait..."))
                self.setCancelState(True)
                if callable(self.__canceled_callback):
                    self.__canceled_callback()
                    self.slotHidden()
            else:
                ev.ignore()

    def showEvent(self, ev: QShowEvent):
        # self.setCancelState(False)
        x = self.parent().geometry().x() + self.parent().width() / 2 - self.width() / 2
        y = self.parent().geometry().y() + self.parent().height() / 2 - self.height() / 2
        self.move(QPoint(x, y))

    def slotHidden(self):
        self.setProgress(self.maximum())
        self.setHidden(True)

    def isCanceled(self) -> bool:
        return self.__canceled if self.__cancelable else False

    def setCloseable(self, en: bool):
        self.__closeable = True if en else False

    def setCancelable(self, en: bool):
        self.__cancelable = True if en else False

    def setCancelState(self, st: bool):
        self.__canceled = True if st else False
        self.progressCanceled.emit(self.__canceled)

    def setCancelCallback(self, callback: typing.Callable):
        self.__canceled_callback = callback

    def setLabelText(self, text: str):
        if self.isCanceled():
            return

        self.setWhatsThis(text)

        # Make sure label text can fully show up
        width = int(QtGui.QFontMetrics(self.font()).width(text) * 1.5)
        if self.width() < width:
            self.setMinimumWidth(width)

        super(ProgressDialog, self).setLabelText(text)

    def setProgress(self, value: int, force: bool = False):
        self.setValue(value)
        if value != self.maximum():
            self.show()
        x = self.parent().geometry().x() + self.parent().width() / 2 - self.width() / 2
        y = self.parent().geometry().y() + self.parent().height() / 2 - self.height() / 2
        self.move(QPoint(x, y))
        if force:
            QtWidgets.QApplication.processEvents()


class BasicJsonSettingDialog(QDialog):
    def __init__(self, widget_cls: Union[BasicJsonSettingWidget.__class__, MultiTabJsonSettingsWidget.__class__],
                 settings: DynamicObject, data: Optional[dict] = None,
                 reset: bool = True, apply: Optional[DialogApplyFunction] = None, parent: Optional[QWidget] = None):
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
        self.ui_widget.settingChangedDetail.connect(self.slotSettingChangedDetail)

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

        try:
            font = QFont(*settings.layout.get_font())
        except (TypeError, ValueError):
            pass
        else:
            self.setFont(font)

        self.setLayout(layout)
        self.setWindowTitle(self.tr(title))
        # noinspection PyUnresolvedReferences
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    # noinspection PyMethodOverriding
    def tr(self, text: str) -> str:
        # noinspection PyTypeChecker
        return QApplication.translate("BasicJsonSettingDialog", text, None)

    def getJsonData(self) -> Optional[dict]:
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
            showMessageBox(self, MB_TYPE_ERR, self.tr("Apply settings error") + " : {}".format(error))

    def slotSettingChanged(self):
        pass

    def slotSettingChangedDetail(self, name: str, value: Any):
        pass

    def getJsonDataWithoutConfirm(self) -> dict:
        return self.ui_widget.getData()

    def setJsonData(self, data: dict) -> bool:
        return self.ui_widget.setData(data)

    @classmethod
    def getData(cls, *args, **kwargs):
        # BasicJsonSettingDialog is abstract class derived class __init__ don't need widget_cls arg
        dialog = cls(*args, **kwargs)
        # For virtual keyboard
        dialog.setWindowModality(Qt.WindowModal)
        dialog.exec_()
        return dialog.getJsonData()


class JsonSettingDialog(BasicJsonSettingDialog):
    def __init__(self, settings: DynamicObject, data: Optional[dict] = None,
                 reset: bool = True, apply: Optional[DialogApplyFunction] = None, parent: Optional[QWidget] = None):
        super(JsonSettingDialog, self).__init__(JsonSettingWidget, settings, data, reset, apply, parent)
        # noinspection PyUnresolvedReferences
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def getJsonSettings(self) -> Optional[DynamicObject]:
        if not self.result():
            return None

        return self.ui_widget.getSettings()

    @classmethod
    def getSettings(cls, *args, **kwargs):
        dialog = cls(*args, **kwargs)
        # For virtual keyboard
        dialog.setWindowModality(Qt.WindowModal)
        dialog.exec_()
        return dialog.getJsonSettings()


class MultiJsonSettingsDialog(BasicJsonSettingDialog):
    def __init__(self, settings: DynamicObject, data: Optional[dict] = None,
                 reset: bool = True, apply: Optional[DialogApplyFunction] = None, parent: Optional[QWidget] = None):
        super(MultiJsonSettingsDialog, self).__init__(MultiJsonSettingsWidget,
                                                      settings, data, reset, apply, parent=parent)
        # noinspection PyUnresolvedReferences
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)


class MultiGroupJsonSettingsDialog(BasicJsonSettingDialog):
    def __init__(self, settings: DynamicObject, data: Optional[dict] = None,
                 reset: bool = True, apply: Optional[DialogApplyFunction] = None, parent: Optional[QWidget] = None):
        super(MultiGroupJsonSettingsDialog, self).__init__(MultiGroupJsonSettingsWidget,
                                                           settings, data, reset, apply, parent=parent)
        # noinspection PyUnresolvedReferences
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)


class MultiTabJsonSettingsDialog(BasicJsonSettingDialog):
    def __init__(self, settings: DynamicObject, data: Optional[dict] = None,
                 reset: bool = True, apply: Optional[DialogApplyFunction] = None, parent: Optional[QWidget] = None):
        super(MultiTabJsonSettingsDialog, self).__init__(MultiTabJsonSettingsWidget,
                                                         settings, data, reset, apply, parent)
        scale_x, _ = get_program_scale_factor()
        self.setMinimumWidth(int(len(settings.layout.layout) * 120 * scale_x))
        # noinspection PyUnresolvedReferences
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def getJsonSettings(self) -> Optional[DynamicObject]:
        if not self.result():
            return None

        return self.ui_widget.getSettings()

    def insertCustomTabWidget(self, name: str, widget: QWidget, position: Optional[int] = None) -> bool:
        return self.ui_widget.insertCustomTabWidget(name, widget, position)

    @classmethod
    def getSettings(cls, *args, **kwargs):
        dialog = cls(*args, **kwargs)
        # For virtual keyboard
        dialog.setWindowModality(Qt.WindowModal)
        dialog.exec_()
        return dialog.getJsonSettings()


class PasswordDialog(QDialog):
    def __init__(self, password: Optional[str] = None,
                 hash_function: PasswordHashFunction = lambda x: hashlib.md5(x).hexdigest(),
                 style: str = 'font: 75 16pt "Arial"', parent: Optional[QWidget] = None):
        super(PasswordDialog, self).__init__(parent)
        if not callable(hash_function):
            raise TypeError("hash_function must be a callable object}")

        self.__new_password = ""
        self.__password = password
        self.__hash_function = hash_function

        self.__initUi()
        self.__initSignalAndSlots()
        self.setStyleSheet(style)
        # noinspection PyUnresolvedReferences
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

    def slotShowPassword(self, ck: bool):
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

    def getNewPassword(self) -> str:
        return self.__new_password

    @staticmethod
    def resetPassword(hash_function: PasswordHashFunction = lambda x: hashlib.md5(x).hexdigest(),
                      style: str = '', parent: Optional[QWidget] = None) -> str:
        dialog = PasswordDialog(hash_function=hash_function, style=style, parent=parent)
        # For virtual keyboard
        dialog.setWindowModality(Qt.WindowModal)
        dialog.exec_()
        return dialog.getNewPassword()

    @staticmethod
    def changePassword(password: Optional[str] = None,
                       hash_function: PasswordHashFunction = lambda x: hashlib.md5(x).hexdigest(),
                       style: str = '', parent: Optional[QWidget] = None) -> str:
        dialog = PasswordDialog(password, hash_function, style, parent)
        # For virtual keyboard
        dialog.setWindowModality(Qt.WindowModal)
        dialog.exec_()
        return dialog.getNewPassword()


class OptionDialog(QDialog):
    def __init__(self, options: Sequence[str], title: str = '', parent: Optional[QWidget] = None):
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
        self.setWindowTitle(title or self.tr('Please select'))
        # noinspection PyUnresolvedReferences
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def slotSelected(self):
        sender = self.sender()
        if not sender:
            return

        self.selection = sender.text()
        self.accept()

    def getSelectionText(self) -> str:
        return self.selection

    def getSelectionIndex(self) -> int:
        try:
            return self.options.index(self.selection)
        except IndexError:
            return -1

    @classmethod
    def getOptionText(cls, *args, **kwargs) -> str:
        dialog = cls(*args, **kwargs)
        # For virtual keyboard
        dialog.setWindowModality(Qt.WindowModal)
        dialog.exec_()
        return dialog.getSelectionText()

    @classmethod
    def getOptionIndex(cls, *args, **kwargs) -> int:
        dialog = cls(*args, **kwargs)
        # For virtual keyboard
        dialog.setWindowModality(Qt.WindowModal)
        dialog.exec_()
        return dialog.getSelectionIndex()


class FileDialog(QtWidgets.QFileDialog):
    def __init__(self, **kwargs):
        """Refer: https://www.qtcentre.org/threads/43841-QFileDialog-to-select-files-AND-folders"""
        self.__selectedFiles = list()
        super(FileDialog, self).__init__(**kwargs)
        self.setFileMode(QtWidgets.QFileDialog.Directory)
        self.setOptions(QtWidgets.QFileDialog.DontResolveSymlinks)
        self.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
        self.ui_list_view = self.findChild(QtWidgets.QListView, 'listView')

        if isinstance(self.ui_list_view, QtWidgets.QListView):
            self.ui_list_view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        tree_view = self.findChild(QtWidgets.QTreeView)
        if isinstance(tree_view, QtWidgets.QTreeView):
            tree_view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        # Find choose or open button install event filter and reconnect clicked signal
        for btn in self.findChildren(QtWidgets.QPushButton):
            if not isinstance(btn, QtWidgets.QPushButton):
                continue

            if any([x in btn.text().lower() for x in ('open', 'choose')]):
                btn.installEventFilter(self)
                btn.clicked.disconnect()
                btn.clicked.connect(self.slotChooseClicked)

    def slotChooseClicked(self):
        if not self.ui_list_view:
            self.reject()

        # noinspection PyUnresolvedReferences
        for index in self.ui_list_view.selectionModel().selectedIndexes():
            if index.column() == 0:
                # noinspection PyUnresolvedReferences
                self.__selectedFiles.append(self.ui_list_view.model().filePath(index))

        self.done(1)

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if isinstance(watched, QPushButton) and event.type() == QtCore.QEvent.EnabledChange:
            if not watched.isEnabled():
                watched.setEnabled(True)

        return super(FileDialog, self).eventFilter(watched, event)

    def selectedFiles(self) -> typing.List:
        return self.__selectedFiles[:]

    @staticmethod
    def getFilesAndDirs(title: str, **kwargs):
        dialog = FileDialog(**kwargs)
        dialog.setWindowTitle(title)
        dialog.exec_()
        return dialog.selectedFiles()


class ScalableCanvasImageDialog(BasicDialog):
    def __init__(self, image_path: str, default_text: str = '',
                 hidden_toolbar: bool = False, parent: QtWidgets.QWidget = None):
        """ScalableCanvasImageDialog

        :param image_path: display image file path
        :param default_text: if nothing to display will display default text
        :param hidden_toolbar: hidden zoom fit_width, fix window tool buttons
        :param parent:
        """
        self._image_path = image_path
        self._default_text = default_text
        self._hidden_toolbar = hidden_toolbar
        super(ScalableCanvasImageDialog, self).__init__(parent)

    def _initUi(self):
        tool_bar = QtWidgets.QToolBar(self)
        tool_bar.setHidden(self._hidden_toolbar)

        self.ui_zoom = CustomSpinBox(maximum=300, suffix=' %')
        self.action_capture = QtWidgets.QAction(self.tr('Capture'))
        self.action_fit_width = QtWidgets.QAction(self.tr('Fit Width'))
        self.action_fit_window = QtWidgets.QAction(self.tr('Fit Window'))
        self.ui_preview = ScalableCanvasWidget(default_text=self._default_text, change_cursor=False, parent=self)

        for item in (self.ui_zoom, self.action_fit_width, self.action_fit_window, QtWidgets.QSplitter()):
            if isinstance(item, QtWidgets.QWidget):
                tool_bar.addWidget(item)
            else:
                tool_bar.addAction(item)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(tool_bar)
        layout.addWidget(self.ui_preview)

        self.setLayout(layout)
        self.setWindowTitle(self.tr('Image Preview'))

    def _initData(self):
        self.ui_preview.slotLoadImage(self._image_path)
        self.ui_preview.slotPaintCanvas(int(self.ui_preview.scaleFitWindow() * 100))

    def _initSignalAndSlots(self):
        canvas_init_helper(self, self.ui_preview, self.ui_zoom, self.action_fit_width, self.action_fit_window)

    def accept(self) -> None:
        super().accept()
        self.ui_preview.slotClearImage()

    def sizeHint(self) -> QtCore.QSize:
        return QSize(1024, 768)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        self.ui_preview.slotPaintCanvas(int(self.ui_preview.scaleFitWindow() * 100))


class TextInputDialog(BasicDialog):
    def __init__(self, parent: QtWidgets.QWidget, title: str, label: str, validator: str = '',
                 mode: QtWidgets.QLineEdit.EchoMode = QtWidgets.QLineEdit.EchoMode.Normal, text: str = ''):
        self.ui_label = QtWidgets.QLabel(label)

        self.ui_input = QtWidgets.QLineEdit()
        self.ui_input.setEchoMode(mode)
        self.ui_input.setText(text)

        if validator:
            self.ui_input.setValidator(QtGui.QRegExpValidator(QtCore.QRegExp(validator)))

        super(TextInputDialog, self).__init__(parent)
        self.setWindowTitle(title)

    def _initUi(self):
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.ui_label)
        layout.addWidget(self.ui_input)
        layout.addWidget(QtWidgets.QSplitter())
        layout.addWidget(self.ui_buttons)
        self.setLayout(layout)

    def getInputText(self) -> typing.Tuple[str, bool]:
        return self.ui_input.text(), bool(self.result())

    @classmethod
    def getText(cls, parent: QtWidgets.QWidget, title: str, label: str, validator: str = '',
                mode: QtWidgets.QLineEdit.EchoMode = QtWidgets.QLineEdit.EchoMode.Normal, text: str = ''):
        dialog = cls(parent=parent, title=title, label=label, validator=validator, mode=mode, text=text)
        dialog.exec_()
        return dialog.getInputText()


class TextDisplayDialog(BasicDialog):
    def __init__(self, content: str, title: str, zoom_in: int = 1,
                 advice_size: QSize = QSize(500, 300), parent: typing.Optional[QWidget] = None):
        self.adv_size = advice_size
        super(TextDisplayDialog, self).__init__(parent)
        self.ui_content.setHtml(content)
        self.ui_content.zoomIn(zoom_in)
        self.setWindowTitle(title)

    def _initUi(self):
        self.ui_content = QtWidgets.QTextEdit()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.ui_content)
        layout.addWidget(QtWidgets.QSplitter())
        layout.addWidget(self.ui_buttons)
        self.setLayout(layout)

    def _initStyle(self):
        self.ui_content.setReadOnly(True)

    def sizeHint(self) -> QtCore.QSize:
        return self.adv_size

    @classmethod
    def showContent(cls, **kwargs):
        dialog = cls(**kwargs)
        dialog.exec_()
        return dialog.result()


class AboutDialog(QtWidgets.QDialog):
    CompanyInfo = collections.namedtuple('CompanyInfo', 'start_year en_name ch_name')

    def __init__(self, logo: str, logo_width: int, ver_str: str, company_info: CompanyInfo,
                 margin: int = 20, change_log: str = '', ver_font: QtGui.QFont = QtGui.QFont('宋体', 18),
                 copyright_font: QtGui.QFont = QtGui.QFont('宋体', 9),
                 changelog_font: QtGui.QFont = QtGui.QFont('宋体', 11),
                 parent: typing.Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self._change_log = change_log if os.path.isfile(change_log) else ''
        self._company_info = company_info
        self._ver_str = ver_str

        self._ver_font = ver_font
        self._cr_font = copyright_font
        self._cl_font = changelog_font

        self._clickable_rect = QtCore.QRect()
        self._pixmap = QtGui.QPixmap(logo)
        self._logo_width = logo_width
        self._margin = margin
        self.setMouseTracking(True)

    def getCopyrightStr(self) -> str:
        return f'Copyright © {self._company_info.start_year} - {time.strftime("%Y")} {self._company_info.en_name}®. ' \
                f'All rights reserved.\n{self._company_info.ch_name} 版权所有'

    def isChangeLogPos(self, pos: QtCore.QPoint) -> bool:
        return self._clickable_rect.contains(pos)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        self.setCursor(QtGui.QCursor(Qt.PointingHandCursor if self.isChangeLogPos(event.pos()) else Qt.ArrowCursor))

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if not self.isChangeLogPos(event.pos()):
            return

        try:
            system_open_file(self._change_log)
        except (AttributeError, ValueError, OSError) as e:
            showMessageBox(self, MB_TYPE_ERR, f'{e}', self.tr('Open change log filed'))

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.HighQualityAntialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        center = self.rect().center()
        painter.drawPixmap(
            center.x() - self._logo_width // 2, self._margin, self._logo_width, self._logo_width, self._pixmap
        )

        rect = self.rect()
        rect.y = self._margin + self._logo_width + self._margin * 2
        painter.setFont(self._ver_font)
        painter.setPen(QtGui.QPen(QtGui.QColor(QtCore.Qt.black)))
        painter.drawText(rect, QtCore.Qt.AlignCenter, self._ver_str)

        vfh = QtGui.QFontMetrics(self._ver_font).height()
        rect.moveTop(vfh * 6)
        painter.setFont(self._cr_font)
        painter.setPen(QtGui.QPen(QtGui.QColor(QtCore.Qt.black)))
        painter.drawText(rect, QtCore.Qt.AlignCenter, self.getCopyrightStr())

        if self._change_log:
            rect.moveTop(vfh * 7.2)
            painter.setFont(self._cl_font)
            painter.setPen(QtGui.QPen(QtGui.QColor(QtCore.Qt.blue)))
            painter.drawText(rect, QtCore.Qt.AlignCenter, self.tr('ChangeLog'))

            fm = QtGui.QFontMetrics(painter.font())
            self._clickable_rect = QtCore.QRect(
                self.rect().center().x() - fm.width(self.tr('ChangeLog')) // 2,
                self._margin * 3 + self._logo_width + vfh * 7 + QtGui.QFontMetrics(self._cr_font).height(),
                fm.width(self.tr('ChangeLog')), fm.height()
            )


# noinspection PyTypeChecker
def showFileExportDialog(parent: QWidget, fmt: str, name: str = "",
                         title: str = QApplication.translate("dialog",
                                                             "Please select export file save path",
                                                             None)) -> str:
    path, ret = QFileDialog.getSaveFileName(parent, parent.tr(title), name, parent.tr(fmt))
    if not ret or len(path) == 0:
        return ""

    return path


# noinspection PyTypeChecker
def showFileImportDialog(parent: QWidget, fmt: str, path: str = "",
                         title: str = QApplication.translate("dialog",
                                                             "Please select import file",
                                                             None)) -> str:

    # If not specified path load recently used path
    path = __showFileImportDialogRecentPathDict.get(title, "") if not path else path

    import_path, ret = QFileDialog.getOpenFileName(parent, parent.tr(title), path, parent.tr(fmt))
    if not ret or not os.path.isfile(import_path):
        return ""

    __showFileImportDialogRecentPathDict[title] = os.path.dirname(import_path)
    return import_path


def showPasswordAuthDialog(parent: QWidget, name: str,
                           auth: typing.Callable[[str], bool],
                           success_action: typing.Callable[[], Any] = None,
                           retry_times: int = 3, space_size: int = 60,
                           auto_lock: bool = True,
                           disable_ui: typing.Callable[[], None] = None,
                           delay_enable_ui: typing.Callable[[], Any] = None):
    unlocked = False
    retry_count = retry_times
    while retry_count > 0:
        try:
            # noinspection PyTypeChecker
            raw_password, ret = QtWidgets.QInputDialog.getText(
                parent,
                QApplication.translate('dialog', 'Please Input') +
                f' {name} ' + QApplication.translate('dialog', 'Password'),
                QApplication.translate('dialog', 'Password') + ' ' * space_size, QtWidgets.QLineEdit.Password,
            )
            if not ret:
                return False

            if not raw_password:
                # noinspection PyTypeChecker
                raise ValueError(QApplication.translate('dialog', "Password can't be empty"))

            if not auth(raw_password):
                # noinspection PyTypeChecker
                showMessageBox(
                    parent, MB_TYPE_ERR, QApplication.translate('dialog', 'Password verify failed, please retry!!!')
                )
                retry_count -= 1
                continue

            unlocked = True
            if callable(success_action):
                success_action()
            return True
        except ValueError as e:
            showMessageBox(parent, MB_TYPE_ERR, f'{e}')
            retry_count -= 1

    if retry_count <= 0 and not unlocked and auto_lock and callable(disable_ui) and callable(delay_enable_ui):
        disable_ui()
        # noinspection PyTypeChecker
        showMessageBox(
            parent, MB_TYPE_WARN,
            QApplication.translate('dialog', 'Too many errors, locked for 1 minute, please retry later.')
        )
        delay_enable_ui()
        return False

    return False


def checkSocketSingleInstanceLock(port: int, parent: QWidget) -> SocketSingleInstanceLock:
    try:
        return SocketSingleInstanceLock(port)
    except RuntimeError as e:
        showMessageBox(parent, MB_TYPE_WARN, "{}".format(e))
        sys.exit()
