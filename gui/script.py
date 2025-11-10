# -*- coding: utf-8 -*-
import os
import abc
import typing
import threading
import collections
from PySide2 import QtCore, QtWidgets

from .view import *
from .msgbox import *
from .mailbox import *
from ..misc.settings import *
from .widget import BasicWidget
from ..gui.model import AbstractTableModel
from .misc import CustomTextEditor, qtTranslateAuto
from .dialog import showFileImportDialog, BasicDialog

__all__ = ['Script', 'BaseRemoteScriptModel', 'RemoteScriptSelectDialog', 'ScriptEditDebugView']
Script = collections.namedtuple('Script', 'name data')


class BaseRemoteScriptModel(AbstractTableModel):
    ColumnRole = collections.namedtuple('ColumnRole', 'Idx Script Delete Rename')(*range(4))

    @abc.abstractmethod
    def setScriptInfo(self, script_info: str):
        pass

    @abc.abstractmethod
    def getColumnRole(self, role: int) -> int:
        pass

    def getScriptName(self, row: int) -> str:
        return self.data(self.index(row, self.getColumnRole(self.ColumnRole.Script)))


class RemoteScriptModel(BaseRemoteScriptModel):
    Column = collections.namedtuple('Column', 'Idx Script Delete Rename')(*range(4))

    def __init__(self):
        super(RemoteScriptModel, self).__init__()
        self._header = (self.tr('Idx'), self.tr('Script Name'), self.tr('Delete'), self.tr('Rename'))
        # Script name using , split
        self.__script_info = ''

    def getColumnRole(self, role: int) -> int:
        return {
            self.ColumnRole.Script: self.Column.Script,
            self.ColumnRole.Delete: self.Column.Delete,
            self.ColumnRole.Rename: self.Column.Rename,
        }.get(role)

    def setScriptInfo(self, info: str):
        if not info:
            self.clearAll()
            self.__script_info = ''
        else:
            self.__script_info = info
            self._table = [
                [f'{i + 1}', s.strip(), 'Delete', 'Rename']
                for i, s in enumerate(info.split(','))
            ]
            self.layoutChanged.emit()
            self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount() - 1, self.columnCount() - 1))

    def isReadonly(self, index: QtCore.QModelIndex) -> bool:
        return True


