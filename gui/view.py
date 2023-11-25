# -*- coding: utf-8 -*-
import abc
import typing
import datetime
import contextlib
import collections
from PySide2.QtCore import Qt
from PySide2 import QtCore, QtGui, QtWidgets

from .msgbox import *
from .checkbox import CheckBox
from .misc import PageNumberBox
# from ..misc.debug import track_time
from .container import ComponentManager
from .widget import JsonSettingWidget, BasicWidget

from ..misc.settings import *
from ..core.timer import Task, Tasklet
from ..core.datatype import DynamicObject
from ..misc.windpi import get_program_scale_factor
from ..gui.model import SqliteQueryModel, AbstractTableModel
__all__ = ['TableView', 'TableViewDelegate', 'SQliteQueryView']


class TableView(QtWidgets.QTableView):
    tableDataChanged = QtCore.Signal()

    # Custom menu signals
    signalRequestClearAll = QtCore.Signal()
    signalRequestRowMoveUp = QtCore.Signal(int)
    signalRequestRowMoveDown = QtCore.Signal(int)
    signalRequestRowMoveToTop = QtCore.Signal(int)
    signalRequestRowMoveToBottom = QtCore.Signal(int)

    ALL_ACTION = 0xf
    Action = collections.namedtuple('Action', ['COMM', 'MOVE', 'FROZEN', 'CUSTOM'])(*(0x1, 0x2, 0x4, 0x8))

    def __init__(self, disable_custom_content_menu: bool = True, parent: typing.Optional[QtWidgets.QWidget] = None):
        super(TableView, self).__init__(parent)
        self.__autoHeight = False
        self.__contentMenu = QtWidgets.QMenu(self)
        self.__contentMenuEnableMask = 0x0
        self.__columnStretchFactor = list()
        self.__scale_x, self.__scale_y = get_program_scale_factor()

        for group, actions in {
            self.Action.COMM: [
                (
                        QtWidgets.QAction(self.tr("Clear All"), self), lambda: self.signalRequestClearAll.emit()
                ),
            ],

            self.Action.MOVE: [
                (
                        QtWidgets.QAction(self.tr("Move Up"), self),
                        lambda: self.signalRequestRowMoveUp.emit(self.getCurrentRow())
                ),

                (
                        QtWidgets.QAction(self.tr("Move Down"), self),
                        lambda: self.signalRequestRowMoveDown.emit(self.getCurrentRow())
                ),

                (
                        QtWidgets.QAction(self.tr("Move Top"), self),
                        lambda: self.signalRequestRowMoveToTop.emit(self.getCurrentRow())
                ),

                (
                        QtWidgets.QAction(self.tr("Move Bottom"), self),
                        lambda: self.signalRequestRowMoveToBottom.emit(self.getCurrentRow())
                ),
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
        for group in self.Action:
            enabled = group & self.__contentMenuEnableMask
            for action in self.__contentMenu.actions():
                if action.property("group") == group:
                    action.setVisible(enabled)

        self.__contentMenu.popup(self.viewport().mapToGlobal(pos))

    def setModel(self, model: QtCore.QAbstractItemModel):
        if isinstance(model, AbstractTableModel):
            def rowMoveUp(row: int):
                with self.autoScrollContextManager():
                    if model.rowMoveUp(row):
                        self.setCurrentRow(row - 1)
                        self.tableDataChanged.emit()

            def rowMoveDown(row: int):
                with self.autoScrollContextManager():
                    if model.rowMoveDown(row):
                        self.setCurrentRow(row + 1)
                        self.tableDataChanged.emit()

            def rowMoveToTop(row: int):
                with self.autoScrollContextManager():
                    if model.rowMoveToTop(row):
                        self.setCurrentRow(0)
                        self.tableDataChanged.emit()

            def rowMoveToBottom(row: int):
                with self.autoScrollContextManager():
                    if model.rowMoveToBottom(row):
                        self.setCurrentRow(self.rowCount() - 1)
                        self.tableDataChanged.emit()

            self.signalRequestClearAll.connect(model.clearAll)

            self.signalRequestRowMoveUp.connect(rowMoveUp)
            self.signalRequestRowMoveDown.connect(rowMoveDown)
            self.signalRequestRowMoveToTop.connect(rowMoveToTop)
            self.signalRequestRowMoveToBottom.connect(rowMoveToBottom)

        super().setModel(model)

    def setContentMenuMask(self, mask: int):
        for group in self.Action:
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

            action.setProperty("group", self.Action.CUSTOM)
            self.__contentMenu.addAction(action)

        if menu:
            self.__contentMenu.addSeparator()
            self.setContentMenuMask(self.Action.CUSTOM)

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

        # if len(factors) > self.model().columnCount():
        #     return

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
        if not self.__checkModel():
            return 0

        return self.currentIndex().row()

    def getCurrentColumn(self) -> int:
        if not self.__checkModel():
            return 0

        return self.currentIndex().column()

    def setCurrentRow(self, row: int) -> bool:
        model = self.model()
        if not isinstance(model, QtCore.QAbstractItemModel):
            return False

        # noinspection PyTypeChecker
        return self.setCurrentIndex(model.index(row, 0, QtCore.QModelIndex()))

    def simulateSelectRow(self, row: int):
        self.selectRow(row)
        self.setFocus(Qt.MouseFocusReason)
        self.scrollTo(self.model().index(row, 0))

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
                widget.setFrozen(frozen) if isinstance(widget, CheckBox) \
                    else widget.setDisabled(frozen)

        if isinstance(self.itemDelegate(), QtWidgets.QItemDelegate):
            self.itemDelegate().setProperty(str(DynamicObject(row=row, column=column)), frozen)

        return True

    @contextlib.contextmanager
    def autoScrollContextManager(self):
        auto_scroll_enabled = self.hasAutoScroll()

        if auto_scroll_enabled:
            yield
        else:
            self.setAutoScroll(True)
            yield
            self.setAutoScroll(False)


class TableViewDelegate(QtWidgets.QItemDelegate):
    dataChanged = QtCore.Signal(QtCore.QModelIndex, object, object)

    def __init__(self, private: typing.Any = None, parent: typing.Optional[QtWidgets.QWidget] = None):
        super(TableViewDelegate, self).__init__(parent)
        self._private_data = private
        self._itemDelegateSettings = dict()
        self._columnDelegateSettings = dict()

    def setItemDelegate(self, filter_: typing.Dict[typing.Tuple[int, int], UiInputSetting]):
        if isinstance(filter_, dict):
            self._columnDelegateSettings.clear()
            self._itemDelegateSettings = filter_

    def setColumnDelegate(self, filter_: typing.Dict[int, UiInputSetting]):
        if isinstance(filter_, dict):
            self._itemDelegateSettings.clear()
            self._columnDelegateSettings = filter_

    def updateColumnDelegate(self, column: int, filter_: UiInputSetting):
        if column in self._columnDelegateSettings and isinstance(filter_, UiInputSetting):
            self._columnDelegateSettings[column] = filter_

    def updateItemDelegate(self, row: int, column: int, filter_: UiInputSetting):
        if (row, column) in self._itemDelegateSettings and isinstance(filter_, UiInputSetting):
            self._itemDelegateSettings[(row, column)] = filter_

    def isFrozen(self, index: QtWidgets.QStyleOptionViewItem) -> bool:
        row = index.row()
        column = index.column()
        return self.property(str(DynamicObject(row=row, column=column)))

    def createEditor(self, parent: QtWidgets.QWidget,
                     option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex):
        if not isinstance(index, QtCore.QModelIndex) or self.isFrozen(index):
            return None

        column_settings = self._columnDelegateSettings.get(index.column())
        item_settings = self._itemDelegateSettings.get((index.row(), index.column()))
        settings = item_settings or column_settings
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
            ComponentManager.connectComponentSignalAndSlot(
                widget, lambda data: self.commitAndCloseEditor(widget, data, index)
            )
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
            self.dataChanged.emit(index, data, self._private_data)

    def updateEditorGeometry(self, editor: QtWidgets.QWidget,
                             option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex):
        editor.setGeometry(option.rect)

    def commitAndCloseEditor(self, editor: QtWidgets.QWidget, data: typing.Any, index: QtCore.QModelIndex):
        self.commitData.emit(editor)
        self.dataChanged.emit(index, data, self._private_data)


class SQliteQueryView(BasicWidget):
    Group = 'group'
    signalRecordsCleared = QtCore.Signal()
    signalRequestScrollToTop = QtCore.Signal()
    signalRequestScrollToBottom = QtCore.Signal()
    signalRecordDeleted = QtCore.Signal(object)
    ToolGroups = collections.namedtuple('ToolGroups', 'Date Search PageTurnCtrl')(*'date search pt_ctrl'.split())

    def __init__(self, model: SqliteQueryModel,
                 stretch_factor: typing.Sequence[float] = None,
                 custom_content_menu: typing.Dict[
                     QtWidgets.QAction, typing.Callable[[QtCore.QModelIndex], bool]
                 ] = None,
                 date_search_columns: typing.Optional[typing.Sequence[int]] = None,
                 precisely_search_columns: typing.Optional[typing.Sequence[int]] = None,
                 readonly: bool = False, without_search: bool = False, without_pt_ctrl: bool = False,
                 row_autoincrement_factor: float = 0.0, datetime_format: str = 'yyyy/MM/dd hh:mm:ss',
                 search_box_min_width: int = 400, auto_init: bool = False, parent: QtWidgets.QWidget = None):
        """SQliteQueryView

        :param model: SqliteQueryModel instance
        :param stretch_factor:  column display stretch factor
        :param custom_content_menu: customize content menu action
        :param date_search_columns: which columns support data search
        :param precisely_search_columns:  which columns support precisely search
        :param readonly: is table is readonly
        :param without_search: hidden search toolbar
        :param without_pt_ctrl: hidden page control toolbar using scrollbar
        :param row_autoincrement_factor: row autoincrement factor
        :param datetime_format: datetime format date search using this
        :param search_box_min_width: search box minimum width
        :param auto_init: if set this stretch_factor/date_search_columns/precisely_search_columns will get from model
        :param parent: parent widget
        """
        date_search_columns = date_search_columns or [-1]
        precisely_search_columns = precisely_search_columns or list()
        stretch_factor = stretch_factor or [1 / model.columnCount()] * model.columnCount()

        self._model = model
        self._tasklet = Tasklet(name=self.__class__.__name__)

        self._without_search = without_search
        self._without_pt_ctrl = without_pt_ctrl

        self._datetime_format = datetime_format
        self._search_box_min_width = search_box_min_width
        self._row_autoincrement_factor = row_autoincrement_factor
        self._custom_content_menu = collections.OrderedDict(custom_content_menu or dict())

        # Auto load from SqliteQueryModel
        self._is_readonly = model.readonly if auto_init else readonly
        self._stretch_factor = model.column_stretch if auto_init else stretch_factor
        self._date_search_columns = model.date_search_columns if auto_init else date_search_columns
        self._precisely_search_columns = model.precisely_search_columns if auto_init else precisely_search_columns

        super(SQliteQueryView, self).__init__(parent)
        self.slotSearchKeyChanged(self.ui_search_key.currentIndex())

    def _initUi(self):
        self.ui_view = TableView(True, self)
        self.ui_page_num = PageNumberBox()
        self.ui_splitter = QtWidgets.QSplitter()
        self.ui_search_key = QtWidgets.QComboBox(self)
        self.ui_start_date = QtWidgets.QDateEdit(self)
        self.ui_end_date = QtWidgets.QDateEdit(self)
        self.ui_search_value = QtWidgets.QComboBox(self)
        self.ui_end = QtWidgets.QPushButton(self.tr('End'))
        self.ui_home = QtWidgets.QPushButton(self.tr('Home'))
        self.ui_next = QtWidgets.QPushButton(self.tr('Next'))
        self.ui_prev = QtWidgets.QPushButton(self.tr('Prev'))
        self.ui_search = QtWidgets.QPushButton(self.tr('Search'))
        self.ui_page_num_label = QtWidgets.QLabel(self.tr('Page Num'))
        self.ui_clear_search = QtWidgets.QPushButton(self.tr('Clear Search'))

        # Custom content menu
        self.ui_action_del = QtWidgets.QAction(self.tr('Delete Record'))
        self.ui_action_clear = QtWidgets.QAction(self.tr('Clear All Records'))

        # Date search layout
        date_search_layout = QtWidgets.QHBoxLayout()
        for item in (QtWidgets.QLabel(self.tr('Start Date')), self.ui_start_date,
                     QtWidgets.QLabel(self.tr('End Date')), self.ui_end_date):
            item.setProperty(self.Group, self.ToolGroups.Date)
            date_search_layout.addWidget(item)

        # Page flip control
        for item in (self.ui_splitter, self.ui_page_num_label,
                     self.ui_page_num, self.ui_prev, self.ui_next, self.ui_home, self.ui_end):
            item.setProperty(self.Group, self.ToolGroups.PageTurnCtrl)

        tools_layout = QtWidgets.QHBoxLayout()
        for item in (self.ui_search_key, self.ui_search_value, date_search_layout, self.ui_search, self.ui_clear_search,
                     self.ui_splitter, self.ui_page_num_label, self.ui_page_num,
                     self.ui_prev, self.ui_next, self.ui_home, self.ui_end):
            if isinstance(item, QtWidgets.QLayout):
                tools_layout.addLayout(item)
            else:
                tools_layout.addWidget(item)
        self.ui_tools_manager = ComponentManager(tools_layout)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.ui_view)
        layout.addLayout(tools_layout)
        self.setLayout(layout)

    def _initData(self):
        self.ui_page_num.setValue(1)
        self.ui_view.setModel(self._model)
        self.ui_page_num.setRange(1, self._model.total_page)

        now = datetime.datetime.now()
        today = QtCore.QDate(now.year, now.month, now.day)
        self.ui_start_date.setDate(today)
        self.ui_end_date.setDate(today)

        for key, name in zip(self._model.keys, self._model.column_header):
            self.ui_search_key.addItem(name, key)

        for element in (self.ui_search, self.ui_clear_search, self.ui_search_key, self.ui_search_value):
            element.setProperty(self.Group, self.ToolGroups.Search)

    def _initStyle(self):
        self.enableDateSearch(False)
        self.ui_search_value.setEditable(True)
        self.ui_search_value.setMinimumWidth(self._search_box_min_width)

        self.ui_end_date.setCalendarPopup(True)
        self.ui_start_date.setCalendarPopup(True)

        self.ui_view.setRowSelectMode()
        self.ui_view.hideRowHeader(True)
        self.ui_view.setAlternatingRowColors(True)
        self.ui_view.setColumnStretchFactor(self._stretch_factor)
        self.ui_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.ui_view.horizontalHeader().setDefaultAlignment(QtCore.Qt.AlignLeft)

        if self._without_search:
            for element in self.ui_tools_manager.findValue(self.Group, self.ToolGroups.Search):
                element.setHidden(True)

        if self._without_pt_ctrl:
            for element in self.ui_tools_manager.findValue(self.Group, self.ToolGroups.PageTurnCtrl):
                element.setHidden(True)

    def _initSignalAndSlots(self):
        self.ui_end.clicked.connect(self.slotEnd)
        self.ui_home.clicked.connect(self.slotHome)
        self.ui_prev.clicked.connect(self.slotPrev)
        self.ui_next.clicked.connect(self.slotNext)
        self.ui_search.clicked.connect(self.slotSearch)
        self.ui_clear_search.clicked.connect(self.slotFlush)
        self.ui_action_del.triggered.connect(self.slotDelete)
        self.ui_action_clear.triggered.connect(self.slotClear)
        self.ui_page_num.valueChanged.connect(self.slotPageNumChanged)
        self.ui_end_date.dateChanged.connect(self.slotUpdateDateRange)
        self.ui_start_date.dateChanged.connect(self.slotUpdateDateRange)
        self.ui_search_key.currentIndexChanged.connect(self.slotSearchKeyChanged)
        self.ui_view.customContextMenuRequested.connect(self.slotCustomContentMenu)

        self.ui_end.setShortcut(QtGui.QKeySequence(Qt.Key_End))
        self.ui_home.setShortcut(QtGui.QKeySequence(Qt.Key_Home))
        self.ui_prev.setShortcut(QtGui.QKeySequence(Qt.Key_PageUp))
        self.ui_next.setShortcut(QtGui.QKeySequence(Qt.Key_PageDown))
        self.ui_search.setShortcut(QtGui.QKeySequence(Qt.Key_Return))
        self.ui_clear_search.setShortcut(QtGui.QKeySequence(Qt.Key_Escape))

        self.signalRequestScrollToTop.connect(self.ui_view.scrollToTop)
        self.signalRequestScrollToBottom.connect(self.ui_view.scrollToBottom)

    @property
    def model(self) -> SqliteQueryModel:
        return self._model

    @abc.abstractmethod
    def _get_pk_from_row(self, row: int) -> typing.Any:
        pass

    def _enable_fuzzy_search(self, key: str) -> bool:
        return self._model.is_support_fuzzy_search(key)

    def tr(self, text: str) -> str:
        # noinspection PyTypeChecker
        return QtWidgets.QApplication.translate("SQliteQueryView", text, None)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        self.slotFlush()
        super().showEvent(event)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        if not self._without_pt_ctrl and self._row_autoincrement_factor:
            self.ui_page_num.setRange(1, self._model.total_page)
            self._model.rows_per_page = self.ui_view.geometry().height() / self._row_autoincrement_factor

        super(SQliteQueryView, self).resizeEvent(event)

    def rowCount(self) -> int:
        return self._model.record_count

    def getTableData(self) -> typing.List:
        return self._model.get_table_data()

    def getPKFromRow(self, row) -> typing.Any:
        return self._get_pk_from_row(row)

    def enableDateSearch(self, enable: bool):
        self.ui_search_value.setHidden(enable)
        for element in self.ui_tools_manager.findValue(self.Group, self.ToolGroups.Date):
            if element.property(self.Group) == self.ToolGroups.Date:
                element.setVisible(enable)

    def updateQuery(self, keys: typing.Sequence[str]):
        self.model.keys = keys
        self.ui_view.setColumnStretchFactor(self.model.column_stretch)

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

    def slotFlush(self, scroll_to_end: bool = False):
        if self._without_pt_ctrl:
            # Without page turn ctrl always show all records
            self._model.show_all()
        else:
            self.ui_page_num.setRange(1, self._model.total_page)
            self.slotPageNumChanged(self.ui_page_num.value(), force=True)

        if scroll_to_end:
            if self.ui_page_num.value() != self._model.total_page:
                self.slotNext()

            self._tasklet.add_task(Task(lambda: self.signalRequestScrollToBottom.emit(), timeout=1.0))
        else:
            self._tasklet.add_task(Task(lambda: self.signalRequestScrollToTop.emit(), timeout=1.0))

    def slotClear(self, without_confirm: bool = False) -> bool:
        if not without_confirm and not showQuestionBox(
                self, self.tr('Confirm to clear all records ?'), self.tr('Clear Confirm')
        ):
            return False

        if self._model.clear_table():
            self.signalRecordsCleared.emit()
            self.slotFlush()
            return True

        return False

    def slotUpdate(self, pk: typing.Any, data: dict) -> bool:
        return self._model.update_record(pk, data)

    def slotAppend(self, record: dict, scroll_to_end: bool = True) -> bool:
        if self._model.insert_record(record):
            self.slotFlush(scroll_to_end)
            self.ui_view.selectRow(self._model.rowCount() - 1)
            return True

        return False

    def slotSearch(self):
        value = self.ui_search_value.currentText()
        if not value:
            self._model.show_all()
        else:
            key = self.ui_search_key.currentData(QtCore.Qt.UserRole)
            self._model.search_record(key, value, self._enable_fuzzy_search(key))

    def slotUpdateDateRange(self, _):
        k = self.ui_search_key.currentData(QtCore.Qt.UserRole)
        s = QtCore.QDateTime(self.ui_start_date.date(), QtCore.QTime(0, 0, 0)).toString(self._datetime_format)
        e = QtCore.QDateTime(self.ui_end_date.date(), QtCore.QTime(23, 59, 59)).toString(self._datetime_format)

        cond = f'WHERE {k} > "{s}" and {k} < "{e}"'
        cond = f'{cond} and {self._model.query_condition}' if self._model.query_condition else cond
        self.ui_search_value.setCurrentText(f'SELECT {self._model.columns_str} FROM {self._model.tbl_name} {cond}')

    def slotSearchKeyChanged(self, idx: int):
        if self._without_search:
            return

        if idx in self._precisely_search_columns:
            self.enableDateSearch(False)
            self.ui_search_value.clear()
            self.ui_search_value.setCurrentText('')
            self.ui_search_value.addItems(list(set(self._model.get_column_data(idx))))
        else:
            self.ui_search_value.clear()
            self.ui_search_value.setCurrentText('')
            self.enableDateSearch(idx in self._date_search_columns)
            # Update date search
            if idx in self._date_search_columns:
                self.slotUpdateDateRange('')

    def slotDelete(self, without_confirm: bool = False) -> bool:
        if not without_confirm and not showQuestionBox(
                self, self.tr('Confirm to delete this record ?'), self.tr('Delete Confirm')
        ):
            return False

        row = self.ui_view.getCurrentRow()
        primary_key = self._get_pk_from_row(row)
        if self._model.delete_record(primary_key):
            self.signalRecordDeleted.emit(primary_key)
            self.slotFlush()
            self.ui_view.selectRow(self._model.rowCount() - 1)
            return True

        return False

    def slotPageNumChanged(self, page, force: bool = False):
        self._model.flush_page(page - 1, force)

    def slotCustomContentMenu(self, pos: QtCore.QPoint):
        if not self._model.record_count:
            return

        if self._is_readonly and not self._custom_content_menu:
            return

        menu = QtWidgets.QMenu(self)
        if not self._is_readonly:
            menu.addAction(self.ui_action_del)
            menu.addAction(self.ui_action_clear)

        index = self.ui_view.indexAt(pos)
        custom_content_menu = [action for action, filter_ in self._custom_content_menu.items() if filter_(index)]

        if custom_content_menu:
            menu.addSeparator()
            menu.addActions(custom_content_menu)

        menu.popup(self.ui_view.viewport().mapToGlobal(pos))
