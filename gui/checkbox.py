# -*- coding: utf-8 -*-
import json
from PySide.QtGui import *
from PySide.QtCore import *
from ..core.datatype import DynamicObject, DynamicObjectEncodeError, str2number
__all__ = ['CheckBox', 'CheckBoxStyleSheet', 'CheckBoxDelegate']


class CheckBoxStyleSheet(DynamicObject):
    _properties = {'withBox', 'sizeFactor', 'font',
                   'boxColor', 'fillColor', 'hoverColor', 'background', 'foreground'}

    @classmethod
    def default(cls):
        return CheckBoxStyleSheet(withBox=True,
                                  sizeFactor=1.3,
                                  font=("等线 Light", 11),
                                  hoverColor=(240, 154, 55),
                                  boxColor=(0, 0, 0), fillColor=(240, 154, 55),
                                  background=(255, 255, 255), foreground=(255, 0, 0))

    def getFont(self):
        try:
            return QFont(*self.font)
        except TypeError:
            return QFont(("等线 Light", 11))

    def getBoxColor(self):
        try:
            return QColor(*self.boxColor)
        except TypeError:
            return QColor(Qt.black)

    def getHoverColor(self):
        try:
            return QColor(*self.hoverColor)
        except TypeError:
            return QColor(240, 154, 55)

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

    def __init__(self, text: str = "", stylesheet: dict or None = None, parent: QWidget or None = None):
        super(CheckBox, self).__init__(text, parent)
        self.setAutoFillBackground(True)
        self._styleSheet = CheckBoxStyleSheet.default()
        self._boxColor = self._styleSheet.getBoxColor()
        self._sizeFactor = self._styleSheet.sizeFactor
        if stylesheet:
            self.setStyleSheet(stylesheet)

    def reverse(self):
        self.setChecked(Qt.Unchecked if self.isChecked() else Qt.Checked)

    def styleSheet(self) -> str:
        return str(self._styleSheet)

    def getBoxColor(self):
        return self._boxColor

    def getSizeFactor(self):
        return self._sizeFactor

    def setStyleSheet(self, stylesheet: dict or DynamicObject):
        try:
            self._styleSheet.update(stylesheet)
            self._boxColor = self._styleSheet.getBoxColor()
            self._sizeFactor = self._styleSheet.sizeFactor
            self.update()
        except (json.JSONDecodeError, DynamicObjectEncodeError, TypeError) as e:
            print("Invalid CheckEditor stylesheet({}): {}".format(stylesheet, e))

    def paintEvent(self, ev):
        painter = QPainter(self)
        rect = self.rect()

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(QBrush(self.getBoxColor()), 2))
        painter.fillRect(self.rect(), self._styleSheet.backgroundColor())

        try:
            min_ = min(rect.height(), rect.width())
            size = QSize(min_ / self.getSizeFactor(), min_ / self.getSizeFactor())
        except (OverflowError, ZeroDivisionError):
            self._sizeFactor = CheckBoxStyleSheet.default().sizeFactor
            min_ = min(rect.height(), rect.width())
            size = QSize(min_ / self.getSizeFactor(), min_ / self.getSizeFactor())

        x = rect.center().x() - size.width() / 2
        y = rect.center().y() - size.height() / 2

        if self.text():
            metric = QFontMetrics(self._styleSheet.getFont())
            x += metric.width(self.text()) / 2

            painter.setFont(self._styleSheet.getFont())
            painter.drawText(self.rect(), Qt.AlignLeft | Qt.AlignVCenter, self.text())

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

    def enterEvent(self, ev):
        if not self.isCheckable() or not self.isEnabled():
            return

        self._sizeFactor *= 1.1
        self._boxColor = self._styleSheet.getHoverColor()
        self.update()

    def leaveEvent(self, ev):
        if not self.isCheckable() or not self.isEnabled():
            return

        self._sizeFactor = self._styleSheet.sizeFactor
        self._boxColor = self._styleSheet.getBoxColor()
        self.update()

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
    def __init__(self, text: str = "", stylesheet: DynamicObject or None = None, parent: QWidget or None = None):
        super(CheckBoxDelegate, self).__init__(parent)
        self._text = text
        self._stylesheet = stylesheet.dict if isinstance(stylesheet, DynamicObject) else None

    @Slot()
    def commitAndCloseEditor(self):
        sender = self.sender()
        self.commitData.emit(sender)
        self.closeEditor.emit(sender, QAbstractItemDelegate.NoHint)

    def setEditorData(self, editor: CheckBox, index: QModelIndex):
        if not isinstance(index, QModelIndex) or not isinstance(editor, CheckBox) or index.data() is None:
            return

        editor.setChecked(bool(str2number(index.data())))

    def setModelData(self, editor: CheckBox, model: QAbstractItemModel, index: QModelIndex):
        if not isinstance(editor, CheckBox) or not isinstance(model, QAbstractItemModel) \
                or not isinstance(index, QModelIndex) or index.data() is None:
            return

        model.setData(index, editor.isChecked())

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex):
        if not isinstance(index, QModelIndex):
            return

        editor = CheckBox(text=self._text, stylesheet=self._stylesheet, parent=parent)
        editor.editingFinished.connect(self.commitAndCloseEditor)
        return editor
