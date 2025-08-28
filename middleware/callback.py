# -*- coding: utf-8 -*-
import os
import typing
import subprocess
import collections
from threading import Thread
from PySide2.QtWidgets import QWidget
from PySide2.QtCore import Qt, Signal, QObject

from ..gui.msgbox import *
from ..gui.mailbox import *
from ..gui.misc import qtTranslateAuto
from ..gui.dialog import TextDisplayDialog, showFileImportDialog, showFileExportDialog

from ..protocol.upgrade import *
from ..misc.env import RunEnvironment
from ..core.datatype import CustomEvent
from ..misc.windpi import system_open_file
from ..misc.settings import BinarySettings
from ..core.threading import ThreadConditionWrap
from ..misc.process import subprocess_startup_info
from ..protocol.serialport import SerialTransferProtocol
__all__ = ['QtGuiCallback',
           'FileImportCallback', 'FileExportCallback',
           'BinarySettingsImportCallback', 'BinarySettingsExportCallback',
           'SoftwareUpdateCallback', 'SoftwareUpdateCheckCallback',
           'EmbeddedSoftwareUpdateCallback', 'EmbeddedSoftwareUpdateEvent',
           'DownloadGogsReleaseWithoutConfirmCallback']


class QtGuiCallback(QObject):
    signalProgressHidden = Signal()
    signalProgressText = Signal(str)
    signalProgressPercentage = Signal(int)

    # Text, min, max, title, cancelable
    signalInitProgressBar = Signal(str, int, int, str, bool)

    def __init__(self, parent: QWidget, mail: UiMailBox):
        assert isinstance(parent, QWidget), "Parent type error"
        assert isinstance(mail, UiMailBox), "Mail type error"
        super(QtGuiCallback, self).__init__()
        self._private_data = None
        self._progress = mail.progressDialog
        self._parent = parent
        self.mail = mail

        self.signalProgressHidden.connect(self._progress.slotHidden)
        self.signalInitProgressBar.connect(self.slotInitProgressBar)
        self.signalProgressPercentage.connect(self._progress.setProgress)
        self.signalProgressText.connect(lambda x: self._progress.setLabelText(x))

    def sendMail(self, mail):
        self.mail.send(mail)

    def setData(self, data: typing.Any):
        self._private_data = data

    def showQuestion(self, content: str, title: str):
        cond = ThreadConditionWrap()
        self.mail.send(QuestionBoxMail(content, title, cond))
        return cond.wait()

    def showMessage(self, type_: str, content: str, title: str = ''):
        self.mail.send(MessageBoxMail(type_, content, title))

    def initProgressBar(self, text: str = "",
                        min_: int = 0, max_: int = 100,
                        title: str = "", cancelable: bool = False):
        self.signalInitProgressBar.emit(text, min_, max_, title, cancelable)

    def slotInitProgressBar(self, text: str = "",
                            min_: int = 0, max_: int = 100, title: str = "", cancelable: bool = False):
        self._progress.setValue(1)
        self._progress.setLabelText(text)
        self._progress.setRange(min_, max_)
        self._progress.setCancelable(cancelable)

        if title:
            self._progress.setWindowTitle(title)

        self._progress.show()

    def canceled(self) -> bool:
        return self._progress.isCanceled()

    def start(self, *args, **kwargs):
        pass

    def stop(self, *args, **kwargs):
        pass

    def final(self, *_args, **_kwargs):
        self.signalProgressPercentage.emit(self._progress.maximum())
        self.signalProgressHidden.emit()
        self.sendMail(StatusBarMail(Qt.blue, ""))

    def error(self, *args, **kwargs):
        pass

    def update(self, *args, **kwargs) -> bool:
        pass

    def success(self, *args, **kwargs):
        pass

    def data(self) -> typing.Any:
        return self._private_data


class FileImportCallback(QtGuiCallback):
    def start(self, fmt: str, name: str = '', title: str = ''):
        self.setData(showFileImportDialog(self._parent, fmt, name, title))

    def error(self, error: str):
        self.showMessage(MB_TYPE_ERR, error, self.tr('Import failed'))

    def success(self, path: str):
        self.showMessage(MB_TYPE_INFO,  path, self.tr('Import success'))


