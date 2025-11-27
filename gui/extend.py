# -*- coding: utf-8 -*-
import abc
import copy
import typing
import collections
from PySide2 import QtWidgets, QtCore
import xml.etree.ElementTree as XmlElementTree
from xml.etree.ElementTree import Element as XmlElement
from framework.misc.windpi import get_program_scale_factor

from .msgbox import *
from .dialog import BasicDialog
from .widget import BasicWidget

__all__ = ['AbstractSubExtendPanel', 'AbstractExtendPanel', 'AbstractExtendParser']
ExtendInfo = collections.namedtuple('ExtendInfo', ['id', 'name'])


class AbstractSubExtendPanel(BasicDialog):
    EXTEND_ID = 0
    EXTEND_NAME = ""
    EXTEND_DESC = ""
    EXTEND_WHAT_THIS = ""
    SUPPORT_DEVICES = ()

    def __init__(self, model: typing.Any, setting: typing.Any,
                 private: typing.Any = None, parent: typing.Optional[QtWidgets.QWidget] = None):
        """
        :param model: device model
        :param private: different extend using different private data
        :param parent:
        """
        self._model = model
        self._private = private
        self._settings = setting
        self._settings_desc = ""
        self._scale_x, self._scale_y = get_program_scale_factor()
        super(AbstractSubExtendPanel, self).__init__(parent)

        # self.setWindowIcon(icon)
        self.setWindowTitle(self.tr(self.EXTEND_DESC))
        self.setWhatsThis(self.tr(self.EXTEND_WHAT_THIS))

    def __str__(self):
        return "{}".format(self._settings_desc)

    def _createSettingXml(self) -> XmlElement:
        return XmlElement(self.EXTEND_NAME)

    def _scaleSize(self, size: QtCore.QSize) -> QtCore.QSize:
        if not isinstance(size, QtCore.QSize):
            return size
        else:
            return QtCore.QSize(int(size.width() * self._scale_x), int(size.height() * self._scale_y))

    @abc.abstractmethod
    def getSetting(self) -> typing.Optional[str]:
        pass

    def getBooleanStr(self, enable: typing.Any) -> str:
        return self.tr('Enable') if enable else self.tr('Disable')

    def getExtendInfo(self) -> ExtendInfo:
        return ExtendInfo(self.EXTEND_ID, self.EXTEND_NAME)


