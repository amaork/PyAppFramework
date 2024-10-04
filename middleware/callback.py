# -*- coding: utf-8 -*-
import os
import subprocess
from threading import Thread
from PySide2.QtWidgets import QWidget
from PySide2.QtCore import Qt, Signal, QObject

from ..gui.msgbox import *
from ..gui.mailbox import *
from ..protocol.upgrade import *

from ..misc.env import RunEnvironment
from ..misc.process import subprocess_startup_info
__all__ = ['QtGuiCallback', 'SoftwareUpdateCallback', 'SoftwareUpdateCheckCallback']


class QtGuiCallback(QObject):
    signalProgressHidden = Signal()
    signalProgressText = Signal(str)
    signalProgressPercentage = Signal(int)

    # Text, min, max, title, cancelable
    signalInitProgressBar = Signal(str, int, int, str, bool)

    def __init__(self, parent: QWidget, mail: UiMailBox, env: RunEnvironment):
        assert isinstance(parent, QWidget), "Parent type error"
        assert isinstance(mail, UiMailBox), "Mail type error"
        assert isinstance(env, RunEnvironment), "Env type error"
        super(QtGuiCallback, self).__init__()
        self._progress = mail.progressDialog
        self._parent = parent
        self.mail = mail
        self.env = env

        self.signalProgressHidden.connect(self._progress.slotHidden)
        self.signalInitProgressBar.connect(self.slotInitProgressBar)
        self.signalProgressPercentage.connect(self._progress.setProgress)
        self.signalProgressText.connect(lambda x: self._progress.setLabelText(x))

    def sendMail(self, mail):
        self.mail.send(mail)

    def showMessage(self, type_: str, content: str, title: str or None = None):
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


class SoftwareUpdateCallback(QtGuiCallback):
    def start(self):
        self.sendMail(StatusBarMail(Qt.blue, self.tr("Downloading software upgrade")))

    def stop(self):
        self.showMessage(MB_TYPE_INFO, title=self.tr("Download canceled"), content=self.tr("Software update canceled"))

    def success(self, release: GogsSoftwareReleaseDesc, path: str):
        try:
            if self.canceled():
                return

            subprocess.Popen("{}".format(release.name),
                             cwd=path, shell=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=subprocess_startup_info())
        except Exception as error:
            msg = self.tr("Launch software upgrade install package failed") + ": {}, ".format(error) + \
                  self.tr("please manual install!")
            os.system("start {}".format(path))
            self.showMessage(MB_TYPE_ERR, msg)

    def error(self, error: str = ""):
        self.showMessage(MB_TYPE_ERR, title=self.tr("Download failed"),
                         content=self.tr("Download software upgrade failed") + ": {}".format(error))

    def update(self, progress: float, info: str) -> bool:
        if self._progress.isCanceled():
            return False

        self.signalProgressPercentage.emit(progress)
        self.signalProgressText.emit(self.tr("Downloading") + ": {}".format(info))
        return True


class SoftwareUpdateCheckCallback(QtGuiCallback):
    def __init__(self, parent: QWidget, mail: UiMailBox, env: RunEnvironment, title: str = ""):
        super(SoftwareUpdateCheckCallback, self).__init__(parent, mail, env)
        self.__title = title
        self.__version = env.software_version

    def start(self):
        self.initProgressBar(self.tr("Checking please wait"), 0, 100, self.tr("Software update"), True)

    def stop(self):
        self.showMessage(MB_TYPE_INFO, self.tr("Do not found upgrade release"))

    def error(self, error):
        self.showMessage(MB_TYPE_ERR, self.tr("Download software upgrade failed") + ": {}".format(error))

    def success(self, client: GogsUpgradeClient, release_desc: GogsSoftwareReleaseDesc):
        if release_desc.version <= self.__version:
            return self.showMessage(MB_TYPE_INFO, self.tr("Currently version is newest version"))

        ver_info = " V{} ".format(release_desc.version)
        size_info = self.tr("Size") + ": {0:.2f}M".format(release_desc.size / 1024 ** 2)
        title = self.__title if self.__title else self.tr("Confirm Update to") + ver_info + size_info

        if not showQuestionBox(self._parent, content=release_desc.desc, title=title):
            msg = self.tr("Software update canceled")
            self.sendMail(StatusBarMail(Qt.blue, msg, 3))
            return self.showMessage(MB_TYPE_INFO, content=msg)

        # Prepare download software update package
        from ..middleware.routine import SoftwareUpdateRoutine
        update_routine = SoftwareUpdateRoutine(self.mail)
        update_routine.setCallback(SoftwareUpdateCallback(self._parent, self.mail, self.env))
        Thread(
            name="Software update", target=update_routine.run,
            kwargs=dict(client=client, release=release_desc), daemon=True
        ).start()
