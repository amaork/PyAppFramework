# -*- coding: utf-8 -*-
import abc
import typing
from PySide2.QtCore import Qt
from PySide2 import QtSql, QtCore, QtGui
from ..core.database import SQLiteDatabase, DBTable
__all__ = ['AbstractTableModel', 'SqliteQueryModel', 'SqliteQueryModelWrap']


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

    def __init__(self, db_name: str, tbl_name: str, columns: typing.Sequence[str], pk_name: str = 'id',
                 is_autoincrement: bool = False, rows_per_page: int = 20, placeholder: str = '', verbose: bool = False,
                 parent: QtCore.QObject = None):
        # Create placeholder
        need_clear = False
        if not self.get_row_count(tbl_name):
            need_clear = True
            QtSql.QSqlQuery().exec_(placeholder)

        self._cur_page = 0
        self._verbose = verbose
        self._pk_name = pk_name
        self._db_name = db_name
        self._tbl_name = tbl_name
        self._rows_per_page = int(rows_per_page)
        self._is_autoincrement = is_autoincrement
        self._query_columns = ', '.join(columns) or '*'
        self._columns = list(columns) or list(SQLiteDatabase(self._db_name).getTableInfo(self._tbl_name).keys())
        super(SqliteQueryModel, self).__init__(parent)
        self.flush_page(self.cur_page)
        self.set_column_header()

        if need_clear:
            self.clear_table()

    @property
    def keys(self) -> typing.List[str]:
        return self._columns[:]

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
        return self.get_row_count(self._tbl_name)

    @property
    def display_columns(self) -> str:
        return self._query_columns

    @property
    @abc.abstractmethod
    def column_header(self) -> typing.Tuple[str, ...]:
        pass

    @property
    def rows_per_page(self) -> int:
        return self._rows_per_page

    @rows_per_page.setter
    def rows_per_page(self, rows_per_page: int):
        self._rows_per_page = int(rows_per_page)
        self.flush_page(self.cur_page, force=True)

    @property
    def autoincrement_id(self) -> int:
        if not self._is_autoincrement:
            return self.record_count

        query = QtSql.QSqlQuery()
        if query.exec_(f'SELECT seq FROM {self.SQLITE_SEQ_TBL_NAME} WHERE name = "{self._tbl_name}"') and query.first():
            return query.value(0)

        return self.record_count

    @staticmethod
    def get_row_count(tbl: str) -> int:
        query = QtSql.QSqlQuery()
        return query.value(0) if query.exec_(f'SELECT COUNT(*) FROM {tbl};') and query.first() else 0

    def get_column_data(self, column: int) -> typing.Sequence:
        try:
            column_name = self._columns[column]
        except IndexError:
            return []

        column_data = list()
        query = QtSql.QSqlQuery()
        query.setForwardOnly(True)
        if query.exec_(f'SELECT {column_name} FROM {self._tbl_name}') and query.isActive():
            while query.next():
                column_data.append(query.value(column_name))

        return column_data

    def set_column_header(self):
        for column, name in enumerate(self.column_header):
            self.setHeaderData(column, QtCore.Qt.Horizontal, name)

    def show_all(self):
        self.set_query(f'SELECT {self._query_columns} FROM {self._tbl_name};')

    def set_query(self, query: str):
        if self._verbose:
            print(query)
        self.setQuery(query)

    def clear_table(self) -> bool:
        query = QtSql.QSqlQuery()
        if query.exec_(f'DELETE FROM {self._tbl_name}'):
            if not self._is_autoincrement:
                return True

            if query.exec_(f'UPDATE {self.SQLITE_SEQ_TBL_NAME} SET seq = 0 WHERE name = "{self._tbl_name}";'):
                # Reset current page
                self.flush_page(0, force=True)
                return True

        return False

    def flush_page(self, page: int, force: bool = False):
        if page < self.total_page or force:
            self._cur_page = page
            start = page * self._rows_per_page
            limit = f'LIMIT {int(self._rows_per_page)} OFFSET {int(start)};'
            self.set_query(f'SELECT {self._query_columns} FROM {self._tbl_name} {limit}')

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
            self.flush_page(self.cur_page, force=True)
            return True

        return False

    def insert_record(self, record: typing.Tuple) -> bool:
        query = QtSql.QSqlQuery()
        keys = self._columns[1:] if self._is_autoincrement else self._columns[:]
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
        # Sql sentence select
        if 'select' in value.lower():
            self.set_query(value)
        else:
            condition = f'{key} like "%{value}%"' if like else f'{key} = "{value}"'
            self.set_query(f'SELECT {self._query_columns} FROM {self._tbl_name} WHERE {condition};')


class SqliteQueryModelWrap(SqliteQueryModel):
    def __init__(self, db_name: str, db_tbl: DBTable, parent: QtCore.QObject = None):
        self.tbl = db_tbl
        super().__init__(
            parent=parent,
            db_name=db_name, tbl_name=self.tbl.name, columns=self.tbl.display_columns(),
            is_autoincrement=self.tbl.is_autoincrement, placeholder=self.tbl.get_placeholder_sentence(),
        )

    @property
    def readonly(self) -> bool:
        return self.tbl.readonly

    @property
    def column_header(self) -> typing.Tuple[str, ...]:
        return self.tbl.columns_annotation()

    @property
    def column_stretch(self) -> typing.Tuple[float, ...]:
        return self.tbl.columns_stretch()
