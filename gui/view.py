# -*- coding: utf-8 -*-
import abc
import typing
from PySide2.QtCore import Qt
from PySide2 import QtCore, QtGui, QtWidgets

from .msgbox import *
from .checkbox import CheckBox
from .container import ComponentManager
from .widget import JsonSettingWidget, BasicWidget

from ..misc.settings import *
from ..gui.model import SqliteQueryModel
from ..core.datatype import DynamicObject
from ..misc.windpi import get_program_scale_factor
__all__ = ['TableView', 'TableViewDelegate', 'SQliteQueryView']


class TableView(QtWidgets.QTableView):
    tableDataChanged = QtCore.Signal()

    ALL_ACTION = 0x7
    SUPPORT_ACTIONS = (0x1, 0x2, 0x4, 0x8)
    COMM_ACTION, MOVE_ACTION, FROZEN_ACTION, CUSTOM_ACTION = SUPPORT_ACTIONS

    def __init__(self, disable_custom_content_menu: bool = True, parent: typing.Optional[QtWidgets.QWidget] = None):
        super(TableView, self).__init__(parent)
        self.__autoHeight = False
        self.__contentMenu = QtWidgets.QMenu(self)
        self.__contentMenuEnableMask = 0x0
        self.__columnStretchFactor = list()
        self.__scale_x, self.__scale_y = get_program_scale_factor()

        for group, actions in {
            self.COMM_ACTION: [
                (QtWidgets.QAction(self.tr("Clear All"), self), lambda: self.model().setRowCount(0)),
            ],

            self.MOVE_ACTION: [
                (QtWidgets.QAction(self.tr("Move Up"), self), lambda: self.rowMoveUp()),
                (QtWidgets.QAction(self.tr("Move Down"), self), lambda: self.rowMoveDown()),

                (QtWidgets.QAction(self.tr("Move Top"), self), lambda: self.rowMoveTop()),
                (QtWidgets.QAction(self.tr("Move Bottom"), self), lambda: self.rowMoveBottom()),
            ],
        }.items():
            for action, slot in actions:
                action.triggered.connect(slot)
                action.setProperty("group", group)
                self.__contentMenu.addAction(action)

            self.__contentMenu.addSeparator()

        if not disable_custom_content_menu:
            self.customContextMenuRequested.connect(self.__slotShowContentMenu)

    def __checkModel(self) -> bool:
        return isinstance(self.model(), QtCore.QAbstractItemModel)

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

    def __slotShowContentMenu(self, pos: QtCore.QPoint):
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

    def setCustomContentMenu(self, menu: typing.List[QtWidgets.QAction]):
        for action in menu:
            if not isinstance(action, QtWidgets.QAction):
                continue

            action.setProperty("group", self.CUSTOM_ACTION)
            self.__contentMenu.addAction(action)

        self.__contentMenu.addSeparator()

    def item(self, row: int, column: int) -> typing.Union[QtWidgets.QTableWidgetItem, None]:
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
        vertical_header.setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        vertical_header.setDefaultSectionSize(height)
        self.setVerticalHeader(vertical_header)

    def getHorizontalHeaderWidth(self):
        horizontal_header = self.horizontalHeader()
        return horizontal_header.defaultSectionSize()

    def setHorizontalHeaderWidth(self, width: int):
        horizontal_header = self.horizontalHeader()
        horizontal_header.setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        horizontal_header.setDefaultSectionSize(width)
        self.setHorizontalHeader(horizontal_header)

    def disableScrollBar(self, horizontal: bool, vertical: bool):
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff if vertical else Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff if horizontal else Qt.ScrollBarAsNeeded)

    def setNoSelection(self):
        self.setFocusPolicy(Qt.NoFocus)
        self.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)

    def setRowSelectMode(self):
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

    def setItemSelectMode(self):
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

    def setColumnSelectMode(self):
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectColumns)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

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
                # noinspection PyTypeChecker
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
                # noinspection PyTypeChecker
                item.setTextAlignment(alignment)
            except AttributeError:
                continue

        return True

    def setTableAlignment(self, alignment: Qt.AlignmentFlag) -> bool:
        for row in range(self.rowCount()):
            if not self.setRowAlignment(row, alignment):
                return False

        return True

    def setRowHeader(self, headers: typing.Sequence[str]) -> bool:
        if not isinstance(headers, (list, tuple)) or not self.__checkModel():
            return False

        if len(headers) > self.model().rowCount():
            return False

        return self.model().setVerticalHeaderLabels(headers)

    def setColumnHeader(self, headers: typing.Sequence[str]) -> bool:
        if not isinstance(headers, (list, tuple)) or not self.__checkModel():
            return False

        if len(headers) > self.model().rowCount():
            return False

        return self.model().setHorizontalHeaderLabels(headers)

    def setColumnStretchFactor(self, factors: typing.Sequence[float]):
        if not isinstance(factors, (list, tuple)):
            return

        if len(factors) > self.model().columnCount():
            return

        self.__columnStretchFactor = factors
        self.resizeEvent(QtGui.QResizeEvent(self.geometry().size(), self.geometry().size()))

    def resizeEvent(self, ev: QtGui.QResizeEvent):
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
            header.setSectionResizeMode(column, QtWidgets.QHeaderView.Fixed)
            self.setColumnWidth(column, width * factor)

    def getCurrentRow(self) -> int:
        model = self.model()
        if not isinstance(model, QtCore.QAbstractItemModel):
            return 0

        return self.currentIndex().row()

    def getCurrentColumn(self) -> int:
        model = self.model()
        if not isinstance(model, QtCore.QAbstractItemModel):
            return 0

        return self.currentIndex().column()

    def setCurrentRow(self, row: int) -> bool:
        model = self.model()
        if not isinstance(model, QtCore.QAbstractItemModel):
            return False

        # noinspection PyTypeChecker
        return self.setCurrentIndex(model.index(row, 0, QtCore.QModelIndex()))

    def setRowCount(self, count: int):
        if isinstance(self.model(), QtCore.QAbstractItemModel):
            self.model().setRowCount(count)

    def getTableData(self, role: Qt.ItemDataRole = Qt.DisplayRole):
        model = self.model()
        if not isinstance(model, QtCore.QAbstractItemModel):
            return list()
        return [self.getRowData(row, role) for row in range(model.rowCount())]

    def setTableData(self, data: typing.List[typing.Any], role: Qt.ItemDataRole = Qt.EditRole):
        model = self.model()
        if not isinstance(model, QtCore.QAbstractItemModel):
            return False

        if not isinstance(data, list) or len(data) != model.rowCount():
            return False

        return sum([self.setRowData(row, data[row], role) for row in range(model.rowCount())]) == len(data)

    def getRowData(self, row: int, role: Qt.ItemDataRole = Qt.DisplayRole):
        model = self.model()
        if not isinstance(model, QtCore.QAbstractItemModel):
            return list()

        return [self.getItemData(row, column, role) for column in range(model.columnCount())]

    def setRowData(self, row: int, data: typing.Sequence[typing.Any], role: Qt.ItemIsEditable = Qt.EditRole):
        model = self.model()
        if not isinstance(model, QtCore.QAbstractItemModel):
            return False

        if not isinstance(data, (list, tuple)) or len(data) != model.columnCount():
            return False

        return sum([self.setItemData(row, column, data[column], role)
                    for column in range(model.columnCount())]) == len(data)

    def getColumnData(self, column: int, role: Qt.ItemDataRole = Qt.DisplayRole):
        model = self.model()
        if not isinstance(model, QtCore.QAbstractItemModel):
            return list()

        return [self.getItemData(row, column, role) for row in range(model.rowCount())]

    def setColumnData(self, column: int, data: typing.Sequence[typing.Any], role: Qt.ItemDataRole = Qt.EditRole):
        model = self.model()
        if not isinstance(model, QtCore.QAbstractItemModel):
            return False

        if not isinstance(data, (list, tuple)) or len(data) != model.rowCount():
            return False

        return sum([self.setItemData(row, column, data[row], role)
                    for row in range(model.rowCount())]) == len(data)

    def getItemData(self, row: int, column: int, role: Qt.ItemDataRole = Qt.DisplayRole):
        model = self.model()
        if not isinstance(model, QtCore.QAbstractItemModel):
            return ""

        widget = self.indexWidget(self.model().index(row, column))
        if isinstance(widget, QtWidgets.QWidget):
            return ComponentManager.getComponentData(widget)
        else:
            return model.itemData(model.index(row, column, QtCore.QModelIndex())).get(role)

    def setItemData(self, row: int, column: int, data: typing.Any, role: Qt.ItemDataRole = Qt.EditRole):
        model = self.model()
        if not isinstance(model, QtCore.QAbstractItemModel):
            return False

        # noinspection PyTypeChecker
        return model.setData(model.index(row, column, QtCore.QModelIndex()), data, role)

    def frozenItem(self, row: int, column: int, frozen: bool) -> bool:
        if not self.__checkRow(row) or not self.__checkColumn(column):
            return False

        item = self.item(row, column)
        if isinstance(item, QtWidgets.QTableWidgetItem):
            flags = item.flags()
            if frozen:
                flags &= ~Qt.ItemIsEditable
            else:
                flags |= Qt.ItemIsEditable
            item.setFlags(flags)

        if self.__checkModel():
            widget = self.indexWidget(self.model().index(row, column))
            if isinstance(widget, QtWidgets.QWidget):
                widget.setCheckable(not frozen) if isinstance(widget, QtWidgets.QCheckBox) \
                    else widget.setDisabled(frozen)

        if isinstance(self.itemDelegate(), QtWidgets.QItemDelegate):
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

    def rowMoveUp(self) -> bool:
        row = self.getCurrentRow()
        if row == 0:
            return False

        self.swapRow(row, row - 1)
        return True

    def rowMoveDown(self) -> bool:
        row = self.getCurrentRow()
        if row == self.rowCount() - 1:
            return False

        self.swapRow(row, row + 1)
        return True

    def rowMoveTop(self):
        while self.getCurrentRow() != 0:
            self.rowMoveUp()

        self.setCurrentRow(0)

    def rowMoveBottom(self):
        while self.getCurrentRow() != self.rowCount() - 1:
            self.rowMoveDown()

        self.setCurrentRow(self.rowCount() - 1)

    def columnMoveLeft(self) -> bool:
        column = self.getCurrentColumn()
        if column == 0:
            return False

        self.swapColumn(column, column - 1)
        return True

    def columnMoveRight(self) -> bool:
        column = self.getCurrentColumn()
        if column == self.columnCount() - 1:
            return False

        self.swapColumn(column, column + 1)
        return True

    def setItemBackground(self, row: int, column: int, background: QtGui.QBrush) -> bool:
        if not self.__checkRow(row) or not self.__checkColumn(column) or not isinstance(background, QtGui.QBrush):
            return False

        try:
            item = self.item(row, column)
            item.setBackground(background)
        except AttributeError:
            return False

        return True

    def setItemForeground(self, row: int, column: int, foreground: QtGui.QBrush) -> bool:
        if not self.__checkRow(row) or not self.__checkColumn(column) or not isinstance(foreground, QtGui.QBrush):
            return False

        try:
            item = self.item(row, column)
            item.setForeground(foreground)
        except AttributeError:
            return False

        return True

    def setRowBackgroundColor(self, row: int, color: QtGui.QBrush):
        [self.setItemBackground(row, column, color) for column in range(self.columnCount())]

    def setRowForegroundColor(self, row: int, color: QtGui.QBrush):
        [self.setItemForeground(row, column, color) for column in range(self.columnCount())]

    def setColumnBackgroundColor(self, column: int, color: QtGui.QBrush):
        [self.setItemBackground(row, column, color) for row in range(self.rowCount())]

    def setColumnForegroundColor(self, column: int, color: QtGui.QBrush):
        [self.setItemForeground(row, column, color) for row in range(self.rowCount())]


