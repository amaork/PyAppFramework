# -*- coding: utf-8 -*-

"""
Class Tree

TreeWidget
ListWidget
TableWidget
PaintWidget
    |------RgbWidget
    |------LumWidget
    |------ImageWidget
    |------ColorWidget
                |------CursorWidget

LogMessageWidget
SerialPortSettingWidget

BasicJsonSettingWidget
    |------JsonSettingWidget
    |------MultiJsonSettingsWidget
    |------MultiGroupJsonSettingsWidget

MultiTabJsonSettingsWidget
"""
import re
import json
import html
import typing
import logging
import os.path
import collections
from PySide2 import QtWidgets, QtGui, QtCore
from serial import Serial
from PySide2.QtGui import QColor, QPixmap, QPainter, QFont, QPen, QBrush, QImage, QImageReader, QTextCursor,\
    QMouseEvent, QHideEvent, QPaintEvent, QContextMenuEvent, QResizeEvent, QRegExpValidator
from PySide2.QtCore import Qt, Signal, Slot, QPoint, QSize, QDate, QDateTime, QRegExp, QTime, QRect
from PySide2.QtWidgets import QWidget, QApplication, QLayout, QHBoxLayout, QVBoxLayout, QGridLayout, QButtonGroup, \
    QSpinBox, QDoubleSpinBox, QTableWidget, QHeaderView, QSplitter, QLabel, QMenu, QAction, QRadioButton, \
    QCheckBox, QPushButton, QLineEdit, QProgressBar, QDateTimeEdit, QAbstractItemView, QTableWidgetItem, \
    QComboBox, QTreeWidget, QListWidget, QSizePolicy, QTreeWidgetItem, QFileDialog, QColorDialog, QFontDialog, \
    QListWidgetItem, QGroupBox, QTabWidget, QTextEdit, QMainWindow
from datetime import datetime
from typing import Optional, Union, List, Any, Sequence, Tuple, Iterable, Dict, Callable

from .container import ComponentManager
from ..dashboard.input import VirtualNumberInput

from ..misc.debug import LoggerWrap
from ..gui.msgbox import showQuestionBox
from ..misc.windpi import get_program_scale_factor

from .misc import SerialPortSelector, NetworkInterfaceSelector
from ..core.datatype import str2number, str2float, DynamicObject, DynamicObjectDecodeError
from ..misc.settings import UiInputSetting, UiLogMessage, UiLayout, UiFontInput, UiColorInput, \
    UiDoubleInput, UiIntegerInput, UiTextInput, UiFileInput, SystemTrayIconSettings, WindowsPositionSettings


__all__ = ['BasicWidget', 'BasicWindow', 'BasicGroupBox', 'PaintWidget',
           'ColorWidget', 'CursorWidget', 'RgbWidget', 'LumWidget', 'ImageWidget',
           'TableWidget', 'ListWidget', 'TreeWidget',
           'SerialPortSettingWidget', 'LogMessageWidget',
           'BasicJsonSettingWidget', 'JsonSettingWidget', 'MultiJsonSettingsWidget',
           'MultiGroupJsonSettingsWidget', 'MultiTabJsonSettingsWidget']

TableDataFilter = Union[list, tuple, str, UiInputSetting]


class BasicWidget(QWidget):
    Tag = ComponentManager.DefaultObjectNameKey

    def __init__(self, parent: Optional[QWidget] = None):
        super(BasicWidget, self).__init__(parent)

        self._initUi()
        self._initData()
        self._initStyle()
        self._initSignalAndSlots()
        self._initThreadAndTimer()

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

    def initStyle(self):
        self._initStyle()

    @classmethod
    def createGroupBox(cls, title: str, items: typing.Sequence, checkable: bool = False, name: str = '',
                       stretch: typing.Tuple[int, int] = (2, 9), margins: typing.Tuple[int, ...] = (9, 9, 9, 9)):
        layout = QtWidgets.QGridLayout()
        layout.setContentsMargins(*margins)
        layout.setColumnStretch(0, stretch[0])
        layout.setColumnStretch(1, stretch[1])

        group = QtWidgets.QGroupBox(title)
        group.setLayout(layout)
        group.setCheckable(checkable)

        if name:
            group.setProperty(ComponentManager.DefaultObjectNameKey, name)

        for row, item in enumerate(items):
            text, name, widget_cls, range_ = item
            label, widget = cls.createInputWithLabel(text, name, widget_cls, range_)
            layout.addWidget(label, row, 0)
            layout.addWidget(widget, row, 1)

        return group

    @classmethod
    def createInputWithLabel(cls, label: str, key: str, input_cls: QWidget.__class__,
                             range_: typing.Tuple[typing.Union[int, float], typing.Union[int, float]] = None,
                             value: typing.Union[int, float] = None) -> Tuple[QLabel, QWidget]:
        input_ = input_cls()
        label = QLabel(label)
        input_.setProperty(cls.Tag, key)

        if isinstance(input_, (QSpinBox, QDoubleSpinBox)):
            if range_ and len(range_) == 2:
                input_.setRange(*range_)

            if value is not None:
                input_.setValue(value)

        label.setProperty(cls.Tag, "{}_label".format(key))
        return label, input_

    @classmethod
    def createMultiInputWithLabel(cls, texts: Iterable[Tuple[str, str]], input_cls: QWidget.__class__) -> QGridLayout:
        layout = QGridLayout()
        for row, text in enumerate(texts):
            label, key = text
            text = input_cls()
            label = QLabel(label)
            text.setProperty(cls.Tag, key)
            label.setProperty(cls.Tag, "{}_label".format(key))
            layout.addWidget(label, row, 0)
            layout.addWidget(text, row, 1)
        return layout

    @classmethod
    def createButtonGroup(cls, key: str, names: Iterable[str], title: str) -> Tuple[QLabel, QHBoxLayout, QButtonGroup]:
        """Create button group and set button id

        :param key: button group key name
        :param names: button text
        :param title: Radio button title
        :return: button group, and layout
        """
        label = QLabel(title)
        group = QButtonGroup()
        layout = QHBoxLayout()
        group.setProperty(cls.Tag, key)
        for bid, name in enumerate(names):
            button = QRadioButton(name)
            button.setProperty(cls.Tag, name)
            group.addButton(button)
            group.setId(button, bid)
            layout.addWidget(button)

        # Select first
        layout.addWidget(QSplitter())
        group.button(0).setChecked(True)

        return label, layout, group


class BasicWindow(QMainWindow):
    signalTrayIconDoubleClicked = Signal()

    def __init__(self, ui_cls=None, tray_icon_settings: SystemTrayIconSettings = None, parent: QWidget = None):
        QMainWindow.__init__(self, parent)
        self.__en_system_tray_msg_notify = False
        self.__en_minimize_to_system_tray = False
        self.__tray_icon_settings = tray_icon_settings
        if ui_cls:
            self.ui = ui_cls()
            self.ui.setupUi(self)

        self.__initSystemTrayIcon()
        self._initUi()
        self._initData()
        self._initStyle()
        self._initSignalAndSlots()
        self._initThreadAndTimer()

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

    def initStyle(self):
        self._initStyle()

    def isSupportTrayIcon(self) -> bool:
        return isinstance(self.__tray_icon_settings, SystemTrayIconSettings)

    def __initSystemTrayIcon(self):
        if not self.isSupportTrayIcon():
            return

        self.__timer_cnt = 0
        self.__timer_flush_icon = QtCore.QTimer(self)
        self.__timer_flush_icon.timeout.connect(self.slotFlushIcon)

        self.ui_tray_exit = QtWidgets.QAction(self.tr('Exit'))
        self.ui_tray_exit.triggered.connect(self.slotTrayIconExit)

        self.ui_tray_menu = QtWidgets.QMenu(self)
        self.ui_tray_menu.addAction(self.ui_tray_exit)

        self.ui_tray_icon = QtWidgets.QSystemTrayIcon(QtGui.QIcon(self.__tray_icon_settings.icon))
        self.ui_tray_icon.activated.connect(self.slotTrayIconActivated)
        self.ui_tray_icon.setToolTip(self.__tray_icon_settings.tips)
        self.ui_tray_icon.setContextMenu(self.ui_tray_menu)
        self.ui_tray_icon.show()
        QApplication.instance().setQuitOnLastWindowClosed(False)

    def isPin(self) -> bool:
        return bool(self.windowFlags() & Qt.WindowStaysOnTopHint)

    def setPin(self, pin: bool):
        if pin:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)

        self.show()

    def stopFlush(self):
        self.__timer_flush_icon.stop()
        self.ui_tray_icon.setIcon(QtGui.QIcon(self.__tray_icon_settings.icon))

    def startFlush(self, interval: float = 1.0):
        self.__timer_flush_icon.setInterval(int(interval * 1e3))
        self.__timer_flush_icon.start()

    def setEnableSystemTrayMsgNotify(self, en: bool):
        self.__en_system_tray_msg_notify = en

    def setEnableMinimizeToSystemTray(self, en: bool):
        self.__en_minimize_to_system_tray = en

    def addTrayActions(self, actions: typing.Sequence[QAction]):
        before = self.ui_tray_exit

        for action in actions:
            if not isinstance(action, QAction):
                continue

            self.ui_tray_menu.insertAction(before, action)
            before = action

    def loadWindowsPosition(self, config_path: str, prefer_width: int = 0, prefer_height: int = 0):
        pos = WindowsPositionSettings.get(config_path)
        if not pos.isValid():
            pos.setPosition(300, 200, prefer_width, prefer_height)

        self.setGeometry(QRect(*pos.getPosition()))
        if pos.pin:
            self.slotShowTrayIconMsg(self.tr('Pin on top'))
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

    def saveWindowsPosition(self, config_path: str, x_offset: int = 30):
        pos = WindowsPositionSettings.get(config_path)
        pos.update(dict(x=self.x(), y=self.y() + x_offset, width=self.width(), height=self.height(), pin=self.isPin()))
        pos.save(config_path)

    def slotFlushIcon(self):
        self.__timer_cnt += 1
        self.ui_tray_icon.setIcon(QtGui.QIcon(self.__tray_icon_settings.icon if self.__timer_cnt % 2 else ':null.ico'))

    def slotShowTrayIconMsg(self, msg: str, title: str = ''):
        if not self.isSupportTrayIcon() or not self.__en_system_tray_msg_notify:
            return

        self.ui_tray_icon.showMessage(
            title or self.__tray_icon_settings.msg_title, msg, QtGui.QIcon(self.__tray_icon_settings.icon)
        )

    def slotTrayIconExit(self) -> bool:
        """Can't exit return false"""
        if callable(self.__tray_icon_settings.exit_callback):
            if self.__tray_icon_settings.exit_callback():
                QtWidgets.QApplication.exit()
                return True
            else:
                return False
        else:
            if showQuestionBox(
                    parent=self, title=self.tr('Exit confirm'),
                    content=self.tr('Are you sure to exit') + f': {self.__tray_icon_settings.msg_title} ?',
            ):
                QtWidgets.QApplication.exit()
                return True
            else:
                return False

    def slotTrayIconActivated(self, reason: QtWidgets.QSystemTrayIcon.ActivationReason):
        if self.isHidden():
            self.showNormal()

        if reason == QtWidgets.QSystemTrayIcon.DoubleClick:
            self.signalTrayIconDoubleClicked.emit()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self.isSupportTrayIcon():
            if self.__en_minimize_to_system_tray:
                self.hide()
                event.ignore()
                self.slotShowTrayIconMsg(
                    self.__tray_icon_settings.minimize_msg or
                    self.tr('Minimize to system tray, click to restore display')
                )
            else:
                if not self.slotTrayIconExit():
                    event.ignore()
        else:
            QtWidgets.QApplication.exit()


class BasicGroupBox(QGroupBox):
    Tag = ComponentManager.DefaultObjectNameKey

    def __init__(self, parent: Optional[QWidget] = None):
        super(BasicGroupBox, self).__init__(parent)

        self._initUi()
        self._initData()
        self._initStyle()
        self._initSignalAndSlots()
        self._initThreadAndTimer()

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

    def initStyle(self):
        self._initStyle()

    @classmethod
    def createInputWithLabel(cls, label: str, key: str, input_cls: QWidget.__class__,
                             range_: typing.Tuple[typing.Union[int, float], typing.Union[int, float]] = None,
                             value: typing.Union[int, float] = None) -> Tuple[QLabel, QWidget]:
        return BasicWidget.createInputWithLabel(label, key, input_cls, range_, value)

    @classmethod
    def createMultiInputWithLabel(cls, texts: Iterable[Tuple[str, str]], input_cls: QWidget.__class__) -> QGridLayout:
        return BasicWidget.createMultiInputWithLabel(texts, input_cls)

    @classmethod
    def createButtonGroup(cls, key: str, names: Iterable[str], title: str) -> Tuple[QLabel, QHBoxLayout, QButtonGroup]:
        return BasicWidget.createButtonGroup(key, names, title)


class PaintWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        """Base class provide basic draw functions and get widget message """

        super(PaintWidget, self).__init__(parent)

    def getXRatio(self, maxValue: Union[int, float]) -> int:
        if not self.isNumber(maxValue):
            return 0

        if isinstance(maxValue, int):
            maxValue = float(maxValue)

        x = self.cursor().pos().x()
        return int(round(maxValue / self.width() * x))

    def getYRatio(self, maxValue: Union[int, float]) -> int:
        if not self.isNumber(maxValue):
            return 0

        if isinstance(maxValue, int):
            maxValue = float(maxValue)

        y = self.cursor().pos().y()
        return int(round(maxValue / self.height() * y))

    def getCursorPos(self) -> Tuple[int, int]:
        x = self.cursor().pos().x()
        y = self.cursor().pos().y()
        return x, y

    def getCursorLum(self) -> int:
        """Get current cursor position luminance

        :return:
        """
        x, y = self.getCursorPos()
        color = QColor(QPixmap().grabWindow(self.winId()).toImage().pixel(x, y))
        return max(color.red(), color.green(), color.blue())

    def getDynamicTextPos(self, fontSize: int, textSize: int) -> QPoint:
        """Get dynamic text position

        :param fontSize: Font size
        :param textSize: Text length
        :return:QPoint
        :return:QPoint
        """
        if not isinstance(fontSize, int) or not isinstance(textSize, int):
            return QPoint(self.width() // 2, self.height() // 2)

        # Get mouse position
        x, y = self.getCursorPos()

        # Offset
        offset = 3

        if x < self.width() / 2:
            tx = x + fontSize * offset
        else:
            tx = x - (textSize + offset - 1) * fontSize

        if y < self.height() / 2:
            ty = y + fontSize * offset
        else:
            ty = y - fontSize * (offset - 1)

        return QPoint(tx, ty)

    def drawCenterText(self, painter: QPainter, font: QFont, color: Union[QColor, Qt.GlobalColor], text: str):
        """Draw dynamic text follow mouse movement

        :param painter:
        :param font: Text Font
        :param color: Text color
        :param text: draw text
        :return:
        """
        if not isinstance(painter, QPainter) or not isinstance(font, QFont) or not self.isColor(color):
            print("TypeError")
            return

        try:
            painter.setFont(font)
            painter.setPen(QPen(QColor(color)))
            painter.drawText(self.rect(), Qt.AlignCenter, text)
        except TypeError:
            print("Text TypeError")

    def drawDynamicText(self, painter: QPainter, font: QFont, color: Union[QColor, Qt.GlobalColor], text: str):
        """Draw dynamic text follow mouse movement

        :param painter:
        :param font: Text Font
        :param color: Text color
        :param text: draw text
        :return:
        """
        if not isinstance(painter, QPainter) or not isinstance(font, QFont) or not self.isColor(color):
            return

        if not isinstance(text, str):
            return

        painter.setFont(font)
        painter.setPen(QPen(QColor(color)))
        painter.drawText(self.getDynamicTextPos(font.pointSize(), len(text)), text)

    def drawSquare(self, painter: QPainter, color: Union[QColor, Qt.GlobalColor], start: QPoint, side: int):
        return self.drawRectangle(painter, color, start, side, side)

    def drawRectangle(self, painter: QPainter,
                      color: Union[QColor, Qt.GlobalColor],
                      start: QPoint, width: int, height: int) -> bool:
        """Draw Rectangle at start point

        :param painter:QPainter
        :param color: Rectangle background color
        :param start: Rectangle upper left conner point position
        :param width: Rectangle width
        :param height:Rectangle height
        :return:
        """
        if not isinstance(painter, QPainter) or not self.isColor(color):
            return False

        if not isinstance(start, QPoint) or not self.isValidWidth(width) or not self.isValidHeight(height):
            return False

        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(QColor(color)))
        painter.drawRect(start.x(), start.y(), width, height)
        return True

    def drawCenterRect(self, painter: QPainter, color: Union[QColor, Qt.GlobalColor], width: int, height: int) -> bool:
        if not self.isValidWidth(width) or not self.isValidHeight(height):
            return False

        x = self.rect().center().x()
        y = self.rect().center().y()
        start = QPoint(x - width / 2, y - height / 2)
        return self.drawRectangle(painter, color, start, width, height)

    def drawCenterSquare(self, painter: QPainter, color: Union[QColor, Qt.GlobalColor], side: int) -> bool:
        return self.drawCenterRect(painter, color, side, side)

    def drawBackground(self, painter: QPainter, color: Union[QColor, Qt.GlobalColor]) -> bool:
        if not isinstance(painter, QPainter) or not self.isColor(color):
            return False

        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(QColor(color)))
        painter.drawRect(self.rect())
        return True

    def drawHorizontalLine(self, painter: QPainter, color: Union[QColor, Qt.GlobalColor], y: int, xs: int, xe: int):
        """Draw a horizontal line at y form xs to xe

        :param painter:
        :param color: line color
        :param y: Vertical pos
        :param xs:Horizontal line start
        :param xe:Horizontal line end
        :return:True or false
        """
        if not isinstance(painter, QPainter) or not self.isColor(color):
            return

        if not self.isValidHeight(y) or not self.isValidHRange(xs, xe):
            return

        painter.setPen(QPen(color))
        painter.drawLine(QPoint(xs, y), QPoint(xe, y))

    def drawVerticalLine(self, painter: QPainter, color: Union[QColor, Qt.GlobalColor], x: int, ys: int, ye: int):
        """

        :param painter:
        :param color: line color
        :param x: Horizontal pos
        :param ys: Vertical line start
        :param ye: Vertical line end
        :return:
        """
        if not isinstance(painter, QPainter) or not self.isColor(color):
            return

        if not self.isValidWidth(x) or not self.isValidVRange(ys, ye):
            return

        painter.setPen(QPen(color))
        painter.drawLine(QPoint(x, ys), QPoint(x, ye))

    @staticmethod
    def adjustColorBrightness(color: Union[QColor, Qt.GlobalColor], brightness: int) -> QColor:
        """Adjust color brightness

        :param color: QColor
        :param brightness: brightness value (0 - 255)
        :return:success return after just color, else black
        """

        if not PaintWidget.isColor(color) or not PaintWidget.isNumber(brightness):
            return QColor(Qt.black)

        if brightness < 0 or brightness > 255:
            return QColor(Qt.black)

        color = QColor(color)
        if color.black():
            color.setRed(255 - brightness)
            color.setGreen(255 - brightness)
            color.setBlue(255 - brightness)
            return color

        if color.red():
            color.setRed(brightness)

        if color.green():
            color.setGreen(brightness)

        if color.blue():
            color.setBlue(brightness)

        return color

    @staticmethod
    def getMonitorResolution() -> QSize:
        return QApplication.desktop().screenGeometry().size()

    @staticmethod
    def getColorMode(color: Union[QColor, Qt.GlobalColor]) -> int:
        """Return color mode, blue -> 1, red -> 4 white -> 7

        :param color:
        :return:
        """

        if not PaintWidget.isColor(color):
            return 0

        mode = 0
        color = QColor(color)

        if color.red():
            mode |= 4

        if color.green():
            mode |= 2

        if color.blue():
            mode |= 1

        return mode

    @staticmethod
    def getColorRawValue(color: Union[QColor, Qt.GlobalColor]) -> int:
        if not PaintWidget.isColor(color):
            return 0

        color = QColor(color)
        return color.rgb() & 0xffffff

    @staticmethod
    def getRgbMode(r: int, g: int, b: int) -> int:
        """From rgb to rgb mode (255, 0, 0) -> 4 (True, True, True) -> 7

        :param r: Red color value or is red set boolean value
        :param g: Green color value or is red set boolean value
        :param b: Blue color value or is set boolean value
        :return:
        """
        mode = 0
        if r:
            mode |= 4

        if g:
            mode |= 2

        if b:
            mode |= 1

        return mode

    @staticmethod
    def isColor(color: Any) -> bool:
        if not isinstance(color, QColor) and not isinstance(color, Qt.GlobalColor):
            return False

        return True

    @staticmethod
    def isNumber(number: Any) -> bool:
        if not isinstance(number, float) and not isinstance(number, int):
            return False

        return True

    def isValidWidth(self, x: int) -> bool:
        if x < 0 or x > self.width():
            return False

        return True

    def isValidHeight(self, y: int) -> bool:
        if y < 0 or y > self.height():
            return False

        return True

    def isValidHRange(self, start: int, end: int) -> bool:
        if not self.isValidWidth(start) or not self.isValidWidth(end):
            return False

        return start < end

    def isValidVRange(self, start: int, end: int) -> bool:
        if not self.isValidHeight(start) or not self.isValidHeight(end):
            return False

        return start < end


class ColorWidget(PaintWidget):
    colorMax = 255.0

    # When color changed will send is signal, r, g, b value
    colorChanged = Signal(int, int, int)

    # When mouse release send this signal
    colorStopChange = Signal(int, int, int)

    def __init__(self, font: QFont = QFont("Times New Roman", 10), parent: Optional[QWidget] = None):
        """Color grab widget double click mouse left button change color, mouse horizontal move change color brightness

        ColorWidget provide two signal 'colorChanged' and 'colorStopChange', when mouse horizontal moved, the color
        will changed, the 'colorChanged' signal will send. 'colorStopChange' signal will send when the mouse is stop .

        Signal: colorChanged(int r, int g, int b)
        Signal: colorStopChange(int r, int g, int b)

        :param font: Color r, g, b value display font
        :param parent:
        :return: None, double click mouse right button will exit
        """
        super(ColorWidget, self).__init__(parent)
        # Enter full screen mode
        self.showFullScreen()

        # Default setting
        self.font = QFont("Times New Roman", 10)
        if isinstance(font, QFont):
            self.font = font

        # Color list
        self.colorIndex = -1
        self.color = (Qt.white, Qt.black)
        self.colorTable = [(Qt.blue, Qt.white), (Qt.green, Qt.black), (Qt.cyan, Qt.black), (Qt.red, Qt.white),
                           (Qt.magenta, Qt.white), (Qt.yellow, Qt.black), (Qt.white, Qt.black), (Qt.black, Qt.white)]

    def getColor(self) -> Tuple[Qt.GlobalColor, Qt.GlobalColor]:
        self.colorIndex += 1
        if self.colorIndex >= len(self.colorTable):
            self.colorIndex = 0

        return self.colorTable[self.colorIndex]

    def addColor(self, color: Sequence[Union[QColor, Qt.GlobalColor]]) -> bool:
        """Add color to color group

        :param color: (QColor, QColor)
        :return:
        """
        if not isinstance(color, (tuple, list)) or len(color) != 2:
            return False

        if not isinstance(color[0], QColor) or not isinstance(color[1], QColor):
            return False

        self.colorTable.append(color)
        return True

    def getBackgroundColor(self) -> QColor:
        return QColor(self.color[0])

    def getForegroundColor(self) -> QColor:
        return QColor(self.color[1])

    def mouseDoubleClickEvent(self, ev: QMouseEvent):
        # Left button change background color
        if ev.button() == Qt.LeftButton:
            self.color = self.getColor()
            self.update()
        # Right button exit
        elif ev.button() == Qt.RightButton:
            self.close()

    def mouseReleaseEvent(self, ev: QMouseEvent):
        # Send color changed signal
        if ev.button() == Qt.LeftButton:
            value = self.getXRatio(self.colorMax)
            color = ColorWidget.adjustColorBrightness(self.getBackgroundColor(), value)
            self.colorChanged.emit(color.red(), color.green(), color.blue())
            self.colorStopChange.emit(color.red(), color.green(), color.blue())

    def mouseMoveEvent(self, ev: QMouseEvent):
        # Update re paint
        self.update()

    def paintEvent(self, ev: QPaintEvent):
        painter = QPainter(self)
        value = self.getXRatio(self.colorMax)
        color = ColorWidget.adjustColorBrightness(self.getBackgroundColor(), value)
        textColor = Qt.white if self.getCursorLum() < 64 else self.getForegroundColor()
        text = "R:{0:d}, G:{1:d}, B{2:d}".format(color.red(), color.green(), color.blue())

        # Send color changed signal
        self.colorChanged.emit(color.red(), color.green(), color.blue())

        # Draw cross line and cursor pos
        self.drawBackground(painter, color)
        self.drawDynamicText(painter, self.font, textColor, text)


class CursorWidget(ColorWidget):
    # When cursor changed will send this signal
    cursorChanged = Signal(int, int, int)

    # When cursor stop changed will send this signal
    cursorStopChange = Signal(int, int, int)

    def __init__(self, font: QFont = QFont("Times New Roman", 10), parent: Optional[QWidget] = None):
        """Cursor grab widget, double click mouse left button change color, mouse moved change cursor position

        CursorWidget provide two signal 'cursorChanged' and 'cursorStopChange', when mouse moved, the cursor position
        will be changed, the 'cursorChanged' signal will send.
        'cursorStopChange' signal will send when the mouse is stop.

        Signal: cursorChanged(int x, int y, int backgroundColor)
        Signal: cursorStopChange(int x, int y, int backgroundColor)

        1 signal inherited from ColorWidget: colorChanged

        :param font:Cursor position display font
        :param parent:
        :return:
        """
        super(CursorWidget, self).__init__(font, parent)
        self.color = (Qt.white, Qt.black)
        self.oldColor = self.getForegroundColor()
        self.remap_width, self.remap_height = self.width(), self.height()

    def __remapCursor(self, x: int, y: int) -> Tuple[int, int]:
        px = 1 if x == 0 else self.remap_width * 1.0 / self.width() * (x + 1)
        py = 1 if y == 0 else self.remap_height * 1.0 / self.height() * (y + 1)
        return int(round(px)) - 1, int(round(py)) - 1

    def setRemap(self, width: int, height: int) -> bool:
        """Set cursor remap width and height

        :param width: remap width
        :param height: remap height
        :return:
        """
        if not isinstance(width, int) or not isinstance(height, int):
            print("setRemap TypeError:{}, {}".format(type(width), type(height)))
            return False

        self.remap_width = width
        self.remap_height = height
        return True

    def mouseReleaseEvent(self, ev: QMouseEvent):
        # Send color changed signal
        if self.getBackgroundColor() != self.oldColor:
            color = self.getBackgroundColor()
            self.colorChanged.emit(color.red(), color.green(), color.blue())

        # Mouse release and cursor position changed send mouse pos
        if ev.button() == Qt.LeftButton:
            x = ev.pos().x()
            y = ev.pos().y()
            rx, ry = self.__remapCursor(x, y)
            self.cursorChanged.emit(rx, ry, self.getColorRawValue(self.getBackgroundColor()))
            self.cursorStopChange.emit(rx, ry, self.getColorRawValue(self.getBackgroundColor()))

    def paintEvent(self, ev: QPaintEvent):
        painter = QPainter(self)
        x, y = self.getCursorPos()
        rx, ry = self.__remapCursor(x, y)
        text = "X:{0:d}, Y:{1:d}".format(rx, ry)

        # Cursor changed
        self.cursorChanged.emit(rx, ry, self.getColorRawValue(self.getBackgroundColor()))

        # Draw cross line and cursor pos
        self.drawBackground(painter, self.getBackgroundColor())
        self.drawVerticalLine(painter, self.getForegroundColor(), x, 0, self.height())
        self.drawHorizontalLine(painter, self.getForegroundColor(), y, 0, self.width())
        self.drawDynamicText(painter, self.font, self.getForegroundColor(), text)


class RgbWidget(PaintWidget):
    # When r, g, b changed send this signal
    rgbChanged = Signal(bool, bool, bool)

    def __init__(self, parent: Optional[QWidget] = None):
        """ RGB color control widget, double-click the color zone will turn of or turn off this color.

        When color states changed will send 'rgbChanged' signal

        Signal:rgbChanged(bool rState, bool gState, bool bState)

        :param parent:
        :return:
        """
        super(RgbWidget, self).__init__(parent)
        self.showFullScreen()
        self.rgb = [True, True, True]
        self.part = int(self.height() / 3)
        self.colorTable = (Qt.red, Qt.green, Qt.blue)
        self.rgbChanged.emit(self.rgb[0], self.rgb[1], self.rgb[2])

    def mouseDoubleClickEvent(self, ev: QMouseEvent):
        # Left button change background color
        if ev.button() == Qt.LeftButton:
            _, y = self.getCursorPos()
            if y < self.part:
                self.rgb[0] = not self.rgb[0]
            elif (y > self.part) and (y < self.part * 2):
                self.rgb[1] = not self.rgb[1]
            else:
                self.rgb[2] = not self.rgb[2]

            self.update()

        # Right button exit
        elif ev.button() == Qt.RightButton:
            self.close()

    def hideEvent(self, ev: QHideEvent):
        self.rgbChanged.emit(True, True, True)

    def paintEvent(self, ev: QPaintEvent):
        painter = QPainter(self)
        self.rgbChanged.emit(self.rgb[0], self.rgb[1], self.rgb[2])

        for idx, rgb in enumerate(self.rgb):
            if rgb:
                color = self.colorTable[idx]
            else:
                color = Qt.black
                self.drawHorizontalLine(painter, QColor(Qt.white), idx * self.part - 1, 0, self.width())

            self.drawRectangle(painter, color, QPoint(0, idx * self.part), self.width(), self.part)


