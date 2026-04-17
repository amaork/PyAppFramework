# -*- coding: utf-8 -*-
"""
ctd.py — Countdown Dashboard widgets
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Architecture
  CountdownDashboard  Pure display widget (title → time → status → bar)
  ThemeEditorDialog   Modal dialog: preset selector, per-key color pickers,
                      export to JSON file / copy dict, import from JSON file

ColorTheme keys
  bg / bg_track
  bar_high / bar_mid / bar_low
  time_high / time_mid / time_low
  text_title / text_status
  dot_run / dot_pause / dot_finish
"""

import math
import json
import copy
from pathlib import Path
from typing import Dict, Optional
from PySide2.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QSizePolicy, QFrame,
    QScrollArea, QFileDialog, QMessageBox, QColorDialog, QApplication
)
from PySide2.QtCore import Qt, QTimer, Signal
from PySide2.QtGui import (
    QPainter, QColor, QFont, QBrush,
    QLinearGradient, QRadialGradient
)

__all__ = [
    'ColorTheme', 'THEME_KEY_LABELS',
    'PRESET_DEFAULT', 'PRESET_OCEAN', 'PRESET_SLATE', 'PRESET_MONO',
    'BUILTIN_PRESETS', 'DEFAULT_THEME',
    'MasterBar', 'StatusDot', 'CountdownDashboard', 'ThemeEditorDialog',
    'get_theme_color_by_key',
]

# ══════════════════════════════════════════════════════════════════════════════
# Color-theme types & helpers
# ══════════════════════════════════════════════════════════════════════════════

ColorTheme = Dict[str, str]

# Human-readable label for each theme key (used in ThemeEditorDialog)
THEME_KEY_LABELS: Dict[str, str] = {
    "bg":            "Background",
    "bg_track":      "Progress track",
    "bar_high":      "Bar — high  (> 50 %)",
    "bar_mid":       "Bar — mid   (20–50 %)",
    "bar_low":       "Bar — low   (< 20 %)",
    "time_high":     "Digits — high",
    "time_mid":      "Digits — mid",
    "time_low":      "Digits — low",
    "text_title":    "Title text",
    "text_status":   "Status / pct text",
    "dot_run":       "Dot — running",
    "dot_pause":     "Dot — paused",
    "dot_finish":    "Dot — finished",
}

# ── Built-in presets ──────────────────────────────────────────────────────────

PRESET_DEFAULT: ColorTheme = {
    "bg":            "#151929",   # dark navy
    "bg_track":      "#FFFFFF18",
    "bar_high":      "#2CB887",   # emerald green
    "bar_mid":       "#F0A030",   # warm amber
    "bar_low":       "#E84545",   # clear red
    "time_high":     "#F0A030",   # amber — prominent, distinct from bar green
    "time_mid":      "#F07850",   # orange-red transition
    "time_low":      "#E84545",   # red — alarm
    "text_title":    "#D0D0E8",   # cool light grey-blue
    "text_status":   "#F07850",   # warm coral, echoes mid→low transition
    "dot_run":       "#2CB887",   # matches bar_high
    "dot_pause":     "#F0A030",   # amber
    "dot_finish":    "#E84545",   # matches bar_low
}

PRESET_OCEAN: ColorTheme = {
    "bg":            "#0A1628",   # deep navy
    "bg_track":      "#00000020",
    "bar_high":      "#007A6E",   # deep teal
    "bar_mid":       "#1558A8",   # deep blue
    "bar_low":       "#C02030",   # deep red
    "time_high":     "#007A6E",   # aligned with bar_high
    "time_mid":      "#1558A8",   # aligned with bar_mid
    "time_low":      "#C02030",   # aligned with bar_low
    "text_title":    "#A8C8E8",   # light blue-grey
    "text_status":   "#4EC9C0",   # bright cyan-teal
    "dot_run":       "#007A6E",   # teal
    "dot_pause":     "#1558A8",   # blue
    "dot_finish":    "#C02030",   # red
}

