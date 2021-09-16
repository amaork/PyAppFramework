# -*- coding: utf-8 -*-
import time
import inspect
import threading
import collections
from typing import Optional, Callable, Any

from .datatype import DynamicObject
from .threading import ThreadLockAndDataWrap, ThreadConditionWrap
__all__ = ['SwTimer', 'Tasklet', 'Task']


class SwTimer(object):
    def __init__(self, base: float = 1.0,
                 private: Any = None,
                 callback: Optional[Callable] = None,
                 cb_args: Optional[tuple] = None, cb_kwargs: Optional[dict] = None, auto_start: bool = False):
        """
        Software timer base on thread
        :param base: timer base interval unit second
        :param callback: timer callback
        :param cb_args: timer callback args (Notice: callback first arg always be the SwTimer itself)
        :param cb_kwargs: timer callback kwargs (Notice: callback kwargs always has a key named timer(SwTimer itself))
        :param auto_start: auto start the timer
        """
        self._base = base
        self._private = private
        self._cb_callback = callback
        self._cb_args = cb_args or ()
        self._cb_kwargs = cb_kwargs or dict()

        self._event = threading.Event()
        self._stop = ThreadLockAndDataWrap(False)
        self._timer_cnt = ThreadLockAndDataWrap(0)
        self._start_timestamp = time.perf_counter()
        self._is_running = ThreadLockAndDataWrap(auto_start)

        self._th = threading.Thread(target=self.__timer_thread, name="Software timer")
        self._th.setDaemon(True)
        self._th.start()

    def __del__(self):
        self.stop()

    def __timer_thread(self):
        while not self._stop:
            self._event.wait(self._base)
            if self._is_running:
                self.__callback()

    def __callback(self):
        self._timer_cnt.data += 1
        if not callable(self._cb_callback):
            return

        if self._cb_args:
            self._cb_callback(*(self, *self._cb_args))
        elif self._cb_kwargs:
            self._cb_callback(timer=self, **self._cb_kwargs)
        else:
            self._cb_callback(self)

    @property
    def cnt(self) -> int:
        return self._timer_cnt.data

    @property
    def private(self) -> Any:
        return self._private

    @private.setter
    def private(self, data: Any):
        self._private = data

    def stop(self):
        self._event.set()
        self._stop.data = True
        self._is_running.data = False

    def pause(self):
        self._is_running.data = False

    def reset(self):
        self._timer_cnt.data = 0

    def resume(self):
        self._is_running.data = True

    def wait(self, timeout: float):
        self._event.wait(timeout)

    def is_running(self) -> bool:
        return not self._stop and self._is_running.data

    def time_elapsed(self) -> float:
        return time.perf_counter() - self._start_timestamp if self.is_running() else 0.0

    def is_timeout(self, time_in_s: float) -> bool:
        return self.time_elapsed() >= time_in_s

    @staticmethod
    def singleShot(timeout: float,
                   callback: Optional[Callable] = None,
                   cb_args: Optional[tuple] = None, cb_kwargs: Optional[dict] = None):
        """
        Create a single shot SwTimer
        :param timeout: timer timeout in second
        :param callback: timer timeout callback
        :param cb_args: timer callback args
        :param cb_kwargs: timer callback kwargs
        :return:
        """
        def callback_wrapper(timer: SwTimer, *args, **kwargs):
            timer.stop()
            callback(*args, **kwargs)

        SwTimer(base=timeout, callback=callback_wrapper, cb_args=cb_args, cb_kwargs=cb_kwargs, auto_start=True)


