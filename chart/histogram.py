# -*- coding: utf-8 -*-
import io
import numpy as np
import collections
from PIL import Image
import multiprocessing
from PySide2 import QtWidgets

from ..gui.widget import BasicWidget
from .canvas import CustomCanvas, ChartAxesAttribute
__all__ = ['image_to_np_array', 'HistogramType', 'HistogramChart']
__process_pipe = multiprocessing.Pipe()
HistogramType = collections.namedtuple('HistogramType', 'red green blue rgb grayscale')(*(
    'red', 'green', 'blue', 'rgb', 'grayscale'
))


def image_to_np_array(im_data: bytes, grayscale: bool) -> np.ndarray:
    im = Image.open(io.BytesIO(im_data))
    image = np.frombuffer(im.tobytes(), dtype=np.uint8).reshape(*im.size[::-1], 3)
    if not hasattr(image, 'ndim'):
        return image

    if not grayscale:
        return image

    image = image / 255
    factor = np.array([0.2125, 0.7154, 0.0721], dtype=np.float64)
    # factor = np.array([0.2989, 0.5870, 0.1140], dtype=np.float64)
    return image @ factor


class HistogramChart(BasicWidget):
    def __init__(self,
                 show_title: bool = False,
                 hide_x_axis: bool = True, hide_y_axis: bool = True,
                 canvas_kwargs: dict = None, parent: QtWidgets.QWidget = None):
        self.canvas_kwargs = canvas_kwargs or dict()
        self.canvas_kwargs.setdefault('figsize', (4, 3))
        self.canvas_kwargs.setdefault('tight_layout', True)
        self.axes_attr = ChartAxesAttribute(
            title_kwargs=dict(label='Histogram') if show_title else None,
            show_grid=False, hide_x_axis=hide_x_axis, hide_y_axis=hide_y_axis
        )
        super(HistogramChart, self).__init__(parent)

    def _initUi(self):
        self.canvas = CustomCanvas(**self.canvas_kwargs)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.canvas)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def _initStyle(self):
        self.canvas.updateAxesAttribute(self.axes_attr)

    def updateFromFile(self, filename: str, his_type: HistogramType = 'grayscale', grayscale_color: str = 'gray'):
        try:
            with open(filename, 'rb') as fp:
                data = fp.read()
            self.updateFromMem(data, his_type, grayscale_color)
        except OSError as e:
            print(f'{self.__class__.__name__}.updateFromFile error: {e}')

    def updateFromMem(self, im_data: bytes, his_type: HistogramType = 'grayscale', grayscale_color: str = 'gray'):
        colors = ("red", "green", "blue")

        # Convert image data to numpy array
        try:
            image = image_to_np_array(im_data, his_type == HistogramType.grayscale)
        except OSError:
            return

        # Get max color and figure color
        max_color = 1 if his_type == HistogramType.grayscale else 256
        figure_color = grayscale_color if his_type == HistogramType.grayscale else his_type

        # Draw histogram
        with self.canvas.updateContextManager():
            if his_type == HistogramType.rgb:
                for channel_id, color in enumerate(colors):
                    histogram, bin_edges = np.histogram(image[:, :, channel_id], bins=256, range=(0, 256))
                    self.canvas.axes.plot(bin_edges[0:-1], histogram, color=color)
            else:
                image = image if his_type == HistogramType.grayscale else image[:, :, colors.index(his_type)]
                histogram, bin_edges = np.histogram(image, bins=256, range=(0, max_color))
                self.canvas.axes.plot(bin_edges[0:-1], histogram, color=figure_color)
