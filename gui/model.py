# -*- coding: utf-8 -*-
import abc
import PySide2.QtCore
from typing import Sequence, Optional, Any
from PySide2.QtCore import Qt, QModelIndex, QAbstractTableModel, QObject
__all__ = ['AbstractTableModel']


class AbstractTableModel(QAbstractTableModel):
    def __init__(self, headers: Sequence[str], row_count: int, parent: Optional[QObject] = None):
        super(AbstractTableModel, self).__init__(parent)
        self._row_count = row_count
        self._header = tuple(headers)
        self._data = {x: '' for x in range(self.rowCount())}

    def rowCount(self, parent: PySide2.QtCore.QModelIndex = QModelIndex) -> int:
        return self._row_count

    def columnCount(self, parent: PySide2.QtCore.QModelIndex = QModelIndex) -> int:
        return len(self._header)

    def headerData(self, section: int, orientation: PySide2.QtCore.Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._header[section]
        else:
            return super(QAbstractTableModel, self).headerData(section, orientation, role)

    def data(self, index: PySide2.QtCore.QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if role in (Qt.DisplayRole, Qt.EditRole):
            return self.getDisplay(index)
        elif role == Qt.TextAlignmentRole:
            return self.getAlignment(index)
        else:
            return None

    def setData(self, index: PySide2.QtCore.QModelIndex, value : Any, role: int = Qt.DisplayRole) -> bool:
        if index.row() < self.rowCount():
            self._data[index.row()] = value
            return True

        return False

    @abc.abstractmethod
    def getDisplay(self, index: QModelIndex) -> Any:
        pass

    def getAlignment(self, _index: QModelIndex) -> Any:
        return Qt.AlignCenter
