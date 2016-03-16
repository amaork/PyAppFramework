# -*- coding: utf-8 -*-

"""
Class Tree

PaintWidget
    |------RgbWidget
    |------LumWidget
    |------ColorWidget
                |------CursorWidget
"""

import types
from PySide.QtCore import *
from PySide.QtGui import *

__all__ = ['ColorWidget', 'CursorWidget', 'RgbWidget', 'updateListWidget', 'updateTableWidget', 'ListWidgetDefStyle']

ListWidgetDefStyle = {"font": "Times New Roman", "size": 14, "color": QColor(51, 153, 255)}


class PaintWidget(QWidget):
    def __init__(self, parent=None):
        super(PaintWidget, self).__init__(parent)

    def getXRatio(self, maxValue):
        if not self.isNumber(maxValue):
            return 0

        if isinstance(maxValue, int):
            maxValue = float(maxValue)

        x = self.cursor().pos().x()
        return int(round(maxValue / self.width() * x))

    def getYRatio(self, maxValue):
        if not self.isNumber(maxValue):
            return 0

        if isinstance(maxValue, int):
            maxValue = float(maxValue)

        y = self.cursor().pos().y()
        return int(round(maxValue / self.height() * y))

    def getCursorPos(self):
        x = self.cursor().pos().x()
        y = self.cursor().pos().y()
        return x, y

    def getDynamicTextPos(self, fontSize, textSize):
        """Get dynamic text position

        :param fontSize: Font size
        :param textSize: Text length
        :return:QPointF
        """
        if not isinstance(fontSize, int) or not isinstance(textSize, int):
            return QPointF(self.width() / 2, self.height() / 2)

        # Get mouse position
        x, y = self.getCursorPos()

        if x < self.width() / 2:
            tx = x + fontSize * 3
        else:
            tx = x - (textSize - 2) * fontSize

        if y < self.height() / 2:
            ty = y + fontSize * 3
        else:
            ty = y - fontSize * 2

        return QPointF(tx, ty)

    def drawDynamicText(self, painter, font, color, text):
        """Draw dynamic text follow mouse movement

        :param painter:
        :param font: Text Font
        :param color: Text color
        :param text: draw text
        :return:
        """
        if not isinstance(painter, QPainter) or not isinstance(font, QFont) or not self.isColor(color):
            return False

        if not isinstance(text, types.StringTypes):
            return False

        painter.setFont(font)
        painter.setPen(QPen(color))
        painter.drawText(self.getDynamicTextPos(font.pointSize(), len(text)), text)

    def drawRectangle(self, painter, color, start, width, height):
        """

        :param painter:QPainter
        :param color: Rectangle background color
        :param start: Rectangle upper left conner point position
        :param width: Rectangle width
        :param height:Rectangle height
        :return:
        """
        if not isinstance(painter, QPainter) or not self.isColor(color):
            return False

        if not isinstance(start, QPointF) or not self.isValidWidth(width) or not self.isValidHeight(height):
            return False

        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(QColor(color)))
        painter.drawRect(start.x(), start.y(), width, height)
        return True

    def drawBackground(self, painter, color):
        if not isinstance(painter, QPainter) or not self.isColor(color):
            return False

        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(QBrush(QColor(color)))
        painter.drawRect(self.rect())
        return True

    def drawHorizontalLine(self, painter, color, y, xs, xe):
        """Draw a horizontal line at y form xs to xe

        :param painter:
        :param color: line color
        :param y: Vertical pos
        :param xs:Horizontal line start
        :param xe:Horizontal line end
        :return:True or false
        """
        if not isinstance(painter, QPainter) or not self.isColor(color):
            return False

        if not self.isValidHeight(y) or not self.isValidHRange(xs, xe):
            return False

        painter.setPen(QPen(color))
        painter.drawLine(QPointF(xs, y), QPointF(xe, y))

    def drawVerticalLine(self, painter, color, x, ys, ye):
        """

        :param painter:
        :param color: line color
        :param x: Horizontal pos
        :param ys: Vertical line start
        :param ye: Vertical line end
        :return:
        """
        if not isinstance(painter, QPainter) or not self.isColor(color):
            return False

        if not self.isValidWidth(x) or not self.isValidVRange(ys, ye):
            return False

        painter.setPen(QPen(color))
        painter.drawLine(QPointF(x, ys), QPointF(x, ye))

    @staticmethod
    def isColor(color):
        if not isinstance(color, QColor) and not isinstance(color, Qt.GlobalColor):
            return False

        return True

    @staticmethod
    def isNumber(number):
        if not isinstance(number, float) and not isinstance(number, int):
            return False

        return True

    def isValidWidth(self, x):
        if not isinstance(x, int):
            return False

        if x < 0 or x > self.width():
            return False

        return True

    def isValidHeight(self, y):
        if not isinstance(y, int):
            return False

        if y < 0 or y > self.height():
            return False

        return True

    def isValidHRange(self, start, end):
        if not self.isValidWidth(start) or not self.isValidWidth(end):
            return False

        return start < end

    def isValidVRange(self, start, end):
        if not self.isValidHeight(start) or not self.isValidHeight(end):
            return False

        return start < end


