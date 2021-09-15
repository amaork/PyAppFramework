# -*- coding: utf-8 -*-
import time
import threading
from typing import Optional, Callable, Any
from .threading import ThreadLockAndDataWrap
__all__ = ['SwTimer']


class SwTimer(object):
    def __init__(self, base: float = 1.0,
                 private: Any = None,
                 callback: Optional[Callable] = None,
                 cb_args: Optional[tuple] = None, cb_kwargs: Optional[dict] = None, auto_start: bool = False):
        """
        Software timer base on thread
        :param base: timer base interval unit second
        :param callback: timer callback
        :param cb_args: timer callback args (Notice: callback first arg always be the SwTimer itself)
        :param cb_kwargs: timer callback kwargs (Notice: callback kwargs always has a key named timer(SwTimer itself))
        :param auto_start: auto start the timer
        """
        self._base = base
        self._private = private
        self._cb_callback = callback
        self._cb_args = cb_args or ()
        self._cb_kwargs = cb_kwargs or dict()

        self._event = threading.Event()
        self._stop = ThreadLockAndDataWrap(False)
        self._timer_cnt = ThreadLockAndDataWrap(0)
        self._start_timestamp = time.perf_counter()
        self._is_running = ThreadLockAndDataWrap(auto_start)

        self._th = threading.Thread(target=self.__timer_thread, name="Software timer")
        self._th.setDaemon(True)
        self._th.start()

    def __del__(self):
        self.stop()

    def __timer_thread(self):
        while not self._stop:
            self._event.wait(self._base)
            if self._is_running:
                self.__callback()

    def __callback(self):
        self._timer_cnt.data += 1
        if not callable(self._cb_callback):
            return

        if self._cb_args:
            self._cb_callback(*(self, *self._cb_args))
        elif self._cb_kwargs:
            self._cb_callback(timer=self, **self._cb_kwargs)
        else:
            self._cb_callback(self)

    @property
    def cnt(self) -> int:
        return self._timer_cnt.data

    @property
    def private(self) -> Any:
        return self._private

    @private.setter
    def private(self, data: Any):
        self._private = data

    def stop(self):
        self._event.set()
        self._stop.data = True
        self._is_running.data = False

    def pause(self):
        self._is_running.data = False

    def reset(self):
        self._timer_cnt.data = 0

    def resume(self):
        self._is_running.data = True

    def wait(self, timeout: float):
        self._event.wait(timeout)

    def is_running(self) -> bool:
        return not self._stop and self._is_running.data

    def time_elapsed(self) -> float:
        return time.perf_counter() - self._start_timestamp if self.is_running() else 0.0

    def is_timeout(self, time_in_s: float) -> bool:
        return self.time_elapsed() >= time_in_s

    @staticmethod
    def singleShot(timeout: float,
                   callback: Optional[Callable] = None,
                   cb_args: Optional[tuple] = None, cb_kwargs: Optional[dict] = None):
        """
        Create a single shot SwTimer
        :param timeout: timer timeout in second
        :param callback: timer timeout callback
        :param cb_args: timer callback args
        :param cb_kwargs: timer callback kwargs
        :return:
        """
        def callback_wrapper(timer: SwTimer, *args, **kwargs):
            timer.stop()
            callback(*args, **kwargs)

        SwTimer(base=timeout, callback=callback_wrapper, cb_args=cb_args, cb_kwargs=cb_kwargs, auto_start=True)