class RemoteScriptSelectDialog(BasicDialog):
    def __init__(self, mailbox: UiMailBox, parent: QtWidgets.QWidget = None):
        self.ui_mail = mailbox
        threading.Thread(target=self.threadGetScriptInfo, daemon=True).start()
        super(RemoteScriptSelectDialog, self).__init__(parent)

    def _initUi(self):
        self.ui_view = TableView(True, parent=self)
        self.ui_delegate = TableViewDelegate(parent=self)
        self.ui_model = self._create_remote_script_model()
        self._delete_column = self.ui_model.getColumnRole(BaseRemoteScriptModel.ColumnRole.Delete)
        self._rename_column = self.ui_model.getColumnRole(BaseRemoteScriptModel.ColumnRole.Rename)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.ui_view)
        layout.addWidget(QtWidgets.QSplitter())
        layout.addWidget(self.ui_buttons)
        self.setLayout(layout)
        self.setWindowTitle(self.tr('Remote Script Select Dialog'))

    def _initData(self):
        self.ui_view.setModel(self.ui_model)
        self.ui_view.setItemDelegate(self.ui_delegate)
        self.ui_delegate.setColumnDelegate({
            self._delete_column: UiPushButtonInput(self.tr('Delete'), self.slotDelete),
            self._rename_column: UiPushButtonInput(self.tr('Rename'), self.slotRename),
        })

    def _initStyle(self):
        self.ui_view.hideRowHeader(True)
        self.ui_view.setRowSelectMode()
        self.ui_view.setColumnStretchFactor((0.1, 0.48, 0.21))

    def _initSignalAndSlots(self):
        self.ui_view.doubleClicked.connect(lambda _: self.accept())

    def sizeHint(self) -> QtCore.QSize:
        return QtCore.QSize(800, 400)

    # noinspection PyMethodOverriding
    def tr(self, text: str):
        return qtTranslateAuto(text, self.__class__)

    @abc.abstractmethod
    def _check_name(self, name: str) -> str:
        """Check if script is valid, invalid raise RuntimeError"""
        pass

    @abc.abstractmethod
    def _callback_get_script_info(self) -> str:
        """Get remote script info(name list)"""
        pass

    @abc.abstractmethod
    def _callback_del_script(self, name: str) -> bool:
        """Delete #name specified script"""
        pass

    @abc.abstractmethod
    def _callback_rename_script(self, old: str, new: str) -> bool:
        """Rename #old script name to #new name"""
        pass

    @abc.abstractmethod
    def _callback_get_script(self, name: str) -> typing.Optional[Script]:
        """Get #name specified script"""
        pass

    # noinspection PyMethodMayBeStatic
    def _create_remote_script_model(self) -> BaseRemoteScriptModel:
        return RemoteScriptModel()

    def slotDelete(self):
        script_name = self.ui_model.getScriptName(self.ui_view.getCurrentRow())
        if not showQuestionBox(self, self.tr('Are you sure to delete ?') + f' {script_name!r}'):
            return

        threading.Thread(target=self.threadDeleteAction, args=(script_name,), daemon=True).start()

    def slotRename(self):
        old_name = self.ui_model.getScriptName(self.ui_view.getCurrentRow())
        new_name, ret = QtWidgets.QInputDialog.getText(
            self, self.tr('Please enter new name'), self.tr('Name') + ' ' * 40, QtWidgets.QLineEdit.Normal, old_name
        )

        if not new_name or not ret:
            return

        if new_name == old_name:
            showMessageBox(self, MB_TYPE_WARN, self.tr('New name are same as old name'))
            return

        try:
            new_name = self._check_name(new_name)
        except RuntimeError as e:
            showMessageBox(self, MB_TYPE_WARN, f'{e}', self.tr('Script name error'))
            return

        threading.Thread(target=self.threadRenameAction, args=(old_name, new_name), daemon=True).start()

    def getData(self) -> typing.Optional[Script]:
        if not self.result() or not self.ui_model.rowCount():
            return None

        return self._callback_get_script(self.ui_model.getScriptName(self.ui_view.getCurrentRow()))

    def updateScriptInfo(self, info: str):
        self.ui_model.setScriptInfo(info)
        self.ui_view.setOpenPersistentEditor([self._delete_column, self._rename_column])

    def threadGetScriptInfo(self):
        try:
            script_info = self._callback_get_script_info()
        except ValueError as e:
            self.ui_mail.send(MessageBoxMail(MB_TYPE_ERR, f'{e}', self.tr('Decode script info fail')))
            return

        self.ui_mail.send(CallbackFuncMail(self.updateScriptInfo, args=(script_info,)))

    def threadDeleteAction(self, name: str):
        if self._callback_del_script(name):
            self.threadGetScriptInfo()

    def threadRenameAction(self, old: str, new: str):
        if self._callback_rename_script(old, new):
            self.threadGetScriptInfo()


