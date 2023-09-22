# -*- coding: utf-8 -*-
import abc
import json
import typing
import itertools
import collections
from PySide2.QtCore import Qt
from PySide2 import QtSql, QtCore, QtGui

from ..core.database import DBTable
__all__ = ['AbstractTableModel', 'SqliteQueryModel', 'Rect', 'q2r', 'r2q']


Rect = collections.namedtuple('Rect', 'x y width height')


def q2r(q: QtCore.QRect) -> Rect:
    return Rect(q.x(), q.y(), q.width(), q.height())


def r2q(r: Rect) -> QtCore.QRect:
    return QtCore.QRect(*r)


class AbstractTableModel(QtCore.QAbstractTableModel):
    def __init__(self, parent: typing.Optional[QtCore.QObject] = None):
        super(AbstractTableModel, self).__init__(parent)
        self._user = list()
        self._table = list()
        self._header = tuple()

    def clearAll(self):
        c = self.rowCount()
        self._user.clear()
        self._table.clear()
        self.removeRows(0, c)
        self.dataChanged.emit(self.index(-1, -1), self.index(-1, -1))

    def item(self, _row: int, _column: int):
        return None

    def getLastIndex(self, column: int = 0) -> QtCore.QModelIndex:
        return self.index(self.rowCount() - 1, column)

    def getRowData(self, row: int, user: bool = False) -> typing.Sequence:
        try:
            src = self._user if user else self._table
            return [src[row][column] for column in range(self.columnCount())]
        except (IndexError, TypeError):
            return []

    def getColumnData(self, column: int, user: bool = False) -> typing.Sequence:
        try:
            src = self._user if user else self._table
            return [src[row][column] for row in range(self.rowCount())]
        except (IndexError, TypeError):
            return []

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._table)

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._header)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> typing.Any:
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._header[section]
        elif orientation == Qt.Horizontal and role == Qt.ForegroundRole:
            return self.getForeground(QtCore.QModelIndex())
        elif orientation == Qt.Horizontal and role == Qt.TextAlignmentRole:
            return self.getAlignment(QtCore.QModelIndex())
        else:
            return super(QtCore.QAbstractTableModel, self).headerData(section, orientation, role)

    def flags(self, index: QtCore.QModelIndex) -> QtCore.Qt.ItemFlags:
        flags = super(QtCore.QAbstractTableModel, self).flags(index)
        if not self.isReadonly(index):
            return flags | Qt.ItemIsEditable
        else:
            return super(QtCore.QAbstractTableModel, self).flags(index)

    def data(self, index: QtCore.QModelIndex, role: int = Qt.DisplayRole) -> typing.Any:
        if role in (Qt.DisplayRole, Qt.EditRole):
            return self.getDisplay(index)
        elif role == Qt.TextAlignmentRole:
            return self.getAlignment(index)
        elif role == Qt.BackgroundRole:
            return self.getBackground(index)
        elif role == Qt.ForegroundRole:
            return self.getForeground(index)
        elif role == Qt.UserRole and index.isValid():
            return self._user[index.row()][index.column()]
        else:
            return None

    def setData(self, index: QtCore.QModelIndex, value: typing.Any, role: int = Qt.DisplayRole) -> bool:
        if index.row() < self.rowCount():
            if role in (Qt.DisplayRole, Qt.EditRole):
                if self.setDisplay(index, value):
                    self.dataChanged.emit(index, index, role)
                    return True
                return False
            elif role == Qt.UserRole and index.isValid():
                self._user[index.row()][index.column()] = value
            else:
                return super(AbstractTableModel, self).setData(index, value, role)

        return False

    def appendRow(self, data: typing.Sequence[str], user: typing.Sequence[typing.Any] = None):
        self.insertRow(self.rowCount())
        row = self.rowCount() - 1
        user = user or list()

        for column, item in enumerate(itertools.zip_longest(data, user)):
            self.setData(self.index(row, column), item[0])
            self.setData(self.index(row, column), item[1], Qt.UserRole)

    def insertRows(self, row: int, count: int, parent: QtCore.QModelIndex = ...) -> bool:
        self.beginInsertRows(QtCore.QModelIndex(), row, row + count - 1)
        for idx in range(count):
            self._table.insert(row + idx, [''] * self.columnCount())
            self._user.insert(row + idx, [''] * self.columnCount())
        self.endInsertRows()
        return True

    def removeRows(self, row: int, count: int, parent: QtCore.QModelIndex = ...) -> bool:
        self.beginRemoveRows(QtCore.QModelIndex(), row, row + count - 1)
        del self._table[row: row + count]
        del self._user[row: row + count]
        self.endRemoveRows()
        return True

    def getBackground(self, index: QtCore.QModelIndex) -> QtGui.QColor:
        return QtGui.QColor(Qt.white)

    def getForeground(self, index: QtCore.QModelIndex) -> QtGui.QColor:
        return QtGui.QColor(Qt.black)

    def getAlignment(self, index: QtCore.QModelIndex) -> Qt.AlignmentFlag:
        return Qt.AlignCenter

    def getDisplay(self, index: QtCore.QModelIndex) -> typing.Any:
        return self._table[index.row()][index.column()] if index.isValid() else False

    def setDisplay(self, index: QtCore.QModelIndex, value: typing.Any) -> bool:
        if index.isValid():
            self._table[index.row()][index.column()] = value
            return True

        return False

    @abc.abstractmethod
    def isReadonly(self, index: QtCore.QModelIndex) -> bool:
        pass


