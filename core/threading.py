# -*- coding: utf-8 -*-
import threading
import time
from typing import Any
__all__ = ['ThreadConditionWrap', 'ThreadLockAndDataWrap']


class ThreadConditionWrap(object):
    def __init__(self):
        self.__result = None
        self.__finished = False
        self.__condition = threading.Condition()

    def wait(self, timeout: float = -1) -> Any:
        self.__finished = False
        t0 = time.perf_counter()
        with self.__condition:
            while not self.__finished:
                self.__condition.wait(0.1)
                if time.perf_counter() - t0 >= timeout:
                    return None

        return self.__result

    def reset(self):
        self.__result = None
        self.__finished = False

    def finished(self, result: Any):
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
    def data(self) -> Any:
        with self.__lock:
            return self.__data

    @data.setter
    def data(self, data: Any):
        with self.__lock:
            self.__data = data