class ScriptEditDebugView(BasicWidget):
    sourceProperty = 'source'
    Source = collections.namedtuple('Source', 'Local Remote')(*'local remote'.split())

    def __init__(self, comment_sign: str = '', parent: QtWidgets.QWidget = None):
        self.__comment_sign = comment_sign
        super().__init__(parent)

    def _initUi(self):
        self.ui_name = QtWidgets.QLineEdit()
        self.ui_run = QtWidgets.QPushButton(self.tr('Run'))
        self.ui_stop = QtWidgets.QPushButton(self.tr('Stop'))
        self.ui_load = QtWidgets.QPushButton(self.tr('Load'))
        self.ui_remote_save = QtWidgets.QPushButton(self.tr('Save to remote'))
        self.ui_remote_load = QtWidgets.QPushButton(self.tr('Load from remote'))
        self.ui_editor = CustomTextEditor(
            parent=self, comment_sign=self.__comment_sign, save_as_info=CustomTextEditor.SaveAsInfo(
                title=self.tr('Save script as'), format=self._format
            )
        )

        tool_layout = QtWidgets.QHBoxLayout()
        for item in (
                QtWidgets.QLabel(self.tr('Script name')), self.ui_name,
                self.ui_load, self.ui_remote_load, self.ui_remote_save, self.ui_run, self.ui_stop
        ):
            tool_layout.addWidget(item)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(tool_layout)
        layout.addWidget(self.ui_editor)
        self.setLayout(layout)

    def _initStyle(self):
        self.setRemoteConnected(False)
        self.ui_editor.setTabStopDistance(40)
        self.ui_editor.setAcceptRichText(False)
        self.setTabOrder(self.ui_name, self.ui_editor)

    def _initSignalAndSlots(self):
        self.ui_run.clicked.connect(self.slotRun)
        self.ui_stop.clicked.connect(self.slotStop)
        self.ui_load.clicked.connect(self.slotLoad)
        self.ui_editor.signalRequireSave.connect(self.slotSave)
        self.ui_remote_load.clicked.connect(self.slotRemoteLoad)
        self.ui_remote_save.clicked.connect(self.slotRemoteSave)

    @property
    @abc.abstractmethod
    def _format(self) -> str:
        pass

    @abc.abstractmethod
    def _check_name(self, name: str) -> str:
        """Check if script is valid, invalid raise RuntimeError"""
        pass

    @abc.abstractmethod
    def _callback_run(self, script: Script):
        """Clicked Run button will invoke this from thread"""
        pass

    @abc.abstractmethod
    def _callback_stop(self, script: Script):
        """Clicked Stop button will invoke this from thread"""
        pass

    @abc.abstractmethod
    def _callback_save_to_remote(self, script: Script):
        """Clicked Remote Save button will invoke this from thread"""
        pass

    @abc.abstractmethod
    def _callback_load_from_remote(self) -> typing.Optional[Script]:
        """Clicked Remote Load button will invoke this from thread"""
        pass

    def setRemoteConnected(self, connected: bool):
        self.ui_run.setVisible(connected)
        self.ui_remote_load.setVisible(connected)
        self.ui_remote_save.setVisible(connected)

    def getCurrentScript(self) -> typing.Optional[Script]:
        name = os.path.basename(self.ui_name.text().strip())
        script = self.ui_editor.toPlainText()
        if not script:
            return

        try:
            self._check_name(name)
        except RuntimeError as e:
            showMessageBox(self, MB_TYPE_WARN, f'{e}')
            return

        return Script(name=name, data=script.encode())

    def slotRun(self):
        script = self.getCurrentScript()
        if not script:
            return

        threading.Thread(target=self.threadRunScript, args=(script,), daemon=True).start()

    def slotStop(self):
        script = self.getCurrentScript()
        if not script:
            return

        threading.Thread(target=self.threadStopScript, args=(script,), daemon=True).start()

    def slotLoad(self):
        script_file = showFileImportDialog(self, self._format, '', title=self.tr('Please select script file'))

        if not script_file:
            return

        try:
            self._check_name(script_file)
        except RuntimeError as e:
            showMessageBox(self, MB_TYPE_WARN, f'{e}')
            return

        try:
            script_data = open(script_file, 'r', encoding='utf-8').read()
        except (OSError, ValueError) as e:
            showMessageBox(self, MB_TYPE_ERR, f'{e}')
            return

        self.ui_editor.clear()
        self.ui_editor.setPlainText(script_data)

        self.ui_name.setText(script_file)
        self.ui_name.setProperty(self.sourceProperty, self.Source.Local)

    def slotSave(self):
        try:
            self._check_name(self.ui_name.text().strip())
        except RuntimeError as e:
            showMessageBox(self, MB_TYPE_WARN, f'{e}')
            return

        if self.ui_name.property(self.sourceProperty) == self.Source.Local:
            self.ui_editor.slotSave(self.ui_name.text().strip())
        else:
            self._callback_save_to_remote(self.getCurrentScript())

    def slotRemoteLoad(self):
        script = self._callback_load_from_remote()
        if not isinstance(script, Script):
            return

        self.ui_editor.clear()
        self.ui_editor.setText(script.data.decode())

        self.ui_name.setText(script.name)
        self.ui_name.setProperty(self.sourceProperty, self.Source.Remote)

    def slotRemoteSave(self):
        script = self.getCurrentScript()
        if not script:
            return

        if not showQuestionBox(self, self.tr('Save to remote ?') + f' ({script.name})'):
            return

        threading.Thread(target=self.threadRemoteSave, args=(script,), daemon=True).start()

    def threadRunScript(self, script: Script):
        self._callback_run(script)

    def threadStopScript(self, script: Script):
        self._callback_stop(script)

    def threadRemoteSave(self, script: Script):
        self._callback_save_to_remote(script)
