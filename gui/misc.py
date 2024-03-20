# -*- coding: utf-8 -*-
import glob
import typing
import platform
import threading
import ipaddress
import websocket
import collections
import datetime as dt
from PySide2.QtWidgets import QApplication
from PySide2.QtCore import Qt, Signal, SLOT
from PySide2 import QtWidgets, QtGui, QtCore

import serial.tools.list_ports
from raspi_io.utility import scan_server
from ..misc.utils import get_timestamp_str
from ..network.utility import scan_lan_port
from raspi_io import Query, RaspiSocketError
from typing import Optional, Union, Sequence, Tuple, Callable, Iterable

from ..network.utility import get_system_nic
from ..misc.settings import Color, CustomAction
__all__ = ['SerialPortSelector', 'NetworkInterfaceSelector', 'ServicePortSelector', 'DateTimeEdit',
           'TabBar', 'ExpandWidget', 'CustomTextEditor', 'CustomSpinBox', 'PageNumberBox',
           'NavigationItem', 'NavigationBar',
           'CustomEventFilterHandler',
           'ThreadSafeLabel', 'HyperlinkLabel', 'Separator',
           'updateFilterMenu', 'qtTranslate']


class SerialPortSelector(QtWidgets.QComboBox):
    """List current system exist serial port and LAN raspberry serial port

    """
    # When port selected this signal will emit
    portSelected = Signal(object)
    # noinspection PyTypeChecker
    TIPS = QtWidgets.QApplication.translate("SerialPortSelector", "Please select serial port", None)

    def __init__(self, text: Optional[str] = TIPS, one_shot: bool = False,
                 flush_timeout: float = 0.04, parent: Optional[QtWidgets.QWidget] = None):
        """Select serial port

        :param text: selector text
        :param one_shot: only could select once
        :param flush_timeout: flush raspberry websocket serial port timeout
        :param parent:
        """
        super(SerialPortSelector, self).__init__(parent)

        self.clear()
        self.__one_shot = one_shot
        self.__text = text or self.TIPS
        self.setProperty('format', 'text')
        self.__system = platform.system().lower()
        self.setToolTip(self.tr("Right click reset and refresh serial port"))

        # Flush current serial port list
        self.flushSerialPort(timeout=flush_timeout)
        self.currentIndexChanged.connect(self.slotPortSelected)

    def currentPort(self) -> str:
        return self.getSelectedPort()

    def getSelectedPort(self) -> str:
        if not self.count() or not self.itemData(self.currentIndex()):
            return ""

        return self.itemData(self.currentIndex())

    def setCurrentPort(self, port: str) -> bool:
        return self.setSelectedPort(port)

    def setSelectedPort(self, port: str) -> bool:
        try:
            idx = [self.itemData(x) for x in range(self.count())].index(port)
            self.setCurrentIndex(idx)
            self.slotPortSelected(idx)
            return True
        except ValueError:
            return False

    def flushSerialPort(self, timeout: float = 0.04):
        self.clear()
        self.setEnabled(True)

        if self.__text:
            self.addItem(self.tr(self.__text))

        # Scan local system serial port
        if self.__system == "linux":
            for index, port in enumerate(glob.glob("/dev/tty[A-Za-z]*")):
                self.addItem("{}".format(port))
                self.setItemData(self.count() - 1, port)
        else:
            for index, port in enumerate(list(serial.tools.list_ports.comports())):
                # Windows serial port is an object linux is a tuple
                device = port.device
                desc = "{0:s}".format(device).split(" - ")[-1]
                self.addItem("{0:s}".format(desc))
                self.setItemData(self.count() - 1, device)

        # Scan LAN raspberry serial port
        if timeout != 0.0:
            try:
                for raspberry in scan_server(timeout):
                    for port in Query(raspberry).get_serial_list():
                        self.addItem("{}/{}".format(raspberry, port.split("/")[-1]), (raspberry, port))
            except (RaspiSocketError, TypeError, IndexError, ValueError, OSError, websocket.WebSocketTimeoutException):
                pass

    def slotPortSelected(self, idx: int) -> bool:
        if not isinstance(idx, int) or not self.count() or not 0 <= idx < self.count() or not self.itemData(idx):
            return False

        self.setDisabled(self.__one_shot)
        self.portSelected.emit(self.itemData(idx))
        return True

    def mousePressEvent(self, ev: QtGui.QMouseEvent):
        if ev.button() == Qt.RightButton:
            self.flushSerialPort()

        super(SerialPortSelector, self).mousePressEvent(ev)


