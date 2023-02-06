# -*- coding: utf-8 -*-
import threading
import contextlib
from typing import Any, Optional
__all__ = ['ThreadConditionWrap', 'ThreadLockAndDataWrap', 'ThreadSafeBool', 'ThreadSafeInteger', 'ThreadLockWithOwner']


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

    def reset(self):
        self.__finished = False


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

    def equal(self, right: Any) -> bool:
        return self.data == right


class ThreadSafeBool(ThreadLockAndDataWrap):
    def __init__(self, value: bool):
        if not isinstance(value, bool):
            raise TypeError('value must be a bool')
        super(ThreadSafeBool, self).__init__(value)
        self._preview_data = value

    @property
    def data(self) -> bool:
        with self._lock:
            return self._data

    @data.setter
    def data(self, data: bool):
        with self._lock:
            self._preview_data = self._data
            self._data = data

    @property
    def previous_data(self) -> bool:
        with self._lock:
            return self._preview_data

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

    def is_rising_edge(self) -> bool:
        return self.is_set() and not self._preview_data

    def is_falling_edge(self) -> bool:
        return not self.is_set() and self._preview_data


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


class ThreadLockWithOwner(object):
    def __init__(self, verbose: bool = False):
        self.__verbose = verbose
        self.__lock = threading.Lock()
        self.__owner = ThreadLockAndDataWrap(None)

    @property
    def owner(self) -> Any:
        return self.__owner.data

    def __print__(self):
        if self.__verbose:
            if self.is_locked():
                print(f'Locked by: {self.owner}')
            else:
                print('Unlocked')

    def is_locked(self) -> bool:
        return self.__lock.locked()

    def is_owned(self, owner: Any) -> bool:
        return self.__owner.data == owner

    def unlock(self, owner: Any) -> bool:
        if not self.__lock.locked():
            return True

        if self.__lock.locked() and self.is_owned(owner):
            self.__owner.assign(None)
            self.__lock.release()
            print(f'Unlocked: {self.owner}')
            return True

        self.__print__()
        return False

    def try_lock(self, owner: Any) -> bool:
        return self.lock(owner, timeout=0)

    def lock(self, owner: Any, timeout: float = 0) -> bool:
        if self.__lock.locked() and self.is_owned(owner):
            return True

        if self.__lock.acquire(timeout=timeout):
            self.__owner.assign(owner)
            print(f'Locked: {self.owner}')
            return True

        self.__print__()
        return False

    @contextlib.contextmanager
    def __call__(self, owner: Any):
        if self.try_lock(owner):
            yield
            self.unlock(owner)
        else:
            RuntimeError(f'Locked by {self.owner}')
