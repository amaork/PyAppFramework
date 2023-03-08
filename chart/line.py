# -*- coding: utf-8 -*-
import typing
import collections
import matplotlib.axes
matplotlib.use('Qt5Agg')
from PySide2 import QtWidgets

from ..gui.widget import BasicWidget
from .canvas import CustomCanvas, ChartAxesAttribute
__all__ = ['TimelineChartView', 'ChartLine']
ChartLine = collections.namedtuple('ChartLine', 'name tag style max')


class TimelineChartView(BasicWidget):
    def __init__(self, attr: ChartAxesAttribute, canvas_kwargs: dict = None, parent: QtWidgets.QWidget = None):
        self._attribute = attr
        self.cnt = 0
        self.xdata = list()
        self.ydata = {item.tag: list() for item in self._attribute.lines}
        self._canvas_kwargs = canvas_kwargs or dict()
        super(TimelineChartView, self).__init__(parent)

    def _initUi(self):
        self.canvas = CustomCanvas(**self._canvas_kwargs)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def updateChart(self):
        with self.canvas.updateContextManager():
            for line in self._attribute.lines:
                self.canvas.axes.plot(self.xdata, self.ydata[line.tag], line.style, label=line.name)

            self.canvas.updateAxesAttribute(self._attribute)

    def appendData(self, data: dict):
        self.cnt += 1
        self.xdata.append(self.cnt)
        for line in self._attribute.lines:
            self.ydata[line.tag].append(data.get(line.tag))

        self.updateChart()

    def updateAll(self, sequence: typing.Sequence[dict]):
        self.cnt = len(sequence)
        self.xdata = list(range(1, self.cnt + 1))
        for line in self._attribute.lines:
            self.ydata[line.tag] = [data.get(line.tag) for data in sequence]

        self.updateChart()
