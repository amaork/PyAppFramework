# -*- coding: utf-8 -*-
import math
import typing
import collections
from PIL import Image
from PySide2.QtCore import Qt
from PySide2 import QtCore, QtGui, QtWidgets

from .widget import ImageWidget
from ..misc.settings import Color
__all__ = ['CanvasWidget', 'ScalableCanvasWidget']


class CanvasWidget(QtWidgets.QWidget):
    # Fit to image width
    signalFitWidthRequest = QtCore.Signal()

    # Fit to window with
    signalFitWindowRequest = QtCore.Signal()

    # Scroll factor, orientation
    signalScrollRequest = QtCore.Signal(int, int)

    # Zoom out(delta < 0) or zoom in (delta > 0), focus position
    signalZoomRequest = QtCore.Signal(int, QtCore.QPoint)

    # Selected position and this position color(r, g, b)
    signalSelectRequest = QtCore.Signal(QtCore.QPoint, object)

    def __init__(self,
                 line_width: int = 10, big_img_scale_factor: int = 3,
                 paint_selected_pos: bool = False, select_pos_color: Color = (0, 255, 0),
                 parent: QtWidgets.QWidget = None):
        super(CanvasWidget, self).__init__(parent)
        self.__line_width = line_width
        self.__scale_factor = 1.0
        self.__image_scale_factor = 1
        self.__paint_selected_pos = paint_selected_pos
        self.__big_img_scale_factor = big_img_scale_factor
        self.__selected_pos_color = QtGui.QColor(*select_pos_color)

        self.__current_image_name = ''
        self.__image = Image.Image()
        self.__pixmap = QtGui.QPixmap()
        self.__painter = QtGui.QPainter()

        self.__selected_pos = list()
        self.__highlight_pos = QtCore.QPoint()
        self.__latest_clicked_pos = QtCore.QPoint()

        self.__timer = QtCore.QTimer()
        self.__timer.setInterval(200)
        self.__timer.timeout.connect(self.slotSingleClicked)

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.WheelFocus)

    def sizeHint(self) -> QtCore.QSize:
        return self.minimumSizeHint()

    def minimumSizeHint(self) -> QtCore.QSize:
        if self.__pixmap:
            return self.__scale_factor * self.__pixmap.size()
        return super(CanvasWidget, self).minimumSizeHint()

    @property
    def pixmap_width(self) -> int:
        return self.__pixmap.width()

    @property
    def pixmap_height(self) -> int:
        return self.__pixmap.height()

    @property
    def current_image_name(self) -> str:
        return self.__current_image_name

    def getPositionColor(self, pos: QtCore.QPoint) -> QtGui.QColor:
        return self.__image.getpixel((pos.x(), pos.y()))[:3]

    def isSelectable(self, pos: QtCore.QPoint) -> bool:
        return 0 <= pos.x() < self.__pixmap.width() and 0 <= pos.y() < self.__pixmap.height()

    def setScale(self, factor: float):
        self.__scale_factor = factor
        self.adjustSize()
        self.update()

    def remap2RealPos(self, pos: QtCore.QPoint) -> QtCore.QPoint:
        return pos * self.__image_scale_factor

    def remap2CanvasPos(self, pos: QtCore.QPoint) -> QtCore.QPoint:
        return pos / self.__image_scale_factor

    def transformPos(self, point):
        """Convert from widget-logical coordinates to painter-logical ones."""
        return point / self.__scale_factor - self.offsetToCenter()

    def offsetToCenter(self):
        s = self.__scale_factor
        area = super(CanvasWidget, self).size()
        w, h = self.__pixmap.width() * s, self.__pixmap.height() * s
        aw, ah = area.width(), area.height()
        x = (aw - w) / (2 * s) if aw > w else 0
        y = (ah - h) / (2 * s) if ah > h else 0
        return QtCore.QPoint(x, y)

    def slotClearImage(self):
        self.__current_image_name = ''
        self.__image = Image.Image()
        self.__pixmap = QtGui.QPixmap()
        self.slotClearAllSelect()

    def slotLoadImage(self, path: str, fit_window: bool = True, sel_pos: typing.List[QtCore.QPoint] = None) -> str:
        self.__selected_pos = sel_pos or list()
        self.__highlight_pos = QtCore.QPoint()

        reader = QtGui.QImageReader(path)
        reader.setAutoTransform(True)
        reader.setDecideFormatFromContent(True)
        reader.setScaledSize(ImageWidget.scaleBigImage(reader.size(), factor=self.__big_img_scale_factor))

        image = reader.read()
        if image.isNull():
            return reader.errorString()

        try:
            self.__image = Image.open(path)
        except Exception as e:
            return f'{e}'

        self.__current_image_name = path
        self.__pixmap = QtGui.QPixmap.fromImage(image)
        self.__image_scale_factor = 1 if self.__pixmap.width() == self.__image.size[0] else self.__big_img_scale_factor

        if fit_window:
            self.signalFitWindowRequest.emit()

        self.update()
        return ''

    def slotSingleClicked(self):
        self.__timer.stop()
        pos = self.__latest_clicked_pos
        if self.isSelectable(pos):
            real_pos = self.remap2RealPos(pos)
            self.__selected_pos.append(real_pos)
            self.signalSelectRequest.emit(real_pos, self.getPositionColor(real_pos))
            self.update()

    def slotClearAllSelect(self):
        self.__highlight_pos = QtCore.QPoint()
        self.__selected_pos.clear()
        self.update()

    def slotDeleteSelect(self, pos: QtCore.QPoint):
        try:
            idx = self.__selected_pos.index(pos)
        except ValueError:
            return
        else:
            del self.__selected_pos[idx]
            if self.__highlight_pos == pos:
                self.__highlight_pos = QtCore.QPoint()
            self.update()

    def slotHighlightSelect(self, pos: QtCore.QPoint):
        if pos in self.__selected_pos:
            self.__highlight_pos = self.remap2CanvasPos(pos)
            self.update()

    def enterEvent(self, event: QtCore.QEvent) -> None:
        pos = self.transformPos(QtGui.QCursor.pos())
        self.setCursor(QtGui.QCursor(Qt.CrossCursor if self.isSelectable(pos) else Qt.ForbiddenCursor))

    def leaveEvent(self, event: QtCore.QEvent) -> None:
        self.setCursor(QtGui.QCursor(Qt.ArrowCursor))

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        if not self.__pixmap:
            return super(CanvasWidget, self).paintEvent(event)

        p = self.__painter
        p.begin(self)

        # Pixmap
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setRenderHint(QtGui.QPainter.HighQualityAntialiasing)
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        p.scale(self.__scale_factor, self.__scale_factor)
        p.translate(self.offsetToCenter())
        p.drawPixmap(0, 0, self.__pixmap)

        # Pos
        if self.__paint_selected_pos:
            for pos in [self.remap2CanvasPos(p) for p in self.__selected_pos]:
                r, g, b = self.getPositionColor(self.remap2RealPos(pos))
                fg_color = QtGui.QColor(255 - r, 255 - g, 255 - b)

                p.setPen(QtGui.QPen(fg_color))
                p.drawLine(pos.x() - self.__line_width, pos.y(), pos.x() + self.__line_width, pos.y())
                p.drawLine(pos.x(), pos.y() - self.__line_width, pos.x(), pos.y() + self.__line_width)

                if pos == self.__highlight_pos:
                    p.setBrush(QtGui.QBrush(self.__selected_pos_color))
                    n = QtCore.QPoint(pos.x() - self.__line_width, pos.y() - self.__line_width)
                    p.drawEllipse(QtCore.QRectF(n, QtCore.QSize(self.__line_width * 2, self.__line_width * 2)))

        p.end()

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        mods = event.modifiers()
        delta = event.angleDelta()
        if QtCore.Qt.ControlModifier == mods:
            # with Ctrl/Command key
            # zoom
            self.signalZoomRequest.emit(delta.y(), event.pos())
        else:
            # scroll
            self.signalScrollRequest.emit(delta.x(), QtCore.Qt.Horizontal)
            self.signalScrollRequest.emit(delta.y(), QtCore.Qt.Vertical)

        event.accept()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        pos = self.transformPos(event.localPos())
        self.setCursor(QtGui.QCursor(Qt.CrossCursor if self.isSelectable(pos) else Qt.ForbiddenCursor))

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        self.__latest_clicked_pos = self.transformPos(event.localPos()).toPoint()
        self.__timer.start()

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        self.__timer.stop()
        self.signalFitWidthRequest.emit() if event.button() == Qt.LeftButton else self.signalFitWindowRequest.emit()


