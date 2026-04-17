# -*- coding: utf-8 -*-
"""
temperature_gauge.py
====================
Semicircular temperature gauge widget built with PySide2.

Arc geometry
------------
- Starts at 210 ° (Qt-CCW from East = lower-left).
- Sweeps 240 ° clockwise to the lower-right.
- Fill and tick scale share the same coordinate system [_min, _max].

Public API  (TemperatureGauge)
------------------------------
Slots
    setRV(float)            set current reading
    setRVInt(int)           int overload for QSlider
    setMinValue(float)      set lower range bound
    setMinValueInt(int)     int overload for QSpinBox
    setMaxValue(float)      set upper range bound
    setMaxValueInt(int)     int overload for QSpinBox
    setRange(float, float)  set both bounds at once
    setName(str)            set the label below the gauge
    setSV(float, float)     set the setpoint value and optional diff threshold
    setSVInt(int)           int overload for setSV
    setDiff(float)          set diff threshold for auto ready/reset
    slotReady()             set fill color to orange (ready state)
    slotReset()             reset fill color to default

Allowed range: GLOBAL_MIN (−30) … GLOBAL_MAX (330)
"""

import math
from typing import List, Optional, Tuple

from PySide2.QtCore import Qt, QPointF, QRectF
from PySide2.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPen,
)
from PySide2.QtWidgets import QWidget, QSizePolicy

__all__ = ['TemperatureDashboard', 'DEFAULT_COLORS']

# ──────────────────────────────────────────────────────────────────
# Default colour palette
# ──────────────────────────────────────────────────────────────────

DEFAULT_COLORS: dict = {
    "bg":         "#151929",   # widget background
    "track":      "#2b2f45",   # full arc track
    "fill":       "#F4845F",   # value fill arc + gradient rule
    "fill_ready": "#FFA500",   # value fill arc when ready (orange)
    "tick_major": "#ccccdd",   # major tick marks and labels
    "tick_minor": "#555870",   # minor tick marks
    "text_value": "#F4845F",   # centre value readout
    "text_label": "#ccccdd",   # name label below arc
}


# ──────────────────────────────────────────────────────────────────
# TemperatureGauge
# ──────────────────────────────────────────────────────────────────

