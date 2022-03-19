# -*- coding: utf-8 -*-
from PySide2.QtWidgets import QMessageBox, QApplication, QWidget

__all__ = ['showQuestionBox', 'showMessageBox',
           'MB_TYPES', 'MB_TYPE_ERR', 'MB_TYPE_INFO', 'MB_TYPE_WARN', 'MB_TYPE_QUESTION']

# Message box types
MB_TYPE_ERR = "error"
MB_TYPE_INFO = "info"
MB_TYPE_WARN = "warning"
MB_TYPE_QUESTION = "question"
MB_TYPES = (MB_TYPE_ERR, MB_TYPE_INFO, MB_TYPE_WARN, MB_TYPE_QUESTION)


def showQuestionBox(parent: QWidget, content: str, title: str = '') -> bool:
    """ Show a Question message box and return result

    :param parent: parent widget
    :param content: Message content
    :param title: Message title
    :return: if press ok return true, else return false
    """

    return showMessageBox(parent, MB_TYPE_QUESTION, content, title)


def showMessageBox(parent: QWidget, msg_type: str, content: str, title: str = '') -> bool:
    """Show a QMessage box

    :param parent: parent widget
    :param msg_type: Message type
    :param content: Message content
    :param title: Message title
    :return: result
    """
    # noinspection PyTypeChecker
    attributes = {
        MB_TYPE_ERR: (QMessageBox.Critical, QApplication.translate("msgbox", "Error", None)),
        MB_TYPE_WARN: (QMessageBox.Warning, QApplication.translate("msgbox", "Warning", None)),
        MB_TYPE_INFO: (QMessageBox.Information, QApplication.translate("msgbox", "Info", None)),
        MB_TYPE_QUESTION: (QMessageBox.Question, QApplication.translate("msgbox", "Confirm", None))
    }

    try:
        icon, default_title = attributes.get(msg_type)
        title = title if title else parent.tr(default_title)
        buttons = QMessageBox.Ok | QMessageBox.Cancel if msg_type == MB_TYPE_QUESTION else QMessageBox.NoButton
        msg = QMessageBox(icon, title, content, buttons, parent=parent)
        if msg_type == MB_TYPE_QUESTION:
            return msg.exec_() == QMessageBox.Ok
        else:
            msg.exec_()
            return True if msg_type == MB_TYPE_INFO else False
    except TypeError as e:
        print(f'showMessageBox:{e}')
        return False
