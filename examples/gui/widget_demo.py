# -*- coding: utf-8 -*-
import os
import sys
sys.path.append("../../../")
from PyAppFramework.gui.widget import *
from PySide.QtGui import *
from PySide.QtCore import *


class ListDemoWidget(QWidget):
    def __init__(self, parent=None):
        super(ListDemoWidget, self).__init__(parent)

        # Elements
        self.fontButton = QPushButton("Font")
        self.addButton = QPushButton("Add item")
        self.getButton = QPushButton("Get data")
        self.getMarkButton = QPushButton("Get mark item")
        self.listData = QTextEdit()
        self.listWidget = ListWidget()
        self.listWidget.setItems(zip(["Item{0:d}".format(i) for i in range(10)], range(10)))

        # Signal and slots
        self.addButton.clicked.connect(self.slotAddItem)
        self.fontButton.clicked.connect(self.slotGetFont)
        self.getButton.clicked.connect(self.slotGetData)
        self.getMarkButton.clicked.connect(self.slotGetMarkItem)
        self.listWidget.itemDoubleClicked.connect(self.listWidget.markItem)

        # Layout
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.fontButton)
        button_layout.addWidget(self.addButton)
        button_layout.addWidget(self.getButton)
        button_layout.addWidget(self.getMarkButton)

        layout = QVBoxLayout()
        layout.addWidget(self.listWidget)
        layout.addLayout(button_layout)
        layout.addWidget(self.listData)

        self.setLayout(layout)
        self.setWindowTitle("ListWidget Dialog Demo")

    def slotGetFont(self):
        font, ok = QFontDialog.getFont(self)
        if ok:
            self.listWidget.setFont(font)

    def slotAddItem(self):
        text, ok = QInputDialog.getText(self, "Please enter items text", "Text:",
                                        QLineEdit.Normal, QDir.home().dirName())

        if ok:
            self.listWidget.addItem(text)

    def slotGetData(self):
        self.listData.setText("{0:s}".format(zip(self.listWidget.getItems(), self.listWidget.getItemsData())))

    def slotGetMarkItem(self):
        self.listData.setText("{0:s}".format(self.listWidget.getMarkItem()))