class Task(DynamicObject):
    TASK_KEYWORD = 'task'
    TASKLET_KEYWORD = 'tasklet'
    TID = collections.namedtuple('TID', ['id', 'result'])

    _properties = {'func', 'args',
                   'timeout', 'timeout_reload', 'periodic',
                   'result', 'tasklet', 'latest_run', 'running_cnt'}

    _check = {
        'func': lambda x: callable(x),
        'args': lambda x: isinstance(x, tuple),
        'periodic': lambda x: isinstance(x, bool),
        'timeout': lambda x: isinstance(x, (int, float)),
        'result': lambda x: isinstance(x, ThreadConditionWrap)
    }

    def run(self):
        """Run task and set result"""
        kwargs = dict()
        user_params = self.__get_user_param(self.func)
        parameters = inspect.signature(self.func).parameters

        if self.TASK_KEYWORD in parameters:
            kwargs[self.TASK_KEYWORD] = self

        if self.TASKLET_KEYWORD in parameters:
            kwargs[self.TASKLET_KEYWORD] = self.tasklet

        kwargs.update(dict(zip(user_params, self.args)))

        self.result.reset()
        self.result.finished(self.func(**kwargs))
        self.update(dict(latest_run=time.perf_counter(), running_cnt=self.running_cnt + 1))
        if self.periodic:
            self.reload()

    def reload(self):
        self.update(dict(timeout=self.timeout_reload))

    def delete(self):
        if self.is_running():
            self.tasklet.del_task(self.id())

    def reschedule(self):
        if self.is_running():
            self.tasklet.create_task(self)
        else:
            print("Error: {} is not running, please schedule it first".format(self))

    def id(self) -> str:
        return str(self)

    def is_running(self):
        return isinstance(self.tasklet, Tasklet)

    def __eq__(self, other):
        return self.id() == other.id()

    def __str__(self):
        return f'{self.func.__name__}: timeout {self.timeout_reload}, periodic {self.periodic}'

    def __repr__(self):
        d = self.dict
        d.pop('func')
        d.pop('result')
        d.pop('tasklet')
        return f'{self.func.__name__}: {d}'

    def __init__(self, **kwargs):
        kwargs.setdefault('args', ())
        kwargs.setdefault('tasklet', '')
        kwargs.setdefault('periodic', False)
        kwargs.setdefault('latest_run', 0.0)
        kwargs.setdefault('running_cnt', 0)
        kwargs.setdefault('result', ThreadConditionWrap())
        kwargs.setdefault('timeout', float(kwargs.get('timeout')))
        kwargs.setdefault('timeout_reload', float(kwargs.get('timeout')))
        self.__check_parameters(kwargs.get('func'), kwargs.get('args'))
        super(Task, self).__init__(**kwargs)

    def __get_user_param(self, func):
        return [x for x in inspect.signature(func).parameters if x not in (self.TASK_KEYWORD, self.TASKLET_KEYWORD)]

    def __check_parameters(self, func, args):
        params = self.__get_user_param(func)
        if len(args) < len(params):
            missing = tuple(params[len(args):])
            message = ",".join([f'{x!r}' for x in missing])
            raise TypeError(f'{func.__name__} missing {len(missing)} required positional arguments: {message}')
        elif len(args) > len(params):
            raise TypeError(f'{func.__name__} takes {len(params)} positional arguments but {len(args)} were given')


class Tasklet(SwTimer):
    def __init__(self, schedule_interval: float = 1.0):
        self.__tasks = dict()
        self.__schedule_interval = schedule_interval
        super(Tasklet, self).__init__(base=schedule_interval, callback=self.__schedule, auto_start=True)

    def __del__(self):
        print("Tasklet exit")

    def __repr__(self):
        return ", ".join([repr(x) for x in self.__tasks.values()])

    def __schedule(self, _timer: SwTimer):
        for task in self.__tasks.values():
            task.timeout -= self.__schedule_interval

        timeout_task = [x for x in self.__tasks.values() if x.timeout <= 0]
        for task in timeout_task:
            task.run()
            if task.timeout <= 0:
                task.reload()
                temp = self.__tasks.pop(task.id())
                temp.tasklet = None

    def is_idle(self) -> bool:
        return len(self.__tasks) == 0

    def del_task(self, tid: str):
        if tid in self.__tasks:
            task = self.__tasks.pop(tid)
            task.tasklet = None

    def create_task(self, task: Task) -> Task.TID:
        """Insert task to tasklet, same task will reload"""
        tid = task.id()
        if tid in self.__tasks:
            old = self.__tasks.get(tid)
            if id(old) == id(task):
                task.reload()

        task.tasklet = self
        self.__tasks[tid] = task
        return Task.TID(tid, task.result)

    def is_task_in_schedule(self, tid: str) -> bool:
        return tid in self.__tasks