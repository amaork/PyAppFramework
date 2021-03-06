# -*- coding: utf-8 -*-
import glob
import platform
from typing import *
from PySide.QtGui import *
from PySide.QtCore import *
import serial.tools.list_ports
from raspi_io.utility import scan_server
from raspi_io import Query, RaspiSocketError
from ..network.utility import get_system_nic
__all__ = ['SerialPortSelector', 'NetworkInterfaceSelector',
           'TabBar', 'ExpandWidget',
           'NavigationItem', 'NavigationBar',
           'CustomEventFilterHandler',
           'ThreadSafeLabel', 'HyperlinkLabel',
           'updateFilterMenu']


class SerialPortSelector(QComboBox):
    """List current system exist serial port and LAN raspberry serial port

    """
    # When port selected this signal will emit
    portSelected = Signal(object)
    TIPS = QApplication.translate("SerialPortSelector", "Please select serial port", None, QApplication.UnicodeUTF8)

    def __init__(self, text: str or None = TIPS, one_shot: bool = False, parent=None):
        """Select serial port

        :param text: selector text
        :param one_shot: only could select once
        :param parent:
        """
        super(SerialPortSelector, self).__init__(parent)

        self.clear()
        self.__text = text
        self.__one_shot = one_shot
        self.__system = platform.system().lower()
        self.setToolTip(self.tr("Right click reset and refresh serial port"))

        # Flush current serial port list
        self.flushSerialPort()
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
                # Windows serial port is a object linux is a tuple
                device = port.device
                desc = "{0:s}".format(device).split(" - ")[-1]
                self.addItem("{0:s}".format(desc))
                self.setItemData(self.count() - 1, device)

        # Scan LAN raspberry serial port
        try:
            for raspberry in scan_server(timeout):
                for port in Query(raspberry).get_serial_list():
                    self.addItem("{}/{}".format(raspberry, port.split("/")[-1]), (raspberry, port))
        except (RaspiSocketError, IndexError, ValueError, OSError):
            pass

    def slotPortSelected(self, idx):
        if not isinstance(idx, int) or not self.count() or not 0 <= idx < self.count() or not self.itemData(idx):
            return

        self.setDisabled(self.__one_shot)
        self.portSelected.emit(self.itemData(idx))

    def mousePressEvent(self, ev):
        if ev.button() == Qt.RightButton:
            self.flushSerialPort()

        super(SerialPortSelector, self).mousePressEvent(ev)


class NetworkInterfaceSelector(QComboBox):
    networkChanged = Signal(object)
    addressChanged = Signal(object)

    """List current system exist network interface"""
    TIPS = QApplication.translate("NetworkInterfaceSelector", "Please select network interface",
                                  None, QApplication.UnicodeUTF8)

    def __init__(self, text: str or None = TIPS, one_short: bool = False,
                 ignore_loopback: bool = True, network_mode=False, parent=None):
        super(NetworkInterfaceSelector, self).__init__(parent)

        self._text = text
        self._one_short = one_short
        self._ignore_loopback = ignore_loopback
        self.setToolTip(self.tr("Right click reset and refresh network interface"))

        self.flushNic()
        self.currentIndexChanged.connect(self.slotNicSelected)
        self.setNetworkMode() if network_mode else self.setAddressMode()

    def flushNic(self):
        self.clear()
        self.setEnabled(True)

        if self._text:
            self.addItem(self._text)

        for nic_name, nic_attr in get_system_nic(self._ignore_loopback).items():
            self.addItem("{}: {}".format(nic_name, nic_attr.ip), nic_attr.network)

    def isNetworkMode(self):
        return self.property("format") == "network"

    def setNetworkMode(self):
        self.setProperty("format", "network")

    def setAddressMode(self):
        self.setProperty("format", "address")

    def slotNicSelected(self, idx):
        if not isinstance(idx, int) or not self.count() or not 0 <= idx < self.count() or not self.itemData(idx):
            return

        self.setDisabled(self._one_short)
        self.networkChanged.emit(self.itemData(idx))
        self.addressChanged.emit(self.itemText(idx).split(":")[-1].strip())

    def currentSelect(self):
        return self.currentNetwork() if self.isNetworkMode() else self.currentAddress()

    def currentAddress(self) -> str:
        if not self.count() or not self.itemData(self.currentIndex()):
            return ""

        return self.currentText().split(":")[-1].strip()

    def currentNetwork(self) -> str:
        if not self.count() or not self.itemData(self.currentIndex()):
            return ""

        return self.itemData(self.currentIndex())

    def setCurrentSelect(self, select: str) -> None:
        self.setCurrentNetwork(select) if self.isNetworkMode() else self.setCurrentAddress(select)

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

    def mousePressEvent(self, ev):
        if ev.button() == Qt.RightButton:
            self.flushNic()

        super(NetworkInterfaceSelector, self).mousePressEvent(ev)


