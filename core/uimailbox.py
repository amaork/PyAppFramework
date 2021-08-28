# -*- coding: utf-8 -*-
from threading import Timer
from typing import Callable, Optional, Union
from PySide.QtCore import Qt, Signal, Slot, QObject, QTimer
from PySide.QtGui import QColor, QWidget, QStatusBar, QLabel

from .threading import ThreadConditionWrap
from ..gui.msgbox import MB_TYPES, showMessageBox, showQuestionBox

__all__ = ['UiMailBox', 'StatusBarMail', 'MessageBoxMail', 'QuestionBoxMail', 'WindowsTitleMail', 'CallbackFuncMail']


class BaseUiMail(object):
    def __init__(self, content: str = ""):
        if not isinstance(content, str):
            raise RuntimeError("Mail context TypeError:{0:s}".format(content.__class__.__name__))
        self.__content = content

    @property
    def content(self) -> str:
        return self.__content


class StatusBarMail(BaseUiMail):
    def __init__(self, color: Union[QColor, Qt.GlobalColor], content: str, timeout: int = 0):
        """ Show message on statusBar

        :param color: Message color
        :param content: Message content
        :param timeout: Message display timeout(second)
        :return:
        """
        super(StatusBarMail, self).__init__(content)
        if not isinstance(color, (QColor, Qt.GlobalColor)):
            raise RuntimeError("StatusBar mail color TypeError:{0:s}".format(color.__class__.__name__))

        if not isinstance(timeout, int):
            raise RuntimeError("StatusBar mail timeout TypeError:{0:s}".format(timeout.__class__.__name__))

        self.__color = QColor(color)
        self.__timeout = timeout * 1000

    @property
    def color(self) -> QColor:
        return self.__color

    @property
    def timeout(self) -> int:
        return self.__timeout


class MessageBoxMail(BaseUiMail):
    def __init__(self, type_: str, content: str, title: Optional[str] = None):
        """ Show QMessageBox with #title and #content

        :param type_: QMessageBox types ["info", "error", "warning"]
        :param content: QMessageBox context
        :param title: QMessageBox title
        :return:
        """
        super(MessageBoxMail, self).__init__(content)
        if type_ not in MB_TYPES:
            raise RuntimeError("MessageBox mail message type TypeError:{}".format(type_))

        self.__type = type_
        self.__title = title

    @property
    def type(self) -> str:
        return self.__type[:]

    @property
    def title(self) -> str or None:
        return self.__title


class WindowsTitleMail(BaseUiMail):
    def __init__(self, content: str):
        """Show a message on windows title with #content

        :param content: message content
        :return:
        """
        super(WindowsTitleMail, self).__init__(content)


class CallbackFuncMail(BaseUiMail):
    def __init__(self, func: Callable, timeout: int = 0, args: tuple = (), kwargs: Optional[dict] = None):
        """Call #func specified function with #args

        :param func: Callback function
        :param args:  Callback function args
        :param timeout: Callback function timeout
        :param kwargs: Callback function args
        :return:
        """
        super(CallbackFuncMail, self).__init__()
        if not hasattr(func, "__call__"):
            raise RuntimeError("CallbackFunc mail func TypeError is not callable")

        if not isinstance(timeout, int):
            raise RuntimeError("CallbackFunc mail timeout TypeError:{0:s}".format(timeout.__class__.__name__))

        self.__func = func
        self.__args = args
        self.__timeout = timeout
        self.__kwargs = kwargs if isinstance(kwargs, dict) else {}

    @property
    def callback(self) -> Callable:
        return self.__func

    @property
    def args(self) -> tuple:
        return self.__args

    @property
    def kwargs(self) -> dict:
        return self.__kwargs

    @property
    def timeout(self) -> int:
        return self.__timeout


