#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import types
from PySide.QtCore import *
from PySide.QtGui import *

__all__ = ['ColorWidget', 'CursorWidget', 'updateListWidget', 'updateTableWidget']

ListWidgetDefStyle = {"font": "Times New Roman", "size": 14, "color": QColor(51, 153, 255)}


class PaintWidget(QWidget):
    def __init__(self, parent=None):
        super(PaintWidget, self).__init__(parent)

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
        if not isinstance(painter, QPainter) or not isinstance(font, QFont) or not isinstance(color, QColor):
            return False

        if not isinstance(text, types.StringTypes):
            return False

        painter.setFont(font)
        painter.setPen(QPen(color))
        painter.drawText(self.getDynamicTextPos(font.pointSize(), len(text)), text)

    def drawBackground(self, painter, color):
        if not isinstance(painter, QPainter):
            return False

        if not isinstance(color, QColor) and not isinstance(color, Qt.GlobalColor):
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
        if not isinstance(painter, QPainter) or not isinstance(color, QColor):
            return False

        if not isinstance(y, int) or y > self.height():
            return False

        if (not isinstance(xs, int) or xs < 0) or (not isinstance(xe, int) or xe > self.width()) or xs > xe:
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
        if not isinstance(painter, QPainter) or not isinstance(color, QColor):
            return False

        if not isinstance(x, int) or x > self.width():
            return False

        if (not isinstance(ys, int) or ys < 0) or (not isinstance(ye, int) or ye > self.height()) or ys > ye:
            return False

        painter.setPen(QPen(color))
        painter.drawLine(QPointF(x, ys), QPointF(x, ye))


class ColorWidget(PaintWidget):
    # When color changed will send is signal
    colorChanged = Signal(int, int, int)

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

    def calcColorValue(self):
        """According current mouse x position calc color

        :return:
        """
        x = self.cursor().pos().x()
        value = int(round(255.0 / self.width() * x))
        return value

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
        value = self.calcColorValue()
        color = ColorWidget.adjustColor(self.getBackgroundColor(), value)
        self.colorChanged.emit(color.red(), color.green(), color.blue())

    def mouseMoveEvent(self, ev):
        # Update re paint
        self.update()

    def paintEvent(self, ev):
        painter = QPainter(self)
        value = self.calcColorValue()
        color = ColorWidget.adjustColor(self.getBackgroundColor(), value)
        text = "R:{0:d}, G:{1:d}, B{2:d}".format(color.red(), color.green(), color.blue())

        # Draw cross line and cursor pos
        self.drawBackground(painter, color)
        if value < 64:
            color = QColor(Qt.white)
        else:
            color = self.getForegroundColor()

        self.drawDynamicText(painter, self.font, color, text)

    @staticmethod
    def checkColor(color):
        if not isinstance(color, QColor) and not isinstance(color, Qt.GlobalColor):
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

    def __init__(self, font=QFont("Times New Roman", 10), parent=None):
        super(CursorWidget, self).__init__(font, parent)
        self.color = (Qt.white, Qt.black)
        x, y = self.getCursorPos()
        self.oldPos = QPoint(x, y)

    def mouseReleaseEvent(self, ev):
        # Only watch left button
        if ev.button() == Qt.RightButton:
            return

        # Send color change signal
        color = self.getBackgroundColor()
        self.colorChanged.emit(color.red(), color.green(), color.blue())

        # Mouse release and cursor position changed send mouse pos
        if ev.pos() != self.oldPos:
            x = ev.pos().x()
            y = ev.pos().y()
            self.oldPos = ev.pos()
            self.cursorChanged.emit(x, y)
            # print x, y

    def paintEvent(self, ev):
        painter = QPainter(self)
        x, y = self.getCursorPos()
        text = "X:{0:d}, Y:{1:d}".format(x, y)

        # Draw cross line and cursor pos
        self.drawBackground(painter, self.getBackgroundColor())
        self.drawVerticalLine(painter, self.getForegroundColor(), x, 0, self.height())
        self.drawHorizontalLine(painter, self.getForegroundColor(), y, 0, self.width())
        self.drawDynamicText(painter, self.font, self.getForegroundColor(), text)


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