class AbstractExtendPanel(BasicWidget):
    supportExtend = {}
    dataChanged = QtCore.Signal()

    @staticmethod
    def id2name(_id: int) -> str:
        for name, extend in list(AbstractExtendPanel.supportExtend.items()):
            if extend.EXTEND_ID == _id:
                return name

        return ""

    @staticmethod
    def name2id(name_: str) -> int:
        for name, extend in list(AbstractExtendPanel.supportExtend.items()):
            if name == name_:
                return extend.EXTEND_ID

        return -1

    @staticmethod
    def register(name: str):
        def decorator_register_panel(cls):
            if not issubclass(cls, AbstractSubExtendPanel):
                raise TypeError(f'Panel: {cls.__name__!r} must be {AbstractSubExtendPanel.__name__}!r')

            if cls in AbstractExtendPanel.supportExtend:
                raise ValueError(f'Panel: {cls.__name__!r} already registered')

            cls.EXTEND_NAME = name
            AbstractExtendPanel.supportExtend[name] = cls
            return cls

        return decorator_register_panel

    def __init__(self, model: typing.Any, parent: typing.Optional[QtWidgets.QWidget] = None):
        super(AbstractExtendPanel, self).__init__(parent)

        self.__model = model
        self.__data = dict()
        self.__extend = dict()
        self.__private = None
        self.setModelName(model)

    def _initUi(self):
        self.ui_addList = QtWidgets.QComboBox()
        self.ui_modList = QtWidgets.QComboBox()
        self.ui_addContent = QtWidgets.QLineEdit()
        self.ui_modContent = QtWidgets.QLineEdit()
        self.ui_addContent.setDisabled(True)
        self.ui_modContent.setDisabled(True)
        self.ui_add = QtWidgets.QPushButton(self.tr("Add Extension"))
        self.ui_mod = QtWidgets.QPushButton(self.tr("Modify Extension"))
        self.ui_remove = QtWidgets.QPushButton(self.tr("Delete Extension"))

        # Change combobox and line edit size policy
        policy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        # policy.setHorizontalStretch(1)
        # self.modList.setSizePolicy(policy)
        # self.addList.setSizePolicy(policy)
        policy.setHorizontalStretch(3)
        self.ui_addContent.setSizePolicy(policy)
        self.ui_modContent.setSizePolicy(policy)

        group_layout = QtWidgets.QHBoxLayout()
        group_layout.addWidget(self.ui_addList)
        group_layout.addWidget(self.ui_addContent)
        group_layout.addWidget(self.ui_add)
        group_layout.addWidget(self.ui_modList)
        group_layout.addWidget(self.ui_modContent)
        group_layout.addWidget(self.ui_mod)
        group_layout.addWidget(self.ui_remove)
        group_layout.setContentsMargins(9, 9, 9, 9)

        self.ui_group = QtWidgets.QGroupBox()
        self.ui_group.setLayout(group_layout)
        self.ui_group.setTitle(self.tr("Extended Parameters"))

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.ui_group)
        self.setLayout(layout)

    def _initStyle(self):
        self.ui_addList.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.ui_modList.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)

    def _initSignalAndSlots(self):
        self.ui_add.clicked.connect(self.__slotAddExtend)
        self.ui_mod.clicked.connect(self.__slotModExtend)
        self.ui_remove.clicked.connect(self.__slotRemoveExtend)
        self.ui_addList.currentIndexChanged.connect(self.__slotShowExtendDesc)
        self.ui_modList.currentIndexChanged.connect(self.__slotShowExtendData)

    @abc.abstractmethod
    def _getSubExtendCls(self, model: typing.Any) -> typing.Dict[str, typing.Type[AbstractSubExtendPanel]]:
        pass

    def __getAddExtend(self) -> typing.Optional[typing.Type[AbstractSubExtendPanel]]:
        return self.__extend.get(self.ui_addList.currentText())

    def __getModExtend(self) -> typing.Optional[typing.Type[AbstractSubExtendPanel]]:
        return self.__extend.get(self.ui_modList.currentText())

    def __slotShowExtendData(self, idx: int):
        if not isinstance(idx, int) or idx < 0 or idx >= self.ui_modList.count():
            self.ui_modContent.clear()
        else:
            name = self.ui_modList.currentText()
            panel = self.__getModExtend()(self.__model, self.__data.get(name), self.__private, self)
            self.ui_modContent.setText(self.tr("{}".format(panel)))
            self.ui_modContent.setToolTip(self.tr("{}".format(panel)))

    def __slotShowExtendDesc(self, idx: int):
        if not isinstance(idx, int) or idx < 0 or idx >= self.ui_addList.count():
            self.ui_addContent.clear()
        else:
            extend = self.__getAddExtend()
            desc = extend.EXTEND_DESC
            self.ui_addContent.setToolTip(desc)
            self.ui_addContent.setText(QtWidgets.QApplication.translate(extend.__name__, desc, None))

    def __slotAddExtend(self):
        if self.ui_addList.count() == 0:
            return

        extend = self.__getAddExtend()
        name = self.ui_addList.currentText()
        if not issubclass(extend, AbstractSubExtendPanel):
            return showMessageBox(self, MB_TYPE_ERR, self.tr("Unknown extension"))

        setting = self.getExtendSetting(extend)
        if not isinstance(setting, str):
            return

        self.__data[name] = setting
        self.ui_modList.addItem(name)
        self.ui_addList.removeItem(self.ui_addList.currentIndex())
        self.dataChanged.emit()
        msg = self.tr("Extension") + ' "{}" '.format(name) + self.tr("add success")
        return showMessageBox(self, MB_TYPE_INFO, msg)

    def __slotModExtend(self):
        if self.ui_modList.count() == 0:
            return

        extend = self.__getModExtend()
        name = self.ui_modList.currentText()
        data = self.__data.get(name)
        setting = self.getExtendSetting(extend, data)
        if isinstance(setting, str):
            self.__data[name] = setting
            self.dataChanged.emit()
            msg = self.tr("Extension") + ' "{}" '.format(name) + self.tr("modify success")
            return showMessageBox(self, MB_TYPE_INFO, msg)

    def __slotRemoveExtend(self):
        if self.ui_modList.count() == 0:
            return

        name = self.ui_modList.currentText()
        if not showQuestionBox(self, self.tr("Confirm to delete extension") + ' "{}" '.format(name)):
            return

        self.__data.pop(name)
        self.ui_addList.addItem(name)
        self.ui_modContent.clear()
        self.ui_modList.removeItem(self.ui_modList.currentIndex())
        self.dataChanged.emit()
        msg = self.tr("Extension") + ' "{}" '.format(name) + self.tr("delete success")
        return showMessageBox(self, MB_TYPE_INFO, msg)

    def reset(self):
        self.ui_addList.clear()
        self.ui_modList.clear()
        self.ui_addContent.clear()
        self.ui_modContent.clear()

    def setData(self, data: dict, private: typing.Any = None):
        """When data changed set extend data

        :param data: extend data
        :param private: extend private data
        :return:
        """
        try:
            self.__private = private
            extend = list(self.__extend.keys())

            for name in list(data.keys()):
                if name not in self.__extend:
                    print("Unknown extend:{}".format(name))
                    return False

                extend.remove(name)

            self.reset()
            self.__data = data
            self.ui_addList.clear()
            self.ui_modList.clear()
            self.ui_addList.addItems(extend)
            self.ui_modList.addItems(list(data.keys()))
            return True

        except AttributeError:
            return False

    def getData(self) -> dict:
        return copy.deepcopy(self.__data)

    def setModelName(self, model: typing.Any):
        self.__extend = {}
        self.__model = model
        self.__extend = self._getSubExtendCls(model)

        self.ui_addList.clear()
        self.ui_addList.addItems(list(self.__extend.keys()))

    def getExtendSetting(self, extend: typing.Type[AbstractSubExtendPanel], data: typing.Any = None):
        if not issubclass(extend, AbstractSubExtendPanel):
            return None

        panel = extend(self.__model, data, self.__private, parent=self)
        panel.exec_()
        return panel.getSetting()


