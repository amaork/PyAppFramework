# -*- coding: utf-8 -*-
import os
import sys
import datetime
from PySide.QtGui import *
from PySide.QtCore import *

from ..gui.widget import *
from ..misc.settings import *
from .images import ImagesPath
from ..gui.container import ComponentManager
from ..gui.widget import SerialPortSettingWidget


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
        self.listWidget.setItems(list(zip(["Item{0:d}".format(i) for i in range(10)], list(range(10)))))

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
        self.listData.setText("{}".format(list(zip(self.listWidget.getItems(), self.listWidget.getItemsData()))))

    def slotGetMarkItem(self):
        self.listData.setText("{}".format(self.listWidget.getMarkedItem()))


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

        self.set_row_select_mode = QPushButton("Row select mode")
        self.set_column_select_mode = QPushButton("Column select mode")
        self.set_item_select_mode = QPushButton("Item select mode")

        self.get_table_data = QPushButton("Get table data")
        self.get_table_data.clicked.connect(self.__slotGetTableData)
        self.get_row_data = QPushButton("Get row data")
        self.get_row_data.clicked.connect(self.__slotGetRowData)
        self.get_column_data = QPushButton("Get column data")
        self.get_column_data.clicked.connect(self.__slotGetColumnData)

        self.set_column_as_int = QPushButton("Set column as int")
        self.set_column_as_int.clicked.connect(self.__slotSetAsIntType)
        self.set_column_as_double = QPushButton("Set column as double")
        self.set_column_as_double.clicked.connect(self.__slotSetAsDoubleType)

        self.set_column_as_bool = QPushButton("Set column as bool")
        self.set_column_as_bool.clicked.connect(self.__slotSetAsBoolType)
        self.set_column_as_list = QPushButton("Set column as list")
        self.set_column_as_list.clicked.connect(self.__slotSetAsListType)

        self.set_column_as_date = QPushButton("Set column as datatime")
        self.set_column_as_date.clicked.connect(self.__slotSetAsTimeType)

        self.set_column_as_state = QPushButton("Set column as ColorState")
        self.set_column_as_state.clicked.connect(self.__slotSetAsColorType)

        self.set_column_as_progress = QPushButton("Set column as Progress")
        self.set_column_as_progress.clicked.connect(self.__slotSetAsProgressType)

        self.hide_row_header = QPushButton("Hide Row Header")
        self.hide_row_header.setCheckable(True)
        self.hide_column_header = QPushButton("Hide Column Header")
        self.hide_column_header.setCheckable(True)

        self.btn_groups = {

            "New": (
                self.new, self.new_row
            ),

            "Get": (

                self.get_row_data, self.get_column_data, self.get_table_data
            ),

            "Mode": (
                self.set_row_select_mode, self.set_column_select_mode, self.set_item_select_mode
            ),

            "Move": (
                self.row_move_up, self.row_move_down, self.column_move_left, self.column_move_right
            ),

            "Frozen": (
                self.frozen_row, self.unfrozen_row, self.frozen_column, self.unfrozen_column
            ),

            "Header": (

                self.set_row_header, self.set_column_header, self.hide_row_header, self.hide_column_header
            ),

            "Alignment": (
                self.set_row_alignment, self.set_column_alignment,
                self.set_center_alignment, self.set_justify_alignment
            ),

            "Data Type": (

                self.set_column_as_int, self.set_column_as_double,
                self.set_column_as_bool, self.set_column_as_list
            ),

            "Data Type2": (

                self.set_column_as_date, self.set_column_as_state, self.set_column_as_progress
            )
        }

        self.table_layout = QVBoxLayout()
        self.data = QTextEdit()
        self.data.setMaximumHeight(100)
        self.data.setHidden(True)
        self.button_layout = QGridLayout()

        for row, btn_group in enumerate(self.btn_groups.items()):
            self.button_layout.addWidget(QLabel(btn_group[0]), row, 0)
            for column, btn in enumerate(btn_group[1]):
                btn.setDisabled(True)
                self.button_layout.addWidget(btn, row, column + 1)

        self.new.setEnabled(True)
        layout = QVBoxLayout()
        layout.addLayout(self.table_layout)
        layout.addLayout(self.button_layout)
        self.setLayout(layout)
        self.setWindowTitle("TableWidget Test")
        self.ui_manager = ComponentManager(layout)

    def __get_text(self, title, lable):
        text, ok = QInputDialog.getText(self, title, lable, QLineEdit.Normal, QDir.home().dirName())
        return text if ok else "Header"

    def __get_number(self, title, label, default, min_value, max_value):
        i, ok = QInputDialog.getInteger(self, title, label, default, min_value, max_value, 1)
        return i

    def __slotCreateTable(self):
        max_column = self.__get_number("Please enter max column number", "Column count", 8, 1, 100)
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
        for btn in self.ui_manager.getByType(QPushButton):
            btn.setEnabled(True)
        self.new.setDisabled(True)

    def __slotNewRow(self):
        count = self.table.rowCount()
        column = self.table.columnCount()
        self.table.addRow(list(range(count * column, (count + 1) * column)))

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
            headers.append("{} {}".format(text, index))

        self.table.setRowHeader(headers)

    def __slotSetColumnHeader(self):
        text = self.__get_text("Please enter column header:", "Column header:")
        headers = list()
        for index in range(self.table.columnCount()):
            headers.append("{} {}".format(text, index))

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
        data = [d for d in self.table.getRowData(self.table.currentRow())]
        self.data.setText("{}".format(data))

    def __slotGetColumnData(self):
        data = [d for d in self.table.getColumnData(self.table.currentColumn())]
        self.data.setText("{}".format(data))

    def __slotGetTableData(self):
        data = self.table.getTableData()
        self.data.setText("")
        self.data.setText("{}".format(data))

    def __slotSetAsIntType(self):
        print(self.table.setColumnDataFilter(self.table.currentColumn(), (1, 100)))

    def __slotSetAsDoubleType(self):
        print(self.table.setColumnDataFilter(self.table.currentColumn(), (0.1, 100.0)))

    def __slotSetAsBoolType(self):
        print(self.table.setColumnDataFilter(self.table.currentColumn(), (False, "信号")))

    def __slotSetAsListType(self):
        print(self.table.setColumnDataFilter(self.table.currentColumn(), ["VESA", "JEIDA", "VIMM"]))

    def __slotSetAsTimeType(self):
        filters = (datetime.datetime.now(), "%Y-%m-%d %H:%M:%S", "yyyy-MM-dd hh:mm:ss")
        print(self.table.setColumnDataFilter(self.table.currentColumn(), filters))

    def __slotSetAsColorType(self):
        print(self.table.setColumnDataFilter(self.table.currentColumn(), ["成功", QColor(Qt.green)]))

    def __slotSetAsProgressType(self):
        print(self.table.setColumnDataFilter(self.table.currentColumn(), [QProgressBar(), True, 10]))


