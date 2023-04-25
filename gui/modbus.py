# -*- coding: utf-8 -*-
import typing
import collections
from PySide2.QtCore import Qt
from PySide2 import QtWidgets, QtCore

from .model import AbstractTableModel
from .view import TableView, TableViewDelegate
from ..core.datatype import DynamicObject, str2number
from ..misc.settings import UiCheckBoxInput, UiIntegerInput, UiDoubleInput

from ..protocol.modbus import DataType, DataConvert, DataFormat, DataPresent, \
    WriteRequest, ReadResponse, Address, Table, FuncCode, helper_get_func_code
__all__ = ['ModbusAddressModel', 'ModbusAddressView', 'ModbusWriteRequest']
ModbusWriteRequest = collections.namedtuple('ModbusWriteRequest', 'name fc request')


class ModbusAddressModel(AbstractTableModel):
    # Table name, function code, ModbusWriteRequest
    signalWriteRequest = QtCore.Signal(object, object, object)
    Column = collections.namedtuple('Column', 'Name Address Type State Desc')(*range(5))

    def __init__(self, table: Table, parent: QtWidgets.QWidget = None):
        super(ModbusAddressModel, self).__init__(parent=parent)
        self._header = (self.tr('Name'), self.tr('Modbus Address'), self.tr('R/W'), self.tr('State'), self.tr('Desc'))

        self.table = table
        self._address_list = list()
        self.dc = DataConvert(table.endian)
        self.fc = helper_get_func_code(table.type)
        for name, address in table.address_list.items():
            address = Address(**address)
            self._table.append([name, f'{address.ma}', ('R/W', 'RD')[address.ro], 0, address.annotate])
            self._user.append([address])
            self._address_list.append(address)

    @property
    def address_list(self) -> typing.List[Address]:
        return self._address_list

    def getModbusAddressAndRow(self, address: int) -> typing.Tuple[int, typing.Optional[Address]]:
        for row, attr in enumerate(self._address_list):
            if attr.ma == address:
                return row, attr

        return -1, None

    def getModbusAddress(self, index: QtCore.QModelIndex) -> typing.Optional[Address]:
        return self.data(self.index(index.row(), 0), Qt.UserRole) if index.isValid() else None

    def getValueByAddress(self, address: int) -> typing.Tuple[QtCore.QModelIndex, typing.Any]:
        try:
            row = [str2number(x) for x in self.getColumnData(self.Column.Address)].index(address)
        except ValueError:
            return QtCore.QModelIndex(), None
        else:
            index = self.index(row, self.Column.State)
            return index, self.getDisplay(index)

    def updateDisplay(self, response: ReadResponse):
        row, address = self.getModbusAddressAndRow(response.request.start)
        if not isinstance(address, DynamicObject):
            return

        if DataConvert.get_format_size(address.format) == 2:
            value = self.dc.plc2python(response.data, address.format)
            self.setDisplay(self.index(row, self.Column.State), value, flush=False)
        else:
            for i in range(response.request.count):
                try:
                    self.setDisplay(self.index(row + i, self.Column.State), response.data[i], flush=False)
                except (ValueError, IndexError, AttributeError):
                    continue

        # Flush whole table
        self.dataChanged.emit(self.index(-1, -1), self.index(-1, -1), Qt.DisplayRole)

    def isReadonly(self, index: QtCore.QModelIndex) -> bool:
        if index.column() != self.Column.State:
            return True

        attr = self.getModbusAddress(index)
        return attr.ro if isinstance(attr, DynamicObject) else True

    def getDisplay(self, index: QtCore.QModelIndex) -> typing.Any:
        return self._table[index.row()][index.column()] if index.isValid() else False

    def setDisplay(self, index: QtCore.QModelIndex, value: typing.Any, flush: bool = True) -> bool:
        if not index.isValid():
            return False

        attr = self.getModbusAddress(index)
        if not isinstance(attr, DynamicObject):
            return False

        self._table[index.row()][index.column()] = f'{value:.4f}' if attr.format == DataFormat.float else value

        if not self.isReadonly(index) and index.column() == self.Column.State:
            data = self.dc.python2plc(value, attr.format)
            function_code = self.fc.wr if value == data else self.fc.mwr
            address = str(self.data(self.index(index.row(), self.Column.Address)))

            if self.table.type != DataType.Bit:
                address = int(address)

            if flush:
                self.signalWriteRequest.emit(
                    self.table.name, function_code, WriteRequest(self.table.type, address, data)
                )
        return True


