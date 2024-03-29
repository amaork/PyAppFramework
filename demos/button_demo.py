# -*- coding: utf-8 -*-
import sys
from .images import ImagesPath
from ..gui.button import RectButton, RoundButton, IconButton, StateButton, TextButton
from PySide2.QtGui import QImageReader
from PySide2.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QComboBox, QPushButton, QLabel, \
    QFileDialog, QApplication


class DemoWidget(QWidget):
    def __init__(self, parent=None):
        super(DemoWidget, self).__init__(parent)
        self.buttonType = [TextButton, RectButton, RoundButton]
        self.buttonList = ["TextButton", "RectButton", "RoundButton", "IconButton"]

        self.addButton = QPushButton("Add a button")
        self.buttonSelect = QComboBox()
        self.buttonSelect.addItems(self.buttonList)
        self.addButton.clicked.connect(self.slotAddButton)

        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("Button type"))
        h_layout.addWidget(self.buttonSelect)
        h_layout.addWidget(self.addButton)

        self.g_layout = QGridLayout()
        layout = QVBoxLayout()
        layout.addLayout(h_layout)
        layout.addLayout(self.g_layout)

        self.setLayout(layout)
        self.setWindowTitle("Button Demo")

    def slotAddButton(self):
        buttonText = self.buttonSelect.currentText()
        typeIndex = self.buttonList.index(buttonText)
        buttonTextGroup = ("{} ON".format(buttonText), "{} OFF".format(buttonText))

        state = StateButton(50)
        if buttonText == "RoundButton":
            button = RoundButton(200, text=buttonTextGroup)
        elif buttonText == "IconButton":
            all_ = ""
            for name in QImageReader.supportedImageFormats():
                all_ += "*.{} ".format(name)
            files, _ = QFileDialog.getOpenFileNames(self,
                                                    "Select icon images",
                                                    ImagesPath,
                                                    "Images(*.jpg)")
            button = IconButton(icons=files)
        else:
            button = self.buttonType[typeIndex](200, 50, text=buttonTextGroup)

        button.toggled.connect(state.slotChangeView)
        self.g_layout.addWidget(QLabel(buttonText), typeIndex, 0)
        self.g_layout.addWidget(button, typeIndex, 1)
        self.g_layout.addWidget(state, typeIndex, 2)

        self.buttonSelect.removeItem(self.buttonSelect.currentIndex())
        if self.buttonSelect.count() == 0:
            self.addButton.setDisabled(True)
            self.buttonSelect.setDisabled(True)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    widget = DemoWidget()
    widget.show()
    sys.exit(app.exec_())