class ServicePortSelector(QtWidgets.QComboBox):
    updateItems = Signal(object)
    deviceSelected = Signal(object)

    def __init__(self, port: int, network: str, text: Optional[str] = '',
                 one_short: bool = False, timeout: float = 0.04, parent: Optional[QtWidgets.QWidget] = None):
        super(ServicePortSelector, self).__init__(parent)
        self._port = port
        self.__text = text
        self._timeout = timeout
        self._network = network
        self._one_short = one_short

        if self.__text:
            self.addItem(self.__text)
        self.updateItems.connect(self.slotAddItems)
        self.flushAddress(self._network, self._timeout)
        self.setToolTip(self.tr("Right click reset and refresh"))
        self.currentIndexChanged.connect(self.slotDeviceSelected)

    def currentAddress(self) -> str:
        return self.getSelectedAddress()

    def getSelectedAddress(self) -> str:
        try:
            address = ipaddress.ip_address(self.currentText())
        except ValueError:
            return ''
        else:
            return f'{address}'

    def flushAddress(self, network: str = '', timeout: float = 0.0):
        network = network or self._network
        timeout = timeout or self._timeout
        threading.Thread(target=self.threadFlush, args=(network, timeout), daemon=True).start()

    def threadFlush(self, network: str, timeout: float):
        try:
            self.updateItems.emit(scan_lan_port(self._port, network=network, timeout=timeout))
        except OSError:
            self.updateItems.emit([])

    def setScanNetwork(self, network: str):
        self._network = network

    def slotAddItems(self, items: typing.List[str]):
        self.setEnabled(True)
        self.clear()
        if self.__text:
            self.addItem(self.__text)
        self.addItems(items)

    def slotDeviceSelected(self, idx: int) -> bool:
        if not isinstance(idx, int) or not self.count() or not 0 <= idx < self.count() or not self.itemData(idx):
            return False

        self.setDisabled(self.__one_shot)
        self.deviceSelected.emit(self.itemData(idx))
        return True

    def mousePressEvent(self, ev: QtGui.QMouseEvent):
        if ev.button() == Qt.RightButton:
            self.flushAddress()

        super().mousePressEvent(ev)


