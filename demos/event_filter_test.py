# -*- coding: utf-8 -*-
import sys
from PySide2.QtCore import QEvent
from PySide2.QtWidgets import QPushButton, QRadioButton, QCheckBox, QLineEdit, QDoubleSpinBox, QSpinBox, QLabel, \
    QHBoxLayout, QApplication

from ..gui.msgbox import *
from ..gui.widget import BasicWidget
from ..gui.container import ComponentManager
from ..gui.misc import CustomEventFilterHandler


class DemoEventFilter(BasicWidget):
    def __init__(self, parent=None):
        super(DemoEventFilter, self).__init__(parent)

        self.disable_event_handle = CustomEventFilterHandler(
            (QRadioButton, QCheckBox, QSpinBox, QDoubleSpinBox, QPushButton, QLineEdit),
            (QEvent.MouseButtonRelease, QEvent.MouseButtonPress, QEvent.MouseButtonDblClick,
             QEvent.KeyPress, QEvent.KeyRelease, QEvent.Wheel),
            self,
        )

    def _initUi(self):
        layout = QHBoxLayout()
        self.ui_btn = QPushButton("Button")
        self.ui_enable = QPushButton("Enable")
        self.ui_disable = QPushButton("Disable")
        layout.addWidget(QLabel("RadioButton"))
        layout.addWidget(QRadioButton())
        layout.addWidget(QLabel("CheckBox"))
        layout.addWidget(QCheckBox())
        layout.addWidget(QLabel("SpinBox"))
        layout.addWidget(QSpinBox())
        layout.addWidget(QLabel("DoubleSpinbox"))
        layout.addWidget(QDoubleSpinBox())
        layout.addWidget(QLabel("LineEdit"))
        layout.addWidget(QLineEdit())
        layout.addWidget(self.ui_btn)
        layout.addWidget(self.ui_enable)
        layout.addWidget(self.ui_disable)

        self.setLayout(layout)
        self.setWindowTitle("Qt 事件过滤处理")
        self.ui_manager = ComponentManager(layout)

    def _initData(self):
        pass

    def _initSignalAndSlots(self):
        self.ui_btn.clicked.connect(self.slotBtn)
        self.ui_enable.clicked.connect(self.slotEnableEdit)
        self.ui_disable.clicked.connect(self.slotDisableEdit)

    def slotBtn(self):
        showMessageBox(self, MB_TYPE_INFO, "按键点击")

    def slotEnableEdit(self):
        for item in self.ui_manager.getAll():
            if item not in (self.ui_enable, self.ui_enable):
                self.disable_event_handle.process(item, False)

        showMessageBox(self, MB_TYPE_INFO, "允许修改")

    def slotDisableEdit(self):
        for item in self.ui_manager.getAll():
            if item not in (self.ui_enable, self.ui_disable):
                self.disable_event_handle.process(item, True)

        showMessageBox(self, MB_TYPE_INFO, "禁止修改")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    widget = DemoEventFilter()
    widget.show()
    sys.exit(app.exec_())
