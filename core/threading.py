# -*- coding: utf-8 -*-
import threading
from typing import *
__all__ = ['ThreadLockContentManager', 'ThreadConditionWrap', 'ThreadLockAndDataWrap']


class ThreadLockContentManager(object):
    def __init__(self, lock: threading.Lock):
        self.__lock = lock

    def __enter__(self):
        self.__lock.acquire(blocking=True)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__lock.release()


class ThreadConditionWrap(object):
    def __init__(self):
        self.__result = False
        self.__finished = False
        self.__condition = threading.Condition()

    def wait(self):
        self.__finished = False
        with self.__condition:
            while not self.__finished:
                self.__condition.wait(1)

        return self.__result

    def reset(self):
        self.__result = False
        self.__finished = False

    def finished(self, result):
        with self.__condition:
            self.__result = result
            self.__finished = True
            self.__condition.notify()


class ThreadLockAndDataWrap(object):
    def __init__(self, data: Any):
        self.__data = data
        self.__lock = threading.Lock()

    def __bool__(self):
        return bool(self.data)

    @property
    def data(self):
        with self.__lock:
            return self.__data

    @data.setter
    def data(self, data):
        with self.__lock:
            self.__data = data
