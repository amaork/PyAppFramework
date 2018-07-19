# -*- coding: utf-8 -*-
import os
from PySide.QtGui import *
from PySide.QtCore import *
from .button import RectButton
from .widget import SerialPortSettingWidget, JsonSettingWidget, MultiJsonSettingsWidget, MultiTabJsonSettingsWidget


__all__ = ['SimpleColorDialog', 'SerialPortSettingDialog', 'ProgressDialog',
           'JsonSettingDialog', 'MultiJsonSettingsDialog', 'MultiTabJsonSettingsWidget',
           'showFileImportDialog', 'showFileExportDialog']


class SimpleColorDialog(QDialog):
    # This signal is emitted just after the user has clicked OK to select a color to use
    colorSelected = Signal(QColor)
    # This signal is emitted just after the user selected a color
    currentColorChanged = Signal(QColor)

    def __init__(self, basic=False, color=Qt.black, button_box=False, parent=None):
        """Simple color dialog

        :param basic: if basic is true, only allow red, greed, blue, cyan, yellow, magenta, black, white color
        :param color: init color
        :param button_box: with or without ok cancel button box
        :param parent:
        :return:
        """
        super(SimpleColorDialog, self).__init__(parent)
        if not isinstance(color, (QColor, Qt.GlobalColor)):
            raise TypeError("color expect a 'QColor' or 'Qt.GlobalColor' not '{}'".format(color.__class__.__name__))

        self.__initUi(button_box)
        self.__basic = basic
        self.__color = QColor(color)
        self.__updateColor(self.__color)

    def __initUi(self, without_buttons):
        # Color select buttons
        colorLayout = QGridLayout()
        colors = (Qt.black, Qt.red, Qt.blue, Qt.magenta, Qt.yellow, Qt.green, Qt.cyan, Qt.white)
        for row, depth in enumerate((255, 127, 64)):
            colorLayout.addWidget(QLabel("{0:d}".format(depth)), row, 0)
            for column, color in enumerate(colors):
                c = QColor(color)
                r, g, b = (depth if x else x for x in self.convertToRgb(c))
                c = QColor(r, g, b)
                button = RectButton(32, 24, color=(c, c))
                button.clicked.connect(self.slotChangeColor)
                colorLayout.addWidget(button, row, column + 1)

        # Color depth slider
        depthLayout = QHBoxLayout()
        self.__depth = QSlider(Qt.Horizontal)
        self.__depth.setRange(0, 255)
        self.__depth.setTickInterval(10)
        self.__depth.setTickPosition(QSlider.TicksBelow)
        self.__depth.valueChanged.connect(self.slotChangeDepth)
        depthLayout.addWidget(QLabel(self.tr("亮度")))
        depthLayout.addWidget(self.__depth)

        # Label for preview color
        self.__preview = QLabel()

        # Color value spinbox
        self.__red = QSpinBox()
        self.__green = QSpinBox()
        self.__blue = QSpinBox()
        valueLayout = QHBoxLayout()
        for text, spinbox in (("Red", self.__red), ("Green", self.__green), ("Blue", self.__blue)):
            valueLayout.addWidget(QLabel(text))
            valueLayout.addWidget(spinbox)
            spinbox.setRange(0, 255)
            spinbox.valueChanged.connect(self.slotChangeDepth)
            if text != "Blue":
                valueLayout.addWidget(QSplitter())

        # Dialog button
        layout = QVBoxLayout()
        layout.addLayout(colorLayout)
        layout.addLayout(depthLayout)
        layout.addWidget(self.__preview)
        layout.addLayout(valueLayout)
        layout.addWidget(QSplitter())
        layout.addWidget(QSplitter())
        if not without_buttons:
            button = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            button.accepted.connect(self.accept)
            button.rejected.connect(self.reject)
            layout.addWidget(button)

        self.setLayout(layout)
        self.setWindowTitle(self.tr("请选择颜色"))

    def __getColor(self):
        """Get select color setting

        :return: r, g, b
        """
        return self.__color.red(), self.__color.green(), self.__color.blue()

    def __setColor(self, color):
        """Save color and update spinbox color

        :param color: select color
        :return: true or false
        """
        if not isinstance(color, QColor):
            return False

        self.__color = color
        self.__red.setValue(color.red())
        self.__blue.setValue(color.blue())
        self.__green.setValue(color.green())
        return True

    def __getCurrentColor(self):
        """Get ui spinbox color setting

        :return: r, g, b
        """
        r = self.__red.value()
        b = self.__blue.value()
        g = self.__green.value()
        return r, g, b

    def __updateColor(self, color):
        """Update ui elements setting

        :param color:
        :return:
        """
        if not isinstance(color, QColor):
            return

        self.__setColor(color)
        value = max(self.convertToRgb(color))
        self.slotChangeDepth(value)
        self.__depth.setValue(value)

        # Basic mode
        if self.__basic:
            r, g, b = self.__getColor()
            self.__red.setEnabled(r)
            self.__blue.setEnabled(b)
            self.__green.setEnabled(g)

    def slotChangeColor(self):
        btn = self.sender()
        if not isinstance(btn, RectButton):
            return

        # Update select color
        color = btn.getBrush().color()
        self.__updateColor(color)
        self.currentColorChanged.emit(color)

    def slotChangeDepth(self, value):
        if self.__basic or self.sender() == self.__depth:
            r, g, b = self.__getColor()
            if r:
                self.__red.setValue(value)

            if g:
                self.__green.setValue(value)

            if b:
                self.__blue.setValue(value)

        if self.__basic:
            self.__depth.setValue(value)
        r, g, b = self.__getCurrentColor()
        self.currentColorChanged.emit(QColor(r, g, b))
        self.__preview.setStyleSheet("background:rgb({0:d},{1:d},{2:d})".format(r, g, b))

    def getSelectColor(self):
        if self.result():
            r, g, b = self.__getCurrentColor()
            self.colorSelected.emit(QColor(r, g, b))
            return QColor(r, g, b)
        else:
            return self.__color

    @classmethod
    def getColor(cls, parent, color=Qt.red):
        panel = cls(color=color, parent=parent)
        panel.exec_()
        return panel.getSelectColor()

    @classmethod
    def getBasicColor(cls, parent, color=Qt.red):
        panel = cls(True, color, False, parent)
        panel.exec_()
        return panel.getSelectColor()

    @staticmethod
    def convertToRgb(color):
        if not isinstance(color, QColor):
            return 0, 0, 0

        return color.red(), color.green(), color.blue()

    @staticmethod
    def convertToIndexColor(color):
        if not isinstance(color, QColor):
            return 0, 0

        index = 0
        r, g, b = SimpleColorDialog.convertToRgb(color)

        if r:
            index |= 4

        if g:
            index |= 2

        if b:
            index |= 1

        return index, max(r, g, b)


