# -*- coding: utf-8 -*-
import os
import time
import typing
import collections
from PySide2.QtCore import Qt
from PySide2 import QtCore, QtGui, QtWidgets

from .widget import ImageWidget
from .canvas import ScalableCanvasWidget
__all__ = ['StretchFactor', 'BasicDock', 'FilelistDock', 'ImagePreviewDock', 'ImageIconPreviewDock']
StretchFactor = collections.namedtuple('StretchFactor', 'h v')


class BasicDock(QtWidgets.QDockWidget):
    def __init__(self, suggest_area: Qt.DockWidgetArea, stretch_factor: StretchFactor,
                 closeable: bool = True, allowed_areas: Qt.DockWidgetAreas = Qt.AllDockWidgetAreas, **kwargs):
        super().__init__(**kwargs)
        self.suggest_area = suggest_area
        self.stretch_factor = stretch_factor
        self.setAllowedAreas(allowed_areas)

        if closeable:
            self.setFeatures(self.features() & ~QtWidgets.QDockWidget.DockWidgetClosable)

        self._initUi()
        self._initData()
        self._initStyle()
        self._initThreadAndTimer()
        self._initSignalAndSlots()

    def _initUi(self):
        pass

    def _initData(self):
        pass

    def _initStyle(self):
        pass

    def _initThreadAndTimer(self):
        pass

    def _initSignalAndSlots(self):
        pass


class FilelistDock(QtWidgets.QDockWidget):
    signalImageAppend = QtCore.Signal(str)
    signalImageSelected = QtCore.Signal(str)
    signalLeftKeyDoubleClicked = QtCore.Signal()
    signalRightKeyDoubleClicked = QtCore.Signal()

    def __init__(self, title: str, parent: QtWidgets.QWidget = None):
        super(FilelistDock, self).__init__(parent)
        self.__files = list()
        self.ui_list = QtWidgets.QListWidget(parent)
        self.ui_search = QtWidgets.QLineEdit(parent)
        self.ui_list.mouseDoubleClickEvent = self.mouseDoubleClickEvent

        widget = QtWidgets.QWidget(self)
        widget.setLayout(QtWidgets.QVBoxLayout())
        widget.layout().addWidget(self.ui_search)
        widget.layout().addWidget(self.ui_list)
        widget.layout().setContentsMargins(0, 0, 0, 0)
        # TODO: Support search
        self.ui_search.setHidden(True)

        self.setWidget(widget)
        self.setWindowTitle(title)
        self.ui_search.textChanged.connect(self.slotSearch)
        self.ui_list.itemClicked.connect(self.slotItemClicked)

    @property
    def count(self) -> int:
        return len(self.__files)

    @property
    def current(self) -> str:
        try:
            return self.ui_list.selectedItems()[0].text() if self.ui_list.count() else ''
        except IndexError:
            return ''

    def clear(self):
        self.__files.clear()
        self.ui_list.clear()

    def slotSearch(self, key: str):
        pass

    def slotAppendFile(self, file: str, last: bool = True):
        if file in self.__files:
            return

        self.__files.append(file)
        self.ui_list.addItem(file)
        self.signalImageAppend.emit(file)

        if last:
            self.signalImageSelected.emit(file)
            self.ui_list.setItemSelected(self.ui_list.item(len(self.__files) - 1), True)
            self.ui_list.scrollToBottom()

    def slotSelectFile(self, file: str):
        if file in self.__files:
            self.signalImageSelected.emit(file)
            self.ui_list.setItemSelected(self.ui_list.item(self.__files.index(file)), True)

    def batchAppendImage(self, images: typing.List[str], interval: float, callback: typing.Callable = None):
        try:
            for idx, filename in enumerate(images):
                if callable(callback):
                    callback(idx, filename)
                self.slotAppendFile(filename, filename == images[-1])
                time.sleep(interval)
        except OSError as e:
            print(f'{self.__class__.__name__}: {e}')

    def slotItemClicked(self, item: QtWidgets.QListWidgetItem):
        self.signalImageSelected.emit(item.text())

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        if not self.__files:
            return

        if event.button() == Qt.LeftButton:
            self.signalLeftKeyDoubleClicked.emit()
        elif event.button() == Qt.RightButton:
            self.signalRightKeyDoubleClicked.emit()


