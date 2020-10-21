# -*- coding: utf-8 -*-
import threading
__all__ = ['ThreadLockContentManager', 'ThreadConditionWrap']


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
