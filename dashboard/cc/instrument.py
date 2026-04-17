# -*- coding: utf-8 -*-
"""instrument.py — Instrument Status Dashboard widgets

完全动态配置的仪器状态显示控件，支持主题切换和标签自定义。
"""

import math
import json
import copy
from pathlib import Path
from typing import Dict, Optional, Union, Tuple, List, Any
from PySide2.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QSizePolicy, QFrame,
    QFileDialog, QMessageBox, QColorDialog, QApplication
)
from PySide2.QtCore import Qt, QTimer, Signal
from PySide2.QtGui import (
    QPainter, QColor, QFont, QBrush, QFontMetrics, QPen,
    QLinearGradient, QRadialGradient
)

__all__ = [
    'ColorTheme', 'LabelsConfig', 'LabelConfig', 'THEME_KEY_LABELS',
    'PRESET_LIGHT', 'PRESET_DARK', 'PRESET_CONTRAST', 'PRESET_WARM',
    'BUILTIN_PRESETS', 'DEFAULT_THEME', 'DEFAULT_LABELS_CONFIG',
    'StatusDot', 'ProgressBar', 'InstrumentStatusWidget', 'ThemeConfigDialog',
    'STATUS_IDLE', 'STATUS_RUN', 'STATUS_ERROR',
]

# StatusDot 状态常量
STATUS_IDLE = "idle"   # 待机状态
STATUS_RUN = "run"     # 运行状态
STATUS_ERROR = "error"  # 错误状态

# Color-theme types & helpers

ColorTheme = Dict[str, str]

THEME_KEY_LABELS: Dict[str, str] = {
    "bg": "窗口背景",
    "panel": "卡片背景",
    "border": "卡片边框",
    "accent": "强调色/主要文字",
    "text": "次要文字",
    "status_run": "运行状态",
    "status_idle": "待机状态",
    "status_err": "错误状态",
}

# Built-in presets

PRESET_LIGHT: ColorTheme = {
    "bg": "#ffffff",
    "panel": "#ffffff",
    "border": "#b0cfe0",
    "accent": "#1a6b8a",
    "text": "#3a6070",
    "status_run": "#1a8a3b",
    "status_idle": "#b87333",
    "status_err": "#c0392b",
}

PRESET_DARK: ColorTheme = {
    "bg": "#1e1e1e",
    "panel": "#2d2d2d",
    "border": "#404040",
    "accent": "#4fc3f7",
    "text": "#aaaaaa",
    "status_run": "#4caf50",
    "status_idle": "#ff9800",
    "status_err": "#f44336",
}

PRESET_CONTRAST: ColorTheme = {
    "bg": "#000000",
    "panel": "#000000",
    "border": "#ffffff",
    "accent": "#00ffff",
    "text": "#cccccc",
    "status_run": "#00ff00",
    "status_idle": "#ffff00",
    "status_err": "#ff0000",
}

PRESET_WARM: ColorTheme = {
    "bg": "#fef9f3",
    "panel": "#fff5e6",
    "border": "#e8d5c4",
    "accent": "#d35400",
    "text": "#8d6e63",
    "status_run": "#2e7d32",
    "status_idle": "#f57c00",
    "status_err": "#c62828",
}

BUILTIN_PRESETS: Dict[str, ColorTheme] = {
    "浅色主题": PRESET_LIGHT,
    "深色主题 (默认)": PRESET_DARK,
    "高对比度": PRESET_CONTRAST,
    "暖色主题": PRESET_WARM,
}

DEFAULT_THEME = PRESET_DARK


# Label config types & defaults

LabelConfig = Tuple[str, str]  # (label_text, state_key)
RowConfig = Dict[str, Union[str, List[LabelConfig]]]
LabelsConfig = Dict[str, Any]