PRESET_SLATE: ColorTheme = {
    "bg":            "#EFF1F5",   # Catppuccin Latte base
    "bg_track":      "#BCC0CC",   # Catppuccin Latte surface1
    "bar_high":      "#40A02B",   # Catppuccin Latte green
    "bar_mid":       "#DF8E1D",   # Catppuccin Latte yellow
    "bar_low":       "#D20F39",   # Catppuccin Latte red
    "time_high":     "#40A02B",   # aligned with bar_high
    "time_mid":      "#DF8E1D",   # aligned with bar_mid
    "time_low":      "#D20F39",   # aligned with bar_low
    "text_title":    "#4C4F69",   # Catppuccin Latte text
    "text_status":   "#1E66F5",   # Catppuccin Latte blue
    "dot_run":       "#40A02B",   # green
    "dot_pause":     "#DF8E1D",   # yellow
    "dot_finish":    "#D20F39",   # red
}

PRESET_MONO: ColorTheme = {
    "bg":            "#F5F5F5",   # near white
    "bg_track":      "#BBBBBB",   # visible grey track on light bg
    "bar_high":      "#808080",   # medium grey
    "bar_mid":       "#505050",   # dark grey
    "bar_low":       "#282828",   # near black
    "time_high":     "#404040",   # dark, readable
    "time_mid":      "#282828",   # darker
    "time_low":      "#101010",   # near black — maximum attention
    "text_title":    "#1C1C1C",   # near black
    "text_status":   "#505050",   # dark grey
    "dot_run":       "#808080",   # medium
    "dot_pause":     "#505050",   # dark
    "dot_finish":    "#282828",   # near black
}

BUILTIN_PRESETS: Dict[str, ColorTheme] = {
    "Default (Amber)": PRESET_DEFAULT,
    "Ocean":           PRESET_OCEAN,
    "Catppuccin Latte": PRESET_SLATE,
    "Monochrome":      PRESET_MONO,
}

DEFAULT_THEME = PRESET_DEFAULT


def get_theme_color_by_key(theme: ColorTheme, key: str) -> QColor:
    """Parse a theme hex value (6-char or 8-char RRGGBBAA) into QColor."""
    raw = theme[key].lstrip("#")
    if len(raw) == 8:
        return QColor(int(raw[0:2], 16), int(raw[2:4], 16),
                      int(raw[4:6], 16), int(raw[6:8], 16))
    return QColor(f"#{raw}")


# noinspection SpellCheckingInspection
def _qcolor_to_hex(c: QColor) -> str:
    if c.alpha() < 255:
        return f"#{c.red():02X}{c.green():02X}{c.blue():02X}{c.alpha():02X}"
    return c.name().upper()


# ══════════════════════════════════════════════════════════════════════════════
# MasterBar
# ══════════════════════════════════════════════════════════════════════════════

class MasterBar(QWidget):
    def __init__(self, theme: ColorTheme, parent=None):
        super().__init__(parent)
        self._theme = theme
        self._target = 1.0
        self._current = 1.0
        self.setFixedHeight(14)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._anim = QTimer(self)
        self._anim.setInterval(16)
        self._anim.timeout.connect(self._step)

    def applyTheme(self, theme: ColorTheme):
        self._theme = theme
        self.update()

    def setValue(self, v: float):
        self._target = max(0.0, min(1.0, v))
        self._anim.start()

    def _step(self):
        d = self._target - self._current
        if abs(d) < 0.0008:
            self._current = self._target
            self._anim.stop()
        else:
            self._current += d * 0.14
        self.update()

    def _bar_color(self, pct: float) -> QColor:
        if pct > 0.5:
            return get_theme_color_by_key(self._theme, "bar_high")
        if pct > 0.2:
            return get_theme_color_by_key(self._theme, "bar_mid")
        return get_theme_color_by_key(self._theme, "bar_low")

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        r = h / 2
        p.setPen(Qt.NoPen)
        p.setBrush(get_theme_color_by_key(self._theme, "bg_track"))
        p.drawRoundedRect(0, 0, w, h, r, r)
        fw = int(w * self._current)
        if fw > 2:
            c = self._bar_color(self._current)
            g = QLinearGradient(0, 0, fw, 0)
            g.setColorAt(0, c.darker(140))
            g.setColorAt(1, c)
            p.setBrush(QBrush(g))
            p.drawRoundedRect(0, 0, fw, h, r, r)
            glow = QRadialGradient(fw, h/2, 11)
            glow.setColorAt(0, QColor(c.red(), c.green(), c.blue(), 200))
            glow.setColorAt(1, QColor(c.red(), c.green(), c.blue(), 0))
            p.setBrush(QBrush(glow))
            p.drawEllipse(fw-11, int(h/2)-11, 22, 22)
        p.end()