class TableViewDelegate(QtWidgets.QItemDelegate):
    dataChanged = QtCore.Signal(QtCore.QModelIndex, object)

    def __init__(self, parent: typing.Optional[QtWidgets.QWidget] = None):
        super(TableViewDelegate, self).__init__(parent)
        self._columnDelegateSettings = dict()

    def setColumnDelegate(self, filter_: typing.Dict[int, UiInputSetting]):
        if isinstance(filter_, dict):
            self._columnDelegateSettings = filter_

    def updateColumnDelegate(self, column: int, filter_: UiInputSetting):
        if column in self._columnDelegateSettings and isinstance(filter_, UiInputSetting):
            self._columnDelegateSettings[column] = filter_

    def isFrozen(self, index: QtWidgets.QStyleOptionViewItem) -> bool:
        row = index.row()
        column = index.column()
        return self.property(str(DynamicObject(row=row, column=column)))

    def createEditor(self, parent: QtWidgets.QWidget,
                     option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex):
        if not isinstance(index, QtCore.QModelIndex) or self.isFrozen(index):
            return None

        settings = self._columnDelegateSettings.get(index.column())
        if not isinstance(settings, UiInputSetting):
            return None

        if isinstance(settings, UiCheckBoxInput):
            checkbox = CheckBox(stylesheet=DynamicObject(fillColor=(0, 0, 0), sizeFactor=1.7).dict, parent=parent)
            checkbox.stateChanged.connect(lambda x: self.commitData.emit(checkbox))
            return checkbox
        elif isinstance(settings, UiPushButtonInput):
            button = QtWidgets.QPushButton(settings.get_name(), parent=parent)
            button.setProperty('private', index.data())
            button.setProperty('index', index)
            button.clicked.connect(settings.get_default())
            return button
        else:
            widget = JsonSettingWidget.createInputWidget(settings, parent=parent)
            widget.setFocus()
            ComponentManager.connectComponentSignalAndSlot(widget, lambda _: self.commitData.emit(widget))
            return widget

    def setEditorData(self, editor: QtWidgets.QWidget, index: QtCore.QModelIndex):
        if not isinstance(index, QtCore.QModelIndex):
            return None

        value = index.model().data(index, Qt.EditRole)
        ComponentManager.setComponentData(editor, value)

    def setModelData(self, editor: QtWidgets.QWidget, model: QtGui.QStandardItemModel, index: QtCore.QModelIndex):
        if not isinstance(index, QtCore.QModelIndex) or not isinstance(model, QtCore.QAbstractItemModel):
            return None

        data = ComponentManager.getComponentData(editor)
        if model.data(index) != data:
            model.setData(index, data, Qt.EditRole)
            self.dataChanged.emit(index, data)

    def updateEditorGeometry(self, editor: QtWidgets.QWidget,
                             option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex):
        editor.setGeometry(option.rect)


