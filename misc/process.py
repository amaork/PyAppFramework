# -*- coding: utf-8 -*-
import os
import signal
import platform

_system = platform.system().lower()

__all__ = ['get_pid', 'process_start', 'process_stop', 'process_kill']


def get_pid(name):
    """Get process id

    :param name: process name
    :return: pid list
    """
    if _system == "windows":
        cmd = os.popen("tasklist | grep {0:s} | awk '{{ print $2 }}'".format(name))
    else:
        cmd = os.popen('pidof {0:s}'.format(name))

    data = cmd.read().strip()
    if not data:
        return []
    return [int(pid) for pid in data.split(' ')]


def process_control(name, cmd, start):
    """Control process

    :param name: process name for get_pid
    :param cmd: process start command
    :param start: True start, False stop
    :return:
    """
    retry = 3
    lst = list()
    assert isinstance(cmd, str), 'process cmd error!'

    # Make program running in background
    if _system == "windows":
        cmd = "start /b {0:s}".format(cmd)
    else:
        if not cmd.endswith('&'):
            cmd += ' &'

    while not lst and retry > 0:
        lst = get_pid(name)
        if not lst:
            os.system(cmd)
            retry -= 1
            continue

        if _system != "windows":
            for pid in lst:
                os.kill(pid, signal.SIGCONT if start else signal.SIGSTOP)


def process_start(name, cmd):
    process_control(name, cmd, True)
    return True if get_pid(name) else False


def process_stop(name, cmd):
    if _system == "windows":
        return process_kill(name)
    process_control(name, cmd, False)
    return True if get_pid(name) else False


def process_kill(name):
    kill_signal = signal.SIGILL if _system == "windows" else signal.SIGKILL
    for pid in get_pid(name):
        os.kill(pid, kill_signal)

    return True if not get_pid(name) else False