DEFAULT_LABELS_CONFIG: LabelsConfig = {
    "title": ("当前方法", "method"),
    "size": (2, 4),
    "row0": {
        "title": "序列/瓶位信息",
        "items": [
            ("当前序列", "seq"),
            ("开始瓶位", "start"),
            ("结束瓶位", "end"),
            ("当前瓶位", "cur_pos"),
        ]
    },
    "row1": {
        "title": "萃取信息/温度/时间",
        "items": [
            ("萃取次数", "ext_total"),
            ("当前次数", "ext_current"),
            ("萃取温度", "temp"),
            ("萃取时间", "time"),
        ]
    },
    "status": ("当前状态",)  # 只包含状态标题，total_steps 通过 setTotalSteps 设置
}


def get_theme_color_by_key(theme: ColorTheme, key: str) -> QColor:
    """Parse a theme hex value into QColor."""
    raw = theme.get(key, "#000000").lstrip("#")
    if len(raw) == 8:
        return QColor(int(raw[0:2], 16), int(raw[2:4], 16),
                      int(raw[4:6], 16), int(raw[6:8], 16))
    return QColor(f"#{raw}")


def _qcolor_to_hex(c: QColor) -> str:
    if c.alpha() < 255:
        return f"#{c.red():02X}{c.green():02X}{c.blue():02X}{c.alpha():02X}"
    return c.name().upper()


# StatusDot — 状态指示灯

class StatusDot(QWidget):
    """带脉冲动画的状态指示灯"""

    def __init__(self, theme: ColorTheme, parent=None):
        super().__init__(parent)
        self._theme = theme
        self.setFixedSize(14, 14)
        self._color = get_theme_color_by_key(theme, "status_idle")
        self._phase = 0.0
        self._pulse = QTimer(self)
        self._pulse.setInterval(40)
        self._pulse.timeout.connect(self._tick)
        self._pulse.start()

    def applyTheme(self, theme: ColorTheme):
        self._theme = theme
        self.update()

    def setState(self, state: str):
        """设置状态: 只接受 STATUS_IDLE, STATUS_RUN, STATUS_ERROR 三个常量"""
        if state == STATUS_ERROR:
            key, pulse = "status_err", True
        elif state == STATUS_RUN:
            key, pulse = "status_run", True
        else:  # STATUS_IDLE or any other value defaults to idle
            key, pulse = "status_idle", False

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
        size = min(self.width(), self.height()) - 4
        p.drawEllipse(2, 2, size, size)
        p.end()


# ProgressBar — 自定义进度条

class ProgressBar(QWidget):
    """带渐变和光晕效果的进度条"""

    def __init__(self, theme: ColorTheme, parent=None):
        super().__init__(parent)
        self._theme = theme
        self._target = 0.0
        self._current = 0.0
        self.setFixedHeight(8)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._anim = QTimer(self)
        self._anim.setInterval(16)
        self._anim.timeout.connect(self._step)

    def applyTheme(self, theme: ColorTheme):
        self._theme = theme
        self.update()

    def setValue(self, v: float):
        """设置进度值 0.0 ~ 1.0"""
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

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        r = h / 2
        p.setPen(Qt.NoPen)

        bg_color = get_theme_color_by_key(self._theme, "border")
        p.setBrush(bg_color)
        p.drawRoundedRect(0, 0, w, h, r, r)

        fw = int(w * self._current)
        if fw > 2:
            accent = get_theme_color_by_key(self._theme, "accent")
            g = QLinearGradient(0, 0, fw, 0)
            g.setColorAt(0, accent)
            g.setColorAt(1, accent)
            p.setBrush(QBrush(g))
            p.drawRoundedRect(0, 0, fw, h, r, r)

            glow = QRadialGradient(fw, h/2, 12)
            glow.setColorAt(0, QColor(accent.red(), accent.green(), accent.blue(), 180))
            glow.setColorAt(1, QColor(accent.red(), accent.green(), accent.blue(), 0))
            p.setBrush(QBrush(glow))
            p.drawEllipse(fw-12, int(h/2)-12, 24, 24)

        p.end()


