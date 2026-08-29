"""二维右侧点线工具栏。"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QPoint, QTimer, Qt, Signal
from PySide6.QtWidgets import QFrame, QToolButton, QVBoxLayout, QWidget

from models.geometry_2d import LinearKind
from ui.icons import apply_icon
from ui.tokens import apply_drop_shadow

ToolKind = LinearKind | str


class TwoDGeometryToolbar(QFrame):
    """提供选择、点工具及悬浮展开的线工具组，并含网格吸附开关。"""

    tool_selected = Signal(object)
    snap_toggled = Signal(bool)
    undo_requested = Signal()
    redo_requested = Signal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._active_tool: ToolKind | None = None
        self.setObjectName("twoDGeometryToolbar")
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        apply_drop_shadow(self, "overlay")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self.select_button = self._button("move", "选择/移动", "selectToolButton")
        self.point_button = self._button("circle-dot", "点", "pointToolButton")
        self.line_button = self._button("slash", "线工具", "lineToolButton")
        layout.addWidget(self.select_button)
        layout.addWidget(self.point_button)
        layout.addWidget(self.line_button)

        self.snap_button = self._button("grid-3x3", "吸附到网格", "snapToggleButton")
        self.snap_button.setChecked(False)
        layout.addWidget(self.snap_button)

        self.undo_button = self._action_button("undo-2", "撤回", "undoToolButton")
        self.redo_button = self._action_button("redo-2", "反撤回", "redoToolButton")
        layout.addWidget(self.undo_button)
        layout.addWidget(self.redo_button)

        self.line_flyout = QFrame(parent)
        self.line_flyout.setObjectName("twoDLineFlyout")
        apply_drop_shadow(self.line_flyout, "overlay")
        flyout_layout = QVBoxLayout(self.line_flyout)
        flyout_layout.setContentsMargins(4, 4, 4, 4)
        flyout_layout.setSpacing(4)
        self.line_buttons: dict[LinearKind, QToolButton] = {
            "line": self._button("slash", "直线", "lineGeometryButton"),
            "segment": self._button("minus", "线段", "segmentToolButton"),
            "ray": self._button("arrow-up-right", "射线", "rayToolButton"),
            "vector": self._button("arrow-up-right", "向量", "vectorToolButton"),
        }
        for button in self.line_buttons.values():
            flyout_layout.addWidget(button)
            button.installEventFilter(self)
        self.line_flyout.hide()

        self.select_button.clicked.connect(lambda: self._toggle_tool("select"))
        self.point_button.clicked.connect(lambda: self._toggle_tool("point"))
        self.line_button.clicked.connect(lambda: self._toggle_tool("line"))
        for kind, button in self.line_buttons.items():
            button.clicked.connect(lambda _checked=False, value=kind: self._select_tool(value))
        self.snap_button.toggled.connect(self.snap_toggled)
        self.undo_button.clicked.connect(self.undo_requested)
        self.redo_button.clicked.connect(self.redo_requested)
        self.line_button.installEventFilter(self)
        self.line_flyout.installEventFilter(self)
        self.adjustSize()
        self.line_flyout.adjustSize()
        self.set_history_state(can_undo=False, can_redo=False)

    def set_active_tool(self, tool: ToolKind | None) -> None:
        self._active_tool = tool
        self.select_button.setChecked(tool == "select")
        self.point_button.setChecked(tool == "point")
        self.line_button.setChecked(tool in self.line_buttons)
        for kind, button in self.line_buttons.items():
            button.setChecked(tool == kind)

    def is_snap_enabled(self) -> bool:
        return self.snap_button.isChecked()

    def set_history_state(self, *, can_undo: bool, can_redo: bool) -> None:
        self.undo_button.setEnabled(can_undo)
        self.redo_button.setEnabled(can_redo)

    def position_in_host(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        self.move(
            max(8, parent.width() - self.width() - 12),
            max(12, (parent.height() - self.height()) // 2),
        )
        if self.line_flyout.isVisible():
            self._position_flyout()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.line_button or watched is self.line_flyout or watched in self.line_buttons.values():
            if event.type() == QEvent.Type.Enter:
                self._show_line_flyout()
            elif event.type() == QEvent.Type.Leave:
                QTimer.singleShot(90, self._hide_flyout_if_unhovered)
        return super().eventFilter(watched, event)

    def _toggle_tool(self, tool: ToolKind) -> None:
        self._select_tool(None if self._active_tool == tool else tool)

    def _select_tool(self, tool: ToolKind | None) -> None:
        if tool is not None and tool == self._active_tool:
            tool = None
        self.set_active_tool(tool)
        self.tool_selected.emit(tool)
        if tool is not None:
            self.line_flyout.hide()

    def _show_line_flyout(self) -> None:
        if not self.isVisible():
            return
        self._position_flyout()
        self.line_flyout.show()
        self.line_flyout.raise_()

    def _position_flyout(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        origin = self.mapTo(
            parent,
            QPoint(-self.line_flyout.width() - 8, self.line_button.y()),
        )
        self.line_flyout.move(max(8, origin.x()), max(8, origin.y()))

    def _hide_flyout_if_unhovered(self) -> None:
        if not self.line_button.underMouse() and not self.line_flyout.underMouse():
            self.line_flyout.hide()

    @staticmethod
    def _button(icon_name: str, tooltip: str, object_name: str) -> QToolButton:
        button = QToolButton()
        button.setObjectName(object_name)
        button.setToolTip(tooltip)
        button.setCheckable(True)
        apply_icon(button, icon_name, "#3f4c5c", icon_size=16, hit_size=36)
        return button

    @staticmethod
    def _action_button(icon_name: str, tooltip: str, object_name: str) -> QToolButton:
        button = QToolButton()
        button.setObjectName(object_name)
        button.setToolTip(tooltip)
        apply_icon(button, icon_name, "#3f4c5c", icon_size=16, hit_size=36)
        return button