class TableWidgetTest(QWidget):
    def __init__(self, parent=None):
        super(TableWidgetTest, self).__init__(parent)

        # Create
        self.new = QPushButton("Create")
        self.new.clicked.connect(self.__slotCreateTable)
        self.new_row = QPushButton("Create Row")
        self.new_row.clicked.connect(self.__slotNewRow)

        # Frozen/unfrozen row
        self.frozen_row = QPushButton("Frozen Row")
        self.frozen_row.clicked.connect(self.__slotFrozenRow)
        self.unfrozen_row = QPushButton("Unfrozen Row")
        self.unfrozen_row.clicked.connect(self.__slotUnfrozenRow)

        # Frozen/unfrozen column
        self.frozen_column = QPushButton("Frozen Column")
        self.frozen_column.clicked.connect(self.__slotFrozenColumn)
        self.unfrozen_column = QPushButton("Unfrozen Column")
        self.unfrozen_column.clicked.connect(self.__slotUnfrozenColumn)

        # Item move
        self.row_move_up = QPushButton("Row move up")
        self.row_move_down = QPushButton("Row move down")

        self.column_move_left = QPushButton("Column move left")
        self.column_move_right = QPushButton("Column move right")

        self.set_row_header = QPushButton("Set row header")
        self.set_row_header.clicked.connect(self.__slotSetRowHeader)
        self.set_column_header = QPushButton("Set column header")
        self.set_column_header.clicked.connect(self.__slotSetColumnHeader)

        self.set_row_alignment = QPushButton("Set row alignment")
        self.set_row_alignment.clicked.connect(self.__slotSetRowAlignment)
        self.set_column_alignment = QPushButton("Set column alignment")
        self.set_column_alignment.clicked.connect(self.__slotSetColumnAlignment)

        self.set_center_alignment = QPushButton("Set AlignHCenter")
        self.set_center_alignment.clicked.connect(self.__slotSetTableAlignHCenter)
        self.set_justify_alignment = QPushButton("Set AlignJustify")
        self.set_justify_alignment.clicked.connect(self.__slotSetTableAlignJustify)

        self.set_row_select_mode = QPushButton("Set row select mode")
        self.set_column_select_mode = QPushButton("Set column select mode")
        self.set_item_select_mode = QPushButton("Set item select mode")

        self.get_table_data = QPushButton("Get table data")
        self.get_table_data.clicked.connect(self.__slotGetTableData)
        self.get_row_data = QPushButton("Get row data")
        self.get_row_data.clicked.connect(self.__slotGetRowData)
        self.get_column_data = QPushButton("Get column data")
        self.get_column_data.clicked.connect(self.__slotGetColumnData)

        self.set_row_as_int = QPushButton("Set row as int")
        self.set_row_as_int.clicked.connect(self.__slotSetAsIntType)
        self.set_row_as_double = QPushButton("Set row as double")
        self.set_row_as_double.clicked.connect(self.__slotSetAsDoubleType)

        self.set_row_as_bool = QPushButton("Set row as bool")
        self.set_row_as_bool.clicked.connect(self.__slotSetAsBoolType)
        self.set_row_as_list = QPushButton("Set row as list")
        self.set_row_as_list.clicked.connect(self.__slotSetAsListType)

        self.hide_row_header = QPushButton("Hide Row Header")
        self.hide_row_header.setCheckable(True)
        self.hide_column_header = QPushButton("Hide Column Header")
        self.hide_column_header.setCheckable(True)


        self.all_btn = (self.new, self.new_row,
                        self.frozen_row, self.unfrozen_row,
                        self.frozen_column, self.unfrozen_column,
                        self.row_move_up, self.row_move_down,
                        self.column_move_left, self.column_move_right,
                        self.set_row_header, self.set_column_header,
                        self.set_row_alignment, self.set_column_alignment,
                        self.set_center_alignment, self.set_justify_alignment,
                        self.set_row_select_mode, self.set_column_select_mode,
                        self.set_item_select_mode, self.get_table_data,
                        self.set_row_as_int, self.set_row_as_double,
                        self.set_row_as_bool, self.set_row_as_list,
                        self.get_row_data, self.get_column_data,
                        self.hide_row_header, self.hide_column_header)

        self.table_layout = QVBoxLayout()
        self.data = QTextEdit()
        self.data.setMaximumHeight(100)
        self.data.setHidden(True)
        self.button_layout = QHBoxLayout()

        for idx in range(0, len(self.all_btn), 2):
            layout = QVBoxLayout()
            for i in range(2):
                btn = self.all_btn[idx + i]
                btn.setDisabled(True)
                layout.addWidget(btn)
            self.button_layout.addLayout(layout)

        self.new.setEnabled(True)

        layout = QVBoxLayout()
        layout.addLayout(self.table_layout)
        layout.addLayout(self.button_layout)
        self.setLayout(layout)
        self.setWindowTitle("TableWidget Test")

    def __get_text(self, title, lable):
        text, ok = QInputDialog.getText(self, title, lable, QLineEdit.Normal, QDir.home().dirName())
        return text if ok else "Header"

    def __get_number(self, title, label, default, min_value, max_value):
        i, ok = QInputDialog.getInteger(self, title, label, default, min_value, max_value, 1)
        return i

    def __slotCreateTable(self):
        max_column = self.__get_number("Please enter max column number", "Column count", 5, 1, 100)
        self.table = TableWidget(max_column, True)
        self.table_layout.addWidget(self.table)
        self.table_layout.addWidget(self.data)
        self.data.setHidden(False)
        self.row_move_up.clicked.connect(self.table.rowMoveUp)
        self.row_move_down.clicked.connect(self.table.rowMoveDown)
        self.column_move_left.clicked.connect(self.table.columnMoveLeft)
        self.column_move_right.clicked.connect(self.table.columnMoveRight)
        self.hide_row_header.toggled.connect(self.table.hideRowHeader)
        self.hide_column_header.toggled.connect(self.table.hideColumnHeader)
        self.set_row_select_mode.clicked.connect(self.table.setRowSelectMode)
        self.set_item_select_mode.clicked.connect(self.table.setItemSelectMode)
        self.set_column_select_mode.clicked.connect(self.table.setColumnSelectMode)
        for btn in self.all_btn: btn.setEnabled(True)
        self.new.setDisabled(True)


    def __slotNewRow(self):
        count = self.table.rowCount()
        column = self.table.columnCount()
        self.table.addRow(range(count * column, (count + 1) * column))

    def __slotFrozenRow(self):
        row = self.__get_number("Please enter will frozen row number:", "Row",
                                1, 1, self.table.rowCount())
        self.table.frozenRow(row - 1, True)

    def __slotUnfrozenRow(self):
        row = self.__get_number("Please enter will unfrozen row number:", "Row",
                                1, 1, self.table.rowCount())
        self.table.frozenRow(row - 1, False)

    def __slotFrozenColumn(self):
        column = self.__get_number("Please enter will frozen row number:", "Column",
                                1, 1, self.table.columnCount())
        self.table.frozenColumn(column - 1, True)

    def __slotUnfrozenColumn(self):
        column = self.__get_number("Please enter will unfrozen row number:", "Column",
                                1, 1, self.table.columnCount())
        self.table.frozenColumn(column - 1, False)

    def __slotSetRowHeader(self):
        text = self.__get_text("Please enter row header:", "Row header:")
        headers = list()
        for index in range(self.table.rowCount()):
            headers.append("{0:s} {1:d}".format(text.encode("utf-8"), index))

        self.table.setRowHeader(headers)

    def __slotSetColumnHeader(self):
        text = self.__get_text("Please enter column header:", "Column header:")
        headers = list()
        for index in range(self.table.columnCount()):
            headers.append("{0:s} {1:d}".format(text.encode("utf-8"), index))

        self.table.setColumnHeader(headers)

    def __slotSetRowAlignment(self):
        self.table.setRowAlignment(self.table.currentRow(), Qt.AlignCenter)

    def __slotSetColumnAlignment(self):
        self.table.setColumnAlignment(self.table.currentColumn(), Qt.AlignCenter)

    def __slotSetTableAlignHCenter(self):
        self.table.setTableAlignment(Qt.AlignCenter)

    def __slotSetTableAlignJustify(self):
        self.table.setTableAlignment(Qt.AlignJustify)

    def __slotGetRowData(self):
        data = [d.encode("utf-8") for d in self.table.getRowData(self.table.currentRow())]
        self.data.setText("{0:s}".format(data))

    def __slotGetColumnData(self):
        data = [d.encode("utf-8") for d in self.table.getColumnData(self.table.currentColumn())]
        self.data.setText("{0:s}".format(data))

    def __slotGetTableData(self):
        data = self.table.getTableData()
        self.data.setText("")
        for row in data:
            row = [d.encode("utf-8") for d in row]
            self.data.append("{0:s}".format(row))

    def __slotSetAsIntType(self):
        print self.table.setRowDataFilter(self.table.currentRow(), (1, 100))

    def __slotSetAsDoubleType(self):
        print self.table.setRowDataFilter(self.table.currentRow(), (0.1, 100.0))

    def __slotSetAsBoolType(self):
        print self.table.setRowDataFilter(self.table.currentRow(), (False, "信号"))

    def __slotSetAsListType(self):
        print self.table.setRowDataFilter(self.table.currentRow(), ["VESA", "JEIDA", "VIMM"])

