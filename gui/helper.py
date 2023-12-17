# -*- coding: utf-8 -*-
import typing
import threading

from .msgbox import *
from ..misc.utils import wait_timeout
from ..misc.debug import ExceptionHandle
from ..core.threading import ThreadConditionWrap
from .mailbox import UiMailBox, MessageBoxMail, QuestionBoxMail, ProgressBarMail
__all__ = [
    'ExceptionHandleMsgBox', 'ProgressBarContextManager',
    'showMessageBoxFromThread', 'showQuestionBoxFromThread', 'saveFileToFSFromThread', 'loadFileFromFSFromThread']


class ExceptionHandleMsgBox(ExceptionHandle):
    def __init__(self, mailbox: UiMailBox, **kwargs):
        super(ExceptionHandleMsgBox, self).__init__(
            param=mailbox, callback=lambda mbox, msg:
            mbox.send(MessageBoxMail(MB_TYPE_ERR, msg, f'{self.__class__.__name__}')), **kwargs
        )


class ProgressBarContextManager:
    def __init__(self, mailbox: UiMailBox,
                 content: str, title: str = '',
                 init: int = 1, increase: int = 1, interval: float = 1.0, timeout: int = 0xffffffff,
                 ignore_exceptions: bool = False, catch_exceptions: typing.Sequence[typing.Type[Exception]] = None):
        self.__init = init
        self.__title = title
        self.__mailbox = mailbox
        self.__content = content
        self.__increase = increase
        self.__interval = interval
        self.__max_timeout = timeout
        self.__operation_finish = threading.Event()
        self.__ignore_exceptions = ignore_exceptions
        self.__catch_exceptions = catch_exceptions or list()

    def __timeoutDetection(self):
        try:
            wait_timeout(self.__operation_finish.is_set, timeout=self.__max_timeout, desc=self.__content)
        except RuntimeError:
            self.set_closeable()
            self.__sendProgressBarMail(0)
            self.__mailbox.send(MessageBoxMail(MB_TYPE_ERR, '操作超时，请检查', f'{self.__title}超时'))

    def __sendProgressBarMail(self, progress: int, closeable: bool = False):
        self.__mailbox.send(ProgressBarMail(
            progress, self.__content, self.__title,
            closeable=closeable, increase=self.__increase, interval=self.__interval
        ))

    def set_closeable(self):
        self.__sendProgressBarMail(self.__mailbox.getProgressValue(), True)

    def update(self, progress: int):
        self.__sendProgressBarMail(progress)

    def __enter__(self):
        self.__sendProgressBarMail(self.__init)
        threading.Thread(target=self.__timeoutDetection, daemon=True).start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__operation_finish.set()
        self.__sendProgressBarMail(0)
        if exc_type in self.__catch_exceptions:
            self.__mailbox.send(MessageBoxMail(MB_TYPE_ERR, f'{exc_val}', f'{self.__title}失败'))
            return True

        return self.__ignore_exceptions


def showMessageBoxFromThread(mailbox: UiMailBox, msg_type: str, content: str, title: str = '') -> bool:
    mailbox.send(MessageBoxMail(msg_type, content, title))
    return True if msg_type == MB_TYPE_INFO else False


def showQuestionBoxFromThread(mailbox: UiMailBox, content: str, title: str = '') -> bool:
    condition = ThreadConditionWrap()
    mailbox.send(QuestionBoxMail(content, title, condition))
    return condition.wait()


def saveFileToFSFromThread(data: bytes, path: str, mailbox: UiMailBox) -> bool:
    try:
        with open(path, 'wb') as fp:
            fp.write(data)
    except OSError as e:
        mailbox.send(MessageBoxMail(MB_TYPE_ERR, f'Save file to filesystem failed: {e}'))
        return False
    else:
        mailbox.send(MessageBoxMail(MB_TYPE_INFO, f'{path}'))
        return True


def loadFileFromFSFromThread(path: str, mailbox: UiMailBox) -> bytes:
    try:
        with open(path, 'rb') as fp:
            return fp.read()
    except OSError as e:
        mailbox.send(MessageBoxMail(MB_TYPE_ERR, f'Load file from filesystem failed: {e}'))
        return bytes()
