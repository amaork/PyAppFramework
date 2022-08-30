# -*- coding: utf-8 -*-
import abc
import typing
from PySide2.QtCore import Qt
from PySide2 import QtSql, QtCore, QtGui
from ..core.database import SQLiteDatabase
__all__ = ['AbstractTableModel', 'SqliteQueryModel']


class AbstractTableModel(QtCore.QAbstractTableModel):
    def __init__(self, parent: typing.Optional[QtCore.QObject] = None):
        super(AbstractTableModel, self).__init__(parent)
        self._user = list()
        self._table = list()
        self._header = tuple()

    def clearAll(self):
        self.removeRows(0, self.rowCount())

    def item(self, _row: int, _column: int):
        return None

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
                return self.setDisplay(index, value)
            elif role == Qt.UserRole and index.isValid():
                self._user[index.row()][index.column()] = value
            else:
                return super(AbstractTableModel, self).setData(index, value, role)

        return False

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

    @abc.abstractmethod
    def getDisplay(self, index: QtCore.QModelIndex) -> typing.Any:
        pass

    @abc.abstractmethod
    def setDisplay(self, index: QtCore.QModelIndex, value: typing.Any) -> bool:
        pass

    @abc.abstractmethod
    def isReadonly(self, index: QtCore.QModelIndex) -> bool:
        pass


class SqliteQueryModel(QtSql.QSqlQueryModel):
    SQLITE_SEQ_TBL_NAME = 'sqlite_sequence'

    def __init__(self, db_name: str, tbl_name: str, pk_name: str = 'id',
                 is_autoincrement: bool = False, rows_per_page: int = 20, parent: QtCore.QObject = None):
        self._cur_page = 0
        self._pk_name = pk_name
        self._db_name = db_name
        self._tbl_name = tbl_name
        self._rows_per_page = rows_per_page
        self._is_autoincrement = is_autoincrement
        self._keys = list(SQLiteDatabase(self._db_name).getTableInfo(self._tbl_name).keys())
        super(SqliteQueryModel, self).__init__(parent)

    @property
    def keys(self) -> typing.List[str]:
        return self._keys[:]

    @property
    def tbl_name(self) -> str:
        return self._tbl_name[:]

    @property
    def cur_page(self) -> int:
        return self._cur_page

    @property
    def total_page(self) -> int:
        row_count = self.record_count
        ext_page = 1 if row_count % self._rows_per_page else 0
        return self.record_count // self._rows_per_page + ext_page

    @property
    def record_count(self) -> int:
        query = QtSql.QSqlQuery()
        return query.value(0) if query.exec_(f'SELECT COUNT(*) FROM {self._tbl_name};') and query.first() else 0

    @property
    def column_header(self) -> typing.List[str]:
        return [self.headerData(column, QtCore.Qt.Horizontal) for column in range(self.columnCount())]

    @property
    def rows_per_page(self) -> int:
        return self._rows_per_page

    @rows_per_page.setter
    def rows_per_page(self, rows_per_page: int):
        self._rows_per_page = rows_per_page
        self.flush_page(self.cur_page, force=True)

    @property
    def autoincrement_id(self) -> int:
        if not self._is_autoincrement:
            return self.record_count

        query = QtSql.QSqlQuery()
        if query.exec_(f'SELECT seq FROM {self.SQLITE_SEQ_TBL_NAME} WHERE name = "{self._tbl_name}"') and query.first():
            return query.value(0)

        return self.record_count

    def set_column_header(self, header: typing.Iterable):
        for column, name in enumerate(header):
            self.setHeaderData(column, QtCore.Qt.Horizontal, name)

    def show_all(self):
        self.setQuery(f'SELECT * FROM {self._tbl_name};')

    def clear_table(self) -> bool:
        query = QtSql.QSqlQuery()
        if query.exec_(f'DELETE FROM {self._tbl_name}'):
            if not self._is_autoincrement:
                return True

            if query.exec_(f'UPDATE {self.SQLITE_SEQ_TBL_NAME} SET seq = 0 WHERE name = "{self._tbl_name}";'):
                self.flush_page(self.cur_page, force=True)
                return True

        return False

    def flush_page(self, page: int, force: bool = False):
        if page < self.total_page or force:
            self._cur_page = page
            start = page * self._rows_per_page + self._is_autoincrement
            condition = f'{self._pk_name} >= {start} AND {self._pk_name} < {start + self._rows_per_page}'
            self.setQuery(f'SELECT * FROM {self._tbl_name} WHERE {condition};')

    def select_record(self, condition: str):
        record_value = list()
        query = QtSql.QSqlQuery()
        if query.exec_(f'SELECT * FROM {self._tbl_name} WHERE {condition};'):
            while query.next():
                values = list()
                record = query.record()
                for i in range(record.count()):
                    values.append(record.value(i))

                record_value.append(dict(zip(self.keys, values)))

        return record_value

    def delete_record(self, pk: typing.Any) -> bool:
        query = QtSql.QSqlQuery()
        if query.exec_(f'DELETE FROM {self._tbl_name} WHERE {self._pk_name} = {pk};'):
            self.flush_page(self.cur_page)
            return True

        return False

    def insert_record(self, record: typing.Tuple) -> bool:
        query = QtSql.QSqlQuery()
        keys = self._keys[1:] if self._is_autoincrement else self._keys[:]
        if query.exec_(f'INSERT INTO {self._tbl_name} {tuple(keys)} VALUES{tuple(record)}'):
            if self.rowCount() < self._rows_per_page:
                self.flush_page(self.cur_page)

            return True
        return False

    def update_record(self, pk: typing.Any, kv: str) -> bool:
        query = QtSql.QSqlQuery()
        if query.exec_(f'UPDATE {self._tbl_name} {kv} WHERE {self._pk_name} = {pk};'):
            self.flush_page(self.cur_page)
            return True

        print(query.lastError().text())
        return False

    def search_record(self, key: str, value: str, like: bool = False):
        condition = f'{key} like "%{value}%"' if like else f'{key} = {value}'
        self.setQuery(f'SELECT * FROM {self._tbl_name} WHERE {condition};')
