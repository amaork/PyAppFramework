# -*- coding: utf-8 -*-
import time
import inspect
import threading
import collections
from typing import Optional, Callable, Any, Tuple

from .datatype import DynamicObject
from .utils import util_check_arguments, util_auto_kwargs
from .threading import ThreadLockAndDataWrap, ThreadConditionWrap
__all__ = ['SwTimer', 'Tasklet', 'Task']


class SwTimer(object):
    TIMER_KEYWORD = 'timer'
    AUTO_ARGS = (TIMER_KEYWORD,)

    def __init__(self, base: float = 1.0, private: Any = None,
                 callback: Optional[Callable] = None, cb_args: Optional[tuple] = None, auto_start: bool = False):
        """
        Software timer base on thread
        :param base: timer base interval unit second
        :param callback: timer callback
        :param cb_args: timer callback args
        :param auto_start: auto start the timer
        """
        self._base = base
        self._private = private
        self._cb_callback = callback
        self._cb_args = cb_args or ()

        if callable(self._cb_callback):
            util_check_arguments(self._cb_callback, self._cb_args, self.AUTO_ARGS)

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
        self._cb_callback(**util_auto_kwargs(self._cb_callback, self._cb_args, {self.TIMER_KEYWORD: self}))

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


class TaskRuntime(DynamicObject):
    _properties = {'timeout', 'latest', 'cnt', 'tasklet'}

    def __init__(self, **kwargs):
        kwargs.setdefault('cnt', 0)
        kwargs.setdefault('tasklet', '')
        kwargs.setdefault('latest', 0.0)
        kwargs.setdefault('timeout', 0.0)
        super(TaskRuntime, self).__init__(**kwargs)

    def __repr__(self):
        return '{}'.format({k: v for k, v in self.dict.items() if k != 'tasklet'})


class Task(DynamicObject):
    TASK_KEYWORD = 'task'
    TASKLET_KEYWORD = 'tasklet'
    AUTO_ARGS = (TASK_KEYWORD, TASKLET_KEYWORD)
    TID = collections.namedtuple('TID', ['id', 'result'])

    _properties = {'func', 'args', 'timeout', 'periodic', 'result', 'runtime'}

    _check = {
        'func': lambda x: callable(x),
        'args': lambda x: isinstance(x, tuple),
        'periodic': lambda x: isinstance(x, bool),
        'timeout': lambda x: isinstance(x, (int, float)),
        'result': lambda x: isinstance(x, ThreadConditionWrap)
    }

    def __init__(self, func: Callable, timeout: float,
                 periodic: bool = False, args: Tuple = (),
                 result: Optional[ThreadConditionWrap] = None, id_ignore_args: bool = True):
        util_check_arguments(func, args, self.AUTO_ARGS)

        runtime = TaskRuntime()
        result = ThreadConditionWrap() if not isinstance(result, ThreadConditionWrap) else result
        kwargs = dict(func=func, args=args, timeout=float(timeout), periodic=periodic, result=result, runtime=runtime)
        super(Task, self).__init__(**kwargs)
        self.__id_ignore_args = True if id_ignore_args else False

    def __eq__(self, other):
        return self.id() == other.id()

    def __str__(self):
        args = '' if self.__id_ignore_args else f'{self.args}'
        return f"{self.func.__name__}{inspect.signature(self.func)}{args}{self.timeout}{self.periodic}"

    def __repr__(self):
        dict_ = {k: v for k, v in self.dict.items() if k not in ('result', '_Task__id_ignore_args')}
        dict_.update(func=self.func.__name__)
        return f'{dict_}'

    def id(self) -> str:
        return str(self)

    def run(self):
        """Run task and set result"""
        auto_args = {self.TASK_KEYWORD: self, self.TASKLET_KEYWORD: self.runtime.tasklet}

        self.result.reset()
        self.result.finished(self.func(**util_auto_kwargs(self.func, self.args, auto_args)))
        self.runtime.update(dict(cnt=self.runtime.cnt + 1, latest=time.perf_counter()))

        if self.periodic:
            self.reload()

    def clear(self):
        """"""
        self.reload()
        self.runtime.tasklet = None

    def bind(self, tasklet):
        """Bind task to tasklet

        :param tasklet:
        :return:
        """
        self.runtime.tasklet = tasklet
        self.runtime.update(dict(timeout=self.timeout, cnt=0))

    def tick(self):
        if self.is_running():
            self.runtime.timeout -= self.runtime.tasklet.tick

    def reload(self):
        self.runtime.update(dict(timeout=self.timeout))

    def delete(self):
        if self.is_running():
            self.runtime.tasklet.del_task(self.id())

    def reschedule(self):
        if self.is_running():
            self.runtime.tasklet.create_task(self)
        else:
            print("Error: {} is not running, please schedule it first".format(self))

    def is_timeout(self):
        return self.runtime.timeout <= 0

    def is_running(self):
        return isinstance(self.runtime.tasklet, Tasklet)

    def running_times(self):
        return self.runtime.cnt


class Tasklet(SwTimer):
    def __init__(self, schedule_interval: float = 1.0, name: str = '', debug: bool = False):
        """Tasklet is sample Round-Robin schedule is base on SwTimer(a threading)
        Add a Task to tasklet, when task timeout will schedule it once,
        if a Task is running, it could be delete or reschedule.

        A task has an unique id(function name, timeout and periodic params)
        at the sametime only one task instance could running in tasklet.

        Add same task to tasklet will cause previous task rescheduled

        :param schedule_interval: basic schedule interval unit is second
        :param name: Tasklet name just for debug and trance
        :param debug: Debug tasklet
        """
        self.__tasks = dict()
        self.__debug = True if debug else False
        self.__name = str(name) or str(id(self))
        self.__schedule_interval = schedule_interval
        super(Tasklet, self).__init__(base=schedule_interval, callback=self.__schedule, auto_start=True)

    def __repr__(self):
        tasks = sorted(self.__tasks.values(), key=lambda x: x.timeout)
        return f'{type(self).__name__} ({self.__name}) [\n' + '\n'.join([repr(x) for x in tasks]) + '\n]'

    def __schedule(self):
        for task in self.__tasks.values():
            task.tick()

        timeout_task = [x for x in self.__tasks.values() if x.is_timeout()]
        for task in timeout_task:
            # Execute task, periodic task will auto reload timeout timer
            task.run()
            if task.is_timeout():
                self.del_task(task.id())

    @property
    def tick(self) -> float:
        return self._base

    def is_idle(self) -> bool:
        """Tasklet is idle no task in tasklet"""
        return len(self.__tasks) == 0

    def del_task(self, tid: str):
        """Delete a task from tasklet"""
        if tid in self.__tasks:
            task = self.__tasks.pop(tid)
            task.clear()
            if self.__debug:
                print(repr(self))

    def create_task(self, task: Task) -> Task.TID:
        """Insert task to tasklet, same task will reload"""
        tid = task.id()
        if tid in self.__tasks:
            old = self.__tasks.get(tid)
            if id(old) == id(task):
                task.reload()

        task.bind(self)
        self.__tasks[tid] = task
        result = Task.TID(tid, task.result)

        if self.__debug:
            print(repr(self))

        return result

    def is_task_in_schedule(self, tid: str) -> bool:
        """Check if a task is in tasklet"""
        return tid in self.__tasks
