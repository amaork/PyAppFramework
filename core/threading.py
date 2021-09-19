# -*- coding: utf-8 -*-
import threading
from typing import Any, Optional
__all__ = ['ThreadConditionWrap', 'ThreadLockAndDataWrap']


class ThreadConditionWrap(object):
    def __init__(self):
        self.__result = None
        self.__finished = False
        self.__condition = threading.Condition()

    def wait(self, timeout: Optional[float] = None) -> Any:
        with self.__condition:
            while not self.__finished:
                if not self.__condition.wait(timeout):
                    return None

        # Get result will clear the finished flag
        self.__finished = False
        return self.__result

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