class NetworkInterfaceSelector(QtWidgets.QComboBox):
    networkChanged = Signal(object)
    addressChanged = Signal(object)
    Mode = collections.namedtuple('Mode', 'Address Network Interface')(*('address', 'network', 'interface'))

    """List current system exist network interface"""
    # noinspection PyTypeChecker
    TIPS = QtWidgets.QApplication.translate("NetworkInterfaceSelector", "Please select network interface", None)

    def __init__(self, text: Optional[str] = TIPS, one_short: bool = False,
                 ignore_loopback: bool = True, mode: Mode = Mode.Address, parent: Optional[QtWidgets.QWidget] = None):
        super(NetworkInterfaceSelector, self).__init__(parent)

        self._text = text
        self._mode = mode
        self._one_short = one_short
        self._ignore_loopback = ignore_loopback
        self.setToolTip(self.tr("Right click reset and refresh network interface"))

        self.flushNic()
        self.setProperty("format", mode)
        self.currentIndexChanged.connect(self.slotNicSelected)

    def getMode(self) -> str:
        return self._mode[:]

    def flushNic(self):
        self.clear()
        self.setEnabled(True)

        if self._text:
            self.addItem(self._text)

        for nic_name, nic_attr in get_system_nic(self._ignore_loopback).items():
            self.addItem("{}: {}".format(nic_name, nic_attr.ip), nic_attr.network)

    def setNetworkMode(self):
        self.setProperty("format", self.Mode.Network)

    def setAddressMode(self):
        self.setProperty("format", self.Mode.Address)

    def setInterfaceMode(self):
        self.setProperty("format", self.Mode.Interface)

    def slotNicSelected(self, idx: int) -> bool:
        if not isinstance(idx, int) or not self.count() or not 0 <= idx < self.count() or not self.itemData(idx):
            return False

        self.setDisabled(self._one_short)
        self.networkChanged.emit(self.itemData(idx))
        self.addressChanged.emit(self.itemText(idx).split(":")[-1].strip())
        return True

    def currentSelect(self) -> str:
        get_func = {
            self.Mode.Address: self.currentAddress,
            self.Mode.Network: self.currentNetwork,
            self.Mode.Interface: self.currentInterface
        }.get(self._mode)

        return get_func() if callable(get_func) else ''

    def currentAddress(self) -> str:
        if not self.count() or not self.itemData(self.currentIndex()):
            return ""

        return self.currentText().split(":")[-1].strip()

    def currentNetwork(self) -> str:
        if not self.count() or not self.itemData(self.currentIndex()):
            return ""

        return self.itemData(self.currentIndex())

    def currentInterface(self) -> str:
        if not self.count() or not self.itemData(self.currentIndex()):
            return ""

        return self.currentText().split(":")[0].strip()

    def setCurrentSelect(self, select: str) -> bool:
        set_func = {
            self.Mode.Address: self.setCurrentAddress,
            self.Mode.Network: self.setCurrentNetwork,
            self.Mode.Interface: self.setCurrentInterface
        }.get(self._mode)

        return set_func(select) if callable(set_func) else False

    def setCurrentAddress(self, address: str) -> bool:
        try:
            idx = [self.itemText(x).split(":")[-1].strip() for x in range(self.count())].index(address)
            self.setCurrentIndex(idx)
            self.slotNicSelected(idx)
            return True
        except ValueError:
            return False

    def setCurrentNetwork(self, network: str) -> bool:
        try:
            idx = [self.itemData(x) for x in range(self.count())].index(network)
            self.setCurrentIndex(idx)
            self.slotNicSelected(idx)
            return True
        except ValueError:
            return False

    def setCurrentInterface(self, interface: str) -> bool:
        try:
            idx = [self.itemText(x).split(":")[0].strip() for x in range(self.count())].index(interface)
            self.setCurrentIndex(idx)
            self.slotNicSelected(idx)
            return True
        except ValueError:
            return False

    def mousePressEvent(self, ev: QtGui.QMouseEvent):
        if ev.button() == Qt.RightButton:
            self.flushNic()

        super(NetworkInterfaceSelector, self).mousePressEvent(ev)


class TabBar(QtWidgets.QTabBar):
    def __init__(self, *args, **kwargs):
        self.tabSize = QtCore.QSize(int(kwargs.pop('width')), int(kwargs.pop('height')))
        super(TabBar, self).__init__(*args, **kwargs)

    def updateTabSize(self, size: QtCore.QSize):
        if isinstance(size, QtCore.QSize):
            self.tabSize = size
            self.update()

    @staticmethod
    def calcHorizonTablePerfectSize(windows_size: QtCore.QSize, tab_number: int) -> Tuple[float, float]:
        return (windows_size.width() / tab_number) - 5, windows_size.height() / 10

    def paintEvent(self, ev: QtGui.QPaintEvent):
        option = QtWidgets.QStyleOptionTab()
        painter = QtWidgets.QStylePainter(self)
        for index in range(self.count()):
            self.initStyleOption(option, index)
            tabRect = self.tabRect(index)
            painter.drawControl(QtWidgets.QStyle.CE_TabBarTabShape, option)
            if self.tabSize.width() > self.tabSize.height():
                painter.drawText(tabRect, Qt.AlignCenter | Qt.TextDontClip, self.tabText(index))
            else:
                painter.drawText(tabRect, Qt.AlignCenter | Qt.TextDontClip, "\n".join(self.tabText(index)))

    def tabSizeHint(self, index: int) -> QtCore.QSize:
        return self.tabSize