class FileExportCallback(QtGuiCallback):
    def start(self, fmt: str, name: str = '', title: str = ''):
        self.setData(showFileExportDialog(self._parent, fmt, name, title))

    def error(self, error: str):
        self.showMessage(MB_TYPE_ERR, error, self.tr('Export failed'))

    def success(self, path: str):
        self.showMessage(MB_TYPE_INFO, path, self.tr('Export success'))


class BinarySettingsImportCallback(FileImportCallback):
    def __init__(self, parent: QWidget, mail: UiMailBox, file_cls: BinarySettings.__class__):
        super().__init__(parent, mail)
        self.__file_cls = file_cls
        self.__import_data = bytes()

    # noinspection PyMethodOverriding
    def tr(self, msg: str):
        return qtTranslateAuto(msg, self.__class__)

    def getImportData(self) -> bytes:
        return self.__import_data

    def process(self, export_path: str, cond: ThreadConditionWrap):
        result = False
        try:
            import_data = self.__file_cls.load(export_path)
        except OSError as e:
            showMessageBox(self, MB_TYPE_ERR, f'{e}', self.tr('Export failed'))
        else:
            if not self.showQuestion(self.tr('Are you sure to import this ?'), self.tr('Import confirm')):
                result = None
            else:
                result = True
                self.__import_data = import_data
        finally:
            cond.finished(result)


class BinarySettingsExportCallback(FileExportCallback):
    def __init__(self, parent: QWidget, mail: UiMailBox,
                 file_cls: BinarySettings.__class__, export_data: bytes = bytes()):
        super().__init__(parent, mail)
        self.__file_cls = file_cls
        self.__export_data = export_data

    # noinspection PyMethodOverriding
    def tr(self, msg: str):
        return qtTranslateAuto(msg, self.__class__)

    def setExportData(self, data: bytes):
        self.__export_data = data

    def process(self, export_path: str, cond: ThreadConditionWrap):
        result = False
        try:
            self.__file_cls.save(self.__export_data, export_path)
        except OSError as e:
            showMessageBox(self, MB_TYPE_ERR, f'{e}', self.tr('Export failed'))
        else:
            result = True
        finally:
            cond.finished(result)


class SoftwareUpdateCallback(QtGuiCallback):
    def __init__(self, parent: QWidget, mail: UiMailBox, env: RunEnvironment):
        super(SoftwareUpdateCallback, self).__init__(parent, mail)
        self.env = env

    def start(self):
        self.sendMail(StatusBarMail(Qt.blue, self.tr("Downloading software upgrade")))

    def stop(self):
        self.showMessage(MB_TYPE_INFO, title=self.tr("Download canceled"), content=self.tr("Software update canceled"))

    def success(self, release: GogsSoftwareReleaseDesc, path: str,
                start_update_callback: typing.Optional[typing.Callable[[bool, str], None]] = None):
        try:
            if self.canceled():
                return

            release_name = release.name
            if os.path.splitext(release.name)[-1] == '.encrypt':
                try:
                    release_name = release.name.replace('encrypt', 'exe')
                    self.env.decrypt_file(os.path.join(path, release.name), os.path.join(path, release_name))
                except ValueError as e:
                    self.showMessage(MB_TYPE_ERR, f'{e}', self.tr('Decrypt software upgrade failed'))
                    return
                finally:
                    os.unlink(os.path.join(path, release.name))

            if callable(start_update_callback):
                self.mail.send(CallbackFuncMail(start_update_callback, args=(True, os.path.join(path, release_name))))

            subprocess.Popen("{}".format(release_name),
                             cwd=path, shell=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=subprocess_startup_info())
        except Exception as error:
            msg = self.tr("Launch software upgrade install package failed") + ": {}, ".format(error) + \
                  self.tr("please manual install!")
            system_open_file(path)
            if callable(start_update_callback):
                self.mail.send(CallbackFuncMail(start_update_callback, args=(False, path)))
            self.showMessage(MB_TYPE_ERR, msg)

    def error(self, error: str = ""):
        self.showMessage(MB_TYPE_ERR, title=self.tr("Download failed"),
                         content=self.tr("Download software upgrade failed") + ": {}".format(error))

    def update(self, progress: float, info: str) -> bool:
        if self._progress.isCanceled():
            return False

        self.signalProgressPercentage.emit(progress)
        self._progress.setWindowTitle(self.tr('Download update'))
        self.signalProgressText.emit(self.tr("Downloading") + ": {}".format(info))
        return True


