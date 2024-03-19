# -*- coding: utf-8 -*-
import typing
from PySide2.QtGui import QColor
from PySide2.QtCore import Qt, Signal, Slot, QObject, QTimer
from PySide2.QtWidgets import QWidget, QStatusBar, QLabel, QMessageBox, QProgressBar

from ..core.timer import Task, Tasklet
from ..core.threading import ThreadConditionWrap

from .dialog import ProgressDialog
from .msgbox import MB_TYPES, showMessageBox, showQuestionBox, showOnSPMsgBox

__all__ = ['UiMailBox', 'StatusBarMail', 'MessageBoxMail', 'QuestionBoxMail',
           'WindowsTitleMail', 'CallbackFuncMail', 'ProgressBarMail', 'StatusBarLabelMail', 'StatusBarProgressBarMail']


class BaseUiMail(object):
    def __init__(self, content: str = ""):
        if not isinstance(content, str):
            raise RuntimeError("Mail context TypeError:{0:s}".format(content.__class__.__name__))
        self.__content = content

    @property
    def content(self) -> str:
        return self.__content

    @content.setter
    def content(self, content: str):
        self.__content = content


class StatusBarMail(BaseUiMail):
    def __init__(self, color: typing.Union[QColor, Qt.GlobalColor], content: str, timeout: int = 0):
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
    def __init__(self, type_: str, content: str, title: typing.Optional[str] = None, tag: str = ''):
        """ Show QMessageBox with #title and #content

        :param type_: QMessageBox types ["info", "error", "warning"]
        :param content: QMessageBox context
        :param title: QMessageBox title
        :param tag: specified which message box showing on
        :return:
        """
        super(MessageBoxMail, self).__init__(content)
        if type_ not in MB_TYPES:
            raise RuntimeError("MessageBox mail message type TypeError:{}".format(type_))

        self.__tag = tag
        self.__type = type_
        self.__title = title

    @property
    def tag(self) -> str:
        return self.__tag[:]

    @property
    def type(self) -> str:
        return self.__type[:]

    @property
    def title(self) -> str or None:
        return self.__title


class WindowsTitleMail(BaseUiMail):
    def __init__(self, content: str):
        """Show a message on window title with #content

        :param content: message content
        :return:
        """
        super(WindowsTitleMail, self).__init__(content)


class CallbackFuncMail(BaseUiMail):
    def __init__(self, func: typing.Callable, timeout: int = 0,
                 args: tuple = (), kwargs: typing.Optional[dict] = None,
                 callback_check: typing.Callable[[], bool] = lambda: True):
        """Call #func specified function with #args

        :param func: Callback function
        :param args:  Callback function args
        :param timeout: Callback function timeout
        :param kwargs: Callback function args
        :param callback_check: before invoke func will invoke this first,
        only if callback_check return true then will invoke func
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
        self.__callback_check = callback_check
        self.__kwargs = kwargs if isinstance(kwargs, dict) else {}

    @property
    def timeout(self) -> int:
        return self.__timeout

    def execute(self, check: bool):
        if not check or self.__callback_check():
            self.__func(*self.__args, **self.__kwargs)


class QuestionBoxMail(BaseUiMail):
    def __init__(self, content: str, title: str, condition: ThreadConditionWrap):
        """ Show QMessageBox.Question with #title and #content,
        when user clicked cancel or ok will pass result by ThreadConditionWrap

        :param content: QMessageBox.Question content
        :param title: QMessageBox.Question title
        :param condition: sync user click result ThreadConditionWrap::wait
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

    @property
    def title(self) -> str:
        return self._title[:]

    def syncClickResult(self, result: bool):
        self._condition.finished(True if result else False)


class ProgressBarMail(BaseUiMail):
    def __init__(self, progress: int, content: str = '', title: str = '',
                 closeable: bool = False, increase: int = 0, interval: float = 0.0,
                 cancelable: bool = False, cancel_callback: typing.Callable = None, force: bool = False):
        """
        ProgressBarMail
        :param progress: progress bar initial value
        :param content: progress bar display content
        :param title: progress bar display title
        :param closeable: is progress bar closeable
        :param increase: progress bar auto increase value
        :param interval: progress bar auto increase interval
        :param cancelable: is progress bar cancelable
        :param cancel_callback: cancel callback
        :param force: force flush UI process event
        """
        super(ProgressBarMail, self).__init__(content)
        self.increase = increase
        self.interval = interval

        self.title = title
        self.force = force
        self._progress = progress
        self.closeable = closeable
        self.cancelable = cancelable
        self.cancel_callback = cancel_callback

    @property
    def progress(self) -> int:
        return self._progress

    @progress.setter
    def progress(self, progress: int):
        self._progress = progress

    def autoIncreaseEnabled(self) -> bool:
        return self.increase > 0 and self.interval > 0.0

    @classmethod
    def create(cls, total_time: float, **kwargs):
        def calc(interval_: float) -> typing.Tuple[float, int]:
            increase_ = int(100 / (total_time / interval_))
            if increase_ < 1.0:
                return calc(interval_ * 10)

            return interval_, increase_

        interval, increase = calc(0.1)
        kwargs.setdefault('progress', 1)
        return cls(interval=interval, increase=increase, **kwargs)


class StatusBarWidgetMail(BaseUiMail):
    def __init__(self, widget_type, widget_name: str):
        super(StatusBarWidgetMail, self).__init__('')
        self._widget_type = widget_type
        self._widget_name = widget_name

    @property
    def widget_type(self):
        return self._widget_type

    @property
    def widget_name(self) -> str:
        return self._widget_name


class StatusBarLabelMail(StatusBarWidgetMail):
    def __init__(self, name: str, text: str, cls=QLabel):
        super(StatusBarLabelMail, self).__init__(cls, name)
        self._text = text

    @property
    def text(self) -> str:
        return self._text