def qtTranslate(text: str, views_name: typing.Sequence[str]) -> str:
    try:
        # noinspection PyTypeChecker
        return [tr for tr in [QApplication.translate(view, text) for view in views_name] if tr != text][0]
    except IndexError:
        return text


def updateFilterMenu(options: Sequence[str], menu: QtWidgets.QMenu,
                     group: QtWidgets.QActionGroup, slot: Callable, select: str = ''):
    """Update filter menu

    :param options: menu options
    :param menu: QMenu
    :param group: filter action group
    :param slot: menu filter function
    :param select: default select action
    :return:
    """
    if not isinstance(options, (list, tuple)):
        raise TypeError("options require {!r} not {!r}".format(list.__name__, options.__class__.__name__))

    if not isinstance(menu, QtWidgets.QMenu):
        raise TypeError("menu require {!r} not {!r}".format(QtWidgets.QMenu.__name__, menu.__class__.__name__))

    if not isinstance(group, QtWidgets.QActionGroup):
        raise TypeError("group require {!r} not {!r}".format(QtWidgets.QActionGroup.__name__, group.__class__.__name__))

    if not hasattr(slot, "__call__"):
        raise TypeError("filter_slot require callable")

    # Remove old actions from menu
    for action in menu.actions():
        menu.removeAction(action)
        group.removeAction(action)

    # Add new actions to menu
    for option in options:
        action = QtWidgets.QAction(menu.tr(option), menu)
        action.setCheckable(True)
        action.setActionGroup(group)
        action.triggered.connect(slot)
        menu.addAction(action)

        # Default select all menu
        if option == select:
            action.setChecked(True)

        # Update
        slot()


class ExpandWidget(QtWidgets.QWidget):
    def __init__(self, orientation: Qt.Orientation = Qt.Horizontal, parent: Optional[QtWidgets.QWidget] = None):
        super(ExpandWidget, self).__init__(parent)
        self.setOrientation(orientation)

    def setOrientation(self, orientation: Qt.Orientation):
        if orientation == Qt.Vertical:
            self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        else:
            self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)


