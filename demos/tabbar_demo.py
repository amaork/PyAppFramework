# -*- coding: utf-8 -*-
import sys
from PySide2.QtWidgets import *
from ..gui.misc import TabBar
from ..gui.container import ComponentManager


class TabBarDemo(QWidget):
    PositionText = ["East", "West", "South", "North"]
    Positions = [QTabWidget.East, QTabWidget.West, QTabWidget.South, QTabWidget.North]

    # noinspection PyTypeChecker
    def __init__(self, parent=None):
        super(TabBarDemo, self).__init__(parent)

        layout = QHBoxLayout()

        vertical = QRadioButton("Vertical")
        vertical.setChecked(True)
        vertical.setProperty("name", "vertical")

        horizontal = QRadioButton("Horizontal")
        horizontal.setProperty("name", "horizontal")

        direction = QButtonGroup()
        direction.addButton(vertical)
        direction.addButton(horizontal)

        position = QComboBox()
        position.setProperty("name", "position")
        position.addItems(self.PositionText)

        layout.addWidget(QLabel("TabBar direction:"))
        layout.addWidget(vertical)
        layout.addWidget(horizontal)
        layout.addWidget(QLabel("TabBar position:"))
        layout.addWidget(position)
        self.tabs = QTabWidget()
        self.setLayout(layout)
        self.manager = ComponentManager(layout)
        self.manager.dataChanged.connect(self.slotCreateTabWidget)

    def slotCreateTabWidget(self):
        settings = self.manager.getData("name")
        width, height = (25, 75) if settings.get("vertical") else (75, 25)
        self.tabs = QTabWidget()
        self.tabs.setTabBar(TabBar(width=width, height=height))
        for i in range(5):
            page = QLabel("Area #{}".format(i))
            self.tabs.addTab(page, "Tab{}".format(i))
        self.tabs.setTabPosition(self.Positions[settings.get("position")])
        self.tabs.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = TabBarDemo()
    widget.show()
    sys.exit(app.exec_())
