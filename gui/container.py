# -*- coding: utf-8 -*-
"""
Provide UI elements container
"""

from PySide2.QtCore import *
from PySide2.QtWidgets import QComboBox, QWidget, QDoubleSpinBox, QSpinBox, QLineEdit, QPlainTextEdit, QDateTimeEdit, \
    QDial, QRadioButton, QCheckBox, QPushButton, QLCDNumber, QLabel, QTextEdit, QLayout, QGridLayout, QLayoutItem
from typing import Union, Optional, List, Any, Sequence, Callable

from .binder import *
from .misc import HyperlinkLabel, NetworkInterfaceSelector, CustomEventFilterHandler
from ..core.datatype import str2number, str2float, DynamicObject
from ..dashboard.status import DashboardStatusIcon

__all__ = ['ComboBoxGroup', 'ComponentManager', 'HyperlinkGroup']


class ComboBoxGroup(QObject):
    sequenceChanged = Signal()

    def __init__(self, template: QComboBox, autoCreate: bool = False,
                 ordered: bool = False, parent: Optional[QWidget] = None):
        super(ComboBoxGroup, self).__init__(parent)

        self.__group = list()

        if not isinstance(template, QComboBox):
            raise TypeError("template require {!r} not {!r}".format(QComboBox.__name__, template.__class__.__name__))

        if template.count() <= 1:
            print("ComboBox template data at least needs 2 items")
            return

        self.__template = template
        texts = [template.itemText(x) for x in range(template.count())]

        if not autoCreate:
            return

        # Auto create QCombBox item
        for index in range(template.count()):
            item = QComboBox()
            item.addItems(texts)
            if ordered:
                item.setCurrentIndex(index)
            item.currentIndexChanged.connect(self.slotDataChanged)
            self.__group.append(item)

    def __len__(self):
        return len(self.__group)

    def __typeCheck(self, item: QComboBox) -> bool:
        if not self.__template:
            print("TypeError: template is None")
            return False

        if not isinstance(item, QComboBox):
            print("TypeError: {0:x}".format(type(item)))
            return False

        if item.count() != self.__template.count():
            print("QComboBox count mismatch")
            return False

        for index in range(item.count()):
            if item.itemText(index) != self.__template.itemText(index):
                print("QComboBox item text mismatch")
                return False

        return True

    def __indexCheck(self, index: int) -> bool:
        if not isinstance(index, int):
            print("TypeError:{!r}".format(index.__class__.__name__))
            return False

        if index >= self.count() or index < 0:
            print("IndexError: out of range")
            return False

        return True

    def __findConflictItem(self, current: QComboBox) -> Union[QComboBox, None]:
        if not isinstance(current, QComboBox) or current not in self.__group:
            return None

        for item in self.__group:
            if not isinstance(item, QComboBox):
                return None

            if item == current:
                continue

            if item.currentIndex() == current.currentIndex():
                return item

        return None

    def __findUnusedIndex(self) -> Union[int, None]:
        if self.count() == 0:
            return None

        values = [item.currentIndex() for item in self.__group]
        values.sort()
        if values == list(range(self.count())):
            return None

        for index in range(self.count()):
            if values.count(index) == 0:
                return index

        return None

    def count(self) -> int:
        return len(self.__group)

    def items(self) -> List[QComboBox]:
        """Get all ComboBox items in group"""
        return self.__group

    def itemAt(self, idx: int) -> Union[QComboBox, None]:
        """Get idx specified ComboBox item

        :param idx: index
        :return:  QComboBox object or None
        """
        if not self.__indexCheck(idx):
            return None

        return self.__group[idx]

    def setEditable(self, editable: bool):
        for item in list(self.items()):
            item.setEnabled(editable)

    def addComboBox(self, box: QComboBox, ordered: bool = False) -> bool:
        """And a QComboBox to group

        :param box: QComboBox item
        :param ordered: Set QComboBox ordered in group
        :return: True / False
        """

        if not self.__typeCheck(box):
            return False

        if self.count() == self.__template.count():
            return False

        if ordered:
            box.setCurrentIndex(self.count())

        self.__group.append(box)
        box.currentIndexChanged.connect(self.slotDataChanged)
        return True

    def slotDataChanged(self):
        sender = self.sender()
        if sender not in self.__group:
            return

        self.sequenceChanged.emit()
        item = self.__findConflictItem(sender)

        if not item:
            return

        index = self.__findUnusedIndex()
        if index is not None:
            item.setCurrentIndex(index)

    def getSequence(self) -> List[int]:
        """Get group QComboBox index sequence
        """
        return [item.currentIndex() for item in self.__group]

    def getSequenceText(self) -> List[str]:
        """Get group QComboBox texts
        """
        return [item.currentText() for item in self.__group]

    def setSequence(self, sequence: Sequence[int]) -> bool:
        """Set group QComboBox sequence

        :param sequence: QComboBox index sequence
        :return:
        """
        if not hasattr(sequence, "__iter__"):
            print("TypeError:{!r}".format(sequence.__class__.__name__))
            return False

        if len(sequence) != self.count():
            print("Sequence length error")
            return False

        for index in sequence:
            if not isinstance(index, int):
                print("Sequence item TypeError: {!r}".format(index.__class__.__name__))
                return False

        if len(set(sequence)) != len(sequence):
            print("Sequence item conflict")
            return False

        for item, index in zip(self.__group, sequence):
            item.setCurrentIndex(index)

        return True


