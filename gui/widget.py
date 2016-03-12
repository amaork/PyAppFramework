#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import types
from PySide.QtCore import *
from PySide.QtGui import *

__all__ = ['updateListWidget', 'updateTableWidget']

ListWidgetDefStyle = {"font": "Times New Roman", "size": 14, "color": QColor(51, 153, 255)}


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


class DemoWidget(QWidget):
    def __init__(self, parent=None):
        super(DemoWidget, self).__init__(parent)

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
            print type(items[0]), type(text)
            items.append(text)
            updateListWidget(self.listWidget, items, text, {"font": self.font, "size": self.size, "color": self.color})

    def slotMarkItem(self):
        print self.getCurrentItem()
        updateListWidget(self.listWidget, self.getListItems(), self.getCurrentItem(),
                         {"font": self.font, "size": self.size, "color": self.color})


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DemoWidget()
    window.show()
    sys.exit(app.exec_())
