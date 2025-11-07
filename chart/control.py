# -*- coding: utf-8 -*-
import typing
import collections
from PySide2 import QtWidgets

from .canvas import ChartAxesAttribute
from ..core.datatype import DynamicObject
from .line import TimelineChart, ChartLine
__all__ = ['ControlChartView', 'CCResult', 'CCWarning', 'CCLineTag']


CCWarning = collections.namedtuple('OVResult', 'v threshold tag pos')
CCLineTag = collections.namedtuple('CCLineTag', 'V UCL LCL')(*'v ucl lcl'.split())


class CCResult(DynamicObject):
    _properties = {'v', 'ucl', 'lcl', 'cl'}

    def __init__(self, v, ucl, lcl, cl=None):
        super(CCResult, self).__init__(v=v, ucl=ucl, lcl=lcl, cl=cl)

    def __getitem__(self, item):
        return self.__dict__[item]


class ControlChartView(TimelineChart):
    def __init__(self, attr: ChartAxesAttribute, canvas_kwargs: dict = None,
                 show_warning: bool = False, max_density: int = 70, parent: QtWidgets.QWidget = None):
        self.warning_xdata = list()
        self.warning_ydata = list()
        self.max_density = max_density
        self.show_warning = show_warning
        self.v_line = ChartLine(name='V', style='ko-', tag=CCLineTag.V, max=0)
        self.ucl_line = ChartLine(name='UCL', style='r', tag=CCLineTag.UCL, max=0)
        self.lcl_line = ChartLine(name='LCL', style='b', tag=CCLineTag.LCL, max=0)
        self.max_density_v_line = ChartLine(name='V', style='k', tag=CCLineTag.V, max=0)

        attr.lines = [self.v_line, self.lcl_line, self.ucl_line]
        if attr.legend_kwargs is None:
            attr.legend_kwargs = dict(loc='upper right', bbox_to_anchor=(0.44, 0.67, 0.5, 0.5), ncol=4)
        super().__init__(attr=attr, canvas_kwargs=canvas_kwargs, parent=parent)

    def isLatestDataOverBounds(self) -> typing.Tuple[bool, CCWarning]:
        return self.isDataOverBounds(self.cnt - 1)

    def isDataOverBounds(self, x: int) -> typing.Tuple[bool, CCWarning]:
        try:
            v = self.ydata[self.v_line.tag][x]
            lcl = self.ydata[self.lcl_line.tag][x]
            ucl = self.ydata[self.ucl_line.tag][x]

            if v < lcl:
                return True, CCWarning(v, lcl, self.lcl_line.tag, x)

            if v > ucl:
                return True, CCWarning(v, ucl, self.ucl_line.tag, x)

            return False, CCWarning(None, None, None, x)
        except IndexError as e:
            return False, CCWarning(0.0, 0.0, f'{e}', x)

    def checkValueDensity(self):
        if self.cnt >= self.max_density:
            self._attribute.lines[0] = self.max_density_v_line
        else:
            self._attribute.lines[0] = self.v_line

    def _updateChartCallback(self):
        """Plot warning data to canvas"""
        if self.show_warning and self.warning_xdata and self.warning_ydata:
            self.canvas.axes.plot(self.warning_xdata, self.warning_ydata, 'ro', label='Warning')

    def _updateChartPreCallback(self):
        """Filter warning data"""
        for x in range(self.cnt):
            if self.isDataOverBounds(x)[0]:
                self.warning_xdata.append(self.xdata[x])
                self.warning_ydata.append(self.ydata[self.v_line.tag][x])

        self.checkValueDensity()

    def _updateAllDataCallback(self):
        self.warning_xdata.clear()
        self.warning_ydata.clear()
