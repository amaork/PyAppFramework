# -*- coding: utf-8 -*-
import glob
import platform
from PySide.QtGui import *
from PySide.QtCore import *
import serial.tools.list_ports
from raspi_io.utility import scan_server
from raspi_io import Query, RaspiSocketError
from .container import ComponentManager
__all__ = ['SerialPortSelector', 'TabBar', 'ExpandWidget',
           'NavigationItem', 'NavigationBar',
           'CustomEventFilterHandler',
           'updateFilterMenu']


class SerialPortSelector(QComboBox):
    """List current system exist serial port and LAN raspberry serial port

    """
    # When port selected this signal will emit
    portSelected = Signal(object)

    def __init__(self, text="请选择要使用的串口", one_shot=False, parent=None):
        """Select serial port

        :param text: selector text
        :param one_shot: only could select once
        :param parent:
        """
        super(SerialPortSelector, self).__init__(parent)

        self.clear()
        self.__text = text
        self.__selected = ""
        self.__one_shot = one_shot
        self.__system = platform.system().lower()
        self.setToolTip(self.tr("右键单击复位并刷新串口"))

        # Flush current serial port list
        self.flushSerialPort()
        self.currentIndexChanged.connect(self.__slotPortSelected)

    def getSelectedPort(self):
        return self.__selected

    def setSelectedPort(self, port):
        ports = [self.itemData(i) for i in range(1, self.count())]
        if port not in ports:
            return False

        index = ports.index(port) + 1
        self.setCurrentIndex(index)
        self.__slotPortSelected(index)
        return True

    def flushSerialPort(self, timeout=0.04):
        self.clear()
        self.__selected = ""
        self.setEnabled(True)
        self.addItem(self.tr(self.__text))

        # Scan local system serial port
        if self.__system == "linux":
            for index, port in enumerate(glob.glob("/dev/tty[A-Za-z]*")):
                self.addItem("{}".format(port))
                self.setItemData(index + 1, port)
        else:
            for index, port in enumerate(list(serial.tools.list_ports.comports())):
                # Windows serial port is a object linux is a tuple
                device = port.device
                desc = "{0:s}".format(device).split(" - ")[-1]
                self.addItem("{0:s}".format(desc))
                self.setItemData(index + 1, device)

        # Scan LAN raspberry serial port
        try:
            for raspberry in scan_server(timeout):
                for port in Query(raspberry).get_serial_list():
                    self.addItem("{}/{}".format(raspberry, port.split("/")[-1]), (raspberry, port))
        except (RaspiSocketError, IndexError, ValueError, OSError):
            pass

    def __slotPortSelected(self, idx):
        if not isinstance(idx, int) or idx == 0 or self.count() == 0:
            return

        self.__selected = self.itemData(idx)
        self.portSelected.emit(self.__selected)
        self.setDisabled(self.__one_shot)

    def mousePressEvent(self, ev):
        if ev.button() == Qt.RightButton:
            self.flushSerialPort()

        super(SerialPortSelector, self).mousePressEvent(ev)


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
    ACTIVATE_STYLE = 'color: rgb(0, 0, 0);font: 20pt "宋体";'
    DEFAULT_STYLE = 'color: rgb(255, 255, 255);font: 20pt "宋体";'

    def __init__(self, text, icon, slot=None, activate_invert=True,
                 default_style=DEFAULT_STYLE, activate_style=ACTIVATE_STYLE, parent=None):
        super(NavigationItem, self).__init__(parent)
        self.__text = text
        self.__icon = icon
        self.__slot = slot
        self.__activate = False
        self.__default_style = default_style
        self.__activate_style = activate_style
        self.__activate_invert = activate_invert
        self.__action = QAction(QIcon(icon), text, self)
        self.__action.triggered.connect(self.slotSelected)
        self.addAction(self.__action)
        self.setDefaultAction(self.__action)
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.setStyleSheet(self.__default_style)

    def slotSelected(self):
        self.activated.emit()
        if hasattr(self.__slot, "__call__"):
            self.__slot()

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
        if activate:
            image = QImage(self.__icon)
            image.invertPixels()
            self.setStyleSheet(self.__activate_style)
            self.__action.setIcon(QPixmap.fromImage(image))
        else:
            self.setStyleSheet(self.__default_style)
            self.__action.setIcon(QIcon(self.__icon))

    def setDefaultStyle(self, style):
        self.__default_style = style

    def setActivateStyle(self, style):
        self.__activate_style = style


class NavigationBar(QToolBar):
    def __init__(self, normal_size=QSize(64, 64), fold_size=QSize(96, 96), moveAble=False, parent=None):
        super(NavigationBar, self).__init__(parent)

        self.__fold = False
        self.__fold_size = fold_size
        self.__normal_size = normal_size
        self.setMovable(moveAble)
        self.setIconSize(self.__normal_size)
        self.setContextMenuPolicy(Qt.PreventContextMenu)
        self.ui_manager = ComponentManager(self.layout())

    def foldExpand(self):
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
    def __init__(self, types, events, parent=None):
        super(CustomEventFilterHandler, self).__init__(parent)

        if not isinstance(types, (list, tuple)):
            raise TypeError("{!r} request a list or tuple".format("objs"))

        if not isinstance(events, (list, tuple)):
            raise TypeError("{!r} request a list or tuple".format("events"))

        self.__filter_types = types
        self.__filter_events = events

    def eventFilter(self, obj, event):
        if isinstance(obj, self.__filter_types) and event.type() in self.__filter_events:
            event.ignore()
            return True
        else:
            return super(CustomEventFilterHandler, self).eventFilter(obj, event)

    def process(self, obj, install):
        if isinstance(obj, QObject):
            if install:
                obj.installEventFilter(self)
            else:
                obj.removeEventFilter(self)