class ListDemoWidget(QWidget):
    itemSelected = Signal(str)

    def __init__(self, parent=None):
        super(ListDemoWidget, self).__init__(parent)

        self.font = ListWidgetDefStyle.get("font")
        self.size = ListWidgetDefStyle.get("size")
        self.color = ListWidgetDefStyle.get("color")
        self.styleSheet = {"font": self.font, "size": self.size, "color": self.color}

        # Elements
        self.listWidget = QListWidget()
        self.fontButton = QPushButton("Font")
        self.colorButton = QPushButton("Color")
        self.addButton = QPushButton("Add item")
        self.markButton = QPushButton("Mark item")

        for idx in range(11):
            self.listWidget.addItem("Item{0:d}".format(idx))

        # Signal and slots
        self.addButton.clicked.connect(self.slotAddItem)
        self.fontButton.clicked.connect(self.slotGetFont)
        self.markButton.clicked.connect(self.slotMarkItem)
        self.colorButton.clicked.connect(self.slotGetColor)
        self.listWidget.doubleClicked.connect(self.slotSelectItem)

        # Layout
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.fontButton)
        button_layout.addWidget(self.colorButton)
        button_layout.addWidget(self.markButton)
        button_layout.addWidget(self.addButton)

        layout = QVBoxLayout()
        layout.addWidget(self.listWidget)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.setWindowTitle("ListWidget Dialog Demo")

    def getListItems(self):
        items = []
        for idx in range(self.listWidget.count()):
            items.append(self.listWidget.item(idx).text())

        return items

    def getCurrentItem(self):
        return self.listWidget.currentItem().text()

    def slotGetFont(self):
        font, ok = QFontDialog.getFont(QFont(ListWidgetDefStyle.get("font")), self)
        if ok:
            self.font = font.family()
            self.size = font.pointSize()
            updateListWidget(self.listWidget, self.getListItems(), self.getCurrentItem(),
                             {"font": self.font, "size": self.size, "color": self.color})

    def slotGetColor(self):
        self.color = QColorDialog.getColor(self.color, self)
        updateListWidget(self.listWidget, self.getListItems(), self.getCurrentItem(),
                         {"font": self.font, "size": self.size, "color": self.color})

    def slotAddItem(self):
        text, ok = QInputDialog.getText(self, "Please enter items text", "Text:",
                                        QLineEdit.Normal, QDir.home().dirName())

        if ok:
            items = self.getListItems()
            items.append(text)
            updateListWidget(self.listWidget, items, text, {"font": self.font, "size": self.size, "color": self.color})

    def slotMarkItem(self):
        updateListWidget(self.listWidget, self.getListItems(), self.getCurrentItem(),
                         {"font": self.font, "size": self.size, "color": self.color})

    def slotSelectItem(self, item):
        text = self.getCurrentItem()
        self.slotMarkItem()
        self.itemSelected.emit(text)


class Demo(QMainWindow):
    def __init__(self):
        super(Demo, self).__init__()
        frameStyle = QFrame.Sunken | QFrame.Panel

        self.layout = QGridLayout()

        self.listWidget = ListDemoWidget()
        self.listWidget.setHidden(True)
        self.listLabel = QLabel()
        self.listLabel.setFrameStyle(frameStyle)

        self.colorWidget = ColorWidget()
        self.colorWidget.setHidden(True)
        self.colorLabel = QLabel()
        self.colorLabel.setFrameStyle(frameStyle)

        self.cursorWidget = CursorWidget()
        self.cursorWidget.setHidden(True)
        self.cursorLabel = QLabel()
        self.cursorLabel.setFrameStyle(frameStyle)

        self.listButton = QPushButton("Get list")
        self.colorButton = QPushButton("Get color")
        self.colorButton.setToolTip("Double click exit")
        self.cursorButton = QPushButton("Get cursor")
        self.cursorButton.setToolTip("Double click exit")

        self.listButton.clicked.connect(self.showWidget)
        self.colorButton.clicked.connect(self.showWidget)
        self.cursorButton.clicked.connect(self.showWidget)
        self.listWidget.itemSelected.connect(self.setItem)
        self.colorWidget.colorChanged.connect(self.setColor)
        self.cursorWidget.colorChanged.connect(self.setColor)
        self.cursorWidget.cursorChanged.connect(self.setCursor)

        self.layout.addWidget(self.listButton, 0, 0)
        self.layout.addWidget(self.listLabel, 0, 1)
        self.layout.addWidget(self.colorButton, 1, 0)
        self.layout.addWidget(self.colorLabel, 1, 1)
        self.layout.addWidget(self.cursorButton, 2, 0)
        self.layout.addWidget(self.cursorLabel, 2, 1)

        self.setCentralWidget(QWidget())
        self.centralWidget().setLayout(self.layout)
        self.setWindowTitle("Widget Demo")

    def showWidget(self):
        if self.sender() == self.listButton:
            self.listWidget.setHidden(False)
        elif self.sender() == self.colorButton:
            self.colorWidget.setHidden(False)
        elif self.sender() == self.cursorButton:
            self.cursorWidget.setHidden(False)

    def setItem(self, item):
        self.listLabel.setText(item)

    def setColor(self, r, g, b):
        self.colorLabel.setText("R:{0:d} G{1:d} B{2:d}".format(r, g, b))

    def setCursor(self, x, y):
        self.cursorLabel.setText("X:{0:d} Y:{1:d}".format(x, y))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Demo()
    window.show()
    sys.exit(app.exec_())
