# -*- coding: utf-8 -*-
import typing
import contextlib
import matplotlib.axes
import matplotlib.pyplot
matplotlib.use('Qt5Agg')
from matplotlib.figure import Figure
from ..core.datatype import DynamicObject
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

matplotlib.pyplot.rcParams['font.sans-serif'] = ['SimHei']
matplotlib.pyplot.rcParams['axes.unicode_minus'] = False
__all__ = ['CustomCanvas', 'ChartAxesAttribute']


class ChartAxesAttribute(DynamicObject):
    _properties = {'lines', 'title_kwargs',
                   'show_frame', 'show_grid',
                   'hide_x_axis', 'hide_y_axis',
                   'x_ticks', 'y_ticks', 'x_label', 'y_label', 'legend_kwargs', 'style', 'with_toolbar'}

    def __init__(self, **kwargs):
        kwargs.setdefault('style', 'k-')
        kwargs.setdefault('lines', [])
        kwargs.setdefault('x_ticks', [])
        kwargs.setdefault('y_ticks', [])
        kwargs.setdefault('x_label', '')
        kwargs.setdefault('y_label', '')
        kwargs.setdefault('show_grid', True)
        kwargs.setdefault('show_frame', True)
        kwargs.setdefault('hide_x_axis', False)
        kwargs.setdefault('hide_y_axis', False)
        kwargs.setdefault('with_toolbar', False)
        kwargs.setdefault('title_kwargs', None)
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

    def save(self, path: str, **kwargs):
        self.figure.savefig(path, **kwargs)
        return path

    @staticmethod
    def updateAxes(axes: matplotlib.axes.Axes, attribute: ChartAxesAttribute):
        if attribute.legend_kwargs:
            axes.legend(**attribute.legend_kwargs)

        if attribute.x_label:
            axes.set_xlabel(attribute.x_label)

        if attribute.y_label:
            axes.set_ylabel(attribute.y_label)

        if attribute.x_ticks:
            axes.set_xticks(attribute.x_ticks)

        if attribute.y_ticks:
            axes.set_yticks(attribute.y_ticks)

        if attribute.title_kwargs:
            axes.set_title(**attribute.title_kwargs)

        if attribute.hide_y_axis:
            axes.get_yaxis().set_visible(False)

        if attribute.hide_x_axis:
            axes.get_xaxis().set_visible(False)

        axes.set_frame_on(attribute.show_frame)

        if attribute.show_grid:
            axes.grid()

    def updateAxesAttribute(self, attribute: ChartAxesAttribute):
        self.updateAxes(self.axes, attribute)

    def generatePlotAndSave(self, xdata, ydata, path: str, attr: ChartAxesAttribute):
        self.updateAxesAttribute(attr)
        self.axes.plot(xdata, ydata, attr.style)
        return self.save(path)

    def generatePieAndSave(self, values, ingredients: typing.Sequence[str], path: str, attr: ChartAxesAttribute):
        self.updateAxesAttribute(attr)
        wedges, _, _ = self.axes.pie(values, autopct=f'%1.2f%%', textprops=dict(color="w"), startangle=45)
        self.axes.legend(wedges, ingredients, loc='center left', bbox_to_anchor=(1, 0, 0.5, 1))
        return self.save(path)