class NavigationItem(QtWidgets.QToolButton):
    activated = Signal()
    HOVER_COLOR = (240, 154, 55)
    ACTIVATE_COLOR = (0, 0, 0)
    DEFAULT_COLOR = (255, 255, 255)
    DEFAULT_FONT = 'font: 20pt "宋体";'

    def __init__(self, text: str, icon: str, slot: Optional[Callable] = None, activate_invert: bool = True,
                 font: str = DEFAULT_FONT, hover_color: Color = HOVER_COLOR, default_color: Color = DEFAULT_COLOR,
                 activate_color: Color = ACTIVATE_COLOR, parent: Optional[QtWidgets.QWidget] = None):
        super(NavigationItem, self).__init__(parent)
        self.__text = text
        self.__icon = icon
        self.__slot = slot
        self.__font = font
        self.__activate = False

        # Colors
        self.__hover_color = hover_color
        self.current_color = default_color
        self.__default_color = default_color
        self.__activate_color = activate_color

        # Cached icons with different color
        self.__hover_color_icon = self.__getColoredIcon(self.__hover_color)
        self.current_color_icon = self.__getColoredIcon(self.__default_color)
        self.__default_color_icon = self.__getColoredIcon(self.__default_color)
        self.__activate_color_icon = self.__getColoredIcon(self.__activate_color)

        self.__activate_invert = activate_invert
        self.__action = QtWidgets.QAction(QtGui.QIcon(icon), text, self)
        self.__action.triggered.connect(self.slotSelected)
        self.addAction(self.__action)
        self.setDefaultAction(self.__action)
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.setStyleSheet(self.__color2StyleSheet(self.__default_color))

    @staticmethod
    def __checkColor(new_color: Union[QtGui.QColor, Qt.GlobalColor, Sequence[int]],
                     old_color: Union[QtGui.QColor, Qt.GlobalColor, Sequence[int]]) -> Color:
        if isinstance(new_color, (QtGui.QColor, Qt.GlobalColor)):
            new_color = QtGui.QColor(new_color)
            return new_color.red(), new_color.green(), new_color.blue()
        elif isinstance(new_color, (list, tuple)) and len(new_color) == 3:
            try:
                new_color = QtGui.QColor(new_color[0], new_color[1], new_color[2])
                return new_color.red(), new_color.green(), new_color.blue()
            except (TypeError, ValueError):
                return old_color
        else:
            return old_color

    def __getColoredIcon(self, color: Color) -> QtGui.QPixmap:
        r, g, b = color
        image = QtGui.QImage(self.__icon)
        for x in range(image.width()):
            for y in range(image.height()):
                pixel = image.pixel(x, y)
                image.setPixel(x, y, QtGui.qRgba(r, g, b, QtGui.qAlpha(pixel)))

        return QtGui.QPixmap.fromImage(image)

    def __color2StyleSheet(self, color: Color) -> str:
        return 'color: rgb{}; {}'.format(color, self.__font)

    def _setColorAndIcon(self, color: Color, icon: QtGui.QIcon):
        self.__action.setIcon(icon)
        self.setStyleSheet(self.__color2StyleSheet(color))

    def slotSelected(self):
        self.activated.emit()
        if hasattr(self.__slot, "__call__"):
            self.__slot()

    def text(self) -> str:
        return self.__text

    def isActivate(self) -> bool:
        return self.__activate

    def isActivateInvert(self) -> bool:
        return self.__activate_invert

    def setFold(self, fold: bool):
        self.setToolButtonStyle(Qt.ToolButtonIconOnly if fold else Qt.ToolButtonTextBesideIcon)

    def setActivate(self, activate: bool):
        self.__activate = activate
        if not self.__activate_invert:
            return

        self.current_color = self.__activate_color if activate else self.__default_color
        self.current_color_icon = self.__activate_color_icon if activate else self.__default_color_icon
        self._setColorAndIcon(self.current_color, self.current_color_icon)

    def setHoverColor(self, color: Union[QtGui.QColor, Qt.GlobalColor, Sequence[int]]):
        self.__hover_color = self.__checkColor(color, self.__hover_color)
        self.__hover_color_icon = self.__getColoredIcon(self.__hover_color)

    def setDefaultColor(self, color: Union[QtGui.QColor, Qt.GlobalColor, Sequence[int]]):
        self.__default_color = self.__checkColor(color, self.__default_color)
        self.__default_color_icon = self.__getColoredIcon(self.__default_color)

    def setActivateColor(self, color: Union[QtGui.QColor, Qt.GlobalColor, Sequence[int]]):
        self.__activate_color = self.__checkColor(color, self.__activate_color)
        self.__activate_color_icon = self.__getColoredIcon(self.__activate_color)

    def enterEvent(self, ev: QtCore.QEvent):
        self._setColorAndIcon(self.__hover_color, self.__hover_color_icon)

    def leaveEvent(self, ev: QtCore.QEvent):
        self._setColorAndIcon(self.current_color, self.current_color_icon)


