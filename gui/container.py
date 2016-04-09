# -*- coding: utf-8 -*-

"""
Provide UI elements container
"""

import sys
import copy
import types
from PySide.QtGui import *
from PySide.QtCore import *

sys.path.append("../../")
from PyAppFramework.core.datatype import str2number, str2float

__all__ = ['ComboBoxGroup', 'ComponentManager']


class ComboBoxGroup(QObject):
    sequenceChanged = Signal()

    def __init__(self, template, autoCreate=False, ordered=False, parent=None):
        super(ComboBoxGroup, self).__init__(parent)

        self.__group = list()

        if not isinstance(template, QComboBox):
            print "Template TypeError: {0:s}".format(type(template))
            self.__template = None
            return

        if template.count() <= 1:
            print "ComboBox template data at least needs 2 items"
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

    def __typeCheck(self, item):
        if not self.__template:
            print "TypeError: template is None"
            return False

        if not isinstance(item, QComboBox):
            print "TypeError: {0:x}".format(type(item))
            return False

        if item.count() != self.__template.count():
            print "QComboBox count mismatch"
            return False

        for index in range(item.count()):
            if item.itemText(index) != self.__template.itemText(index):
                print "QComboBox item text mismatch"
                return False

        return True

    def __indexCheck(self, index):
        if not isinstance(index, int):
            print "TypeError:{0:s}".format(type(index))
            return False

        if index >= self.count() or index < 0:
            print "IndexError: out of range"
            return False

        return True

    def __findConflictItem(self, current):
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

    def __findUnusedIndex(self):
        if self.count() == 0:
            return None

        values = [item.currentIndex() for item in self.__group]
        values.sort()
        if values == range(self.count()):
            return None

        for index in range(self.count()):
            if values.count(index) == 0:
                return index

        return None

    def count(self):
        return len(self.__group)

    def items(self):
        """Get all ComboBox items in group"""
        return self.__group

    def itemAt(self, idx):
        """Get idx specified ComboBox item

        :param idx: index
        :return:  QComboBox object or None
        """
        if not self.__indexCheck(idx):
            return None

        return self.__group[idx]

    def setEditable(self, editable):
        for item in self.items():
            item.setEnabled(editable)

    def addComboBox(self, box, ordered=False):
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

    def getSequence(self):
        """Get group QComboBox index sequence
        """
        return [item.currentIndex() for item in self.__group]

    def getSequenceText(self):
        """Get group QComboBox texts
        """
        return [item.currentText() for item in self.__group]

    def setSequence(self, sequence):
        """Set group QComboBox sequence

        :param sequence: QComboBox index sequence
        :return:
        """
        if not hasattr(sequence, "__iter__"):
            print "TypeError:{0:s}".format(type(sequence))
            return False

        if len(sequence) != self.count():
            print "Sequence length error"
            return False

        for index in sequence:
            if not isinstance(index, int):
                print "Sequence item TypeError: {0:s}".format(type(index))
                return False

        values = copy.copy(sequence)
        values.sort()

        if values != range(len(sequence)):
            print "Sequence item conflict"
            return False

        for item, index in zip(self.__group, sequence):
            item.setCurrentIndex(index)

        return True


