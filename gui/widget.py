# -*- coding: utf-8 -*-

"""
Class Tree

TableWidget

PaintWidget
    |------RgbWidget
    |------LumWidget
    |------ImageWidget
    |------ColorWidget
                |------CursorWidget
"""
import types
import os.path
from PySide.QtCore import *
from PySide.QtGui import *

__all__ = ['ColorWidget', 'CursorWidget', 'RgbWidget', 'LumWidget', 'ImageWidget', 'TableWidget',
           'updateListWidget', 'ListWidgetDefStyle']

ListWidgetDefStyle = {"font": "Times New Roman", "size": 14, "color": QColor(51, 153, 255)}


def __type_error(correct, error):
    print "TypeError, should be: {0:s}, actually is: {1:s}".format(type(correct), type(error))


class PaintWidget(QWidget):
    def __init__(self, parent=None):
        """Base class provide basic draw functions and get widget message """

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

    def getCursorLum(self):
        """Get current cursor position luminance

        :return:
        """
        x, y = self.getCursorPos()
        color = QColor(QPixmap().grabWindow(self.winId()).toImage().pixel(x, y))
        return max(color.red(), color.green(), color.blue())

    def getDynamicTextPos(self, fontSize, textSize):
        """Get dynamic text position

        :param fontSize: Font size
        :param textSize: Text length
        :return:QPoint
        :return:QPoint
        """
        if not isinstance(fontSize, int) or not isinstance(textSize, int):
            return QPoint(self.width() / 2, self.height() / 2)

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

    def drawCenterText(self, painter, font, color, text):
        """Draw dynamic text follow mouse movement

        :param painter:
        :param font: Text Font
        :param color: Text color
        :param text: draw text
        :return:
        """
        if not isinstance(painter, QPainter) or not isinstance(font, QFont) or not self.isColor(color):
            print "TypeError"
            return False

        if not isinstance(text, types.StringTypes):
            print "TextError"
            return False

        painter.setFont(font)
        painter.setPen(QPen(QColor(color)))
        painter.drawText(self.rect(), Qt.AlignCenter, self.tr(text))

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
        painter.setPen(QPen(QColor(color)))
        painter.drawText(self.getDynamicTextPos(font.pointSize(), len(text)), text)

    def drawSquare(self, painter, color, start, side):
        return self.drawRectangle(painter, color, start, side, side)

    def drawRectangle(self, painter, color, start, width, height):
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

    def drawCenterRect(self, painter, color, width, height):
        if not self.isValidWidth(width) or not self.isValidHeight(height):
            return False

        x = self.rect().center().x()
        y = self.rect().center().y()
        start = QPoint(x - width / 2, y - height / 2)
        return self.drawRectangle(painter, color, start, width, height)

    def drawCenterSquare(self, painter, color, side):
        return self.drawCenterRect(painter, color, side, side)

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
        painter.drawLine(QPoint(xs, y), QPoint(xe, y))

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
        painter.drawLine(QPoint(x, ys), QPoint(x, ye))

    @staticmethod
    def adjustColorBrightness(color, brightness):
        """Adjust color brightness

        :param color: QColor
        :param brightness: brightness value (0 - 255)
        :return:success return after just color, else Qt.back
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
    def getColorMode(color):
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
    def getColorRawValue(color):
        if not PaintWidget.isColor(color):
            return 0

        color = QColor(color)
        return color.rgb() & 0xffffff

    @staticmethod
    def getRgbMode(r, g, b):
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

    # When color changed will send is signal, r, g, b value
    colorChanged = Signal(int, int, int)

    # When mouse release send this signal
    colorStopChange = Signal(int, int, int)

    def __init__(self, font=QFont("Times New Roman", 10), parent=None):
        """Color grab widget double click mouse left button change color, mouse horizontal move change color brightness

        ColorWidget provide two signal 'colorChanged' and 'colorStopChange', when mouse horizontal moved, the color
        will changed, the 'colorChanged' signal will send. 'colorStopChange' signal will send when the mouse is stop .

        Signal: colorChanged(int r, int g, int b)
        Signal: colorStopChange(int r, int g, int b)

        :param font: Color r, g, b value display font
        :param parent:
        :return:None double click mouse right button will exit
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

    def getColor(self):
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
        if ev.button() == Qt.LeftButton:
            value = self.getXRatio(self.colorMax)
            color = ColorWidget.adjustColorBrightness(self.getBackgroundColor(), value)
            self.colorChanged.emit(color.red(), color.green(), color.blue())
            self.colorStopChange.emit(color.red(), color.green(), color.blue())

    def mouseMoveEvent(self, ev):
        # Update re paint
        self.update()

    def paintEvent(self, ev):
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

    def __init__(self, font=QFont("Times New Roman", 10), parent=None):
        """Cursor grab widget, double click mouse left button change color, mouse moved change cursor position

        CursorWidget provide two signal 'cursorChanged' and 'cursorStopChange', when mouse moved, the cursor position
        will changed, the 'cursorChanged' signal will send. 'cursorStopChange' signal will send when the mouse is stop .

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

    def mouseReleaseEvent(self, ev):
        # Send color changed signal
        if self.getBackgroundColor() != self.oldColor:
            color = self.getBackgroundColor()
            self.colorChanged.emit(color.red(), color.green(), color.blue())

        # Mouse release and cursor position changed send mouse pos
        if ev.button() == Qt.LeftButton:
            x = ev.pos().x()
            y = ev.pos().y()
            self.cursorChanged.emit(x, y, self.getColorRawValue(self.getBackgroundColor()))
            self.cursorStopChange.emit(x, y, self.getColorRawValue(self.getBackgroundColor()))

    def paintEvent(self, ev):
        painter = QPainter(self)
        x, y = self.getCursorPos()
        text = "X:{0:d}, Y:{1:d}".format(x, y)

        # Cursor changed
        self.cursorChanged.emit(x, y, self.getColorRawValue(self.getBackgroundColor()))

        # Draw cross line and cursor pos
        self.drawBackground(painter, self.getBackgroundColor())
        self.drawVerticalLine(painter, self.getForegroundColor(), x, 0, self.height())
        self.drawHorizontalLine(painter, self.getForegroundColor(), y, 0, self.width())
        self.drawDynamicText(painter, self.font, self.getForegroundColor(), text)


class RgbWidget(PaintWidget):
    # When r, g, b changed send this signal
    rgbChanged = Signal(bool, bool, bool)

    def __init__(self, parent=None):
        """ RGB color control widget, double click the color zone will turn of or turn off this color.

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

    def __init__(self, font=QFont("Times New Roman", 10), parent=None):
        """Luminance grab widget, double click mouse left button change mode, mouse moved change windows Luminance

        Press mouse left button, then move mouse will change the low luminance
        Press mouse right button, then move mouse will change the high luminance

        LumWidget provide 2 signal 'lumChanged' and 'lumStopChange', when mouse moved, the windows Luminance
        will changed, the 'lumChanged' signal will send. 'lumStopChange' signal will send when the mouse is stop .

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

    def getLumMode(self):
        self.lumIndex += 1
        if self.lumIndex >= len(self.LUM_MODE):
            self.lumIndex = 0

        return self.LUM_MODE[self.lumIndex]

    def getLowLum(self):
        return QColor(self.lum[0], self.lum[0], self.lum[0])

    def getHighLum(self):
        return QColor(self.lum[1], self.lum[1], self.lum[1])

    def mouseMoveEvent(self, ev):
        self.lum[self.adjustHigh] = self.getXRatio(self.lumMax)
        self.update()

    def mousePressEvent(self, ev):
        # If left key press adjust low
        if ev.button() == Qt.LeftButton:
            self.adjustHigh = False
        # Right button press adjust high
        elif ev.button() == Qt.RightButton:
            self.adjustHigh = True

    def mouseReleaseEvent(self, ev):
        if self.lum != self.oldLum:
            self.oldLum = self.lum
            self.lumChanged.emit(self.lum[1], self.lum[0], self.lumMode)
            self.lumStopChange.emit(self.lum[1], self.lum[0], self.lumMode)

    def mouseDoubleClickEvent(self, ev):
        # Left button change background color
        if ev.button() == Qt.LeftButton:
            self.lumMode = self.getLumMode()
            self.lum = [0, int(self.lumMax)]
            self.update()

        # Right button exit
        elif ev.button() == Qt.RightButton:
            self.close()

    def paintEvent(self, ev):
        painter = QPainter(self)
        self.drawBackground(painter, self.getLowLum())
        textColor = Qt.white if self.getCursorLum() < 64 else Qt.black
        text = "Hi:{0:d} Low:{1:d}".format(int(self.lum[1]), int(self.lum[0]))

        # Send lum changed signal
        self.lumChanged.emit(self.lum[1], self.lum[0], self.lumMode)

        if self.lumMode == self.CE1_MODE:
            self.drawCenterSquare(painter, self.getHighLum(), self.height() / 2)
        elif self.lumMode == self.CE2_MODE:
            self.drawCenterRect(painter, self.getHighLum(), self.width() / 2, self.height() / 2)
        elif self.lumMode == self.LF_MODE:
            self.drawRectangle(painter, self.getHighLum(), QPoint(0, 0), self.width() / 2, self.height())
        elif self.lumMode == self.UD_MODE:
            self.drawRectangle(painter, self.getHighLum(), QPoint(0, 0), self.width(), self.height() / 2)
        elif self.lumMode == self.CT_MODE:
            side = self.height() / 7
            self.drawBackground(painter, QColor(127, 127, 127))
            self.drawCenterSquare(painter, self.getHighLum(), side)
            self.drawSquare(painter, self.getLowLum(), QPoint(self.width() / 2 - side / 2, side), side)
            self.drawSquare(painter, self.getLowLum(), QPoint(self.width() / 2 - side / 2, side * 5), side)
            self.drawSquare(painter, self.getLowLum(), QPoint(self.width() / 2 - side * 2.5, side * 3), side)
            self.drawSquare(painter, self.getLowLum(), QPoint(self.width() / 2 + side * 1.5, side * 3), side)

        self.drawDynamicText(painter, self.font, textColor, text)


class ImageWidget(PaintWidget):
    def __init__(self, width=0, height=0, zoomIn=False, parent=None):
        """ImageWidget provide 3 method to draw a image

        drawFromFs  :   load a image from filesystem and show it
        drawFromMem :   load a image form memory data and show it
        drawFromText:   Dynamic draw a image with text

        :param width:
        :param height:
        :param zoomIn:
        :param parent:
        :return:
        """
        super(ImageWidget, self).__init__(parent)
        self.supportFormats = [str(name) for name in QImageReader.supportedImageFormats()]

        # Default setting
        self.text = ""
        self.textColor = Qt.black
        self.bgColor = Qt.lightGray
        self.textFont = QFont("Times New Roman", width / 16)

        # Draw image using
        self.image = QImage()

        # For grab cursor position pixel
        self.zoomIn = zoomIn
        self.zoomInFlag = False
        self.zoomInPattern = QPixmap()

        self.setMinimumSize(width, height)
        self.setMaximumSize(width, height)

    @Slot(str)
    def drawFromFs(self, filePath):
        """Load a image from filesystem, then display it

        :param filePath: Image file path
        :return:
        """
        if not isinstance(filePath, types.StringTypes) or not os.path.isfile(filePath):
            print "File path:{0:s} is not exist!".format(filePath)
            return False

        image = QImageReader(filePath)
        if not len(image.format()):
            print "File is not a image file:{0:s}".format(image.errorString())
            return False

        # Load image file to memory
        self.image = image.read()
        self.update()
        return True

    @Slot(object, object)
    def drawFromMem(self, data, imageFormat="bmp"):
        """Load image form memory

        :param data: Image data
        :param imageFormat: Image format
        :return:
        """
        if not isinstance(data, str) or len(data) == 0:
            print "Invalid image data:{0:s}".format(type(data))
            return False

        if not isinstance(imageFormat, str) or imageFormat not in self.supportFormats:
            print "Invalid image format:{0:s}".format(imageFormat)
            return False

        # Clear loadImageFromFs data
        self.image = QImage.fromData(data, imageFormat)
        self.update()
        return True

    @Slot(str)
    def drawFromText(self, text, textColor=Qt.black, bgColor=Qt.lightGray, fontSize=40):
        """Draw a text message in the center of the widget

        :param text: Text context
        :param textColor: Text color
        :param bgColor: Widget background color
        :param fontSize: fontSize
        :return:
        """
        if not isinstance(text, types.StringTypes):
            print "Text is not a string:{0:s}".format(type(text))
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
        fontMaxWidth = round(self.width() / textMaxLength)

        if self.textFont.pointSize() > fontMaxWidth:
            self.textFont.setPointSize(fontMaxWidth)

        if all(ord(c) < 128 for c in text):
            self.text = str(text)
        else:
            self.text = text.encode("utf-8")

        self.image = QImage()
        self.update()

    def paintEvent(self, ev):
        painter = QPainter(self)

        # Is image show it
        if not self.image.isNull():
            painter.drawImage(self.rect(), self.image)
        # Draw text and show
        else:
            self.drawBackground(painter, self.bgColor)
            self.drawCenterText(painter, self.textFont, self.textColor, self.text)


class TableWidget(QTableWidget):
    def __init__(self, max_column, hide_header=False, parent=None):
        """Create a QTableWidget

        :param max_column: max column number
        :param hide_header: hide vertical and horizontal header
        :param parent:
        :return:
        """
        super(TableWidget, self).__init__(parent)

        self.setColumnCount(max_column)
        self.hideHeaders(hide_header)

    def __checkRow(self, row):
        if not isinstance(row, int):
            print "TypeError:{0:s}".format(type(row))
            return False

        if row >= self.rowCount() or row < 0:
            print "Row range error, max row: {0:d}".format(self.rowCount())
            return False

        return True

    def __checkColumn(self, column):
        if not isinstance(column, int):
            print "TypeError:{0:s}".format(type(column))
            return False

        if column >= self.columnCount() or column < 0:
            print "Column range error, max column: {0:d}".format(self.columnCount())
            return False

        return True

    @Slot(bool)
    def hideHeaders(self, hide):
        self.hideRowHeader(hide)
        self.hideColumnHeader(hide)

    @Slot(bool)
    def hideRowHeader(self, hide):
        self.verticalHeader().setVisible(not hide)

    @Slot(bool)
    def hideColumnHeader(self, hide):
        self.horizontalHeader().setVisible(not hide)

    def frozenItem(self, row, column, frozen):
        """Frozen or unfroze a item

        :param row: item row number
        :param column: item column number
        :param frozen: True -> Frozen, False -> Unfrozen
        :return: True / False
        """
        if not self.__checkRow(row) or not self.__checkColumn(column):
            return False

        flags = QTableWidgetItem("").flags()
        flags = flags & ~Qt.ItemIsEditable if frozen else flags

        item = self.takeItem(row, column)
        item.setFlags(flags)
        self.setItem(row, column, item)
        return True

    def frozenRow(self, row, frozen):
        """Frozen or unfrozen a row item

        :param row: row number start from 0
        :param frozen: True -> Frozen, False -> Unfrozen
        :return: True / False
        """
        for column in range(self.columnCount()):
            if not self.frozenItem(row, column, frozen):
                return False

        return True

    def frozenColumn(self, column, frozen):
        """Frozen or unfrozen a column item

        :param column: column number
        :param frozen: True -> Frozen, False -> Unfrozen
        :return: True / False
        """
        for row in range(self.rowCount()):
            if not self.frozenItem(row, column, frozen):
                return False

        return True

    def swapRow(self, src, dst):
        """Swap src and dst row data

        :param src: src row number
        :param dst: dst row number
        :return:
        """
        if not self.__checkRow(src):
            print "Source row number[{0:d}] out of range".format(src)
            return

        if not self.__checkRow(dst):
            print "Destination row number[0:d] out of range".format(dst)
            return

        for index in range(self.columnCount()):
            src_item = self.takeItem(src, index)
            dst_item = self.takeItem(dst, index)
            self.setItem(src, index, dst_item)
            self.setItem(dst, index, src_item)

        # Select dst row
        self.selectRow(dst)

    def swapColumn(self, src, dst):
        """Swap src and dst column data

        :param src: source column number
        :param dst: destination column number
        :return:
        """

        if not self.__checkColumn(src):
            print "Source column number[{0:d}] out of range".format(src)
            return

        if not self.__checkColumn(dst):
            print "Destination column number[0:d] out of range".format(dst)
            return

        for index in range(self.rowCount()):
            src_item = self.takeItem(index, src)
            dst_item = self.takeItem(index, dst)
            self.setItem(index, src, dst_item)
            self.setItem(index, dst, src_item)

        # Select destination column
        self.selectColumn(dst)

    @Slot()
    def rowMoveUp(self):
        row = self.currentRow()
        if row == 0: return
        self.swapRow(row, row - 1)

    @Slot()
    def rowMoveDown(self):
        row = self.currentRow()
        if row == self.rowCount() - 1: return
        self.swapRow(row, row + 1)

    @Slot()
    def columnMoveLeft(self):
        column = self.currentColumn()
        if column == 0: return
        self.swapColumn(column, column - 1)

    @Slot()
    def columnMoveRight(self):
        column = self.currentColumn()
        if column == self.columnCount() - 1: return
        self.swapColumn(column, column + 1)

    def addRow(self, data):
        if not hasattr(data, "__iter__"):
            print "TypeError: item should a iterable"
            return False

        if len(data) > self.columnCount():
            print "Item length too much"
            return False

        # Increase row count
        current = self.rowCount()
        self.setRowCount(current + 1)

        # Add data to row
        for idx, item_data in enumerate(data):
            try:

                item = QTableWidgetItem(self.tr(str(item_data)))
                self.setItem(current, idx, item)

            except ValueError, e:

                print "TableWidget addItem error: {0:s}".format(e)
                continue

        # Select current item
        self.selectRow(current)

    def setRowHeader(self, data):
        if not hasattr(data, "__iter__"):
            print "TypeError: item should a iterable"
            return False

        if len(data) > self.rowCount():
            print "Item length too much"
            return False

        for row, text in enumerate(data):
            if not isinstance(text, str): continue
            self.takeVerticalHeaderItem(row)
            header = QTableWidgetItem(self.tr(text))
            self.setVerticalHeaderItem(row, header)

        self.hideRowHeader(False)

    def setColumnHeader(self, data):
        if not hasattr(data, "__iter__"):
            print "TypeError: item should a iterable"
            return False

        if len(data) > self.columnCount():
            print "Item length too much"
            return False

        for column, text in enumerate(data):
            if not isinstance(text, str): continue
            self.takeHorizontalHeaderItem(column)
            header = QTableWidgetItem(self.tr(text))
            self.setHorizontalHeaderItem(column, header)

        self.hideColumnHeader(False)

    def setRowAlignment(self, row, alignment):
        if not isinstance(alignment, Qt.AlignmentFlag):
            print "TypeError:{0:s}".format(type(alignment))
            return False

        if not self.__checkRow(row):
            return False

        for column in range(self.columnCount()):
            item = self.takeItem(row, column)
            item.setTextAlignment(alignment)
            self.setItem(row, column, item)

        return True

    def setColumnAlignment(self, column, alignment):
        if not isinstance(alignment, Qt.AlignmentFlag):
            print "TypeError:{0:s}".format(type(alignment))
            return False

        if not self.__checkColumn(column):
            return False

        for row in range(self.rowCount()):
            item = self.takeItem(row, column)
            item.setTextAlignment(alignment)
            self.setItem(row, column, item)

        return True

    def setTableAlignment(self, alignment):
        for row in range(self.rowCount()):
            if not self.setRowAlignment(row, alignment):
                return False

        return True

    @Slot()
    def setRowSelectMode(self):
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

    @Slot()
    def setItemSelectMode(self):
        self.setSelectionBehavior(QAbstractItemView.SelectItems)

    @Slot()
    def setColumnSelectMode(self):
        self.setSelectionBehavior(QAbstractItemView.SelectColumns)

    def getRowData(self, row):
        if not self.__checkRow(row):
            return []

        data = list()
        for column in range(self.columnCount()):
            item = self.item(row, column)
            data.append(item.text())

        return data

    def getColumnData(self, column):
        if not self.__checkColumn(column):
            return []

        data = list()
        for row in range(self.rowCount()):
            item = self.item(row, column)
            data.append(item.text())

        return data

    def getTableData(self):
        data = list()
        for row in range(self.rowCount()):
            data.append(self.getRowData(row))

        return data


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
