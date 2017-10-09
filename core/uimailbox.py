# -*- coding: utf-8 -*-
import types
from threading import Timer
from ..gui.msgbox import MB_TYPES, showMessageBox
from PySide.QtCore import Qt, Signal, Slot, QObject
from PySide.QtGui import QColor, QWidget, QStatusBar, QLabel
__all__ = ['UiMailBox', 'StatusBarMail', 'MessageBoxMail', 'WindowsTitleMail', 'CallbackFuncMail']


class BaseUiMail(object):
    def __init__(self, context=""):
        if not isinstance(context, types.StringTypes):
            raise RuntimeError("Mail context TypeError:{0:s}".format(context.__class__.__name__))
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
    def __init__(self, type_, title, context):
        """ Show QMessageBox with #title and #context

        :param type_: QMessageBox types ["info", "error", "warning"]
        :param title: QMessageBox title
        :param context: QMessageBox context
        :return:
        """
        super(MessageBoxMail, self).__init__(context)
        if type_ not in MB_TYPES:
            raise RuntimeError("MessageBox mail message type TypeError:{}".format(type_))

        if not isinstance(title, types.StringTypes):
            raise RuntimeError("MessageBox mail title TypeError:{0:s}".format(title.__class__.__name__))

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
    def __init__(self, func, timeout=0, *args, **kwargs):
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
        self.__kwargs = kwargs
        self.__timeout = timeout

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
                    self.__parent.ui.statusbar.showMessage(self.tr(mail.context), mail.timeout)
                    self.__parent.ui.statusbar.setStyleSheet(
                        "QStatusBar{"
                        "padding-left:8px;"
                        "background:rgba(0,0,0,0);"
                        "color:%s;"
                        "font-weight:bold;}" % color)
                # Widget has label named as statusbar
                elif isinstance(self.__parent.ui.statusbar, QLabel):
                    self.__parent.ui.statusbar.setText(self.tr(mail.context))
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
            showMessageBox(self.__parent, mail.type, mail.title, mail.context)

        # Appended a message on windows title
        elif isinstance(mail, WindowsTitleMail):
            self.__parent.setWindowTitle(self.__parent.windowTitle() + self.tr("  {0:s}".format(mail.context)))

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