class ImagePreviewDock(QtWidgets.QDockWidget):
    signalRequestLoad = QtCore.Signal()
    signalRequestShow = QtCore.Signal(str)

    def __init__(self,
                 title: str, default_text: str = '',
                 min_size: QtCore.QSize = QtCore.QSize(320, 240), parent: QtWidgets.QWidget = None):
        super(ImagePreviewDock, self).__init__(parent)
        self.__filename = ''
        self.__min_size = min_size
        self.ui_preview = ScalableCanvasWidget(change_cursor=False, default_text=default_text, parent=self)
        self.ui_preview.canvas.mousePressEvent = self.mousePressEvent
        self.ui_preview.canvas.mouseDoubleClickEvent = self.mouseDoubleClickEvent
        self.ui_preview.signalImageChanged.connect(self.slotImageLoaded)
        self.ui_preview.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.ui_preview.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.setWidget(self.ui_preview)
        self.setWindowTitle(title)
        self.setMinimumSize(self.__min_size)

    def sizeHint(self) -> QtCore.QSize:
        return self.__min_size

    @property
    def filename(self) -> str:
        return self.__filename

    def clear(self):
        self.__filename = ''
        self.ui_preview.slotClearImage()

    def slotImageLoaded(self, path: str):
        self.__filename = path

    def slotPreviewImage(self, path: str):
        self.ui_preview.slotLoadImage(path)
        self.ui_preview.slotPaintCanvas(int(self.ui_preview.scaleFitWindow() * 100))

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        self.ui_preview.slotPaintCanvas(int(self.ui_preview.scaleFitWindow() * 100))

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        self.signalRequestShow.emit(self.filename)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        self.signalRequestLoad.emit()


class ImageIconPreviewDock(QtWidgets.QDockWidget):
    signalRequestSelectImage = QtCore.Signal(str)
    signalLeftKeyDoubleClicked = QtCore.Signal()
    signalRightKeyDoubleClicked = QtCore.Signal()

    def __init__(self,
                 title: str,
                 icon_size: QtCore.QSize = QtCore.QSize(80, 60),
                 min_size: QtCore.QSize = QtCore.QSize(800, 125), parent: QtWidgets.QWidget = None):
        super(ImageIconPreviewDock, self).__init__(parent)
        self.__min_size = min_size
        self.images = list()
        self.ui_view = QtWidgets.QListView(self)
        self.ui_view.setWrapping(False)
        self.ui_view.setIconSize(icon_size)
        self.ui_view.setViewMode(QtWidgets.QListView.IconMode)
        self.ui_view.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.ui_view.keyPressEvent = self.keyPressEvent
        self.ui_view.mouseDoubleClickEvent = self.mouseDoubleClickEvent

        self.ui_model = QtGui.QStandardItemModel(1, 0, self)
        self.ui_view.setModel(self.ui_model)

        self.setWidget(self.ui_view)
        self.setWindowTitle(title)
        self.setFixedHeight(self.__min_size.height())
        self.setAllowedAreas(Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea)
        self.ui_view.clicked.connect(self.slotSelImage)

    def clear(self):
        self.images.clear()
        self.ui_model.setRowCount(0)
        self.ui_model.setRowCount(1)

    def minimumSizeHint(self) -> QtCore.QSize:
        return self.__min_size

    def slotAddImage(self, img: str):
        self.images.append(img)

        reader = QtGui.QImageReader(img)
        reader.setDecideFormatFromContent(True)
        reader.setScaledSize(QtCore.QSize(ImageWidget.scaleBigImage(reader.size(), self.ui_view.iconSize())))

        item = QtGui.QStandardItem(QtGui.QIcon(QtGui.QPixmap.fromImage(reader.read())), '')
        item.setToolTip(os.path.basename(img))
        item.setData(img, Qt.UserRole)

        self.ui_model.insertRow(self.ui_model.rowCount() - 1, [item])
        self.ui_view.scrollTo(self.ui_model.index(self.ui_model.rowCount() - 1, 0))

    def slotSelImage(self, index: QtCore.QModelIndex):
        item = self.ui_model.item(index.row(), index.column())
        self.signalRequestSelectImage.emit(item.data(Qt.UserRole))

    def slotImageSelected(self, img: str):
        try:
            self.ui_view.setCurrentIndex(self.ui_model.index(self.images.index(img), 0))
        except ValueError:
            pass

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        index = self.ui_view.currentIndex()
        row = index.row()
        if event.key() == Qt.Key_Left:
            row = index.row() - 1
            row = self.ui_model.rowCount() - 2 if row < 0 else row
        elif event.key() == Qt.Key_Right:
            row = index.row() + 1
            row = 0 if row >= self.ui_model.rowCount() - 1 else row
        elif event.key() in (Qt.Key_Home, Qt.Key_Up):
            row = 0
        elif event.key() in (Qt.Key_End, Qt.Key_Down):
            row = self.ui_model.rowCount() - 2

        index = self.ui_model.index(row, index.column())
        self.ui_view.scrollTo(index)
        self.ui_view.setCurrentIndex(index)
        self.signalRequestSelectImage.emit(self.images[row])

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        if not self.images:
            return

        if event.button() == Qt.LeftButton:
            self.signalLeftKeyDoubleClicked.emit()
        elif event.button() == Qt.RightButton:
            self.signalRightKeyDoubleClicked.emit()
