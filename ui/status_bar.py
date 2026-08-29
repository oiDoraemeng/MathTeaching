from __future__ import annotations

from typing import Literal

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QLabel, QToolButton, QHBoxLayout

from ui.icons import apply_icon

ThemeMode = Literal["light", "dark", "system"]


class AppStatusBar(QFrame):
    agent_toggle_requested = Signal()
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
        self.render_label = QLabel("就绪", self)
        self.agent_button = QToolButton(self)
        self.agent_button.setText("Agent")
        self.agent_button.clicked.connect(self.agent_toggle_requested)
        self.theme_button = QToolButton(self)
        self.theme_button.setFixedSize(28, 28)
        self.theme_button.clicked.connect(self.theme_cycle_requested)
        for widget in (self.scene_label, self.tool_label, self.render_label, self.agent_button):
            layout.addWidget(widget)
        layout.addStretch(1)
        layout.addWidget(self.theme_button)
        self._theme_mode: ThemeMode = "system"
        self.set_theme_mode(self._theme_mode)

    def set_scene_mode(self, mode) -> None:
        self.scene_label.setText("2D" if getattr(mode, "value", mode) in ("2d", "2D") else "3D")

    def set_active_tool(self, tool: str | None) -> None:
        self.tool_label.setText(tool or "")
        self.tool_label.setVisible(bool(tool))

    def set_render_status(self, text: str) -> None:
        self.render_label.setText(text)

    def set_agent_status(self, state: str) -> None:
        self.agent_button.setText(state or "Agent")

    def set_theme_mode(self, mode: ThemeMode) -> None:
        if mode not in {"system", "light", "dark"}:
            mode = "system"
        self._theme_mode = mode
        labels = {"system": "系统主题", "light": "浅色主题", "dark": "深色主题"}
        icons = {"system": "monitor", "light": "sun", "dark": "moon"}
        label = labels[mode]
        self.theme_button.setToolTip(f"{label}（点击切换）")
        self.theme_button.setAccessibleName(label)
        apply_icon(self.theme_button, icons[mode], "#687386", icon_size=16, hit_size=28)

    @property
    def theme_mode(self) -> ThemeMode:
        return self._theme_mode
