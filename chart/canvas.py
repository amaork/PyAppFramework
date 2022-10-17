# -*- coding: utf-8 -*-
import contextlib
import matplotlib.axes
matplotlib.use('Qt5Agg')
from matplotlib.figure import Figure
from ..core.datatype import DynamicObject
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
__all__ = ['CustomCanvas', 'ChartAxesAttribute']


class ChartAxesAttribute(DynamicObject):
    _properties = {'lines', 'title_kwargs',
                   'show_frame', 'show_grid',
                   'y_ticks', 'x_ticks', 'x_label', 'y_label', 'legend_kwargs'}

    def __init__(self, **kwargs):
        kwargs.setdefault('lines', [])
        kwargs.setdefault('x_ticks', [])
        kwargs.setdefault('x_label', '')
        kwargs.setdefault('y_label', '')
        kwargs.setdefault('show_grid', True)
        kwargs.setdefault('show_frame', True)
        kwargs.setdefault('legend_kwargs', None)
        super(ChartAxesAttribute, self).__init__(**kwargs)


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

    def updateAxesAttribute(self, attribute: ChartAxesAttribute):
        if attribute.legend_kwargs:
            self.axes.legend(**attribute.legend_kwargs)

        if attribute.x_label:
            self.axes.set_xlabel(attribute.x_label)

        if attribute.y_label:
            self.axes.set_ylabel(attribute.y_label)

        if attribute.x_ticks:
            self.axes.set_xticks(attribute.x_ticks)

        if attribute.y_ticks:
            self.axes.set_yticks(attribute.y_ticks)

        if attribute.title_kwargs:
            self.axes.set_title(**attribute.title_kwargs)

        self.axes.set_frame_on(attribute.show_frame)

        if attribute.show_grid:
            self.axes.grid()
