# -*- coding: utf-8 -*-
import sys
from PySide.QtGui import *
from PySide.QtCore import *
from ..gui.checkbox import *
from ..core.datatype import *
from ..gui.widget import BasicWidget, TableWidget


class CheckboxDemoWidget(BasicWidget):
    TOTAL_COLUMN, TOTAL_ROW, CHECKBOX_COLUMN = 6, 5, 5

    def __init__(self, parent=None):
        super(CheckboxDemoWidget, self).__init__(parent)

    def _initUi(self):
        self.def_style = CheckBoxStyleSheet.default()
        style = DynamicObject(background=(240, 240, 240), font=("宋体", 9))
        self.ui_data = QTextEdit(self)
        self.ui_table = TableWidget(self.TOTAL_COLUMN)
        self.ui_factor = QDoubleSpinBox(self)
        self.ui_get_data = QPushButton("Get Data")
        self.ui_font_color = QPushButton(self.tr("Box Color"))
        self.ui_fill_color = QPushButton(self.tr("Fill Color"))
        self.ui_hover_color = QPushButton(self.tr("Hover Color"))
        self.ui_bg_color = QPushButton(self.tr("Background Color"))
        self.ui_fg_color = QPushButton(self.tr("Foreground Color"))
        self.ui_frozen = CheckBox(self.tr("Frozen"), stylesheet=style.dict, parent=self)
        self.ui_with_box = CheckBox(self.tr("With box"), stylesheet=style.dict, parent=self)

        tools_layout = QHBoxLayout()
        for x in (self.ui_frozen, self.ui_with_box, QLabel(self.tr("Size Factor")), self.ui_factor,
                  self.ui_fill_color, self.ui_hover_color, self.ui_bg_color, self.ui_fg_color):
            tools_layout.addWidget(x)

        layout = QVBoxLayout()
        layout.addWidget(self.ui_table)
        layout.addLayout(tools_layout)
        layout.addWidget(self.ui_get_data)
        layout.addWidget(self.ui_data)
        self.setLayout(layout)
        self.setWindowTitle(self.tr("Checkbox Demo"))

    def _initData(self):
        for row in range(self.TOTAL_ROW):
            data = [str(row)] * self.ui_table.columnCount()
            data[-1] = str(row % 2 == 0)
            data[-2] = str(row % 2 == 1)
            self.ui_table.addRow(data)

        self.ui_factor.setSingleStep(0.1)
        self.ui_factor.setValue(self.def_style.sizeFactor)
        self.ui_with_box.setChecked(self.def_style.withBox)
        self.ui_table.setItemDelegateForColumn(self.CHECKBOX_COLUMN, CheckBoxDelegate(parent=self))

    def _initStyle(self):
        self.ui_table.setAutoWidth()
        self.ui_table.setAutoHeight(True)
        self.ui_table.setItemSelectMode()
        self.ui_table.setTableAlignment(Qt.AlignCenter)
        [self.ui_table.openPersistentEditor(self.ui_table.item(row, self.CHECKBOX_COLUMN))
         for row in range(self.ui_table.rowCount())]

    def _initSignalAndSlots(self):
        self.ui_with_box.stateChanged.connect(
            lambda x: self.slotCheckboxStyleChanged(DynamicObject(withBox=x == Qt.Checked))
        )

        self.ui_frozen.stateChanged.connect(
            lambda x: self.ui_table.frozenTable(x == Qt.Checked)
        )

        self.ui_factor.valueChanged.connect(
            lambda x: self.slotCheckboxStyleChanged(DynamicObject(sizeFactor=x))
        )

        self.ui_get_data.clicked.connect(
            lambda: self.ui_data.setText("{}".format(self.ui_table.getTableData()))
        )

        self.ui_fill_color.clicked.connect(self.slotColorChanged)
        self.ui_hover_color.clicked.connect(self.slotColorChanged)
        self.ui_bg_color.clicked.connect(self.slotColorChanged)
        self.ui_fg_color.clicked.connect(self.slotColorChanged)

    def slotColorChanged(self):
        sender = self.sender()
        origin_color, keyword = {
            self.ui_fg_color: (self.def_style.foregroundColor(), "foreground"),
            self.ui_bg_color: (self.def_style.backgroundColor(), "background"),
            self.ui_fill_color: (self.def_style.getFilledColor(), "fillColor"),
            self.ui_hover_color: (self.def_style.getHoverColor(), "hoverColor")
        }.get(sender, (None, ""))

        if not origin_color or not keyword:
            return

        color = QColorDialog.getColor(origin_color, self, "Get {} color".format(keyword))
        if not isinstance(color, QColor):
            return

        self.slotCheckboxStyleChanged({keyword: (color.red(), color.green(), color.blue())})

    def slotCheckboxStyleChanged(self, stylesheet):
        try:
            self.def_style.update(stylesheet)
        except (DynamicObjectEncodeError, TypeError) as e:
            print("{}: {}".format(stylesheet, e))
            return

        for row in range(self.ui_table.rowCount()):
            check_box = self.ui_table.indexWidget(self.ui_table.model().index(row, self.CHECKBOX_COLUMN))
            if isinstance(check_box, CheckBox):
                check_box.setStyleSheet(self.def_style)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    QTextCodec.setCodecForTr(QTextCodec.codecForName("UTF-8"))
    widget = CheckboxDemoWidget()
    widget.show()
    sys.exit(app.exec_())
