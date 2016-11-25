# -*- coding: utf-8 -*-
import os
import signal

__all__ = ['get_pid', 'process_start', 'process_stop', 'process_kill']


def get_pid(name):
    """Get process id

    :param name: process name
    :return: pid list
    """
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
    if not cmd.endswith('&'):
        cmd += ' &'

    while not lst and retry > 0:
        lst = get_pid(name)
        if not lst:
            os.system(cmd)
            retry -= 1
            continue

        for pid in lst:
            os.kill(pid, signal.SIGCONT if start else signal.SIGSTOP)


def process_start(name, cmd):
    process_control(name, cmd, True)
    return True if get_pid(name) else False


def process_stop(name, cmd):
    process_control(name, cmd, False)
    return True if get_pid(name) else False


def process_kill(name):
    for pid in get_pid(name):
        os.kill(pid, signal.SIGKILL)

    return True if not get_pid(name) else False
