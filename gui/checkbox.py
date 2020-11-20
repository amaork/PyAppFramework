# -*- coding: utf-8 -*-
import json
from PySide.QtGui import *
from PySide.QtCore import *
from ..core.datatype import DynamicObject, DynamicObjectEncodeError
__all__ = ['CheckBox', 'CheckBoxStyleSheet', 'CheckBoxDelegate']


class CheckBoxStyleSheet(DynamicObject):
    _properties = {'withBox', 'boxColor', 'fillColor',
                   'sizeFactor', 'background', 'foreground'}

    @classmethod
    def default(cls):
        return CheckBoxStyleSheet(withBox=True, sizeFactor=1.3,
                                  boxColor=(0, 0, 0), fillColor=(240, 154, 55),
                                  background=(255, 255, 255), foreground=(255, 0, 0))

    def getBoxColor(self):
        try:
            return QColor(*self.boxColor)
        except TypeError:
            return QColor(Qt.black)

    def getFilledColor(self):
        try:
            return QColor(*self.fillColor)
        except TypeError:
            return None

    def backgroundColor(self):
        try:
            return QColor(*self.background)
        except TypeError:
            return QColor(Qt.white)

    def foregroundColor(self):
        try:
            return QColor(*self.foreground)
        except TypeError:
            return QColor(Qt.red)


class CheckBox(QCheckBox):
    editingFinished = Signal()

    def __init__(self, parent=None):
        super(CheckBox, self).__init__(parent)
        self._styleSheet = CheckBoxStyleSheet.default()
        self.setAutoFillBackground(True)

    def reverse(self):
        self.setChecked(Qt.Unchecked if self.isChecked() else Qt.Checked)

    def styleSheet(self) -> str:
        return str(self._styleSheet)

    def setStyleSheet(self, stylesheet: str):
        try:
            style = json.loads(stylesheet)
            self._styleSheet.update(style)
            self.update()
        except (json.JSONDecodeError, DynamicObjectEncodeError) as e:
            print("Invalid CheckEditor stylesheet: {}".format(stylesheet, e))

    def paintEvent(self, ev):
        painter = QPainter(self)
        rect = self.rect()

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QBrush(self._styleSheet.getBoxColor()), 2))
        painter.fillRect(self.rect(), self._styleSheet.backgroundColor())

        min_ = min(rect.height(), rect.width())
        size = QSize(min_ / self._styleSheet.sizeFactor, min_ / self._styleSheet.sizeFactor)

        x = rect.center().x() - size.width() / 2
        y = rect.center().y() - size.height() / 2

        if self._styleSheet.withBox:
            painter.drawRect(x, y, size.width(), size.height())

        if self.isChecked():
            check = QPolygonF()
            painter.setPen(QPen(self._styleSheet.foregroundColor()))
            painter.setBrush(QBrush(self._styleSheet.getFilledColor(), Qt.SolidPattern))

            check.append(QPointF(x, y + size.height() / 2))
            check.append(QPointF(x + size.width() / 2, y + size.height() / 2 + size.height() / 5))
            check.append(QPointF(x + size.width() + size.width() / 3, rect.y() + 1))
            check.append(QPointF(x + size.width() / 2, y + size.height() / 2 + size.height() / 5 * 2))
            painter.drawPolygon(check, Qt.WindingFill)

        painter.restore()

    def mousePressEvent(self, ev):
        if ev.button() != Qt.LeftButton or ev.type() == QEvent.MouseButtonDblClick or not self.isCheckable():
            return

        self.reverse()
        self.update()

    def mouseReleaseEvent(self, ev):
        if ev.button() != Qt.LeftButton or not self.isCheckable():
            return

        self.editingFinished.emit()


class CheckBoxDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super(CheckBoxDelegate, self).__init__(parent)

    @Slot()
    def commitAndCloseEditor(self):
        sender = self.sender()
        self.commitData.emit(sender)
        self.closeEditor.emit(sender, QAbstractItemDelegate.NoHint)

    def setEditorData(self, editor: CheckBox, index: QModelIndex):
        if not isinstance(index, QModelIndex) or not isinstance(editor, CheckBox) or index.data() is None:
            return

        editor.setChecked(bool(int(index.data())))

    def setModelData(self, editor: CheckBox, model: QAbstractItemModel, index: QModelIndex):
        if not isinstance(editor, CheckBox) or not isinstance(model, QAbstractItemModel) \
                or not isinstance(index, QModelIndex) or index.data() is None:
            return

        model.setData(index, editor.isChecked())

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex):
        if not isinstance(index, QModelIndex):
            return

        editor = CheckBox(parent)
        editor.editingFinished.connect(self.commitAndCloseEditor)
        return editor