class NavigationBar(QtWidgets.QToolBar):
    def __init__(self, normal_size: QtCore.QSize = QtCore.QSize(64, 64), fold_size: QtCore.QSize = QtCore.QSize(96, 96),
                 moveAble: bool = False, disableHorizontalFold: bool = False,
                 parent: Optional[QtWidgets.QWidget] = None):
        super(NavigationBar, self).__init__(parent)
        from .container import ComponentManager

        self.__fold = False
        self.__items = list()
        self.__fold_size = fold_size
        self.__normal_size = normal_size
        self.__disable_horizontal_fold = disableHorizontalFold

        self.setFloatable(True)
        self.setMovable(moveAble)
        self.setIconSize(self.__normal_size)
        self.setContextMenuPolicy(Qt.PreventContextMenu)
        self.ui_manager = ComponentManager(self.layout())
        self.orientationChanged.connect(self.slotOrientationChanged)

    def isFold(self) -> bool:
        return self.__fold

    def foldExpand(self):
        if self.orientation() == Qt.Horizontal and self.__disable_horizontal_fold and not self.__fold:
            return

        self.__fold = not self.__fold
        self.setIconSize(self.__fold_size if self.__fold else self.__normal_size)
        [item.setFold(self.__fold) for item in self.ui_manager.getByType(NavigationItem)]

    def items(self) -> typing.List[NavigationItem]:
        return self.__items

    def getActionByItemText(self, text: str) -> typing.Optional[QtWidgets.QAction]:
        for idx, item in enumerate(self.__items):
            if item.text() == text:
                return self.actions()[idx]

        return None

    def addItem(self, item: NavigationItem):
        if not isinstance(item, NavigationItem):
            return

        self.addWidget(item)
        self.__items.append(item)
        if item.isActivateInvert():
            item.activated.connect(self.slotActivateItem)

    def addExpandWidget(self):
        self.addWidget(ExpandWidget(self.orientation()))

    def slotActivateItem(self):
        sender = self.sender()
        activate_item = self.getActivateItem()
        if isinstance(activate_item, NavigationItem):
            activate_item.setActivate(False)

        if isinstance(sender, NavigationItem):
            sender.setActivate(True)

    def slotHiddenItem(self, name: str, hidden: bool):
        try:
            self.getActionByItemText(name).setVisible(not hidden)
        except AttributeError:
            pass

    def slotOrientationChanged(self, direction: Qt.Orientation):
        if not self.isFold():
            self.foldExpand()

        if not self.__disable_horizontal_fold:
            return

        if direction == Qt.Horizontal and self.isFold():
            self.foldExpand()

    def setActivateItem(self, name: str):
        for item in self.ui_manager.getByType(NavigationItem):
            if item.text() == name:
                item.activated.emit()

    def getActivateItem(self) -> Optional[NavigationItem]:
        for item in self.ui_manager.getByType(NavigationItem):
            if item.isActivate():
                return item

        return None

    def getActivateItemName(self) -> str:
        item = self.getActivateItem()
        if isinstance(item, NavigationItem):
            return item.text()

        return ""

    def moveEvent(self, ev: QtGui.QMoveEvent):
        for expand_widget in self.ui_manager.getByType(ExpandWidget):
            expand_widget.setOrientation(self.orientation())


class CustomEventFilterHandler(QtCore.QObject):
    def __init__(self, types: Tuple[type, ...], events: Sequence[QtCore.QEvent.Type],
                 parent: Optional[QtWidgets.QWidget] = None):
        super(CustomEventFilterHandler, self).__init__(parent)

        if not isinstance(types, tuple):
            raise TypeError("{!r} request a list or tuple".format("types"))

        if not isinstance(events, (list, tuple)):
            raise TypeError("{!r} request a list or tuple".format("events"))

        self.__filter_types = types
        self.__filter_events = events

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if isinstance(obj, self.__filter_types) and event.type() in self.__filter_events:
            event.ignore()
            return True
        else:
            return super(CustomEventFilterHandler, self).eventFilter(obj, event)

    def process(self, obj: QtCore.QObject, install: bool):
        if isinstance(obj, QtCore.QObject):
            if install:
                obj.installEventFilter(self)
            else:
                obj.removeEventFilter(self)


