# -*- coding: utf-8 -*-
import time
import queue
import inspect
import traceback
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
    _properties = {'timeout', 'latest', 'cnt', 'cost', 'tasklet'}

    def __init__(self, **kwargs):
        kwargs.setdefault('cnt', 0)
        kwargs.setdefault('cost', 0.0)
        kwargs.setdefault('tasklet', '')
        kwargs.setdefault('latest', 0.0)
        kwargs.setdefault('timeout', 0.0)
        super(TaskRuntime, self).__init__(**kwargs)

    def __repr__(self):
        return '{}'.format({k: format(v, '.2f') if k != 'cnt' else v for k, v in self.dict.items() if k != 'tasklet'})


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
                 result: Optional[ThreadConditionWrap] = None,
                 id_ignore_args: bool = True, id_ignore_timeout: bool = False):
        util_check_arguments(func, args, self.AUTO_ARGS)

        runtime = TaskRuntime()
        result = ThreadConditionWrap() if not isinstance(result, ThreadConditionWrap) else result
        kwargs = dict(func=func, args=args, timeout=float(timeout), periodic=periodic, result=result, runtime=runtime)
        super(Task, self).__init__(**kwargs)
        self.__lock = threading.Lock()
        self.__id_ignore_args = True if id_ignore_args else False
        self.__id_ignore_timeout = True if id_ignore_timeout else False

    def __eq__(self, other):
        return self.id() == other.id()

    def __str__(self):
        args = '' if self.__id_ignore_args else f'{self.args}'
        timeout = '' if self.__id_ignore_timeout else f'{self.timeout}'
        return f"{self.func.__name__}{inspect.signature(self.func)}{args}{timeout}{self.periodic}"

    def __repr__(self):
        dict_ = {k: v for k, v in self.dict.items() if k not in ('result',) and not k.startswith('_Task__')}
        dict_.update(func=self.func.__name__)
        return f'{dict_}'

    def id(self) -> str:
        return str(self)

    def run(self):
        """Run task and set result"""
        with self.__lock:
            auto_args = {self.TASK_KEYWORD: self, self.TASKLET_KEYWORD: self.runtime.tasklet}
            start_ts = time.perf_counter()

            try:
                self.result.finished(self.func(**util_auto_kwargs(self.func, self.args, auto_args)))
            except Exception as e:
                self.delete()
                self.result.finished(False)
                return f'Task: {self} raise critical error, will be deleted: {e}, {traceback.format_exc()}'
            finally:
                end_ts = time.perf_counter()
                self.runtime.update(dict(cnt=self.runtime.cnt + 1, latest=end_ts, cost=end_ts - start_ts))

            # Periodic task auto reload timeout
            if self.periodic:
                self.reload()

            # Single shot task if not calling `reschedule` will automatically delete
            if self.is_timeout():
                self.delete()

    def detach(self):
        """"""
        self.reload()
        self.runtime.tasklet = None

    def attach(self, tasklet):
        """Attach task to tasklet

        :param tasklet:
        :return:
        """
        self.runtime.tasklet = tasklet
        self.runtime.update(dict(timeout=self.timeout, cnt=0))

    def tick(self):
        if self.is_attached():
            self.runtime.timeout -= self.runtime.tasklet.tick

    def reload(self):
        self.runtime.update(dict(timeout=self.timeout))

    def delete(self):
        if self.is_attached():
            self.runtime.tasklet.del_task(self.id())

    def reschedule(self):
        if self.is_attached():
            self.runtime.tasklet.add_task(self)
        else:
            print("Error: {} is not attached, please add task to tasklet first".format(self))

    def is_delayed(self):
        """Return true if a task latest running time is out of tasklet schedule time (only works for periodic task)"""
        if self.periodic and self.is_attached():
            return self.runtime.cost > self.runtime.tasklet.tick

        return False

    def is_timeout(self):
        """Return true is a time is timeout, timeout means it's need to be scheduled"""
        return self.runtime.timeout <= 0.0

    def is_running(self):
        return self.__lock.locked()

    def is_attached(self):
        return isinstance(self.runtime.tasklet, Tasklet)

    def running_times(self):
        return self.runtime.cnt


