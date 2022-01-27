# -*- coding: utf-8 -*-
import time
import reprlib
import functools
import contextlib
__all__ = ['track_time', 'statistics_time']


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
