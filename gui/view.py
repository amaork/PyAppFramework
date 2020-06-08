# -*- coding: utf-8 -*-
from PySide.QtGui import *
from PySide.QtCore import *
from ..misc.windpi import get_program_scale_factor
__all__ = ['TableView']


class TableView(QTableView):
    def __init__(self, parent=None):
        super(TableView, self).__init__(parent)
        self.__autoHeight = False
        self.__columnStretchFactor = list()
        self.__scale_x, self.__scale_y = get_program_scale_factor()

    def hideHeaders(self, hide):
        self.hideRowHeader(hide)
        self.hideColumnHeader(hide)

    def hideRowHeader(self, hide):
        self.verticalHeader().setVisible(not hide)

    def hideColumnHeader(self, hide):
        self.horizontalHeader().setVisible(not hide)

    def getVerticalHeaderHeight(self):
        vertical_header = self.verticalHeader()
        return vertical_header.defaultSectionSize()

    def setVerticalHeaderHeight(self, height):
        vertical_header = self.verticalHeader()
        vertical_header.setResizeMode(QHeaderView.Fixed)
        vertical_header.setDefaultSectionSize(height)
        self.setVerticalHeader(vertical_header)

    def getHorizontalHeaderWidth(self):
        horizontal_header = self.horizontalHeader()
        return horizontal_header.defaultSectionSize()

    def setHorizontalHeaderWidth(self, width):
        horizontal_header = self.horizontalHeader()
        horizontal_header.setResizeMode(QHeaderView.Fixed)
        horizontal_header.setDefaultSectionSize(width)
        self.setHorizontalHeader(horizontal_header)

    def disableScrollBar(self, horizontal, vertical):
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

    def setAutoHeight(self, enable):
        self.__autoHeight = enable
        self.resize(self.geometry().width(), self.geometry().height())

    def setColumnStretchFactor(self, factors):
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
            self.setVerticalHeaderHeight(height / self.mode().rowCount())

        if len(self.__columnStretchFactor) == 0:
            super(TableView, self).resizeEvent(ev)
            return

        # Auto adjust table column width
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        for column, factor in enumerate(self.__columnStretchFactor):
            header.setResizeMode(column, QHeaderView.Fixed)
            self.setColumnWidth(column, width * factor)

    def getCurrentRow(self):
        model = self.model()
        if not isinstance(model, QAbstractItemModel):
            return 0

        return self.currentIndex().row()

    def setCurrentRow(self, row):
        model = self.model()
        if not isinstance(model, QAbstractItemModel):
            return False

        return self.setCurrentIndex(model.index(row, 0, QModelIndex()))

    def getTableData(self, role=Qt.DisplayRole):
        model = self.model()
        if not isinstance(model, QAbstractItemModel):
            return list()
        return [self.getRowData(row, role) for row in range(model.rowCount())]

    def setTableData(self, data, role=Qt.EditRole):
        model = self.model()
        if not isinstance(model, QAbstractItemModel):
            return False

        if not isinstance(data, list) or len(data) != model.rowCount():
            return False

        return sum([self.setRowData(row, data[row], role) for row in range(model.rowCount())]) == len(data)

    def getRowData(self, row, role=Qt.DisplayRole):
        model = self.model()
        if not isinstance(model, QAbstractItemModel):
            return list()

        return [self.getItemData(row, column, role) for column in range(model.columnCount())]

    def setRowData(self, row, data, role=Qt.EditRole):
        model = self.model()
        if not isinstance(model, QAbstractItemModel):
            return False

        if not isinstance(data, (list, tuple)) or len(data) != model.columnCount():
            return False

        return sum([self.setItemData(row, column, data[column], role)
                    for column in range(model.columnCount())]) == len(data)

    def getItemData(self, row, column, role=Qt.DisplayRole):
        model = self.model()
        if not isinstance(model, QAbstractItemModel):
            return ""

        return model.itemData(model.index(row, column, QModelIndex())).get(role)

    def setItemData(self, row, column, data, role=Qt.EditRole):
        model = self.model()
        if not isinstance(model, QAbstractItemModel):
            return False

        return model.setData(model.index(row, column, QModelIndex()), data, role)