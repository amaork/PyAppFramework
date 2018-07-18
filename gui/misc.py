# -*- coding: utf-8 -*-
import platform
from PySide.QtGui import *
from PySide.QtCore import *
import serial.tools.list_ports
from raspi_io.utility import scan_server
from raspi_io import Query, RaspiSocketError
__all__ = ['SerialPortSelector', 'TabBar', 'updateFilterMenu']


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
        for index, port in enumerate(list(serial.tools.list_ports.comports())):
            # Windows serial port is a object linux is a tuple
            device = port.device if self.__system == "windows" else port[0]
            desc = "{0:s}".format(device).split(" - ")[-1]
            self.addItem("{0:s}".format(desc))
            self.setItemData(index + 1, device)

        # Scan LAN raspberry serial port
        for raspberry in scan_server(timeout):
            try:

                for port in Query(raspberry).get_serial_list():
                    self.addItem("{}/{}".format(raspberry, port.split("/")[-1]), (raspberry, port))

            except (RaspiSocketError, IndexError):
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