class ComponentManager(QObject):
    dataChanged = Signal()
    dataChangedDetail = Signal(str, object)

    DefaultObjectNameKey = 'data'
    QPushButtonPrivateDataKey = 'private'

    def __init__(self, layout: QLayout, parent: Optional[QWidget] = None):
        super(ComponentManager, self).__init__(parent)
        if not isinstance(layout, QLayout):
            raise TypeError("layout require {!r} not {!r}".format(QLayout.__name__, layout.__class__.__name__))

        self.__object = layout
        self.__disabled = False
        self.__eventHandle = CustomEventFilterHandler(
            (QWidget,),
            (QEvent.MouseButtonPress, QEvent.MouseButtonRelease, QEvent.Wheel,
             QEvent.MouseButtonDblClick, QEvent.HoverLeave, QEvent.HoverEnter,
             QEvent.KeyPress, QEvent.KeyRelease), self)

        # For dynamic bind usage
        self.__bindingList = list()

        # Watch all component data changed event
        self.__initSignalAndSlots()

    @property
    def layout(self) -> QLayout:
        return self.__object

    def __initSignalAndSlots(self):
        from ..dashboard.input import VirtualNumberInput

        for component in self.getAll():
            if isinstance(component, QSpinBox):
                component.valueChanged.connect(self.slotDataChanged)
            if isinstance(component, QDoubleSpinBox):
                component.valueChanged.connect(self.slotDataChanged)
            elif isinstance(component, QComboBox):
                component.currentIndexChanged.connect(self.slotDataChanged)
            elif isinstance(component, QCheckBox):
                component.stateChanged.connect(self.slotDataChanged)
            elif isinstance(component, QRadioButton):
                component.clicked.connect(self.slotDataChanged)
            elif isinstance(component, VirtualNumberInput):
                component.numberChanged.connect(self.slotDataChanged)
            elif isinstance(component, QLineEdit):
                component.textChanged.connect(self.slotDataChanged)
            elif isinstance(component, QTextEdit):
                component.textChanged.connect(self.slotDataChanged)
            elif isinstance(component, QPlainTextEdit):
                component.textChanged.connect(self.slotDataChanged)
            elif isinstance(component, QDateTimeEdit):
                component.dateTimeChanged.connect(self.slotDataChanged)
            elif isinstance(component, QDial):
                component.valueChanged.connect(self.slotDataChanged)
            elif isinstance(component, DashboardStatusIcon):
                component.statusChanged.connect(self.slotDataChanged)

    def __getComponentsWithType(self, componentType: QWidget.__class__) -> List[QWidget]:
        if isinstance(componentType, QWidget.__class__):
            components = self.getByType(componentType)
        else:
            components = self.getAll()

        return components

    @staticmethod
    def getComponentData(component: QWidget) -> Any:
        if isinstance(component, QSpinBox):
            return component.value()
        elif isinstance(component, QDoubleSpinBox):
            return component.value()
        elif isinstance(component, NetworkInterfaceSelector):
            return component.currentSelect()
        elif isinstance(component, QComboBox):
            return component.currentText() if component.property("format") == "text" else component.currentIndex()
        elif isinstance(component, QCheckBox):
            return component.isChecked()
        elif isinstance(component, QRadioButton):
            return component.isChecked()
        elif isinstance(component, QLineEdit):
            return {
                "int": str2number(component.text()),
                "float": str2float(component.text())
            }.get(component.property("format"), component.text())
        elif isinstance(component, QTextEdit):
            return component.toPlainText()
        elif isinstance(component, QPlainTextEdit):
            return component.toPlainText()
        elif isinstance(component, QDateTimeEdit):
            return component.displayFormat()
        elif isinstance(component, QDial):
            return component.value()
        elif isinstance(component, QLCDNumber):
            return component.value()
        elif isinstance(component, QPushButton):
            return component.property(ComponentManager.QPushButtonPrivateDataKey)
        elif isinstance(component, DashboardStatusIcon):
            return component.status()
        else:
            return ""

    @staticmethod
    def setComponentData(component: QWidget, data: Any):
        from ..dashboard.input import VirtualNumberInput

        if isinstance(component, QSpinBox):
            component.setValue(str2number(data))
        elif isinstance(component, QDoubleSpinBox):
            component.setValue(str2float(data))
        elif isinstance(component, NetworkInterfaceSelector):
            component.setCurrentSelect(data)
        elif isinstance(component, QComboBox):
            texts = [component.itemText(i) for i in range(component.count())]
            if data in texts:
                index = texts.index(data)
            else:
                index = str2number(data)
                index = 0 if index >= component.count() else index
            component.setCurrentIndex(index)
        elif isinstance(component, QCheckBox):
            component.setCheckable(True)
            component.setChecked(str2number(data))
        elif isinstance(component, QRadioButton):
            component.setCheckable(True)
            component.setChecked(str2number(data))
        elif isinstance(component, VirtualNumberInput):
            component.setValue(data)
        elif isinstance(component, QLineEdit):
            component.setText(str(data))
        elif isinstance(component, QTextEdit):
            if isinstance(data, str):
                component.setText(data)
        elif isinstance(component, QPlainTextEdit):
            if isinstance(data, str):
                component.setPlainText(data)
        elif isinstance(component, QDial):
            component.setValue(str2number(data))
        elif isinstance(component, QLCDNumber):
            component.display(str2float(data))
        elif isinstance(component, QPushButton):
            component.setProperty(ComponentManager.QPushButtonPrivateDataKey, data)
        elif isinstance(component, DashboardStatusIcon):
            component.changeStatus(data)

    @staticmethod
    def connectComponentSignalAndSlot(component: QWidget, slot: Callable[[Any], None]):
        if isinstance(component, QSpinBox):
            component.valueChanged.connect(slot)
        if isinstance(component, QDoubleSpinBox):
            component.valueChanged.connect(slot)
        elif isinstance(component, QComboBox):
            component.currentIndexChanged.connect(slot)
        elif isinstance(component, QCheckBox):
            component.stateChanged.connect(slot)
        elif isinstance(component, QRadioButton):
            component.clicked.connect(slot)
        elif isinstance(component, QLineEdit):
            component.textChanged.connect(slot)
        elif isinstance(component, QTextEdit):
            component.textChanged.connect(slot)
        elif isinstance(component, QPlainTextEdit):
            component.textChanged.connect(slot)
        elif isinstance(component, QDateTimeEdit):
            component.dateTimeChanged.connect(slot)
        elif isinstance(component, QDial):
            component.valueChanged.connect(slot)

    @staticmethod
    def findParentLayout(obj: QWidget, top: QLayout) -> Union[QLayout, None]:
        if not isinstance(obj, QWidget) or not isinstance(top, QLayout):
            return None

        for index in range(top.count()):
            item = top.itemAt(index)
            if not isinstance(item, QLayoutItem):
                continue

            widget = item.widget()

            # Item is QWidget
            if isinstance(widget, QWidget):
                # Found object in top layout
                if widget == obj:
                    return top
                # QWidget has sub widgets
                elif isinstance(widget.layout(), QLayout):
                    layout = ComponentManager.findParentLayout(obj, widget.layout())
                    if layout:
                        return layout
            # Item is layout
            elif isinstance(item.layout(), QLayout):
                layout = ComponentManager.findParentLayout(obj, item.layout())
                if layout:
                    return layout
            else:
                continue

        return None

    @staticmethod
    def getAllComponents(obj: QWidget) -> List[QWidget]:
        """Get object specified object all components

        :param obj: should be a QWidget or Layout
        :return:
        """
        components = list()
        if isinstance(obj, QWidget) and isinstance(obj.layout(), QLayout):
            layout = obj.layout()
        elif isinstance(obj, QLayout) and obj.count() > 0:
            layout = obj
        else:
            return []

        # Traversal all component
        for index in range(layout.count()):
            item = layout.itemAt(index)
            if not isinstance(item, QLayoutItem):
                continue

            widget = item.widget()
            # Is a QWidget
            if isinstance(widget, QWidget):
                components.append(widget)
                components.extend(ComponentManager.getAllComponents(widget))
                continue

            sub_layout = item.layout()
            # Is a QLayout
            if isinstance(sub_layout, QLayout):
                components.extend(ComponentManager.getAllComponents(sub_layout))

        return components

    def slotDataChanged(self):
        sender = self.sender()
        if sender not in self.getAll():
            return

        # Emit dataChanged signal
        self.dataChanged.emit()
        self.dataChangedDetail.emit(sender.property(self.DefaultObjectNameKey), self.getComponentData(sender))

    def getAll(self) -> List[QWidget]:
        return self.getAllComponents(self.__object)

    def getParentLayout(self, obj: QWidget) -> Union[QLayout, None]:
        if obj not in self.getAll():
            return None

        return self.findParentLayout(obj, self.__object)

    def findRowSibling(self, obj: QWidget) -> List[QWidget]:
        layout = self.getParentLayout(obj)
        if not isinstance(layout, QGridLayout):
            print("Only QGridLayout support find row sibling")
            return []

        for row in range(layout.rowCount()):
            for column in range(layout.columnCount()):
                item = layout.itemAt(row * layout.columnCount() + column)
                if isinstance(item, QLayoutItem) and item.widget() == obj:
                    return [layout.itemAt(row * layout.columnCount() + column).widget()
                            for column in range(layout.columnCount())]

        return []

    def findColumnSibling(self, obj: QWidget) -> List[QWidget]:
        layout = self.getParentLayout(obj)
        if not isinstance(layout, QGridLayout):
            print("Only QGridLayout support find column sibling")
            return []

        for row in range(layout.rowCount()):
            for column in range(layout.columnCount()):
                item = layout.itemAt(row * layout.columnCount() + column)
                if isinstance(item, QLayoutItem) and item.widget() == obj:
                    return [layout.itemAt(row * layout.columnCount() + column).widget()
                            for row in range(layout.rowCount() - 1)]

        return []

    def getNextSibling(self, obj: QWidget) -> Union[QWidget, None]:
        layout = self.getParentLayout(obj)
        if not isinstance(layout, QLayout):
            return None

        components = self.getAllComponents(layout)
        index = components.index(obj)
        if index >= len(components) - 1:
            return None
        else:
            return components[index + 1]

    def getPrevSibling(self, obj: QWidget) -> Union[QWidget, None]:
        layout = self.getParentLayout(obj)
        if not isinstance(layout, QLayout):
            return None

        components = self.getAllComponents(layout)
        index = components.index(obj)
        if index == 0:
            return None
        else:
            return components[index - 1]

    def getByType(self, componentType: QWidget.__class__) -> List[QWidget]:
        """Get componentType specified type components

        :param componentType: component type
        :return: matched objects
        """

        if not isinstance(componentType, QWidget.__class__):
            print("TypeError:{!r}".format(componentType.__class__.__name__))
            return []

        components = list()
        for component in self.getAll():
            if isinstance(component, componentType):
                components.append(component)

        return components

    def getByValue(self, key: str, value: Any,
                   componentType: Optional[QWidget.__class__] = None) -> Union[QWidget, None]:
        """Get componentType specified component property key  is value

        :param key: property key
        :param value: property keys value
        :param componentType: component componentType
        :return:
        """

        if not isinstance(key, str):
            print("Property key TypeError:{!r}".format(key.__class__.__name__))
            return None

        # Search by property
        for component in self.__getComponentsWithType(componentType):
            if component.property(key) == value:
                return component

        return None

    def findKey(self, key: str, componentType: Optional[QWidget.__class__] = None) -> List[QWidget]:
        """find component with componentType specified type, and key specified property key

        :param key: property key
        :param componentType: component type
        :return:
        """

        if not isinstance(key, str):
            print("Property key typeError: {!r}".format(key.__class__.__name__))
            return []

        lst = list()
        for component in self.__getComponentsWithType(componentType):
            if component.property(key) is not None:
                lst.append(component)

        return lst

    def findValue(self, key: str, searchValue: Any, componentType: Optional[QWidget.__class__] = None) -> List[QWidget]:
        """Find component with componentType specified types and property key hast value

        :param key: property key
        :param searchValue: property value key value
        :param componentType: component types
        :return:
        """
        lst = list()
        for component in self.findKey(key, componentType):
            value = component.property(key)
            if isinstance(value, str) and searchValue in value or value == searchValue:
                lst.append(component)

        return lst

    def getData(self, key: str,
                componentTypes: Optional[Sequence[QWidget.__class__]] = None,
                exclude: Optional[Sequence[str]] = None) -> dict:
        data = dict()
        components = list()
        exclude = exclude if isinstance(exclude, (list, tuple)) else []

        if hasattr(componentTypes, "__iter__"):
            for t in componentTypes:
                if isinstance(t, QWidget.__class__):
                    components.extend(self.findKey(key, t))
        else:
            components = self.findKey(key, componentTypes)

        for component in components:
            value = component.property(key)

            if value in exclude:
                continue

            data[value] = self.getComponentData(component)

        return data

    def setData(self, key: str, data: Union[str, dict]) -> bool:
        if not isinstance(key, str) or not isinstance(data, dict):
            return False

        for component in self.getAll():
            property_key = component.property(key)
            value = data.get(property_key)

            if value is not None:
                self.setComponentData(component, value)

        return True

    def setEnabled(self, enabled: bool):
        self.setDisabled(not enabled)

    def setDisabled(self, disable: bool):
        self.__disabled = disable
        [self.__eventHandle.process(element, self.__disabled) for element in self.getAll()]

    def bindSpinBox(self, key: str, sender: Any, receiver: Any,
                    factor: Union[int, float], enable: bool = False) -> bool:
        """Bind two spinbox, when one spinbox is changes another will linkage

        :param key: property key
        :param sender: sender Spinbox property value
        :param receiver: receiver Spinbox property value
        :param factor: linkage factor
        :param enable: enable receiver
        :return:
        """

        senderObject = self.getByValue(key, sender)
        receiverObject = self.getByValue(key, receiver)

        binder = SpinBoxBinder(senderObject)

        if isinstance(receiverObject, (QSpinBox, QDoubleSpinBox)):
            if binder.bindSpinBox(receiverObject, factor):
                self.__bindingList.append(binder)
            else:
                return False
        elif isinstance(receiverObject, (QLabel, QLineEdit)):
            if binder.bindTextBox(receiverObject, factor):
                self.__bindingList.append(binder)
            else:
                return False
        else:
            return False

        receiverObject.setEnabled(enable)
        return True

    def bindComboBox(self, key: str, sender: Any, receiver: Any, reverse: bool = False, enable: bool = False) -> bool:
        """Bind two ComboBox, on changed, another changed too

        :param key: property key
        :param sender: Sender comboBox property value
        :param receiver:  Receiver ComboBox property value
        :param enable: disable or enable receiver
        :param reverse:
        :return:
        """

        senderComboBox = self.getByValue(key, sender, QComboBox)
        receiverComboBox = self.getByValue(key, receiver, QComboBox)

        senderBinder = ComboBoxBinder(senderComboBox)
        if senderBinder.bindComboBox(receiverComboBox, reverse):
            self.__bindingList.append(senderBinder)
        else:
            return False

        receiverComboBox.setEnabled(enable)
        return True

    def bindComboBoxWithLabel(self, key: str, sender: Any, receiver: Any, texts: Sequence[str]) -> bool:
        """Bind ComboBox with label, ComboBox current index changed, label text changed too

        :param key: property key
        :param sender: QComboBox property value
        :param receiver: QLabel property value
        :param texts:  QLabel texts
        :return:
        """

        label = self.getByValue(key, receiver, QLabel)
        comboBox = self.getByValue(key, sender, QComboBox)

        binder = ComboBoxBinder(comboBox)
        if binder.bindTextBox(label, texts):
            self.__bindingList.append(binder)
        else:
            return False

        return True

    def bindComboBoxWithSpinBox(self, key: str, sender: Any, receiver: Any, limit: Union[list, tuple]) -> bool:
        """Bind ComboBox with SpinBox, ComboBox current index changed, SpinBox will changed

        limit length = 3 (min, max, step)
        limit length = 2 (min, max)
        limit length = 1 (ratio)

        :param key: property key
        :param sender: QComboBox property value
        :param receiver: QSpinbox property value
        :param limit: limit setting
        :return:
        """

        spinBox = self.getByValue(key, receiver)
        comboBox = self.getByValue(key, sender, QComboBox)

        binder = ComboBoxBinder(comboBox)
        if binder.bindSpinBox(spinBox, limit):
            self.__bindingList.append(binder)
        else:
            return False

        return True


