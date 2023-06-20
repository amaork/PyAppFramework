# -*- coding: utf-8 -*-
from .msgbox import *
from ..misc.debug import ExceptionHandle
from ..core.threading import ThreadConditionWrap
from .mailbox import UiMailBox, MessageBoxMail, QuestionBoxMail
__all__ = ['ExceptionHandleMsgBox', 'showMessageBoxFromThread', 'showQuestionBoxFromThread']


class ExceptionHandleMsgBox(ExceptionHandle):
    def __init__(self, mailbox: UiMailBox, **kwargs):
        super(ExceptionHandleMsgBox, self).__init__(
            param=mailbox, callback=lambda mbox, msg:
            mbox.send(MessageBoxMail(MB_TYPE_ERR, msg, f'{self.__class__.__name__}')), **kwargs
        )


def showMessageBoxFromThread(mailbox: UiMailBox, msg_type: str, content: str, title: str = '') -> bool:
    mailbox.send(MessageBoxMail(msg_type, content, title))
    return True if msg_type == MB_TYPE_INFO else False


def showQuestionBoxFromThread(mailbox: UiMailBox, content: str, title: str = '') -> bool:
    condition = ThreadConditionWrap()
    mailbox.send(QuestionBoxMail(content, title, condition))
    return condition.wait()
