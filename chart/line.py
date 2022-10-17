# -*- coding: utf-8 -*-
import collections
import matplotlib.axes
matplotlib.use('Qt5Agg')
from PySide2 import QtWidgets

from ..gui.widget import BasicWidget
from .canvas import CustomCanvas, ChartAxesAttribute
__all__ = ['TimelineChartView', 'ChartLine']
ChartLine = collections.namedtuple('ChartLine', 'name tag color max')


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

    def updateChart(self, data: dict):
        self.cnt += 1
        self.xdata.append(self.cnt)

        with self.canvas.updateContextManager():
            for line in self._attribute.lines:
                self.ydata[line.tag].append(data.get(line.tag))
                self.canvas.axes.plot(self.xdata, self.ydata[line.tag], line.color, label=line.name)

            self.canvas.updateAxesAttribute(self._attribute)
