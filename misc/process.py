# -*- coding: utf-8 -*-
import os
import sys
import time
import queue
import psutil
import signal
import platform
import threading
import subprocess
from typing import List
__all__ = ['ProcessManager', 'SubprocessWithTimeoutRead', 'subprocess_startup_info', 'launch_program', 'watch_program']


class ProcessManager(object):
    WAIT_TIME = 0.5
    SYSTEM = platform.system().lower()

    def __init__(self, cmdline: str, autostart: bool = True):
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

    def __process_control(self, run: bool):
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
        finally:
            os.chdir(cwd)

    @property
    def args(self) -> str:
        return self.__args

    @property
    def name(self) -> str:
        return self.__name

    @property
    def path(self) -> str:
        return self.__path

    @property
    def cmdline(self) -> str:
        return self.__cmdline

    @staticmethod
    def is_windows() -> bool:
        return ProcessManager.SYSTEM == "windows"

    @staticmethod
    def get_pid(name: str) -> List[int]:
        """Get process id

        :param name: process name
        :return: pid list
        """
        pid_list = list()
        for process in psutil.process_iter():
            try:
                if process.name() == name:
                    pid_list.append(process.pid)
            except psutil.AccessDenied:
                pass

        return pid_list

    @staticmethod
    def kill(name: str) -> bool:
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

    def suspend(self) -> bool:
        if self.is_windows():
            return self.kill(self.name)

        self.__process_control(False)
        return True if self.get_pid(self.name) else False

    def resume(self) -> bool:
        self.__process_control(True)
        time.sleep(ProcessManager.WAIT_TIME)
        return True if self.get_pid(self.name) else False

    def terminate(self) -> bool:
        return self.kill(self.name)

    def is_running(self) -> bool:
        return len(self.get_pid(self.name)) != 0


class SubprocessWithTimeoutRead(object):
    def __init__(self, args):
        self.__queue = queue.Queue()
        is_posix = 'posix' in sys.builtin_module_names
        self.__process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                          bufsize=1, close_fds=is_posix)
        self.__thread = threading.Thread(target=self.__blockReadStdoutThread)
        self.__thread.setDaemon(True)
        self.__thread.start()

    def __del__(self):
        self.kill()

    def wait(self, timeout: float):
        try:
            timeout = timeout or None
            self.__process.wait(timeout)
        except subprocess.TimeoutExpired:
            pass

    def kill(self):
        self.__process.kill()
        ret, err = self.__process.communicate()
        self.__queue.put_nowait((ret + err).decode())

    def read(self, timeout: float = 0):
        try:
            return self.__queue.get(timeout=timeout)
        except queue.Empty:
            return ""

    def __blockReadStdoutThread(self):
        while True:
            try:
                data = self.__process.stdout.read().decode()
                self.__queue.put_nowait(data)
                time.sleep(0.1)
            except ValueError:
                ret, err = self.__process.communicate()
                self.__queue.put_nowait((ret + err).decode())
                break


def subprocess_startup_info(console_mode: bool = False):
    if platform.system().lower() == 'windows':
        startup_info = subprocess.STARTUPINFO()
        startup_info.dwFlags = subprocess.STARTF_USESHOWWINDOW
        startup_info.wShowWindow = subprocess.SW_HIDE
        return None if console_mode else startup_info
    else:
        return None


def watch_program(name: str, launch_kwargs: dict, interval: float = 3.0, pipe_write: str = ''):
    while True:
        if ProcessManager.get_pid(name):
            time.sleep(interval)
            continue

        proc = launch_program(**launch_kwargs)
        if pipe_write:
            proc.stdin.write(pipe_write.encode())
            proc.stdin.close()
        time.sleep(interval)


def launch_program(launch_cmd: str, program_path: str, console_mode: bool, verbose: bool = False) -> subprocess.Popen:
    cwd = os.getcwd()
    path, program = os.path.split(program_path)
    ProcessManager.kill(program)

    proc = subprocess.Popen(
        launch_cmd.format(program), cwd=path,
        shell=True, startupinfo=subprocess_startup_info(console_mode),
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )

    os.chdir(cwd)

    if verbose:
        print(launch_cmd.format(program), path, os.getcwd())

    return proc