class SqliteQueryModel(QtSql.QSqlQueryModel):
    SQLITE_SEQ_TBL_NAME = 'sqlite_sequence'

    def __init__(self, db_name: str, tbl: DBTable,
                 display_columns: typing.Sequence[str] = None, condition: str = '',
                 rows_per_page: int = 20, verbose: bool = False, parent: QtCore.QObject = None):
        self.tbl = tbl
        self._cur_page = 0
        self._verbose = verbose
        self._db_name = db_name
        self._rows_per_page = int(rows_per_page)

        self._columns = display_columns or self.tbl.display_columns()
        self._condition = condition
        super(SqliteQueryModel, self).__init__(parent)

        # Create placeholder
        need_clear = False
        if not self.get_row_count(tbl.name):
            need_clear = True
            self.set_query(self.tbl.get_placeholder_sentence())

        self.flush_page(self.cur_page)
        self.set_column_header()

        if need_clear:
            self.clear_table()

    @property
    def keys(self) -> typing.List[str]:
        return self._columns[:]

    @keys.setter
    def keys(self, keys: typing.Sequence[str]):
        try:
            self._columns = [k for k in keys if k in self.tbl.display_columns()]
        except TypeError:
            pass
        else:
            self.set_column_header()
            self.show_all()

    @property
    def tbl_name(self) -> str:
        return self.tbl.name

    @property
    def cur_page(self) -> int:
        return self._cur_page

    @property
    def total_page(self) -> int:
        if not self._rows_per_page:
            return 1

        row_count = self.record_count
        ext_page = 1 if row_count % self._rows_per_page else 0
        return self.record_count // self._rows_per_page + ext_page

    @property
    def record_count(self) -> int:
        return self.get_row_count(self.tbl.name)

    @property
    def query_condition(self) -> str:
        return self._condition

    @query_condition.setter
    def query_condition(self, condition: str):
        self._condition = condition
        self.show_all()

    @property
    def columns_str(self) -> str:
        return ', '.join(self._columns)

    @property
    def readonly(self) -> bool:
        return self.tbl.readonly

    @property
    def column_header(self) -> typing.Tuple[str, ...]:
        return tuple([self.tbl.get_column_annotate_from_name(x) for x in self._columns])

    @property
    def column_stretch(self) -> typing.Tuple[float, ...]:
        return tuple([self.tbl.get_column_from_name(x).stretch for x in self._columns])

    @property
    def date_search_columns(self) -> typing.List[int]:
        return self.tbl.get_timestamp_columns()

    @property
    def precisely_search_columns(self) -> typing.List[int]:
        return self.tbl.get_enumeration_columns()

    @property
    def rows_per_page(self) -> int:
        return self._rows_per_page

    @rows_per_page.setter
    def rows_per_page(self, rows_per_page: int):
        self._rows_per_page = int(rows_per_page)
        self.flush_page(self.cur_page, force=True)

    @property
    def autoincrement_id(self) -> int:
        if not self.tbl.is_autoincrement:
            return self.record_count

        query = QtSql.QSqlQuery()
        if query.exec_(f'SELECT seq FROM {self.SQLITE_SEQ_TBL_NAME} WHERE name = "{self.tbl_name}"') and query.first():
            return query.value(0)

        return self.record_count

    @staticmethod
    def get_row_count(tbl: str) -> int:
        query = QtSql.QSqlQuery()
        return query.value(0) if query.exec_(f'SELECT COUNT(*) FROM {tbl};') and query.first() else 0

    @staticmethod
    def format_blob_data(data: typing.Any) -> str:
        return f"'{json.dumps(data, ensure_ascii=False)}'"

    def is_support_fuzzy_search(self, key: str) -> bool:
        return self.tbl.get_column_index_from_name(key) in self.tbl.get_fuzzy_columns()

    def get_column_data(self, column: int) -> typing.Sequence:
        try:
            column_name = self._columns[column]
        except IndexError:
            return []

        column_data = list()
        query = QtSql.QSqlQuery()
        query.setForwardOnly(True)
        if query.exec_(f'SELECT {column_name} FROM {self.tbl_name}') and query.isActive():
            while query.next():
                column_data.append(query.value(column_name))

        return column_data

    def set_column_header(self):
        for column, name in enumerate(self.column_header):
            self.setHeaderData(column, QtCore.Qt.Horizontal, name)

    def show_all(self):
        cond = f' WHERE {self._condition}' if self._condition else ''
        self.set_query(f'SELECT {self.columns_str} FROM {self.tbl_name}{cond};')

    def set_query(self, query: str):
        if self._verbose:
            print(query)
        self.setQuery(query)

    def exec_query(self, query: str) -> typing.Tuple[bool, QtSql.QSqlQuery]:
        if self._verbose:
            print(query)

        query_obj = QtSql.QSqlQuery()
        query_result = query_obj.exec_(query) and query_obj.isActive()

        if self._verbose:
            print(query_obj.lastError().text())

        return query_result, query_obj

    def clear_table(self) -> bool:
        query = QtSql.QSqlQuery()
        if query.exec_(f'DELETE FROM {self.tbl_name}'):
            if query.exec_(f'UPDATE {self.SQLITE_SEQ_TBL_NAME} SET seq = 0 WHERE name = "{self.tbl_name}";'):
                # Reset current page
                self._cur_page = 0
                return True

        return False

    def flush_page(self, page: int, force: bool = False):
        if page < self.total_page or force:
            self._cur_page = page

            if not self._rows_per_page:
                self.show_all()
            else:
                start = page * self._rows_per_page
                limit = f' LIMIT {int(self._rows_per_page)} OFFSET {int(start)};'
                condition = f' WHERE {self._condition}' if self._condition else ''
                self.set_query(f'SELECT {self.columns_str} FROM {self.tbl_name}{condition}{limit}')

    def select_record(self, condition: str):
        record_value = list()
        query = QtSql.QSqlQuery()
        if query.exec_(f'SELECT * FROM {self.tbl_name} WHERE {condition};'):
            while query.next():
                values = list()
                record = query.record()
                for i in range(record.count()):
                    values.append(record.value(i))

                record_value.append(dict(zip(self.keys, values)))

        return record_value

    def delete_record(self, pk: typing.Any) -> bool:
        return self.exec_query(f'DELETE FROM {self.tbl_name} WHERE {self.tbl.pk} = {pk};')[0]

    def search_record(self, key: str, value: str, like: bool = False):
        # Sql sentence select
        if 'select' in value.lower():
            self.set_query(value)
        else:
            q = f' and {self._condition}' if self._condition else ''
            condition = f'{key} like "%{value}%"' if like else f'{key} = "{value}"'
            self.set_query(f'SELECT {self.columns_str} FROM {self.tbl_name} WHERE {condition}{q};')

    def insert_record(self, record: typing.Dict[str, typing.Any]) -> bool:
        return self.exec_query(self.tbl.get_inert_sentence(record))[0]

    def update_record(self, pk: typing.Any, record: typing.Dict[str, typing.Any]) -> bool:
        result, query = self.exec_query(self.tbl.get_update_sentence(record, f'{self.tbl.pk} = {pk}'))
        if result:
            self.flush_page(self.cur_page, force=True)
            return True

        return False

    def get_table_data(self) -> typing.List[typing.List]:
        return [
            [self.data(self.index(r, c), QtCore.Qt.DisplayRole) for c in range(self.columnCount())]
            for r in range(self.rowCount())
        ]