class TabBar(QTabBar):
    def __init__(self, *args, **kwargs):
        self.tabSize = QSize(kwargs.pop('width'), kwargs.pop('height'))
        super(TabBar, self).__init__(*args, **kwargs)

    def updateTabSize(self, size):
        if isinstance(size, QSize):
            self.tabSize = size
            self.update()

    @staticmethod
    def calcHorizonTablePerfectSize(windows_size, tab_number):
        return (windows_size.width() / tab_number) - 5, windows_size.height() / 10

    def paintEvent(self, ev):
        option = QStyleOptionTab()
        painter = QStylePainter(self)
        for index in range(self.count()):
            self.initStyleOption(option, index)
            tabRect = self.tabRect(index)
            painter.drawControl(QStyle.CE_TabBarTabShape, option)
            if self.tabSize.width() > self.tabSize.height():
                painter.drawText(tabRect, Qt.AlignCenter | Qt.TextDontClip, self.tabText(index))
            else:
                painter.drawText(tabRect, Qt.AlignCenter | Qt.TextDontClip, "\n".join(self.tabText(index)))

    def tabSizeHint(self, index):
        return self.tabSize


def updateFilterMenu(options, menu, group, slot, select=None):
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

    if not isinstance(menu, QMenu):
        raise TypeError("menu require {!r} not {!r}".format(QMenu.__name__, menu.__class__.__name__))

    if not isinstance(group, QActionGroup):
        raise TypeError("group require {!r} not {!r}".format(QActionGroup.__name__, group.__class__.__name__))

    if not hasattr(slot, "__call__"):
        raise TypeError("filter_slot require callable")

    # Remove old actions from menu
    for action in menu.actions():
        menu.removeAction(action)
        group.removeAction(action)

    # Add new actions to menu
    for option in options:
        action = QAction(menu.tr(option), menu)
        action.setCheckable(True)
        action.setActionGroup(group)
        action.triggered.connect(slot)
        menu.addAction(action)

        # Default select all menu
        if option == select:
            action.setChecked(True)

        # Update
        slot()


class ExpandWidget(QWidget):
    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super(ExpandWidget, self).__init__(parent)
        self.setOrientation(orientation)

    def setOrientation(self, orientation):
        if orientation == Qt.Vertical:
            self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        else:
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)


