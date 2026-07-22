# -*- coding: utf-8 -*-
import typing
from PySide2 import QtWidgets, QtCore
from ..misc.windpi import thread_dpi_awareness, is_windows
__all__ = ['MousePositionPicker']


class MousePositionPicker(QtCore.QObject):
    """Pick screen coordinate, a floating tooltip follows the mouse and shows current position.

    Left button: pick (emit signalPicked), Esc: cancel (emit signalCancelled).
    Coordinates are physical pixels, not affected by app high-dpi setting.
    """
    signalPicked = QtCore.Signal(int, int)
    signalCancelled = QtCore.Signal()

    PollIntervalMs = 30
    LabelOffset = 16

    def __init__(self, parent: typing.Optional[QtCore.QObject] = None):
        super().__init__(parent)
        self.__armed = False
        self.__dpi_context = None
        self.__timer = QtCore.QTimer(self)
        self.__label = QtWidgets.QLabel(
            None, QtCore.Qt.ToolTip | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint
        )
        self.__label.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self.__label.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)
        self.__label.setStyleSheet('background: yellow; color: black; padding: 2px;')
        self.__timer.timeout.connect(self.__poll)

    def isActive(self) -> bool:
        return self.__timer.isActive()

    def start(self):
        if not is_windows() or self.isActive():
            return

        self.__armed = False
        self.__dpi_context = thread_dpi_awareness()
        self.__dpi_context.__enter__()
        self.__label.show()
        self.__timer.start(self.PollIntervalMs)

    def stop(self):
        self.__timer.stop()
        self.__label.hide()
        if self.__dpi_context:
            self.__dpi_context.__exit__(None, None, None)
            self.__dpi_context = None

    def __poll(self):
        import pyautogui as pg
        import win32api
        import win32con

        x, y = pg.position()
        self.__label.setText(f'{x}, {y}')
        self.__label.adjustSize()

        # Flip to the other side of cursor when near screen edge
        screen_w, screen_h = pg.size()
        label_x = x + self.LabelOffset if x + self.LabelOffset + self.__label.width() <= screen_w else \
            x - self.LabelOffset - self.__label.width()
        label_y = y + self.LabelOffset if y + self.LabelOffset + self.__label.height() <= screen_h else \
            y - self.LabelOffset - self.__label.height()
        self.__label.move(label_x, label_y)

        if win32api.GetAsyncKeyState(win32con.VK_ESCAPE) & 0x8000:
            self.stop()
            self.signalCancelled.emit()
            return

        # Arm only after the button click that started picking is released, avoid instant self-trigger
        if not (win32api.GetAsyncKeyState(win32con.VK_LBUTTON) & 0x8000):
            self.__armed = True
        elif self.__armed:
            self.stop()
            self.signalPicked.emit(x, y)
