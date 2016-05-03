# -*- coding: utf-8 -*-

import sys

sys.path.append("../../")
from gui.container import *
from PySide.QtGui import *


class ComboBoxGroupTest(QWidget):
    def __init__(self, parent=None):
        super(ComboBoxGroupTest, self).__init__(parent)

        frameStyle = QFrame.Sunken | QFrame.Panel

        country = QComboBox()
        country.addItem("China")
        country.addItem("Japan")
        country.addItem("Korea")
        country.addItem("England")
        country.addItem("American")

        self.reverse = QPushButton("Reverse sequence")
        self.reverse.clicked.connect(self.__slotSetReverse)

        self.editable = QCheckBox("Editable")
        self.editable.setCheckable(True)
        self.editable.setChecked(True)
        self.editable.toggled.connect(self.__slotSetEditable)

        self.getSequence = QPushButton("Get sequence")
        self.sequenceLabel = QLabel()
        self.sequenceLabel.setFrameStyle(frameStyle)
        self.getSequence.clicked.connect(self.__slotGetSequence)

        self.getSequenceText = QPushButton("Get sequence text")
        self.textLabel = QLabel()
        self.textLabel.setFrameStyle(frameStyle)
        self.getSequenceText.clicked.connect(self.__slotGetSequenceText)

        self.countrySequence = ComboBoxGroup(country, autoCreate=True, ordered=True)
        self.countrySequence.sequenceChanged.connect(self.__slotGetSequence)
        self.countrySequence.sequenceChanged.connect(self.__slotGetSequenceText)

        layout = QVBoxLayout()
        for item in self.countrySequence.items():
            layout.addWidget(item)

        layout1 = QGridLayout()
        layout1.addWidget(self.editable, 0, 0)
        layout1.addWidget(self.reverse, 0, 1)
        layout1.addWidget(self.getSequence, 1, 0)
        layout1.addWidget(self.sequenceLabel, 1, 1)
        layout1.addWidget(self.getSequenceText, 2, 0)
        layout1.addWidget(self.textLabel, 2, 1)

        layout.addLayout(layout1)
        self.setLayout(layout)
        self.setWindowTitle("ComboBoxGroup Test")

        self.__slotGetSequence()
        self.__slotGetSequenceText()
        self.setFixedSize(self.sizeHint())

    def __slotSetReverse(self):
        sequence = self.countrySequence.getSequence()
        sequence.reverse()
        self.countrySequence.setSequence(sequence)

    def __slotSetEditable(self, editable):
        self.countrySequence.setEditable(editable)

    def __slotGetSequence(self):
        self.sequenceLabel.setText("{0:s}".format(self.countrySequence.getSequence()))

    def __slotGetSequenceText(self):
        self.textLabel.setText("{0:s}".format(self.countrySequence.getSequenceText()))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ComboBoxGroupTest()
    window.show()
    sys.exit(app.exec_())