class ModbusAddressView(QtWidgets.QTabWidget):
    # Table name, function code, ReadRequest list
    signalReadRequest = QtCore.Signal(object, object, object)

    # Table name, function code, WriteRequest
    signalWriteRequest = QtCore.Signal(object, object, object)

    def __init__(self, parent: QtWidgets.QWidget = None):
        self.models = dict()
        self._timer_cnt = 0
        super(ModbusAddressView, self).__init__(parent)
        self.startTimer(1000)

    def getModel(self, name: str) -> typing.Optional[ModbusAddressModel]:
        return self.models.get(name)

    def initAddressTables(self, tables: typing.Iterable[Table]):
        for table in tables:
            model = ModbusAddressModel(table, self)
            view = TableView(parent=self)

            view.setModel(model)
            view.setNoSelection()
            view.setColumnStretchFactor((0.25, 0.12, 0.12, 0.1))

            delegate = TableViewDelegate()
            if table.type in (DataType.Bit, DataType.Coil):
                delegate.setColumnDelegate({ModbusAddressModel.Column.State: UiCheckBoxInput(table.type)})
                view.setItemDelegate(delegate)

                for row in range(model.rowCount()):
                    # if model.isReadonly(model.index(row, model.Column.STATE)):
                    #     continue
                    view.openPersistentEditor(model.index(row, ModbusAddressModel.Column.State))

                for row in range(model.rowCount()):
                    index = model.index(row, model.Column.State)
                    if model.isReadonly(index):
                        view.frozenItem(row, index.column(), True)
            else:
                filter_ = dict()
                for row in range(model.rowCount()):
                    address = model.data(model.index(row, 0), Qt.UserRole)
                    if address.format in (DataFormat.uint16, DataFormat.uint32):
                        bits = DataConvert.get_format_size(address.format) * 16
                        input_ = UiIntegerInput(table.type, 0, maximum=(1 << bits) - 1)
                    else:
                        input_ = UiDoubleInput(table.type, -999999999.0, 999999999.0, decimals=4)
                    filter_[(row, ModbusAddressModel.Column.State)] = input_
                    # view.openPersistentEditor(model.index(row, ModbusAddressModel.Column.STATE))

                delegate.setItemDelegate(filter_)
                view.setItemDelegate(delegate)

            self.models[table.name] = model
            self.addTab(view, table.name)

    def slotHandleWriteRequest(self, table: str, fc: FuncCode, request: WriteRequest):
        if request.type != DataType.Bit:
            self.signalWriteRequest.emit(table, fc, request)
        else:
            reg_address, bit = [int(x) for x in request.address.split('/')]
            for model in self.ui_tab.models.values():
                index, reg_value = model.getValueByAddress(reg_address)
                if reg_value is not None:
                    if request.data:
                        reg_value |= (1 << bit)
                    else:
                        reg_value &= ~(1 << bit)

                    request = WriteRequest(type=DataType.Register, address=reg_address, data=reg_value)
                    model.setData(index, reg_value)

    def timerEvent(self, event: QtCore.QTimerEvent) -> None:
        if self.isHidden():
            return

        self._timer_cnt += 1
        for name, model in self.models.items():
            if not model.table.auto_flush:
                continue

            if self._timer_cnt % model.table.auto_flush:
                return

            self.signalReadRequest.emit(name, model.fc.rd, DataConvert.merge_read_request(model.address_list))
