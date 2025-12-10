# -*- coding: utf-8 -*-
import abc
import time
import queue
import typing
import threading
import collections
import matplotlib.axes
matplotlib.use('Qt5Agg')
from PySide2 import QtWidgets, QtCore
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from ..gui.msgbox import *
from ..gui.mailbox import *
from ..gui.misc import ExpandWidget
from ..gui.widget import BasicWidget
from ..gui.dialog import showFileExportDialog

from ..core.datatype import str2number
from ..core.threading import ThreadSafeBool

from ..misc.utils import get_timestamp_str
from ..misc.debug import get_debug_timestamp

from .canvas import CustomCanvas, ChartAxesAttribute
__all__ = ['AutoRangeTimelineChart', 'TimelineChart', 'ChartLine']
ChartLine = collections.namedtuple('ChartLine', 'name tag style max')


class TimelineChart(BasicWidget):
    def __init__(self, attr: ChartAxesAttribute, canvas_kwargs: dict = None, parent: QtWidgets.QWidget = None):
        self._attribute = attr
        self._canvas_kwargs = canvas_kwargs or dict()

        self.cnt = 0
        self.xdata = list()
        self.ydata = {line.tag: list() for line in self._attribute.lines}
        super(TimelineChart, self).__init__(parent)

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


class AutoRangeTimelineChart(BasicWidget):
    signalUpdatePlot = QtCore.Signal(object)
    ToolbarItemType = typing.Union[QtWidgets.QWidget, QtWidgets.QAction]
    ToolbarPos = collections.namedtuple('ToolbarPos', 'Left Middle Right')(*range(3))

    def __init__(self, mailbox: UiMailBox, parent: QtWidgets.QWidget):
        self.cnt = 0
        self.xdata = list()
        self.ydata = dict()
        self._config = dict()
        self.records = dict()
        self.ui_mail = mailbox
        self._queue = queue.Queue()
        self.aui = ThreadSafeBool(True)
        self.data_export_ts = time.time()
        self.pause = ThreadSafeBool(False)
        self.boot_time = get_debug_timestamp(fmt='%H:%M:%S')
        self.previous_update_ts = str2number(get_debug_timestamp(fmt='%S'))
        super(AutoRangeTimelineChart, self).__init__(parent=parent)

    def _initUi(self):
        self.canvas = self._create_canvas()
        self.ui_toolbar = QtWidgets.QToolBar(self)
        self.plot_toolbar = NavigationToolbar(self.canvas, self)

        self.ui_clear = QtWidgets.QAction(self.tr('Clear'))
        self.ui_pause = QtWidgets.QAction(self.tr('Pause'))
        self.ui_resume = QtWidgets.QAction(self.tr('Resume'))
        self.ui_export_raw_data = QtWidgets.QAction(self.tr('Export Raw Data'))

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.ui_toolbar)
        layout.addWidget(self.plot_toolbar)
        layout.addWidget(self.canvas)
        layout.setContentsMargins(3, 0, 0, 0)
        self.setLayout(layout)

    def _initData(self):
        self.updateChart()

    def _initStyle(self):
        self.ui_toolbar.setHidden(True)

    def _initSignalAndSlots(self):
        self.signalUpdatePlot.connect(self.slotUpdatePlot)

        self.ui_clear.triggered.connect(self.slotClear)
        self.ui_pause.triggered.connect(self.pause.set)
        self.ui_resume.triggered.connect(self.pause.clear)
        self.ui_export_raw_data.triggered.connect(self.slotExportRawData)
        threading.Thread(target=self.threadUpdatePlot, daemon=True).start()

    def _toolbarAddItems(self, items: typing.Sequence[ToolbarItemType], last: bool = False):
        for item in items or list():
            if isinstance(item, QtWidgets.QAction):
                self.ui_toolbar.addAction(item)
            elif isinstance(item, QtWidgets.QWidget):
                self.ui_toolbar.addWidget(item)

        if not last:
            self.ui_toolbar.addWidget(ExpandWidget())

    def _initToolbar(self):
        self._toolbarAddItems(self._get_toolbar_items(self.ToolbarPos.Left))
        self._toolbarAddItems(self._get_toolbar_items(self.ToolbarPos.Middle))
        self._toolbarAddItems(list(self._get_toolbar_items(self.ToolbarPos.Right) or list()) + [
            self.ui_clear, self.ui_pause, self.ui_resume, self.ui_export_raw_data
        ], last=True)

    @abc.abstractmethod
    def _pre_update(self):
        pass

    @abc.abstractmethod
    def _post_update(self):
        pass

    @abc.abstractmethod
    def _post_export(self, export_path: str):
        pass

    @abc.abstractmethod
    def _get_config(self) -> dict:
        pass

    @abc.abstractmethod
    def _create_canvas(self) -> FigureCanvas:
        pass

    @abc.abstractmethod
    def _export_raw2excel(self, records: typing.Dict, export_path: str):
        pass

    @abc.abstractmethod
    def _get_toolbar_items(self, pos: ToolbarPos) -> typing.Sequence[ToolbarItemType]:
        pass

    def updateChart(self):
        self.cnt = 0
        self.xdata.clear()
        self._config = self._get_config()
        self.ydata = {k: {line.tag: list() for line in v.lines.values()} for k, v in self._config.items()}

    def updateChartData(self, data: dict, record: typing.Any):
        if not self.aui and str2number(get_debug_timestamp(fmt='%S')) == self.previous_update_ts:
            return

        self._queue.put(data)
        self.records[get_debug_timestamp(fmt='%H:%M:%S')] = record
        self.previous_update_ts = str2number(get_debug_timestamp(fmt='%S'))

    def startDraw(self, start: bool):
        self.ui_toolbar.setVisible(start)
        if start:
            self.boot_time = get_debug_timestamp(fmt='%Y/%m/%d %H:%M:%S')
            self.previous_update_ts = (str2number(get_debug_timestamp(fmt='%S')) - 1) % 60
        else:
            self.slotClear(without_confirm=True)

    def isDataExported(self) -> bool:
        return time.time() - self.data_export_ts <= 60.0

    def threadUpdatePlot(self):
        while True:
            data = self._queue.get()
            self.signalUpdatePlot.emit(data)

    def slotSetAUI(self, aui: bool):
        self.aui.assign(aui)

    def slotClear(self, without_confirm: bool = False):
        if not without_confirm and not showQuestionBox(self, self.tr('Clear chart data and records ?')):
            return

        self.updateChart()
        self.records.clear()
        self.boot_time = get_debug_timestamp(fmt='%Y/%m/%d %H:%M:%S')

    def slotExportRawData(self):
        export_path = showFileExportDialog(
            self, 'CSV(*.csv)',
            name=get_timestamp_str(time.time(), fs_valid=True),
            title=self.tr('Please select export data save path')
        )

        if not export_path:
            return

        if not self.records:
            showMessageBox(self, MB_TYPE_WARN, self.tr("There's not data to export"))
            return

        threading.Thread(
            target=self.threadExportRawData2Excel, args=(dict(self.records), export_path), daemon=True
        ).start()

    def slotUpdatePlot(self, data: dict):
        if not data:
            return

        self.cnt += 1
        self.xdata.append(self.cnt)
        self.canvas.clear()
        min_dict = dict()
        max_dict = dict()

        try:
            self._pre_update()

            for k, v in data.items():
                for axes, ydata in self.ydata.items():
                    if k in ydata:
                        item = self._config.get(axes).lines.get(k)
                        ydata[k].append(v)
                        min_dict[k] = min(ydata[k])
                        max_dict[k] = max(ydata[k])

                        try:
                            axes.plot(self.xdata, ydata[k], item.style, label=item.name)
                        except ValueError:
                            pass

                        continue

            for axes, attr in self._config.items():
                attr.update_range(min_dict, max_dict)
                CustomCanvas.updateAxes(axes, attr)

            if not self.pause:
                self.canvas.draw()
                self._post_update()
        except Exception as e:
            print(f'slotUpdatePlot: {e}')
            pass

    def threadExportRawData2Excel(self, records: typing.Dict, export_path: str):
        try:
            self.ui_mail.send(ProgressBarMail.create(total_time=60, title=self.tr('Exporting cvs, please wait......')))
            self._export_raw2excel(records, export_path)
        except Exception as e:
            self.ui_mail.send(MessageBoxMail(MB_TYPE_ERR, f'{e}', self.tr('Export to excel fail')))
        else:
            self.data_export_ts = time.time()
            self.ui_mail.send(MessageBoxMail(MB_TYPE_INFO, f'{export_path}', self.tr('Export success')))
            self.ui_mail.send(CallbackFuncMail(self._post_export, args=(export_path,), timeout=3))
        finally:
            self.ui_mail.send(ProgressBarMail(0))
