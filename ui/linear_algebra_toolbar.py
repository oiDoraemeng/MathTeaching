"""Horizontal linear algebra toolbar for 2D canvas."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QToolButton, QWidget


class LinearAlgebraToolbar(QWidget):
    """Horizontal linear algebra toolbar positioned at top-left.

    Provides 9 tools: select, point, vector, angle, projection, polygon,
    transform, subspace, oriented area, plus undo/redo.
    """

    # Signals
    tool_selected = Signal(str)  # Tool name: "select", "point", "vector", etc.
    undo_requested = Signal()
    redo_requested = Signal()

    def __init__(self, parent: QWidget | None = None, theme: str = "light"):
        super().__init__(parent)
        self._theme = theme
        self._active_tool = "select"
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self):
        """Create toolbar layout and buttons."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)  # 4px between tools

        # Basic tools group
        self.select_tool = self._create_tool_button("select", "选择/移动", "🖱️")
        self.point_tool = self._create_tool_button("point", "点", "⚫")
        self.vector_tool = self._create_tool_button("vector", "向量", "➡️")

        layout.addWidget(self.select_tool)
        layout.addWidget(self.point_tool)
        layout.addWidget(self.vector_tool)

        # Spacer between groups
        layout.addSpacing(12)

        # Linear algebra tools group (NEW)
        self.angle_tool = self._create_tool_button("angle", "角度测量", "∠")
        self.projection_tool = self._create_tool_button("projection", "投影", "⊥")
        self.polygon_tool = self._create_tool_button("polygon", "多边形", "⬡")
        self.transform_tool = self._create_tool_button("transform", "矩阵变换", "⊞")
        self.subspace_tool = self._create_tool_button("subspace", "子空间", "◱")
        self.area_tool = self._create_tool_button("area", "有向面积", "▭")

        layout.addWidget(self.angle_tool)
        layout.addWidget(self.projection_tool)
        layout.addWidget(self.polygon_tool)
        layout.addWidget(self.transform_tool)
        layout.addWidget(self.subspace_tool)
        layout.addWidget(self.area_tool)

        # Spacer before history
        layout.addSpacing(12)

        # History group
        self.undo_button = self._create_action_button("undo", "撤销", "↶")
        self.redo_button = self._create_action_button("redo", "重做", "↷")

        layout.addWidget(self.undo_button)
        layout.addWidget(self.redo_button)

        # Push everything to the left
        layout.addStretch()

        # Set select as default active tool
        self.select_tool.setChecked(True)

    def _create_tool_button(self, name: str, tooltip: str, icon_text: str) -> QToolButton:
        """Create a toggleable tool button."""
        btn = QToolButton()
        btn.setText(icon_text)
        btn.setToolTip(tooltip)
        btn.setCheckable(True)
        btn.setFixedSize(32, 32)
        btn.clicked.connect(lambda: self._on_tool_clicked(name))
        return btn

    def _create_action_button(self, name: str, tooltip: str, icon_text: str) -> QToolButton:
        """Create a non-toggleable action button."""
        btn = QToolButton()
        btn.setText(icon_text)
        btn.setToolTip(tooltip)
        btn.setCheckable(False)
        btn.setFixedSize(32, 32)

        if name == "undo":
            btn.clicked.connect(self.undo_requested.emit)
        elif name == "redo":
            btn.clicked.connect(self.redo_requested.emit)

        return btn

    def _on_tool_clicked(self, tool_name: str):
        """Handle tool selection."""
        if tool_name == self._active_tool:
            return  # Already active

        # Update active tool
        self._active_tool = tool_name

        # Map tool names to buttons
        tool_buttons = {
            "select": self.select_tool,
            "point": self.point_tool,
            "vector": self.vector_tool,
            "angle": self.angle_tool,
            "projection": self.projection_tool,
            "polygon": self.polygon_tool,
            "transform": self.transform_tool,
            "subspace": self.subspace_tool,
            "area": self.area_tool,
        }

        # Uncheck all buttons
        for btn in tool_buttons.values():
            btn.setChecked(False)

        # Check the active button
        if tool_name in tool_buttons:
            tool_buttons[tool_name].setChecked(True)

        # Emit signal
        self.tool_selected.emit(tool_name)

    def set_active_tool(self, tool: str) -> None:
        """Programmatically set the active tool."""
        if tool == self._active_tool:
            return

        self._active_tool = tool

        # Map tool name to button
        tool_buttons = {
            "select": self.select_tool,
            "point": self.point_tool,
            "vector": self.vector_tool,
            "angle": self.angle_tool,
            "projection": self.projection_tool,
            "polygon": self.polygon_tool,
            "transform": self.transform_tool,
            "subspace": self.subspace_tool,
            "area": self.area_tool,
        }

        # Uncheck all
        for btn in tool_buttons.values():
            btn.setChecked(False)

        # Check the active one
        if tool in tool_buttons:
            tool_buttons[tool].setChecked(True)
            self.tool_selected.emit(tool)

    def set_theme(self, theme: str) -> None:
        """Update toolbar appearance for theme."""
        self._theme = theme
        self._apply_theme()

    def _apply_theme(self) -> None:
        """Apply theme-specific styling."""
        if self._theme == "dark":
            bg_color = "rgba(40, 40, 40, 0.9)"
            text_color = "#e0e0e0"
            hover_color = "rgba(60, 60, 60, 1.0)"
            active_color = "rgba(80, 120, 200, 0.8)"
        else:  # light
            bg_color = "rgba(255, 255, 255, 0.9)"
            text_color = "#303030"
            hover_color = "rgba(240, 240, 240, 1.0)"
            active_color = "rgba(100, 150, 255, 0.8)"

        # Toolbar background
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                border-radius: 4px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }}

            QToolButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                color: {text_color};
                font-size: 16px;
                padding: 4px;
            }}

            QToolButton:hover {{
                background-color: {hover_color};
            }}

            QToolButton:checked {{
                background-color: {active_color};
            }}

            QToolButton:pressed {{
                background-color: {active_color};
            }}
        """)

    def position_in_host(self) -> None:
        """Position toolbar at top-left of parent, 12px from edges."""
        if self.parent():
            self.move(12, 12)
            self.raise_()  # Ensure it's on top

    def get_active_tool(self) -> str:
        """Get the currently active tool name."""
        return self._active_tool