class ComponentManager(QObject):
    dataChanged = Signal()

    __supportBinder = {

        QSpinBox: (QSpinBox, QDoubleSpinBox),
        QDoubleSpinBox: (QSpinBox, QDoubleSpinBox),
        QComboBox: (QComboBox, QLabel, QSpinBox, QDoubleSpinBox),
    }

    def __init__(self, obj, parent=None):
        super(ComponentManager, self).__init__(parent)

        # Get object layout
        if isinstance(obj, QWidget) and isinstance(obj.layout(), QLayout):
            self.__object = obj.layout()
        elif isinstance(obj, QLayout) and obj.count() > 0:
            self.__object = obj
        else:
            self.__object = None

        # For dynamic bind usage
        self.__bindingList = dict()
        self.__bindingProcess = [

            self.__spinBoxBindProcess,
            self.__comboBoxBindProcess,
            self.__comboBoxBindLabelProcess,
            self.__comboBoxBindSpinBoxProcess,
        ]

        # Watch all component data changed event
        self.__initSignalAndSlots()

    def __initSignalAndSlots(self):
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

    def __bindTypeCheck(self, sender, receiver):
        receivers = self.__supportBinder.get(type(sender))
        if receivers is None:
            print "Sender type unsupported:{0:s}".format(type(sender))
            return False

        if type(receiver) not in receivers:
            print "Receiver type unsupported:{0:s}".format(type(receiver))
            return False

        return True

    def __bind(self, sender, receiver, data):
        """Bind sender and receiver

        :param sender: Sender object
        :param receiver: Receiver object
        :param data: bind data
        :return:
        """
        receivers = self.__bindingList.get(sender)
        if receivers is None:
            receivers = [(receiver, data)]
        elif isinstance(receivers, list):
            receivers.append((receiver, data))

        self.__bindingList[sender] = receivers

    def __getBindReceivers(self, sender):
        """Get bind receivers list

        :param sender:Sender object
        :return:
        """
        receivers = self.__bindingList.get(sender)
        if isinstance(receivers, list):
            return receivers
        else:
            return []

    def __isBinding(self, sender):
        """Check if object is bind

        :param sender:
        :return:
        """
        return sender in self.__bindingList

    def __bindProcess(self, sender):
        # Process each receivers
        for receiver in self.__getBindReceivers(sender):
            if not isinstance(receiver, tuple):
                continue

            # Get receiver and it's data
            receiver, data = receiver
            if not self.__bindTypeCheck(sender, receiver):
                continue

            # Process
            for handle in self.__bindingProcess:
                if not hasattr(handle, "__call__"):
                    continue

                if handle(sender, receiver, data):
                    break

    def __spinBoxBindProcess(self, sender, receiver, data):
        if not isinstance(sender, QSpinBox) and not isinstance(sender, QDoubleSpinBox):
            return False

        if not isinstance(receiver, QSpinBox) and not isinstance(receiver, QDoubleSpinBox):
            return False

        if isinstance(data, int) or isinstance(data, float):
            receiver.setValue(sender.value() * data)

        return True

    def __comboBoxBindProcess(self, sender, receiver, data):
        if not isinstance(sender, QComboBox) or not isinstance(receiver, QComboBox):
            return False

        if data and sender.count() == receiver.count() and sender.count():
            receiver.setCurrentIndex(sender.count() - sender.currentIndex() - 1)
        else:
            receiver.setCurrentIndex(sender.currentIndex())

        return True

    def __comboBoxBindLabelProcess(self, sender, receiver, data):
        if not isinstance(sender, QComboBox) or not isinstance(receiver, QLabel):
            return False

        if data and len(data) == sender.count() and isinstance(data[sender.currentIndex()], types.StringTypes):
            receiver.setText(data[sender.currentIndex()])

        return True

    def __comboBoxBindSpinBoxProcess(self, sender, receiver, data):
        if not isinstance(sender, QComboBox):
            return False

        if not isinstance(receiver, QSpinBox) and not isinstance(receiver, QDoubleSpinBox):
            return False

        if hasattr(data, "__iter__") and len(data) == sender.count():
            setting = data[sender.currentIndex()]

            # Setting range and step
            if hasattr(setting, "__iter__"):
                for num in setting:
                    if not isinstance(num, int) and not isinstance(num, float):
                        return True

                if len(setting) == 3:
                    receiver.setSingleStep(setting[2])
                    receiver.setRange(setting[0], setting[1])
                elif len(setting) == 2:
                    receiver.setRange(setting[0], setting[1])

            # Setting value
            elif isinstance(setting, int) or isinstance(sender, float):
                receiver.setRange(setting, setting)

        return True

    def __getComponentsWithType(self, componentType):
        if isinstance(componentType, type):
            components = self.getByType(componentType)
        else:
            components = self.getAll()

        return components

    def __getComponentData(self, component):
        if isinstance(component, QSpinBox):
            return str(component.value())
        elif isinstance(component, QDoubleSpinBox):
            return str(component.value())
        elif isinstance(component, QComboBox):
            return str(component.currentIndex())
        elif isinstance(component, QCheckBox):
            return str(component.isChecked())
        elif isinstance(component, QRadioButton):
            return str(component.isChecked())
        elif isinstance(component, QLineEdit):
            return component.text()
        elif isinstance(component, QTextEdit):
            return component.toPlainText()
        elif isinstance(component, QPlainTextEdit):
            return component.toPlainText()
        elif isinstance(component, QDateTimeEdit):
            return component.displayFormat()
        elif isinstance(component, QDial):
            return component.value()
        else:
            return ""

    def __setComponentData(self, component, data):
        if isinstance(component, QSpinBox):
            component.setValue(str2number(data))
        elif isinstance(component, QDoubleSpinBox):
            component.setValue(str2float(data))
        elif isinstance(component, QComboBox):
            index = str2number(data)
            index = 0 if index >= component.count() else index
            component.setCurrentIndex(index)
        elif isinstance(component, QCheckBox):
            component.setCheckable(True)
            component.setChecked(str2number(data))
        elif isinstance(component, QRadioButton):
            component.setCheckable(True)
            component.setChecked(str2number(data))
        elif isinstance(component, QLineEdit):
            if isinstance(data, types.StringTypes):
                component.setText(data)
        elif isinstance(component, QTextEdit):
            if isinstance(data, types.StringTypes):
                component.setText(data)
        elif isinstance(component, QPlainTextEdit):
            if isinstance(data, types.StringTypes):
                component.setPlainText(data)
        elif isinstance(component, QDial):
            component.setValue(str2number(data))

    @staticmethod
    def findParentLayout(obj, top):
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
    def getAllComponents(obj):
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

            sublayout = item.layout()
            # Is a QLayout
            if isinstance(sublayout, QLayout):
                components.extend(ComponentManager.getAllComponents(sublayout))

        return components

    def slotDataChanged(self):
        sender = self.sender()
        if sender not in self.getAll():
            return

        # Emit dataChanged signal
        self.dataChanged.emit()

        # Object bind process
        if not self.__isBinding(sender):
            return

        # Process bind
        self.__bindProcess(sender)

    def getAll(self):
        if not self.__object:
            return []

        return self.getAllComponents(self.__object)

    def getParentLayout(self, obj):
        if obj not in self.getAll():
            return None

        return self.findParentLayout(obj, self.__object)

    def findRowSibling(self, obj):
        layout = self.getParentLayout(obj)
        if not isinstance(layout, QGridLayout):
            print "Only QGridLayout support find row sibling:{0:s}".format(type(layout))
            return []

        for row in range(layout.rowCount()):
            for column in range(layout.columnCount()):
                item = layout.itemAt(row * layout.columnCount() + column)
                if isinstance(item, QLayoutItem) and item.widget() == obj:
                    return [layout.itemAt(row * layout.columnCount() + column).widget()
                            for column in range(layout.columnCount())]

        return []

    def findColumnSibling(self, obj):
        layout = self.getParentLayout(obj)
        if not isinstance(layout, QGridLayout):
            print "Only QGridLayout support find column sibling:{0:s}".format(type(layout))
            return []

        for row in range(layout.rowCount()):
            for column in range(layout.columnCount()):
                item = layout.itemAt(row * layout.columnCount() + column)
                if isinstance(item, QLayoutItem) and item.widget() == obj:
                    return [layout.itemAt(row * layout.columnCount() + column).widget()
                            for row in range(layout.rowCount() - 1)]

        return []

    def getNextSibling(self, obj):
        layout = self.getParentLayout(obj)
        if not isinstance(layout, QLayout):
            return None

        components = self.getAllComponents(layout)
        index = components.index(obj)
        if index >= len(components) - 2:
            return None
        else:
            return components[index + 1]

    def getPrevSibling(self, obj):
        layout = self.getParentLayout(obj)
        if not isinstance(layout, QLayout):
            return None

        components = self.getAllComponents(layout)
        index = components.index(obj)
        if index == 0:
            return None
        else:
            return components[index - 1]

    def getByType(self, componentType):
        """Get componentType specified type components

        :param componentType: component type
        :return: matched objects
        """

        if not isinstance(componentType, type):
            print "TypeError:{0:s}".format(type(componentType))
            return []

        components = list()
        for component in self.getAll():
            if isinstance(component, componentType):
                components.append(component)

        return components

    def getByValue(self, key, value, componentType=None):
        """Get componentType specified component property key  is value

        :param key: property key
        :param value: property keys value
        :param componentType: component componentType
        :return:
        """

        if not isinstance(key, str) or not isinstance(value, types.StringTypes):
            print "Property TypeError:{0:s}, {1:s}".format(type(key), type(value))
            return None

        # Search by property
        for component in self.__getComponentsWithType(componentType):
            if component.property(key) == value:
                return component

        return None

    def findKey(self, key, componentType=None):
        """find component with componentType specified type, and key specified property key

        :param key: property key
        :param componentType: component type
        :return:
        """

        if not isinstance(key, str):
            print "Property key typeError: {0:s}".format(type(key))
            return []

        lst = list()
        for component in self.__getComponentsWithType(componentType):
            if component.property(key):
                lst.append(component)

        return lst

    def findValue(self, key, searchValue, componentType=None):
        """Find component with componentType specified types and property key hast value

        :param key: property key
        :param searchValue: property value key value
        :param componentType: component types
        :return:
        """
        lst = list()
        for component in self.findKey(key, componentType):
            value = component.property(key)
            if value is not None and searchValue in value:
                lst.append(component)

        return lst

    def getData(self, key, componentType=None):
        data = dict()
        components = list()

        if hasattr(componentType, "__iter__"):
            for t in componentType:
                if isinstance(t, type):
                    components.extend(self.findKey(key, t))
        else:
            components = self.findKey(key, componentType)

        for component in components:
            value = component.property(key)
            data[value] = self.__getComponentData(component)

        return data

    def setData(self, key, data):
        if not isinstance(key, str) or not isinstance(data, dict):
            print "TypeError:{0:s}, {1:s}".format(type(key), type(data))
            return False

        for component in self.getAll():
            property_key = component.property(key)
            value = data.get(property_key)

            if value:
                self.__setComponentData(component, value)

        return True

    def bindSpinBox(self, key, sender, receiver, ratio, bilateral=False):
        """Bind two spinbox, when one spinbox is changes another will linkage

        :param key: property key
        :param sender: sender Spinbox property value
        :param receiver: receiver Spinbox property value
        :param ratio: linkage ratio
        :param bilateral: linkage is bilateral setting
        :return:
        """

        senderSpinBox = self.getByValue(key, sender)
        receiverSpinBox = self.getByValue(key, receiver)

        if not self.__bindTypeCheck(senderSpinBox, receiverSpinBox):
            return False

        if not isinstance(ratio, int) and not isinstance(ratio, float):
            print "TypeError, binSpinBox ratio should be a number or float:{0:s}".format(type(ratio))
            return False

        # Bind two SpinBox range
        receiverSpinBox.setRange(senderSpinBox.minimum() * ratio, senderSpinBox.maximum() * ratio)

        # Set dst SpinBox decimals
        if isinstance(ratio, float):
            receiverSpinBox.setDecimals(len(str(ratio).split('.')[-1]))
            receiverSpinBox.setSingleStep(ratio)

        # Bind
        if bilateral:
            senderSpinBox.setEnabled(True)
            receiverSpinBox.setEnabled(True)
            self.__bind(senderSpinBox, receiverSpinBox, ratio)
            self.__bind(receiverSpinBox, senderSpinBox, 1.0 / ratio)
        else:
            senderSpinBox.setEnabled(True)
            receiverSpinBox.setEnabled(False)
            self.__bind(senderSpinBox, receiverSpinBox, ratio)

        return True

    def bindComboBox(self, key, sender, receiver, reverse=False, bilateral=False):
        """Bind two ComboBox, on changed, another changed too

        :param key: property key
        :param sender: Sender comboBox property value
        :param receiver:  Receiver ComboBox property value
        :param bilateral: if is set, sender can be receive and receive can be sender
        :param reverse:
        :return:
        """

        senderComboBox = self.getByValue(key, sender)
        receiverComboBox = self.getByValue(key, receiver)

        if not self.__bindTypeCheck(senderComboBox, receiverComboBox):
            return False

        if senderComboBox.count() != receiverComboBox.count():
            print "Two bind ComboBox count number should same!"
            return False

        if bilateral:
            senderComboBox.setEnabled(True)
            receiverComboBox.setEnabled(True)
            self.__bind(senderComboBox, receiverComboBox, reverse)
            self.__bind(receiverComboBox, senderComboBox, reverse)
        else:
            senderComboBox.setEnabled(True)
            receiverComboBox.setEnabled(False)
            self.__bind(senderComboBox, receiverComboBox, receiver)

        return True

    def bindComboBoxWithLabel(self, key, sender, receiver, texts):
        """Bind ComboBox with label, ComboBox current index changed, label text changed too

        :param key: property key
        :param sender: QComboBox property value
        :param receiver: QLabel property value
        :param texts:  QLabel texts
        :return:
        """

        comboBox = self.getByValue(key, sender, QComboBox)
        label = self.getByValue(key, receiver, QLabel)

        if not self.__bindTypeCheck(comboBox, label):
            return False

        if not hasattr(texts, "__iter__") or comboBox.count() != len(texts):
            print "Label texts type error:{0:s}".format(type(texts))
            return False

        for text in texts:
            if not isinstance(text, types.StringTypes):
                print "Label text type error:{0:s}".format(type(text))
                return False

        self.__bind(comboBox, label, texts)
        return True

    def bindComboBoxWithSpinBox(self, key, sender, receiver, limit):
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

        comboBox = self.getByValue(key, sender, QComboBox)
        spinBox = self.getByValue(key, receiver)

        if not self.__bindTypeCheck(comboBox, spinBox):
            return False

        if not hasattr(limit, "__iter__") or len(limit) != comboBox.count():
            print "Limit data type error:{0:s}".format(type(limit))
            return False

        self.__bind(comboBox, spinBox, limit)
        return True
