# -*- coding: utf-8 -*-
import os
import time
import signal
import platform

__all__ = ['ProcessManager']


class ProcessManager(object):
    WAIT_TIME = 0.5
    SYSTEM = platform.system().lower()

    def __init__(self, cmdline, autostart=True):
        """Process manager

        :param cmdline: command line
        :param autostart: if set auto start program
        """
        self.__cmdline = cmdline
        self.__args = ' '.join(cmdline.split(' ')[1:])
        self.__path = os.path.dirname(cmdline.split(' ')[0])
        self.__name = os.path.basename(cmdline.split(' ')[0])
        if autostart:
            self.resume()

    def __process_control(self, run):
        """Process control

        :param run:
        :return:
        """
        retry = 3
        lst = list()
        cwd = os.getcwd()

        try:

            # Absolute path, enter path
            if os.path.isdir(self.path):
                os.chdir(self.path)
                if self.is_windows():
                    cmd = "{} {}".format(self.name, self.args)
                else:
                    cmd = "./{} {}".format(self.name, self.args)
            else:
                cmd = self.cmdline

            # Make program running in background
            if self.is_windows():
                cmd = "start /b {}".format(cmd)
            else:
                if not cmd.endswith('&'):
                    cmd += ' &'

            while not lst and retry > 0:
                lst = self.get_pid(self.name)
                if not lst:
                    os.system(cmd)
                    retry -= 1
                    continue

                if not self.is_windows():
                    for pid in lst:
                        os.kill(pid, signal.SIGCONT if run else signal.SIGSTOP)
        except Exception:
            pass
        finally:
            os.chdir(cwd)

    @property
    def args(self):
        return self.__args

    @property
    def name(self):
        return self.__name

    @property
    def path(self):
        return self.__path

    @property
    def cmdline(self):
        return self.__cmdline

    @staticmethod
    def is_windows():
        return ProcessManager.SYSTEM == "windows"

    @staticmethod
    def get_pid(name):
        """Get process id

           :param name: process name
           :return: pid list
           """
        if ProcessManager.is_windows():
            cmd = os.popen("tasklist | grep {0:s} | awk '{{ print $2 }}'".format(name))
        else:
            cmd = os.popen('pidof {0:s}'.format(name))

        data = cmd.read().strip()
        if not data:
            return []

        try:
            return [int(pid) for pid in data.split(' ')]
        except ValueError:
            return [int(pid) for pid in data.split('\n')]

    @staticmethod
    def kill(name):
        """Kill name specified process

        :param name: process name
        :return: success return True, failed return false
        """
        kill_signal = signal.SIGILL if ProcessManager.is_windows() else signal.SIGKILL
        for pid in ProcessManager.get_pid(name):
            os.kill(pid, kill_signal)

        # Wait process be killed
        time.sleep(ProcessManager.WAIT_TIME)
        return True if not ProcessManager.get_pid(name) else False

    def suspend(self):
        if self.is_windows():
            return self.kill(self.name)

        self.__process_control(False)
        return True if self.get_pid(self.name) else False

    def resume(self):
        self.__process_control(True)
        time.sleep(ProcessManager.WAIT_TIME)
        return True if self.get_pid(self.name) else False

    def terminate(self):
        return self.kill(self.name)

    def is_running(self):
        return len(self.get_pid(self.name)) != 0