class NavigationItem(QToolButton):
    activated = Signal()
    HOVER_COLOR = (240, 154, 55)
    ACTIVATE_COLOR = (0, 0, 0)
    DEFAULT_COLOR = (255, 255, 255)
    DEFAULT_FONT = 'font: 20pt "宋体";'

    def __init__(self, text, icon, slot=None, activate_invert=True, font=DEFAULT_FONT,
                 hover_color=HOVER_COLOR, default_color=DEFAULT_COLOR, activate_color=ACTIVATE_COLOR, parent=None):
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
        self.__action = QAction(QIcon(icon), text, self)
        self.__action.triggered.connect(self.slotSelected)
        self.addAction(self.__action)
        self.setDefaultAction(self.__action)
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.setStyleSheet(self.__color2StyleSheet(self.__default_color))

    @staticmethod
    def __checkColor(new_color, old_color):
        if isinstance(new_color, (QColor, Qt.GlobalColor)):
            new_color = QColor(new_color)
            return new_color.red(), new_color.green(), new_color.blue()
        elif isinstance(new_color, (list, tuple)) and len(new_color) == 3:
            try:
                new_color = QColor(new_color[0], new_color[1], new_color[2])
                return new_color.red(), new_color.green(), new_color.blue()
            except (TypeError, ValueError):
                return old_color
        else:
            return old_color

    def __getColoredIcon(self, color):
        r, g, b = color
        image = QImage(self.__icon)
        for x in range(image.width()):
            for y in range(image.height()):
                pixel = image.pixel(x, y)
                image.setPixel(x, y, qRgba(r, g, b, qAlpha(pixel)))

        return QPixmap.fromImage(image)

    def __color2StyleSheet(self, color):
        return 'color: rgb{}; {}'.format(color, self.__font)

    def _setColorAndIcon(self, color, icon):
        self.__action.setIcon(icon)
        self.setStyleSheet(self.__color2StyleSheet(color))

    def slotSelected(self):
        self.activated.emit()
        if hasattr(self.__slot, "__call__"):
            self.__slot()

    def text(self):
        return self.__text

    def isActivate(self):
        return self.__activate

    def isActivateInvert(self):
        return self.__activate_invert

    def setFold(self, fold):
        self.setToolButtonStyle(Qt.ToolButtonIconOnly if fold else Qt.ToolButtonTextBesideIcon)

    def setActivate(self, activate):
        self.__activate = activate
        if not self.__activate_invert:
            return

        self.current_color = self.__activate_color if activate else self.__default_color
        self.current_color_icon = self.__activate_color_icon if activate else self.__default_color_icon
        self._setColorAndIcon(self.current_color, self.current_color_icon)

    def setHoverColor(self, color):
        self.__hover_color = self.__checkColor(color, self.__hover_color)
        self.__hover_color_icon = self.__getColoredIcon(self.__hover_color)

    def setDefaultColor(self, color):
        self.__default_color = self.__checkColor(color, self.__default_color)
        self.__default_color_icon = self.__getColoredIcon(self.__default_color)

    def setActivateColor(self, color):
        self.__activate_color = self.__checkColor(color, self.__activate_color)
        self.__activate_color_icon = self.__getColoredIcon(self.__activate_color)

    def enterEvent(self, ev):
        self._setColorAndIcon(self.__hover_color, self.__hover_color_icon)

    def leaveEvent(self, ev):
        self._setColorAndIcon(self.current_color, self.current_color_icon)


class NavigationBar(QToolBar):
    def __init__(self, normal_size=QSize(64, 64), fold_size=QSize(96, 96),
                 moveAble=False, disableHorizontalFold=False, parent=None):
        super(NavigationBar, self).__init__(parent)
        from .container import ComponentManager

        self.__fold = False
        self.__fold_size = fold_size
        self.__normal_size = normal_size
        self.__disable_horizontal_fold = disableHorizontalFold

        self.setFloatable(True)
        self.setMovable(moveAble)
        self.setIconSize(self.__normal_size)
        self.setContextMenuPolicy(Qt.PreventContextMenu)
        self.ui_manager = ComponentManager(self.layout())
        self.orientationChanged.connect(self.slotOrientationChanged)

    def isFold(self):
        return self.__fold

    def foldExpand(self):
        if self.orientation() == Qt.Horizontal and self.__disable_horizontal_fold and not self.__fold:
            return

        self.__fold = not self.__fold
        self.setIconSize(self.__fold_size if self.__fold else self.__normal_size)
        [item.setFold(self.__fold) for item in self.ui_manager.getByType(NavigationItem)]

    def addItem(self, item):
        if not isinstance(item, NavigationItem):
            return

        self.addWidget(item)
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

    def slotOrientationChanged(self, direction):
        if not self.isFold():
            self.foldExpand()

        if not self.__disable_horizontal_fold:
            return

        if direction == Qt.Horizontal and self.isFold():
            self.foldExpand()

    def setActivateItem(self, name):
        for item in self.ui_manager.getByType(NavigationItem):
            if item.text() == name:
                item.activated.emit()

    def getActivateItem(self):
        for item in self.ui_manager.getByType(NavigationItem):
            if item.isActivate():
                return item

        return None

    def getActivateItemName(self):
        item = self.getActivateItem()
        if isinstance(item, NavigationItem):
            return item.text()

        return ""

    def moveEvent(self, ev):
        for expand_widget in self.ui_manager.getByType(ExpandWidget):
            expand_widget.setOrientation(self.orientation())


