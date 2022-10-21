# -*- coding: utf-8 -*-
import time
import typing
import reprlib
import inspect
import functools
import contextlib
__all__ = ['track_time', 'statistics_time', 'ExceptionHandle']


def track_time(func):
    @functools.wraps(func)
    def wrapper_debug_time(*args, **kwargs):
        t0 = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - t0
        name = func.__name__

        arg_lst = list()
        if args:
            arg_lst.append(', '.join(repr(arg) for arg in args))

        if kwargs:
            arg_lst.append(', '.join(['{} = {}'.format(k, v) for k, v in sorted(kwargs.items())]))

        arg_str = reprlib.repr(arg_lst)
        print('[{} {:.08f}s] {}({}) -> {}'.format(track_time.__name__, elapsed, name, arg_str, reprlib.repr(result)))
        return result

    return wrapper_debug_time


@contextlib.contextmanager
def statistics_time(label: str = 'statistics_time'):
    start = time.perf_counter()
    try:
        yield
    finally:
        print(f'{label}: {time.perf_counter() - start}')


class ExceptionHandle:
    RELEASE = True

    def __init__(self, param: typing.Any,
                 callback: typing.Callable[[typing.Any, str], None],
                 release: bool = True, debug_info: str = ''):
        self.__param = param
        self.__callback = callback
        self.__debug_info = debug_info
        self.__exception_handled = release and ExceptionHandle.RELEASE

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type and callable(self.__callback):
            frame = inspect.stack()[1][0]
            info = inspect.getframeinfo(frame)
            stack_info = f'filename: {info.filename}, function: {info.function}, lineno: {info.lineno}'
            self.__callback(
                self.__param, f'{exc_type} {exc_val} {exc_tb}\nStack: {stack_info}, debug_info: {self.__debug_info}'
            )
        return self.__exception_handled
