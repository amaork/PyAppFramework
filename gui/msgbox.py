#!/usr/bin/python
# -*- coding: utf-8 -*-
from PySide.QtGui import *

__all__ = ['showQuestionBox', 'showMessageBox', 'MB_TYPE_ERR', 'MB_TYPE_INFO', 'MB_TYPE_WARN']


# Message box types
MB_TYPE_ERR = "error"
MB_TYPE_INFO = "info"
MB_TYPE_WARN = "warning"
MB_TYPES = (MB_TYPE_ERR, MB_TYPE_INFO, MB_TYPE_WARN)


def showQuestionBox(parent, title, context):
    """ Show a Question message box and return result

    :param parent:Message parent
    :param title: Message title
    :param context: Message title
    :return:
    """

    # Type check
    if not isinstance(title, str) or not isinstance(context, str):
        return False

    ret = QMessageBox.question(parent, parent.tr(title), parent.tr(context), QMessageBox.Ok | QMessageBox.Cancel)

    return False if ret == QMessageBox.Cancel else True


def showMessageBox(parent, msg_type, context, title="", result=False):
    """Show a QMessage box

    :param parent: Message box parent
    :param msg_type: Message type
    :param context: Message context
    :param title: Message title
    :param result: result
    :return: result
    """

    # Type check
    if msg_type not in MB_TYPES or not isinstance(title, str) or not isinstance(context, str):
        return False

    # Using default title
    if len(title) == 0:
        title = msg_type[0].upper() + msg_type[1:]

    if msg_type == MB_TYPE_INFO:
        QMessageBox.information(parent, parent.tr(title), parent.tr(context))
    elif msg_type == MB_TYPE_ERR:
        QMessageBox.critical(parent, parent.tr(title), parent.tr(context))
    elif msg_type == MB_TYPE_WARN:
        QMessageBox.warning(parent, parent.tr(title), parent.tr(context))

    return result