class ColorWidget(PaintWidget):
    colorMax = 255.0

    # When color changed will send is signal
    colorChanged = Signal(int, int, int)

    # When mouse release send this signal
    colorStopChange = Signal(int, int, int)

    def __init__(self, font=QFont("Times New Roman", 10), parent=None):
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

    def getColor(self):
        """Get a color from color table

        :return:
        """
        self.colorIndex += 1
        if self.colorIndex >= len(self.colorTable):
            self.colorIndex = 0

        return self.colorTable[self.colorIndex]

    def addColor(self, color):
        """Add color to color group

        :param color:(QColor, QColor)
        :return:
        """
        if not isinstance(color, tuple) or len(color) != 2:
            return False

        if not isinstance(color[0], QColor) or not isinstance(color[1], QColor):
            return False

        self.colorTable.append(color)

    def getBackgroundColor(self):
        return QColor(self.color[0])

    def getForegroundColor(self):
        return QColor(self.color[1])

    def mouseDoubleClickEvent(self, ev):
        # Left button change background color
        if ev.button() == Qt.LeftButton:
            self.color = self.getColor()
            self.update()
        # Right button exit
        elif ev.button() == Qt.RightButton:
            self.close()

    def mouseReleaseEvent(self, ev):
        # Send color changed signal
        value = self.getXRatio(self.colorMax)
        color = ColorWidget.adjustColor(self.getBackgroundColor(), value)
        self.colorChanged.emit(color.red(), color.green(), color.blue())
        self.colorStopChange.emit(color.red(), color.green(), color.blue())

    def mouseMoveEvent(self, ev):
        # Update re paint
        self.update()

    def paintEvent(self, ev):
        painter = QPainter(self)
        value = self.getXRatio(self.colorMax)
        color = ColorWidget.adjustColor(self.getBackgroundColor(), value)
        text = "R:{0:d}, G:{1:d}, B{2:d}".format(color.red(), color.green(), color.blue())

        # Send color changed signal
        self.colorChanged.emit(color.red(), color.green(), color.blue())

        # Draw cross line and cursor pos
        self.drawBackground(painter, color)
        if value < 64:
            color = QColor(Qt.white)
        else:
            color = self.getForegroundColor()

        self.drawDynamicText(painter, self.font, color, text)

    @staticmethod
    def checkColor(color):
        if not ColorWidget.isColor(color):
            return None

        if isinstance(color, Qt.GlobalColor):
            color = QColor(color)

        return color

    @staticmethod
    def analysisColor(color):
        color = ColorWidget.checkColor(color)
        if not isinstance(color, QColor):
            return 0, 0, 0

        return color.red() > 0, color.green() > 0, color.blue() > 0

    @staticmethod
    def adjustColor(color, value):
        color = ColorWidget.checkColor(color)
        if not isinstance(color, QColor):
            return QColor(Qt.white)

        if not isinstance(value, int) or (value < 0 or value > 255):
            return color

        colorSet = ColorWidget.analysisColor(color)

        if colorSet[0]:
            color.setRed(value)

        if colorSet[1]:
            color.setGreen(value)

        if colorSet[2]:
            color.setBlue(value)

        return color


class CursorWidget(ColorWidget):
    # When cursor changed will send this signal
    cursorChanged = Signal(int, int)

    # When cursor stop changed will send this signal
    cursorStopChange = Signal(int, int)

    def __init__(self, font=QFont("Times New Roman", 10), parent=None):
        super(CursorWidget, self).__init__(font, parent)
        self.color = (Qt.white, Qt.black)
        x, y = self.getCursorPos()
        self.oldPos = QPoint(x, y)
        self.oldColor = self.getBackgroundColor()

    def mouseReleaseEvent(self, ev):
        # Only watch left button
        if ev.button() == Qt.RightButton:
            return

        # Send color changed signal
        if self.getBackgroundColor() != self.oldColor:
            color = self.getBackgroundColor()
            self.colorChanged.emit(color.red(), color.green(), color.blue())

        # Mouse release and cursor position changed send mouse pos
        if ev.pos() != self.oldPos:
            x = ev.pos().x()
            y = ev.pos().y()
            self.oldPos = ev.pos()
            self.cursorChanged.emit(x, y)
            self.cursorStopChange.emit(x, y)

    def paintEvent(self, ev):
        painter = QPainter(self)
        x, y = self.getCursorPos()
        text = "X:{0:d}, Y:{1:d}".format(x, y)

        # Cursor changed
        self.cursorChanged.emit(x, y)

        # Draw cross line and cursor pos
        self.drawBackground(painter, self.getBackgroundColor())
        self.drawVerticalLine(painter, self.getForegroundColor(), x, 0, self.height())
        self.drawHorizontalLine(painter, self.getForegroundColor(), y, 0, self.width())
        self.drawDynamicText(painter, self.font, self.getForegroundColor(), text)


