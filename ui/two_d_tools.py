"""二维画布左侧统一工具栏。"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPoint, QPropertyAnimation, QTimer, Qt, Signal
from PySide6.QtWidgets import QBoxLayout, QFrame, QToolButton, QVBoxLayout, QWidget

from models.geometry_2d import LinearKind
from ui.icons import apply_icon, icon_color, retint_icons
from ui.tokens import ThemeName, apply_drop_shadow, apply_rounded_overlay

ToolKind = LinearKind | str


class TwoDGeometryToolbar(QFrame):
    """统一的二维/线性代数工具栏，垂直居中显示在画布左侧。"""

    tool_selected = Signal(object)
    snap_toggled = Signal(bool)
    undo_requested = Signal()
    redo_requested = Signal()

    def __init__(self, parent: QWidget, theme: ThemeName = "light") -> None:
        super().__init__(parent)
        self._active_tool: ToolKind | None = None
        self._theme: ThemeName = theme
        # The toolbar always contains the complete set of geometry and
        # linear-algebra tools.  There is no second toolbar or mode switch in
        # the user interface.
        self._linear_algebra_mode = True
        self.setObjectName("twoDGeometryToolbar")
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        apply_drop_shadow(self, "overlay")
        apply_rounded_overlay(self, "md")
        layout = QBoxLayout(QBoxLayout.Direction.TopToBottom, self)
        self._layout = layout
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self.select_button = self._button("move", "选择/移动", "selectToolButton")
        self.point_button = self._button("circle-dot", "点", "pointToolButton")
        self.line_button = self._button("pen-line", "线工具", "lineToolButton")
        self.vector_button = self._button("vector", "向量", "linearVectorToolButton")
        layout.addWidget(self.select_button)
        layout.addWidget(self.point_button)
        layout.addWidget(self.line_button)
        layout.addWidget(self.vector_button)

        self.line_flyout = QFrame(parent)
        self.line_flyout.setObjectName("twoDLineFlyout")
        apply_drop_shadow(self.line_flyout, "overlay")
        apply_rounded_overlay(self.line_flyout, "md")
        self._flyout_animation = QPropertyAnimation(self.line_flyout, b"windowOpacity", self)
        self._flyout_animation.setDuration(150)
        self._flyout_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        flyout_layout = QVBoxLayout(self.line_flyout)
        flyout_layout.setContentsMargins(4, 4, 4, 4)
        flyout_layout.setSpacing(4)
        self.line_buttons: dict[LinearKind, QToolButton] = {
            "line": self._button("slash", "直线", "lineGeometryButton"),
            "segment": self._button("minus", "线段", "segmentToolButton"),
            "ray": self._button("arrow-up-right", "射线", "rayToolButton"),
            # "vector" removed - now a separate top-level tool in linear algebra mode
        }
        for button in self.line_buttons.values():
            flyout_layout.addWidget(button)
            button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            button.installEventFilter(self)
        self.line_flyout.hide()

        self.angle_button = self._button("angle", "角度测量", "angleToolButton")
        self.projection_button = self._button("corner-down-right", "投影", "projectionToolButton")
        self.polygon_button = self._button("hexagon", "多边形", "polygonToolButton")
        self.transform_button = self._button("grid-2x2", "矩阵变换", "transformToolButton")
        self.subspace_button = self._button("square-dashed", "子空间", "subspaceToolButton")
        self.area_button = self._button("square", "有向面积", "areaToolButton")
        self._linear_algebra_buttons = (
            self.vector_button,
            self.angle_button,
            self.projection_button,
            self.polygon_button,
            self.transform_button,
            self.subspace_button,
            self.area_button,
        )
        for button in self._linear_algebra_buttons[1:]:
            layout.addWidget(button)

        layout.addSpacing(8)
        self.snap_button = self._button("grid-3x3", "吸附到网格", "snapToggleButton")
        self.snap_button.setChecked(False)
        layout.addWidget(self.snap_button)

        self.undo_button = self._action_button("undo-2", "撤回", "undoToolButton")
        self.redo_button = self._action_button("redo-2", "反撤回", "redoToolButton")
        layout.addWidget(self.undo_button)
        layout.addWidget(self.redo_button)

        self.select_button.clicked.connect(lambda: self._toggle_tool("select"))
        self.point_button.clicked.connect(lambda: self._toggle_tool("point"))
        self.line_button.clicked.connect(self._toggle_line_flyout)
        self.vector_button.clicked.connect(lambda: self._toggle_tool("vector"))
        self.angle_button.clicked.connect(lambda: self._select_tool("angle"))
        self.projection_button.clicked.connect(lambda: self._select_tool("projection"))
        self.polygon_button.clicked.connect(lambda: self._select_tool("polygon"))
        self.transform_button.clicked.connect(lambda: self._select_tool("transform"))
        self.subspace_button.clicked.connect(lambda: self._select_tool("subspace"))
        self.area_button.clicked.connect(lambda: self._select_tool("area"))
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

    def set_active_tool(self, tool: ToolKind | None, *, emit_signal: bool = False) -> None:
        self._active_tool = tool
        self.select_button.setChecked(tool == "select")
        self.point_button.setChecked(tool == "point")
        self.line_button.setChecked(tool in self.line_buttons)
        self.vector_button.setChecked(tool == "vector")
        self.angle_button.setChecked(tool == "angle")
        self.projection_button.setChecked(tool == "projection")
        self.polygon_button.setChecked(tool == "polygon")
        self.transform_button.setChecked(tool == "transform")
        self.subspace_button.setChecked(tool == "subspace")
        self.area_button.setChecked(tool == "area")
        for kind, button in self.line_buttons.items():
            button.setChecked(tool == kind)
        if emit_signal:
            self.tool_selected.emit(tool)

    def set_linear_algebra_mode(self, _enabled: bool = True) -> None:
        """Compatibility hook; the visible toolbar is always fully expanded."""
        self._linear_algebra_mode = True
        # The shared geometry toolbar remains vertical in every scene mode.
        # `_enabled` is retained only for integrations that call the former
        # mode-specific API.
        self._layout.setDirection(QBoxLayout.Direction.TopToBottom)
        self.vector_button.setVisible(self._linear_algebra_mode)
        for button in self._linear_algebra_buttons[1:]:
            button.setVisible(self._linear_algebra_mode)
        if not self._linear_algebra_mode:
            self.set_active_tool(
                self._active_tool
                if self._active_tool in {"select", "point", "line", "segment", "ray", "vector"}
                else None
            )
        self.adjustSize()
        self.line_flyout.hide()

    def is_snap_enabled(self) -> bool:
        return self.snap_button.isChecked()

    def is_linear_algebra_mode(self) -> bool:
        return self._linear_algebra_mode

    def set_theme(self, theme: ThemeName) -> None:
        """Re-tint icons so the toolbar stays legible after a theme switch."""
        self._theme = theme
        apply_drop_shadow(self, "overlay", theme)
        apply_drop_shadow(self.line_flyout, "overlay", theme)
        retint_icons(self, theme)
        retint_icons(self.line_flyout, theme)

    def set_history_state(self, *, can_undo: bool, can_redo: bool) -> None:
        self.undo_button.setEnabled(can_undo)
        self.redo_button.setEnabled(can_redo)

    def position_in_host(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        self.adjustSize()
        x = 12
        y = max(8, (parent.height() - self.height()) // 2)
        self.move(x, y)
        if self.line_flyout.isVisible():
            self._position_flyout()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.line_button or watched is self.line_flyout or watched in self.line_buttons.values():
            if event.type() == QEvent.Type.Enter:
                self._show_line_flyout()
            elif event.type() == QEvent.Type.Leave:
                QTimer.singleShot(90, self._hide_flyout_if_unhovered)
            elif watched in self.line_buttons.values() and event.type() == QEvent.Type.KeyPress:
                buttons = list(self.line_buttons.values())
                index = buttons.index(watched)
                key = event.key()
                if key in (Qt.Key.Key_Up, Qt.Key.Key_Left, Qt.Key.Key_Down, Qt.Key.Key_Right):
                    delta = -1 if key in (Qt.Key.Key_Up, Qt.Key.Key_Left) else 1
                    self._focus_line_button((index + delta) % len(buttons))
                    return True
                if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
                    buttons[index].click()
                    return True
                if key == Qt.Key.Key_Escape:
                    self._close_line_flyout()
                    return True
        return super().eventFilter(watched, event)

    def _toggle_tool(self, tool: ToolKind) -> None:
        self._select_tool(None if self._active_tool == tool else tool)

    def _toggle_line_flyout(self) -> None:
        """Toggle the concrete line-tool menu without selecting an abstract tool."""
        if self.line_flyout.isVisible():
            self._close_line_flyout()
            return
        self.line_button.setChecked(self._active_tool in self.line_buttons)
        self._show_line_flyout()
        self._focus_line_button(0)

    def _focus_line_button(self, index: int) -> None:
        buttons = list(self.line_buttons.values())
        if not buttons:
            return
        buttons[index % len(buttons)].setFocus(Qt.FocusReason.OtherFocusReason)

    def _close_line_flyout(self, return_focus: bool = True) -> None:
        self._flyout_animation.stop()
        self.line_flyout.hide()
        if return_focus:
            self.line_button.setFocus(Qt.FocusReason.OtherFocusReason)

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
        self.line_flyout.setWindowOpacity(0.0)
        self.line_flyout.show()
        self._flyout_animation.stop()
        self._flyout_animation.setStartValue(0.0)
        self._flyout_animation.setEndValue(1.0)
        self._flyout_animation.start()
        self.line_flyout.raise_()

    def _position_flyout(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        # The toolbar is vertical, so open the concrete line choices to its
        # right and align them with the line button rather than below it.
        origin = self.mapTo(parent, QPoint(self.width() + 8, self.line_button.y()))
        x = min(max(8, origin.x()), max(8, parent.width() - self.line_flyout.width() - 8))
        y = min(max(8, origin.y()), max(8, parent.height() - self.line_flyout.height() - 8))
        self.line_flyout.move(x, y)

    def _hide_flyout_if_unhovered(self) -> None:
        concrete_focused = any(button.hasFocus() for button in self.line_buttons.values())
        if (
            not self.line_button.underMouse()
            and not self.line_flyout.underMouse()
            and not self.line_button.hasFocus()
            and not concrete_focused
        ):
            self._close_line_flyout(return_focus=False)

    def _button(self, icon_name: str, tooltip: str, object_name: str) -> QToolButton:
        button = QToolButton()
        button.setObjectName(object_name)
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)
        button.setCheckable(True)
        apply_icon(button, icon_name, icon_color(self._theme), icon_size=16, hit_size=36)
        return button

    def _action_button(self, icon_name: str, tooltip: str, object_name: str) -> QToolButton:
        button = QToolButton()
        button.setObjectName(object_name)
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)
        apply_icon(button, icon_name, icon_color(self._theme), icon_size=16, hit_size=36)
        return button
