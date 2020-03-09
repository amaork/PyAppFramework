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
           'ThreadSafeLabel',
           'updateFilterMenu']


class SerialPortSelector(QComboBox):
    """List current system exist serial port and LAN raspberry serial port

    """
    # When port selected this signal will emit
    portSelected = Signal(object)
    TIPS = QApplication.translate("SerialPortSelector", "Please select serial port", None, QApplication.UnicodeUTF8)

    def __init__(self, text=TIPS, one_shot=False, parent=None):
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
        self.setToolTip(self.tr("Right click reset and refresh serial port"))

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

    def slotOrientationChanged(self, dir):
        if not self.isFold():
            self.foldExpand()

        if not self.__disable_horizontal_fold:
            return

        if dir == Qt.Horizontal and self.isFold():
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


class ThreadSafeLabel(QWidget):
    def __init__(self, parent=None, text="", font=QFont("等线 Light", 9), align=Qt.AlignCenter):
        super(ThreadSafeLabel, self).__init__(parent)
        self.__text = text
        self.__font = font
        self.__align = align
        self.update()

    def text(self):
        return self.__text[:]

    def setText(self, text):
        self.__text = text
        self.update()

    def font(self):
        return self.__font

    def setFont(self, font):
        if isinstance(font, QFont):
            self.__font = font

    def setAlignment(self, align):
        self.__align = align

    def paintEvent(self, ev):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setFont(self.font())
        painter.drawText(self.rect(), self.__align, self.__text)

    def sizeHint(self):
        metrics = QFontMetrics(self.font())
        min_height = metrics.height()
        min_width = metrics.width(self.__text) * 1.3
        return QSize(min_width, min_height)
