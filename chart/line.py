# -*- coding: utf-8 -*-
import collections
import matplotlib.axes
matplotlib.use('Qt5Agg')
from PySide2 import QtWidgets

from .canvas import CustomCanvas
from ..gui.widget import BasicWidget
from ..core.datatype import DynamicObject
__all__ = ['TimelineChartView', 'ChartLine', 'ChartAxesAttribute']
ChartLine = collections.namedtuple('ChartLine', 'name tag color max')


class ChartAxesAttribute(DynamicObject):
    _properties = {'lines', 'title_kwargs',
                   'show_frame', 'show_grid',
                   'y_ticks', 'x_ticks', 'x_label', 'y_label', 'legend_kwargs'}

    def __init__(self, **kwargs):
        kwargs.setdefault('x_ticks', [])
        kwargs.setdefault('x_label', '')
        kwargs.setdefault('y_label', '')
        kwargs.setdefault('show_grid', True)
        kwargs.setdefault('show_frame', True)
        kwargs.setdefault('legend_kwargs', None)
        super(ChartAxesAttribute, self).__init__(**kwargs)


class TimelineChartView(BasicWidget):
    def __init__(self, attr: ChartAxesAttribute, canvas_kwargs: dict = None, parent: QtWidgets.QWidget = None):
        self._attribute = attr
        self._canvas_kwargs = canvas_kwargs or dict()
        super(TimelineChartView, self).__init__(parent)

    def _initUi(self):
        self.canvas = CustomCanvas(**self._canvas_kwargs)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def _initData(self):
        self.cnt = 0
        self.xdata = list()
        self.ydata = {item.tag: list() for item in self._attribute.lines}

    def _initStyle(self):
        pass

    def _initThreadAndTimer(self):
        pass

    def slotUpdatePlot(self, data: dict):
        self.cnt += 1
        self.xdata.append(self.cnt)

        with self.canvas.updateContextManager():
            for line in self._attribute.lines:
                self.ydata[line.tag].append(data.get(line.tag))
                self.canvas.axes.plot(self.xdata, self.ydata[line.tag], line.color, label=line.name)

            self.updateAxes(self.canvas.axes, self._attribute)

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

        axes.set_frame_on(attribute.show_frame)

        if attribute.show_grid:
            axes.grid()
