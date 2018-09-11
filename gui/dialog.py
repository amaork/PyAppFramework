# -*- coding: utf-8 -*-
import os
import hashlib
from PySide.QtGui import *
from PySide.QtCore import *
from .button import RectButton
from ..misc.settings import UiLayout
from .msgbox import MB_TYPE_ERR, showMessageBox
from .widget import SerialPortSettingWidget, BasicJsonSettingWidget, \
    JsonSettingWidget, MultiJsonSettingsWidget, MultiTabJsonSettingsWidget, MultiGroupJsonSettingsWidget


__all__ = ['SimpleColorDialog', 'SerialPortSettingDialog', 'ProgressDialog', 'PasswordDialog',
           'JsonSettingDialog', 'MultiJsonSettingsDialog', 'MultiTabJsonSettingsDialog', 'MultiGroupJsonSettingsDialog',
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


class BasicJsonSettingDialog(QDialog):
    def __init__(self, widget_cls, settings, data=None, reset=True, apply=None, parent=None):
        super(BasicJsonSettingDialog, self).__init__(parent)

        if not issubclass(widget_cls, (BasicJsonSettingWidget, MultiTabJsonSettingsWidget)):
            raise TypeError("widget_cls require {!r} or {!r} not {!r}".format(
                BasicJsonSettingWidget.__name__, MultiTabJsonSettingsWidget.__name__, widget_cls.__name__
            ))

        self.apply = apply if hasattr(apply, "__call__") else None
        dialog_buttons = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        dialog_buttons = dialog_buttons | QDialogButtonBox.Reset if reset else dialog_buttons
        dialog_buttons = dialog_buttons | QDialogButtonBox.Apply if self.apply else dialog_buttons

        layout = QVBoxLayout()
        self.ui_widget = widget_cls(settings, data, parent)
        self.ui_buttons = QDialogButtonBox(dialog_buttons)

        self.ui_buttons.accepted.connect(self.accept)
        self.ui_buttons.rejected.connect(self.reject)
        self.apply and self.ui_buttons.button(QDialogButtonBox.Apply).clicked.connect(self.applySetting)
        reset and self.ui_buttons.button(QDialogButtonBox.Reset).clicked.connect(self.ui_widget.resetDefaultData)

        layout.addWidget(self.ui_widget)
        layout.addWidget(QSplitter())
        layout.addWidget(self.ui_buttons)

        try:
            title = settings.layout.get_name() if isinstance(settings.layout, UiLayout) else settings.layout.get("name")
        except AttributeError:
            title = "配置对话框"

        self.setLayout(layout)
        self.setWindowTitle(self.tr(title))

    def getJsonData(self):
        if not self.result():
            return None

        return self.ui_widget.getData()

    def applySetting(self):
        if not self.apply:
            return

        try:
            self.setResult(1)
            self.apply(self.getJsonData())
        except TypeError as error:
            return showMessageBox(self, MB_TYPE_ERR, "应用设置错误：{}".format(error))

    @classmethod
    def getData(cls, settings, data=None, reset=True, apply=None, parent=None):
        dialog = cls(settings, data, reset, apply, parent)
        dialog.exec_()
        return dialog.getJsonData()


class JsonSettingDialog(BasicJsonSettingDialog):
    def __init__(self, settings, data=None, reset=True, apply=None, parent=None):
        super(JsonSettingDialog, self).__init__(JsonSettingWidget, settings, data, reset, apply, parent)

    def getJsonSettings(self):
        if not self.result():
            return None

        return self.ui_widget.getSettings()

    @classmethod
    def getSettings(cls, settings, data=None, reset=True, apply=None, parent=None):
        dialog = cls(settings, data, reset, apply, parent)
        dialog.exec_()
        return dialog.getJsonSettings()


class MultiJsonSettingsDialog(BasicJsonSettingDialog):
    def __init__(self, settings, data=None, reset=True, apply=None, parent=None):
        super(MultiJsonSettingsDialog, self).__init__(MultiJsonSettingsWidget,
                                                      settings, data, reset, apply, parent=parent)


class MultiGroupJsonSettingsDialog(BasicJsonSettingDialog):
    def __init__(self, settings, data=None, reset=True, apply=None, parent=None):
        super(MultiGroupJsonSettingsDialog, self).__init__(MultiGroupJsonSettingsWidget,
                                                           settings, data, reset, apply, parent=parent)


class MultiTabJsonSettingsDialog(BasicJsonSettingDialog):
    def __init__(self, settings, data, reset=True, apply=None, parent=None):
        super(MultiTabJsonSettingsDialog, self).__init__(MultiTabJsonSettingsWidget,
                                                         settings, data, reset, apply, parent)
        self.setMinimumWidth(len(settings.layout.layout) * 100)

    def getJsonSettings(self):
        if not self.result():
            return None

        return self.ui_widget.getSettings()

    @classmethod
    def getSettings(cls, settings, data=None, reset=True, apply=None, parent=None):
        dialog = cls(settings, data, reset, apply, parent)
        dialog.exec_()
        return dialog.getJsonSettings()


class PasswordDialog(QDialog):
    DefaultHashFunction= lambda x: hashlib.md5(x).hexdigest()

    def __init__(self, password=None, hash_function=DefaultHashFunction, style='font: 75 16pt "Arial"', parent=None):
        super(PasswordDialog, self).__init__(parent)
        if not hasattr(hash_function, "__call__"):
            raise TypeError("hash_function must be a callable object}")

        self.__new_password = ""
        self.__password = password
        self.__hash_function = hash_function

        self.__initUi()
        self.__initSignalAndSlots()
        self.setStyleSheet(style)

    def __initUi(self):
        # Ui elements
        self.ui_old_password = QLineEdit()
        self.ui_old_password.setPlaceholderText(self.tr("请输入旧密码"))

        self.ui_new_password = QLineEdit()
        self.ui_new_password.setPlaceholderText(self.tr("请输入新密码"))

        self.ui_show_password = QCheckBox()

        self.ui_confirm_password = QLineEdit()
        self.ui_confirm_password.setPlaceholderText(self.tr("请再次输入新密码"))

        self.ui_old_password_label = QLabel(self.tr("旧密码"))
        self.ui_buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)

        # Ui layout
        item_layout = QGridLayout()
        item_layout.addWidget(self.ui_old_password_label, 0, 0)
        item_layout.addWidget(self.ui_old_password, 0, 1)

        item_layout.addWidget(QLabel(self.tr("新密码")), 1, 0)
        item_layout.addWidget(self.ui_new_password, 1, 1)

        item_layout.addWidget(QLabel(self.tr("重复新密码")), 2, 0)
        item_layout.addWidget(self.ui_confirm_password, 2, 1)

        sub_layout = QHBoxLayout()
        sub_layout.addWidget(self.ui_show_password)
        self.ui_show_password.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        sub_layout.addWidget(QLabel(self.tr("显示密码")))
        item_layout.addLayout(sub_layout, 3, 1)

        for item in (self.ui_old_password, self.ui_new_password, self.ui_confirm_password):
            item.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))
            item.setInputMethodHints(Qt.ImhHiddenText | Qt.ImhNoAutoUppercase | Qt.ImhNoPredictiveText)
            item.setMaxLength(32)
            item.setEchoMode(QLineEdit.Password)

        # Mode switch
        if self.__password:
            self.setWindowTitle(self.tr("更改密码"))
        else:
            self.setWindowTitle(self.tr("重置密码"))
            self.ui_old_password.setHidden(True)
            self.ui_old_password_label.setHidden(True)

        layout = QVBoxLayout()
        layout.addLayout(item_layout)
        layout.addWidget(QSplitter())
        layout.addWidget(self.ui_buttons)
        self.setMinimumWidth(320)
        self.setLayout(layout)

    def __initSignalAndSlots(self):
        self.ui_buttons.accepted.connect(self.accept)
        self.ui_buttons.rejected.connect(self.reject)
        self.ui_show_password.stateChanged.connect(self.slotShowPassword)

    def slotShowPassword(self, ck):
        for item in (self.ui_old_password, self.ui_new_password, self.ui_confirm_password):
            item.setEchoMode(QLineEdit.Normal if ck else QLineEdit.Password)
            item.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))
            item.setInputMethodHints(Qt.ImhHiddenText | Qt.ImhNoAutoUppercase | Qt.ImhNoPredictiveText)

    def accept(self, *args, **kwargs):
        old = self.__hash_function(self.ui_old_password.text().encode())
        new = self.__hash_function(self.ui_new_password.text().encode())
        confirm = self.__hash_function(self.ui_confirm_password.text().encode())

        if self.__password and old != self.__password:
            return showMessageBox(self, MB_TYPE_ERR, "旧密码不正确，请重新输入!")

        if new != confirm:
            return showMessageBox(self, MB_TYPE_ERR, "两次输入的密码不相同，请重新输入!")

        if len(self.ui_new_password.text()) == 0 or len(self.ui_confirm_password.text()) == 0:
            return showMessageBox(self, MB_TYPE_ERR, "密码不能为空，请重新输入!")

        self.__new_password = new
        self.setResult(1)
        self.close()
        return True

    def getNewPassword(self):
        return self.__new_password

    @staticmethod
    def resetPassword(hash_function=DefaultHashFunction, style='', parent=None):
        dialog = PasswordDialog(hash_function=hash_function, style=style, parent=parent)
        dialog.exec_()
        return dialog.getNewPassword()

    @staticmethod
    def changePassword(password=None, hash_function=DefaultHashFunction, style='', parent=None):
        dialog = PasswordDialog(password, hash_function, style, parent)
        dialog.exec_()
        return dialog.getNewPassword()


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