# InstrumentStatusWidget — 仪器状态面板主控件

class InstrumentStatusWidget(QWidget):
    """
    仪器工作状态面板 — 纯 paintEvent 绘制，完全动态配置

    Public API
    ───────────────────
      setState(state: dict)         批量设置状态 (键名由 labels_config 决定)
      setCurrentStatus(step, text)  设置当前步骤和状态文字
      setDotState(state)            明确设置状态指示灯状态 (STATUS_IDLE/STATUS_RUN/STATUS_ERROR)
      setTotalSteps(steps)          设置运行状态总数
      applyTheme(ColorTheme)        热切换主题

    动态配置
    ───────
      通过 labels_config 参数配置所有标签文字和对应的状态键名
      默认配置见 DEFAULT_LABELS_CONFIG
    """

    def __init__(self, theme: Optional[ColorTheme] = None,
                 labels_config: Optional[LabelsConfig] = None,
                 margin: int = 24,
                 padding: int = 12,
                 spacing: int = 12,
                 parent=None):
        super().__init__(parent)
        self._theme = {**DEFAULT_THEME, **(theme or {})}

        # 标签配置
        labels = {**DEFAULT_LABELS_CONFIG, **(labels_config or {})}

        # 检查必需的键及其类型
        if 'title' not in labels:
            raise ValueError("Labels config missing required key: 'title'")
        title = labels['title']
        if not isinstance(title, (list, tuple)) or len(title) != 2:
            raise ValueError("'title' must be a tuple/list of (label_text, state_key)")

        if 'size' not in labels:
            raise ValueError("Labels config missing required key: 'size'")
        size = labels['size']
        if not isinstance(size, (list, tuple)) or len(size) != 2:
            raise ValueError("'size' must be a tuple/list of (num_rows, num_cols)")
        if not isinstance(size[0], int) or not isinstance(size[1], int):
            raise ValueError("'size' values must be integers")

        if 'status' not in labels:
            raise ValueError("Labels config missing required key: 'status'")
        status = labels['status']
        if not isinstance(status, (list, tuple)) or len(status) < 1:
            raise ValueError("'status' must be a tuple/list of (label_text,) or (label_text,)")

        self._labels = labels

        # 从 labels 配置中提取所有状态键并初始化 _state
        self._state = self._extractStateKeys(labels)
        self._status = "待机中"
        self._status_step = 0
        self._dot_state = STATUS_IDLE  # 状态指示灯当前状态
        self._total_steps = 5  # 运行状态总数，可通过 setTotalSteps 动态设置

        # 布局参数
        self._margin = margin
        self._card_padding = padding
        self._card_padding_top = max(0, padding - 4)
        self._card_spacing = spacing
        self._section_spacing = spacing + 8
        self._label_value_gap = 4
        self._status_label_gap = 2
        self._row_height = 0
        self._col_width = 0

        # 用户自定义标志（通过参数初始化，标记为已自定义）
        self._custom_margin = True
        self._custom_padding = True
        self._custom_spacing = True

        # 字体
        self._font_title = QFont("Segoe UI", 11, QFont.Bold)
        self._font_label = QFont("Segoe UI", 9)
        self._font_value = QFont("Courier New", 18, QFont.Bold)
        self._font_value_small = QFont("Courier New", 14, QFont.Bold)
        self._font_method = QFont("Courier New", 20, QFont.Bold)
        self._font_status = QFont("Segoe UI", 22, QFont.Bold)
        self._font_unit = QFont("Segoe UI", 9)

        self.setMinimumSize(600, 400)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 子控件
        self._status_dot = StatusDot(self._theme, self)
        self._progress_bar = ProgressBar(self._theme, self)

        self._refreshLayout()

    def _extractStateKeys(self, labels: LabelsConfig) -> dict:
        """从 labels 配置中提取所有状态键，初始化为默认值"""
        state_keys = set()

        # 从 title 提取状态键 (title 格式: (label_text, state_key))
        title = labels['title']
        state_keys.add(title[1])

        # 从 rowX 配置中提取状态键
        size = labels['size']
        num_rows = size[0]

        for row_idx in range(num_rows):
            row_key = f'row{row_idx}'
            row_config = labels.get(row_key)
            if not row_config:
                continue
            items = row_config.get('items', [])
            for item in items:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    state_keys.add(item[1])

        # 所有状态键初始化为 "—"
        return {key: "—" for key in state_keys}

    # Public API

    def setDotState(self, state: str):
        """明确设置状态指示灯状态
        :param state: STATUS_IDLE, STATUS_RUN, STATUS_ERROR 之一
        """
        self._dot_state = state
        self._status_dot.setState(state)

    def setTotalSteps(self, steps: int):
        """设置运行状态总数
        :param steps: 状态总数，必须大于 0
        """
        self._total_steps = max(1, steps)
        self._updateProgress()
        self.update()

    def setCurrentStatus(self, step_index: int, status_text: str):
        """设置当前状态文字和步骤
        :param step_index: 步骤编号，从 0 开始
        :param status_text: 状态文字（仅显示，不控制指示灯）
        """
        self._status_step = max(0, step_index)
        self._status = str(status_text)
        self._updateProgress()
        self.update()

    def setState(self, state: dict):
        """批量设置状态（不控制指示灯，需单独调用 setDotState）"""
        for key in self._state:
            if key in state:
                self._state[key] = state[key]
        if state.get('status_step') is not None:
            self._status_step = max(0, state['status_step'])
        if state.get('status_text') is not None:
            self._status = str(state['status_text'])
        self._updateProgress()
        self.update()

    def applyTheme(self, theme: ColorTheme):
        """热切换主题"""
        self._theme = theme
        self._status_dot.applyTheme(theme)
        self._progress_bar.applyTheme(theme)
        self.update()

    def setMargin(self, margin: int):
        """设置控件整体边距"""
        self._custom_margin = True
        self._margin = max(0, margin)
        self._refreshLayout()
        self.update()

    def setPadding(self, padding: int):
        """设置卡片内边距"""
        self._custom_padding = True
        self._card_padding = max(0, padding)
        self._card_padding_top = max(0, padding - 4)  # 顶部稍小
        self.update()

    def setSpacing(self, spacing: int):
        """设置卡片间距"""
        self._custom_spacing = True
        self._card_spacing = max(0, spacing)
        self._section_spacing = max(0, spacing + 8)  # 区块间距稍大
        self._refreshLayout()
        self.update()

    # Internal

    def _updateProgress(self):
        """更新进度条 - 基于步骤索引和 _total_steps"""
        # 使用当前步骤索引计算进度 (0-indexed, 所以 +1 后除以总数)
        ratio = (self._status_step + 1) / self._total_steps if self._total_steps > 0 else 0.0
        self._progress_bar.setValue(ratio)

    def _getStatusColor(self) -> QColor:
        """根据状态指示灯状态获取颜色"""
        if self._dot_state == STATUS_ERROR:
            return get_theme_color_by_key(self._theme, "status_err")
        elif self._dot_state == STATUS_RUN:
            return get_theme_color_by_key(self._theme, "status_run")
        else:
            return get_theme_color_by_key(self._theme, "status_idle")

    # Layout & Resize

    def resizeEvent(self, event):
        """窗口大小变化时重新计算布局"""
        super().resizeEvent(event)
        self._refreshLayout()

    def _refreshLayout(self):
        """计算布局参数和子控件位置"""
        w = self.width()
        h = self.height()

        # 只在用户未自定义时根据窗口大小调整
        if w < 500:
            if not self._custom_margin:
                self._margin = 16
            if not self._custom_padding:
                self._card_padding = 10
                self._card_padding_top = 6
            if not self._custom_spacing:
                self._card_spacing = 8
                self._section_spacing = 14
        else:
            if not self._custom_margin:
                self._margin = 24
            if not self._custom_padding:
                self._card_padding = 12
                self._card_padding_top = 8
            if not self._custom_spacing:
                self._card_spacing = 12
                self._section_spacing = 20

        content_w = w - 2 * self._margin

        # 根据配置中的列数自动计算每列宽度
        size_config = self._labels['size']
        num_cols = size_config[1] if isinstance(size_config, (list, tuple)) else 4
        total_spacing = (num_cols - 1) * self._card_spacing if num_cols > 1 else 0
        self._col_width = (content_w - total_spacing) // num_cols

        base_font_size = max(8, min(11, h // 40))
        self._font_label.setPointSize(base_font_size)
        self._font_unit.setPointSize(base_font_size)

        value_font_size = max(12, min(18, h // 25))
        self._font_value.setPointSize(value_font_size)

        method_font_size = max(14, min(20, h // 22))
        self._font_method.setPointSize(method_font_size)

        status_font_size = max(16, min(24, h // 20))
        self._font_status.setPointSize(status_font_size)

        progress_height = max(6, min(10, h // 50))
        self._progress_bar.setFixedHeight(progress_height)

        self.update()

    # Paint Event

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        p.fillRect(self.rect(), get_theme_color_by_key(self._theme, "bg"))

        y = self._margin

        # 1. 状态条 - 第一行内容
        title_config = self._labels['title']
        title_label = title_config[0]
        y = self._drawTitleBar(p, y, title_label)
        y += self._section_spacing

        # 获取 size 配置
        size_config = self._labels['size']
        num_rows = size_config[0]
        num_cols = size_config[1]

        # 2. 绘制每一行
        for row_idx in range(num_rows):
            row_key = f'row{row_idx}'
            row_config = self._labels.get(row_key)
            if not row_config:
                continue

            items = row_config.get('items', [])
            if not items:
                continue

            section_title = row_config.get('title', f'Row {row_idx}')
            y = self._drawSectionTitle(p, y, f"▸  {section_title}")
            y += self._card_spacing

            values = []
            for item in items:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    label_text, state_key = item[0], item[1]
                    if state_key in self._state:
                        values.append((label_text, str(self._state[state_key]), ""))

            if values:
                while len(values) < num_cols:
                    values.append(("", "—", ""))
                y = self._drawStatusRow(p, y, values[:num_cols])
                y += self._section_spacing

        # 3. 当前状态区域
        status_config = self._labels['status']
        status_title = status_config[0]
        y = self._drawSectionTitle(p, y, f"▸  {status_title}")
        y += self._card_spacing
        self._drawStatusArea(p, y, status_config)

        p.end()

    def _drawRoundedRect(self, p: QPainter, x: int, y: int, w: int, h: int,
                         radius: int, fill: QColor, stroke: QColor):
        """绘制圆角矩形卡片"""
        p.setPen(Qt.NoPen)
        p.setBrush(fill)
        p.drawRoundedRect(x, y, w, h, radius, radius)

        pen = p.pen()
        pen.setColor(stroke)
        pen.setWidth(1)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(x, y, w, h, radius, radius)

    def _drawSectionTitle(self, p: QPainter, y: int, text: str) -> int:
        """绘制分隔标题"""
        x = self._margin

        p.setPen(get_theme_color_by_key(self._theme, "text"))
        p.setFont(self._font_label)

        fm = QFontMetrics(self._font_label)
        text_h = fm.height()
        p.drawText(x, y + text_h, text)

        line_y = y + text_h + 4
        line_w = self.width() - 2 * self._margin
        p.setPen(QPen(get_theme_color_by_key(self._theme, "border"), 1))
        p.drawLine(x, line_y, x + line_w, line_y)

        return line_y

    def _drawTitleBar(self, p: QPainter, y: int, label: str) -> int:
        """绘制方法状态条"""
        x = self._margin
        w = self.width() - 2 * self._margin

        fm_label = QFontMetrics(self._font_label)
        fm_method = QFontMetrics(self._font_method)
        h = self._card_padding_top + fm_label.height() + self._label_value_gap + fm_method.height() + self._card_padding

        self._drawRoundedRect(
            p, x, y, w, h, 6,
            get_theme_color_by_key(self._theme, "panel"),
            get_theme_color_by_key(self._theme, "border")
        )

        label_x = x + self._card_padding
        label_y = y + self._card_padding_top
        p.setPen(get_theme_color_by_key(self._theme, "text"))
        p.setFont(self._font_label)
        p.drawText(label_x, label_y + fm_label.ascent(), label)

        value_y = label_y + fm_label.height() + self._label_value_gap * 3
        p.setPen(get_theme_color_by_key(self._theme, "accent"))
        p.setFont(self._font_method)
        title_config = self._labels['title']
        method_key = title_config[1]
        p.drawText(label_x, value_y + fm_method.ascent(), str(self._state[method_key]))

        return y + h

    def _drawStatusRow(self, p: QPainter, y: int, items) -> int:
        """绘制一行状态项 (4列)"""
        x = self._margin
        max_h = 0

        for i, (label, value, unit) in enumerate(items):
            item_x = x + i * (self._col_width + self._card_spacing)
            item_h = self._drawStatusItem(p, item_x, y, self._col_width, label, value, unit)
            max_h = max(max_h, item_h)

        return y + max_h

    def _drawStatusItem(self, p: QPainter, x: int, y: int, w: int,
                        label: str, value: str, unit: str) -> int:
        """绘制单个状态项卡片"""
        fm_label = QFontMetrics(self._font_label)
        fm_value = QFontMetrics(self._font_value)

        item_gap = self._label_value_gap + 16
        top_padding = self._card_padding_top
        bottom_padding = self._card_padding

        h = top_padding + fm_label.height() + item_gap + fm_value.height() + bottom_padding

        self._drawRoundedRect(
            p, x, y, w, h, 6,
            get_theme_color_by_key(self._theme, "panel"),
            get_theme_color_by_key(self._theme, "border")
        )

        label_x = x + self._card_padding
        label_y = y + top_padding + fm_label.ascent()
        p.setPen(get_theme_color_by_key(self._theme, "text"))
        p.setFont(self._font_label)
        p.drawText(label_x, label_y, label)

        value_y = label_y + fm_label.height() + self._label_value_gap + item_gap
        p.setPen(get_theme_color_by_key(self._theme, "accent"))
        p.setFont(self._font_value)
        value_text = str(value)

        if unit:
            value_w = fm_value.horizontalAdvance(value_text)
            p.drawText(label_x, value_y, value_text)
            unit_x = label_x + value_w + 4
            p.drawText(unit_x, value_y, unit)
        else:
            p.drawText(label_x, value_y, value_text)

        return h

    def _drawStatusArea(self, p: QPainter, y: int, status_config: Tuple) -> int:
        """绘制当前状态区域"""
        x = self._margin
        w = self.width() - 2 * self._margin

        total_steps = self._total_steps

        fm_label = QFontMetrics(self._font_label)
        fm_status = QFontMetrics(self._font_status)
        progress_h = self._progress_bar.height()

        status_to_progress_gap = 24
        h = (self._card_padding_top + fm_label.height() + self._status_label_gap +
             fm_status.height() + status_to_progress_gap + progress_h + self._card_padding)

        self._drawRoundedRect(
            p, x, y, w, h, 6,
            get_theme_color_by_key(self._theme, "panel"),
            get_theme_color_by_key(self._theme, "border")
        )

        label_x = x + self._card_padding
        label_y = y + self._card_padding_top + fm_label.ascent()

        dot_size = max(8, int(fm_label.height() * 0.8))
        self._status_dot.setFixedSize(dot_size, dot_size)
        dot_x = label_x
        dot_y = label_y - fm_label.ascent() // 2 - dot_size // 2 + 2
        self._status_dot.move(dot_x, dot_y)

        step_display = f"{self._status_step + 1} / {total_steps}"
        fm_pct = QFontMetrics(self._font_label)
        pct_w = fm_pct.horizontalAdvance(step_display)
        pct_x = x + w - self._card_padding - pct_w
        p.setPen(get_theme_color_by_key(self._theme, "accent"))
        p.setFont(self._font_label)
        p.drawText(pct_x, label_y, step_display)

        status_y = label_y + fm_label.height() + self._status_label_gap + fm_status.ascent()
        status_color = self._getStatusColor()
        p.setPen(status_color)
        p.setFont(self._font_status)
        p.drawText(label_x, status_y, self._status)

        bar_y = (y + self._card_padding_top + fm_label.height() +
                 self._status_label_gap + fm_status.height() + status_to_progress_gap)
        self._progress_bar.setGeometry(
            label_x, bar_y,
            w - 2 * self._card_padding, progress_h
        )

        return y + h


# ThemeConfigDialog — 主题配置对话框

class ThemeConfigDialog(QDialog):
    """
    Modal theme editor.
      • Preset selector  — instantly applies a built-in theme
      • Color grid       — one color-picker button per theme key
      • Export JSON      — save to file
      • Copy as dict     — copy Python dict literal to clipboard
      • Import JSON      — load from file
    Emits signalThemeApplied(ColorTheme) when a color or preset changes.
    """

    signalThemeApplied = Signal(object)

    def __init__(self, current_theme: ColorTheme, parent=None):
        super().__init__(parent)
        self._theme = copy.deepcopy(current_theme)
        self.setWindowTitle(self.tr("配置主题颜色"))
        self.setMinimumWidth(520)
        self._buildUi()

    def _buildUi(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(12)

        preset_row = QHBoxLayout()
        preset_row.setSpacing(10)
        lbl = QLabel(self.tr("预设主题"))
        lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self._ui_preset_combo = QComboBox()
        self._ui_preset_combo.setFont(QFont("Segoe UI", 9))
        self._ui_preset_combo.setFixedHeight(32)
        self._ui_preset_combo.addItem("— Custom —")
        for name in BUILTIN_PRESETS:
            self._ui_preset_combo.addItem(name)
        self._ui_preset_combo.currentIndexChanged.connect(self._onPreset)
        preset_row.addWidget(lbl)
        preset_row.addWidget(self._ui_preset_combo, 1)
        root.addLayout(preset_row)

        scroll = QFrame()
        scroll.setFrameShape(QFrame.NoFrame)
        grid = QGridLayout(scroll)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)

        self._ui_color_btns: Dict[str, QPushButton] = {}
        for row_i, (key, label) in enumerate(THEME_KEY_LABELS.items()):
            lbl2 = QLabel(label)
            lbl2.setFont(QFont("Segoe UI", 9))
            lbl2.setFixedWidth(170)
            btn = QPushButton()
            btn.setFixedSize(80, 26)
            btn.setFont(QFont("Segoe UI", 8))
            btn.setCursor(Qt.PointingHandCursor)
            self._refreshBtn(btn, key)
            btn.clicked.connect(lambda checked=False, k=key: self._pickColor(k))
            self._ui_color_btns[key] = btn
            grid.addWidget(lbl2, row_i, 0)
            grid.addWidget(btn, row_i, 1)

        root.addWidget(scroll, 1)

        sep = QFrame()
        sep.setFixedHeight(1)
        root.addWidget(sep)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        export_btn = QPushButton(self.tr("导出 JSON"))
        export_btn.setFont(QFont("Segoe UI", 9))
        export_btn.setFixedHeight(32)
        export_btn.clicked.connect(self._exportJson)

        copy_btn = QPushButton(self.tr("复制 Dict"))
        copy_btn.setFont(QFont("Segoe UI", 9))
        copy_btn.setFixedHeight(32)
        copy_btn.clicked.connect(self._copyDict)

        import_btn = QPushButton(self.tr("导入 JSON"))
        import_btn.setFont(QFont("Segoe UI", 9))
        import_btn.setFixedHeight(32)
        import_btn.clicked.connect(self._importJson)

        close_btn = QPushButton(self.tr("关闭"))
        close_btn.setFont(QFont("Segoe UI", 9))
        close_btn.setFixedHeight(32)
        close_btn.clicked.connect(self.accept)

        btn_row.addWidget(export_btn)
        btn_row.addWidget(copy_btn)
        btn_row.addWidget(import_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

    def _pickColor(self, key: str):
        initial = get_theme_color_by_key(self._theme, key)
        dlg = QColorDialog(initial, self)
        dlg.setOption(QColorDialog.ShowAlphaChannel, True)
        if dlg.exec_() == QColorDialog.Accepted:
            chosen = dlg.selectedColor()
            self._theme[key] = _qcolor_to_hex(chosen)
            self._refreshBtn(self._ui_color_btns[key], key)
            self._ui_preset_combo.blockSignals(True)
            self._ui_preset_combo.setCurrentIndex(0)
            self._ui_preset_combo.blockSignals(False)
            self.signalThemeApplied.emit(copy.deepcopy(self._theme))

    def _refreshBtn(self, btn: QPushButton, key: str):
        c = get_theme_color_by_key(self._theme, key)
        hex_str = _qcolor_to_hex(c)
        luma = 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()
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

    def _onPreset(self, idx: int):
        if idx == 0:
            return
        name = self._ui_preset_combo.currentText()
        preset = BUILTIN_PRESETS.get(name)
        if preset:
            self._theme = copy.deepcopy(preset)
            for key, btn in self._ui_color_btns.items():
                self._refreshBtn(btn, key)
            self.signalThemeApplied.emit(copy.deepcopy(self._theme))

    def _exportJson(self):
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("导出主题"), "my_theme.json", self.tr("JSON files (*.json)")
        )
        if path:
            try:
                Path(path).write_text(
                    json.dumps(self._theme, indent=2, ensure_ascii=False), encoding="utf-8"
                )
                QMessageBox.information(self, self.tr("导出成功"), self.tr("主题已保存到:\n") + path)
            except Exception as e:
                QMessageBox.critical(self, self.tr("错误"), str(e))

    def _copyDict(self):
        lines = ["theme = {"]
        for k, v in self._theme.items():
            lines.append(f'    "{k}": "{v}",')
        lines.append("}")
        QApplication.clipboard().setText("\n".join(lines))
        QMessageBox.information(self, self.tr("复制成功"), self.tr("主题字典已复制到剪贴板"))

    def _importJson(self):
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr("导入主题"), "", self.tr("JSON files (*.json)")
        )
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            missing = [k for k in DEFAULT_THEME if k not in data]
            if missing:
                QMessageBox.warning(
                    self, self.tr("部分主题"),
                    self.tr("缺少的键将使用默认值:\n") + ", ".join(missing)
                )
            self._theme = {**DEFAULT_THEME, **data}
            for key, btn in self._ui_color_btns.items():
                self._refreshBtn(btn, key)
            self._ui_preset_combo.blockSignals(True)
            self._ui_preset_combo.setCurrentIndex(0)
            self._ui_preset_combo.blockSignals(False)
            self.signalThemeApplied.emit(copy.deepcopy(self._theme))
        except Exception as e:
            QMessageBox.critical(self, self.tr("导入失败"), str(e))

    def getTheme(self) -> ColorTheme:
        """返回当前配置的主题"""
        return copy.deepcopy(self._theme)
