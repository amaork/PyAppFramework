# -*- coding: utf-8 -*-
import sys
sys.path.append("../../../")
from PyAppFramework.gui.widget import *
from PySide.QtGui import *
from PySide.QtCore import *


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

        self.rgbWidget = RgbWidget()
        self.rgbWidget.setHidden(True)
        self.rgbLabel = QLabel()
        self.rgbLabel.setFrameStyle(frameStyle)

        self.listButton = QPushButton("Get list")

        self.colorButton = QPushButton("Get color")
        self.colorButton.setToolTip("Double click exit")

        self.cursorButton = QPushButton("Get cursor")
        self.cursorButton.setToolTip("Double click exit")

        self.rgbButton = QPushButton("Get rgb state")

        self.rgbButton.clicked.connect(self.showWidget)
        self.listButton.clicked.connect(self.showWidget)
        self.colorButton.clicked.connect(self.showWidget)
        self.cursorButton.clicked.connect(self.showWidget)
        self.rgbWidget.rgbChanged.connect(self.setRGB)
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
        self.layout.addWidget(self.rgbButton, 3, 0)
        self.layout.addWidget(self.rgbLabel, 3, 1)

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
        elif self.sender() == self.rgbButton:
            self.rgbWidget.setHidden(False)

    def setRGB(self, r, g, b):
        self.rgbLabel.setText("R:{0:b} G:{1:b} B{2:b}".format(r, g, b))

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