class RgbWidget(PaintWidget):
    # When r, g, b changed send this signal
    rgbChanged = Signal(bool, bool, bool)

    def __init__(self, parent=None):
        super(RgbWidget, self).__init__(parent)
        self.showFullScreen()
        self.rgb = [True, True, True]
        self.part = int(self.height() / 3)
        self.colorTable = (Qt.red, Qt.green, Qt.blue)
        self.rgbChanged.emit(self.rgb[0], self.rgb[1], self.rgb[2])

    def mouseDoubleClickEvent(self, ev):
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
            # self.rgbChanged.emit(self.rgb[0], self.rgb[1], self.rgb[2])
            self.close()

    def paintEvent(self, ev):
        painter = QPainter(self)
        self.rgbChanged.emit(self.rgb[0], self.rgb[1], self.rgb[2])

        for idx, rgb in enumerate(self.rgb):
            if rgb:
                color = self.colorTable[idx]
            else:
                color = Qt.black
                self.drawHorizontalLine(painter, QColor(Qt.white), idx * self.part - 1, 0, self.width())

            self.drawRectangle(painter, color, QPointF(0, idx * self.part), self.width(), self.part)


def updateListWidget(widget, items, select="", style=ListWidgetDefStyle, callback=None):
    """Update QListWidget add items to widget and select item than call a callback function

    :param widget: QListWidget
    :param items: QListWidget items data
    :param select: select item
    :param style: Item stylesheet
    :param callback: callback function
    :return: return select item number
    """

    selectRow = 0

    # Type check
    if not isinstance(widget, QListWidget) or not hasattr(items, "__iter__"):
        print "TypeCheckError"
        return 0

    if len(items) and not isinstance(items[0], types.StringTypes):
        print "TypeCheckError"
        return 0

    if len(select) and not isinstance(select, types.StringTypes):
        print "TypeCheckError"
        return 0

    # Remove list old items
    for _ in range(widget.count()):
        widget.removeItemWidget(widget.item(0))
        widget.takeItem(0)

    # If style is set change item style
    if isinstance(style, dict) and "font" in style and "size" in style:
        widget.setFont(QFont(style.get("font"), style.get("size")))

    # Add items to widget, if select is set mark it's selected
    for idx, name in enumerate(items):
        # Create a item
        item = QListWidgetItem(name)

        # Change select row
        if name == select:
            selectRow = idx

            # If has style change it
            if isinstance(style, dict) and "color" in style:
                item.setBackground(QBrush(style.get("color")))

        widget.addItem(item)

    # Select row
    widget.setCurrentRow(selectRow)

    # Call callback
    if hasattr(callback, "__call__"):
        callback(widget.currentItem())

    return selectRow


def updateTableWidget(widget, rowSize, columnSize, data, select=0, style=ListWidgetDefStyle):
    """Update QTableWidget

    :param widget: QTableWidget
    :param rowSize: table widget row size
    :param columnSize: table widget column size
    :param data: table data
    :param select: default select table
    :param style: select item
    :return:
    """

    # Type check
    if not isinstance(widget, QTableWidget) or not isinstance(rowSize, int) or not isinstance(columnSize, int):
        print "TypeCheckError"
        return False

    # Data check
    # print len(data), len(data[0]), rowSize, columnSize
    if not hasattr(data, "__iter__") or len(data) != rowSize or len(data[0]) != columnSize:
        print "TypeCheckError"
        return False

    # Set stylesheet
    if isinstance(style, dict) and "font" in style and "size" in style:
        widget.setFont(QFont(style.get("font"), style.get("size")))

    # Set table size
    widget.setRowCount(rowSize)
    widget.setColumnCount(columnSize)

    # Add data to table
    item = ""
    for row, rowData in enumerate(data):
        for column, columnData in enumerate(rowData):
            if isinstance(columnData, int):
                item = "{0:d}".format(columnData)
            elif isinstance(columnData, str):
                item = columnData
            elif isinstance(columnData, float):
                item = "{0:.2f}".format(columnData)

            widget.setItem(row, column, QTableWidgetItem(item))

    # Select item
    if select < widget.rowCount():
        widget.selectRow(select)
