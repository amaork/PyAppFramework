# -*- coding: utf-8 -*-

"""
Provide UI elements container
"""

import copy
from PySide.QtGui import *
from PySide.QtCore import *

__all__ = ['ComboBoxGroup']


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