class SerialPortSettingDialog(QDialog):
    def __init__(self, settings=SerialPortSettingWidget.DEFAULTS, parent=None):
        """Serial port configure dialog

        :param settings: serial port settings
        :param parent:
        """
        settings = settings or self.DEFAULTS
        super(SerialPortSettingDialog, self).__init__(parent)

        layout = QVBoxLayout()
        self.__widget = SerialPortSettingWidget(settings)
        button = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button.accepted.connect(self.accept)
        button.rejected.connect(self.reject)

        layout.addWidget(self.__widget)
        layout.addWidget(QSplitter())
        layout.addWidget(button)

        self.setLayout(layout)
        self.setFixedSize(self.sizeHint())
        self.setWindowTitle(self.tr("串口配置对话框"))

    def getSerialSetting(self):
        if not self.result():
            return None

        return self.__widget.getSetting()

    @classmethod
    def getSetting(cls, parent, settings=SerialPortSettingWidget.DEFAULTS):
        dialog = cls(settings, parent)
        dialog.exec_()
        return dialog.getSerialSetting()


class ProgressDialog(QProgressDialog):
    def __init__(self, parent, title="操作进度", max_width=350, cancel_button=None):
        super(ProgressDialog, self).__init__(parent)

        self.setFixedWidth(max_width)
        self.setWindowFlags(Qt.Dialog)
        self.setWindowTitle(self.tr(title))
        if cancel_button is None:
            self.setCancelButton(None)
        else:
            self.setCancelButtonText(self.tr(cancel_button))

    @Slot(int)
    def setProgress(self, value):
        self.setValue(value)
        if value != 100:
            self.show()
        x = self.parent().geometry().x() + self.parent().width() / 2 - self.width() / 2
        y = self.parent().geometry().y() + self.parent().height() / 2 - self.height() / 2
        self.move(QPoint(x, y))


