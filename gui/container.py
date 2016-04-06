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

    def __init__(self, parent=None):
        super(ComboBoxGroup, self).__init__(parent)

        self.__group = list()

    def __indexCheck(self, index):
        if not isinstance(index, int):
            print "TypeError:{0:s}".format(type(index))
            return False

        if index >= len(self.__group) or index < 0:
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
        if len(self.__group) == 0:
            return None

        values = [item.currentIndex() for item in self.__group]
        values.sort()
        if values == range(len(self.__group)):
            return None

        for index in range(len(self.__group)):
            if values.count(index) == 0:
                return index

        return None

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

    def takeItem(self, idx):
        """Remove QComboBox item from group and return item

        :param idx: index
        :return: None or QComboBox
        """
        if not self.__indexCheck(idx):
            return None

        item = self.itemAt(idx)
        self.removeComboBox(item)
        return item

    def addComboBox(self, box):
        """And a QComboBox to group

        :param box: QComboBox item
        :return: True / False
        """
        if not isinstance(box, QComboBox):
            print "TypeError:{0:s}".format(type(box))
            return False

        if box in self.__group:
            print "Item already in group"
            return False

        self.__group.append(box)
        box.currentIndexChanged.connect(self.slotDataChanged)
        return True

    def removeComboBox(self, box):
        """Remove QComboBox item from group

        :param box: QComboBox
        :return: True / False
        """
        if not isinstance(box, QComboBox):
            print "TypeError:{0:s}".format(type(box))
            return False

        if box not in self.__group:
            return False

        box.currentIndexChanged.disconnect(self.slotDataChanged)
        self.__group.remove(box)
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

        if len(sequence) != len(self.__group):
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
