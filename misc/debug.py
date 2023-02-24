# -*- coding: utf-8 -*-
import time
import typing
import reprlib
import inspect
import logging
import datetime
import functools
import contextlib
from ..misc.settings import UiLogMessage
__all__ = ['track_time', 'statistics_time', 'get_debug_timestamp', 'ExceptionHandle', 'LoggerWrap', 'LogAdapter']


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


def get_debug_timestamp() -> str:
    return datetime.datetime.now().strftime('%H:%M:%S.%f')


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


class LoggerWrap:
    DefaultFormat = '%(asctime)s %(levelname)s %(message)s'

    def __init__(self, filename: str, fmt: str = DefaultFormat, level: int = logging.DEBUG, propagate: bool = False):
        # Get logger and set level and propagate
        self._logger = logging.getLogger(filename)
        self._logger.propagate = propagate
        self._logger.setLevel(level)
        self._filename = filename

        # Create a file handler
        file_handler = logging.FileHandler(filename, encoding="utf-8")
        file_handler.setLevel(level)

        # Create a stream handler
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.ERROR)

        # Create a formatter and add it to handlers
        formatter = logging.Formatter(fmt)
        file_handler.setFormatter(formatter)
        stream_handler.setFormatter(formatter)

        # Add handlers to logger
        self._logger.addHandler(file_handler)
        self._logger.addHandler(stream_handler)

    @property
    def filename(self) -> str:
        return self._filename

    def info(self, msg: str):
        self.logging(UiLogMessage.genDefaultInfoMessage(msg))

    def debug(self, msg: str):
        self.logging(UiLogMessage.genDefaultDebugMessage(msg))

    def error(self, msg: str):
        self.logging(UiLogMessage.genDefaultErrorMessage(msg))

    def logging(self, message: UiLogMessage):
        if not isinstance(message, UiLogMessage):
            return

        self._logger.log(message.level, message.content)


class LogAdapter(logging.LoggerAdapter):
    def __init__(self, logger, extra):
        super(LogAdapter, self).__init__(logger, extra)
        self.logger = logger
        self.extra = extra

    def process(self, msg, kwargs):
        kwargs['extra'] = self.extra
        return msg, kwargs