class LumWidget(PaintWidget):
    # Lum max value
    lumMax = 255.0

    # When lum changed will send this signal hi, low, mode
    lumChanged = Signal(int, int, int)
    lumStopChange = Signal(int, int, int)

    # Lum mode
    CE1_MODE = 1
    CE2_MODE = 2
    LF_MODE = 3
    UD_MODE = 4
    CT_MODE = 5
    LUM_MODE = (CE1_MODE, CE2_MODE, LF_MODE, UD_MODE, CT_MODE)

    def __init__(self, font: QFont = QFont("Times New Roman", 10), parent: Optional[QWidget] = None):
        """Luminance grab widget, double click mouse left button change mode, mouse moved change windows Luminance

        Press mouse left button, then move mouse will change the low luminance
        Press mouse right button, then move mouse will change the high luminance

        LumWidget provide 2 signal 'lumChanged' and 'lumStopChange', when mouse moved, the windows Luminance
        will be changed, the 'lumChanged' signal will send. 'lumStopChange' signal will send when the mouse is stop .

        Signal: lumChanged(int hi, int low, int mode)
        Signal: lumStopChange(int hi, int low, int mode)

        :param font:Windows Luminance display font
        :param parent:
        :return:
        """
        super(LumWidget, self).__init__(parent)
        self.showFullScreen()

        if isinstance(font, QFont):
            self.font = QFont("Times New Roman", 10)

        # Default is center windows
        self.lumIndex = 0
        self.lumMode = self.CE1_MODE

        # Default adjust low lum
        self.adjustHigh = False
        self.lum = [0, int(self.lumMax)]
        self.oldLum = [int(self.lumMax), 0]

    def getLumMode(self) -> int:
        self.lumIndex += 1
        if self.lumIndex >= len(self.LUM_MODE):
            self.lumIndex = 0

        return self.LUM_MODE[self.lumIndex]

    def getLowLum(self) -> QColor:
        return QColor(self.lum[0], self.lum[0], self.lum[0])

    def getHighLum(self) -> QColor:
        return QColor(self.lum[1], self.lum[1], self.lum[1])

    def mouseMoveEvent(self, ev: QMouseEvent):
        self.lum[self.adjustHigh] = self.getXRatio(self.lumMax)
        self.update()

    def mousePressEvent(self, ev: QMouseEvent):
        # If left key press adjust low
        if ev.button() == Qt.LeftButton:
            self.adjustHigh = False
        # Right button press adjust high
        elif ev.button() == Qt.RightButton:
            self.adjustHigh = True

    def mouseReleaseEvent(self, ev: QMouseEvent):
        if self.lum != self.oldLum:
            self.oldLum = self.lum
            self.lumChanged.emit(self.lum[1], self.lum[0], self.lumMode)
            self.lumStopChange.emit(self.lum[1], self.lum[0], self.lumMode)

    def mouseDoubleClickEvent(self, ev: QMouseEvent):
        # Left button change background color
        if ev.button() == Qt.LeftButton:
            self.lumMode = self.getLumMode()
            self.lum = [0, int(self.lumMax)]
            self.update()

        # Right button exit
        elif ev.button() == Qt.RightButton:
            self.close()

    def paintEvent(self, ev: QPaintEvent):
        painter = QPainter(self)
        self.drawBackground(painter, self.getLowLum())
        textColor = Qt.white if self.getCursorLum() < 64 else Qt.black
        text = "Hi:{0:d} Low:{1:d}".format(int(self.lum[1]), int(self.lum[0]))

        # Send lum changed signal
        self.lumChanged.emit(self.lum[1], self.lum[0], self.lumMode)

        if self.lumMode == self.CE1_MODE:
            self.drawCenterSquare(painter, self.getHighLum(), self.height() // 2)
        elif self.lumMode == self.CE2_MODE:
            self.drawCenterRect(painter, self.getHighLum(), self.width() // 2, self.height() // 2)
        elif self.lumMode == self.LF_MODE:
            self.drawRectangle(painter, self.getHighLum(), QPoint(0, 0), self.width() // 2, self.height())
        elif self.lumMode == self.UD_MODE:
            self.drawRectangle(painter, self.getHighLum(), QPoint(0, 0), self.width(), self.height() // 2)
        elif self.lumMode == self.CT_MODE:
            side = self.height() // 7
            self.drawBackground(painter, QColor(127, 127, 127))
            self.drawCenterSquare(painter, self.getHighLum(), side)
            self.drawSquare(painter, self.getLowLum(), QPoint(self.width() // 2 - side // 2, side), side)
            self.drawSquare(painter, self.getLowLum(), QPoint(self.width() // 2 - side // 2, side * 5), side)
            self.drawSquare(painter, self.getLowLum(), QPoint(int(self.width() / 2 - side * 2.5), side * 3), side)
            self.drawSquare(painter, self.getLowLum(), QPoint(int(self.width() / 2 + side * 1.5), side * 3), side)

        self.drawDynamicText(painter, self.font, textColor, text)


class ImageWidget(PaintWidget):
    def __init__(self, width: int = 0, height: int = 0,
                 zoomInRatio: int = 0, zoomInArea: int = 20, parent: Optional[QWidget] = None):
        """ImageWidget provide 3 method to draw an image

        drawFromFs  :   load an image from filesystem and show it
        drawFromMem :   load an image form memory data and show it
        drawFromText:   Dynamic draw an image with text

        :param width: widget fixed width
        :param height:widget fixed height
        :param zoomInRatio: zoom in ratio 0 is turn off
        :param zoomInArea: zoom in area width and height
        :param parent:
        :return:
        """
        super(ImageWidget, self).__init__(parent)
        self.supportFormats = [str(name) for name in QImageReader.supportedImageFormats()]

        # Default setting
        self.text = ""
        self.textColor = Qt.black
        self.bgColor = Qt.lightGray
        self.textFont = QFont("Times New Roman", width // 16)

        # Draw image using
        self.image = QImage()

        # For grab cursor position pixel
        self.zoomInX = 0
        self.zoomInY = 0
        self.zoomInFlag = False
        self.zoomInPattern = QPixmap()
        self.zoomInArea = zoomInArea if isinstance(zoomInArea, int) else 20
        self.zoomInRatio = zoomInRatio if isinstance(zoomInRatio, int) else 0

        self.setMinimumSize(width, height)

    @staticmethod
    def scaleBigImage(img_size: QSize, rule: QSize = QSize(4096, 4096), factor: int = 2) -> QSize:
        if img_size.width() <= rule.width() and img_size.height() <= rule.height():
            return img_size
        else:
            return ImageWidget.scaleBigImage(img_size / factor, rule, factor)

    @Slot(str)
    def drawFromFs(self, filePath: str) -> bool:
        """Load an image from filesystem, then display it

        :param filePath: Image file path
        :return:
        """
        if not isinstance(filePath, str) or not os.path.isfile(filePath):
            print("File path:{} is not exist!".format(filePath))
            return False

        reader = QImageReader(filePath)
        reader.setAutoTransform(True)
        reader.setDecideFormatFromContent(True)
        reader.setScaledSize(self.scaleBigImage(reader.size()))
        if not len(reader.format()):
            print("File is not a image file:{}".format(reader.errorString()))
            return False

        # Load image file to memory
        self.image = reader.read()
        self.update()
        return True

    @Slot(object, object)
    def drawFromMem(self, data: bytes, imageFormat: str = 'bmp') -> bool:
        """Load image form memory

        :param data: Image data
        :param imageFormat: Image format
        :return:
        """
        if not isinstance(data, bytes) or len(data) == 0:
            print("Invalid image data:{}".format(type(data)))
            return False

        imageFormat = str(imageFormat.encode())
        if not isinstance(imageFormat, str) or imageFormat not in self.supportFormats:
            print("Invalid image format:{}".format(imageFormat))
            return False

        # Clear loadImageFromFs data
        # QImage fromData(const uchar * data, int size, const char * format = 0)
        # noinspection PyTypeChecker
        self.image = QImage.fromData(data, imageFormat)
        self.update()
        return True

    @Slot(str)
    def drawFromText(self, text: str, textColor: Union[QColor, Qt.GlobalColor] = Qt.black,
                     bgColor: Union[QColor, Qt.GlobalColor] = Qt.lightGray, fontSize: int = 40):
        """Draw a text message in the center of the widget

        :param text: Text context
        :param textColor: Text color
        :param bgColor: Widget background color
        :param fontSize: fontSize
        :return:
        """
        if not isinstance(text, str):
            print("text require :{!r}".format(text.__class__.__name__))
            return False

        if len(text) == 0:
            return False

        if self.isColor(bgColor):
            self.bgColor = bgColor

        if self.isColor(textColor):
            self.textColor = textColor

        if isinstance(fontSize, int):
            self.textFont.setPointSize(fontSize)

        # From text max length get max text size
        textMaxLength = max([len(t) for t in text.split('\n')])
        fontMaxWidth = round(self.width() / textMaxLength) / 1.2

        if self.textFont.pointSize() > fontMaxWidth:
            self.textFont.setPointSize(fontMaxWidth)

        self.text = self.tr(text)
        self.image = QImage()
        self.update()

    def paintEvent(self, ev: QPaintEvent):
        painter = QPainter(self)

        # Is image show it
        if not self.image.isNull():
            painter.drawImage(self.rect(), self.image)
        # Draw text and show
        else:
            self.drawBackground(painter, self.bgColor)
            self.drawCenterText(painter, self.textFont, self.textColor, self.text)

        # If zoom in flag superimposed zoom in pattern
        if self.zoomInFlag:
            if self.zoomInX < self.width() / 2:
                x = self.zoomInX + 15
            else:
                x = self.zoomInX - 15 - self.zoomInPattern.width()

            if self.zoomInY < self.height() / 2:
                y = self.zoomInY + 15
            else:
                y = self.zoomInY - 15 - self.zoomInPattern.height()

            painter.drawPixmap(x, y, self.zoomInPattern)

    def mouseMoveEvent(self, ev: QMouseEvent):
        if not self.zoomInRatio:
            return

        # Clear zoom in flag
        self.zoomInFlag = False

        self.zoomInX = ev.x()
        self.zoomInY = ev.y()
        ratio = self.zoomInRatio

        # Cursor move out of the range
        if self.zoomInX < -8 or self.zoomInX >= self.width() \
                or self.zoomInY < -8 or self.zoomInY >= self.height():
            self.update()
            return

        # Grab cursor pointer pattern
        sample = QPixmap()
        sample = sample.grabWidget(self, self.zoomInX, self.zoomInY, self.zoomInArea, self.zoomInArea)
        self.zoomInPattern = sample.scaled(sample.width() * ratio, sample.height() * ratio, Qt.KeepAspectRatio)

        # Update call paintEvent
        self.zoomInFlag = True
        self.update()

    def mouseReleaseEvent(self, ev: QMouseEvent):
        # Mouse release will clear zoom in flag
        self.zoomInFlag = False
        self.update()


class TableWidget(QTableWidget):
    tableDataChanged = Signal()
    ALL_ACTION = 0xF
    SUPPORT_ACTIONS = (0x1, 0x2, 0x4, 0x8)
    ACTION = collections.namedtuple('Action', ['COMM', 'MOVE', 'FROZEN', 'CUSTOM'])(*SUPPORT_ACTIONS)

    def __init__(self, max_column: int, hide_header: bool = False,
                 disable_custom_content_menu: bool = False, parent: Optional[QWidget] = None):
        """Create a QTableWidget

        :param max_column: max column number
        :param hide_header: hide vertical and horizontal header
        :param parent:
        :return:
        """
        super(TableWidget, self).__init__(parent)

        self.setColumnCount(max_column)
        self.hideHeaders(hide_header)
        self.__table_filters = dict()
        self.__autoHeight = False

        self.__columnMaxWidth = dict()
        self.__columnStretchFactor = list()
        self.__columnStretchMode = QHeaderView.Fixed

        self.__contextMenu = QMenu(self)
        self.__contextMenuEnableMask = 0x0

        for group, actions in {
            self.ACTION.COMM: [
                (QAction(self.tr("Clear All"), self), self.clearTableData),
            ],

            self.ACTION.MOVE: [
                (QAction(self.tr("Move Up"), self), lambda: self.rowMoveUp()),
                (QAction(self.tr("Move Down"), self), lambda: self.rowMoveDown()),

                (QAction(self.tr("Move to Top"), self), lambda: self.rowMove2Top()),
                (QAction(self.tr("Move to Bottom"), self), lambda: self.rowMove2Bottom())
            ],
        }.items():
            for action, slot in actions:
                # noinspection PyUnresolvedReferences
                action.triggered.connect(slot)
                action.setProperty("group", group)
                self.__contextMenu.addAction(action)

            self.__contextMenu.addSeparator()

        self.__scale_x, self.__scale_y = get_program_scale_factor()
        if not disable_custom_content_menu:
            self.customContextMenuRequested.connect(self.__slotShowContextMenu)
        self.setVerticalHeaderHeight(int(self.getVerticalHeaderHeight() * self.__scale_y))

    # noinspection PyMethodOverriding
    def tr(self, text: str) -> str:
        # noinspection PyTypeChecker
        return QApplication.translate("TableWidget", text, None)

    def __checkRow(self, row: int) -> bool:
        if not isinstance(row, int):
            print("TypeError:{}".format(type(row)))
            return False

        if abs(row) >= self.rowCount():
            print("Row range error, max row: {0:d}".format(self.rowCount()))
            return False

        return True

    def __checkColumn(self, column: int) -> bool:
        if not isinstance(column, int):
            print("TypeError:{}".format(type(column)))
            return False

        if abs(column) >= self.columnCount():
            print("Column range error, max column: {0:d}".format(self.columnCount()))
            return False

        return True

    def __autoRowIndex(self, row_idx: int) -> int:
        row_count = self.rowCount()
        return row_idx if 0 <= row_idx < row_count else row_count + row_idx

    def __autoColumnIndex(self, column_idx: int) -> int:
        column_count = self.columnCount()
        return column_idx if 0 <= column_idx < column_count else column_count + column_idx

    @staticmethod
    def __copyWidget(widget: QWidget) -> QWidget:
        temp = widget
        if not isinstance(widget, QWidget):
            return widget

        if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
            temp = QSpinBox() if isinstance(widget, QSpinBox) else QDoubleSpinBox()
            temp.setRange(widget.minimum(), widget.maximum())
            temp.setSingleStep(widget.singleStep())
            if isinstance(temp, QDoubleSpinBox):
                temp.setDecimals(widget.decimals())
            temp.setEnabled(widget.isEnabled())
            temp.setValue(widget.value())
        elif isinstance(widget, QCheckBox):
            temp = QCheckBox()
            temp.setText(widget.text())
            temp.setChecked(widget.isChecked())
            temp.setEnabled(widget.isEnabled())
        elif isinstance(widget, QComboBox):
            temp = QComboBox()
            temp.addItems([widget.itemText(x) for x in range(widget.count())])
            temp.setCurrentIndex(widget.currentIndex())
            temp.setEnabled(widget.isEnabled())
        elif isinstance(widget, QDateTimeEdit):
            temp = QDateTimeEdit()
            temp.setDateTime(widget.dateTime())
            temp.setEnabled(widget.isEnabled())
            temp.setCalendarPopup(widget.calendarPopup())
        elif isinstance(widget, QPushButton):
            temp = QPushButton(widget.text())
            widget.setHidden(True)
            widget.deleteLater()
        elif isinstance(widget, QProgressBar):
            temp = QProgressBar()
            temp.setInvertedAppearance(widget.invertedAppearance())
            temp.setRange(widget.minimum(), widget.maximum())
            temp.setTextVisible(widget.isTextVisible())
            temp.setFormat(widget.format())
            temp.setValue(widget.value())

        # Copy widget property
        for key in widget.dynamicPropertyNames():
            key = bytes(key).decode()
            # Internal using, do not copy
            if key.startswith('_'):
                continue
            temp.setProperty(key, widget.property(key))
            if key == "clicked" and isinstance(widget, QPushButton):
                temp.clicked.connect(widget.property(key))

        return temp

    def __slotShowContextMenu(self, pos: QPoint):
        for group in self.SUPPORT_ACTIONS:
            enabled = group & self.__contextMenuEnableMask

            if enabled and group in (self.ACTION.MOVE, self.ACTION.FROZEN):
                if not self.rowCount():
                    return

            for action in self.__contextMenu.actions():
                if action.property("group") == group:
                    action.setVisible(enabled)

        self.__contextMenu.popup(self.viewport().mapToGlobal(pos))

    def __slotWidgetDataChanged(self):
        self.tableDataChanged.emit()

    def setAutoWidth(self):
        self.setColumnStretchFactor([1 / self.columnCount()] * self.columnCount())

    def setAutoHeight(self, enable: bool):
        self.__autoHeight = enable
        self.resize(self.geometry().width(), self.geometry().height())

    def setContextMenuMask(self, mask: int):
        for group in self.SUPPORT_ACTIONS:
            if mask & group:
                self.__contextMenuEnableMask |= group
            else:
                self.__contextMenuEnableMask &= ~group

        if self.__contextMenuEnableMask:
            self.setContextMenuPolicy(Qt.CustomContextMenu)
        else:
            self.setContextMenuPolicy(Qt.DefaultContextMenu)

    def setCustomContextMenu(self, menu: List[QAction]):
        for action in menu:
            if not isinstance(action, QAction):
                continue

            action.setProperty("group", self.ACTION.CUSTOM)
            self.__contextMenu.addAction(action)

        self.__contextMenu.addSeparator()

    def resizeColumnWidthFitContents(self):
        header = self.horizontalHeader()
        for column in range(self.columnCount()):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)

    def setColumnMaxWidth(self, column: int, max_width: int):
        if not self.__checkColumn(column):
            return

        column = self.__autoColumnIndex(column)
        self.__columnMaxWidth[column] = max_width

    def setColumnStretchFactor(self, factors: Sequence[float], mode: QHeaderView.ResizeMode = QHeaderView.Fixed):
        if not isinstance(factors, (list, tuple)):
            return

        if len(factors) > self.columnCount():
            return

        self.__columnStretchMode = mode
        self.__columnStretchFactor = factors
        self.resize(self.geometry().width(), self.geometry().height())

    def setItemBackground(self, row: int, column: int, background: QBrush) -> bool:
        if not self.__checkRow(row) or not self.__checkColumn(column) or not isinstance(background, QBrush):
            return False

        try:
            item = self.item(row, column)
            item.setBackground(background)
        except AttributeError:
            return False

        return True

    def setItemForeground(self, row: int, column: int, foreground: QBrush) -> bool:
        if not self.__checkRow(row) or not self.__checkColumn(column) or not isinstance(foreground, QBrush):
            return False

        try:
            item = self.item(row, column)
            item.setForeground(foreground)
        except AttributeError:
            return False

        return True

    @Slot(bool)
    def hideHeaders(self, hide: bool):
        self.hideRowHeader(hide)
        self.hideColumnHeader(hide)

    @Slot(bool)
    def hideRowHeader(self, hide: bool):
        self.verticalHeader().setVisible(not hide)

    @Slot(bool)
    def hideColumnHeader(self, hide: bool):
        self.horizontalHeader().setVisible(not hide)

    def getVerticalHeaderHeight(self) -> int:
        vertical_header = self.verticalHeader()
        return vertical_header.defaultSectionSize()

    def setVerticalHeaderHeight(self, height: int):
        vertical_header = self.verticalHeader()
        vertical_header.setSectionResizeMode(QHeaderView.Fixed)
        vertical_header.setDefaultSectionSize(height)
        self.setVerticalHeader(vertical_header)

    def getHorizontalHeaderWidth(self) -> int:
        horizontal_header = self.horizontalHeader()
        return horizontal_header.defaultSectionSize()

    def setHorizontalHeaderWidth(self, width: int):
        horizontal_header = self.horizontalHeader()
        horizontal_header.setSectionResizeMode(QHeaderView.Fixed)
        horizontal_header.setDefaultSectionSize(width)
        self.setHorizontalHeader(horizontal_header)

    def disableScrollBar(self, horizontal: bool, vertical: bool):
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff if vertical else Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff if horizontal else Qt.ScrollBarAsNeeded)

    @Slot()
    def rowMoveUp(self):
        row = self.currentRow()
        if row == 0:
            return
        self.swapRow(row, row - 1)

    @Slot()
    def rowMoveDown(self):
        row = self.currentRow()
        if row == self.rowCount() - 1:
            return
        self.swapRow(row, row + 1)

    def rowMove2Top(self):
        while self.currentRow() != 0:
            self.rowMoveUp()

        self.simulateSelectRow(0)

    def rowMove2Bottom(self):
        while self.currentRow() != self.rowCount() - 1:
            self.rowMoveDown()

        self.simulateSelectRow(self.rowCount() - 1)

    @Slot()
    def columnMoveLeft(self):
        column = self.currentColumn()
        if column == 0:
            return
        self.swapColumn(column, column - 1)

    @Slot()
    def columnMoveRight(self):
        column = self.currentColumn()
        if column == self.columnCount() - 1:
            return
        self.swapColumn(column, column + 1)

    @Slot()
    def setNoSelection(self):
        self.setFocusPolicy(Qt.NoFocus)
        self.setSelectionMode(QAbstractItemView.NoSelection)

    @Slot()
    def setRowSelectMode(self):
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

    @Slot()
    def setItemSelectMode(self):
        self.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

    @Slot()
    def setColumnSelectMode(self):
        self.setSelectionBehavior(QAbstractItemView.SelectColumns)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

    def simulateSelectRow(self, row: int):
        self.selectRow(row)
        self.setFocus(Qt.MouseFocusReason)
        self.scrollTo(self.model().index(row, 0))

    def simulateSelectColumn(self, column: int):
        self.selectColumn(column)
        self.setFocus(Qt.MouseFocusReason)
        self.scrollTo(self.model().index(0, column))

    def frozenItem(self, row: int, column: int, frozen: bool) -> bool:
        """Frozen or unfroze a item

        :param row: item row number
        :param column: item column number
        :param frozen: True -> Frozen, False -> Unfrozen
        :return: True / False
        """
        if not self.__checkRow(row) or not self.__checkColumn(column):
            return False

        # Item
        item = self.item(row, column)
        if isinstance(item, QTableWidgetItem):
            flags = item.flags()
            if frozen:
                flags &= ~Qt.ItemIsEditable
            else:
                flags |= Qt.ItemIsEditable
            item.setFlags(flags)

        # Widget:
        widget = self.cellWidget(row, column)
        if isinstance(widget, QWidget):
            widget.setDisabled(frozen)

        return True

    def frozenTable(self, frozen: bool) -> bool:
        for row in range(self.rowCount()):
            if not self.frozenRow(row, frozen):
                return False

        return True

    def frozenRow(self, row: int, frozen: bool) -> bool:
        """Frozen or unfrozen a row item

        :param row: row number start from 0
        :param frozen: True -> Frozen, False -> Unfrozen
        :return: True / False
        """
        for column in range(self.columnCount()):
            if not self.frozenItem(row, column, frozen):
                return False

        return True

    def frozenColumn(self, column: int, frozen: bool) -> bool:
        """Frozen or unfrozen a column item

        :param column: column number
        :param frozen: True -> Frozen, False -> Unfrozen
        :return: True / False
        """
        for row in range(self.rowCount()):
            if not self.frozenItem(row, column, frozen):
                return False

        return True

    def swapItem(self, src_row: int, src_column: int, dst_row: int, dst_column: int):
        if not self.__checkRow(src_row) or not self.__checkRow(dst_row):
            print("Row number[{0:d}, {1:d}] out of range".format(src_row, dst_row))
            return False

        if not self.__checkColumn(src_column) or not self.__checkColumn(dst_column):
            print("Column number[{0:d}, {1:d}] out of range".format(src_column, dst_column))
            return False

        src_item = self.takeItem(src_row, src_column)
        src_widget = self.__copyWidget(self.cellWidget(src_row, src_column))

        dst_item = self.takeItem(dst_row, dst_column)
        dst_widget = self.__copyWidget(self.cellWidget(dst_row, dst_column))

        # Both CellWidget
        if isinstance(src_widget, QWidget) and isinstance(dst_widget, QWidget):
            self.removeCellWidget(src_row, src_column)
            self.removeCellWidget(dst_row, dst_column)
            self.setCellWidget(src_row, src_column, dst_widget)
            self.setCellWidget(dst_row, dst_column, src_widget)
        # Src is CellWidget dst is not
        elif isinstance(src_widget, QWidget) and not isinstance(dst_widget, QWidget):
            self.removeCellWidget(src_row, src_column)
            self.setCellWidget(dst_row, dst_column, src_widget)
            if isinstance(dst_item, QTableWidgetItem):
                self.setItem(src_row, src_column, dst_item)
        # Dst is CellWidget src is not
        elif isinstance(dst_widget, QWidget) and not isinstance(src_widget, QWidget):
            self.removeCellWidget(dst_row, dst_column)
            self.setCellWidget(src_row, src_column, dst_widget)
            if isinstance(src_item, QTableWidgetItem):
                self.setItem(dst_row, dst_column, src_item)
        else:
            if isinstance(dst_item, QTableWidgetItem):
                self.setItem(src_row, src_column, dst_item)

            if isinstance(src_item, QTableWidgetItem):
                self.setItem(dst_row, dst_column, src_item)

    def swapRow(self, src: int, dst: int):
        """Swap src and dst row data

        :param src: src row number
        :param dst: dst row number
        :return:
        """

        for column in range(self.columnCount()):
            self.swapItem(src, column, dst, column)

        # Select dst row
        self.selectRow(dst)
        self.tableDataChanged.emit()

    def swapColumn(self, src: int, dst: int):
        """Swap src and dst column data

        :param src: source column number
        :param dst: destination column number
        :return:
        """

        for row in range(self.rowCount()):
            self.swapItem(row, src, row, dst)

        # Select destination column
        self.selectColumn(dst)
        self.tableDataChanged.emit()

    def delRow(self, row: int):
        self.removeRow(row)
        self.tableDataChanged.emit()

    def setRow(self, row: int, data: Sequence[Any], property_: Optional[Sequence[Any]] = None):
        if not hasattr(data, "__iter__"):
            print("TypeError: item should a iterable")
            return False

        if len(data) > self.columnCount():
            print("Item length too much")
            return False

        for column, item_data in enumerate(data):
            try:
                if isinstance(item_data, QTableWidgetItem):
                    item = item_data
                else:
                    item = QTableWidgetItem("{}".format(item_data))
                    if property_:
                        try:
                            item.setData(Qt.UserRole, property_[column])
                        except (AttributeError, IndexError):
                            pass

                self.setItem(row, column, item)

                # Get column filters
                filters = self.__table_filters.get(column)
                if filters:
                    self.setItemDataFilter(row, column, filters)
                    self.setItemData(row, column, item_data)

            except ValueError as e:
                print("TableWidget setRow error: {}".format(e))
                continue

        self.tableDataChanged.emit()
        return True

    def addRow(self, data: Sequence[Any], property_: Optional[Sequence[Any]] = None):
        """Add a row and set row property data

        :param data: row data should be an iterable object
        :param property_: row hidden property data
        :return:
        """
        # Increase row count
        row = self.rowCount()
        self.setRowCount(row + 1)

        # Add data to row
        self.setRow(row, data, property_)

        # Select current item
        self.selectRow(row)

    def insRow(self, row: int, data: Sequence[Any], property_: Optional[Sequence[Any]] = None) -> bool:
        """Insert row and set item data

        :param row: row to insert
        :param data: row data
        :param property_: row properties
        :return:
        """
        self.insertRow(row)
        return self.setRow(row, data, property_)

    def insRowByOrder(self, key: Callable[[Sequence[str]], bool], data: Sequence[Any], property_: Sequence[Any] = None):
        for row in range(self.rowCount()):
            if key(self.getRowData(row)):
                return self.insRow(row, data, property_)
        else:
            # Table is empty
            return self.insRow(0, data, property_)

    def setRowBackgroundColor(self, row: int, color: QBrush):
        [self.setItemBackground(row, column, color) for column in range(self.columnCount())]

    def setRowForegroundColor(self, row: int, color: QBrush):
        [self.setItemForeground(row, column, color) for column in range(self.columnCount())]

    def setColumnBackgroundColor(self, column: int, color: QBrush):
        [self.setItemBackground(row, column, color) for row in range(self.rowCount())]

    def setColumnForegroundColor(self, column: int, color: QBrush):
        [self.setItemForeground(row, column, color) for row in range(self.rowCount())]

    def setRowHeader(self, data: Sequence[str]):
        if not hasattr(data, "__iter__"):
            print("TypeError: item should a iterable")
            return False

        if len(data) > self.rowCount():
            print("Item length too much")
            return False

        for row, text in enumerate(data):
            if not isinstance(text, str):
                continue
            self.takeVerticalHeaderItem(row)
            header = QTableWidgetItem(self.tr(text))
            self.setVerticalHeaderItem(row, header)

        self.hideRowHeader(False)

    def setColumnHeader(self, data: Sequence[str], align: Qt.Alignment = Qt.AlignCenter):
        if not hasattr(data, "__iter__"):
            print("TypeError: item should a iterable")
            return False

        if len(data) > self.columnCount():
            print("Item length too much")
            return False

        for column, text in enumerate(data):
            if not isinstance(text, str):
                continue
            self.takeHorizontalHeaderItem(column)
            header = QTableWidgetItem(self.tr(text))
            header.setTextAlignment(align)
            self.setHorizontalHeaderItem(column, header)

        self.hideColumnHeader(False)

    def setRowAlignment(self, row: int, alignment: Qt.AlignmentFlag) -> bool:
        if not isinstance(alignment, Qt.AlignmentFlag):
            print("TypeError:{}".format(type(alignment)))
            return False

        if not self.__checkRow(row):
            return False

        for column in range(self.columnCount()):
            try:
                item = self.item(row, column)
                item.setTextAlignment(alignment)
            except AttributeError:
                continue

        return True

    def setColumnAlignment(self, column: int, alignment: Qt.AlignmentFlag) -> bool:
        if not isinstance(alignment, Qt.AlignmentFlag):
            print("TypeError:{}".format(type(alignment)))
            return False

        if not self.__checkColumn(column):
            return False

        for row in range(self.rowCount()):
            try:
                item = self.item(row, column)
                item.setTextAlignment(alignment)
            except AttributeError:
                continue

        return True

    def setTableAlignment(self, alignment: Qt.AlignmentFlag) -> bool:
        for row in range(self.rowCount()):
            if not self.setRowAlignment(row, alignment):
                return False

        return True

    def setItemData(self, row: int, column: int, data: Any, property_: Optional[Any] = None):
        if not self.__checkRow(row) or not self.__checkColumn(column):
            return False

        try:

            item = self.item(row, column)
            if isinstance(item, QTableWidgetItem):
                item.setText("{}".format(data))
                if property_ is not None:
                    item.setData(Qt.UserRole, property_)
            else:
                widget = self.__copyWidget(self.cellWidget(row, column))
                if isinstance(widget, (QSpinBox, QDoubleSpinBox)) and isinstance(data, (int, float)):
                    widget.setValue(data)
                    widget.valueChanged.connect(self.__slotWidgetDataChanged)
                    self.cellWidget(row, column).setHidden(True)
                    self.removeCellWidget(row, column)
                    self.setCellWidget(row, column, widget)
                elif isinstance(widget, QCheckBox) and isinstance(data, bool):
                    widget.setChecked(data)
                    widget.stateChanged.connect(self.__slotWidgetDataChanged)
                    self.cellWidget(row, column).setHidden(True)
                    self.removeCellWidget(row, column)
                    self.setCellWidget(row, column, widget)
                elif isinstance(widget, QComboBox) and isinstance(data, int) and data < widget.count():
                    widget.setCurrentIndex(data)
                    # noinspection PyUnresolvedReferences
                    widget.currentIndexChanged.connect(self.__slotWidgetDataChanged)
                    self.cellWidget(row, column).setHidden(True)
                    self.removeCellWidget(row, column)
                    self.setCellWidget(row, column, widget)
                elif isinstance(widget, QDateTimeEdit) and isinstance(data, datetime):
                    date = QDate(data.year, data.month, data.day)
                    time = QTime(data.hour, data.minute, data.second)
                    widget.setDateTime(QDateTime(date, time))
                    # noinspection PyUnresolvedReferences
                    widget.dateTimeChanged.connect(self.__slotWidgetDataChanged)
                    self.removeCellWidget(row, column)
                    self.setCellWidget(row, column, widget)
                elif isinstance(widget, QPushButton) and isinstance(data, object):
                    widget.setProperty("private", data)
                    self.removeCellWidget(row, column)
                    self.setCellWidget(row, column, widget)
                elif isinstance(widget, QProgressBar) and isinstance(data, (int, float)):
                    widget.setValue(data)
                    self.removeCellWidget(row, column)
                    self.setCellWidget(row, column, widget)
                else:
                    return False

            self.tableDataChanged.emit()
            return True

        except Exception as e:
            print("Set table item data error:{}".format(e))
            return False

    def setItemProperty(self, row: int, column: int, property_: Any):
        if not self.__checkRow(row) or not self.__checkColumn(column):
            return None

        item = self.item(row, column)
        if isinstance(item, QTableWidgetItem):
            item.setData(Qt.UserRole, property_)

    def setItemDataFilter(self, row: int, column: int, filters: TableDataFilter) -> bool:
        if not self.__checkRow(row) or not self.__checkColumn(column):
            return False

        try:

            if not isinstance(filters, (list, tuple, str, UiInputSetting)):
                return False

            # Normal text
            if isinstance(filters, str):
                widget = self.cellWidget(row, column)
                if isinstance(widget, QWidget):
                    self.cellWidget(row, column).setHidden(True)
                    self.removeCellWidget(row, column)
                item = self.item(row, column)
                item.setText(filters)
            # Number type QSpinbox(int, int) or QDoubleSpinbox(float, float) set spinbox range
            elif len(filters) == 2 and isinstance(filters[0], type(filters[1])) and \
                    isinstance(filters[0], (int, float)):
                spinbox = QSpinBox() if isinstance(filters[0], int) else QDoubleSpinBox()
                spinbox.setRange(filters[0], filters[1])
                value = self.getItemData(row, column)
                value = str2number(value) if isinstance(filters[0], int) else str2float(value)
                spinbox.setValue(value)
                spinbox.valueChanged.connect(self.__slotWidgetDataChanged)
                self.takeItem(row, column)
                self.setCellWidget(row, column, spinbox)
            # Bool type QCheckBox(bool, "Desc text")
            elif len(filters) == 2 and isinstance(filters[0], bool) and isinstance(filters[1], str):
                widget = QCheckBox(self.tr(filters[1]))
                widget.stateChanged.connect(self.__slotWidgetDataChanged)
                widget.setChecked(filters[0])
                self.takeItem(row, column)
                self.setCellWidget(row, column, widget)
            # Datetime type QDatetimeEdit (datetime.datetime, python_datetime_format, qt_datetime_format)
            elif len(filters) == 3 and isinstance(filters[0], datetime) and isinstance(filters[2], str):
                try:
                    value = self.getItemData(row, column)
                    datetime.strptime(value, filters[1])
                    dt = QDateTime.fromString(value, filters[2])
                except (TypeError, ValueError):
                    dt = filters[0]
                    date = QDate(dt.year, dt.month, dt.day)
                    time = QTime(dt.hour, dt.minute, dt.second)
                    dt = QDateTime(date, time)

                widget = QDateTimeEdit(dt)
                widget.setCalendarPopup(True)
                widget.setProperty("format", filters[2])
                # noinspection PyUnresolvedReferences
                widget.dateTimeChanged.connect(self.__slotWidgetDataChanged)
                self.takeItem(row, column)
                self.setCellWidget(row, column, widget)
            # Self-defined type data QPushButton (button_text, callback, private_data)
            elif len(filters) == 3 and isinstance(filters[0], str) and hasattr(filters[1], "__call__"):
                button = QPushButton(self.tr(filters[0]))
                button.clicked.connect(filters[1])
                button.setProperty("clicked", filters[1])
                button.setProperty("private", filters[2])
                button.setProperty('index', self.model().index(row, column))
                button.setProperty("dataChanged", self.__slotWidgetDataChanged)
                self.takeItem(row, column)
                self.setCellWidget(row, column, button)
            # Label with color
            elif len(filters) == 2 and isinstance(filters[0], str) and isinstance(filters[1], QColor):
                item = QTableWidgetItem(filters[0])
                item.setBackground(QBrush(filters[1]))
                item.setTextAlignment(Qt.AlignCenter)
                self.takeItem(row, column)
                self.setItem(row, column, item)
                self.frozenItem(row, column, True)
            # Progress bar
            elif len(filters) == 3 and isinstance(filters[0], QProgressBar) and isinstance(filters[1], bool) \
                    and isinstance(filters[1], (int, float)):
                progress = QProgressBar()
                progress.setValue(filters[2])
                progress.setTextVisible(filters[1])
                self.takeItem(row, column)
                self.setCellWidget(row, column, progress)
            # QComboBox (list) or tuple
            elif isinstance(filters, (list, tuple)):
                widget = QComboBox()
                widget.addItems(filters)
                value = self.getItemData(row, column)
                try:
                    value = int(value)
                except ValueError:
                    value = filters.index(value) if value in filters else 0
                    widget.setProperty("format", "text")
                widget.setCurrentIndex(value)
                # noinspection PyUnresolvedReferences
                widget.currentIndexChanged.connect(self.__slotWidgetDataChanged)
                self.takeItem(row, column)
                self.setCellWidget(row, column, widget)
            elif isinstance(filters, UiInputSetting):
                # Create widget, set data and connect signal and slot
                widget = JsonSettingWidget.createInputWidget(filters, parent=self)
                ComponentManager.setComponentData(widget, self.getItemData(row, column))
                ComponentManager.connectComponentSignalAndSlot(widget, lambda _: self.__slotWidgetDataChanged())

                self.takeItem(row, column)
                self.setCellWidget(row, column, widget)
            else:
                return False

            return True

        except Exception as e:
            print("Set table item filter error:{}".format(e))
            return False

    def setRowData(self, row: int, data: Sequence[Any]) -> bool:
        try:
            if len(data) != self.columnCount() or not 0 <= row < self.rowCount():
                return False

            for column, item_data in enumerate(data):
                self.setItemData(row, column, item_data)

            return True
        except TypeError:
            return False

    def setRowDataFilter(self, row: int, filters: TableDataFilter) -> bool:
        for column in range(self.columnCount()):
            if not self.setItemDataFilter(row, column, filters):
                return False

        return True

    def setColumnData(self, column: int, data: Sequence[Any]):
        try:
            if len(data) != self.rowCount() or not 0 <= column < self.columnCount():
                return False

            for row, item_data in enumerate(data):
                self.setItemData(row, column, item_data)
        except TypeError:
            return False

    def setColumnDataFilter(self, column: int, filters: TableDataFilter) -> bool:
        for row in range(self.rowCount()):
            if not self.setItemDataFilter(row, column, filters):
                return False

        return True

    def setTableDataFilter(self, filters: Dict[int, TableDataFilter]) -> bool:
        if not isinstance(filters, dict):
            return False

        self.__table_filters = filters
        return True

    def setTableData(self, table_data: Sequence[Sequence[Any]]) -> bool:
        try:
            for row, data in enumerate(table_data):
                self.setRowData(row, data)
            return True
        except TypeError:
            print("{!r} request a list or tuple not {!r}".format("table_data", table_data.__class__.__name__))
            return False

    def getItemData(self, row: int, column: int) -> Any:
        if not self.__checkRow(row) or not self.__checkColumn(column):
            return None

        item = self.item(row, column)
        widget = self.cellWidget(row, column)
        if isinstance(widget, QSpinBox):
            return widget.value()
        elif isinstance(widget, QDoubleSpinBox):
            return widget.value()
        elif isinstance(widget, QCheckBox):
            return widget.isChecked()
        elif isinstance(widget, QComboBox):
            return widget.currentText() if widget.property("format") else widget.currentIndex()
        elif isinstance(widget, QDateTimeEdit):
            return widget.dateTime().toString(widget.property("format"))
        elif isinstance(widget, QPushButton):
            return widget.property("private")
        elif isinstance(widget, QProgressBar):
            return widget.value()
        elif isinstance(item, QTableWidgetItem):
            return item.text()
        else:
            return ""

    def getItemProperty(self, row: int, column: int) -> Optional[Any]:
        if not self.__checkRow(row) or not self.__checkColumn(column):
            return None

        item = self.item(row, column)
        return item.data(Qt.UserRole) if isinstance(item, QTableWidgetItem) else None

    def getRowData(self, row: int) -> List[Any]:
        return [self.getItemData(row, column) for column in range(self.columnCount())]

    def getRowProperty(self, row: int) -> List[Any]:
        return [self.getItemProperty(row, column) for column in range(self.columnCount())]

    def getColumnData(self, column: int) -> List[Any]:
        return [self.getItemData(row, column) for row in range(self.rowCount())]

    def getColumnProperty(self, column: int) -> List[Any]:
        return [self.getItemProperty(row, column) for row in range(self.rowCount())]

    def getTableData(self) -> List[List[Any]]:
        return [self.getRowData(row) for row in range(self.rowCount())]

    def clearTableData(self):
        self.setRowCount(0)
        self.tableDataChanged.emit()

    def getTableProperty(self) -> List[List[Any]]:
        return [self.getRowProperty(row) for row in range(self.rowCount())]

    def resizeEvent(self, ev: QResizeEvent):
        width = ev.size().width()
        height = ev.size().height()

        # Auto adjust table row height
        if self.__autoHeight:
            self.setVerticalHeaderHeight(height / self.rowCount())

        if len(self.__columnStretchFactor) == 0:
            super(TableWidget, self).resizeEvent(ev)
            return

        # Auto adjust table column width
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        for column, factor in enumerate(self.__columnStretchFactor):
            header.setSectionResizeMode(column, self.__columnStretchMode)
            self.setColumnWidth(column, width * factor)

        # Apply max width after resize
        for column, max_width in self.__columnMaxWidth.items():
            header.resizeSection(column, max_width)


class TreeWidget(QTreeWidget):
    PRIVATE_DATA_DEFAULT_COLUMN = 0

    def __init__(self, parent: Optional[QWidget] = None):
        super(TreeWidget, self).__init__(parent)
        self.__autoHeight = False
        self.__columnStretchFactor = list()

        self.ui_context_menu = QMenu(self)
        self.ui_expand_all = QAction(self.tr("Expand All"), self)
        self.ui_collapse_all = QAction(self.tr("Collapse All"), self)

        self.ui_context_menu.addAction(self.ui_expand_all)
        self.ui_context_menu.addAction(self.ui_collapse_all)

        # noinspection PyUnresolvedReferences
        self.ui_expand_all.triggered.connect(self.expandAll)
        # noinspection PyUnresolvedReferences
        self.ui_collapse_all.triggered.connect(self.collapseAll)

    def disableScrollBar(self, horizontal: bool, vertical: bool):
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff if vertical else Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff if horizontal else Qt.ScrollBarAsNeeded)

    def clear(self):
        for i in range(self.topLevelItemCount()):
            self.takeTopLevelItem(0)

    def createTreeFromDict(self, tree: collections.OrderedDict):
        for root, config in tree.items():
            # All leaves without branch
            private_data, children = config
            if all(isinstance(x, str) for x in children):
                self.addSubTree(root, [[x] for x in children], private_data)
            else:
                self.addSubTree(root, private_data)
                for child in children:
                    # Leaf
                    if isinstance(child, str):
                        self.insSubTree(root, [[child]], private_data)
                    # Branch with leaves
                    elif isinstance(child, typing.Sequence) and len(child) == 2:
                        sub_root, sub_children = child
                        self.insSubTree(root, [[sub_root]], private_data)
                        self.insSubTree(sub_root, [[x] for x in sub_children], private_data)

    def findItemByNameAndData(self, name: str, column: int, private_data: Any = None) -> Optional[QTreeWidgetItem]:
        if not isinstance(name, str) or not isinstance(column, int) or not (0 <= column < self.columnCount()):
            return None

        for item in self.findItems(name, Qt.MatchExactly | Qt.MatchRecursive, column):
            if not private_data:
                return item

            if item.data(self.PRIVATE_DATA_DEFAULT_COLUMN, Qt.UserRole) == private_data:
                return item

        return None

    def insSubTree(self, parent: str,
                   children: Sequence[Union[Sequence[str], str]],
                   private_data: Any = None, auto_expand: bool = True):
        root = self.findItemByNameAndData(parent, 0)
        if not isinstance(root, QTreeWidgetItem):
            return

        self.addSubTreeToRoot(root, children, private_data, auto_expand)

    def addSubTree(self, name: str,
                   children: Sequence[Union[Sequence[str], str]] = None,
                   private_data: Any = None, auto_expand: bool = True):
        children = children or list()
        if not isinstance(name, str):
            return

        # Create root item
        root = QTreeWidgetItem(self, [name])
        root.setData(self.PRIVATE_DATA_DEFAULT_COLUMN, Qt.UserRole, private_data)

        # Append children to root
        self.addSubTreeToRoot(root, children, private_data, auto_expand)

    def addSubTreeToRoot(self, root: QTreeWidgetItem,
                         children: Sequence[Union[Sequence[str], str]],
                         private_data: Any = None, auto_expand: bool = True):
        if not isinstance(children, (list, tuple)):
            return

        # Append children to root
        for child in children:
            item = QTreeWidgetItem(root, child)
            if private_data:
                item.setData(self.PRIVATE_DATA_DEFAULT_COLUMN, Qt.UserRole, private_data)
            root.addChild(item)

        if auto_expand:
            self.expandAll()

        self.setCurrentItem(root.child(root.childCount() - 1))

    def setAutoHeight(self, enable: bool):
        self.__autoHeight = enable
        self.resize(self.geometry().width(), self.geometry().height())

    def setColumnStretchFactor(self, factors: Sequence[float]):
        if not isinstance(factors, (list, tuple)):
            return

        if len(factors) > self.columnCount():
            return

        self.__columnStretchFactor = factors
        self.resize(self.geometry().width(), self.geometry().height())

    def resizeEvent(self, ev: QResizeEvent):

        width = ev.size().width()
        height = ev.size().height()

        # Auto adjust table row height
        if self.__autoHeight:
            self.setVerticalHeaderHeight(height / self.rowCount())

        if len(self.__columnStretchFactor) == 0:
            super(QTreeWidget, self).resizeEvent(ev)
            return

        # Auto adjust table column width
        header = self.header()
        header.setStretchLastSection(True)
        for column, factor in enumerate(self.__columnStretchFactor):
            header.setSectionResizeMode(column, QHeaderView.Fixed)
            header.resizeSection(column, width * factor)

    def contextMenuEvent(self, ev: QContextMenuEvent):
        self.ui_context_menu.exec_(ev.globalPos())


class ListWidget(QListWidget):
    def __init__(self, unique: bool = False,
                 markColor: QColor = QColor(51, 153, 255), parent: Optional[QWidget] = None):
        super(ListWidget, self).__init__(parent)

        self.__unique = unique
        if isinstance(markColor, (QColor, Qt.GlobalColor)):
            self.__markColor = markColor
        else:
            self.__markColor = QColor(51, 153, 255)

    def __setItemBackground(self, index: int, background: QBrush) -> bool:
        if not isinstance(index, int) or not isinstance(background, QBrush):
            return False

        item = self.item(index)
        if not isinstance(item, QListWidgetItem):
            return False

        item.setBackground(background)
        return True

    def __setItemForeground(self, index: int, foreground: QBrush) -> bool:
        if not isinstance(index, int) or not isinstance(foreground, QBrush):
            return False

        item = self.item(index)
        if not isinstance(item, QListWidgetItem):
            return False

        item.setForeground(foreground)
        return True

    @Slot(object)
    def markItem(self, item: QListWidgetItem, background: bool = True) -> bool:
        """Mark item background or foreground with different color

        :param item: witch item to marked
        :param background: if background set will mark background else foreground
        :return: success, return true else false
        """
        if not isinstance(item, QListWidgetItem):
            return False

        # Get item row
        row = self.row(item)

        if row < 0 or row >= self.count():
            return False

        brush = QBrush(QColor(self.__markColor))

        # Clear old mark
        for index in range(self.count()):
            if background and self.item(index).background() == brush:
                self.__setItemBackground(index, QListWidgetItem("").background())
                break
            elif not background and self.item(index).foreground() == brush:
                self.__setItemForeground(index, QListWidgetItem("").foreground())
                break

        # Set new mark
        self.__setItemBackground(row, brush)if background else self.__setItemForeground(row, brush)
        self.setCurrentRow(row)
        return True

    def getMarkedItem(self, background: bool = True) -> Optional[str]:
        """Get marked item text

        :param background: if set will return marked background item text else foreground item text
        :return:
        """
        for index in range(self.count()):
            item = self.item(index)
            if not isinstance(item, QListWidgetItem):
                continue

            if background and item.background() == self.__markColor:
                return item.text()
            elif not background and item.foreground() == self.__markColor:
                return item.text()

        return None

    def addItem(self, name: str, data: Optional[Any] = None) -> bool:
        if not isinstance(name, str):
            print("TypeError: {}".format(type(name)))
            return False

        if self.__unique and name in self.getItems():
            print("Same name item is exist")
            return False

        item = QListWidgetItem(name)
        if data is not None:
            item.setData(Qt.UserRole, data)

        super(ListWidget, self).addItem(item)
        self.setCurrentItem(item)
        return True

    def setItems(self, items: Sequence[Union[Tuple[str, Any], str]]) -> bool:
        if not isinstance(items, (list, tuple)):
            print("Items data type error:{}".format(type(items)))
            return False

        # Remove old items
        self.clearItems()

        # Add items data to ListWidget
        for data in items:
            if isinstance(data, (tuple, list)) and len(data) == 2 and isinstance(data[0], str):
                self.addItem(data[0], data[1])
            elif isinstance(data, str):
                self.addItem(data)
            else:
                continue

        return True

    def clearItems(self):
        for _ in range(self.count()):
            item = self.takeItem(0)
            self.removeItemWidget(item)

    def getItems(self) -> List[str]:
        return [self.item(i).text() for i in range(self.count())]

    def getItemsData(self) -> List[Any]:
        return [self.item(i).data(Qt.UserRole) for i in range(self.count())]


class SerialPortSettingWidget(QWidget):
    Tag = ComponentManager.DefaultObjectNameKey

    # noinspection PyTypeChecker
    PARITIES_STR = QApplication.translate("SerialPortSettingWidget", "Parity", None)
    # noinspection PyTypeChecker
    # noinspection SpellCheckingInspection
    DATABITS_STR = QApplication.translate("SerialPortSettingWidget", "DataBits", None)
    # noinspection PyTypeChecker
    # noinspection SpellCheckingInspection
    STOPBITS_STR = QApplication.translate("SerialPortSettingWidget", "StopBits", None)
    # noinspection PyTypeChecker
    # noinspection SpellCheckingInspection
    BAUDRATE_STR = QApplication.translate("SerialPortSettingWidget", "BaudRate", None)
    # noinspection PyTypeChecker
    TIMEOUT_STR = QApplication.translate("SerialPortSettingWidget", "Timeout (ms)", None)

    # noinspection SpellCheckingInspection
    OPTIONS = {
        "baudrate": {
            "text": BAUDRATE_STR,
            "values": (50, 75, 110, 134, 150, 200, 300, 600, 1200, 1800, 2400, 4800,
                       9600, 19200, 38400, 57600, 115200, 230400, 460800, 500000, 576000, 921600)
        },

        "bytesize": {
            "text": DATABITS_STR,
            "values": Serial.BYTESIZES
        },

        "parity": {
            "text": PARITIES_STR,
            "values": Serial.PARITIES
        },

        "stopbits": {
            "text": STOPBITS_STR,
            "values": Serial.STOPBITS
        },

        "timeout": {
            "text": TIMEOUT_STR,
            "values": [0, 9999]
        }
    }
    # noinspection SpellCheckingInspection
    ALL_OPTIONS = ("baudrate", "bytesize", "parity", "stopbits", "timeout")
    # noinspection SpellCheckingInspection
    DEFAULTS = {"baudrate": 9600, "bytesize": 8, "parity": "N", "stopbits": 1, "timeout": 0}

    def __init__(self, settings: Optional[dict] = None, flush_timeout: float = 0.04, parent: Optional[QWidget] = None):
        """Serial port configure dialog

        :param settings: serial port settings
        :param parent:
        """
        settings = settings or self.DEFAULTS
        super(SerialPortSettingWidget, self).__init__(parent)

        layout = QGridLayout()

        # If specified port select it
        port = SerialPortSelector(flush_timeout=flush_timeout)
        port.setProperty(self.Tag, "port")
        select_port = settings.get("port")
        if select_port is not None:
            port.setSelectedPort(select_port)

        # Add port to dialog
        layout.addWidget(QLabel(self.tr("PortName")), 0, 0)
        layout.addWidget(port, 0, 1)

        # If specified it add option to dialog
        for index, option in enumerate(self.ALL_OPTIONS):
            if option not in settings:
                continue

            # Get option settings
            value = settings.get(option)
            text = self.OPTIONS.get(option).get("text")
            values = self.OPTIONS.get(option).get("values")

            # Create option element
            element = QComboBox() if isinstance(values, tuple) else QSpinBox()
            if isinstance(element, QComboBox):
                # If user settings is invalid then using default settings
                value = self.DEFAULTS.get(option) if value not in values else value
                for v in values:
                    element.addItem(str(v), v)
                element.setCurrentIndex(values.index(value))
            else:
                element.setRange(values[0], values[1])
                element.setValue(value)

            # Set option property
            label = QLabel(self.tr(text))
            element.setProperty(self.Tag, option)

            # Layout direction setting
            layout.addWidget(label, index + 1, 0)
            layout.addWidget(element, index + 1, 1)

        self.setLayout(layout)
        self.__uiManager = ComponentManager(layout)

    def getSetting(self) -> Dict[str, Any]:
        settings = dict()
        for item in self.__uiManager.findKey(self.Tag):
            if isinstance(item, QComboBox):
                value = item.property(self.Tag)
                if value == "port" and item.currentIndex() == 0:
                    settings[value] = ""
                else:
                    settings[value] = item.itemData(item.currentIndex())
            elif isinstance(item, QSpinBox):
                settings[item.property(self.Tag)] = item.value()

        return settings


class BasicJsonSettingWidget(QWidget):
    settingChanged = Signal()
    settingChangedDetail = Signal(str, object)

    def __init__(self, settings: DynamicObject, parent: Optional[QWidget] = None):
        super(BasicJsonSettingWidget, self).__init__(parent)

        if not isinstance(settings, DynamicObject):
            raise TypeError("settings require {!r}".format(DynamicObject.__name__))

        try:
            layout = settings.layout
            self.settings = settings.dict
            self.settings_cls = settings.__class__
            self.layout = layout if isinstance(layout, UiLayout) else UiLayout(**layout)
            if not self.layout.check_layout(self.settings):
                raise ValueError("layout error")
        except AttributeError:
            raise ValueError("Do not found layout settings")
        except (json.JSONDecodeError, DynamicObjectDecodeError):
            raise TypeError("settings.layout must be {!r}".format(UiLayout.__name__))

        try:
            font = QFont(*self.layout.get_font())
        except (TypeError, ValueError):
            pass
        else:
            self.setFont(font)

    def createLayout(self, row_stretch_mode: bool = False) -> QGridLayout:
        layout = QGridLayout()
        _, h, v = tuple(self.layout.get_spaces())
        layout.setVerticalSpacing(v)
        layout.setHorizontalSpacing(h)
        layout.setContentsMargins(*tuple(self.layout.get_margins()))
        if any(self.layout.get_stretch()):
            for column, stretch in enumerate(self.layout.get_stretch()):
                if row_stretch_mode:
                    layout.setRowStretch(column, stretch)
                else:
                    layout.setColumnStretch(column, stretch)
        return layout

    def getData(self) -> Any:
        pass

    def setData(self, data: Any) -> Any:
        pass

    def resetDefaultData(self):
        pass

    def slotSettingChanged(self):
        pass

    def slotDisableInput(self, disable: bool):
        pass


class JsonSettingWidget(BasicJsonSettingWidget):
    def __init__(self, settings: DynamicObject, data: Optional[dict] = None, parent: Optional[QWidget] = None):
        super(JsonSettingWidget, self).__init__(settings, parent)

        self.__groups = list()
        # Convert layout to grid layout
        self.top_layout = self.layout.get_grid_layout(self.settings)

        self.__initUi()
        self.__initData(data)
        self.__initSignalAndSlots()

    def __initUi(self):
        row = 0
        layout = self.createLayout()
        for items in self.top_layout:
            column = 0
            for item in items:
                try:
                    dict_ = self.settings.get(item)
                    ui_input = UiInputSetting(**dict_)
                    widget = self.createInputWidget(ui_input, item, parent=self)
                    if isinstance(widget, QWidget):
                        # Add label and widget
                        if ui_input.label_left:
                            layout.addWidget(QLabel(self.tr(ui_input.get_name())), row, column)
                            column += 1
                            layout.addWidget(widget, row, column)
                            column += 1
                        else:
                            widget.setSizePolicy(QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding))
                            layout.addWidget(widget, row, column)
                            column += 1
                            layout.addWidget(QLabel(self.tr(ui_input.get_name())), row, column)
                            column += 1

                        # QLine edit special process re check
                        if isinstance(widget, QLineEdit):
                            widget.setSizePolicy(QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed))

                            if not isinstance(widget, VirtualNumberInput):
                                widget.textChanged.connect(self.slotSettingChanged)
                                widget.textChanged.connect(
                                    lambda x: self.settingChangedDetail.emit(widget.property("data"), x)
                                )
                    elif isinstance(widget, QLayout):
                        # Add label and layout
                        layout.addWidget(QLabel(self.tr(ui_input.get_name())), row, column)
                        column += 1
                        layout.addLayout(widget, row, column)
                        column += 1
                    elif isinstance(widget, tuple) and len(widget) == 3 and isinstance(widget[0], QLayout) and \
                            isinstance(widget[1], QButtonGroup) and isinstance(widget[2], (QLineEdit, QSpinBox)):
                        widget, btn_group, select_value = widget

                        # Add label and layout
                        layout.addWidget(QLabel(self.tr(ui_input.get_name())), row, column)
                        column += 1
                        layout.addLayout(widget, row, column)
                        column += 1

                        # This is necessary otherwise buttonClicked won't be emitted
                        self.__groups.append(btn_group)

                        # Text mode
                        if isinstance(select_value, QLineEdit):
                            # noinspection PyUnresolvedReferences
                            select_value.textChanged.connect(self.slotSettingChanged)
                            # noinspection PyUnresolvedReferences
                            select_value.textChanged.connect(
                                lambda x: self.settingChangedDetail.emit(select_value.property("data"), x)
                            )
                            btn_group.buttonClicked.connect(lambda x: select_value.setText(x.text()))
                        # Value mode
                        elif isinstance(select_value, QSpinBox):
                            select_value.valueChanged.connect(self.slotSettingChanged)
                            select_value.valueChanged.connect(
                                lambda x: self.settingChangedDetail.emit(select_value.property("data"), x)
                            )
                            btn_group.buttonClicked.connect(lambda x: select_value.setValue(x.property("id")))
                except (TypeError, ValueError, IndexError, json.JSONDecodeError, DynamicObjectDecodeError) as err:
                    print("{}".format(err))

            row += 1
        self.setLayout(layout)
        if all(self.layout.get_min_size()):
            self.setMinimumSize(QSize(*self.layout.get_min_size()))
        self.ui_manager = ComponentManager(layout)
        self.ui_manager.dataChanged.connect(self.slotSettingChanged)
        self.ui_manager.dataChangedDetail.connect(self.settingChangedDetail.emit)

    def __initData(self, data: dict):
        self.setData(data)

    def __initSignalAndSlots(self):
        for button in self.ui_manager.findValue("clicked", "file", QPushButton):
            if isinstance(button, QPushButton):
                button.clicked.connect(self.slotSelectFile)

        for button in self.ui_manager.findValue("clicked", "folder", QPushButton):
            if isinstance(button, QPushButton):
                button.clicked.connect(self.slotSelectFolder)

        for button in self.ui_manager.findValue("clicked", "font", QPushButton):
            if isinstance(button, QPushButton):
                button.clicked.connect(self.slotSelectFont)
                preview = self.ui_manager.getPrevSibling(button)
                if isinstance(preview, QLineEdit):
                    # noinspection PyUnresolvedReferences
                    preview.textChanged.connect(self.slotPreviewFont)

        for button in self.ui_manager.findValue("clicked", "color", QPushButton):
            if isinstance(button, QPushButton):
                button.clicked.connect(self.slotSelectColor)
                preview = self.ui_manager.getPrevSibling(button)
                if isinstance(preview, QLineEdit):
                    # noinspection PyUnresolvedReferences
                    preview.textChanged.connect(self.slotPreviewColor)

    # noinspection PyMethodOverriding
    def tr(self, text: str) -> str:
        # noinspection PyTypeChecker
        return QApplication.translate("JsonSettingWidget", text, None)

    def getSettings(self) -> DynamicObject:
        data = self.getData()
        settings = self.settings
        for k, v in data.items():
            settings[k]["data"] = v
        return self.settings_cls(**settings)

    def getData(self) -> dict:
        ext_list = list()
        data = self.ui_manager.getData("data")
        for k, v in data.items():
            ext_key = self.get_file_input_enable_key(k)
            if ext_key in data:
                ext_list.append(ext_key)
                data[k] = (data.get(ext_key), v)

        for ext_key in ext_list:
            data.pop(ext_key)
        return data

    def setData(self, data: dict):
        font_inputs = self.ui_manager.findValue("clicked", "font", QPushButton)
        file_inputs = self.ui_manager.findValue("clicked", "file", QPushButton)
        color_inputs = self.ui_manager.findValue("clicked", "color", QPushButton)
        for button in font_inputs + color_inputs:
            if isinstance(button, QPushButton):
                preview = self.ui_manager.getPrevSibling(button)
                if isinstance(preview, QLineEdit) and data:
                    button.setProperty("private", "{}".format(data.get(preview.property("data"))))

        for button in file_inputs:
            if isinstance(button, QPushButton):
                preview = self.ui_manager.getPrevSibling(button)
                enabled = self.ui_manager.getPrevSibling(preview)
                if isinstance(enabled, QCheckBox) and isinstance(preview, QLineEdit) and \
                        data and preview.property("data"):
                    file_name = preview.property("data")
                    try:
                        enabled, path = data.get(file_name)
                    except (AttributeError, TypeError, ValueError):
                        enabled, path = False, data.get(file_name)
                    data[file_name] = path
                    data[self.get_file_input_enable_key(file_name)] = enabled

        return self.ui_manager.setData("data", data)

    def resetDefaultData(self):
        data = dict()
        for key in self.getData().keys():
            data[key] = self.settings[key]["default"]
        self.ui_manager.setData("data", data)

    def slotSelectFile(self):
        sender = self.sender()
        from .dialog import showFileImportDialog
        file_format = " ".join(sender.property("private") or list())
        title = self.tr("Please select") + " {}".format(sender.property("title"))

        path = showFileImportDialog(parent=self, title=title, fmt=self.tr(file_format))
        if not os.path.isfile(path):
            return

        path_edit = self.ui_manager.getPrevSibling(sender)
        if isinstance(path_edit, QLineEdit):
            path_edit.setText(path)
            # path_edit.setReadOnly(True)
            enabled = self.ui_manager.getPrevSibling(path_edit)
            if isinstance(enabled, QCheckBox):
                enabled.setChecked(True)

    def slotSelectFolder(self):
        sender = self.sender()
        title = self.tr("Please select") + " {}".format(sender.property("title"))
        path = QFileDialog.getExistingDirectory(self, title, "")
        if not os.path.isdir(path):
            return

        path_edit = self.ui_manager.getPrevSibling(sender)
        if isinstance(path_edit, QLineEdit):
            path_edit.setText(path)

    def slotSelectFont(self):
        sender = self.sender()
        if not isinstance(sender, QPushButton):
            return
        title = self.tr("Please select") + " {}".format(sender.property("title"))
        font_name, point_size, weight = UiFontInput.get_font(sender.property("private"))
        selected, font = QFontDialog.getFont(QFont(font_name, point_size, weight), self, title)
        if not selected or not isinstance(font, QFont):
            return

        font_edit = self.ui_manager.getPrevSibling(sender)
        if isinstance(font_edit, QLineEdit):
            font_setting = font.family(), font.pointSize(), font.weight()
            sender.setProperty("private", "{}".format(font_setting))
            font_edit.setText("{}".format(font_setting))

    def slotPreviewFont(self):
        sender = self.sender()
        if not isinstance(sender, QLineEdit):
            return

        font_setting = sender.text()
        sender.setStyleSheet(UiFontInput.get_stylesheet(font_setting))

    def slotSelectColor(self):
        sender = self.sender()
        title = self.tr("Please select") + " {}".format(sender.property("title"))
        r, g, b = UiColorInput.get_color(sender.property("private"))
        color = QColorDialog.getColor(QColor(r, g, b), self, title)
        if not isinstance(color, QColor) or not color.isValid():
            color = QColor(r, g, b)

        color_edit = self.ui_manager.getPrevSibling(sender)
        if isinstance(color_edit, QLineEdit):
            rgb = color.red(), color.green(), color.blue()
            sender.setProperty("private", "{}".format(rgb))
            color_edit.setText("{}".format(rgb))

    def slotPreviewColor(self):
        sender = self.sender()
        if not isinstance(sender, QLineEdit):
            return

        color = sender.text()
        sender.setStyleSheet("background-color: rgb{}; color: rgb{};".format(color, color))

    def slotSettingChanged(self):
        self.settingChanged.emit()

        sender = self.sender()
        # Line edit text content check
        if isinstance(sender, QLineEdit):
            filters = sender.property("filter")
            if not filters:
                return

            try:
                re.search(filters, sender.text(), re.S).group(0)
                sender.setStyleSheet("color: rgb(0, 0, 0);")
            except AttributeError:
                sender.setStyleSheet("color: rgb(255, 0, 0);")

    def slotDisableInput(self, disable: bool):
        self.ui_manager.setDisabled(disable)

    @staticmethod
    def createInputWidget(setting: UiInputSetting,
                          name: Optional[str] = None,
                          parent: Optional[QWidget] = None) -> \
            Union[QWidget, Tuple[QHBoxLayout, QButtonGroup, Union[QLineEdit, QSpinBox, QDoubleSpinBox]], None]:
        if not isinstance(setting, UiInputSetting):
            return None

        widget = None

        try:
            if setting.is_int_type():
                if setting.is_readonly():
                    widget = VirtualNumberInput(parent=parent, initial_value=setting.get_data(),
                                                min_=setting.get_check()[UiIntegerInput.CHECK.MIN],
                                                max_=setting.get_check()[UiIntegerInput.CHECK.MAX])
                    widget.setProperty("format", "int")
                else:
                    widget = QSpinBox(parent)
                    widget.setMinimum(setting.get_check()[UiIntegerInput.CHECK.MIN])
                    widget.setMaximum(setting.get_check()[UiIntegerInput.CHECK.MAX])
                    widget.setValue(setting.get_data())
                    widget.setSingleStep(setting.get_check()[UiIntegerInput.CHECK.STEP])
            elif setting.is_bool_type():
                widget = QCheckBox(parent=parent)
                widget.setCheckable(True)
                widget.setChecked(setting.get_data())
            elif setting.is_text_type():
                widget = QLineEdit(parent)
                widget.setText(setting.get_data())
                widget.setPlaceholderText(setting.get_default())

                # If password set set echo mode
                if len(setting.get_check()) == 3 and setting.get_check()[-1]:
                    widget.setEchoMode(QLineEdit.Password)

                # Set regular expression and max length
                widget.setProperty("filter", setting.check[UiTextInput.CHECK.REGEXP])
                widget.setValidator(QRegExpValidator(QRegExp(setting.check[UiTextInput.CHECK.REGEXP])))
                widget.setMaxLength(setting.check[UiTextInput.CHECK.LENGTH])
            elif setting.is_float_type():
                if setting.is_readonly():
                    widget = VirtualNumberInput(parent=parent,
                                                initial_value=setting.get_data(),
                                                min_=setting.get_check()[UiDoubleInput.CHECK.MIN],
                                                max_=setting.get_check()[UiDoubleInput.CHECK.MAX],
                                                decimals=setting.get_check()[UiDoubleInput.CHECK.DECIMALS])
                    widget.setProperty("format", "float")
                else:
                    widget = QDoubleSpinBox(parent)
                    widget.setMinimum(setting.get_check()[UiDoubleInput.CHECK.MIN])
                    widget.setMaximum(setting.get_check()[UiDoubleInput.CHECK.MAX])
                    widget.setValue(setting.get_data())
                    widget.setSingleStep(setting.get_check()[UiDoubleInput.CHECK.STEP])
                    if len(setting.get_check()) > UiDoubleInput.CHECK.DECIMALS:
                        widget.setDecimals(setting.get_check()[UiDoubleInput.CHECK.DECIMALS])
            elif setting.is_select_type():
                widget = QComboBox(parent)
                widget.addItems(setting.get_check())
                # Data is text, using text format set and get
                if isinstance(setting.get_data(), str) and setting.get_data() in setting.get_check():
                    widget.setProperty("format", "text")
                    widget.setCurrentIndex(setting.get_check().index(setting.get_data()))
                # Data is number, using index format set and get
                elif isinstance(setting.get_data(), int) and setting.get_data() < len(setting.get_check()):
                    widget.setCurrentIndex(setting.get_data())
                else:
                    widget.setCurrentIndex(0)
            elif setting.is_button_type():
                widget = QPushButton(setting.get_name())
            elif setting.is_sbs_select_type():
                group = QButtonGroup(parent)
                layout = QHBoxLayout()

                for id_, text in enumerate(setting.get_check()):
                    btn = QRadioButton(text, parent=parent)
                    btn.setProperty("id", id_)
                    group.addButton(btn, id_)
                    layout.addWidget(btn)
                    layout.addWidget(QSplitter())

                text_input = QLineEdit(parent=parent)
                text_input.setReadOnly(True)
                text_input.setVisible(False)
                text_input.setProperty("data", name)

                number_input = QSpinBox(parent=parent)
                number_input.setVisible(False)
                number_input.setProperty("data", name)

                # Default select the first item
                group.button(0).setChecked(True)

                # Data is number, using index format set and get
                if isinstance(setting.get_data(), str):
                    for btn in group.buttons():
                        if btn.text() == setting.get_data():
                            btn.setChecked(True)
                            text_input.setText(btn.text())
                            layout.addWidget(text_input)
                            return layout, group, text_input
                elif isinstance(setting.get_data(), int):
                    value = setting.get_data() if setting.get_data() < len(setting.get_check()) else 0
                    group.button(value).setChecked(True)
                    number_input.setValue(value)
                    layout.addWidget(number_input)
                    return layout, group, number_input

                return layout, group, number_input
            elif setting.is_serial_type():
                widget = SerialPortSelector(flush_timeout=setting.get_check(), parent=parent)
                widget.setProperty("format", "text")
                widget.setCurrentIndex([widget.itemText(i) for i in range(widget.count())].index(setting.get_data()))
            elif setting.is_network_type():
                widget = NetworkInterfaceSelector(
                    mode=NetworkInterfaceSelector.Mode.Network, text=setting.get_default(), parent=parent
                )
                widget.setCurrentNetwork(setting.get_data())
            elif setting.is_address_type():
                widget = NetworkInterfaceSelector(
                    mode=NetworkInterfaceSelector.Mode.Address, text=setting.get_default(), parent=parent
                )
                widget.setCurrentAddress(setting.get_data())
            elif setting.is_interface_type():
                widget = NetworkInterfaceSelector(
                    mode=NetworkInterfaceSelector.Mode.Interface, text=setting.get_default(), parent=parent
                )
                widget.setCurrentInterface(setting.get_data())
            elif setting.is_file_type():
                widget = QLineEdit(parent)
                widget.setProperty("data", name)
                widget.setText(setting.get_data())
                widget.setReadOnly(not UiFileInput.isEditable(setting.get_check()))

                # noinspection PyTypeChecker
                enable = QCheckBox(QApplication.translate("JsonSettingWidget", "Enable", None), parent=parent)
                enable.setProperty("data", JsonSettingWidget.get_file_input_enable_key(name))
                enable.setVisible(UiFileInput.isSelectable(setting.get_check()))
                # noinspection PyTypeChecker
                button = QPushButton(QApplication.translate("JsonSettingWidget",
                                                            "Please Select File",
                                                            None), parent=parent)
                button.setProperty("clicked", "file")
                button.setProperty("title", setting.get_name())
                button.setProperty("private", setting.get_check()[:UiFileInput.CHECK_SELECTABLE])

                layout = QHBoxLayout()
                layout.addWidget(enable)
                layout.addWidget(widget)
                layout.addWidget(button)
                return layout
            elif setting.is_folder_type():
                widget = QLineEdit(parent)
                widget.setReadOnly(True)
                widget.setProperty("data", name)
                widget.setText(setting.get_data())
                # noinspection PyTypeChecker
                button = QPushButton(QApplication.translate("JsonSettingWidget",
                                                            "Please Select Directory",
                                                            None), parent=parent)
                button.setProperty("clicked", "folder")
                button.setProperty("title", setting.get_name())
                button.setProperty("private", setting.get_check())

                layout = QHBoxLayout()
                layout.addWidget(widget)
                layout.addWidget(button)
                return layout
            elif setting.is_font_type():
                widget = QLineEdit(parent)
                widget.setReadOnly(True)
                widget.setProperty("data", name)
                widget.setText(setting.get_data())
                widget.setStyleSheet(UiFontInput.get_stylesheet(setting.get_data()))
                # noinspection PyTypeChecker
                button = QPushButton(QApplication.translate("JsonSettingWidget",
                                                            "Please Select Font",
                                                            None), parent=parent)
                button.setProperty("clicked", "font")
                button.setProperty("title", setting.get_name())
                button.setProperty("private", setting.get_data())

                layout = QHBoxLayout()
                layout.addWidget(widget)
                layout.addWidget(button)
                return layout
            elif setting.is_color_type():
                color = setting.get_data()
                widget = QLineEdit(parent)
                widget.setReadOnly(True)
                widget.setProperty("data", name)
                widget.setText("{}".format(setting.get_data()))
                widget.setStyleSheet("background-color: rgb{}; color: rgb{};".format(color, color))
                # noinspection PyTypeChecker
                button = QPushButton(QApplication.translate("JsonSettingWidget",
                                                            "Please Select Color",
                                                            None), parent=parent)
                button.setProperty("clicked", "color")
                button.setProperty("title", setting.get_name())
                button.setProperty("private", setting.get_data())

                layout = QHBoxLayout()
                layout.addWidget(widget)
                layout.addWidget(button)
                return layout
        except (IndexError, ValueError):
            pass

        # Set property for ComponentManager get data
        if isinstance(name, str) and isinstance(widget, QWidget):
            widget.setProperty("data", name)

        # Set readonly option
        if setting.is_readonly():
            if isinstance(widget, QLineEdit):
                widget.setReadOnly(True)
            elif isinstance(widget, QWidget):
                widget.setDisabled(True)

        return widget

    @staticmethod
    def get_file_input_enable_key(name: str) -> str:
        return "{}_enabled".format(name)


class MultiJsonSettingsWidget(BasicJsonSettingWidget):
    def __init__(self, settings: DynamicObject, data: Sequence[Sequence[Any]], parent: Optional[QWidget] = None):
        super(MultiJsonSettingsWidget, self).__init__(settings, parent)

        if not isinstance(data, (list, tuple)):
            raise TypeError("data require a list or tuple not {!r}".format(data.__class__.__name__))

        self.frozen_columns = list()
        self.layout = self.layout.get_vertical_layout(self.settings)
        self.__initUi()
        self.__initData(data)
        self.__initStyleSheet()
        self.ui_table.tableDataChanged.connect(self.slotSettingChanged)

    def __initUi(self):
        try:
            columns_header = [self.settings.get(x).name for x in self.layout]
        except AttributeError:
            columns_header = [self.settings.get(x).get("name") for x in self.layout]
        self.ui_table = TableWidget(len(columns_header))
        self.ui_table.setColumnHeader(columns_header)
        self.ui_table.setRowSelectMode()

        table_filters = dict()
        for column, item in enumerate(self.layout):
            try:

                dict_ = self.settings.get(item)
                ui_input = dict_ if isinstance(dict_, UiInputSetting) else UiInputSetting(**dict_)

                if ui_input.is_bool_type():
                    table_filters[column] = (ui_input.get_default(), ui_input.get_name())
                elif ui_input.is_int_type() or ui_input.is_float_type():
                    table_filters[column] = ui_input.get_check()[:2]
                elif ui_input.is_select_type():
                    table_filters[column] = ui_input.get_check()
                elif ui_input.is_file_type():
                    text = self.tr("Please Select File")
                    table_filters[column] = (text, self.slotSelectFile, ui_input.get_check())
                elif ui_input.is_folder_type():
                    text = self.tr("Please Select Directory")
                    table_filters[column] = (text, self.slotSelectFolder, ui_input.get_check())

                if ui_input.is_readonly():
                    self.frozen_columns.append(column)
            except (TypeError, ValueError, json.JSONDecodeError, DynamicObjectDecodeError) as err:
                print("{}".format(err))

        # Set table filters
        self.ui_table.setTableDataFilter(table_filters)

        # Set widget minimum size
        layout = self.settings.get('layout')
        if all(layout.get_min_size()):
            self.setMinimumSize(QSize(*layout.get_min_size()))

        layout = QVBoxLayout()
        layout.addWidget(self.ui_table)
        self.setLayout(layout)

    def __initData(self, data: Sequence[Sequence[Any]]):
        self.setData(data)

    def __initStyleSheet(self):
        self.ui_table.resizeColumnWidthFitContents()

    def getData(self) -> List[List[Any]]:
        return self.ui_table.getTableData()

    def setData(self, data: Sequence[Sequence[Any]]):
        self.ui_table.setRowCount(0)
        # Add data to table
        for item in data:
            self.ui_table.addRow(item)

        # Frozen table readonly column
        for column in self.frozen_columns:
            self.ui_table.frozenColumn(column, True)

        # Move to first row
        self.ui_table.selectRow(0)

    def resetDefaultData(self):
        try:
            data = [self.settings.get(k).default for k in self.layout]
        except AttributeError:
            data = [self.settings.get(k).get("default") for k in self.layout]

        self.setData([data for _ in range(self.ui_table.rowCount())])

    def slotSelectFile(self):
        file_format = "*"
        sender = self.sender()
        from .dialog import showFileImportDialog
        path = showFileImportDialog(parent=self, title=self.tr("Please Select File"), fmt=self.tr(file_format))
        if not os.path.isfile(path):
            return

        sender.setProperty("private", path)

    def slotSelectFolder(self):
        sender = self.sender()
        path = QFileDialog.getExistingDirectory(self, self.tr("Please Select Directory"), "")
        if not os.path.isdir(path):
            return

        sender.setProperty("private", path)

    def slotSettingChanged(self):
        self.settingChanged.emit()

        sender = self.sender()
        # Line edit text content check
        if isinstance(sender, QLineEdit):
            filters = sender.property("filter")
            try:
                re.search(filters, sender.text(), re.S).group(0)
                sender.setStyleSheet("color: rgb(0, 0, 0);")
            except AttributeError:
                sender.setStyleSheet("color: rgb(255, 0, 0);")

    def slotDisableInput(self, disable: bool):
        self.ui_table.frozenTable(disable)


class MultiGroupJsonSettingsWidget(BasicJsonSettingWidget):
    Property = collections.namedtuple('Property', 'Name Data Group')(*'name data group'.split())

    def __init__(self, settings: DynamicObject, data: dict, parent: Optional[QWidget] = None):
        super(MultiGroupJsonSettingsWidget, self).__init__(settings, parent)

        if not isinstance(data, dict):
            raise TypeError("data require a dict not {!r}".format(data.__class__.__name__))

        self.widget_list = list()
        self.items_name = self.layout.get_grid_layout(self.settings)

        self.__initUi()
        self.__initData(data)
        self.__initSignalAndSlots()

    def __initUi(self):
        row = 0
        widget_layout = self.createLayout(row_stretch_mode=True)
        for groups in self.items_name:
            column = 0
            for group in groups:
                try:
                    group_settings = self.settings.get(group)
                    group_settings = group_settings if isinstance(group_settings, UiLayout) else \
                        UiLayout(**group_settings)
                    if not group_settings.check_layout(self.settings):
                        continue

                    box = QGroupBox()
                    group_layout = QVBoxLayout()

                    # Only one group do not display title
                    if len(self.items_name) > 1 or group_settings.force_display_title():
                        box.setTitle(group_settings.get_name())

                    settings = {"layout": group_settings}
                    if group_settings.is_vertical_layout(group_settings.get_layout(), self.settings):
                        for item_name in group_settings.get_layout():
                            settings[item_name] = self.settings.get(item_name)
                    else:
                        for item_name in group_settings.get_vertical_layout(group_settings.dict):
                            settings[item_name] = self.settings.get(item_name)

                    box_widget = JsonSettingWidget(DynamicObject(**settings))
                    box_widget.setProperty(self.Property.Name, group_settings.get_name())
                    box_widget.setProperty(self.Property.Group, box)
                    group_layout.addWidget(box_widget)
                    box.setLayout(group_layout)
                    widget_layout.addWidget(box, row, column)
                    self.widget_list.append(box_widget)
                    column += 1
                except (TypeError, ValueError, IndexError, json.JSONDecodeError, DynamicObjectDecodeError) as err:
                    print("{}".format(err))

            row += 1

        self.setLayout(widget_layout)
        if all(self.layout.get_min_size()):
            self.setMinimumSize(QSize(*self.layout.get_min_size()))

    def __initData(self, data: dict):
        self.setData(data)

    def __initSignalAndSlots(self):
        for widget in self.widget_list:
            widget.settingChanged.connect(self.slotSettingChanged)
            widget.settingChangedDetail.connect(self.settingChangedDetail.emit)

    def getData(self) -> dict:
        data = dict()
        [data.update(widget.getData()) for widget in self.widget_list]
        return data

    def setData(self, data: dict):
        return all(widget.setData(data) for widget in self.widget_list)

    def getSettings(self) -> DynamicObject:
        data = self.getData()
        settings = self.settings
        for k, v in data.items():
            settings[k][self.Property.Data] = v
        return self.settings_cls(**settings)

    def resetDefaultData(self):
        [widget.resetDefaultData() for widget in self.widget_list]

    def slotSettingChanged(self):
        self.settingChanged.emit()

    def getGroupWidget(self, name: str) -> Optional[QWidget]:
        for widget in self.widget_list:
            if widget.property(self.Property.Name) == name:
                return widget.property(self.Property.Group)

        return None

    def getWidgetManager(self, name: str) -> Optional[ComponentManager]:
        for widget in self.widget_list:
            if widget.property(self.Property.Name) == name:
                return widget.ui_manager

        return None

    def slotDisableInput(self, disable: bool):
        [widget.ui_manager.setDisabled(disable) for widget in self.widget_list]


class MultiTabJsonSettingsWidget(QTabWidget):
    settingChanged = Signal()
    settingChangedDetail = Signal(str, object)

    SET_DATA_METHOD_NAME = "setData"
    GET_DATA_METHOD_NAME = "getData"
    RESET_DATA_METHOD_NAME = "resetDefaultData"
    Property = collections.namedtuple('Property', 'Name Data Group')(*'name data group'.split())

    def __init__(self, settings: DynamicObject, data: dict, parent: Optional[QWidget] = None):
        super(MultiTabJsonSettingsWidget, self).__init__(parent)

        if not isinstance(settings, DynamicObject):
            raise TypeError("settings require {!r} not {!r}".format(
                DynamicObject.__name__, settings.__class__.__name__))

        if not isinstance(data, dict):
            raise TypeError("data require {!r} not {!r}".format(dict.__name__, data.__class__.__name__))

        try:
            layout = settings.layout
            self.settings = settings.dict
            self.settings_cls = settings.__class__
            self.layout = layout if isinstance(layout, UiLayout) else UiLayout(**layout)
            if not self.layout.check_layout(self.settings):
                raise ValueError("tabs layout error!")
        except AttributeError:
            raise ValueError("Do not found tabs settings")
        except (json.JSONDecodeError, DynamicObjectDecodeError):
            raise TypeError("settings.tabs must be {!r}".format(UiLayout.__name__))

        # Widget list for set/get data using
        self.widget_list = list()
        if all(self.layout.get_min_size()):
            self.setMinimumSize(QSize(*self.layout.get_min_size()))
        self.__initUi()
        self.__initData(data)
        self.__initSignalAndSlots()

    def __initUi(self):
        # Init tabs and group
        for tab in self.layout.get_layout():
            try:
                tab_layout = QVBoxLayout()
                tab_setting = self.settings.get(tab)
                tab_setting = tab_setting if isinstance(tab_setting, UiLayout) else UiLayout(**tab_setting)
                if not tab_setting.check_layout(self.settings):
                    continue

                settings = {"layout": tab_setting}
                for group in tab_setting.get_layout():
                    group_setting = self.settings.get(group)
                    group_setting = group_setting if isinstance(group_setting, UiLayout) else UiLayout(**group_setting)
                    if not group_setting.check_layout(self.settings):
                        continue

                    settings[group] = group_setting
                    if group_setting.is_vertical_layout(group_setting.get_layout(), self.settings):
                        for item_name in group_setting.get_layout():
                            settings[item_name] = self.settings.get(item_name)
                    else:
                        for item_name in group_setting.get_vertical_layout(group_setting.dict):
                            settings[item_name] = self.settings.get(item_name)

                widget = MultiGroupJsonSettingsWidget(DynamicObject(**settings), dict())
                widget.setProperty(self.Property.Name, tab_setting.name)

                self.widget_list.append(widget)
                tab_layout.addWidget(widget)
                self.insertTab(self.count(), widget, tab_setting.name)
            except (TypeError, ValueError, IndexError, json.JSONDecodeError, DynamicObjectDecodeError) as err:
                print("{}".format(err))

    def __initData(self, data: dict):
        self.setData(data)

    def __initSignalAndSlots(self):
        for widget in self.widget_list:
            widget.settingChanged.connect(self.slotSettingChanged)
            widget.settingChangedDetail.connect(self.settingChangedDetail.emit)

    def insertCustomTabWidget(self, name: str, widget: QWidget, position: Optional[int] = None):
        if not isinstance(widget, QWidget):
            return False

        if not hasattr(widget, self.GET_DATA_METHOD_NAME) or not hasattr(widget.getData, "__call__"):
            print("Custom tab widget {!r} do not has {!r} method or {!r} is not callable".format(
                widget.__class__.__name__, self.GET_DATA_METHOD_NAME, self.GET_DATA_METHOD_NAME))
            return False

        if not hasattr(widget, self.SET_DATA_METHOD_NAME) or not hasattr(widget.setData, "__call__"):
            print("Custom tab widget {!r} do not has {!r} method or {!r} is not callable".format(
                widget.__class__.__name__, self.SET_DATA_METHOD_NAME, self.SET_DATA_METHOD_NAME))
            return False

        if not hasattr(widget, self.RESET_DATA_METHOD_NAME) or not hasattr(widget.resetDefaultData, "__call__"):
            print("Custom tab widget {!r} do not has {!r} method or {!r} is not callable".format(
                widget.__class__.__name__, self.RESET_DATA_METHOD_NAME, self.RESET_DATA_METHOD_NAME))
            return False

        self.widget_list.append(widget)
        self.insertTab(position or self.count(), widget, name)

    def getData(self) -> dict:
        data = dict()
        [data.update(widget.getData()) for widget in self.widget_list]
        return data

    def setData(self, data: dict):
        return all(widget.setData(data) for widget in self.widget_list)

    def getSettings(self) -> DynamicObject:
        data = self.getData()
        settings = self.settings
        for k, v in data.items():
            settings[k][self.Property.Data] = v
        return self.settings_cls(**settings)

    def resetDefaultData(self):
        [widget.resetDefaultData() for widget in self.widget_list]

    def slotSettingChanged(self):
        self.settingChanged.emit()

    def getTabWidget(self, name: str) -> Optional[QWidget]:
        for widget in self.widget_list:
            if widget.property(self.Property.Name) == name:
                return widget

        return None

    def getGroupWidgetManager(self, name: str) -> Optional[ComponentManager]:
        for widget in self.widget_list:
            manager = widget.getWidgetManager(name)
            if isinstance(manager, ComponentManager):
                return manager

        return None

    def slotDisableInput(self, disable: bool):
        [widget.ui_manager.setDisabled(disable) for widget in self.widget_list]


class LogMessageWidget(QTextEdit):
    LOG_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    DISPLAY_DEBUG, DISPLAY_INFO, DISPLAY_WARN, DISPLAY_ERROR = (0x1, 0x2, 0x4, 0x8)
    DISPLAY_ALL = DISPLAY_INFO | DISPLAY_DEBUG | DISPLAY_ERROR | DISPLAY_WARN

    # noinspection SpellCheckingInspection
    def __init__(self, filename: str, log_format: str = "%(asctime)s %(levelname)s %(message)s",
                 level: int = logging.DEBUG, propagate: bool = False, display_filter: int = DISPLAY_ALL,
                 parent: Optional[QWidget] = None):
        super(LogMessageWidget, self).__init__(parent)

        self._logger = LoggerWrap(filename, log_format, level, logging.ERROR, propagate)
        self.setReadOnly(True)
        self._startTime = datetime.now()
        self._displayFilter = display_filter
        self.textChanged.connect(self.slotAutoScroll)

        # Context menu
        self.ui_context_menu = QMenu(self)
        self.ui_show_info = QAction(self.tr("Show Info"), self)
        self.ui_show_warn = QAction(self.tr("Show Warn"), self)
        self.ui_show_debug = QAction(self.tr("Show Debug"), self)
        self.ui_show_error = QAction(self.tr("Show Error"), self)
        self.ui_clean_action = QAction(self.tr("Clear All"), self)

        self.ui_context_menu.addAction(self.ui_clean_action)
        for action in (self.ui_show_info, self.ui_show_warn, self.ui_show_debug, self.ui_show_error):
            action.setCheckable(True)
            action.setChecked(True)
            # noinspection PyUnresolvedReferences
            action.triggered.connect(self.slotShowSelectLog)
            self.ui_context_menu.addAction(action)

        # noinspection PyUnresolvedReferences
        self.ui_clean_action.triggered.connect(self.clear)
        self.setDisplayFilter(display_filter, load=False)

    def getLevelMask(self, level: int) -> int:
        return {
            logging.INFO: self.DISPLAY_INFO,
            logging.WARN: self.DISPLAY_WARN,
            logging.DEBUG: self.DISPLAY_DEBUG,
            logging.ERROR: self.DISPLAY_ERROR
        }.get(level, self.DISPLAY_ALL)

    def _enableInfo(self, en: bool):
        if en:
            self._displayFilter |= self.DISPLAY_INFO
        else:
            self._displayFilter &= ~self.DISPLAY_INFO

    def _enableWarn(self, en: bool):
        if en:
            self._displayFilter |= self.DISPLAY_WARN
        else:
            self._displayFilter &= ~self.DISPLAY_WARN

    def _enableDebug(self, en: bool):
        if en:
            self._displayFilter |= self.DISPLAY_DEBUG
        else:
            self._displayFilter &= ~self.DISPLAY_DEBUG

    def _enableError(self, en: bool):
        if en:
            self._displayFilter |= self.DISPLAY_ERROR
        else:
            self._displayFilter &= ~self.DISPLAY_ERROR

    def infoEnabled(self, target: Optional[int] = None):
        return (target or self._displayFilter) & self.DISPLAY_INFO

    def warnEnabled(self, target: Optional[int] = None):
        return (target or self._displayFilter) & self.DISPLAY_WARN

    def debugEnabled(self, target: Optional[int] = None):
        return (target or self._displayFilter) & self.DISPLAY_DEBUG

    def errorEnabled(self, target: Optional[int] = None):
        return (target or self._displayFilter) & self.DISPLAY_ERROR

    def info(self, msg: str):
        self.logging(UiLogMessage.genDefaultInfoMessage(msg))

    def warn(self, msg: str):
        self.logging(UiLogMessage.genDefaultWarnMessage(msg))

    def debug(self, msg: str):
        self.logging(UiLogMessage.genDefaultDebugMessage(msg))

    def error(self, msg: str):
        self.logging(UiLogMessage.genDefaultErrorMessage(msg))

    @Slot(object)
    def logging(self, message: UiLogMessage, write_to_log: bool = True):
        if not isinstance(message, UiLogMessage):
            return

        # Show log
        if self._displayFilter & self.getLevelMask(message.level):
            self.append("<font color='{}' size={}>{}: {}</font>".format(
                message.color, message.font_size,
                logging.getLevelName(message.level),
                html.escape(message.content))
            )

        # Write to log file if write_to_log set
        write_to_log and self._logger.logging(message)

    @Slot(object)
    def filterLog(self, levels: List[int]):
        if not isinstance(levels, list):
            return

        try:
            # First read all log to memory
            with open(self._logger.filename, encoding="utf-8") as fp:
                text = fp.read()
        except UnicodeDecodeError:
            # Loading failed delete log
            text = ""

        # Process data
        valid_record = list()
        for level in levels:
            level_name = logging.getLevelName(level)

            for record in text.split("\n"):
                record.strip()
                time_end = record.find(",")
                time_str = record[:time_end]

                try:
                    record_time = datetime.strptime(time_str, self.LOG_TIME_FORMAT)
                    record_time = record_time.replace(microsecond=int(record[time_end + 1: time_end + 4]) * 1000)
                except ValueError:
                    continue

                if record_time < self._startTime:
                    continue

                level_name_start = record.find(level_name)
                if level_name_start == -1:
                    continue

                # Append to record list
                valid_record.append(UiLogMessage.genDefaultMessage(record[level_name_start + len(level_name):], level))

        # Append to browser
        self.clear()
        for record in valid_record:
            self.logging(record, False)

    def slotAutoScroll(self):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)

    def slotShowSelectLog(self):
        levels = list()
        if self.ui_show_info.isChecked():
            levels.append(logging.INFO)

        if self.ui_show_warn.isChecked():
            levels.append(logging.WARN)

        if self.ui_show_debug.isChecked():
            levels.append(logging.DEBUG)

        if self.ui_show_error.isChecked():
            levels.append(logging.ERROR)

        self._enableInfo(self.ui_show_info.isChecked())
        self._enableWarn(self.ui_show_warn.isChecked())
        self._enableDebug(self.ui_show_debug.isChecked())
        self._enableError(self.ui_show_error.isChecked())
        self.filterLog(levels)

    def setDisplayFilter(self, display_filter: int, load: bool = True):
        if not isinstance(display_filter, int):
            return

        if self.infoEnabled(display_filter):
            self.ui_show_info.setChecked(True)
        else:
            self.ui_show_info.setChecked(False)

        if self.warnEnabled(display_filter):
            self.ui_show_warn.setChecked(True)
        else:
            self.ui_show_warn.setChecked(False)

        if self.debugEnabled(display_filter):
            self.ui_show_debug.setChecked(True)
        else:
            self.ui_show_debug.setChecked(False)

        if self.errorEnabled(display_filter):
            self.ui_show_error.setChecked(True)
        else:
            self.ui_show_error.setChecked(False)

        if load:
            self.slotShowSelectLog()

    def contextMenuEvent(self, ev: QContextMenuEvent):
        self.ui_context_menu.exec_(ev.globalPos())
