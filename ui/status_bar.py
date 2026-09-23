from __future__ import annotations

from typing import Literal

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QLabel, QToolButton, QHBoxLayout

from linear_algebra.catalog.model import display_math_text
from ui.icons import apply_icon, icon_color, retint_icons
from ui.tokens import ThemeName

ThemeMode = Literal["light", "dark", "system"]


class AppStatusBar(QFrame):
    theme_cycle_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("appStatusBar")
        self.setFixedHeight(30)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(8)
        self.scene_label = QLabel("3D", self)
        self.tool_label = QLabel("", self)
        # 状态栏只保留一个、不可点击的说明区。右侧 AI 面板的开关位于
        # 顶部标题栏，避免“就绪”看起来像状态却意外展开侧栏。
        self.render_label = QLabel("", self)
        self.render_label.setObjectName("statusMessage")
        self.render_label.setVisible(False)
        self.theme_button = QToolButton(self)
        self.theme_button.setFixedSize(28, 28)
        self.theme_button.clicked.connect(self.theme_cycle_requested)
        for widget in (self.scene_label, self.tool_label, self.render_label):
            layout.addWidget(widget)
        layout.addStretch(1)
        layout.addWidget(self.theme_button)
        self._theme_mode: ThemeMode = "system"
        self._icon_theme: ThemeName = "light"
        self.set_theme_mode(self._theme_mode)

    def set_theme(self, theme: ThemeName) -> None:
        """Re-tint the status bar icon for the resolved theme."""
        self._icon_theme = theme
        self.set_theme_mode(self._theme_mode)
        retint_icons(self, theme)

    def set_scene_mode(self, mode) -> None:
        self.scene_label.setText("2D" if getattr(mode, "value", mode) in ("2d", "2D") else "3D")

    def set_active_tool(self, tool: str | None) -> None:
        self.tool_label.setText(tool or "")
        self.tool_label.setVisible(bool(tool))

    def set_render_status(self, text: str) -> None:
        message = display_math_text(str(text or ""))
        self.render_label.setText(message)
        self.render_label.setVisible(bool(message))

    def set_theme_mode(self, mode: ThemeMode) -> None:
        if mode not in {"system", "light", "dark"}:
            mode = "system"
        self._theme_mode = mode
        labels = {"system": "系统主题", "light": "浅色主题", "dark": "深色主题"}
        icons = {"system": "monitor", "light": "sun", "dark": "moon"}
        label = labels[mode]
        self.theme_button.setToolTip(f"{label}（点击切换）")
        self.theme_button.setAccessibleName(label)
        apply_icon(self.theme_button, icons[mode], icon_color(self._icon_theme, "muted"), icon_size=16, hit_size=28)

    @property
    def theme_mode(self) -> ThemeMode:
        return self._theme_mode