class QuestionBoxMail(BaseUiMail):
    def __init__(self, content: str, title: str, condition: ThreadConditionWrap):
        """ Show QMessageBox.Question with #title and #content,
        when user clicked cancel or ok will pass result by ThreadConditionWrap

        :param content: QMessageBox.Question content
        :param title: QMessageBox.Question title
        :param condition: sync user click result ThreadConditionWrap.wait
        """
        super(QuestionBoxMail, self).__init__(content)
        if not isinstance(title, str):
            raise TypeError("{!r} title require a {!r} not {!r}".format(
                self.__class__.__name__, str.__name__, title.__class__.__name__))

        if not isinstance(condition, ThreadConditionWrap):
            raise TypeError("{!r} condition require a {!r} not {!r}".format(
                self.__class__.__name__, ThreadConditionWrap.__name__, title.__class__.__name__))

        self._title = title
        self._condition = condition
        self._condition.reset()

    @property
    def title(self) -> str:
        return self._title[:]

    def syncClickResult(self, result: bool):
        self._condition.finished(True if result else False)


class UiMailBox(QObject):
    hasNewMail = Signal(object)
    timingCallback = Signal(object, object)

    def __init__(self, parent: QWidget):
        """UI mail box using send and receive ui display message in thread

        :return:
        """
        super(UiMailBox, self).__init__(parent)
        if not isinstance(parent, QWidget):
            raise RuntimeError("UiMailBox needs a QWidget as parent")

        self.__parent = parent
        self.hasNewMail.connect(self.mailProcess)

    def send(self, mail: BaseUiMail) -> bool:
        """ Send a mail

        :param mail: mail
        :return:
        """
        if not isinstance(mail, BaseUiMail):
            return False

        try:
            self.hasNewMail.emit(mail)
            return True
        except RuntimeError:
            return False

    @Slot(object)
    def mailProcess(self, mail: BaseUiMail) -> bool:
        """Process ui mail

        :param mail: BaseUiMail
        :return:
        """
        if not isinstance(mail, BaseUiMail):
            return False

        # Show message on status bar
        if isinstance(mail, StatusBarMail):
            if hasattr(self.__parent, "ui") and hasattr(self.__parent.ui, "statusbar"):
                color = "rgb({0:d},{1:d},{2:d})".format(mail.color.red(), mail.color.green(), mail.color.blue())
                # Main windows has status bar
                if isinstance(self.__parent.ui.statusbar, QStatusBar):
                    self.__parent.ui.statusbar.showMessage(self.tr(mail.content), mail.timeout)
                    self.__parent.ui.statusbar.setStyleSheet(
                        "QStatusBar{"
                        "padding-left:8px;"
                        "background:rgba(0,0,0,0);"
                        "color:%s;"
                        "font-weight:bold;}" % color)
                # Widget has label named as statusbar
                elif isinstance(self.__parent.ui.statusbar, QLabel):
                    self.__parent.ui.statusbar.setText(self.tr(mail.content))
                    self.__parent.ui.statusbar.setStyleSheet(
                        "color:{0:s};padding-top:8px;font-weight:bold;".format(color)
                    )
                    # If specified timeout using callback function clear text
                    if mail.timeout:
                        status_mail = StatusBarMail(Qt.blue, "")
                        self.send(CallbackFuncMail(self.send, mail.timeout // 1000, args=(status_mail,)))
                else:
                    print("Do not support StatusBarMail!")

        # Show a message box
        elif isinstance(mail, MessageBoxMail):
            showMessageBox(self.__parent, mail.type, mail.content, mail.title)

        # Show a question box
        elif isinstance(mail, QuestionBoxMail):
            mail.syncClickResult(showQuestionBox(self.__parent, content=mail.content, title=mail.title))

        # Appended a message on windows title
        elif isinstance(mail, WindowsTitleMail):
            self.__parent.setWindowTitle(self.__parent.windowTitle() + self.tr("  {0:s}".format(mail.content)))

        # Callback function
        elif isinstance(mail, CallbackFuncMail):
            if mail.timeout:
                # Using QTimer improve security
                QTimer.singleShot(mail.timeout * 1000, lambda: mail.callback(*mail.args, **mail.kwargs))
            else:
                # Timeout is zero call it immediately
                mail.callback(*mail.args, **mail.kwargs)
        else:
            return False

        return True
