# -*- coding: utf-8 -*-
import abc
import typing
import numpy as np
import matplotlib.axes
matplotlib.use('Qt5Agg')
from PySide2 import QtWidgets

from .canvas import CustomCanvas
from ..gui.widget import BasicWidget
__all__ = ['DonutPieChart', 'BasicPieChart', 'LegendPieChart']


class BasePieChart(BasicWidget):
    def __init__(self, ingredients: typing.Sequence[str], annotation_suffix: str = '',
                 show_detail: bool = True, precision: int = 2, kwargs: dict = None, canvas_kwargs: dict = None,
                 parent: QtWidgets.QWidget = None):
        self.kwargs = kwargs or {}
        self.canvas_kwargs = canvas_kwargs or {}

        self.precision = precision
        self.show_detail = show_detail
        self.ingredients = ingredients
        self.annotation_suffix = annotation_suffix
        super().__init__(parent)

    def _initUi(self):
        self.canvas = CustomCanvas(**self.canvas_kwargs)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        self.setMinimumSize(self.sizeHint())

    def _initStyle(self):
        self.canvas.axes.set_aspect('equal')

    def _initData(self):
        self.updateChart([1] * len(self.ingredients))

    def formatValue(self, v: typing.Union[int, float]) -> str:
        v = v if isinstance(v, int) else round(v, self.precision)
        return f'{v}{self.annotation_suffix}'

    @abc.abstractmethod
    def drawPie(self, values: typing.Sequence[typing.Union[int, float]]):
        pass

    def getAnnotation(self, values: typing.Sequence[typing.Union[int, float]]):
        if not self.show_detail:
            return self.ingredients
        else:
            return [f'{a}({self.formatValue(v)})' for a, v in zip(self.ingredients, values)]

    def updateChart(self, values: typing.Sequence[typing.Union[int, float]]):
        if len(values) != len(self.ingredients):
            return

        with self.canvas.updateContextManager():
            self.drawPie(values)


class DonutPieChart(BasePieChart):
    def drawPie(self, values: typing.Sequence[typing.Union[int, float]]):
        annotation = self.getAnnotation(values)
        wedges, texts = self.canvas.axes.pie(values, wedgeprops=dict(width=0.5), startangle=-40, **self.kwargs)
        bbox_props = dict(boxstyle="square, pad=0.3", fc="w", ec="k", lw=0.72)
        kw = dict(arrowprops=dict(arrowstyle="-"), bbox=bbox_props, zorder=0, va="center")

        for i, p in enumerate(wedges):
            ang = (p.theta2 - p.theta1) / 2. + p.theta1
            y = np.sin(np.deg2rad(ang))
            x = np.cos(np.deg2rad(ang))
            connection_style = "angle,angleA=0,angleB={}".format(ang)
            horizontal_alignment = {-1: "right", 1: "left"}[int(np.sign(x))]
            kw["arrowprops"].update({"connectionstyle": connection_style})
            self.canvas.axes.annotate(
                annotation[i], xy=(x, y), xytext=(1.35 * np.sign(x), 1.4 * y),
                horizontalalignment=horizontal_alignment, **kw
            )


class BasicPieChart(BasePieChart):
    def drawPie(self, values: typing.Sequence[typing.Union[int, float]]):
        autopct = f'%1.{self.precision}f%%' if self.show_detail else None
        self.canvas.axes.pie(values,
                             labels=self.ingredients, shadow=True, startangle=90, autopct=autopct, **self.kwargs)


class LegendPieChart(BasePieChart):
    def drawPie(self, values: typing.Sequence[typing.Union[int, float]]):
        autopct = f'%1.{self.precision}f%%' if self.show_detail else None
        wedges, _, _ = self.canvas.axes.pie(values, autopct=autopct, textprops=dict(color="w"), **self.kwargs)

        self.canvas.axes.legend(
            wedges, self.ingredients, loc="center left", bbox_to_anchor=(1, 0, 0.5, 1)
        )
