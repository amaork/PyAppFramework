# -*- coding: utf-8 -*-
from typing import *
from PySide.QtGui import *
from PySide.QtCore import *
from ..misc.settings import *
from .checkbox import CheckBox
from .widget import JsonSettingWidget
from .container import ComponentManager
from ..core.datatype import DynamicObject
from ..misc.windpi import get_program_scale_factor
__all__ = ['TableView', 'TableViewDelegate']


class TableView(QTableView):
    tableDataChanged = Signal()

    ALL_ACTION = 0x7
    SUPPORT_ACTIONS = (0x1, 0x2, 0x4, 0x8)
    COMM_ACTION, MOVE_ACTION, FROZEN_ACTION, CUSTOM_ACTION = SUPPORT_ACTIONS

    def __init__(self, parent: QWidget or None = None):
        super(TableView, self).__init__(parent)
        self.__autoHeight = False
        self.__contentMenu = QMenu(self)
        self.__contentMenuEnableMask = 0x0
        self.__columnStretchFactor = list()
        self.__scale_x, self.__scale_y = get_program_scale_factor()

        for group, actions in {
            self.COMM_ACTION: [
                (QAction(self.tr("Clear All"), self), lambda: self.model().setRowCount(0)),
            ],

            self.MOVE_ACTION: [
                (QAction(self.tr("Move Up"), self), lambda: self.rowMoveUp()),
                (QAction(self.tr("Move Down"), self), lambda: self.rowMoveDown()),

                (QAction(self.tr("Move Top"), self), lambda: self.rowMoveTop()),
                (QAction(self.tr("Move Bottom"), self), lambda: self.rowMoveBottom()),
            ],
        }.items():
            for action, slot in actions:
                action.triggered.connect(slot)
                action.setProperty("group", group)
                self.__contentMenu.addAction(action)

            self.__contentMenu.addSeparator()

        self.customContextMenuRequested.connect(self.__slotShowContentMenu)

    def __checkModel(self) -> bool:
        return isinstance(self.model(), QAbstractItemModel)

    def __checkRow(self, row: int) -> bool:
        if not isinstance(row, int):
            return False

        if abs(row) >= self.rowCount():
            return False

        return True

    def __checkColumn(self, column: int) -> bool:
        if not isinstance(column, int):
            return False

        if abs(column) >= self.columnCount():
            return False

        return True

    def __slotShowContentMenu(self, pos: QPoint):
        for group in self.SUPPORT_ACTIONS:
            enabled = group & self.__contentMenuEnableMask
            for action in self.__contentMenu.actions():
                if action.property("group") == group:
                    action.setVisible(enabled)

        self.__contentMenu.popup(self.viewport().mapToGlobal(pos))

    def setContentMenuMask(self, mask: int):
        for group in self.SUPPORT_ACTIONS:
            if mask & group:
                self.__contentMenuEnableMask |= group
            else:
                self.__contentMenuEnableMask &= ~group

        if self.__contentMenuEnableMask:
            self.setContextMenuPolicy(Qt.CustomContextMenu)
        else:
            self.setContextMenuPolicy(Qt.DefaultContextMenu)

    def setCustomContentMenu(self, menu: List[QAction]):
        for action in menu:
            if not isinstance(action, QAction):
                continue

            action.setProperty("group", self.CUSTOM_ACTION)
            self.__contentMenu.addAction(action)

        self.__contentMenu.addSeparator()

    def item(self, row: int, column: int) -> QTableWidgetItem or None:
        if not self.__checkRow(row) or not self.__checkColumn(column):
            return None

        return self.model().item(row, column)

    def rowCount(self) -> int:
        return self.model().rowCount() if self.__checkModel() else 0

    def columnCount(self) -> int:
        return self.model().columnCount() if self.__checkModel() else 0

    def hideHeaders(self, hide: bool):
        self.hideRowHeader(hide)
        self.hideColumnHeader(hide)

    def hideRowHeader(self, hide: bool):
        self.verticalHeader().setVisible(not hide)

    def hideColumnHeader(self, hide: bool):
        self.horizontalHeader().setVisible(not hide)

    def getVerticalHeaderHeight(self):
        vertical_header = self.verticalHeader()
        return vertical_header.defaultSectionSize()

    def setVerticalHeaderHeight(self, height: int):
        vertical_header = self.verticalHeader()
        vertical_header.setResizeMode(QHeaderView.Fixed)
        vertical_header.setDefaultSectionSize(height)
        self.setVerticalHeader(vertical_header)

    def getHorizontalHeaderWidth(self):
        horizontal_header = self.horizontalHeader()
        return horizontal_header.defaultSectionSize()

    def setHorizontalHeaderWidth(self, width: int):
        horizontal_header = self.horizontalHeader()
        horizontal_header.setResizeMode(QHeaderView.Fixed)
        horizontal_header.setDefaultSectionSize(width)
        self.setHorizontalHeader(horizontal_header)

    def disableScrollBar(self, horizontal: bool, vertical: bool):
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff if vertical else Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff if horizontal else Qt.ScrollBarAsNeeded)

    def setNoSelection(self):
        self.setFocusPolicy(Qt.NoFocus)
        self.setSelectionMode(QAbstractItemView.NoSelection)

    def setRowSelectMode(self):
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

    def setItemSelectMode(self):
        self.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

    def setColumnSelectMode(self):
        self.setSelectionBehavior(QAbstractItemView.SelectColumns)
        self.setSelectionMode(QAbstractItemView.SingleSelection)

    def setAutoWidth(self):
        self.setColumnStretchFactor([1 / self.columnCount()] * self.columnCount())

    def setAutoHeight(self, enable: bool):
        self.__autoHeight = enable
        self.resize(self.geometry().width(), self.geometry().height())

    def setRowAlignment(self, row: int, alignment: Qt.AlignmentFlag) -> bool:
        if not isinstance(alignment, Qt.AlignmentFlag):
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

    def setRowHeader(self, headers: List[str] or Tuple[str]) -> bool:
        if not isinstance(headers, (list, tuple)) or not self.__checkModel():
            return False

        if len(headers) > self.model().rowCount():
            return False

        return self.model().setVerticalHeaderLabels(headers)

    def setColumnHeader(self, headers: List[str] or Tuple[str]) -> bool:
        if not isinstance(headers, (list, tuple)) or not self.__checkModel():
            return False

        if len(headers) > self.model().rowCount():
            return False

        return self.model().setHorizontalHeaderLabels(headers)

    def setColumnStretchFactor(self, factors: List[float] or Tuple[float]):
        if not isinstance(factors, (list, tuple)):
            return

        if len(factors) > self.model().columnCount():
            return

        self.__columnStretchFactor = factors
        self.resize(self.geometry().width(), self.geometry().height())

    def resizeEvent(self, ev):
        if not self.model():
            return

        width = ev.size().width()
        height = ev.size().height()

        # Auto adjust table row height
        if self.__autoHeight:
            self.setVerticalHeaderHeight(height / self.model().rowCount())

        if len(self.__columnStretchFactor) == 0:
            super(TableView, self).resizeEvent(ev)
            return

        # Auto adjust table column width
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        for column, factor in enumerate(self.__columnStretchFactor):
            header.setResizeMode(column, QHeaderView.Fixed)
            self.setColumnWidth(column, width * factor)

    def getCurrentRow(self) -> int:
        model = self.model()
        if not isinstance(model, QAbstractItemModel):
            return 0

        return self.currentIndex().row()

    def getCurrentColumn(self) -> int:
        model = self.model()
        if not isinstance(model, QAbstractItemModel):
            return 0

        return self.currentIndex().column()

    def setCurrentRow(self, row: int) -> bool:
        model = self.model()
        if not isinstance(model, QAbstractItemModel):
            return False

        return self.setCurrentIndex(model.index(row, 0, QModelIndex()))

    def getTableData(self, role: Qt.ItemDataRole = Qt.DisplayRole):
        model = self.model()
        if not isinstance(model, QAbstractItemModel):
            return list()
        return [self.getRowData(row, role) for row in range(model.rowCount())]

    def setTableData(self, data: List[Any], role: Qt.ItemDataRole = Qt.EditRole):
        model = self.model()
        if not isinstance(model, QAbstractItemModel):
            return False

        if not isinstance(data, list) or len(data) != model.rowCount():
            return False

        return sum([self.setRowData(row, data[row], role) for row in range(model.rowCount())]) == len(data)

    def getRowData(self, row: int, role: Qt.ItemDataRole = Qt.DisplayRole):
        model = self.model()
        if not isinstance(model, QAbstractItemModel):
            return list()

        return [self.getItemData(row, column, role) for column in range(model.columnCount())]

    def setRowData(self, row: int, data: List[Any] or Tuple[Any, ...], role: Qt.ItemIsEditable = Qt.EditRole):
        model = self.model()
        if not isinstance(model, QAbstractItemModel):
            return False

        if not isinstance(data, (list, tuple)) or len(data) != model.columnCount():
            return False

        return sum([self.setItemData(row, column, data[column], role)
                    for column in range(model.columnCount())]) == len(data)

    def getColumnData(self, column: int, role: Qt.ItemDataRole = Qt.DisplayRole):
        model = self.model()
        if not isinstance(model, QAbstractItemModel):
            return list()

        return [self.getItemData(row, column, role) for row in range(model.rowCount())]

    def setColumnData(self, column: int, data: List[Any] or Tuple[Any, ...], role: Qt.ItemDataRole = Qt.EditRole):
        model = self.model()
        if not isinstance(model, QAbstractItemModel):
            return False

        if not isinstance(data, (list, tuple)) or len(data) != model.rowCount():
            return False

        return sum([self.setItemData(row, column, data[row], role)
                    for row in range(model.rowCount())]) == len(data)

    def getItemData(self, row: int, column: int, role: Qt.ItemDataRole = Qt.DisplayRole):
        model = self.model()
        if not isinstance(model, QAbstractItemModel):
            return ""

        widget = self.indexWidget(self.model().index(row, column))

        if isinstance(widget, QWidget):
            return ComponentManager.getComponentData(widget)
        else:
            return model.itemData(model.index(row, column, QModelIndex())).get(role)

    def setItemData(self, row: int, column: int, data: Any, role: Qt.ItemDataRole = Qt.EditRole):
        model = self.model()
        if not isinstance(model, QAbstractItemModel):
            return False

        return model.setData(model.index(row, column, QModelIndex()), data, role)

    def frozenItem(self, row: int, column: int, frozen: bool) -> bool:
        if not self.__checkRow(row) or not self.__checkColumn(column):
            return False

        item = self.item(row, column)
        if isinstance(item, QTableWidgetItem):
            flags = item.flags()
            if frozen:
                flags &= ~Qt.ItemIsEditable
            else:
                flags |= Qt.ItemIsEditable
            item.setFlags(flags)

        if self.__checkModel():
            widget = self.indexWidget(self.model().index(row, column))
            if isinstance(widget, QWidget):
                widget.setCheckable(not frozen) if isinstance(widget, QCheckBox) else widget.setDisabled(frozen)

        if isinstance(self.itemDelegate(), QItemDelegate):
            self.itemDelegate().setProperty(str(DynamicObject(row=row, column=column)), frozen)

        return True

    def frozenTable(self, frozen: bool) -> bool:
        for row in range(self.rowCount()):
            if not self.frozenRow(row, frozen):
                return False

        return True

    def frozenRow(self, row: int, frozen: bool) -> bool:
        for column in range(self.columnCount()):
            if not self.frozenItem(row, column, frozen):
                return False

        return True

    def frozenColumn(self, column: int, frozen: bool) -> bool:
        for row in range(self.rowCount()):
            if not self.frozenItem(row, column, frozen):
                return False

        return True

    def swapItem(self, src_row: int, src_column: int, dst_row: int, dst_column: int) -> bool:
        if not self.__checkRow(src_row) or not self.__checkRow(dst_row):
            return False

        if not self.__checkColumn(src_column) or not self.__checkColumn(dst_column):
            return False

        src_data = self.getItemData(src_row, src_column)
        dst_data = self.getItemData(dst_row, dst_column)
        self.setItemData(src_row, src_column, dst_data)
        self.setItemData(dst_row, dst_column, src_data)
        return True

    def swapRow(self, src: int, dst: int):
        for column in range(self.columnCount()):
            self.swapItem(src, column, dst, column)

            # Select dst row
        self.selectRow(dst)
        self.tableDataChanged.emit()

    def swapColumn(self, src: int, dst: int):
        for row in range(self.rowCount()):
            self.swapItem(row, src, row, dst)

        # Select destination column
        self.selectColumn(dst)
        self.tableDataChanged.emit()

    def rowMoveUp(self):
        row = self.getCurrentRow()
        if row == 0:
            return
        self.swapRow(row, row - 1)

    def rowMoveDown(self):
        row = self.getCurrentRow()
        if row == self.rowCount() - 1:
            return
        self.swapRow(row, row + 1)

    def rowMoveTop(self):
        while self.getCurrentRow() != 0:
            self.rowMoveUp()

        self.setCurrentRow(0)

    def rowMoveBottom(self):
        while self.getCurrentRow() != self.rowCount() - 1:
            self.rowMoveDown()

        self.setCurrentRow(self.rowCount() - 1)

    def columnMoveLeft(self):
        column = self.getCurrentColumn()
        if column == 0:
            return
        self.swapColumn(column, column - 1)

    def columnMoveRight(self):
        column = self.getCurrentColumn()
        if column == self.columnCount() - 1:
            return
        self.swapColumn(column, column + 1)


