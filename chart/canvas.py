# -*- coding: utf-8 -*-
import contextlib
import matplotlib.axes
matplotlib.use('Qt5Agg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
__all__ = ['CustomCanvas']


class CustomCanvas(FigureCanvas):
    def __init__(self, **kwargs):
        kwargs.setdefault('dpi', 100)
        kwargs.setdefault('facecolor', (0.941, 0.941, 0.941))
        self.fig = Figure(**kwargs)
        self.axes = self.fig.add_subplot()
        super(CustomCanvas, self).__init__(self.fig)

    @contextlib.contextmanager
    def updateContextManager(self):
        self.axes.cla()
        yield
        self.draw()