class ScalableCanvasWidget(QtWidgets.QScrollArea):
    signalRequestFitWidth = QtCore.Signal()
    signalRequestFitWindow = QtCore.Signal()
    signalZoomFactorChanged = QtCore.Signal(int)
    signalPositionSelected = QtCore.Signal(QtCore.QPoint, object)

    ZoomValue = collections.namedtuple('ZoomValue', 'mode value')
    ZoomMode = collections.namedtuple('ZoomMode', 'FitWindow FitWidth ManualZoom')(*range(3))

    def __init__(self, **kwargs):
        super(ScalableCanvasWidget, self).__init__(kwargs.get('parent'))
        self.canvas = CanvasWidget(**kwargs)
        self.setWidget(self.canvas)
        self.setWidgetResizable(True)

        # filename: ZoomValue
        self.__zoom_value = 100
        self.__zoom_value_records = {}
        self.__zoom_mode = self.ZoomMode.FitWindow

        self.__scroll_values = {Qt.Horizontal: {}, Qt.Vertical: {}}
        self.__scale_functions = {
            self.ZoomMode.FitWidth: lambda: 1.0,
            self.ZoomMode.ManualZoom: lambda: 1.0,
            self.ZoomMode.FitWindow: self.scaleFitWindow,
        }
        self.__scroll_bars = {Qt.Vertical: self.verticalScrollBar(), Qt.Horizontal: self.horizontalScrollBar()}

        # Pass by signals
        self.canvas.signalSelectRequest.connect(self.signalPositionSelected)
        self.canvas.signalFitWidthRequest.connect(self.signalRequestFitWidth)
        self.canvas.signalFitWindowRequest.connect(self.signalRequestFitWindow)

        self.canvas.signalZoomRequest.connect(self.slotHandleZoomRequest)
        self.canvas.signalScrollRequest.connect(self.slotHandleScrollRequest)

    @property
    def filename(self) -> str:
        return self.canvas.current_image_name

    def addZoom(self, increment: float = 1.1):
        zoom_value = self.__zoom_value * increment
        zoom_func = math.ceil if increment > 1.0 else math.floor

        self.__zoom_mode = self.ZoomMode.ManualZoom
        self.signalZoomFactorChanged.emit(zoom_func(zoom_value))

    def adjustScale(self):
        factor = self.__scale_functions[self.__zoom_mode]()
        zoom_value = int(100 * factor)
        self.signalZoomFactorChanged.emit(zoom_value)
        # self.zoom_value_records[self.filename] = self.ZoomValue(self.zoom_mode, zoom_value)

    def setScroll(self, orientation: int, value: int):
        self.__scroll_bars[orientation].setValue(value)
        self.__scroll_values[orientation][self.filename] = value

    def scaleFitWindow(self) -> float:
        if not self.canvas.pixmap_width:
            return 1.0

        # So that no scrollbars are generated
        e = 2.0
        w1 = self.width() - e
        h1 = self.height() - e
        a1 = w1 / h1

        # Calculate a new scale value based on the pixmap's aspect ratio.
        w2 = self.canvas.pixmap_width
        h2 = self.canvas.pixmap_height
        a2 = w2 / h2

        return w1 / w2 if a2 >= a1 else h1 / h2

    def slotClear(self):
        self.__zoom_value_records.clear()
        self.__scroll_values[Qt.Vertical].clear()
        self.__scroll_values[Qt.Horizontal].clear()

    def slotClearImage(self):
        self.canvas.slotClearImage()

    def slotClearAllSelect(self):
        self.canvas.slotClearAllSelect()

    def slotDeleteSelect(self, pos: QtCore.QPoint):
        self.canvas.slotDeleteSelect(pos)

    def slotHighlightSelect(self, pos: QtCore.QPoint):
        self.canvas.slotHighlightSelect(pos)

    def slotFitWidth(self, enabled):
        self.__zoom_mode = self.ZoomMode.FitWidth if enabled else self.ZoomMode.ManualZoom
        self.adjustScale()

    def slotFitWindow(self, enable: bool):
        self.__zoom_mode = self.ZoomMode.FitWindow if enable else self.ZoomMode.ManualZoom
        self.adjustScale()

    def slotPaintCanvas(self, value: int):
        self.__zoom_value = value
        self.canvas.setScale(0.01 * value)
        self.__zoom_value_records[self.filename] = self.ZoomValue(self.__zoom_mode, value)

    def slotRestoreZoomPosition(self, filename: str):
        if filename in self.__zoom_value_records:
            self.__zoom_mode = self.__zoom_value_records[filename].mode
            self.signalZoomFactorChanged.emit(self.__zoom_value_records[filename].value)

    def slotRestoreScrollPosition(self, filename: str):
        if filename in self.__scroll_values[Qt.Vertical]:
            self.__scroll_bars[Qt.Vertical].setValue(self.__scroll_values[Qt.Vertical].get(filename))

        if filename in self.__scroll_values[Qt.Horizontal]:
            self.__scroll_bars[Qt.Horizontal].setValue(self.__scroll_values[Qt.Horizontal].get(filename))

    def slotHandleZoomRequest(self, delta: int, pos: QtCore.QPoint):
        canvas_width_old = self.canvas.width()
        self.addZoom(0.9 if delta < 0 else 1.1)

        canvas_width_new = self.canvas.width()
        if canvas_width_old != canvas_width_new:
            canvas_scale_factor = canvas_width_new / canvas_width_old

            x_shift = round(pos.x() * canvas_scale_factor) - pos.x()
            y_shift = round(pos.y() * canvas_scale_factor) - pos.y()

            self.setScroll(
                Qt.Horizontal,
                self.__scroll_bars[Qt.Horizontal].value() + x_shift,
            )
            self.setScroll(
                Qt.Vertical,
                self.__scroll_bars[Qt.Vertical].value() + y_shift,
            )

    def slotHandleScrollRequest(self, delta: int, orientation: int):
        units = -delta * 0.1
        bar = self.__scroll_bars[orientation]
        self.setScroll(orientation, bar.value() + bar.singleStep() * units)

    def slotLoadImage(self, image: str, selected_positions: typing.List[QtCore.QPoint] = None):
        self.canvas.slotLoadImage(image, image not in self.__zoom_value_records, selected_positions)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        if self.__zoom_mode != self.ZoomMode.ManualZoom:
            self.adjustScale()
        super(ScalableCanvasWidget, self).resizeEvent(event)