class SerialSettingWidgetTest(QWidget):
    def __init__(self, parent=None):
        super(SerialSettingWidgetTest, self).__init__(parent)
        self.__text = QTextEdit()
        self.__setting = SerialPortSettingWidget()
        get_setting = QPushButton(self.tr("获取串口设置"))
        get_setting.clicked.connect(self.slotGetSetting)

        layout = QVBoxLayout()
        layout.addWidget(self.__setting)
        layout.addWidget(get_setting)
        layout.addWidget(self.__text)

        self.setLayout(layout)
        self.setWindowTitle(self.tr("串口设置对话框"))

    def slotGetSetting(self):
        self.__text.setText("{}".format(self.__setting.getSetting()))


class JsonSettingWidgetTest(QWidget):
    def __init__(self, parent=None):
        super(JsonSettingWidgetTest, self).__init__(parent)

        layout = QVBoxLayout()
        self.widget = JsonSettingWidget(UiInputSetting.getDemoSettings())
        self.widget.settingChanged.connect(self.slotShowData)
        self.ui_button = QPushButton(self.tr("Get settings"))
        self.ui_button.clicked.connect(self.slotShowData)
        self.ui_data = QTextEdit()
        layout.addWidget(self.widget)
        layout.addWidget(self.ui_button)
        layout.addWidget(self.ui_data)
        self.setLayout(layout)

    def slotShowData(self):
        if self.sender() == self.ui_button:
            self.ui_data.setText("{}".format(self.widget.getSettings()))
        else:
            self.ui_data.setText("{}".format(self.widget.getData()))


