# -*- coding: utf-8 -*-
import time
import unittest
from ..core.timer import Task, Tasklet


def func(x):
    return x


class CRC16Test(unittest.TestCase):
    def setUp(self) -> None:
        self.tasklet = Tasklet(max_workers=3)

    def tearDown(self) -> None:
        self.tasklet.destroy()

    def testTask(self):
        t1 = Task(func=func, timeout=1, args=(1,))
        t2 = Task(func=func, timeout=1, args=(2,))

        t3 = Task(func=func, timeout=1, args=(1,))
        t4 = Task(func=func, timeout=1, args=(2,), periodic=True)

        t5 = Task(func=func, timeout=1, args=(1,), id_ignore_args=False)
        t6 = Task(func=func, timeout=1, args=(2,), id_ignore_args=False)

        self.assertEqual(t1, t2)
        self.assertNotEqual(t3, t4)
        self.assertNotEqual(t5, t6)

    def testTaskArgs(self):
        def func1(a, b, c=3):
            return a, b, c

        with self.assertRaises(TypeError):
            Task(func=func1, timeout=1)

        with self.assertRaises(TypeError):
            Task(func=func1, timeout=1, args=(1,))

        with self.assertRaises(TypeError):
            Task(func=func1, timeout=1, args=(1, 2, 3, 4))

        t1 = Task(func=func1, timeout=3, args=(1, 2), id_ignore_args=False)
        t2 = Task(func=func1, timeout=4, args=(1, 3, 5), id_ignore_args=False)

        tid1 = self.tasklet.add_task(t1)
        tid2 = self.tasklet.add_task(t2)
        time.sleep(5)
        self.assertEqual(tid1.result.wait(2), (1, 2, 3))
        self.assertEqual(tid2.result.wait(2), (1, 3, 5))

    def testTaskAutoArgs(self):
        def func1(task, a, tasklet, b, c=3):
            print(task.id(), tasklet.is_idle(), a, b, c)
            return a, b, c

        with self.assertRaises(TypeError):
            Task(func=func1, timeout=1)

        with self.assertRaises(TypeError):
            Task(func=func1, timeout=1, args=(1,))

        with self.assertRaises(TypeError):
            Task(func=func1, timeout=1, args=(1, 2, 3, 4))

        t1 = Task(func=func1, timeout=1, args=(1, 2), id_ignore_args=False)
        t2 = Task(func=func1, timeout=1, args=(1, 3, 5), id_ignore_args=False)

        self.tasklet.add_task(t1)
        self.tasklet.add_task(t2)
        time.sleep(2)

    def testTasklet(self):
        self.assertEqual(self.tasklet.tick, 1.0)
        self.assertEqual(self.tasklet.is_idle(), (True, True))

    def testAddTask(self):
        t1 = Task(func=func, timeout=10, args=(1,))
        t2 = Task(func=func, timeout=10, args=(2,))

        tid1 = self.tasklet.add_task(t1)
        self.assertEqual(t1.is_attached(), True)
        self.assertEqual(t2.is_attached(), False)

        time.sleep(3)
        self.assertLess(t1.runtime.timeout, 10.0)

        tid2 = self.tasklet.add_task(t2)
        self.assertEqual(t1.is_attached(), False)
        self.assertEqual(t2.is_attached(), True)
        self.assertEqual(t1.runtime.timeout, 10.0)

        self.assertEqual(self.tasklet.is_task_in_schedule(tid1.id), True)
        self.assertEqual(self.tasklet.is_task_in_schedule(tid2.id), True)

        self.assertEqual(tid2.result.wait(), 2)
        self.assertEqual(tid1.result.wait(1), None)

    def testAddTask2(self):
        tid1 = self.tasklet.add_task(Task(func=func, args=(1,), timeout=1, periodic=True))
        tid2 = self.tasklet.add_task(Task(func=func, args=(2,), timeout=1, periodic=True))

        time.sleep(3)
        self.assertEqual(self.tasklet.is_task_in_schedule(tid1.id), True)
        self.assertEqual(self.tasklet.is_task_in_schedule(tid2.id), True)

        # Del
        self.tasklet.del_task(tid1.id)
        self.tasklet.del_task(tid2.id)
        self.assertEqual(self.tasklet.is_task_in_schedule(tid1.id), False)
        self.assertEqual(self.tasklet.is_task_in_schedule(tid2.id), False)

        # Re-add
        self.tasklet.add_task(tid1.task)
        self.tasklet.add_task(tid2.task)
        time.sleep(3)
        self.assertEqual(self.tasklet.is_task_in_schedule(tid1.id), True)
        self.assertEqual(self.tasklet.is_task_in_schedule(tid2.id), True)

    def testSchedule(self):
        t1 = Task(func=func, timeout=1, args=(1,), periodic=True)
        t2 = Task(func=lambda: time.sleep(3), timeout=1, periodic=True)
        t3 = Task(func=lambda: time.sleep(2), timeout=1, periodic=True)
        t4 = Task(func=lambda: time.sleep(5), timeout=1, periodic=True)

        self.tasklet.add_task(t1)
        self.tasklet.add_task(t2, immediate=True)
        self.tasklet.add_task(t3, immediate=True)
        self.tasklet.add_task(t4, immediate=True)
        time.sleep(0.5)
        self.assertEqual(t2.is_running(), True)

        time.sleep(10)
        self.assertGreaterEqual(t1.running_times(), 10)
        self.tasklet.destroy()

        self.assertEqual(t1.is_attached(), False)
        self.assertEqual(t2.is_attached(), False)
        self.assertEqual(t3.is_attached(), False)
        self.assertEqual(t4.is_attached(), False)
        time.sleep(10)
        self.assertEqual(self.tasklet.is_idle(), (True, True))


if __name__ == "__main__":
    unittest.main()