# ══════════════════════════════════════════════════════════════════════════════
# StatusDot
# ══════════════════════════════════════════════════════════════════════════════

class StatusDot(QWidget):
    def __init__(self, theme: ColorTheme, parent=None):
        super().__init__(parent)
        self._theme = theme
        self.setFixedSize(10, 10)
        self._color = get_theme_color_by_key(theme, "dot_run")
        self._phase = 0.0
        self._pulse = QTimer(self)
        self._pulse.setInterval(40)
        self._pulse.timeout.connect(self._tick)
        self._pulse.start()

    def applyTheme(self, theme: ColorTheme):
        self._theme = theme
        self.update()

    _STATE_MAP = {
        "running":  ("dot_run",    True),
        "paused":   ("dot_pause",  False),
        "finished": ("dot_finish", False),
        "ready":    ("dot_run",    False),
    }

    def setState(self, state: str):
        key, pulse = self._STATE_MAP.get(state, ("dot_run", False))
        self._color = get_theme_color_by_key(self._theme, key)
        if pulse:
            self._pulse.start()
        else:
            self._pulse.stop()
        self._phase = 0.0
        self.update()

    def _tick(self):
        self._phase = (self._phase + 0.09) % (2 * math.pi)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        alpha = max(0, min(255, int(110 + 145 * math.sin(self._phase)))) if self._pulse.isActive() else 255
        c = QColor(self._color)
        c.setAlpha(alpha)
        p.setPen(Qt.NoPen)
        p.setBrush(c)
        p.drawEllipse(1, 1, 8, 8)
        p.end()


# ══════════════════════════════════════════════════════════════════════════════
# CountdownDashboard
# ══════════════════════════════════════════════════════════════════════════════