class ThreadSafeLabel(QtWidgets.QWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None,
                 text: str = "", font: QtGui.QFont = QtGui.QFont("等线 Light", 9),
                 color: Union[QtGui.QColor, Qt.GlobalColor] = Qt.black, align: Qt.AlignmentFlag = Qt.AlignCenter):
        super(ThreadSafeLabel, self).__init__(parent)
        self._text = text
        self._font = font
        self._align = align
        self._color = QtGui.QColor(color)
        self.update()

    def text(self) -> str:
        return self._text[:]

    def setText(self, text: str):
        self._text = text
        metrics = QtGui.QFontMetrics(self.font())
        self.setMinimumWidth(metrics.width(self._text))
        self.update()

    def font(self) -> QtGui.QFont:
        return self._font

    def setFont(self, font: QtGui.QFont):
        if isinstance(font, QtGui.QFont):
            self._font = font

    def color(self) -> QtGui.QColor:
        return self._color

    def setColor(self, color: Union[Qt.GlobalColor, QtGui.QColor]):
        if isinstance(color, (Qt.GlobalColor, QtGui.QColor)):
            self._color = QtGui.QColor(color)
            self.update()

    def setAlignment(self, align: Qt.AlignmentFlag):
        if isinstance(align, Qt.AlignmentFlag):
            self._align = align

    def paintEvent(self, ev: QtGui.QPaintEvent):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        painter.setFont(self.font())
        painter.setPen(QtGui.QPen(self._color))
        # noinspection PyTypeChecker
        painter.drawText(self.rect(), self._align, self._text)

    def sizeHint(self) -> QtCore.QSize:
        metrics = QtGui.QFontMetrics(self.font())
        min_height = metrics.height()
        min_width = metrics.width(self._text) * 1.3
        return QtCore.QSize(int(min_width), int(min_height))


class HyperlinkLabel(ThreadSafeLabel):
    signalClicked = Signal(object)
    DEFAULT_FONT = QtGui.QFont("等线 Light", 9)

    def __init__(self, text: str = "",
                 font: QtGui.QFont = DEFAULT_FONT,
                 selectedFormat: str = "{}",
                 defaultColor: Union[QtGui.QColor, Qt.GlobalColor] = Qt.black,
                 clickedColor: Union[QtGui.QColor, Qt.GlobalColor] = Qt.blue,
                 hoverColor: Union[QtGui.QColor, Qt.GlobalColor] = Qt.blue,
                 hoverFont: QtGui.QFont = DEFAULT_FONT, parent: Optional[QtWidgets.QWidget] = None):
        super(HyperlinkLabel, self).__init__(parent=parent, text=text, font=font, color=defaultColor)
        self._isClicked = False
        self._defaultFont = font
        self._defaultColor = defaultColor

        self._hoverFont = hoverFont
        self._hoverColor = hoverColor
        self._clickedColor = clickedColor
        self._defaultText = text
        self._selectedFormat = selectedFormat

    def reset(self):
        self._isClicked = False
        self.setText(self._defaultText)
        self.setColor(self._defaultColor)

    def click(self):
        self._isClicked = True
        self.setColor(self._clickedColor)
        self.signalClicked.emit(self._defaultText)
        self.setText(self._selectedFormat.format(self._defaultText))

    def isClicked(self) -> bool:
        return self._isClicked

    def enterEvent(self, ev: QtCore.QEvent):
        self.setFont(self._hoverFont)
        self.setColor(self._hoverColor)

    def leaveEvent(self, ev: QtCore.QEvent):
        self.setFont(self._defaultFont)
        self.setColor(self._clickedColor if self._isClicked else self._defaultColor)

    def mousePressEvent(self, ev: QtGui.QMouseEvent):
        self.click()


