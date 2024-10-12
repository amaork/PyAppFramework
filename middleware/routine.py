# -*- coding: utf-8 -*-
import ping3
import tempfile
import urllib.parse
from typing import *

from ..protocol.upgrade import *
from .callback import QtGuiCallback
from ..misc.env import RunEnvironment
from ..gui.mailbox import UiMailBox, CallbackFuncMail
from ..network.gogs_request import GogsRequestException
__all__ = ['Routine',
           'SoftwareUpdateRoutine', 'SoftwareUpdateCheckRoutine', 'DownloadGogsReleaseWithoutConfirmRoutine']


class Routine(object):
    Exceptions = (RuntimeError,)

    # noinspection PyShadowingNames
    def __init__(self, mail: UiMailBox,
                 start: Callable or None = None, stop: Callable or None = None,
                 final: Callable or None = None, success: Callable or None = None,
                 error: Callable or None = None, update: Callable or None = None, canceled: Callable or None = None):
        if not isinstance(mail, UiMailBox):
            raise RuntimeError("Do not found UiMailBox")

        self.__mail = mail
        self.__stop = stop
        self.__start = start
        self.__error = error
        self.__final = final
        self.__update = update
        self.__success = success
        self.__canceled = canceled

    def _stop(self, *args, **kwargs):
        hasattr(self.__stop, "__call__") and \
            self.__mail.send(CallbackFuncMail(self.__stop, args=args, kwargs=kwargs))

    def _start(self, *args, **kwargs):
        hasattr(self.__start, "__call__") and \
            self.__mail.send(CallbackFuncMail(self.__start, args=args, kwargs=kwargs))

    def _final(self, *args, **kwargs):
        hasattr(self.__final, "__call__") and \
            self.__mail.send(CallbackFuncMail(self.__final, args=args, kwargs=kwargs))

    def _error(self, *args, **kwargs):
        hasattr(self.__error, "__call__") and \
            self.__mail.send(CallbackFuncMail(self.__error, args=args, kwargs=kwargs))

    def _success(self, *args, **kwargs):
        hasattr(self.__success, "__call__") and \
            self.__mail.send(CallbackFuncMail(self.__success, args=args, kwargs=kwargs))

    def _routine(self, *args, **kwargs):
        pass

    def run(self, *args, **kwargs):
        try:
            self._routine(*args, **kwargs)
        except self.Exceptions as err:
            self._error(err)
        finally:
            self._final()

    def update(self, *args, **kwargs):
        return self.__update(*args, **kwargs) if hasattr(self.__update, "__call__") else True

    def isCanceled(self) -> bool:
        return self.__canceled() if hasattr(self.__canceled, "__call__") else False

    def setCallback(self, callback: QtGuiCallback):
        assert isinstance(callback, QtGuiCallback), "Callback type error"
        self.__stop = callback.stop
        self.__start = callback.start
        self.__error = callback.error
        self.__final = callback.final
        self.__update = callback.update
        self.__success = callback.success
        self.__canceled = callback.canceled

    @classmethod
    def createFromCallback(cls, callback: QtGuiCallback):
        return cls(
            mail=callback.mail,

            stop=callback.stop,
            start=callback.start,
            final=callback.final,

            error=callback.error,
            success=callback.success,

            update=callback.update,
            canceled=callback.canceled
        )


class SoftwareUpdateRoutine(Routine):
    def _routine(self, client: GogsUpgradeClient, release: GogsSoftwareReleaseDesc):
        temp_dir = tempfile.gettempdir()

        self._start()

        try:
            if not client.download_release(release=release, path=temp_dir, callback=self.update):
                if self.isCanceled():
                    self._stop()
                else:
                    self._error()
            else:
                self._success(release, temp_dir)
        except GogsUpgradeClientDownloadError as e:
            self._error("{}".format(e))


class SoftwareUpdateCheckRoutine(Routine):
    def _routine(self, env: RunEnvironment):
        if not isinstance(env, RunEnvironment):
            raise RuntimeError("[SoftwareUpdateCheckRoutine]: invalid software running environment")

        try:
            # noinspection PyTypeChecker
            if not ping3.ping(urllib.parse.urlparse(env.gogs_server_url).netloc.split(":")[0]):
                raise RuntimeError("Network error")
        except OSError as e:
            raise RuntimeError(e)

        try:
            self._start()
            client = env.get_gogs_update_client()
            releases = client.get_releases()

            if not releases or any(not release.check() for release in releases):
                self._stop()
            else:
                self._success(client, releases)
        except (GogsUpgradeClientDownloadError, GogsRequestException) as e:
            self._error("{}".format(e))


class DownloadGogsReleaseWithoutConfirmRoutine(Routine):
    def _routine(self, env: RunEnvironment, repo: str, path: str):
        if not ping3.ping(urllib.parse.urlparse(env.gogs_server_url).netloc.split(":")[0]):
            raise RuntimeError("Network error")

        try:
            self._start()
            client = env.get_gogs_update_client(repo)
            releases = client.get_releases()
            release = releases[0] if releases else None

            if not isinstance(release, GogsSoftwareReleaseDesc) or not release.check():
                self._stop()
                return

            if not client.download_release(release=release, path=path, callback=self.update):
                if self.isCanceled():
                    self._stop()
                else:
                    self._error("Download error")
            else:
                self._success(release, path)
        except Exception as e:
            self._error("{}".format(e))