class JsonSettingDialog(QDialog):
    def __init__(self, settings, data=None, parent=None):
        super(JsonSettingDialog, self).__init__(parent)

        layout = QVBoxLayout()
        self.ui_widget = JsonSettingWidget(settings, parent)
        self.ui_buttons = QDialogButtonBox(QDialogButtonBox.Reset | QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.ui_buttons.accepted.connect(self.accept)
        self.ui_buttons.rejected.connect(self.reject)
        self.ui_buttons.button(QDialogButtonBox.Reset).clicked.connect(self.ui_widget.resetDefaultData)

        layout.addWidget(self.ui_widget)
        layout.addWidget(QSplitter())
        layout.addWidget(self.ui_buttons)

        try:
            title = settings.layout.get_name()
        except AttributeError:
            title = "配置对话框"

        if data:
            self.ui_widget.setData(data)

        self.setLayout(layout)
        self.setWindowTitle(self.tr(title))

    def getJsonData(self):
        if not self.result():
            return None

        return self.ui_widget.getData()

    def getJsonSettings(self):
        if not self.result():
            return None

        return self.ui_widget.getSettings()

    @classmethod
    def getData(cls, settings, data=None, parent=None):
        dialog = cls(settings, data, parent)
        dialog.exec_()
        return dialog.getJsonData()

    @classmethod
    def getSettings(cls, settings, data=None, parent=None):
        dialog = cls(settings, data, parent)
        dialog.exec_()
        return dialog.getJsonSettings()


class MultiJsonSettingsDialog(QDialog):
    def __init__(self, settings, data, parent=None):
        super(MultiJsonSettingsDialog, self).__init__(parent)

        layout = QVBoxLayout()
        self.ui_widget = MultiJsonSettingsWidget(settings, data, parent)
        self.ui_buttons = QDialogButtonBox(QDialogButtonBox.Reset | QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.ui_buttons.accepted.connect(self.accept)
        self.ui_buttons.rejected.connect(self.reject)
        self.ui_buttons.button(QDialogButtonBox.Reset).clicked.connect(self.ui_widget.resetDefaultData)

        layout.addWidget(self.ui_widget)
        layout.addWidget(QSplitter())
        layout.addWidget(self.ui_buttons)

        try:
            title = settings.layout.get_name()
        except AttributeError:
            title = "配置对话框"

        if data:
            self.ui_widget.setData(data)

        self.setLayout(layout)
        self.setWindowTitle(self.tr(title))

    def getJsonData(self):
        if not self.result():
            return None

        return self.ui_widget.getData()

    @classmethod
    def getData(cls, settings, data=None, parent=None):
        dialog = cls(settings, data, parent)
        dialog.exec_()
        return dialog.getJsonData()


class MultiTabJsonSettingsDialog(QDialog):
    def __init__(self, settings, data, parent=None):
        super(MultiTabJsonSettingsDialog, self).__init__(parent)

        layout = QVBoxLayout()
        self.ui_widget = MultiTabJsonSettingsWidget(settings, data, parent)
        self.ui_buttons = QDialogButtonBox(QDialogButtonBox.Reset | QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.ui_buttons.accepted.connect(self.accept)
        self.ui_buttons.rejected.connect(self.reject)
        self.ui_buttons.button(QDialogButtonBox.Reset).clicked.connect(self.ui_widget.resetDefaultData)

        layout.addWidget(self.ui_widget)
        layout.addWidget(QSplitter())
        layout.addWidget(self.ui_buttons)

        try:
            title = settings.tabs.name
        except AttributeError:
            title = "配置对话框"

        if data:
            self.ui_widget.setData(data)

        self.setLayout(layout)
        self.setWindowTitle(self.tr(title))

    def getJsonData(self):
        if not self.result():
            return None

        return self.ui_widget.getData()

    @classmethod
    def getData(cls, settings, data=None, parent=None):
        dialog = cls(settings, data, parent)
        dialog.exec_()
        return dialog.getJsonData()


def showFileExportDialog(parent, fmt, name="", title="请选择导出文件的保存位置"):
    path, ret = QFileDialog.getSaveFileName(parent, parent.tr(title), name, parent.tr(fmt))
    if not ret or len(path) == 0:
        return ""

    return path


def showFileImportDialog(parent, fmt, path="", title="请选到要导入的文件"):
    path, ret = QFileDialog.getOpenFileName(parent, parent.tr(title), path, parent.tr(fmt))
    if not ret or not os.path.isfile(path):
        return ""

    return path
