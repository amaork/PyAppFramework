# -*- coding: utf-8 -*-
import typing
import collections
import matplotlib.axes
matplotlib.use('Qt5Agg')
from PySide2 import QtWidgets
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from ..gui.widget import BasicWidget
from .canvas import CustomCanvas, ChartAxesAttribute
__all__ = ['TimelineChartView', 'ChartLine']
ChartLine = collections.namedtuple('ChartLine', 'name tag style max')


class TimelineChartView(BasicWidget):
    def __init__(self, attr: ChartAxesAttribute, canvas_kwargs: dict = None, parent: QtWidgets.QWidget = None):
        self._attribute = attr
        self._canvas_kwargs = canvas_kwargs or dict()

        self.cnt = 0
        self.xdata = list()
        self.ydata = {line.tag: list() for line in self._attribute.lines}
        super(TimelineChartView, self).__init__(parent)

    def _initUi(self):
        self.canvas = CustomCanvas(**self._canvas_kwargs)
        layout = QtWidgets.QVBoxLayout()
        if self._attribute.with_toolbar:
            layout.addWidget(NavigationToolbar(self.canvas, self))
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def _updateChartCallback(self):
        pass

    def _updateChartPreCallback(self):
        pass

    def _updateChartPostCallback(self):
        pass

    def _updateAllDataCallback(self):
        pass

    def updateChart(self):
        self._updateChartPreCallback()

        with self.canvas.updateContextManager():
            for line in self._attribute.lines:
                self.canvas.axes.plot(self.xdata, self.ydata[line.tag], line.style, label=line.name)

            self._updateChartCallback()
            self.canvas.updateAxesAttribute(self._attribute)

        self._updateChartPostCallback()

    def appendData(self, data):
        self.cnt += 1
        self.xdata.append(self.cnt)
        for line in self._attribute.lines:
            self.ydata[line.tag].append(data[line.tag])

        self.updateChart()

    def updateAllData(self, sequence: typing.Sequence):
        self.cnt = len(sequence)
        self.xdata = list(range(1, self.cnt + 1))
        for line in self._attribute.lines:
            self.ydata[line.tag] = [data[line.tag] for data in sequence]

        self._updateAllDataCallback()
        self.updateChart()
