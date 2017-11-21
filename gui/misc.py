# -*- coding: utf-8 -*-
import platform
from PySide.QtGui import *
from PySide.QtCore import *
import serial.tools.list_ports
from ..core.datatype import ip4_check
from raspi_io import Query, RaspiSocketError
__all__ = ['SerialPortSelector', 'TabBar']


class SerialPortSelector(QComboBox):
    """List current system exist serial port and remote system serial port

    """
    # When port selected this signal will emit
    portSelected = Signal(object)

    def __init__(self, text="请选择要使用的串口", one_shot=False, remote="", parent=None):
        """Select serial port

        :param text: selector text
        :param one_shot: only could select once
        :param remote: remote system address for scan raspi_io serial port
        :param parent:
        """
        super(SerialPortSelector, self).__init__(parent)

        self.clear()
        self.__text = text
        self.__selected = ""
        self.__one_shot = one_shot
        self.__system = platform.system().lower()

        # Flush current serial port list
        self.flushSerialPort(remote)
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

    def flushSerialPort(self, remote=""):
        self.clear()
        self.__selected = ""
        self.setEnabled(True)
        self.addItem(self.tr(self.__text))

        # Scan local system serial port
        for index, port in enumerate(list(serial.tools.list_ports.comports())):
            # Windows serial port is a object linux is a tuple
            device = port.device if self.__system == "windows" else port[0]
            desc = "{0:s}".format(device).split(" - ")[-1]
            self.addItem("{0:s}".format(desc).decode("gbk"))
            self.setItemData(index + 1, device)

        # Scan remote system serial port
        if ip4_check(remote):
            try:

                for port in Query(remote).get_serial_list():
                    self.addItem(port, (remote, port))

            except RaspiSocketError:
                pass

    def __slotPortSelected(self, idx):
        if not isinstance(idx, int) or idx == 0 or self.count() == 0:
            return

        self.__selected = self.itemData(idx)
        self.portSelected.emit(self.__selected)
        self.setDisabled(self.__one_shot)


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