class SQliteQueryView(BasicWidget):
    signalRecordsCleared = QtCore.Signal()
    signalRecordDeleted = QtCore.Signal(object)

    def __init__(self, model: SqliteQueryModel,
                 stretch_factor: typing.Sequence[float], column_header: typing.Iterable[str],
                 custom_content_menu: typing.Optional[typing.Sequence[QtWidgets.QAction]] = None,
                 readonly: bool = False, row_autoincrement_factor: float = 0.0,
                 parent: QtWidgets.QWidget = None):
        custom_content_menu = custom_content_menu or list()
        self._model = model
        self._is_readonly = readonly
        self._column_header = column_header
        self._stretch_factor = stretch_factor
        self._custom_content_menu = list(custom_content_menu)
        self._row_autoincrement_factor = row_autoincrement_factor
        super(SQliteQueryView, self).__init__(parent)

    def _initUi(self):
        self.ui_view = TableView(True, self)
        self.ui_page_num = QtWidgets.QSpinBox(self)
        self.ui_search_key = QtWidgets.QComboBox(self)
        self.ui_search_value = QtWidgets.QLineEdit(self)
        self.ui_end = QtWidgets.QPushButton(self.tr('End'))
        self.ui_home = QtWidgets.QPushButton(self.tr('Home'))
        self.ui_next = QtWidgets.QPushButton(self.tr('Next'))
        self.ui_prev = QtWidgets.QPushButton(self.tr('Prev'))
        self.ui_search = QtWidgets.QPushButton(self.tr('Search'))
        self.ui_clear_search = QtWidgets.QPushButton(self.tr('Clear Search'))

        # Custom content menu
        self.ui_content_menu = QtWidgets.QMenu(self)
        self.ui_action_del = QtWidgets.QAction(self.tr('Delete Record'), self.ui_content_menu)
        self.ui_action_clear = QtWidgets.QAction(self.tr('Clear All Records'), self.ui_content_menu)

        if not self._is_readonly:
            self.ui_content_menu.addAction(self.ui_action_del)
            self.ui_content_menu.addAction(self.ui_action_clear)

        if self._custom_content_menu:
            self.ui_content_menu.addSeparator()
            self.ui_content_menu.addActions(self._custom_content_menu)

        tools_layout = QtWidgets.QHBoxLayout()
        for item in (self.ui_search_key, self.ui_search_value, self.ui_search, self.ui_clear_search,
                     QtWidgets.QSplitter(), QtWidgets.QLabel(self.tr('Page Num')), self.ui_page_num,
                     self.ui_prev, self.ui_next, self.ui_home, self.ui_end):
            tools_layout.addWidget(item)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.ui_view)
        layout.addLayout(tools_layout)
        self.setLayout(layout)

    def _initData(self):
        self.ui_page_num.setValue(1)
        self.ui_view.setModel(self._model)
        self.ui_page_num.setRange(1, self._model.total_page)

        self._model.flush_page(0)
        self._model.set_column_header(self._column_header)

        for key, name in zip(self._model.keys, self._model.column_header):
            self.ui_search_key.addItem(name, key)

    def _initStyle(self):
        self.ui_view.setRowSelectMode()
        self.ui_view.hideRowHeader(True)
        self.ui_view.setAlternatingRowColors(True)
        self.ui_view.setColumnStretchFactor(self._stretch_factor)
        self.ui_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.ui_view.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignLeft)

    def _initSignalAndSlots(self):
        self.ui_end.clicked.connect(self.slotEnd)
        self.ui_home.clicked.connect(self.slotHome)
        self.ui_prev.clicked.connect(self.slotPrev)
        self.ui_next.clicked.connect(self.slotNext)
        self.ui_search.clicked.connect(self.slotSearch)
        self.ui_action_del.triggered.connect(self.slotDelete)
        self.ui_action_clear.triggered.connect(self.slotClear)
        self.ui_clear_search.clicked.connect(self.slotClearSearch)
        self.ui_page_num.valueChanged.connect(self.slotPageNumChanged)
        self.ui_view.customContextMenuRequested.connect(self.slotCustomContentMenu)

        self.ui_end.setShortcut(QtGui.QKeySequence(Qt.Key_End))
        self.ui_home.setShortcut(QtGui.QKeySequence(Qt.Key_Home))
        self.ui_prev.setShortcut(QtGui.QKeySequence(Qt.Key_PageUp))
        self.ui_next.setShortcut(QtGui.QKeySequence(Qt.Key_PageDown))
        self.ui_search.setShortcut(QtGui.QKeySequence(Qt.Key_Return))
        self.ui_clear_search.setShortcut(QtGui.QKeySequence(Qt.Key_Escape))

    @abc.abstractmethod
    def _get_pk_from_row(self, row: int) -> typing.Any:
        pass

    @abc.abstractmethod
    def _enable_fuzzy_search(self, key: str) -> bool:
        pass

    def tr(self, text: str) -> str:
        # noinspection PyTypeChecker
        return QtWidgets.QApplication.translate("SQliteQueryView", text, None)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        if self._row_autoincrement_factor:
            self._model.rows_per_page = self.ui_view.geometry().height() / self._row_autoincrement_factor
        super(SQliteQueryView, self).resizeEvent(event)

    def slotEnd(self):
        self.ui_page_num.setValue(self._model.total_page)

    def slotHome(self):
        self.ui_page_num.setValue(1)

    def slotPrev(self):
        if self.ui_page_num.value() > 1:
            self.ui_page_num.setValue(self.ui_page_num.value() - 1)

    def slotNext(self):
        if self.ui_page_num.value() < self._model.total_page:
            self.ui_page_num.setValue(self.ui_page_num.value() + 1)

    def slotClear(self):
        if not showQuestionBox(self, self.tr('Confirm to clear all records ?'), self.tr('Clear Confirm')):
            return

        if self._model.clear_table():
            self.signalRecordsCleared.emit()
            self.slotUpdatePageNum()

    def slotSearch(self):
        value = self.ui_search_value.text()
        if not value:
            self._model.show_all()
        else:
            key = self.ui_search_key.currentData(QtCore.Qt.UserRole)
            self._model.search_record(key, value, self._enable_fuzzy_search(key))

    def slotDelete(self):
        if not showQuestionBox(self, self.tr('Confirm to delete this record ?'), self.tr('Delete Confirm')):
            return

        row = self.ui_view.getCurrentRow()
        primary_key = self._get_pk_from_row(row)
        if self._model.delete_record(primary_key):
            self.signalRecordDeleted.emit(primary_key)
            self.slotUpdatePageNum()

    def slotClearSearch(self):
        self._model.flush_page(self._model.cur_page)

    def slotUpdatePageNum(self):
        self.ui_page_num.setRange(1, self._model.total_page)
        if self._model.record_count == 1:
            self._model.set_column_header(self._column_header)
            self.ui_view.setColumnStretchFactor(self._stretch_factor)

    def slotPageNumChanged(self, page):
        self._model.flush_page(page - 1)

    def slotCustomContentMenu(self, pos: QtCore.QPoint):
        if not self._model.record_count:
            return

        if not self.ui_content_menu.size():
            return

        self.ui_content_menu.popup(self.ui_view.viewport().mapToGlobal(pos))