class SoftwareUpdateCheckCallback(QtGuiCallback):
    def __init__(self, parent: QWidget, mail: UiMailBox, env: RunEnvironment, title: str = ""):
        super(SoftwareUpdateCheckCallback, self).__init__(parent, mail)
        self.env = env
        self.__title = title
        self.__version = env.software_version

    def start(self):
        self.initProgressBar(self.tr("Checking please wait"), 0, 100, self.tr("Software update"), True)

    def stop(self):
        self.showMessage(MB_TYPE_INFO, self.tr("Do not found upgrade release"))

    def error(self, error):
        self.showMessage(MB_TYPE_ERR, self.tr("Download software upgrade failed") + ": {}".format(error))

    def success(self, client: GogsUpgradeClient, releases: typing.Sequence[GogsSoftwareReleaseDesc],
                start_update_callback: typing.Optional[typing.Callable[[bool, str], None]] = None):
        newest_release = releases[0]
        if newest_release.version <= self.__version:
            return self.showMessage(MB_TYPE_INFO, self.tr("Currently version is newest version"))

        ver_info = " V{} ".format(newest_release.version)
        size_info = self.tr("Size") + ": {0:.2f}M".format(newest_release.size / 1024 ** 2)
        title = self.__title if self.__title else self.tr("Confirm Update to") + ver_info + size_info

        middle_releases_desc = '\n'.join([x.desc for x in releases if x.version > self.__version])
        if not TextDisplayDialog.showContent(content=middle_releases_desc, title=title, parent=self._parent):
            msg = self.tr("Software update canceled")
            self.sendMail(StatusBarMail(Qt.blue, msg, 3))
            return self.showMessage(MB_TYPE_INFO, content=msg)

        # Prepare download software update package
        from ..middleware.routine import SoftwareUpdateRoutine
        update_routine = SoftwareUpdateRoutine(self.mail)
        update_routine.setCallback(SoftwareUpdateCallback(self._parent, self.mail, self.env))
        Thread(
            name="Software update", target=update_routine.run,
            kwargs=dict(client=client, release=newest_release, start_update_callback=start_update_callback), daemon=True
        ).start()


class EmbeddedSoftwareUpdateEvent(CustomEvent):
    Type = collections.namedtuple(
        'Type', 'UpdateProgress PostProcess WaitUpdateDone RebootDone RebootFail UpdateFail'
    )(*range(6))

    @classmethod
    def process(cls, value: int):
        return cls(type=cls.Type.UpdateProgress, data=value)

    @classmethod
    def reboot_done(cls):
        return cls(type=cls.Type.RebootDone)

    @classmethod
    def reboot_fail(cls):
        return cls(type=cls.Type.RebootFail)

    @classmethod
    def update_fail(cls,  result: str):
        return cls(type=cls.Type.UpdateFail, data=result)

    @classmethod
    def post_process(cls, st: int, error: str):
        if st == SerialTransferProtocol.State.Error:
            return cls.update_fail(error)
        elif st == SerialTransferProtocol.State.Done:
            return cls.reboot_fail() if 'failed' in error else cls.reboot_done()
        elif st == SerialTransferProtocol.State.Wait:
            return cls.wait_update_done(120.0)
        else:
            return cls(type=cls.Type.PostProcess, data=st)

    @classmethod
    def wait_update_done(cls, timeout: float):
        return cls(type=cls.Type.WaitUpdateDone, data=timeout)