class CustomEventFilterHandler(QObject):
    def __init__(self, types: tuple, events: list or tuple, parent: QWidget or None = None):
        super(CustomEventFilterHandler, self).__init__(parent)

        if not isinstance(types, tuple):
            raise TypeError("{!r} request a list or tuple".format("types"))

        if not isinstance(events, (list, tuple)):
            raise TypeError("{!r} request a list or tuple".format("events"))

        self.__filter_types = types
        self.__filter_events = events

    def eventFilter(self, obj: QObject, event: QEvent):
        if isinstance(obj, self.__filter_types) and event.type() in self.__filter_events:
            event.ignore()
            return True
        else:
            return super(CustomEventFilterHandler, self).eventFilter(obj, event)

    def process(self, obj: QObject, install: bool):
        if isinstance(obj, QObject):
            if install:
                obj.installEventFilter(self)
            else:
                obj.removeEventFilter(self)


class ThreadSafeLabel(QWidget):
    def __init__(self, parent: QWidget or None = None,
                 text: str = "", font: QFont = QFont("等线 Light", 9),
                 color: QColor or Qt.GlobalColor = Qt.black, align: Qt.AlignmentFlag = Qt.AlignCenter):
        super(ThreadSafeLabel, self).__init__(parent)
        self._text = text
        self._font = font
        self._align = align
        self._color = QColor(color)
        self.update()

    def text(self) -> str:
        return self._text[:]

    def setText(self, text: str):
        self._text = text
        metrics = QFontMetrics(self.font())
        self.setMinimumWidth(metrics.width(self._text))
        self.update()

    def font(self) -> QFont:
        return self._font

    def setFont(self, font: QFont):
        if isinstance(font, QFont):
            self._font = font

    def color(self) -> QColor:
        return self._color

    def setColor(self, color: Qt.GlobalColor or QColor):
        if isinstance(color, (Qt.GlobalColor, QColor)):
            self._color = QColor(color)
            self.update()

    def setAlignment(self, align: Qt.AlignmentFlag):
        if isinstance(align, Qt.AlignmentFlag):
            self._align = align

    def paintEvent(self, ev: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setFont(self.font())
        painter.setPen(QPen(self._color))
        painter.drawText(self.rect(), self._align, self._text)

    def sizeHint(self) -> QSize:
        metrics = QFontMetrics(self.font())
        min_height = metrics.height()
        min_width = metrics.width(self._text) * 1.3
        return QSize(min_width, min_height)


class HyperlinkLabel(ThreadSafeLabel):
    signalClicked = Signal(object)
    DEFAULT_FONT = QFont("等线 Light", 9)

    def __init__(self, text: str = "",
                 font: QFont = DEFAULT_FONT,
                 selectedFormat: str = "{}",
                 defaultColor: QColor or Qt.GlobalColor = Qt.black,
                 clickedColor: QColor or Qt.GlobalColor = Qt.blue,
                 hoverColor: QColor or Qt.GlobalColor = Qt.blue,
                 hoverFont: QFont = DEFAULT_FONT, parent: QWidget or None = None):
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

    def enterEvent(self, ev: QEvent):
        self.setFont(self._hoverFont)
        self.setColor(self._hoverColor)

    def leaveEvent(self, ev: QEvent):
        self.setFont(self._defaultFont)
        self.setColor(self._clickedColor if self._isClicked else self._defaultColor)

    def mousePressEvent(self, ev: QMouseEvent):
        self.click()