class MultiJsonSetting(JsonSettings):
    _properties = {'int', 'float', 'bool', 'text', 'select', 'readonly_text', 'layout'}

    @classmethod
    def default(cls):
        return MultiJsonSetting(
            bool=UiCheckBoxInput("布尔型数据"),
            text=UiTextInput("文本型数据", 16, "123"),
            file=UiFileInput("文件", ("*.jpg", "*.bmp")),
            int=UiIntegerInput("整型数据", 1, 100, step=10),
            float=UiDoubleInput("浮点型数据", 3.3, 24.0, step=0.5),
            select=UiSelectInput("选择型数据", ["A", "B", "C"], "A"),
            readonly_text=UiTextInput("只读文本型数据", 16, "ABCD", readonly=True),
            layout=UiLayout(name="多项 Json 设置",
                            layout=['bool', 'text', 'int', 'float', 'select', 'readonly_text', 'file'])
        )


class MultiJsonSettingsWidgetTest(QWidget):
    def __init__(self, parent=None):
        super(MultiJsonSettingsWidgetTest, self).__init__(parent)

        data = [

            (False, "123", 10, 4.5, "A", "ABCDEF_1", ""),
            (True, "1234", 20, 5.5, "A", "ABCDEF_12", ""),
            (False, "12345", 30, 6.5, "B", "ABCDEF_123", ""),
            (True, "123456", 40, 7.5, "B", "ABCDEF_1234", ""),
            (False, "1234567", 50, 8.5, "C", "ABCDEF_12345", ""),
            (True, "12345678", 60, 9.5, "C", "ABCDEF_123456", ""),
        ]
        layout = QVBoxLayout()
        self.widget = MultiJsonSettingsWidget(MultiJsonSetting.default(), data)

        self.widget.settingChanged.connect(self.slotShowData)
        self.ui_get = QPushButton(self.tr("Get settings"))
        self.ui_get.clicked.connect(self.slotShowData)
        self.ui_reset = QPushButton(self.tr("Reset data"))
        self.ui_reset.clicked.connect(self.slotResetData)
        self.ui_data = QTextEdit()
        layout.addWidget(self.widget)
        layout.addWidget(self.ui_get)
        layout.addWidget(self.ui_reset)
        layout.addWidget(self.ui_data)
        self.setLayout(layout)

    def slotShowData(self):
        self.ui_data.setText("{}".format(self.widget.getData()))

    def slotResetData(self):
        self.widget.resetDefaultData()


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

        self.serialWidget = SerialSettingWidgetTest()
        self.serialWidget.setHidden(True)
        self.serialLabel = QLabel()
        self.serialLabel.setFrameStyle(frameStyle)
        self.serialButton = QPushButton("Get serial")
        self.serialButton.clicked.connect(self.showWidget)

        self.settingWidget = JsonSettingWidgetTest()
        self.settingWidget.setHidden(True)
        self.settingLabel = QLabel()
        self.settingLabel.setFrameStyle(frameStyle)
        self.settingButton = QPushButton("Get setting")
        self.settingButton.clicked.connect(self.showWidget)

        self.multiJsonSettingWidget = MultiJsonSettingsWidgetTest()
        self.multiJsonSettingWidget.setHidden(True)
        self.multiJsonSettingLabel = QLabel()
        self.multiJsonSettingLabel.setFrameStyle(frameStyle)
        self.multiJsonSettingButton = QPushButton("Get setting")
        self.multiJsonSettingButton.clicked.connect(self.showWidget)

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
        self.layout.addWidget(self.serialButton, 9, 0)
        self.layout.addWidget(self.serialLabel, 9, 1)
        self.layout.addWidget(self.settingButton, 10, 0)
        self.layout.addWidget(self.settingLabel, 10, 1)
        self.layout.addWidget(self.multiJsonSettingButton, 11, 0)
        self.layout.addWidget(self.multiJsonSettingLabel, 11, 1)

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
        elif self.sender() == self.serialButton:
            self.serialWidget.setHidden(False)
        elif self.sender() == self.settingButton:
            self.settingWidget.setHidden(False)
        elif self.sender() == self.multiJsonSettingButton:
            self.multiJsonSettingWidget.setHidden(False)

    def showImage(self):
        if self.sender() == self.imageFsButton:
            file, _ = QFileDialog.getOpenFileName(self, "Select image", ImagesPath, "All Files (*.jpg)")
            self.drawFromFs.emit(file)
            self.imageWidget.setHidden(False)
        elif self.sender() == self.imageMemButton:
            file, _ = QFileDialog.getOpenFileName(self, "Select image", ImagesPath, "All Files (*.jpg)")
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
