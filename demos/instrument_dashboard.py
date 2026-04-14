# -*- coding: utf-8 -*-
"""instrument_dashboard.py — Instrument Status Dashboard Demo

演示 InstrumentStatusWidget 的使用。
"""

import sys
from typing import Optional
from pathlib import Path
import json

from PySide2.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QFrame, QLabel, QMessageBox, QFileDialog,
    QSpinBox, QSlider, QGridLayout
)
from PySide2.QtGui import QFont
from PySide2.QtCore import QTimer

from ..dashboard.cc.instrument import (
    ColorTheme, DEFAULT_THEME, BUILTIN_PRESETS,
    InstrumentStatusWidget, ThemeConfigDialog, DEFAULT_LABELS_CONFIG
)


class DemoWindow(QWidget):
    """InstrumentStatusWidget 演示窗口"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme: Optional[ColorTheme] = None
        self.setWindowTitle(self.tr("仪器状态控件 - 主题测试"))
        self.setMinimumSize(800, 600)
        self._buildUi()
        self._setupDemoTimer()

    def _buildUi(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        # 顶部控制面板 - 使用 Qt 默认样式
        control_panel = QFrame()
        control_panel.setFrameShape(QFrame.StyledPanel)
        control_layout = QHBoxLayout(control_panel)
        control_layout.setContentsMargins(12, 8, 12, 8)
        control_layout.setSpacing(12)

        # 主题选择
        lbl_theme = QLabel(self.tr("选择主题:"))
        self._ui_cmb_theme = QComboBox()
        self._ui_cmb_theme.addItems(list(BUILTIN_PRESETS.keys()))
        self._ui_cmb_theme.currentTextChanged.connect(self._onThemeChanged)

        # 操作按钮
        self._ui_btn_export = QPushButton(self.tr("导出 JSON"))
        self._ui_btn_export.clicked.connect(self._exportTheme)

        self._ui_btn_copy = QPushButton(self.tr("复制 Dict"))
        self._ui_btn_copy.clicked.connect(self._copyDict)

        self._ui_btn_import = QPushButton(self.tr("导入 JSON"))
        self._ui_btn_import.clicked.connect(self._importTheme)

        self._ui_btn_config = QPushButton(self.tr("配置主题"))
        self._ui_btn_config.clicked.connect(self._configTheme)

        self._ui_btn_load_labels = QPushButton(self.tr("加载配置"))
        self._ui_btn_load_labels.clicked.connect(self._loadLabelsConfig)

        control_layout.addWidget(lbl_theme)
        control_layout.addWidget(self._ui_cmb_theme)
        control_layout.addStretch()
        control_layout.addWidget(self._ui_btn_load_labels)
        control_layout.addWidget(self._ui_btn_config)
        control_layout.addWidget(self._ui_btn_export)
        control_layout.addWidget(self._ui_btn_copy)
        control_layout.addWidget(self._ui_btn_import)

        root_layout.addWidget(control_panel)

        # 布局调节面板
        spacing_panel = QFrame()
        spacing_panel.setFrameShape(QFrame.StyledPanel)
        spacing_layout = QGridLayout(spacing_panel)
        spacing_layout.setContentsMargins(12, 8, 12, 8)
        spacing_layout.setSpacing(8)

        # Margin 调节
        lbl_margin = QLabel(self.tr("边距 (Margin):"))
        self._ui_spin_margin = QSpinBox()
        self._ui_spin_margin.setRange(0, 100)
        self._ui_spin_margin.setValue(24)
        self._ui_spin_margin.valueChanged.connect(self._onMarginChanged)
        spacing_layout.addWidget(lbl_margin, 0, 0)
        spacing_layout.addWidget(self._ui_spin_margin, 0, 1)

        # Padding 调节
        lbl_padding = QLabel(self.tr("内边距 (Padding):"))
        self._ui_spin_padding = QSpinBox()
        self._ui_spin_padding.setRange(0, 50)
        self._ui_spin_padding.setValue(12)
        self._ui_spin_padding.valueChanged.connect(self._onPaddingChanged)
        spacing_layout.addWidget(lbl_padding, 0, 2)
        spacing_layout.addWidget(self._ui_spin_padding, 0, 3)

        # Spacing 调节
        lbl_spacing = QLabel(self.tr("间距 (Spacing):"))
        self._ui_spin_spacing = QSpinBox()
        self._ui_spin_spacing.setRange(0, 50)
        self._ui_spin_spacing.setValue(12)
        self._ui_spin_spacing.valueChanged.connect(self._onSpacingChanged)
        spacing_layout.addWidget(lbl_spacing, 0, 4)
        spacing_layout.addWidget(self._ui_spin_spacing, 0, 5)

        root_layout.addWidget(spacing_panel)

        # 仪器状态控件
        self._ui_status_widget = InstrumentStatusWidget()
        root_layout.addWidget(self._ui_status_widget, 1)

        # 应用初始调节值
        self._ui_status_widget.setMargin(self._ui_spin_margin.value())
        self._ui_status_widget.setPadding(self._ui_spin_padding.value())
        self._ui_status_widget.setSpacing(self._ui_spin_spacing.value())

    def _onThemeChanged(self, theme_name: str):
        """切换主题"""
        if theme_name in BUILTIN_PRESETS:
            self._theme = BUILTIN_PRESETS[theme_name]
            self._ui_status_widget.applyTheme(self._theme)

    def _onMarginChanged(self, value: int):
        """边距调节"""
        self._ui_status_widget.setMargin(value)

    def _onPaddingChanged(self, value: int):
        """内边距调节"""
        self._ui_status_widget.setPadding(value)

    def _onSpacingChanged(self, value: int):
        """间距调节"""
        self._ui_status_widget.setSpacing(value)

    def _exportTheme(self):
        """导出当前主题为 JSON 文件"""
        theme_name = self._ui_cmb_theme.currentText()
        theme = BUILTIN_PRESETS.get(theme_name, DEFAULT_THEME)

        file_path, _ = QFileDialog.getSaveFileName(
            self, self.tr("导出主题"), f"{theme_name.replace(' ', '_')}.json",
            self.tr("JSON Files (*.json)")
        )
        if file_path:
            try:
                Path(file_path).write_text(
                    json.dumps(theme, indent=2, ensure_ascii=False), encoding="utf-8"
                )
                QMessageBox.information(self, self.tr("导出成功"), self.tr("主题已保存到:\n") + file_path)
            except Exception as e:
                QMessageBox.critical(self, self.tr("错误"), str(e))

    def _copyDict(self):
        """复制当前主题字典到剪贴板"""
        theme_name = self._ui_cmb_theme.currentText()
        theme = BUILTIN_PRESETS.get(theme_name, DEFAULT_THEME)

        lines = ["theme = {"]
        for k, v in theme.items():
            lines.append(f'    "{k}": "{v}",')
        lines.append("}")

        QApplication.clipboard().setText("\n".join(lines))
        QMessageBox.information(self, self.tr("复制成功"), self.tr("主题已复制到剪贴板"))

    def _importTheme(self):
        """从 JSON 文件导入主题"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, self.tr("导入主题"), "", self.tr("JSON Files (*.json)")
        )
        if file_path:
            try:
                data = json.loads(Path(file_path).read_text(encoding="utf-8"))
                required_keys = set(DEFAULT_THEME.keys())
                if not required_keys.issubset(set(data.keys())):
                    missing = required_keys - set(data.keys())
                    QMessageBox.warning(self, self.tr("部分主题"), self.tr("缺少的键: ") + ", ".join(missing))
                    return

                custom_name = f"自定义: {Path(file_path).stem}"
                BUILTIN_PRESETS[custom_name] = data

                self._ui_cmb_theme.blockSignals(True)
                self._ui_cmb_theme.addItem(custom_name)
                self._ui_cmb_theme.setCurrentText(custom_name)
                self._ui_cmb_theme.blockSignals(False)

                self._onThemeChanged(custom_name)
            except Exception as e:
                QMessageBox.critical(self, self.tr("导入失败"), str(e))

    def _configTheme(self):
        """打开主题配置对话框"""
        theme_name = self._ui_cmb_theme.currentText()
        current_theme = BUILTIN_PRESETS.get(theme_name, DEFAULT_THEME)

        dialog = ThemeConfigDialog(current_theme, self)
        dialog.signalThemeApplied.connect(self._ui_status_widget.applyTheme)

        if dialog.exec_() == ThemeConfigDialog.Accepted:
            new_theme = dialog.getTheme()
            BUILTIN_PRESETS[theme_name] = new_theme

    def _loadLabelsConfig(self):
        """从 JSON 文件加载标签配置并应用到控件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, self.tr("加载标签配置"), "", self.tr("JSON Files (*.json)")
        )
        if not file_path:
            return
        try:
            data = json.loads(Path(file_path).read_text(encoding="utf-8"))

            required_keys = ['title', 'size']
            missing = [k for k in required_keys if k not in data]
            if missing:
                QMessageBox.warning(self, self.tr("配置不完整"), self.tr("缺少必要键: ") + ", ".join(missing))
                return

            # 保存当前主题
            current_theme = self._theme

            # 从布局中移除旧的 widget
            self.layout().removeWidget(self._ui_status_widget)
            self._ui_status_widget.deleteLater()

            # 创建新的 InstrumentStatusWidget 实例
            self._ui_status_widget = InstrumentStatusWidget(
                theme=current_theme,
                labels_config={**DEFAULT_LABELS_CONFIG, **data},
                parent=self
            )
            # 添加到布局（插入到索引2的位置，即在 spacing_panel 之后）
            self.layout().insertWidget(2, self._ui_status_widget, 1)

            # 应用当前调节值
            self._ui_status_widget.setMargin(self._ui_spin_margin.value())
            self._ui_status_widget.setPadding(self._ui_spin_padding.value())
            self._ui_status_widget.setSpacing(self._ui_spin_spacing.value())

            QMessageBox.information(self, self.tr("加载成功"), self.tr("标签配置已加载:\n") + file_path)
        except Exception as e:
            QMessageBox.critical(self, self.tr("加载失败"), str(e))

    def _setupDemoTimer(self):
        """设置模拟数据定时器"""
        self._step = [0]
        demo_seq = [
            # (序列, 开始, 结束, 方法, 总次数, 当次, 当瓶位, 温度, 时间, 步骤编号, 状态)
            (1, 1, 12, "SPE-STD-01", 3, 0, 1, 25.0, 0, 0, "待机中"),
            (1, 1, 12, "SPE-STD-01", 3, 1, 1, 40.0, 30, 1, "萃取运行中"),
            (1, 1, 12, "SPE-STD-01", 3, 1, 2, 40.5, 60, 1, "萃取运行中"),
            (1, 1, 12, "SPE-STD-01", 3, 2, 3, 41.0, 90, 2, "萃取运行中"),
            (1, 1, 12, "SPE-STD-01", 3, 2, 4, 40.8, 120, 2, "萃取运行中"),
            (1, 1, 12, "SPE-STD-01", 3, 3, 5, 40.2, 150, 3, "萃取运行中"),
            (1, 1, 12, "SPE-STD-01", 3, 3, 6, 38.5, 180, 3, "洗脱中"),
            (2, 1, 12, "SPE-HVY-02", 3, 0, 7, 25.0, 0, 0, "切换方法"),
            (2, 1, 12, "SPE-HVY-02", 3, 1, 7, 55.0, 45, 1, "萃取运行中"),
            (2, 1, 12, "SPE-HVY-02", 3, 2, 8, 55.3, 90, 2, "萃取运行中"),
            (2, 1, 12, "SPE-HVY-02", 3, 3, 9, 54.8, 135, 4, "序列完成"),
            (3, 1, 12, "SPE-HVY-02", 3, 0, 10, 25.0, 0, 0, "待机中"),
        ]

        def update():
            i = self._step[0] % len(demo_seq)
            s, sb, eb, meth, tot, cur, pos, temp, t, step_idx, status = demo_seq[i]
            self._ui_status_widget.setState({
                'seq': s, 'start': sb, 'end': eb, 'method': meth,
                'ext_total': tot, 'ext_current': cur, 'cur_pos': pos,
                'temp': temp, 'time': t, 'status_step': step_idx, 'status_text': status,
            })
            self._step[0] += 1

        self._timer = QTimer(self)
        self._timer.timeout.connect(update)
        self._timer.start(1800)
        update()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = DemoWindow()
    win.show()
    sys.exit(app.exec_())
