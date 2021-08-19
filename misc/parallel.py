# -*- coding: utf-8 -*-
import abc
import time
import concurrent.futures
from threading import Thread
from typing import Callable, Optional
from .settings import UiLogMessage
__all__ = ['ParallelOperate', 'ConcurrentLauncher', 'BackgroundOperateLauncher']


class ParallelOperate(object):
    CACHE_EXCEPTIONS = ()
    LOG_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

    def __init__(self,
                 logging: Optional[Callable[[UiLogMessage], None]] = None,
                 callback: Optional[Callable] = None):
        self._logging = logging
        self._callback = callback

    @abc.abstractmethod
    def _operate(self, *args, **kwargs):
        pass

    def run(self, *args, **kwargs):
        try:
            result = self._operate(*args, **kwargs)
        except Exception as e:
            result = f'{e}'
            print(f'{self.__class__.__name__!r} operate error: {e}')
            self.errorLogging(f'{self.__class__.__name__!r} operate error: {e}')

        self.callback(result, *args)
        return result

    def callback(self, result, *args):
        if not callable(self._callback):
            return

        try:
            self._callback(result, *args)
        except TypeError as e:
            self.errorLogging(f'{self.__class__.__name__!r} callback error: {e}')

    def logging(self, msg: UiLogMessage):
        """Show message on gui

        :param msg: msg content
        :return:
        """
        if callable(self._logging) and isinstance(msg, UiLogMessage):
            self._logging(msg)

    def infoLogging(self, content: str):
        self.logging(UiLogMessage.genDefaultInfoMessage(
            "{} {}".format(time.strftime(self.LOG_TIME_FORMAT), content)
        ))

    def debugLogging(self, content: str):
        self.logging(UiLogMessage.genDefaultDebugMessage(
            "{} {}".format(time.strftime(self.LOG_TIME_FORMAT), content)
        ))

    def errorLogging(self, content: str):
        self.logging(UiLogMessage.genDefaultErrorMessage(
            "{} {}".format(time.strftime(self.LOG_TIME_FORMAT), content)
        ))


class ConcurrentLauncher(object):
    def __init__(self, operate: ParallelOperate, max_workers: Optional[int] = None, daemon: bool = False):
        if not isinstance(operate, ParallelOperate):
            raise TypeError("operate require a {!r}".format(ParallelOperate.__name__))

        self.__daemon = daemon
        self.__operate = operate
        self.max_workers = max_workers

    def run(self, args_list):
        th = Thread(target=self.concurrentRun, kwargs=dict(args_list=args_list))
        th.setDaemon(self.__daemon)
        th.start()

    def concurrentRun(self, args_list):
        with concurrent.futures.ThreadPoolExecutor(self.max_workers) as executor:
            [executor.submit(self.__operate.run, *args) for args in args_list]


class BackgroundOperateLauncher(object):
    def __init__(self, operate: ParallelOperate):
        if not isinstance(operate, ParallelOperate):
            raise TypeError("operate require a {!r}".format(ParallelOperate.__name__))

        self.__operate = operate

    def run(self, *args, **kwargs):
        th = Thread(target=self.__operate.run, args=args, kwargs=kwargs)
        th.start()
