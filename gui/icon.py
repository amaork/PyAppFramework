# -*- coding: utf-8 -*-
from PySide.QtCore import QSize
from PySide.QtGui import QLabel, QPixmap
__all__ = ['StatusIcon', 'MultiStatusIcon', 'DynamicStatusIcon']


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

        self.status = 0
        self.icons = icons
        self.setPixmap(QPixmap(self.icons[0]))
        self.setScaledContents(True)
        self.setFixedSize(size)
        self.setToolTip(tips)

    def resetStatus(self):
        self.status = 0
        self.setPixmap(QPixmap(self.icons[self.status]))

    def switchStatus(self):
        self.status = (self.status + 1) % len(self.icons)
        self.setPixmap(QPixmap(self.icons[self.status]))

    def changeStatus(self, st):
        if not 0 <= st < len(self.icons):
            return

        self.status = st
        self.setPixmap(QPixmap(self.icons[self.status]))


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