class CustomTextEditor(QtWidgets.QTextEdit):
    def __init__(self,
                 save_as_title: str = '',
                 actions: Optional[Iterable[CustomAction]] = None, parent: Optional[QtWidgets.QWidget] = None):
        super(CustomTextEditor, self).__init__(parent)
        self.__save_as_title = save_as_title
        self.__customize_actions = actions or list()

        # Register custom action shortcuts
        for action in self.__customize_actions:
            if not action.shortcut:
                continue

            action.ks = QtGui.QKeySequence(action.shortcut)
            shortcut = QtWidgets.QShortcut(action.ks, self)
            shortcut.activated.connect(action.slot)

        # Shortcut for clear all and save as
        self.__save_ks = QtGui.QKeySequence('Ctrl+S')
        self.__clear_ks = QtGui.QKeySequence('Ctrl+Alt+C')

        self.__save_shortcut = QtWidgets.QShortcut(self.__save_ks, self)
        self.__clear_shortcut = QtWidgets.QShortcut(self.__clear_ks, self)

        self.__clear_shortcut.activated.connect(self.clear)
        self.__save_shortcut.activated.connect(self.slotSaveAs)

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent):
        menu = self.createStandardContextMenu(event.pos())
        # Standard clear and save action
        menu.addSeparator()
        menu.addAction('Clear All', self, SLOT(b'clear()'), self.__clear_ks)
        if self.__save_as_title:
            menu.addAction('Save As File', self, SLOT(b'slotSaveAs()'), self.__save_ks)

        # Customize actions
        menu.addSeparator()
        for action in self.__customize_actions:
            act = menu.addAction(action.text)
            act.setShortcut(action.ks)
            # noinspection PyUnresolvedReferences
            act.triggered.connect(action.slot)

        menu.exec_(event.globalPos())

    def slotSaveAs(self):
        if not self.__save_as_title:
            return

        from .dialog import showFileExportDialog
        from .msgbox import showMessageBox, MB_TYPE_INFO
        path = showFileExportDialog(self, '*.txt', title=self.__save_as_title)
        if not path:
            return

        with open(path, 'w', encoding='utf-8') as fp:
            fp.write(self.toPlainText())

        return showMessageBox(self, MB_TYPE_INFO, self.tr('Save success') + f'\n{path}', title=self.tr('Save File'))


class CustomSpinBox(QtWidgets.QSpinBox):
    def __init__(self, value: int = 0, minimum: int = 1, maximum: int = 100,
                 suffix: str = '', prefix: str = '', tips: str = '', align: QtCore.Qt.Alignment = Qt.AlignCenter):
        super(CustomSpinBox, self).__init__()
        self.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.setRange(minimum, maximum)

        if suffix:
            self.setSuffix(suffix)

        if prefix:
            self.setPrefix(prefix)

        self.setValue(value)
        self.setToolTip(tips)
        self.setAlignment(align)
        self.setStatusTip(self.toolTip())

    def minimumSizeHint(self):
        height = super(CustomSpinBox, self).minimumSizeHint().height()
        fm = QtGui.QFontMetrics(self.font())
        width = fm.width(str(self.maximum()))
        return QtCore.QSize(width, height)


class PageNumberBox(CustomSpinBox):
    def setRange(self, minimum: int, maximum: int) -> None:
        super(PageNumberBox, self).setRange(minimum, maximum)
        self.setSuffix(f'/{maximum}')


class DateTimeEdit(QtWidgets.QLineEdit):
    def __init__(self, fmt: str = '%Y/%m/%d %H:%M:%S',
                 timezone: dt.tzinfo = dt.timezone(dt.timedelta(hours=8)),
                 readonly: bool = True, on_the_wall: bool = True, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self.__format = fmt
        self.__timezone = timezone
        self.setReadOnly(readonly)
        self.setText(self.getDateTimeStr())
        if on_the_wall:
            self.startTimer(1000)

    def getDateTime(self):
        return dt.datetime.now(self.__timezone)

    def getDateTimeStr(self, fmt: str = ''):
        return get_timestamp_str(self.getDateTime().timestamp(), fmt or self.__format)

    def timerEvent(self, event: QtCore.QTimerEvent) -> None:
        self.setText(self.getDateTimeStr())


class Separator(QtWidgets.QFrame):
    def __init__(self,
                 shape: QtWidgets.QFrame.Shape = QtWidgets.QFrame.VLine,
                 shadow: QtWidgets.QFrame.Shadow = QtWidgets.QFrame.Sunken, parent: QtWidgets.QWidget = None):
        super(Separator, self).__init__(parent)
        self.setFrameShape(shape)
        self.setFrameShadow(shadow)