class StatusBarProgressBarMail(StatusBarWidgetMail):
    def __init__(self, name: str, progress: int, increase: int = 0, interval: float = 0.0, auto_hidden: bool = True):
        super(StatusBarProgressBarMail, self).__init__(QProgressBar, name)
        self._increase = increase
        self._interval = interval
        self._progress = progress
        self._auto_hidden = auto_hidden

    @property
    def progress(self) -> int:
        return self._progress

    @progress.setter
    def progress(self, progress: int):
        self._progress = progress

    @property
    def increase(self) -> int:
        return self._increase

    @property
    def interval(self) -> float:
        return self._interval

    @property
    def autoHidden(self) -> bool:
        return self._auto_hidden

    def autoIncreaseEnabled(self) -> bool:
        return self._increase > 0 and self.interval > 0.0


class UiMailBox(QObject):
    hasNewMail = Signal(object)

    def __init__(self, parent: QWidget,
                 msg_content_format: typing.Callable[[str], str] = lambda x: x, **process_bar_kwargs):
        """UiMail box using send and receive ui display message in thread

        :return:
        """
        super(UiMailBox, self).__init__(parent)
        if not isinstance(parent, QWidget):
            raise RuntimeError("UiMailBox needs a QWidget as parent")

        self.__parent = parent
        self.__bind_msg_boxs = dict()
        self.__progress = ProgressDialog(parent=parent, **process_bar_kwargs)

        self.__pai_task = Task.create_tid()
        self.__sb_pai_task = Task.create_tid()
        self.__msg_content_format = msg_content_format
        self.__tasklet = Tasklet(schedule_interval=0.1, name=self.__class__.__name__)

        self.hasNewMail.connect(self.mailProcess)

    def bindMsgBox(self, msg_box: QMessageBox, tag: str):
        self.__bind_msg_boxs[tag] = msg_box

    def getProgressValue(self) -> int:
        return self.__progress.value()

    def taskProgressAutoIncrease(self, task: Task, mail: ProgressBarMail):
        new_value = self.__progress.value() + mail.increase

        self.send(ProgressBarMail(
            progress=new_value, content=mail.content, title=mail.title, closeable=mail.closeable, force=mail.force)
        )

        if new_value >= self.__progress.maximum():
            task.delete()

    def findStatusWidget(self, type_, name: str):
        statusbar = self.__parent.findChild(QStatusBar)
        if not isinstance(statusbar, QStatusBar):
            return None

        return statusbar.findChild(type_, name)

    def send(self, mail: BaseUiMail) -> bool:
        """ Send a mail

        :param mail: mail
        :return:
        """
        if not isinstance(mail, BaseUiMail):
            return False

        if isinstance(mail, (MessageBoxMail, QuestionBoxMail)):
            mail.content = self.__msg_content_format(mail.content)

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
            if mail.tag not in self.__bind_msg_boxs:
                showMessageBox(self.__parent, mail.type, mail.content, mail.title)
            else:
                showOnSPMsgBox(self.__parent, self.__bind_msg_boxs.get(mail.tag), mail.type, mail.content, mail.title)

        # Show a question box
        elif isinstance(mail, QuestionBoxMail):
            mail.syncClickResult(showQuestionBox(self.__parent, content=mail.content, title=mail.title))

        elif isinstance(mail, ProgressBarMail):
            if mail.progress:
                if mail.title:
                    self.__progress.setWindowTitle(mail.title)
                self.__progress.setLabelText(mail.content)
                self.__progress.setCloseable(mail.closeable)
                self.__progress.setCancelable(mail.cancelable)
                self.__progress.setCancelCallback(mail.cancel_callback)
                self.__progress.setProgress(mail.progress, force=mail.force)

                if mail.autoIncreaseEnabled():
                    self.__pai_task = self.__tasklet.add_task(
                        Task(
                            func=self.taskProgressAutoIncrease,
                            timeout=mail.interval, periodic=True, args=(mail,), id_ignore_args=True
                        )
                    )
            else:
                self.__tasklet.del_task(self.__pai_task.id)
                self.__progress.slotHidden()
                self.__progress.setCloseable(True)
        elif isinstance(mail, StatusBarProgressBarMail):
            pb = self.findStatusWidget(mail.widget_type, mail.widget_name)
            if isinstance(pb, QProgressBar):
                pb.setValue(mail.progress)
                if mail.progress >= pb.maximum():
                    pb.setHidden(True)
                    self.__tasklet.del_task(self.__sb_pai_task.id)
                elif mail.autoIncreaseEnabled():
                    mail.progress += mail.increase
                    self.__tasklet.del_task(self.__sb_pai_task.id)
                    self.__sb_pai_task = self.__tasklet.add_task(Task(
                        func=self.send, timeout=mail.interval, args=(mail,), id_ignore_args=False
                    ))
        # Appended a message on window title
        elif isinstance(mail, WindowsTitleMail):
            self.__parent.setWindowTitle(self.__parent.windowTitle() + self.tr("  {0:s}".format(mail.content)))
        elif isinstance(mail, StatusBarLabelMail):
            label = self.findStatusWidget(mail.widget_type, mail.widget_name)
            if hasattr(label, 'setText'):
                label.setText(mail.text)
        # Callback function
        elif isinstance(mail, CallbackFuncMail):
            if mail.timeout:
                # Using QTimer improve security
                # noinspection PyUnresolvedReferences
                QTimer.singleShot(mail.timeout * 1000, lambda: mail.execute(check=True))
            else:
                # Timeout is zero call it immediately
                mail.execute(check=False)
        else:
            return False

        return True