class AbstractExtendParser(object):
    def __init__(self, extend: typing.Type[AbstractSubExtendPanel], model: typing.Any):
        """Parser extend data

        :param extend: extend panel type
        :param model: device model
        """
        if not issubclass(extend, AbstractSubExtendPanel):
            raise TypeError("extend require {!r} not {!r}".format(AbstractSubExtendPanel.__name__, extend.__name__))

        try:
            self._check(model, extend.EXTEND_NAME)
        except RuntimeError:
            raise ValueError(f'Parse {self.__class__.__name__} failed, unknown model name: {model}')

        self._model = model
        self._extend_name = extend.EXTEND_NAME

    def __str__(self):
        return "{0:s}:{1:s}".format(self._model, self._extend_name)

    @abc.abstractmethod
    def _check(self, model: typing.Any, extend_name: str):
        """Do not support raise RuntimeError"""
        pass

    @abc.abstractmethod
    def _get(self, xml: XmlElement) -> str:
        pass

    @abc.abstractmethod
    def _set(self, data: typing.Any) -> XmlElement:
        pass

    def createXml(self) -> XmlElement:
        return XmlElement(self._extend_name)

    def get(self, xml: XmlElement):
        if not isinstance(xml, XmlElement):
            return None

        return self._get(xml)

    def set(self, data: typing.Any) -> XmlElement:
        return self._set(data)

    @staticmethod
    def set_multi_data(xml: XmlElement, data: typing.Sequence) -> typing.Optional[XmlElement]:
        if not isinstance(xml, XmlElement) or not isinstance(data, (list, tuple)):
            return None

        xml.text = ",".join(map(str, data))
        return xml

    @staticmethod
    def get_multi_data(xml: XmlElement) -> typing.Optional[typing.Sequence[str]]:
        if not isinstance(xml, XmlElement):
            return None

        return xml.text.split(",")

    @staticmethod
    def set_multi_item(xml: XmlElement, data: typing.Sequence) -> typing.Optional[XmlElement]:
        if not isinstance(xml, XmlElement) or not isinstance(data, (list, tuple)):
            return None

        xml.set("size", str(len(data)))
        for item in data:
            sub = XmlElementTree.SubElement(xml, "DATA")
            sub.text = str(item)

        return xml

    @staticmethod
    def get_multi_item(xml: XmlElement) -> typing.Optional[typing.Sequence[str]]:
        if not isinstance(xml, XmlElement):
            return None

        return [item.text for item in xml.iter("DATA")]
