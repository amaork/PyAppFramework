# -*- coding: utf-8 -*-
import threading
from typing import Any, Optional
__all__ = ['ThreadConditionWrap', 'ThreadLockAndDataWrap', 'ThreadSafeBool', 'ThreadSafeInteger']


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
        self._data = data
        self._lock = threading.Lock()

    def __bool__(self):
        return bool(self.data)

    @property
    def data(self) -> Any:
        with self._lock:
            return self._data

    @data.setter
    def data(self, data: Any):
        with self._lock:
            self._data = data

    def assign(self, data: Any):
        self.data = data


class ThreadSafeBool(ThreadLockAndDataWrap):
    def __init__(self, value: bool):
        if not isinstance(value, bool):
            raise TypeError('value must be a bool')
        super(ThreadSafeBool, self).__init__(value)

    def set(self):
        self.data = True

    def clear(self):
        self.data = False

    def is_set(self) -> bool:
        return self.data

    def reverse(self) -> bool:
        with self._lock:
            self._data = not self._data
            return self._data


class ThreadSafeInteger(ThreadLockAndDataWrap):
    def __init__(self, value: int):
        if not isinstance(value, int):
            raise TypeError('value must be an integer')
        super(ThreadSafeInteger, self).__init__(value)

    def reset(self):
        self.data = 0

    def increase(self) -> int:
        with self._lock:
            self._data += 1
            return self._data

    def decrease(self) -> int:
        with self._lock:
            self._data -= 1
            return self._data