class Tasklet(SwTimer):
    def __init__(self,
                 schedule_interval: float = 1.0,
                 max_workers: Optional[int] = None,
                 name: str = '', dump: Optional[Callable[[str], None]] = None, err: Callable[[str], None] = print):
        """Tasklet is sample Round-Robin schedule is base on SwTimer(a threading)
        Add a Task to tasklet, when task timeout will schedule it once,
        if a Task is running, it could be delete or reschedule.

        A task has an unique id(function name, timeout and periodic params)
        at the sametime only one task instance could running in tasklet.

        Add same task to tasklet will cause previous task rescheduled.

        If max_workers is set, scheduler will automatically check each periodic task last running cost time,
        if a task last running cost time is to too long(be delayed) it will put the task to a thread pool worker

        :param schedule_interval: basic schedule interval unit is second
        :param max_workers: max worker thread, default only one thread
        :param name: Tasklet name just for debug and track
        :param dump: Tasklet dump output function
        :param err: Tasklet error log output
        """
        if not callable(err):
            raise TypeError('log must be callable')

        self.__tasks = dict()
        self.__dump_callback = dump
        self.__error_callback = err

        self.__queue = queue.Queue()
        self.__name = str(name) or str(id(self))
        self.__schedule_interval = schedule_interval
        self.__max_workers = min(max_workers, 4) if isinstance(max_workers, int) else 0
        super(Tasklet, self).__init__(base=schedule_interval, callback=self.__schedule, auto_start=True)

        for i in range(self.__max_workers):
            threading.Thread(target=self.__worker, daemon=True, name=f'Tasklet worker {i}').start()

    def __repr__(self):
        now = "{:.4f}".format(time.perf_counter())
        tasks = sorted(self.__tasks.values(), key=lambda x: x.timeout)
        return f'{type(self).__name__}, {self.__name}, {self.is_idle()}, {now} ' \
               f'[\n\t' + '\n\t'.join([repr(x) for x in tasks]) + '\n]'

    def __dump(self):
        if callable(self.__dump_callback):
            return self.__dump_callback(repr(self))

    def __worker(self):
        while True:
            task = self.__queue.get()
            if task is None:
                break

            self.__error_handle(task.run())

    def __schedule(self):
        for task in self.__tasks.values():
            task.tick()

        # Find out timeout task, if task is delayed and has enabled workers put to worker thread
        for task in [x for x in self.__tasks.values() if x.is_timeout()]:
            if task.is_delayed() and self.__max_workers:
                if not task.is_running():
                    self.__queue.put(task)
            else:
                if not task.is_running():
                    self.__error_handle(task.run())

    def __error_handle(self, result):
        if result is not None:
            self.__error_callback(f'Tasklet: {self}, {result}')

    @property
    def tick(self) -> float:
        return self._base

    def destroy(self):
        # Detach all task in tasklet
        for task in self.__tasks.values():
            task.detach()

        # Destroy all worker thread
        for _ in range(self.__max_workers):
            self.__queue.put(None)

        self.__tasks.clear()

        # Stop timer
        self.stop()

    def is_idle(self):
        """Check if tasklet is idle(no task in tasklet)"""
        idle = len(self.__tasks) == 0, self.__queue.qsize() == 0
        return collections.namedtuple('TaskletIdle', ['tasklet', 'worker'])(*idle)

    def del_task(self, tid: str):
        """Delete a task from tasklet"""
        if tid in self.__tasks:
            task = self.__tasks.pop(tid)
            task.detach()
            self.__dump()

    def add_task(self, task: Task, immediate: bool = False) -> Task.TID:
        """Insert task to tasklet, same id task will detach old task, add new task"""
        tid = task.id()

        try:
            self.__tasks.get(tid).detach()
        except AttributeError:
            pass

        task.attach(self)
        self.__tasks[tid] = task
        result = Task.TID(tid, task.result)

        # If immediate set will run immediately
        if (immediate or task.is_timeout()) and self.__max_workers:
            self.__queue.put(task)
            if not task.periodic:
                self.del_task(task.id())

        self.__dump()
        return result

    def is_task_in_schedule(self, tid: str) -> bool:
        """Check if a task is in tasklet"""
        return tid in self.__tasks
