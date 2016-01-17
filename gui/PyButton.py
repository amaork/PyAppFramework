# -*- coding: utf-8 -*-
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtNetwork import *
import PyQt4.Qt
import ConfigParser
import math
import sys
import os

try:
    _fromUtf8 = QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s
    
    
class BaseButton(QPushButton):
    def __init__(self, width, height, turnOn = False, shortCut = "", parent=None):
        QWidget.__init__(self,parent)
        
        self.setCheckable(True)
        self.setChecked(turnOn)                
        self.setMinimumSize(width, height)
        self.setShortcut(QKeySequence(self.tr(shortCut)))
        
    def turnOn(self):
        self.setChecked(True)
        
    def turnOff(self):
        self.setChecked(False)

class TextButton(BaseButton):
    def __init__(self, width, height, turnOn = False, text = ("", ""), shortCut = "", parent=None):
        QWidget.__init__(self,parent)
        
        super(TextButton, self).__init__(width, height, turnOn, shortCut)
        
        self.text = text
        self.drawColor = (Qt.red, Qt.green)
        self.textColor = (Qt.white, Qt.black)
        self.textLength = max(len(self.text[0]), len(self.text[1]), 1)  
        
    def drawText(self, painter, rect):
        painter.setPen(self.textColor[self.isChecked()]);
        painter.setFont(QFont("Arial", min(rect.width() / self.textLength / 0.618, rect.height() * 0.618)));
        painter.drawText(rect, Qt.AlignCenter, self.tr(self.text[self.isChecked()]))
        
    def getBrush(self):
        return QBrush(self.drawColor[self.isChecked()], Qt.SolidPattern)
    
class RectButton(TextButton):
    def __init__(self, width, height, turnOn = False, text = ("", ""), shortCut = "", parent=None):
        QWidget.__init__(self,parent)
        
        super(RectButton, self).__init__(width, height, turnOn, text, shortCut)
        
    def paintEvent(self, ev):
        painter = QPainter(self)
        rect = self.rect()
        
        #Draw backgroubd
        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(self.getBrush())
        painter.drawRect(rect)
           
        #Draw text
        self.drawText(painter, rect)
    
class RoundButton(TextButton):
    def __init__(self, dia, turnOn = False, text = ("", ""), shortCut = "", parent=None):
        QWidget.__init__(self,parent)
        
        super(RoundButton, self).__init__(dia, dia, turnOn, text, shortCut)
        
    def paintEvent(self, ev):
        painter = QPainter(self)
        rect = self.rect()
        
        #Draw backgroubd
        painter.setPen(QPen(Qt.NoPen))
        painter.setBrush(self.getBrush())
        width = min(self.size().width(), self.size().height())
        rect.setWidth(width)
        rect.setHeight(width)
        painter.drawEllipse(rect)
           
        #Draw text
        self.drawText(painter, rect)

class IconButton(BaseButton):
    
    __supportFormat = ["jpg", "jpeg", "png", "bmp"]
    
    def __init__(self, width, height, turnOn = False, icon = ("", ""), shortCut = "", parent=None):
        QWidget.__init__(self,parent)
        
        super(IconButton, self).__init__(width, height, turnOn, shortCut)

        self.icon = icon
        self.width = width
        self.height = height
        self.iconData = []
        self.iconFormat = [fname.split(".")[-1] for fname in icon]
        
        #Load icon data to memory
        if isinstance(icon,tuple) and len(icon) == 2:
            
            for i in range(len(icon)):
                if os.path.isfile(icon[i]) and self.iconFormat[i] in self.__supportFormat:
                    with open(icon[i], "rb") as fp:
                        data = fp.read(os.path.getsize(icon[i]))
                        self.iconData.append(data)
                
        
    def paintEvent(self, ev):
        pixmap = QPixmap()
        painter = QPainter(self)
        rect = self.rect()
        idx = self.isChecked()
        
        if len(self.iconData) == 2 and len(self.iconData[idx]):
            pixmap.loadFromData(self.iconData[idx], self.iconFormat[idx])
            painter.drawPixmap(self.rect(), pixmap)
            
            


app = QApplication(sys.argv)
QTextCodec.setCodecForTr(QTextCodec.codecForName("UTF-8"))
demo = RoundButton(256, False, ("打开","关闭"))
demo.show()
app.exec_()