class EmbeddedSoftwareUpdateCallback(QtGuiCallback):
    def __init__(self, parent: QWidget, mail: UiMailBox, success_msg: str = ''):
        super(EmbeddedSoftwareUpdateCallback, self).__init__(parent, mail)
        if success_msg:
            self.success_msg = success_msg
        else:
            self.success_msg = self.tr('Software update success, application already reboot')

    def start(self):
        self.initProgressBar(self.tr('Software updating, please wait......'), 0, 100, self.tr("Software update"), True)

    def final(self, *_args, **_kwargs):
        super(EmbeddedSoftwareUpdateCallback, self).final(*_args, **_kwargs)
        self.mail.send(ProgressBarMail(0))

    def update(self, ev: EmbeddedSoftwareUpdateEvent) -> bool:
        if ev.isEvent(EmbeddedSoftwareUpdateEvent.Type.UpdateProgress):
            self.signalProgressPercentage.emit(ev.data)
            self.signalProgressText.emit(self.tr('Software updating, please wait......'))
        elif ev.isEvent(EmbeddedSoftwareUpdateEvent.Type.WaitUpdateDone):
            self.signalProgressPercentage.emit(0)
            self.mail.send(ProgressBarMail.create(ev.data, content=self.tr('Updating, please wait...')))
        elif ev.isEvent(EmbeddedSoftwareUpdateEvent.Type.PostProcess):
            msg = {
                SerialTransferProtocol.State.Backup: self.tr('Backup data......'),
                SerialTransferProtocol.State.Verify: self.tr('Verifying data......'),
                SerialTransferProtocol.State.Encrypt: self.tr('Encrypting data......'),
                SerialTransferProtocol.State.Decrypt: self.tr('Decrypting data......'),
                SerialTransferProtocol.State.Compress: self.tr('Compressing data......'),
                SerialTransferProtocol.State.Decompress: self.tr('Decompressing data......'),
                SerialTransferProtocol.State.Update: self.tr('Updating application......'),
            }.get(ev.data)
            if msg:
                self.mail.send(WindowsTitleMail.progressBarLabel(msg))
        elif ev.isEvent(EmbeddedSoftwareUpdateEvent.Type.RebootDone):
            self.mail.send(ProgressBarMail(0))
            self.showMessage(MB_TYPE_INFO, self.success_msg)
        elif ev.isEvent(EmbeddedSoftwareUpdateEvent.Type.RebootFail):
            self.mail.send(ProgressBarMail(0))
            self.showMessage(MB_TYPE_WARN, self.tr('Software update success, application reboot failed'))
        elif ev.isEvent(EmbeddedSoftwareUpdateEvent.Type.UpdateFail):
            self.mail.send(ProgressBarMail(0))
            self.showMessage(MB_TYPE_ERR, self.tr('Software update failed') + f': {ev.data}')

        return True

    def success(self):
        return self.showMessage(MB_TYPE_INFO, self.tr('Software update success'))


class DownloadGogsReleaseWithoutConfirmCallback(QtGuiCallback):
    def __init__(self, parent: QWidget, mail: UiMailBox, name: str, callback: typing.Callable[[str], None]):
        super(DownloadGogsReleaseWithoutConfirmCallback, self).__init__(parent, mail)
        self.__name = name
        self.__callback = callback

    def start(self):
        self.initProgressBar(
            self.tr("Downloading please wait......"), 0, 100,
            self.tr("Download") + ": {}".format(self.__name), True
        )
        self.sendMail(StatusBarMail(Qt.blue, self.tr("Downloading") + ": {}".format(self.__name)))

    def stop(self):
        self.showMessage(
            MB_TYPE_INFO, title=self.tr("Download canceled"),
            content=self.__name + " " + self.tr("download canceled")
        )

    def error(self, error: str):
        self.showMessage(
            MB_TYPE_ERR, title=self.tr("Download failed"),
            content=self.__name + " " + self.tr("download failed") + ": {}".format(error)
        )

    def success(self, release: GogsSoftwareReleaseDesc, path: str):
        if self.canceled():
            return

        release.save(os.path.join(path, "{}.json".format(release.name)))
        if hasattr(self.__callback, "__call__"):
            self.sendMail(CallbackFuncMail(self.__callback, args=(os.path.join(path, release.name),)))

    def update(self, progress: int, info: str) -> bool:
        # noinspection PyUnresolvedReferences
        if self._progress.isCanceled():
            return False

        self.signalProgressPercentage.emit(progress)
        self.signalProgressText.emit(self.tr("Downloading") + ": {}".format(info))
        return True