class Demo(QMainWindow):
    drawText = Signal(str)
    drawFromFs = Signal(str)
    drawFromMem = Signal(object, object)

    def __init__(self):
        super(Demo, self).__init__()
        frameStyle = QFrame.Sunken | QFrame.Panel

        self.listWidget = ListDemoWidget()
        self.listWidget.setHidden(True)
        self.listLabel = QLabel()
        self.listLabel.setFrameStyle(frameStyle)
        self.listButton = QPushButton("Get list")
        self.listButton.clicked.connect(self.showWidget)

        self.colorWidget = ColorWidget()
        self.colorWidget.setHidden(True)
        self.colorLabel = QLabel()
        self.colorLabel.setFrameStyle(frameStyle)
        self.colorButton = QPushButton("Get color")
        self.colorButton.clicked.connect(self.showWidget)
        self.colorWidget.colorChanged.connect(self.setColor)

        self.cursorWidget = CursorWidget()
        self.cursorWidget.setHidden(True)
        self.cursorLabel = QLabel()
        self.cursorLabel.setFrameStyle(frameStyle)
        self.cursorButton = QPushButton("Get cursor")
        self.cursorButton.clicked.connect(self.showWidget)
        self.cursorWidget.colorChanged.connect(self.setColor)
        self.cursorWidget.cursorChanged.connect(self.setCursor)

        self.rgbWidget = RgbWidget()
        self.rgbWidget.setHidden(True)
        self.rgbLabel = QLabel()
        self.rgbLabel.setFrameStyle(frameStyle)
        self.rgbButton = QPushButton("Get rgb")
        self.rgbButton.clicked.connect(self.showWidget)
        self.rgbWidget.rgbChanged.connect(self.setRgb)

        self.lumWidget = LumWidget()
        self.lumWidget.setHidden(True)
        self.lumLabel = QLabel()
        self.lumLabel.setFrameStyle(frameStyle)
        self.lumButton = QPushButton("Get lum")
        self.lumButton.clicked.connect(self.showWidget)
        self.lumWidget.lumChanged.connect(self.setLum)

        self.imageWidget = ImageWidget(640, 480)
        self.imageWidget.setHidden(True)

        self.imageFsLabel = QLabel()
        self.imageFsLabel.setFrameStyle(frameStyle)
        self.imageFsButton = QPushButton("Show image(fs)")
        self.imageFsButton.clicked.connect(self.showImage)
        self.drawFromFs.connect(self.imageWidget.drawFromFs)

        self.imageMemLabel = QLabel()
        self.imageMemLabel.setFrameStyle(frameStyle)
        self.imageMemButton = QPushButton("Show image(mem)")
        self.imageMemButton.clicked.connect(self.showImage)
        self.drawFromMem.connect(self.imageWidget.drawFromMem)

        self.imageTextLabel = QLabel()
        self.imageTextLabel.setFrameStyle(frameStyle)
        self.imageTextButton = QPushButton("Show image(text)")
        self.imageTextButton.clicked.connect(self.showImage)
        self.drawText.connect(self.imageWidget.drawFromText)

        self.tableWidget = TableWidgetTest()
        self.tableWidget.setHidden(True)
        self.tableLabel = QLabel()
        self.tableLabel.setFrameStyle(frameStyle)
        self.tableButton = QPushButton("Get table")
        self.tableButton.clicked.connect(self.showWidget)

        self.layout = QGridLayout()
        self.layout.addWidget(self.listButton, 0, 0)
        self.layout.addWidget(self.listLabel, 0, 1)
        self.layout.addWidget(self.colorButton, 1, 0)
        self.layout.addWidget(self.colorLabel, 1, 1)
        self.layout.addWidget(self.cursorButton, 2, 0)
        self.layout.addWidget(self.cursorLabel, 2, 1)
        self.layout.addWidget(self.rgbButton, 3, 0)
        self.layout.addWidget(self.rgbLabel, 3, 1)
        self.layout.addWidget(self.lumButton, 4, 0)
        self.layout.addWidget(self.lumLabel, 4, 1)
        self.layout.addWidget(self.imageFsButton, 5, 0)
        self.layout.addWidget(self.imageFsLabel, 5, 1)
        self.layout.addWidget(self.imageMemButton, 6, 0)
        self.layout.addWidget(self.imageMemLabel, 6, 1)
        self.layout.addWidget(self.imageTextButton, 7, 0)
        self.layout.addWidget(self.imageTextLabel, 7, 1)
        self.layout.addWidget(self.tableButton, 8, 0)
        self.layout.addWidget(self.tableLabel, 8, 1)

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
        elif self.sender() == self.lumButton:
            self.lumWidget.setHidden(False)
        elif self.sender() == self.tableButton:
            self.tableWidget.setHidden(False)

    def showImage(self):
        if self.sender() == self.imageFsButton:
            file, _ = QFileDialog.getOpenFileName(self, "Select image", "../images", "All Files (*)")
            self.drawFromFs.emit(file)
            self.imageWidget.setHidden(False)
        elif self.sender() == self.imageMemButton:
            file, _ = QFileDialog.getOpenFileName(self, "Select image", "../images", "All Files (*)")
            if os.path.isfile(file):
                data = ""
                with open(file, "rb") as fp:
                    data = fp.read()

                image = QImageReader(file)
                self.drawFromMem.emit(data, str(image.format()))
                # self.imageWidget.drawFromMem(data, str(image.format()))
                self.imageWidget.setHidden(False)
        elif self.sender() == self.imageTextButton:
            text, ok = QInputDialog.getText(self, "Please enter text", "Text:",
                                        QLineEdit.Normal, QDir.home().dirName())
            if ok:
                self.drawText.emit(text)
                self.imageWidget.setHidden(False)

    def setLum(self, hi, low, mode):
        self.lumLabel.setText("M:{0:d} Hi:{1:d} Low:{2:d}".format(mode, hi, low))

    def setRgb(self, r, g, b):
        self.rgbLabel.setText("R:{0:b} G:{1:b} B:{2:b}".format(r, g, b))

    def setColor(self, r, g, b):
        self.colorLabel.setText("R:{0:d} G:{1:d} B:{2:d}".format(r, g, b))

    def setCursor(self, x, y, colorMode):
        self.cursorLabel.setText("C:{0:x} X:{1:d} Y:{2:d}".format(colorMode, x, y))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    QTextCodec.setCodecForTr(QTextCodec.codecForName("UTF-8"))
    window = Demo()
    window.show()
    sys.exit(app.exec_())
