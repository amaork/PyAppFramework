# -*- coding: utf-8 -*-
import sys
from typing import Optional

from PySide2.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QFrame, QLineEdit, QLabel,
)
from PySide2.QtGui import QFont

from ..dashboard.cc.ctd import (
    ColorTheme, DEFAULT_THEME, CountdownDashboard, ThemeEditorDialog,
)


# ══════════════════════════════════════════════════════════════════════════════
# DemoWindow
# ══════════════════════════════════════════════════════════════════════════════

class DemoWindow(QWidget):
    """Host window — delegates all timer logic to CountdownDashboard."""

    DURATIONS = {
        "30 sec":  30,  "1 min":  60,  "5 min":  300,
        "10 min":  600, "30 min": 1800, "1 hour": 3600, "2 hours": 7200,
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme: Optional[ColorTheme] = None
        self.setWindowTitle("Countdown Dashboard")
        self.setMinimumSize(480, 360)
        self.resize(640, 420)
        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._widget = CountdownDashboard()
        self._widget.signalStateChanged.connect(self._on_state_changed)
        root.addWidget(self._widget)

        sep = QFrame()
        sep.setFixedHeight(1)
        root.addWidget(sep)

        panel = QWidget()
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(24, 12, 24, 16)
        pl.setSpacing(8)

        # Title row
        tr = QHBoxLayout()
        tr.setSpacing(10)
        tr.addWidget(QLabel("TITLE"))
        self._title_edit = QLineEdit("Countdown Timer")
        self._title_edit.setFont(QFont("Arial", 9))
        self._title_edit.setFixedHeight(30)
        self._title_edit.textChanged.connect(self._widget.setTitle)
        tr.addWidget(self._title_edit)
        pl.addLayout(tr)

        # Duration / control row
        cr = QHBoxLayout()
        cr.setSpacing(8)

        cr.addWidget(QLabel("DURATION"))
        self._dur_combo = QComboBox()
        self._dur_combo.setFont(QFont("Arial", 9))
        self._dur_combo.setFixedHeight(32)
        for k in self.DURATIONS:
            self._dur_combo.addItem(k)
        self._dur_combo.setCurrentText("1 hour")
        self._dur_combo.currentTextChanged.connect(self._on_duration)

        self._start_btn = self._make_btn("▶  START")
        self._pause_btn = self._make_btn("⏸  PAUSE")
        self._pause_btn.setEnabled(False)
        reset_btn = self._make_btn("↺  RESET")

        self._start_btn.clicked.connect(self._widget.start)
        self._pause_btn.clicked.connect(self._widget.pause)
        reset_btn.clicked.connect(self._widget.reset)

        theme_btn = QPushButton("🎨  Theme")
        theme_btn.setFont(QFont("Arial", 9))
        theme_btn.setFixedHeight(32)
        theme_btn.clicked.connect(self._open_theme_editor)

        cr.addWidget(self._dur_combo)
        cr.addStretch()
        cr.addWidget(self._start_btn)
        cr.addWidget(self._pause_btn)
        cr.addWidget(reset_btn)
        cr.addWidget(theme_btn)
        pl.addLayout(cr)
        root.addWidget(panel)

    @staticmethod
    def _make_btn(text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFont(QFont("Arial", 9, QFont.Bold))
        btn.setFixedHeight(32)
        return btn

    # ── State sync ────────────────────────────────────────────────────────

    def _on_state_changed(self, state: str):
        if state in ("ready", "finished"):
            self._start_btn.setEnabled(True)
            self._pause_btn.setEnabled(False)
            self._pause_btn.setText("⏸  PAUSE")
        elif state == "running":
            self._start_btn.setEnabled(False)
            self._pause_btn.setEnabled(True)
            self._pause_btn.setText("⏸  PAUSE")
        elif state == "paused":
            self._start_btn.setEnabled(False)
            self._pause_btn.setEnabled(True)
            self._pause_btn.setText("▶  RESUME")

    # ── Duration ──────────────────────────────────────────────────────────

    def _on_duration(self, text: str):
        seconds = self.DURATIONS.get(text, 3600)
        self._widget.setTime(self._title_edit.text(), seconds)

    # ── Theme editor ──────────────────────────────────────────────────────

    def _open_theme_editor(self):
        dlg = ThemeEditorDialog(self._theme or DEFAULT_THEME, self)
        dlg.signalThemeApplied.connect(self._apply_theme)
        dlg.exec_()

    def _apply_theme(self, theme: ColorTheme):
        self._theme = theme
        self._widget.applyTheme(theme)


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = DemoWindow()
    win.show()
    sys.exit(app.exec_())