class CountdownDashboard(QWidget):
    """
    Countdown display widget with built-in timer.

    Public API
    ──────────
      setTime(title, seconds)   configure title and total duration, reset to ready
      setTitle(text)            update title label only (no reset)
      start()                    start or restart the countdown
      pause()                    toggle pause / resume
      reset()                    stop and reset to ready state
      applyTheme(ColorTheme)    hot-swap color theme

    Signals
    ───────
      signalStateChanged(str)   emits "ready" | "running" | "paused" | "finished"
      signalFinished()           emits when countdown reaches zero
    """

    signalStateChanged = Signal(str)
    signalFinished = Signal()

    _STATE_LABELS = {
        "ready":    "READY",
        "running":  "RUNNING",
        "paused":   "PAUSED",
        "finished": "FINISHED",
    }

    def __init__(self, theme: Optional[ColorTheme] = None, title_align_center: bool = False, parent=None):
        super().__init__(parent)
        self._theme = {**DEFAULT_THEME, **(theme or {})}
        self._title_align_center = title_align_center
        self._total = 3600
        self._remaining = 3600
        self._state = "ready"
        self._ticker = QTimer(self)
        self._ticker.setInterval(1000)
        self._ticker.timeout.connect(self._tick)
        self.setMinimumWidth(280)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._build_ui()
        self._refresh_display()

    # ── Public API ────────────────────────────────────────────────────────

    def setTime(self, title: str, seconds: int):
        """Configure title and total duration, then reset to ready state."""
        self._ticker.stop()
        self._total = max(1, seconds)
        self._remaining = self._total
        self._state = "ready"
        self.ui_title_label.setText(title)
        self._refresh_display()
        self.signalStateChanged.emit("ready")

    def setTitle(self, text: str):
        """Update the title label without resetting the countdown."""
        self.ui_title_label.setText(text)

    def start(self):
        """Start the countdown (from ready or finished state)."""
        if self._state in ("ready", "finished"):
            self._state = "running"
            self._ticker.start()
            self._refresh_display()
            self.signalStateChanged.emit("running")

    def pause(self):
        """Toggle between paused and running."""
        if self._state == "running":
            self._state = "paused"
            self._ticker.stop()
            self._refresh_display()
            self.signalStateChanged.emit("paused")
        elif self._state == "paused":
            self._state = "running"
            self._ticker.start()
            self._refresh_display()
            self.signalStateChanged.emit("running")

    def finish(self):
        """Forcefully switch to finished state from outside."""
        self._ticker.stop()
        self._remaining = 0
        self._state = "finished"
        self._refresh_display()
        self.signalFinished.emit()
        self.signalStateChanged.emit("finished")

    def reload(self):
        """Reset countdown and start immediately (reset + start)."""
        self._ticker.stop()
        self._remaining = self._total
        self._state = "running"
        self._ticker.start()
        self._refresh_display()
        self.signalStateChanged.emit("running")

    def reset(self):
        """Stop and reset to ready state."""
        self._ticker.stop()
        self._remaining = self._total
        self._state = "ready"
        self._refresh_display()
        self.signalStateChanged.emit("ready")

    # ── Theme hot-swap ────────────────────────────────────────────────────

    def applyTheme(self, theme: ColorTheme):
        self._theme = theme
        t = theme
        self.ui_title_label.setStyleSheet(
            f"color: {get_theme_color_by_key(t, 'text_title').name()}; background: transparent;"
        )
        self.ui_status_text.setStyleSheet(
            f"color: {get_theme_color_by_key(t, 'text_status').name()}; letter-spacing: 2px; background: transparent;"
        )
        self.ui_pct_label.setStyleSheet(
            f"color: {get_theme_color_by_key(t, 'text_status').name()}; background: transparent;"
        )
        self.ui_master_bar.applyTheme(t)
        self.ui_status_dot.applyTheme(t)
        self._refresh_display()
        self.update()

    # ── Timer ─────────────────────────────────────────────────────────────

    def _tick(self):
        self._remaining -= 1
        if self._remaining <= 0:
            self._remaining = 0
            self._state = "finished"
            self._ticker.stop()
            self.signalFinished.emit()
            self.signalStateChanged.emit("finished")
        self._refresh_display()

    # ── Internal display refresh ──────────────────────────────────────────

    def _refresh_display(self):
        remaining, total = self._remaining, self._total
        pct = remaining / total if total > 0 else 0.0
        h = remaining // 3600
        m = (remaining % 3600) // 60
        s = remaining % 60
        self.ui_big_time.setText(
            f"{h:02d}:{m:02d}:{s:02d}" if total > 3599 else f"{m:02d}:{s:02d}"
        )
        if pct > 0.5:
            col = get_theme_color_by_key(self._theme, "time_high").name()
        elif pct > 0.2:
            col = get_theme_color_by_key(self._theme, "time_mid").name()
        else:
            col = get_theme_color_by_key(self._theme, "time_low").name()
        self.ui_big_time.setStyleSheet(
            f"color: {col}; letter-spacing: -2px; background: transparent;"
        )
        self.ui_master_bar.setValue(pct)
        self.ui_pct_label.setText(f"{round(pct * 100)}%")
        self.ui_status_text.setText(self._STATE_LABELS.get(self._state, self._state.upper()))
        self.ui_status_dot.setState(self._state)

    # ── UI ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        t = self._theme
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 0, 28, 0)
        root.setSpacing(0)

        # 上部拉伸因子，使控件居中
        root.addStretch(1)

        self.ui_title_label = QLabel(self.tr("Countdown Timer"))
        self.ui_title_label.setAlignment(Qt.AlignCenter if self._title_align_center else Qt.AlignLeft)
        self.ui_title_label.setStyleSheet(
            f"color: {get_theme_color_by_key(t, 'text_title').name()}; background: transparent;"
        )
        root.addWidget(self.ui_title_label)
        root.addSpacing(1)

        self.ui_big_time = QLabel("01:00:00")
        self.ui_big_time.setStyleSheet(
            f"color: {get_theme_color_by_key(t, 'time_high').name()}; letter-spacing: -2px; background: transparent;"
        )
        self.ui_big_time.setAlignment(Qt.AlignLeft)
        root.addWidget(self.ui_big_time)
        root.addSpacing(1)

        srow = QHBoxLayout()
        srow.setSpacing(7)
        self.ui_status_dot = StatusDot(t)
        self.ui_status_text = QLabel("READY")
        self.ui_status_text.setStyleSheet(
            f"color: {get_theme_color_by_key(t, 'text_status').name()}; letter-spacing: 2px; background: transparent;"
        )
        self.ui_pct_label = QLabel("100%")
        self.ui_pct_label.setStyleSheet(
            f"color: {get_theme_color_by_key(t, 'text_status').name()}; background: transparent;"
        )
        srow.addWidget(self.ui_status_dot)
        srow.addWidget(self.ui_status_text)
        srow.addStretch()
        srow.addWidget(self.ui_pct_label)
        root.addLayout(srow)
        root.addSpacing(4)

        self.ui_master_bar = MasterBar(t)
        root.addWidget(self.ui_master_bar)

        # 下部拉伸因子，使控件居中
        root.addStretch(1)

        # 初始化字体大小
        self._refresh_layout()

    def resizeEvent(self, event):
        """窗口大小变化时重新计算字体"""
        super().resizeEvent(event)
        self._refresh_layout()

    def _refresh_layout(self):
        """根据控件大小动态调整字体"""
        w, h = self.width(), self.height()

        # 基于高度计算字体大小（设置最小/最大限制）
        title_size = max(12, min(16, h // 18))
        time_size = max(28, min(54, int(h * 0.35)))
        status_size = max(8, min(10, h // 30))
        pct_size = max(9, min(11, h // 28))

        self.ui_title_label.setFont(QFont("Arial", title_size, QFont.Bold))
        self.ui_big_time.setFont(QFont("Arial", time_size, QFont.Bold))
        self.ui_status_text.setFont(QFont("Arial", status_size))
        self.ui_pct_label.setFont(QFont("Arial", pct_size, QFont.Bold))

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), get_theme_color_by_key(self._theme, "bg"))
        p.end()


# ══════════════════════════════════════════════════════════════════════════════
# ThemeEditorDialog
# ══════════════════════════════════════════════════════════════════════════════

class ThemeEditorDialog(QDialog):
    """
    Modal theme editor.
      • Preset selector  — instantly applies a built-in theme
      • Color grid       — one color-picker button per theme key
      • Export JSON      — save to file
      • Copy as dict     — copy Python dict literal to clipboard
      • Import JSON      — load from file
    Emits signalThemeApplied(ColorTheme) when a color or preset changes.
    """

    signalThemeApplied = Signal(object)   # emits a ColorTheme dict

    def __init__(self, current_theme: ColorTheme, parent=None):
        super().__init__(parent)
        self._theme = copy.deepcopy(current_theme)
        self.setWindowTitle("Theme Editor")
        self.setMinimumWidth(520)
        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(12)

        # ── Preset row ────────────────────────────────────────────────────
        preset_row = QHBoxLayout()
        preset_row.setSpacing(10)
        lbl = QLabel("PRESET")
        lbl.setFont(QFont("Arial", 8, QFont.Bold))
        self._preset_combo = QComboBox()
        self._preset_combo.setFont(QFont("Arial", 9))
        self._preset_combo.setFixedHeight(32)
        self._preset_combo.addItem("— Custom —")
        for name in BUILTIN_PRESETS:
            self._preset_combo.addItem(name)
        self._preset_combo.currentIndexChanged.connect(self._on_preset)
        preset_row.addWidget(lbl)
        preset_row.addWidget(self._preset_combo, 1)
        root.addLayout(preset_row)

        # ── Color grid ────────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)

        self._color_btns: Dict[str, QPushButton] = {}
        for row_i, (key, label) in enumerate(THEME_KEY_LABELS.items()):
            lbl2 = QLabel(label)
            lbl2.setFont(QFont("Arial", 9))
            lbl2.setFixedWidth(170)
            btn = QPushButton()
            btn.setFixedSize(80, 26)
            btn.setFont(QFont("Arial", 8))
            btn.setCursor(Qt.PointingHandCursor)
            self._refresh_btn(btn, key)
            btn.clicked.connect(lambda checked=False, k=key: self._pick_color(k))
            self._color_btns[key] = btn
            grid.addWidget(lbl2, row_i, 0)
            grid.addWidget(btn,  row_i, 1)

        scroll.setWidget(grid_widget)
        root.addWidget(scroll, 1)

        # ── Separator ─────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFixedHeight(1)
        root.addWidget(sep)

        # ── Bottom buttons ────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        export_btn = QPushButton("💾  Export JSON")
        export_btn.setFont(QFont("Arial", 9))
        export_btn.setFixedHeight(32)
        export_btn.clicked.connect(self._export_json)

        copy_btn = QPushButton("📋  Copy as dict")
        copy_btn.setFont(QFont("Arial", 9))
        copy_btn.setFixedHeight(32)
        copy_btn.clicked.connect(self._copy_dict)

        import_btn = QPushButton("📂  Import JSON")
        import_btn.setFont(QFont("Arial", 9))
        import_btn.setFixedHeight(32)
        import_btn.clicked.connect(self._import_json)

        close_btn = QPushButton("✕  Close")
        close_btn.setFont(QFont("Arial", 9))
        close_btn.setFixedHeight(32)
        close_btn.clicked.connect(self.accept)

        btn_row.addWidget(export_btn)
        btn_row.addWidget(copy_btn)
        btn_row.addWidget(import_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

    # ── Color picking ─────────────────────────────────────────────────────

    def _pick_color(self, key: str):
        initial = get_theme_color_by_key(self._theme, key)
        dlg = QColorDialog(initial, self)
        dlg.setOption(QColorDialog.ShowAlphaChannel, True)
        if dlg.exec_() == QColorDialog.Accepted:
            chosen = dlg.selectedColor()
            self._theme[key] = _qcolor_to_hex(chosen)
            self._refresh_btn(self._color_btns[key], key)
            self._preset_combo.blockSignals(True)
            self._preset_combo.setCurrentIndex(0)
            self._preset_combo.blockSignals(False)
            self.signalThemeApplied.emit(copy.deepcopy(self._theme))

    def _refresh_btn(self, btn: QPushButton, key: str):
        c = get_theme_color_by_key(self._theme, key)
        hex_str = _qcolor_to_hex(c)
        luma = 0.299*c.red() + 0.587*c.green() + 0.114*c.blue()
        txt = "#111" if luma > 128 else "#EEE"
        btn.setText(hex_str[:7])
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {c.name()};
                color: {txt};
                border: 1px solid rgba(255,255,255,40);
                border-radius: 4px;
            }}
            QPushButton:hover {{ border: 1px solid rgba(255,255,255,90); }}
        """)

    # ── Preset ────────────────────────────────────────────────────────────

    def _on_preset(self, idx: int):
        if idx == 0:
            return
        name = self._preset_combo.currentText()
        preset = BUILTIN_PRESETS.get(name)
        if preset:
            self._theme = copy.deepcopy(preset)
            for key, btn in self._color_btns.items():
                self._refresh_btn(btn, key)
            self.signalThemeApplied.emit(copy.deepcopy(self._theme))

    # ── Export / import ───────────────────────────────────────────────────

    def _export_json(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export theme", "my_theme.json", "JSON files (*.json)"
        )
        if path:
            try:
                Path(path).write_text(
                    json.dumps(self._theme, indent=2), encoding="utf-8"
                )
                QMessageBox.information(self, "Exported", f"Theme saved to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _copy_dict(self):
        lines = ["theme = {"]
        for k, v in self._theme.items():
            lines.append(f'    "{k}": "{v}",')
        lines.append("}")
        QApplication.clipboard().setText("\n".join(lines))
        QMessageBox.information(self, "Copied", "Theme dict copied to clipboard.")

    def _import_json(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import theme", "", "JSON files (*.json)"
        )
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            missing = [k for k in DEFAULT_THEME if k not in data]
            if missing:
                QMessageBox.warning(
                    self, "Partial theme",
                    f"Missing keys will use defaults:\n{', '.join(missing)}"
                )
            self._theme = {**DEFAULT_THEME, **data}
            for key, btn in self._color_btns.items():
                self._refresh_btn(btn, key)
            self._preset_combo.blockSignals(True)
            self._preset_combo.setCurrentIndex(0)
            self._preset_combo.blockSignals(False)
            self.signalThemeApplied.emit(copy.deepcopy(self._theme))
        except Exception as e:
            QMessageBox.critical(self, "Import failed", str(e))
