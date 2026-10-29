# -*- coding: utf-8 -*-
import typing
from PySide2.QtWidgets import QMessageBox, QApplication, QWidget, QPushButton, QLabel
from PySide2.QtCore import Qt

__all__ = ['showQuestionBox', 'showMessageBox', 'showOnSPMsgBox',
           'MB_TYPES', 'MB_TYPE_ERR', 'MB_TYPE_INFO', 'MB_TYPE_WARN', 'MB_TYPE_QUESTION']

# Message box types
MB_TYPE_ERR = "error"
MB_TYPE_INFO = "info"
MB_TYPE_WARN = "warning"
MB_TYPE_QUESTION = "question"
MB_TYPES = (MB_TYPE_ERR, MB_TYPE_INFO, MB_TYPE_WARN, MB_TYPE_QUESTION)

# Unified message box geometry: pleasant wide ratio, short messages don't look cramped
MSGBOX_MIN_WIDTH = 380
MSGBOX_MIN_HEIGHT = 140
MSGBOX_MAX_TEXT_WIDTH = 560
# Content label min size that drives QMessageBox's fixed sizeHint to ~380x140
MSGBOX_MIN_TEXT_WIDTH = 280
MSGBOX_MIN_TEXT_HEIGHT = 60


def normalizeMsgBox(msg_box: QMessageBox):
    """Unify message box size: min 380x140, text wraps beyond 560px, content centered

    QMessageBox fixes its size from sizeHint in showEvent and ignores widget
    min/max size set beforehand, so drive the size via the content label's
    stylesheet min-width/min-height instead.
    """
    for label in msg_box.findChildren(QLabel):
        if label.objectName() not in ('qt_msgbox_label', 'qt_msgboxex_label'):
            continue

        label.setWordWrap(True)
        label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        # Estimate wrapped size: short text -> unified min box; long text -> grow and wrap
        fm = label.fontMetrics()
        line_height = fm.lineSpacing()
        text = label.text()
        text_width = fm.horizontalAdvance(text)
        wrap_width = MSGBOX_MIN_TEXT_WIDTH if text_width <= MSGBOX_MIN_TEXT_WIDTH \
            else min(text_width, MSGBOX_MAX_TEXT_WIDTH)

        lines = 0
        for paragraph in text.split('\n'):
            lines += max(1, -(-fm.horizontalAdvance(paragraph) // wrap_width))  # ceil

        label.setStyleSheet(
            'QLabel{min-width: %dpx; min-height: %dpx; padding: 6px 12px;}'
            % (wrap_width, max(MSGBOX_MIN_TEXT_HEIGHT, lines * line_height + 16))
        )

    # Vertically center the severity icon with the (vertically centered) text
    layout = msg_box.layout()
    if layout is not None:
        for i in range(layout.count()):
            item_widget = layout.itemAt(i).widget()
            if item_widget is not None and item_widget.objectName() in ('qt_msgbox_icon', 'qt_msgboxex_icon_label'):
                layout.setAlignment(item_widget, Qt.AlignVCenter | Qt.AlignHCenter)


def addExtraButtonsToMsgBox(msg_box: QMessageBox, extra_buttons: typing.Sequence[QPushButton] = None):
    extra_buttons = extra_buttons or list()
    if extra_buttons and all(isinstance(x, QPushButton) for x in extra_buttons):
        for btn in extra_buttons:
            msg_box.addButton(btn, QMessageBox.ButtonRole.YesRole)


def delExtraButtonsToMsgBox(msg_box: QMessageBox, extra_buttons: typing.Sequence[QPushButton] = None):
    extra_buttons = extra_buttons or list()
    if extra_buttons and all(isinstance(x, QPushButton) for x in extra_buttons):
        for btn in extra_buttons:
            msg_box.removeButton(btn)


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
        msg_box.setStandardButtons(buttons)
        normalizeMsgBox(msg_box)

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

    buttons = QMessageBox.Ok | QMessageBox.Cancel if msg_type == MB_TYPE_QUESTION else QMessageBox.Ok

    try:
        icon, default_title = __attributes.get(msg_type)
        title = title if title else parent.tr(default_title)

        msg_box.setIcon(icon)
        msg_box.setText(content)
        msg_box.setWindowTitle(title)
        addExtraButtonsToMsgBox(msg_box, extra_buttons)
        msg_box.setStandardButtons(buttons)
        normalizeMsgBox(msg_box)

        if msg_type == MB_TYPE_QUESTION:
            return msg_box.exec_() == QMessageBox.Ok
        else:
            msg_box.exec_()
            return True if msg_type == MB_TYPE_INFO else False
    except (TypeError, AttributeError) as e:
        print(f'showOnMsgBox:{e}')
        return False
    finally:
        delExtraButtonsToMsgBox(msg_box, extra_buttons)
        msg_box.setStandardButtons(buttons)
