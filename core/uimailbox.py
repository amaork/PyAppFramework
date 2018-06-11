# -*- coding: utf-8 -*-
from threading import Timer
from ..gui.msgbox import MB_TYPES, showMessageBox
from PySide.QtCore import Qt, Signal, Slot, QObject
from PySide.QtGui import QColor, QWidget, QStatusBar, QLabel
__all__ = ['UiMailBox', 'StatusBarMail', 'MessageBoxMail', 'WindowsTitleMail', 'CallbackFuncMail']


class BaseUiMail(object):
    def __init__(self, content=""):
        if not isinstance(content, str):
            raise RuntimeError("Mail context TypeError:{0:s}".format(content.__class__.__name__))
        self.__content = content

    @property
    def content(self):
        return self.__content


class StatusBarMail(BaseUiMail):
    def __init__(self, color, content, timeout=0):
        """ Show message on statusBar

        :param color: Message color
        :param content: Message content
        :param timeout: Message display time(second)
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
    def color(self):
        return self.__color

    @property
    def timeout(self):
        return self.__timeout


class MessageBoxMail(BaseUiMail):
    def __init__(self, type_, content, title=None):
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
    def type(self):
        return self.__type

    @property
    def title(self):
        return self.__title


class WindowsTitleMail(BaseUiMail):
    def __init__(self, content):
        """Show a message on windows title with #content

        :param content: message content
        :return:
        """
        super(WindowsTitleMail, self).__init__(content)


class CallbackFuncMail(BaseUiMail):
    def __init__(self, func, timeout=0, args=(), kwargs=None):
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
    def callback(self):
        return self.__func

    @property
    def args(self):
        return self.__args

    @property
    def kwargs(self):
        return self.__kwargs

    @property
    def timeout(self):
        return self.__timeout


class UiMailBox(QObject):
    hasNewMail = Signal(object)

    def __init__(self, parent):
        """UI mail box using send and receive ui display message in thread

        :return:
        """
        super(UiMailBox, self).__init__(parent)
        if not isinstance(parent, QWidget):
            raise RuntimeError("UiMailBox needs a QWidget as parent")

        self.__parent = parent
        self.hasNewMail.connect(self.mailProcess)

    def send(self, mail):
        """ Send a mail

        :param mail: mail
        :return:
        """
        if not isinstance(mail, BaseUiMail):
            return False

        self.hasNewMail.emit(mail)
        return True

    @Slot(object)
    def mailProcess(self, mail):
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
                        self.send(CallbackFuncMail(self.send, mail.timeout / 1000, args=(status_mail,)))
                else:
                    print("Do not support StatusBarMail!")

        # Show a message box
        elif isinstance(mail, MessageBoxMail):
            showMessageBox(mail.type, mail.content, mail.title)

        # Appended a message on windows title
        elif isinstance(mail, WindowsTitleMail):
            self.__parent.setWindowTitle(self.__parent.windowTitle() + self.tr("  {0:s}".format(mail.content)))

        # Callback function
        elif isinstance(mail, CallbackFuncMail):
            if mail.timeout:
                timer = Timer(mail.timeout, mail.callback, mail.args, mail.kwargs)
                timer.start()
            else:
                # Timeout is zero call it immediately
                mail.callback(*mail.args, **mail.kwargs)
        else:
            return False

        return True
