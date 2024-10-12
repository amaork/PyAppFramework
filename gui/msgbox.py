# -*- coding: utf-8 -*-
import typing
from PySide2.QtWidgets import QMessageBox, QApplication, QWidget, QPushButton

__all__ = ['showQuestionBox', 'showMessageBox', 'showOnSPMsgBox',
           'MB_TYPES', 'MB_TYPE_ERR', 'MB_TYPE_INFO', 'MB_TYPE_WARN', 'MB_TYPE_QUESTION']

# Message box types
MB_TYPE_ERR = "error"
MB_TYPE_INFO = "info"
MB_TYPE_WARN = "warning"
MB_TYPE_QUESTION = "question"
MB_TYPES = (MB_TYPE_ERR, MB_TYPE_INFO, MB_TYPE_WARN, MB_TYPE_QUESTION)


def addExtraButtonsToMsgBox(msg_box: QMessageBox, extra_buttons: typing.Sequence[QPushButton] = None):
    extra_buttons = extra_buttons or list()
    if extra_buttons and all(isinstance(x, QPushButton) for x in extra_buttons):
        for btn in extra_buttons:
            msg_box.addButton(btn, QMessageBox.ButtonRole.YesRole)


def showQuestionBox(parent: QWidget, content: str, title: str = '') -> bool:
    """ Show a Question message box and return result

    :param parent: parent widget
    :param content: Message content
    :param title: Message title
    :return: if press ok return true, else return false
    """

    return showMessageBox(parent, MB_TYPE_QUESTION, content, title)


def showMessageBox(parent: QWidget, msg_type: str, content: str,
                   title: str = '', extra_buttons: typing.Sequence[QPushButton] = None) -> bool:
    """Show a QMessage box

    :param parent: parent widget
    :param msg_type: Message type
    :param content: Message content
    :param title: Message title
    :param extra_buttons: show extra pushbuttonS
    :return: result
    """
    # noinspection PyTypeChecker
    __attributes = {
        MB_TYPE_ERR: (QMessageBox.Critical, QApplication.translate("msgbox", "Error", None)),
        MB_TYPE_WARN: (QMessageBox.Warning, QApplication.translate("msgbox", "Warning", None)),
        MB_TYPE_INFO: (QMessageBox.Information, QApplication.translate("msgbox", "Info", None)),
        MB_TYPE_QUESTION: (QMessageBox.Question, QApplication.translate("msgbox", "Confirm", None))
    }

    try:
        icon, default_title = __attributes.get(msg_type)
        title = title if title else parent.tr(default_title)
        buttons = QMessageBox.Ok | QMessageBox.Cancel if msg_type == MB_TYPE_QUESTION else QMessageBox.Ok
        msg_box = QMessageBox(icon, title, content, buttons, parent=parent)
        addExtraButtonsToMsgBox(msg_box, extra_buttons)

        if msg_type == MB_TYPE_QUESTION:
            return msg_box.exec_() == QMessageBox.Ok
        else:
            msg_box.exec_()
            return True if msg_type == MB_TYPE_INFO else False
    except TypeError as e:
        print(f'showMessageBox:{e}')
        return False


def showOnSPMsgBox(parent: QWidget, msg_box: QMessageBox, msg_type: str,
                   content: str, title: str = '', extra_buttons: typing.Sequence[QPushButton] = None) -> bool:
    # noinspection PyTypeChecker
    __attributes = {
        MB_TYPE_ERR: (QMessageBox.Critical, QApplication.translate("msgbox", "Error", None)),
        MB_TYPE_WARN: (QMessageBox.Warning, QApplication.translate("msgbox", "Warning", None)),
        MB_TYPE_INFO: (QMessageBox.Information, QApplication.translate("msgbox", "Info", None)),
        MB_TYPE_QUESTION: (QMessageBox.Question, QApplication.translate("msgbox", "Confirm", None))
    }

    try:
        icon, default_title = __attributes.get(msg_type)
        title = title if title else parent.tr(default_title)
        buttons = QMessageBox.Ok | QMessageBox.Cancel if msg_type == MB_TYPE_QUESTION else QMessageBox.Ok

        msg_box.setIcon(icon)
        msg_box.setText(content)
        msg_box.setWindowTitle(title)
        msg_box.setDefaultButton(buttons)
        addExtraButtonsToMsgBox(msg_box, extra_buttons)

        if msg_type == MB_TYPE_QUESTION:
            return msg_box.exec_() == QMessageBox.Ok
        else:
            msg_box.exec_()
            return True if msg_type == MB_TYPE_INFO else False
    except (TypeError, AttributeError) as e:
        print(f'showOnMsgBox:{e}')
        return False
