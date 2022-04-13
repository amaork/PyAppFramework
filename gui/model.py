# -*- coding: utf-8 -*-
import abc
import PySide2.QtCore
from typing import Optional, Any
from PySide2.QtGui import QColor
from PySide2.QtCore import Qt, QModelIndex, QAbstractTableModel, QObject
__all__ = ['AbstractTableModel']


class AbstractTableModel(QAbstractTableModel):
    def __init__(self, row_count: int, parent: Optional[QObject] = None):
        super(AbstractTableModel, self).__init__(parent)
        self._header = ()
        self._row_count = row_count
        self._data = [''] * self.rowCount()

    def rowCount(self, parent: PySide2.QtCore.QModelIndex = QModelIndex()) -> int:
        return self._row_count

    def columnCount(self, parent: PySide2.QtCore.QModelIndex = QModelIndex()) -> int:
        return len(self._header)

    def headerData(self, section: int, orientation: PySide2.QtCore.Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._header[section]
        else:
            return super(QAbstractTableModel, self).headerData(section, orientation, role)

    def flags(self, index: PySide2.QtCore.QModelIndex) -> PySide2.QtCore.Qt.ItemFlags:
        flags = super(QAbstractTableModel, self).flags(index)
        if not self.isReadonly(index):
            return flags | Qt.ItemIsEditable
        else:
            return super(QAbstractTableModel, self).flags(index)

    def data(self, index: PySide2.QtCore.QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if role in (Qt.DisplayRole, Qt.EditRole):
            return self.getDisplay(index)
        elif role == Qt.TextAlignmentRole:
            return self.getAlignment(index)
        elif role == Qt.BackgroundRole:
            return self.getBackground(index)
        elif role == Qt.ForegroundRole:
            return self.getForeground(index)
        else:
            return None

    def setData(self, index: PySide2.QtCore.QModelIndex, value: Any, role: int = Qt.DisplayRole) -> bool:
        if index.row() < self.rowCount():
            if role in (Qt.DisplayRole, Qt.EditRole):
                self._data[index.row()] = self.setDisplay(index, value)
                return True
            else:
                return super(AbstractTableModel, self).setData(index, value, role)

        return False

    def getBackground(self, index: QModelIndex) -> QColor:
        return QColor(Qt.white)

    def getForeground(self, index: QModelIndex) -> QColor:
        return QColor(Qt.black)

    def getAlignment(self, index: QModelIndex) -> Qt.AlignmentFlag:
        return Qt.AlignCenter

    @abc.abstractmethod
    def getDisplay(self, index: QModelIndex) -> Any:
        pass

    @abc.abstractmethod
    def setDisplay(self, index: QModelIndex, value: Any) -> Any:
        pass

    @abc.abstractmethod
    def isReadonly(self, index: QModelIndex) -> bool:
        pass
