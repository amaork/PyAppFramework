# -*- coding: utf-8 -*-
import time
import typing
import reprlib
import inspect
import logging
import datetime
import functools
import contextlib
from ..core.datatype import DynamicObject
from ..misc.settings import UiLogMessage, JsonSettings
__all__ = ['track_time', 'statistics_time', 'get_debug_timestamp', 'get_stack_info',
           'ExceptionHandle', 'LoggerWrap', 'LogAdapter', 'JsonSettingsWithDebugCode']


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


def get_stack_info() -> DynamicObject:
    frame = inspect.stack()[1][0]
    info = inspect.getframeinfo(frame)
    return DynamicObject(filename=info.filename, function=info.function, lineno=info.lineno)


class ExceptionHandle:
    RELEASE = True

    def __init__(self, param: typing.Any,
                 callback: typing.Callable[[typing.Any, str], None],
                 release: bool = True, debug_info: str = '', ignore_exceptions: typing.Sequence = None):
        self.__param = param
        self.__callback = callback
        self.__debug_info = debug_info
        self.__ignore_exceptions = ignore_exceptions or list()
        self.__exception_handled = release and ExceptionHandle.RELEASE

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type in self.__ignore_exceptions:
            return False

        if exc_type and callable(self.__callback):
            frame = inspect.stack()[1][0]
            info = inspect.getframeinfo(frame)
            stack_info = f'filename: {info.filename}\rlineno: {info.lineno}\nfunction: {info.function}\n'
            self.__callback(
                self.__param,
                f'Exception:\n{exc_type} {exc_val} {exc_tb}\n\nStack:\n{stack_info}\nDebug info:\n{self.__debug_info}'
            )
        return self.__exception_handled


class LoggerWrap:
    DefaultFormat = '%(asctime)s %(levelname)s %(message)s'

    def __init__(self, filename: str, fmt: str = DefaultFormat,
                 level: int = logging.DEBUG, stream_level: int = logging.DEBUG, propagate: bool = False):
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
        stream_handler.setLevel(stream_level)

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


class JsonSettingsWithDebugCode(JsonSettings):
    _debug_kw = 'debug_code'

    def is_debug_enabled(self, option: str) -> bool:
        return option in self.debug_code

    def get_debug_option(self, option: str) -> str:
        if not self.is_debug_enabled(option):
            return ''

        return [x for x in self.debug_code.split() if option in x][0].split('#')[-1]
