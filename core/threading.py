# -*- coding: utf-8 -*-
import threading
from typing import Any
__all__ = ['ThreadConditionWrap', 'ThreadLockAndDataWrap']


class ThreadConditionWrap(object):
    def __init__(self):
        self.__result = False
        self.__finished = False
        self.__condition = threading.Condition()

    def wait(self) -> bool:
        self.__finished = False
        with self.__condition:
            while not self.__finished:
                self.__condition.wait(1)

        return self.__result

    def reset(self):
        self.__result = False
        self.__finished = False

    def finished(self, result: bool):
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