class TemperatureDashboard(QWidget):
    """Semicircular temperature gauge with dynamic range and name label."""

    GLOBAL_MIN: float = -30.0
    GLOBAL_MAX: float = 330.0

    # Arc geometry — Qt-CCW degree convention (0 ° = East, CCW positive).
    # A negative spanAngle in drawArc() produces a clockwise sweep.
    _QT_START: int = 210   # arc start angle (lower-left)
    _SWEEP: int = 240       # total clockwise sweep in degrees

    def __init__(
        self,
        min_val: float = 0.0,
        max_val: float = 60.0,
        value: float = 23.15,
        sv: float = 25.0,
        diff: float = 0.0,
        unit: str = "°C",
        name: str = "温度",
        colors: Optional[dict] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._min: float = float(min_val)
        self._max: float = float(max_val)
        self._rv: float = float(value)
        self._sv: float = float(sv)
        self._diff: float = float(diff)
        self._unit: str = unit
        self._name: str = name

        palette = {**DEFAULT_COLORS, **(colors or {})}
        self._colors: dict = {k: QColor(v) for k, v in palette.items()}
        self._default_fill: QColor = self._colors["fill"]  # 保存默认填充颜色

        self.setMinimumSize(200, 160)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._update_fill_state()

    # ── public slots ──────────────────────────────────────────────

    def setRV(self, v: float) -> None:
        """Set the current temperature reading (clamped to [min, max])."""
        self._rv = max(self._min, min(self._max, float(v)))
        self._update_fill_state()
        self.update()

    def setRVInt(self, v: int) -> None:
        """int overload of setRV — convenient for QSlider.valueChanged."""
        self.setRV(float(v))

    def setMinValue(self, v: float) -> None:
        """Set the lower display bound (clamped to GLOBAL_MIN, must be < max)."""
        v = max(self.GLOBAL_MIN, float(v))
        if v >= self._max:
            return
        self._min = v
        self._rv = max(self._min, self._rv)
        self._update_fill_state()
        self.update()

    def setMinValueInt(self, v: int) -> None:
        """int overload of setMinValue."""
        self.setMinValue(float(v))

    def setMaxValue(self, v: float) -> None:
        """Set the upper display bound (clamped to GLOBAL_MAX, must be > min)."""
        v = min(self.GLOBAL_MAX, float(v))
        if v <= self._min:
            return
        self._max = v
        self._rv = min(self._max, self._rv)
        self._update_fill_state()
        self.update()

    def setMaxValueInt(self, v: int) -> None:
        """int overload of setMaxValue."""
        self.setMaxValue(float(v))

    def setRange(self, min_val: float, max_val: float) -> None:
        """Set both lower and upper bounds in one call."""
        min_val = max(self.GLOBAL_MIN, float(min_val))
        max_val = min(self.GLOBAL_MAX, float(max_val))
        if min_val >= max_val:
            return
        self._min = min_val
        self._max = max_val
        self._rv = max(self._min, min(self._max, self._rv))
        self._update_fill_state()
        self.update()

    def setName(self, name: str) -> None:
        """Set the descriptive label displayed below the gauge."""
        self._name = name
        self.update()

    def slotReady(self) -> None:
        """Set fill color to orange (ready state)."""
        self._colors["fill"] = self._colors.get("fill_ready", QColor("#FFA500"))
        self.update()

    def slotReset(self) -> None:
        """Reset fill color to default."""
        self._colors["fill"] = self._default_fill
        self.update()

    def setSV(self, v: float, diff: Optional[float] = None) -> None:
        """Set the setpoint value and optional diff threshold."""
        self._sv = float(v)
        if diff is not None:
            self._diff = float(diff)
        self._update_fill_state()
        self.update()

    def setSVInt(self, v: int) -> None:
        """int overload of setSV."""
        self.setSV(float(v))

    def setDiff(self, diff: float) -> None:
        """Set the diff threshold for auto ready/reset."""
        self._diff = float(diff)
        self._update_fill_state()
        self.update()

    def _update_fill_state(self) -> None:
        """Auto switch fill color based on |rv - sv| <= diff."""
        if abs(self._rv - self._sv) <= self._diff:
            self.slotReady()
        else:
            self.slotReset()

    def getRV(self) -> float:
        """Return the current temperature reading."""
        return self._rv

    def getMinValue(self) -> float:
        """Return the lower display bound."""
        return self._min

    def getMaxValue(self) -> float:
        """Return the upper display bound."""
        return self._max

    def getName(self) -> str:
        """Return the descriptive label."""
        return self._name

    def getColor(self, key: str) -> QColor:
        """Return a colour by key, or black if key is missing."""
        return self._colors.get(key, QColor(Qt.black))

    def getSV(self) -> float:
        """Return the setpoint value."""
        return self._sv

    def getDiff(self) -> float:
        """Return the diff threshold."""
        return self._diff

    # ── colour API ────────────────────────────────────────────────

    def colors_as_hex(self) -> dict:
        """Return current colours as a plain {key: '#RRGGBB'} dict."""
        return {k: v.name().upper() for k, v in self._colors.items()}

    def set_color(self, key: str, color: QColor) -> None:
        """Update a single colour entry and repaint."""
        self._colors[key] = QColor(color)
        self.update()

    # ── geometry helpers ──────────────────────────────────────────

    def _layout(self) -> Tuple[float, float, float]:
        """Return (cx, cy, radius) for the arc, centred in the widget."""
        w, h = self.width(), self.height()
        radius = min(w, int(h * 1.15)) * 0.42
        return w / 2, h * 0.58, radius

    def _arc_range(self) -> Tuple[float, float]:
        """
        Return (arc_min, arc_max) shared by fill and tick rendering.
        Both equal the exact _min / _max so that value == _min always
        yields t = 0 with no spurious fill segment.
        """
        return self._min, self._max

    # ── paint dispatch ────────────────────────────────────────────

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), self._colors["bg"])

        cx, cy, R = self._layout()
        self._draw_track(p, cx, cy, R)
        self._draw_fill(p, cx, cy, R)
        self._draw_ticks(p, cx, cy, R)
        self._draw_rv_text(p, cx, cy, R)
        self._draw_name_label(p, cx, cy, R)
        p.end()

    # ── draw helpers ──────────────────────────────────────────────

    def _draw_track(self, p: QPainter, cx: float, cy: float, R: float) -> None:
        """Draw the full grey background arc."""
        p.setPen(QPen(self._colors["track"], R * 0.12, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        p.drawArc(
            QRectF(cx - R, cy - R, R * 2, R * 2),
            self._QT_START * 16,
            -self._SWEEP * 16,
        )

    def _draw_fill(self, p: QPainter, cx: float, cy: float, R: float) -> None:
        """Draw the coral fill arc from _min to the current value."""
        arc_min, arc_max = self._arc_range()
        span = arc_max - arc_min
        if span <= 0:
            return
        t = max(0.0, min(1.0, (self._rv - arc_min) / span))
        if t <= 0:
            return
        p.setPen(QPen(self._colors["fill"], R * 0.12, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        p.drawArc(
            QRectF(cx - R, cy - R, R * 2, R * 2),
            self._QT_START * 16,
            int(-t * self._SWEEP * 16),
        )

    def _draw_ticks(self, p: QPainter, cx: float, cy: float, R: float) -> None:
        """
        Draw major and minor tick marks around the arc.

        Scale: [arc_min, arc_max] = [_min, _max] (exact, no rounding).

        Major ticks
        -----------
        - Always at _min  (frac = 0) and _max (frac = 1).
        - Interior grid points: multiples of `step` strictly between _min and _max.
        - If the first or last interior grid point is closer than step / 2
          to the endpoint it is suppressed to avoid label crowding.

        Minor ticks
        -----------
        5 equal subdivisions between every consecutive pair of major ticks.
        """
        arc_min, arc_max = self._arc_range()
        total = arc_max - arc_min
        if total <= 0:
            return

        step: float = self._nice_step(total)
        minor_divs: int = 5
        half: float = step / 2.0

        p.setFont(QFont("Arial", max(7, int(R * 0.082))))
        fm = QFontMetrics(p.font())

        # Build ordered list of major-tick values
        majors: List[float] = [arc_min]

        v: float = math.ceil(arc_min / step) * step
        if abs(v - arc_min) < 1e-9:   # coincides with arc_min → skip
            v += step
        while v < arc_max - 1e-9:
            majors.append(v)
            v += step

        majors.append(arc_max)

        # Suppress an interior neighbour that is too close to an endpoint
        if len(majors) >= 3 and (majors[1] - majors[0]) < half - 1e-9:
            majors.pop(1)
        if len(majors) >= 3 and (majors[-1] - majors[-2]) < half - 1e-9:
            majors.pop(-2)

        # Render major ticks and the minor ticks between them
        for idx, val in enumerate(majors):
            frac: float = (val - arc_min) / total
            self._draw_single_tick(p, cx, cy, R, frac, val, is_major=True, fm=fm)

            if idx < len(majors) - 1:
                next_frac: float = (majors[idx + 1] - arc_min) / total
                for m in range(1, minor_divs):
                    mfrac = frac + (next_frac - frac) * m / minor_divs
                    self._draw_single_tick(p, cx, cy, R, mfrac, 0.0, is_major=False, fm=fm)

    def _draw_single_tick(
        self,
        p: QPainter,
        cx: float,
        cy: float,
        R: float,
        frac: float,
        val: float,
        is_major: bool,
        fm: QFontMetrics,
    ) -> None:
        """Draw one tick line and, for major ticks, the numeric label."""
        angle_rad: float = math.radians(self._QT_START - frac * self._SWEEP)
        cos_a: float = math.cos(angle_rad)
        sin_a: float = math.sin(angle_rad)

        tick_len: float = R * 0.10 if is_major else R * 0.055
        r_outer: float = R - R * 0.13
        r_inner: float = r_outer - tick_len

        p.setPen(QPen(
            self._colors["tick_major"] if is_major else self._colors["tick_minor"],
            1.8 if is_major else 1.0,
        ))
        p.drawLine(
            QPointF(cx + r_outer * cos_a, cy - r_outer * sin_a),
            QPointF(cx + r_inner * cos_a, cy - r_inner * sin_a),
        )

        if is_major:
            label: str = self._format_label(val)
            r_txt: float = r_inner - R * 0.09
            p.setPen(QPen(self._colors["tick_major"]))
            p.drawText(
                QPointF(
                    cx + r_txt * cos_a - fm.horizontalAdvance(label) / 2,
                    cy - r_txt * sin_a + fm.height() / 3,
                ),
                label,
            )

    def _draw_rv_text(self, p: QPainter, cx: float, cy: float, R: float) -> None:
        """Draw the large current-value readout in the centre of the arc."""
        text: str = f"{self._rv:.1f} {self._unit}"
        font: QFont = QFont("Arial", int(R * 0.22), QFont.Bold)
        p.setFont(font)
        p.setPen(QPen(self._colors["text_value"]))
        fm = QFontMetrics(font)
        p.drawText(
            QPointF(
                cx - fm.horizontalAdvance(text) / 2,
                cy + fm.height() * 0.18,
            ),
            text,
        )

    def _draw_name_label(self, p: QPainter, cx: float, cy: float, R: float) -> None:
        """
        Draw the descriptive name below the arc with a fading gradient rule.

        Layout (top → bottom):
            gradient rule  at  label_y − R * 0.13
            name text      at  label_y
        """
        label_y: float = cy + R * 0.52

        # Gradient horizontal rule — derived from fill colour
        fill = self._colors["fill"]
        fill_180 = QColor(fill.red(), fill.green(), fill.blue(), 180)
        fill_255 = QColor(fill.red(), fill.green(), fill.blue(), 255)
        line_w: float = R * 0.72
        line_y: float = label_y - R * 0.13
        grad = QLinearGradient(cx - line_w, line_y, cx + line_w, line_y)
        grad.setColorAt(0.00, QColor(0, 0, 0, 0))
        grad.setColorAt(0.35, fill_180)
        grad.setColorAt(0.50, fill_255)
        grad.setColorAt(0.65, fill_180)
        grad.setColorAt(1.00, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawRect(QRectF(cx - line_w, line_y, line_w * 2, 1.5))

        # Name + SV text
        label_text: str = "{} {:.1f} {}".format(self._name, self._sv, self._unit)
        font: QFont = QFont("Arial", max(9, int(R * 0.115)))
        p.setFont(font)
        fm = QFontMetrics(font)
        p.setPen(QPen(self._colors["text_label"]))
        p.drawText(
            QPointF(
                cx - fm.horizontalAdvance(label_text) / 2,
                label_y + fm.height() * 0.32,
            ),
            label_text,
        )

    # ── static helpers ────────────────────────────────────────────

    @staticmethod
    def _nice_step(total: float) -> float:
        """
        Return a human-friendly major-tick interval for the given range.
        Picks the smallest candidate that keeps the tick count ≤ 12.
        """
        for c in (1, 2, 5, 10, 20, 25, 50, 100):
            if total / c <= 12:
                return float(c)
        return 100.0

    @staticmethod
    def _format_label(val: float) -> str:
        """Format a tick value as a plain integer string."""
        return str(int(round(val)))
