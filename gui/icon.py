# -*- coding: utf-8 -*-
from PySide.QtCore import QSize
from PySide.QtGui import QLabel, QPixmap
__all__ = ['StatusIcon', 'MultiStatusIcon', 'DynamicStatusIcon', 'MultiStatusNamedIcon']


class StatusIcon(QLabel):
    def __init__(self, icon, size, tips=""):
        super(StatusIcon, self).__init__()

        self.setPixmap(QPixmap(icon))
        self.setScaledContents(True)
        self.setFixedSize(size)
        self.setToolTip(tips)


class MultiStatusIcon(QLabel):
    def __init__(self, icons, size, tips=""):
        super(MultiStatusIcon, self).__init__()
        if not isinstance(size, QSize):
            raise TypeError("size require a QSize type")

        if not isinstance(icons, (list, tuple)):
            raise TypeError("icons require a list or tuple type")

        if len(icons) == 1:
            raise ValueError("MultiStatusIcon at lease require two icons")

        self._status = 0
        self.icons = icons
        self.setPixmap(QPixmap(self.icons[0]))
        self.setScaledContents(True)
        self.setFixedSize(size)
        self.setToolTip(tips)

    def status(self):
        return self._status

    def resetStatus(self):
        self._status = 0
        self.setPixmap(QPixmap(self.icons[self._status]))

    def switchStatus(self):
        self._status = (self._status + 1) % len(self.icons)
        self.setPixmap(QPixmap(self.icons[self._status]))

    def changeStatus(self, st):
        if not 0 <= st < len(self.icons):
            return

        self._status = st
        self.setPixmap(QPixmap(self.icons[self._status]))


class MultiStatusNamedIcon(MultiStatusIcon):
    def __init__(self, named_icons, size, tips=""):
        if not isinstance(named_icons, dict):
            raise TypeError("named_icons require a dict type")

        self.__icons_name = tuple(named_icons.keys())
        super(MultiStatusNamedIcon, self).__init__(tuple(named_icons.values()), size, tips)

    def statusName(self):
        return self.__icons_name[self.status()]

    def changeStatusByName(self, name):
        return self.changeStatus(self.__icons_name.index(name))


class DynamicStatusIcon(MultiStatusIcon):
    def __init__(self, icons, size, tips="",  play_cycle=100, start=False):
        super(DynamicStatusIcon, self).__init__(icons, size, tips)
        self.__start_flag = start
        self.startTimer(play_cycle)

    def timerEvent(self, ev):
        if not self.__start_flag:
            return

        self.switchStatus()

    def stopPlay(self):
        self.__start_flag = False
        self.resetStatus()

    def startPlay(self):
        self.__start_flag = True