class HyperlinkGroup(QObject):
    signalCurrentLinkChanged = Signal(object)

    def __init__(self, exclusive: bool = True,
                 template: Optional[DynamicObject] = None,
                 links: Optional[List[str]] = None, parent: Optional[QWidget] = None):
        super(HyperlinkGroup, self).__init__(parent)
        self._currentText = ""
        self._previousText = ""
        self._linkGroup = list()

        self._template = template
        self._exclusive = exclusive
        self._eventHandle = CustomEventFilterHandler(
            (HyperlinkLabel,),
            (QEvent.MouseButtonPress, QEvent.MouseButtonRelease, QEvent.Wheel,
             QEvent.MouseButtonDblClick, QEvent.HoverLeave, QEvent.HoverEnter,
             QEvent.KeyPress, QEvent.KeyRelease), self
        )
        self.create(links)

    def __len__(self):
        return len(self._linkGroup)

    def __repr__(self):
        return [x.text() for x in self._linkGroup]

    def clear(self):
        self._linkGroup.clear()

    def reset(self):
        [link.reset() for link in self._linkGroup]

    def count(self) -> int:
        return len(self._linkGroup)

    def links(self) -> List[HyperlinkLabel]:
        return self._linkGroup[:]

    def create(self, links: List[str]):
        if isinstance(self._template, DynamicObject) and links:
            for text in links:
                if not isinstance(text, str):
                    continue
                self._template.text = text
                self.addLink(HyperlinkLabel(**self._template.dict))

    def addLink(self, link: HyperlinkLabel) -> bool:
        if not isinstance(link, HyperlinkLabel):
            return False

        self._linkGroup.append(link)
        link.signalClicked.connect(self.slotHyperLinkClicked)
        return True

    def delLink(self, link: HyperlinkLabel) -> bool:
        if not isinstance(link, HyperlinkLabel):
            return False

        if link not in self._linkGroup:
            return False

        self._linkGroup.remove(link)
        return True

    def currentLinkText(self) -> str:
        return self._currentText[:]

    def getPreviousLinkText(self) -> str:
        return self._previousText[:]

    def getLinkByIndex(self, idx: int) -> Union[HyperlinkLabel, None]:
        return self._linkGroup[idx] if 0 <= idx < len(self._linkGroup) else None

    def getLinkByText(self, text: str) -> Union[HyperlinkLabel, None]:
        try:
            return [link for link in self._linkGroup if link.text() == text][0]
        except (ValueError, IndexError):
            return None

    def getCurrentClickedLink(self) -> Union[HyperlinkLabel, None]:
        return self.getLinkByText(self._currentText)

    def slotHyperLinkClicked(self, text: str):
        sender = self.sender()
        if not isinstance(sender, HyperlinkLabel):
            return

        if sender not in self._linkGroup:
            return

        self._previousText, self._currentText = self._currentText, text
        self.signalCurrentLinkChanged.emit(self._currentText)
        if self._exclusive:
            [link.reset() for link in self._linkGroup if link != sender]

    def setDisabled(self, disabled: bool):
        [self._eventHandle.process(link, disabled) for link in self._linkGroup]
