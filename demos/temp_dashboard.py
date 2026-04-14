# -*- coding: utf-8 -*-
import json
import sys

from PySide2.QtCore import Qt, QTimer
from PySide2.QtWidgets import (
    QApplication,
    QColorDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..dashboard.cc.temp import TemperatureDashboard
from PySide2.QtGui import QColor

# ──────────────────────────────────────────────────────────────────
# Styles
# ──────────────────────────────────────────────────────────────────

_SPINBOX_STYLE: str = """
QSpinBox {
    background: #1e2236; color: #ccccdd;
    border: 1px solid #3a3f5c; border-radius: 4px;
    padding: 2px 6px;
}
QSpinBox::up-button, QSpinBox::down-button { background: #2b2f45; }
"""

_SLIDER_STYLE: str = """
QSlider::groove:horizontal {
    height: 6px; background: #2b2f45; border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #F4845F; width: 18px; height: 18px;
    margin: -6px 0; border-radius: 9px;
}
QSlider::sub-page:horizontal { background: #F4845F; border-radius: 3px; }
"""

_LINEEDIT_STYLE: str = """
QLineEdit {
    background: #1e2236; color: #ccccdd;
    border: 1px solid #3a3f5c; border-radius: 4px;
    padding: 2px 8px;
}
"""

_LABEL_STYLE: str = "color:#aaaacc; font-size:12px;"

_BTN_STYLE: str = """
QPushButton {
    background: #2b2f45; color: #ccccdd;
    border: 1px solid #3a3f5c; border-radius: 4px;
    padding: 3px 10px;
}
QPushButton:hover { background: #3a3f5c; }
QPushButton:pressed { background: #1e2236; }
"""

_GROUP_STYLE: str = """
QGroupBox {
    color: #aaaacc; border: 1px solid #2b2f45;
    border-radius: 6px; margin-top: 8px; font-size: 12px;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
"""


# ──────────────────────────────────────────────────────────────────
# Demo window
# ──────────────────────────────────────────────────────────────────

class DemoWindow(QWidget):
    """Demo with range/name controls, per-component colour pickers, and export."""

    # Human-readable labels for each colour key
    _COLOR_LABELS: dict = {
        "bg":         "背景色",
        "track":      "轨道弧",
        "fill":       "填充弧",
        "fill_ready": "填充弧(就绪)",
        "tick_major": "主刻度",
        "tick_minor": "副刻度",
        "text_value": "数值文字",
        "text_label": "标题文字",
    }

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Temperature Gauge — Demo")
        self.setStyleSheet(f"background:#151929; {_LABEL_STYLE}")

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 16, 16)
        root.setSpacing(10)

        # ── gauge ─────────────────────────────────────────────────
        self.gauge = TemperatureDashboard(min_val=0, max_val=60, value=23.15, name="老化温度")
        root.addWidget(self.gauge)

        # ── bottom controls (left: params, right: colours) ────────
        bottom = QHBoxLayout()
        bottom.setSpacing(10)
        bottom.addLayout(self._build_param_panel(), stretch=1)
        bottom.addLayout(self._build_color_panel(), stretch=1)
        root.addLayout(bottom)

        # ── export / import buttons ───────────────────────────────
        export_box = QGroupBox("配色文件", self)
        export_box.setStyleSheet(_GROUP_STYLE)
        el = QHBoxLayout(export_box)

        btn_load = QPushButton("加载 JSON 文件")
        btn_load.setStyleSheet(_BTN_STYLE)
        btn_load.clicked.connect(self._load_json)

        btn_json = QPushButton("保存为 JSON 文件")
        btn_json.setStyleSheet(_BTN_STYLE)
        btn_json.clicked.connect(self._export_json)

        btn_dict = QPushButton("复制为 Python 字典")
        btn_dict.setStyleSheet(_BTN_STYLE)
        btn_dict.clicked.connect(self._export_dict)

        el.addWidget(btn_load)
        el.addWidget(btn_json)
        el.addWidget(btn_dict)
        root.addWidget(export_box)

    # ── panel builders ────────────────────────────────────────────

    def _build_param_panel(self) -> QVBoxLayout:
        vl = QVBoxLayout()
        vl.setSpacing(8)

        # Value slider
        val_box = QGroupBox("当前温度值")
        val_box.setStyleSheet(_GROUP_STYLE)
        hl = QHBoxLayout(val_box)

        self.val_slider = QSlider(Qt.Horizontal)
        self.val_slider.setStyleSheet(_SLIDER_STYLE)
        self._sync_val_slider()
        self.val_slider.valueChanged.connect(self._on_val_changed)

        # noinspection PyProtectedMember
        self.val_label = QLabel(f"{int(self.gauge._value)} °C")
        self.val_label.setFixedWidth(58)
        self.val_label.setStyleSheet("color:#F4845F; font-weight:bold;")

        hl.addWidget(self.val_slider)
        hl.addWidget(self.val_label)
        vl.addWidget(val_box)

        # Range + name
        range_box = QGroupBox("显示范围与标题")
        range_box.setStyleSheet(_GROUP_STYLE)
        fl = QFormLayout(range_box)
        fl.setLabelAlignment(Qt.AlignRight)

        self.min_spin = QSpinBox()
        self.min_spin.setRange(-30, 329)
        # noinspection PyProtectedMember
        self.min_spin.setValue(int(self.gauge._min))
        self.min_spin.setSuffix(" °C")
        self.min_spin.setStyleSheet(_SPINBOX_STYLE)

        self.max_spin = QSpinBox()
        self.max_spin.setRange(-29, 330)
        # noinspection PyProtectedMember
        self.max_spin.setValue(int(self.gauge._max))
        self.max_spin.setSuffix(" °C")
        self.max_spin.setStyleSheet(_SPINBOX_STYLE)
        # noinspection PyProtectedMember
        self.name_edit = QLineEdit(self.gauge._name)
        self.name_edit.setStyleSheet(_LINEEDIT_STYLE)

        def _lbl(t: str) -> QLabel:
            w = QLabel(t)
            w.setStyleSheet(_LABEL_STYLE)
            return w

        fl.addRow(_lbl("最小值"), self.min_spin)
        fl.addRow(_lbl("最大值"), self.max_spin)
        fl.addRow(_lbl("标题"),   self.name_edit)
        vl.addWidget(range_box)

        self.min_spin.valueChanged.connect(self._on_min_changed)
        self.max_spin.valueChanged.connect(self._on_max_changed)
        self.name_edit.textChanged.connect(self.gauge.setName)

        # Ready / Reset 按钮
        btn_box = QGroupBox("状态控制")
        btn_box.setStyleSheet(_GROUP_STYLE)
        btn_hl = QHBoxLayout(btn_box)

        btn_ready = QPushButton("Ready (橙色)")
        btn_ready.setStyleSheet(_BTN_STYLE)
        btn_ready.clicked.connect(self.gauge.slotReady)

        btn_reset = QPushButton("Reset (恢复默认)")
        btn_reset.setStyleSheet(_BTN_STYLE)
        btn_reset.clicked.connect(self.gauge.slotReset)

        btn_hl.addWidget(btn_ready)
        btn_hl.addWidget(btn_reset)
        vl.addWidget(btn_box)

        return vl

    def _build_color_panel(self) -> QVBoxLayout:
        vl = QVBoxLayout()
        vl.setSpacing(0)

        color_box = QGroupBox("颜色配置")
        color_box.setStyleSheet(_GROUP_STYLE)
        fl = QFormLayout(color_box)
        fl.setLabelAlignment(Qt.AlignRight)
        fl.setSpacing(5)

        self._swatches: dict = {}

        for key, label in self._COLOR_LABELS.items():
            swatch = QLabel()
            swatch.setFixedSize(22, 22)
            swatch.setStyleSheet(
                f"background:{self.gauge.colors_as_hex()[key]};"
                "border:1px solid #555; border-radius:3px;"
            )

            btn = QPushButton("选择")
            btn.setFixedWidth(52)
            btn.setStyleSheet(_BTN_STYLE)
            btn.clicked.connect(lambda _=None, k=key: self._pick_color(k))

            row = QHBoxLayout()
            row.setSpacing(6)
            row.addWidget(swatch)
            row.addWidget(btn)

            self._swatches[key] = swatch
            row_lbl = QLabel(label)
            row_lbl.setStyleSheet(_LABEL_STYLE)
            fl.addRow(row_lbl, row)

        vl.addWidget(color_box)
        return vl

    # ── slots ─────────────────────────────────────────────────────

    def _sync_val_slider(self) -> None:
        # noinspection PyProtectedMember
        self.val_slider.setRange(int(self.gauge._min), int(self.gauge._max))
        # noinspection PyProtectedMember
        self.val_slider.setValue(int(self.gauge._value))

    def _on_val_changed(self, v: int) -> None:
        self.gauge.setValueInt(v)
        self.val_label.setText(f"{v} °C")

    def _on_min_changed(self, v: int) -> None:
        if v >= self.max_spin.value():
            self.min_spin.setValue(self.max_spin.value() - 1)
            return
        self.gauge.setMinValueInt(v)
        self._sync_val_slider()

    def _on_max_changed(self, v: int) -> None:
        if v <= self.min_spin.value():
            self.max_spin.setValue(self.min_spin.value() + 1)
            return
        self.gauge.setMaxValueInt(v)
        self._sync_val_slider()

    def _pick_color(self, key: str) -> None:
        # noinspection PyProtectedMember
        current = self.gauge._colors[key]
        color = QColorDialog.getColor(current, self, f"选择颜色 — {self._COLOR_LABELS[key]}")
        if not color.isValid():
            return
        self.gauge.set_color(key, color)
        hex_val = color.name().upper()
        self._swatches[key].setStyleSheet(
            f"background:{hex_val}; border:1px solid #555; border-radius:3px;"
        )

    # ── export / import ───────────────────────────────────────────

    def _load_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "加载配色 JSON", "", "JSON 文件 (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            self.setWindowTitle(f"加载失败：{e}")
            QTimer.singleShot(2000, lambda: self.setWindowTitle("Temperature Gauge — Demo"))
            return

        for key, hex_val in data.items():
            # noinspection PyProtectedMember
            if key not in self.gauge._colors:
                continue
            color = QColor(hex_val)
            if not color.isValid():
                continue
            self.gauge.set_color(key, color)
            if key in self._swatches:
                self._swatches[key].setStyleSheet(
                    f"background:{color.name().upper()};"
                    "border:1px solid #555; border-radius:3px;"
                )

    def _export_json(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "保存配色为 JSON", "gauge_colors.json", "JSON 文件 (*.json)"
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.gauge.colors_as_hex(), f, indent=4, ensure_ascii=False)

    def _export_dict(self) -> None:
        hex_dict = self.gauge.colors_as_hex()
        lines = ["{\n"]
        for k, v in hex_dict.items():
            lines.append(f'    "{k}": "{v}",\n')
        lines.append("}")
        QApplication.clipboard().setText("".join(lines))
        original = self.windowTitle()
        self.setWindowTitle("已复制到剪贴板！")
        QTimer.singleShot(1500, lambda: self.setWindowTitle(original))


# ──────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    win = DemoWindow()
    win.show()
    sys.exit(app.exec_())
