# -*- coding: utf-8 -*-
import threading
from typing import Optional, Callable
from .threading import ThreadLockAndDataWrap
__all__ = ['SwTimer']


class SwTimer(object):
    def __init__(self, base: float = 1.0, callback: Optional[Callable] = None,
                 cb_args: Optional[tuple] = None, cb_kwargs: Optional[dict] = None, auto_start: bool = False):
        """

        :param base:
        :param callback:
        :param cb_args:
        :param cb_kwargs:
        :param auto_start:
        """
        self._base = base
        self._cb_callback = callback
        self._cb_args = cb_args or ()
        self._cb_kwargs = cb_kwargs or dict()

        self._event = threading.Event()
        self._stop = ThreadLockAndDataWrap(False)
        self._timer_cnt = ThreadLockAndDataWrap(0)
        self._is_running = ThreadLockAndDataWrap(auto_start)

        self._th = threading.Thread(target=self.__timer_thread, name="Software timer")
        self._th.setDaemon(True)
        self._th.start()

    def __del__(self):
        self.kill()

    def __timer_thread(self):
        while not self._stop:
            self._event.wait(self._base)
            if self._is_running:
                self.__callback()

    def __callback(self):
        self._timer_cnt.data += 1
        if not callable(self._cb_callback):
            return

        self._cb_callback(*self._cb_args, **self._cb_kwargs)

    @property
    def cnt(self) -> int:
        return self._timer_cnt.data

    def kill(self):
        self._event.set()
        self._stop.data = True
        self._is_running.data = False
        self._th.join()

    def pause(self):
        self._is_running.data = False

    def reset(self):
        self._timer_cnt.data = 0

    def resume(self):
        self._is_running.data = True

    def is_running(self) -> bool:
        return not self._stop and self._is_running.data

    def time_elapsed(self) -> float:
        return self._timer_cnt.data * self._base

    def is_timeout(self, time: float) -> bool:
        return self.time_elapsed() >= time