class TableViewDelegate(QItemDelegate):
    dataChanged = Signal(QModelIndex, object)

    def __init__(self, parent: QWidget or None = None):
        super(TableViewDelegate, self).__init__(parent)
        self._columnDelegateSettings = dict()

    def setColumnDelegate(self, filter_: Dict[int, UiInputSetting]):
        if isinstance(filter_, dict):
            self._columnDelegateSettings = filter_

    def updateColumnDelegate(self, column: int, filter_: UiInputSetting):
        if column in self._columnDelegateSettings and isinstance(filter_, UiInputSetting):
            self._columnDelegateSettings[column] = filter_

    def isFrozen(self, index: QStyleOptionViewItem) -> bool:
        row = index.row()
        column = index.column()
        return self.property(str(DynamicObject(row=row, column=column)))

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QStyleOptionViewItem):
        if not isinstance(index, QModelIndex) or self.isFrozen(index):
            return None

        settings = self._columnDelegateSettings.get(index.column())
        if not isinstance(settings, UiInputSetting):
            return None

        if isinstance(settings, UiCheckBoxInput):
            checkbox = CheckBox(parent=parent)
            checkbox.stateChanged.connect(lambda x: self.commitData.emit(checkbox))
            return checkbox
        else:
            widget = JsonSettingWidget.createInputWidget(settings, parent=parent)

            if isinstance(widget, QSpinBox):
                widget.valueChanged.connect(lambda x: self.commitData.emit(widget))
            if isinstance(widget, QDoubleSpinBox):
                widget.valueChanged.connect(lambda x: self.commitData.emit(widget))
            elif isinstance(widget, QComboBox):
                widget.currentIndexChanged.connect(lambda x: self.commitData.emit(widget))
            elif isinstance(widget, QCheckBox):
                widget.stateChanged.connect(lambda x: self.commitData.emit(widget))
            elif isinstance(widget, QRadioButton):
                widget.clicked.connect(lambda x: self.commitData.emit(widget))
            elif isinstance(widget, QLineEdit):
                widget.textChanged.connect(lambda x: self.commitData.emit(widget))
            elif isinstance(widget, QTextEdit):
                widget.textChanged.connect(lambda x: self.commitData.emit(widget))
            elif isinstance(widget, QPlainTextEdit):
                widget.textChanged.connect(lambda x: self.commitData.emit(widget))
            elif isinstance(widget, QDateTimeEdit):
                widget.dateTimeChanged.connect(lambda x: self.commitData.emit(widget))
            elif isinstance(widget, QDial):
                widget.valueChanged.connect(lambda x: self.commitData.emit(widget))

            return widget

    def setEditorData(self, editor: QWidget, index: QModelIndex):
        if not isinstance(index, QModelIndex):
            return None

        value = index.model().data(index, Qt.EditRole)
        ComponentManager.setComponentData(editor, value)

    def setModelData(self, editor: QWidget, model: QStandardItemModel, index: QModelIndex):
        if not isinstance(index, QModelIndex) or not isinstance(model, QStandardItemModel):
            return None

        data = ComponentManager.getComponentData(editor)
        if model.data(index) != data:
            model.setData(index, data, Qt.EditRole)
            self.dataChanged.emit(index, data)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)
