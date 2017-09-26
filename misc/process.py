# -*- coding: utf-8 -*-
import os
import signal
import platform

__all__ = ['ProcessManager']


class ProcessManager(object):
    SYSTEM = platform.system().lower()

    def __init__(self, name, cmdline, autostart=True):
        """Process manager

        :param name: name
        :param cmdline: command line
        :param autostart: if set auto start program
        """
        self.__name = name
        self.__cmdline = cmdline
        if autostart:
            self.resume()

    def __process_control(self, run):
        """Process control

        :param run:
        :return:
        """
        retry = 3
        lst = list()
        name = self.name()
        cmd = os.path.basename(self.cmdline())
        path = os.path.dirname(self.cmdline())

        try:

            if os.path.isdir(path):
                os.chdir(path)

            # Make program running in background
            if self.is_windows():
                cmd = "start /b {0:s}".format(cmd)
            else:
                if not cmd.endswith('&'):
                    cmd += ' &'
                cmd = "./{}".format(cmd)

            while not lst and retry > 0:
                lst = self.get_pid(name)
                if not lst:
                    os.system(cmd)
                    retry -= 1
                    continue

                if not self.is_windows():
                    for pid in lst:
                        os.kill(pid, signal.SIGCONT if run else signal.SIGSTOP)
        except StandardError:
            pass

    def name(self):
        return self.__name

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
        return [int(pid) for pid in data.split(' ')]

    @staticmethod
    def kill(name):
        """Kill name specified process

        :param name: process name
        :return: success return True, failed return false
        """
        kill_signal = signal.SIGILL if ProcessManager.is_windows() else signal.SIGKILL
        for pid in ProcessManager.get_pid(name):
            os.kill(pid, kill_signal)

        return True if not ProcessManager.get_pid(name) else False

    def suspend(self):
        if self.is_windows():
            return self.kill(self.name())

        self.__process_control(False)
        return True if self.get_pid(self.name()) else False

    def resume(self):
        self.__process_control(True)
        return True if self.get_pid(self.name()) else False

    def terminate(self):
        return self.kill(self.name())

    def is_running(self):
        return len(self.get_pid(self.name())) != 0
