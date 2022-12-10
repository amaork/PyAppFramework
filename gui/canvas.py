# -*- coding: utf-8 -*-
import math
import typing
import collections
from PIL import Image
from PySide2.QtCore import Qt
from PySide2 import QtCore, QtGui, QtWidgets

from .widget import ImageWidget
from ..misc.settings import Color
__all__ = ['CanvasWidget', 'ScalableCanvasWidget', 'canvas_init_helper', 'PaintMode', 'PaintShape']

PaintMode = collections.namedtuple('PaintMode', 'NONE Dot Line Rect Mixture')(*('none', 'dot', 'line', 'rect', 'mix'))
PaintShape = typing.Union[QtCore.QPoint, QtCore.QLine, QtCore.QRect]


class CanvasWidget(QtWidgets.QWidget):
    signalImageChanged = QtCore.Signal(str)

    # Fit to image width
    signalFitWidthRequest = QtCore.Signal()

    # Fit to window with
    signalFitWindowRequest = QtCore.Signal()

    # Scroll factor, orientation
    signalScrollRequest = QtCore.Signal(int, int)

    # Zoom out(delta < 0) or zoom in (delta > 0), focus position
    signalZoomRequest = QtCore.Signal(int, QtCore.QPoint)

    # Selected position and this position color(r, g, b)
    signalSelectRequest = QtCore.Signal(object, object)

    def __init__(self,
                 cursor_size: int = 20,
                 default_text: str = '',
                 change_cursor: bool = True,
                 double_click_timeout: int = 200,
                 enable_double_click_event: bool = True,
                 paint_mode: PaintMode = None, select_color: Color = (0, 255, 0),
                 big_img_shrink_filter: QtCore.QSize = QtCore.QSize(), big_img_shrink_factor: int = 2,
                 parent: QtWidgets.QWidget = None):
        """CanvasWidget

        @param cursor_size: define cursor size
        @param default_text: show default text when image not load yet
        @param change_cursor: enter/leave change cursor shape
        @param double_click_timeout: double click timeout, unit millisecond
        @param enable_double_click_event: enable double click emit signalFitWidthRequest/signalFitWindowRequest
        @param paint_mode: paint mode
        @param select_color: selected position color
        @param big_img_shrink_factor: big image shrink factor
        @param big_img_shrink_filter: image bigger than this size will auto shrink by big_img_shrink_factor
        @param parent:
        """
        super(CanvasWidget, self).__init__(parent)
        self.__line_width = cursor_size // 2
        self.__scale_factor = 1.0
        self.__image_scale_factor = 1
        self.__paint_mode = paint_mode
        self.__default_text = default_text
        self.__change_cursor = change_cursor
        self.__big_img_shrink_filter = big_img_shrink_filter
        self.__big_img_shrink_factor = big_img_shrink_factor

        self.__paint_color = QtGui.QColor()
        self.__select_color = QtGui.QColor(*select_color)
        self.__enable_double_clicked_event = enable_double_click_event

        self.__current_image_name = ''
        self.__image = Image.Image()
        self.__pixmap = QtGui.QPixmap()
        self.__painter = QtGui.QPainter()

        # Store selected dots image position
        self.__selected_pos = list()
        self.__drawing_lines = list()
        self.__drawing_rectangles = list()
        self.__cursor_pos = QtCore.QPoint()
        self.__highlight_shape = QtCore.QPoint()
        self.__latest_clicked_pos = QtCore.QPoint()

        self.__timer = QtCore.QTimer()
        self.__timer.setInterval(double_click_timeout)
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
    def image_size(self) -> QtCore.QSize:
        return QtCore.QSize(*self.__image.size)

    @property
    def pixmap_width(self) -> int:
        return self.__pixmap.width()

    @property
    def pixmap_height(self) -> int:
        return self.__pixmap.height()

    @property
    def current_image_name(self) -> str:
        return self.__current_image_name

    @property
    def sel_color(self) -> QtGui.QColor:
        return self.__select_color

    @sel_color.setter
    def sel_color(self, color: QtGui.QColor):
        if isinstance(color, QtGui.QColor):
            self.__select_color = color

    @property
    def paint_color(self) -> QtGui.QColor:
        return self.__paint_color

    @paint_color.setter
    def paint_color(self, color: QtGui.QColor):
        if isinstance(color, QtGui.QColor):
            self.__paint_color = color

    @property
    def cursor_size(self) -> int:
        return self.__line_width * 2

    @cursor_size.setter
    def cursor_size(self, size: int):
        if isinstance(size, int):
            self.__line_width = size // 2

    @property
    def paint_mode(self) -> PaintMode:
        return self.__paint_mode

    @paint_mode.setter
    def paint_mode(self, mode: PaintMode):
        if mode in PaintMode:
            self.__paint_mode = mode

    def getImageColor(self, image_pos: QtCore.QPoint) -> QtGui.QColor:
        """Get image specified position color"""
        return self.__image.getpixel((image_pos.x(), image_pos.y()))[:3]

    def getPaintColor(self, canvas_pos: QtCore.QPoint) -> QtGui.QColor:
        """Accordingly pos color decide paint line/rect color if paint color is specified just return paint color"""
        if self.__paint_color.isValid():
            return self.__paint_color
        else:
            r, g, b = self.getImageColor(self.remap2ImagePos(canvas_pos))
            return QtGui.QColor(255 - r, 255 - g, 255 - b)

    def isPaintDotMode(self) -> bool:
        return self.__paint_mode == PaintMode.Dot

    def isPaintLineMode(self) -> bool:
        return self.__paint_mode == PaintMode.Line

    def isPaintRectangleMode(self) -> bool:
        return self.__paint_mode == PaintMode.Rect

    def isPaintFinished(self) -> bool:
        return self.__selected_pos and len(self.__selected_pos) % 2 == 0

    def isPaintNotFinished(self) -> bool:
        return not self.isPaintFinished() and self.__selected_pos

    def isSelectable(self, canvas_pos: QtCore.QPoint) -> bool:
        """Check if pos is in canvas"""
        return self.__pixmap.rect().contains(QtCore.QPoint(canvas_pos.x(), canvas_pos.y()))

    def __cancelShapeDrawing(self):
        """Cancel current drawing shape"""
        if (self.isPaintLineMode() or self.isPaintRectangleMode()) and self.isPaintNotFinished():
            self.__selected_pos.remove(self.__selected_pos[-1])
            self.update()
            return True

        return False

    def __painterAutoColor(self, painter: QtGui.QPainter, canvas_pos: QtCore.QPoint):
        """Set paint color automatically by current canvas position color"""
        painter.setPen(QtGui.QPen(self.getPaintColor(canvas_pos)))

    def __drawSelectedRect(self, painter: QtGui.QPainter, rect: QtCore.QRect):
        self.__drawSelectedPoint(painter, rect.topLeft())
        self.__drawSelectedPoint(painter, rect.topRight())
        self.__drawSelectedPoint(painter, rect.bottomLeft())
        self.__drawSelectedPoint(painter, rect.bottomRight())

    def __drawSelectedLine(self, painter: QtGui.QPainter, line: QtCore.QLine):
        self.__drawSelectedPoint(painter, line.p1())
        self.__drawSelectedPoint(painter, line.p2())

    def __drawSelectedPoint(self, painter: QtGui.QPainter, pos: QtCore.QPoint):
        painter.setBrush(QtGui.QBrush(self.__select_color))
        n = QtCore.QPoint(pos.x() - self.__line_width, pos.y() - self.__line_width)
        painter.drawEllipse(QtCore.QRectF(n, QtCore.QSize(self.__line_width * 2, self.__line_width * 2)))

    def __getLatestPos(self) -> QtCore.QPoint:
        """Get latest selected position"""
        return self.remap2CanvasPos(self.__selected_pos[-1]) if self.__selected_pos else QtCore.QPoint()

    def __getShapeListByName(self, name: str) -> typing.List[PaintShape]:
        return {
            QtCore.QRect.__name__: self.__drawing_rectangles,
            QtCore.QLine.__name__: self.__drawing_lines,
            QtCore.QPoint.__name__: self.__selected_pos
        }.get(name)

    def setScale(self, factor: float):
        self.__scale_factor = factor
        self.adjustSize()
        self.update()

    def remap2ImagePos(self, canvas_pos: QtCore.QPoint) -> QtCore.QPoint:
        """Remap canvas position to real image position"""
        image = QtCore.QRect(0, 0, *self.__image.size)
        image_pos = canvas_pos * self.__image_scale_factor
        return image_pos if image.contains(image_pos) else canvas_pos

    def remap2CanvasPos(self, image_pos: QtCore.QPoint) -> QtCore.QPoint:
        """Remap image position to canvas position"""
        return QtCore.QPoint(image_pos.x() // self.__image_scale_factor, image_pos.y() // self.__image_scale_factor)

    def remap2CanvasLine(self, line: QtCore.QLine) -> QtCore.QLine:
        return QtCore.QLine(self.remap2CanvasPos(line.p1()), self.remap2CanvasPos(line.p2()))

    def remap2CanvasRect(self, rect: QtCore.QRect) -> QtCore.QRect:
        return QtCore.QRect(self.remap2CanvasPos(rect.topLeft()), rect.size() / self.__image_scale_factor)

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

    def slotLoadImage(self, path: str, fit_window: bool = True, sel_shape: typing.List[PaintShape] = None) -> str:
        """Load and display image and image selected shape

        @param path: image path
        @param fit_window: emit signalFitWindowRequest or not
        @param sel_shape: selected shapes
        @return: success return empty str, failed return error desc
        """
        sel_shape = sel_shape if isinstance(sel_shape, collections.Sequence) else list()

        self.__highlight_shape = QtCore.QPoint()
        self.__selected_pos = [x for x in sel_shape if isinstance(x, QtCore.QPoint)]
        self.__drawing_lines = [x for x in sel_shape if isinstance(x, QtCore.QLine)]
        self.__drawing_rectangles = [x for x in sel_shape if isinstance(x, QtCore.QRect)]

        reader = QtGui.QImageReader(path)
        reader.setAutoTransform(True)
        reader.setDecideFormatFromContent(True)
        rule = self.__big_img_shrink_filter if self.__big_img_shrink_filter.isValid() else reader.size()
        reader.setScaledSize(ImageWidget.scaleBigImage(reader.size(), rule, factor=self.__big_img_shrink_factor))

        image = reader.read()
        if image.isNull():
            return reader.errorString()

        try:
            self.__image = Image.open(path)
        except Exception as e:
            return f'{e}'

        self.__current_image_name = path
        self.__pixmap = QtGui.QPixmap.fromImage(image)
        self.__image_scale_factor = 1 if self.__pixmap.width() == self.__image.size[0] else self.__big_img_shrink_factor

        if fit_window:
            self.signalFitWindowRequest.emit()

        self.update()
        self.signalImageChanged.emit(path)
        return ''

    def slotSingleClicked(self):
        """Mouse single clicked will call back this"""
        self.__timer.stop()
        canvas_pos = self.__latest_clicked_pos

        if self.isSelectable(canvas_pos):
            image_pos = self.remap2ImagePos(canvas_pos)
            image_color = self.getImageColor(image_pos)
            self.__selected_pos.append(image_pos)

            if self.isPaintFinished():
                if self.isPaintLineMode():
                    self.__drawing_lines.append(QtCore.QLine(*self.__selected_pos[-2:]))
                    self.signalSelectRequest.emit(self.__drawing_lines[-1], image_color)
                elif self.isPaintRectangleMode():
                    self.__drawing_rectangles.append(QtCore.QRect(*self.__selected_pos[-2:]))
                    self.signalSelectRequest.emit(self.__drawing_rectangles[-1], image_color)

            if self.isPaintDotMode():
                self.signalSelectRequest.emit(image_pos, image_color)
            self.update()

    def slotClearAllSelect(self):
        self.__highlight_shape = QtCore.QPoint()
        self.__drawing_rectangles.clear()
        self.__drawing_lines.clear()
        self.__selected_pos.clear()
        self.update()

    def slotDeleteSelect(self, shape: PaintShape):
        shape_list = self.__getShapeListByName(shape.__class__.__name__)
        if shape_list is None:
            return

        try:
            shape_list.remove(shape)
        except ValueError:
            return
        else:
            if self.__highlight_shape == shape:
                self.__highlight_shape = QtCore.QPoint()
            self.update()

    def slotHighlightSelect(self, shape: PaintShape):
        shape_list = self.__getShapeListByName(shape.__class__.__name__)
        if not shape_list:
            return

        if shape in shape_list:
            self.__highlight_shape = self.remap2CanvasPos(shape) if isinstance(shape, QtCore.QPoint) else shape
            self.update()

    def enterEvent(self, event: QtCore.QEvent) -> None:
        """Show cross cursor if mouse is canvas rectangle"""
        if not self.__change_cursor:
            super(CanvasWidget, self).enterEvent(event)
        else:
            pos = self.transformPos(QtGui.QCursor.pos())
            self.setCursor(QtGui.QCursor(Qt.CrossCursor if self.isSelectable(pos) else Qt.ForbiddenCursor))

    def leaveEvent(self, event: QtCore.QEvent) -> None:
        if not self.__change_cursor:
            super(CanvasWidget, self).leaveEvent(event)
        else:
            self.setCursor(QtGui.QCursor(Qt.ArrowCursor))

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        p = self.__painter
        p.begin(self)

        if not self.__pixmap and self.__default_text:
            font = self.font()
            textMaxLength = max([len(t) for t in self.__default_text.split('\n')])
            fontMaxWidth = round(self.width() / textMaxLength) / 1.5
            font.setPointSize(fontMaxWidth)
            p.setFont(font)
            p.setPen(QtGui.QPen(QtGui.QColor(Qt.black)))
            p.drawText(self.rect(), Qt.AlignCenter, self.__default_text)
        else:
            # Pixmap
            p.setRenderHint(QtGui.QPainter.Antialiasing)
            p.setRenderHint(QtGui.QPainter.HighQualityAntialiasing)
            p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
            p.scale(self.__scale_factor, self.__scale_factor)
            p.translate(self.offsetToCenter())
            p.drawPixmap(0, 0, self.__pixmap)

            if self.isPaintDotMode():
                for pos in [self.remap2CanvasPos(p) for p in self.__selected_pos]:
                    self.__painterAutoColor(p, pos)
                    p.drawLine(pos.x() - self.__line_width, pos.y(), pos.x() + self.__line_width, pos.y())
                    p.drawLine(pos.x(), pos.y() - self.__line_width, pos.x(), pos.y() + self.__line_width)

                    if pos == self.__highlight_shape:
                        self.__drawSelectedPoint(p, pos)

            # Drawing unfinished line
            if self.isPaintLineMode() and self.isPaintNotFinished():
                start = self.__getLatestPos()
                self.__painterAutoColor(p, start)
                p.drawLine(start, self.__cursor_pos)

            # Drawing unfinished rect
            if self.isPaintRectangleMode() and self.isPaintNotFinished():
                end = self.__cursor_pos
                start = self.__getLatestPos()
                self.__painterAutoColor(p, start)
                p.drawRect(start.x(), start.y(), end.x() - start.x(), end.y() - start.y())

            for line in self.__drawing_lines:
                canvas_line = self.remap2CanvasLine(line)
                if line == self.__highlight_shape:
                    self.__drawSelectedLine(p, canvas_line)
                self.__painterAutoColor(p, canvas_line.p1())
                p.drawLine(canvas_line)

            for rect in self.__drawing_rectangles:
                canvas_rect = self.remap2CanvasRect(rect)
                if rect == self.__highlight_shape:
                    self.__drawSelectedRect(p, canvas_rect)
                self.__painterAutoColor(p, canvas_rect.topLeft())
                p.setBrush(QtGui.QBrush(Qt.NoBrush))
                p.drawRect(canvas_rect)

        p.end()

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        mods = event.modifiers()
        delta = event.angleDelta()
        if QtCore.Qt.ControlModifier == mods:
            # zoom with Ctrl key
            self.signalZoomRequest.emit(delta.y(), event.pos())
        else:
            # scroll
            self.signalScrollRequest.emit(delta.x(), QtCore.Qt.Horizontal)
            self.signalScrollRequest.emit(delta.y(), QtCore.Qt.Vertical)

        event.accept()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() == Qt.Key_Escape:
            self.__cancelShapeDrawing()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        self.__cursor_pos = self.transformPos(event.localPos())

        # Update cursor shape
        if self.__change_cursor:
            selectable = self.isSelectable(self.__cursor_pos)
            self.setCursor(QtGui.QCursor(Qt.CrossCursor if selectable else Qt.ForbiddenCursor))

        # It's paint shape mode, dynamically drawing shape
        if self.__paint_mode not in (PaintMode.Dot, PaintMode.NONE):
            self.update()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if self.__paint_mode == PaintMode.NONE:
            return

        # Record latest clicked pos start timer, timer using to distinguish click and double click
        self.__latest_clicked_pos = self.transformPos(event.localPos()).toPoint()
        self.__timer.start()

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        self.__timer.stop()
        if event.button() == Qt.RightButton:
            # Right button double click cancel paint line/rectangle
            if self.__cancelShapeDrawing():
                return

        # If double_clicked_event enable emit fitWidth/fitWindow request
        if self.__enable_double_clicked_event:
            self.signalFitWidthRequest.emit() if event.button() == Qt.LeftButton else self.signalFitWindowRequest.emit()


class ScalableCanvasWidget(QtWidgets.QScrollArea):
    signalImageChanged = QtCore.Signal(str)
    signalRequestFitWidth = QtCore.Signal()
    signalRequestFitWindow = QtCore.Signal()
    signalZoomFactorChanged = QtCore.Signal(int)
    signalPositionSelected = QtCore.Signal(object, object)

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
        self.canvas.signalImageChanged.connect(self.signalImageChanged)
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

    def slotDeleteSelect(self, shape: PaintShape):
        self.canvas.slotDeleteSelect(shape)

    def slotHighlightSelect(self, shape: PaintShape):
        self.canvas.slotHighlightSelect(shape)

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

    def slotLoadImage(self, image: str, selected_shapes: typing.List[PaintShape] = None):
        self.canvas.slotLoadImage(image, image not in self.__zoom_value_records, selected_shapes)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        if self.__zoom_mode != self.ZoomMode.ManualZoom:
            self.adjustScale()
        super(ScalableCanvasWidget, self).resizeEvent(event)


def canvas_init_helper(parent: QtWidgets.QWidget,
                       canvas: ScalableCanvasWidget, zoom_factor: QtWidgets.QSpinBox,
                       action_fit_width: QtWidgets.QAction, action_fit_window: QtWidgets.QAction):
    """Help to connect canvas and zoom factor ant fit width/window actions signal and slots

    :param parent: canvas parent widget
    :param canvas: ScalableCanvasWidget
    :param zoom_factor: zoom factor spinbox
    :param action_fit_width: fit width action
    :param action_fit_window: fit window action
    :return: QActionGroup
    """
    action_fit_width.setCheckable(True)
    action_fit_window.setCheckable(True)

    # Fit width/window must be mutual
    action_fit_window.setChecked(True)
    group = QtWidgets.QActionGroup(parent)
    group.addAction(action_fit_width)
    group.addAction(action_fit_window)

    # Connect signal and slots
    zoom_factor.valueChanged.connect(canvas.slotPaintCanvas)
    canvas.signalZoomFactorChanged.connect(zoom_factor.setValue)

    canvas.signalRequestFitWidth.connect(action_fit_width.trigger)
    canvas.signalRequestFitWindow.connect(action_fit_window.trigger)

    action_fit_width.triggered.connect(lambda: canvas.slotFitWidth(action_fit_width.isChecked()))
    action_fit_window.triggered.connect(lambda: canvas.slotFitWindow(action_fit_window.isChecked()))
    return group
