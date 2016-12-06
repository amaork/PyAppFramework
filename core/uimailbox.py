# -*- coding: utf-8 -*-

import types
from PySide.QtGui import QColor, QWidget
from PySide.QtCore import Qt, Signal, Slot, QObject
from ..gui.msgbox import MB_TYPES, showMessageBox


__all__ = ['UiMailBox', 'StatusBarMail', 'MessageBoxMail', 'WindowsTitleMail', 'CallbackFuncMail']


class BaseUiMail(object):
    def __init__(self, context=""):
        assert isinstance(context, types.StringTypes), "Mail context TypeError:{0:s}".format(type(context))
        self.__context = context

    @property
    def context(self):
        return self.__context


class StatusBarMail(BaseUiMail):
    def __init__(self, color, context, timeout=0):
        """ Show message on statusBar

        :param color: Message color
        :param context: Message context
        :param timeout: Message display time(second)
        :return:
        """
        super(StatusBarMail, self).__init__(context)
        assert isinstance(color, (QColor, Qt.GlobalColor)), "StatusBar mail color TypeError:{0:s}".format(type(color))
        assert isinstance(timeout, int), "StatusBar mail timeout TypeError:{0:s}".format(type(timeout))
        self.__color = QColor(color)
        self.__timeout = timeout * 1000

    @property
    def color(self):
        return self.__color

    @property
    def timeout(self):
        return self.__timeout


class MessageBoxMail(BaseUiMail):
    def __init__(self, type_, title, context):
        """ Show QMessageBox with #title and #context

        :param type_: QMessageBox types ["info", "error", "warning"]
        :param title: QMessageBox title
        :param context: QMessageBox context
        :return:
        """
        super(MessageBoxMail, self).__init__(context)
        assert type_ in MB_TYPES, "MessageBox mail message type TypeError:{0:s}".format(type(type_))
        assert isinstance(title, types.StringTypes), "MessageBox mail title TypeError:{0:s}".format(type(title))

        self.__type = type_
        self.__title = title

    @property
    def type(self):
        return self.__type

    @property
    def title(self):
        return self.__title


class WindowsTitleMail(BaseUiMail):
    def __init__(self, context):
        """Show a message on windows title with #context

        :param context: message context
        :return:
        """
        super(WindowsTitleMail, self).__init__(context)


class CallbackFuncMail(BaseUiMail):
    def __init__(self, func, args=(), kwargs=None):
        """Call #func specified function with #args

        :param func: Callback function
        :param args:  Callback function args
        :param kwargs: Callback function args
        :return:
        """
        super(CallbackFuncMail, self).__init__()
        assert hasattr(func, "__call__"), "CallbackFunc mail func TypeError is not callable"
        assert isinstance(args, tuple), "CallbackFunc mail args TypeError:{0:s}".format(type(args))
        self.__func = func
        self.__args = args
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


class UiMailBox(QObject):
    hasNewMail = Signal(object)

    def __init__(self, parent):
        """UI mail box using send and receive ui display message in thread

        :return:
        """
        super(UiMailBox, self).__init__(parent)
        assert isinstance(parent, QWidget), "UiMailBox needs a QWidget:{0:s} as parent".format(type(parent))
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
                self.__parent.ui.statusbar.showMessage(self.tr(mail.context), mail.timeout)
                self.__parent.ui.statusbar.setStyleSheet(
                    "QStatusBar{"
                    "padding-left:8px;"
                    "background:rgba(0,0,0,0);"
                    "color:%s;"
                    "font-weight:bold;}" % color)
        # Show a message box
        elif isinstance(mail, MessageBoxMail):
            showMessageBox(self.__parent, mail.type, mail.title, mail.context)

        # Appended a message on windows title
        elif isinstance(mail, WindowsTitleMail):
            self.__parent.setWindowTitle(self.__parent.windowTitle() + self.tr("  {0:s}".format(mail.context)))

        # Callback function
        elif isinstance(mail, CallbackFuncMail):
            mail.callback(*mail.args, **mail.kwargs)
        else:
            return False

        return True
