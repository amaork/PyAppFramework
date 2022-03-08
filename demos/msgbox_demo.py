# -*- coding: utf-8 -*-
import sys
from ..gui.msgbox import showMessageBox, MB_TYPES
from PySide2.QtWidgets import QWidget, QLabel, QLineEdit, QPushButton, QHBoxLayout, QApplication, QComboBox


class DemoWidget(QWidget):
    def __init__(self, parent=None):
        super(DemoWidget, self).__init__(parent)

        self.messageType = QComboBox()
        for typeName in MB_TYPES:
            self.messageType.addItem(typeName)

        self.titleEdit = QLineEdit("Message Title")
        self.contextEdit = QLineEdit("This is message context")
        self.contextEdit.setMaximumWidth(300)
        self.showMessage = QPushButton("Show Message")
        self.showMessage.clicked.connect(self.slotShowMessageBox)

        layout = QHBoxLayout()
        layout.addWidget(QLabel("Select message type"))
        layout.addWidget(self.messageType)
        layout.addWidget(self.titleEdit)
        layout.addWidget(self.contextEdit)
        layout.addWidget(self.showMessage)

        self.setLayout(layout)
        self.setWindowTitle("MessageBox Demo")

    def slotShowMessageBox(self):
        showMessageBox(self, self.messageType.currentText(), self.contextEdit.text(), self.titleEdit.text())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DemoWidget()
    window.show()
    sys.exit(app.exec_())
