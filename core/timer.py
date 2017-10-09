# -*- coding: utf-8 -*-
import threading

__all__ = ['SwTimer']


class SwTimer(object):
    def __init__(self, base=1, callback=None, args=None):
        """Software timer

        :param self:
        :param base: base interval unit second
        :param callback: timer callback function
        :param args: callback function args
        :return:
        """
        self.args = args
        self.base = base
        self.callback = callback

        self.timer_cnt = 0
        self.lock = threading.RLock()
        self.timer = threading.Timer(self.base, self.__callback)

    def __callback(self):
        self.lock.acquire()
        self.timer_cnt += 1
        if self.callback and hasattr(self.callback, "__call__"):
            if self.args:
                self.callback(self.args)
            else:
                self.callback()
        self.timer = threading.Timer(self.base, self.__callback)
        self.lock.release()
        self.timer.start()

    def is_timeout(self, time):
        self.lock.acquire()
        timeout = self.timer_cnt >= time
        self.lock.release()
        return timeout

    def reset(self):
        self.lock.acquire()
        self.timer_cnt = 0
        self.lock.release()

    def start(self):
        if not self.timer.isAlive():
            self.timer.start()

    def stop(self):
        if self.timer.isAlive():
            self.timer.cancel()
