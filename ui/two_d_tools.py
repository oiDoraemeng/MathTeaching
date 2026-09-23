"""二维画布左上角统一工具栏。"""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPoint, QPropertyAnimation, QRect, QTimer, Qt, Signal
from PySide6.QtWidgets import QBoxLayout, QFrame, QToolButton, QVBoxLayout, QWidget

from models.geometry_2d import LinearKind
from ui.icons import apply_icon, icon_color, retint_icons
from ui.tokens import ThemeName, apply_drop_shadow, apply_rounded_overlay

ToolKind = LinearKind | str


class TwoDGeometryToolbar(QFrame):
    """统一的二维/线性代数工具栏，固定在视口左侧中部，不随焦点窗格移动。"""

    tool_selected = Signal(object)
    function_requested = Signal(object)
    snap_toggled = Signal(bool)
    undo_requested = Signal()
    redo_requested = Signal()

    def __init__(self, parent: QWidget, theme: ThemeName = "light") -> None:
        super().__init__(parent)
        self._active_tool: ToolKind | None = None
        self._theme: ThemeName = theme
        # 几何与线性代数工具共用一个完整工具栏。
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
        self.function_button = self._action_button("function", "函数目录", "functionToolButton")
        self.point_button = self._button("circle-dot", "点工具", "pointToolButton")
        self.annotation_button = self._button("type", "标记", "annotationToolButton")
        self.line_button = self._button("pen-line", "线工具", "lineToolButton")
        self.vector_button = self._button("vector", "向量", "linearVectorToolButton")
        self.addition_button = self._button("plus", "加法", "vectorAdditionToolButton")
        layout.addWidget(self.select_button)
        layout.addWidget(self.function_button)
        layout.addWidget(self.point_button)
        layout.addWidget(self.annotation_button)
        layout.addWidget(self.line_button)
        layout.addWidget(self.vector_button)

        self.point_flyout = QFrame(parent)
        self.point_flyout.setObjectName("twoDPointFlyout")
        apply_drop_shadow(self.point_flyout, "overlay")
        apply_rounded_overlay(self.point_flyout, "md")
        self._point_flyout_animation = QPropertyAnimation(self.point_flyout, b"windowOpacity", self)
        self._point_flyout_animation.setDuration(150)
        self._point_flyout_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        point_flyout_layout = QVBoxLayout(self.point_flyout)
        point_flyout_layout.setContentsMargins(4, 4, 4, 4)
        point_flyout_layout.setSpacing(4)
        self.point_buttons: dict[str, QToolButton] = {
            "point": self._button("circle-dot", "点", "plainPointToolButton"),
            "midpoint": self._button("between-horizontal-start", "中点", "midpointToolButton"),
            "intersection": self._button("badge-x", "交点", "intersectionPointToolButton"),
        }
        for button in self.point_buttons.values():
            point_flyout_layout.addWidget(button)
            button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            button.installEventFilter(self)
        self.point_flyout.hide()

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
        self.line_buttons: dict[str, QToolButton] = {
            "line": self._button("slash", "直线", "lineGeometryButton"),
            "segment": self._button("minus", "线段", "segmentToolButton"),
            "dashed_segment": self._button("minus-dashed", "虚线段", "dashedSegmentToolButton"),
            "ray": self._button("arrow-up-right", "射线", "rayToolButton"),
            # 向量工具已提升为线性代数模式的一级入口。
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
            self.addition_button,
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
        self.function_button.clicked.connect(
            lambda: self.function_requested.emit(
                self.function_button.mapToGlobal(QPoint(self.function_button.width() + 8, 0))
            )
        )
        self.point_button.clicked.connect(self._toggle_point_flyout)
        self.annotation_button.clicked.connect(lambda: self._toggle_tool("annotation"))
        self.line_button.clicked.connect(self._toggle_line_flyout)
        self.vector_button.clicked.connect(lambda: self._toggle_tool("vector"))
        self.addition_button.clicked.connect(lambda: self._select_tool("addition"))
        self.angle_button.clicked.connect(lambda: self._select_tool("angle"))
        self.projection_button.clicked.connect(lambda: self._select_tool("projection"))
        self.polygon_button.clicked.connect(lambda: self._select_tool("polygon"))
        self.transform_button.clicked.connect(lambda: self._select_tool("transform"))
        self.subspace_button.clicked.connect(lambda: self._select_tool("subspace"))
        self.area_button.clicked.connect(lambda: self._select_tool("area"))
        for kind, button in self.line_buttons.items():
            button.clicked.connect(lambda _checked=False, value=kind: self._select_tool(value))
        for kind, button in self.point_buttons.items():
            button.clicked.connect(lambda _checked=False, value=kind: self._select_tool(value))
        self.snap_button.toggled.connect(self.snap_toggled)
        self.undo_button.clicked.connect(self.undo_requested)
        self.redo_button.clicked.connect(self.redo_requested)
        self.line_button.installEventFilter(self)
        self.line_flyout.installEventFilter(self)
        self.point_button.installEventFilter(self)
        self.point_flyout.installEventFilter(self)
        self.adjustSize()
        self.line_flyout.adjustSize()
        self.point_flyout.adjustSize()
        self.set_history_state(can_undo=False, can_redo=False)

    def set_active_tool(self, tool: ToolKind | None, *, emit_signal: bool = False) -> None:
        self._active_tool = tool
        self.select_button.setChecked(tool == "select")
        self.point_button.setChecked(tool in self.point_buttons)
        self.annotation_button.setChecked(tool == "annotation")
        self.line_button.setChecked(tool in self.line_buttons)
        self.vector_button.setChecked(tool == "vector")
        self.addition_button.setChecked(tool == "addition")
        self.angle_button.setChecked(tool == "angle")
        self.projection_button.setChecked(tool == "projection")
        self.polygon_button.setChecked(tool == "polygon")
        self.transform_button.setChecked(tool == "transform")
        self.subspace_button.setChecked(tool == "subspace")
        self.area_button.setChecked(tool == "area")
        for kind, button in self.line_buttons.items():
            button.setChecked(tool == kind)
        for kind, button in self.point_buttons.items():
            button.setChecked(tool == kind)
        if emit_signal:
            self.tool_selected.emit(tool)

    def set_linear_algebra_mode(self, _enabled: bool = True) -> None:
        """Compatibility hook; the visible toolbar is always fully expanded."""
        self._linear_algebra_mode = True
        # 工具栏始终纵向显示；保留 `_enabled` 以兼容旧接口。
        self._layout.setDirection(QBoxLayout.Direction.TopToBottom)
        self.vector_button.setVisible(self._linear_algebra_mode)
        for button in self._linear_algebra_buttons[1:]:
            button.setVisible(self._linear_algebra_mode)
        if not self._linear_algebra_mode:
            self.set_active_tool(
                self._active_tool
                if self._active_tool in {"select", "point", "annotation", "line", "segment", "dashed_segment", "ray", "vector"}
                else None
            )
        self.adjustSize()
        self.line_flyout.hide()
        self.point_flyout.hide()

    def is_snap_enabled(self) -> bool:
        return self.snap_button.isChecked()

    def is_linear_algebra_mode(self) -> bool:
        return self._linear_algebra_mode

    def set_theme(self, theme: ThemeName) -> None:
        """Re-tint icons so the toolbar stays legible after a theme switch."""
        self._theme = theme
        apply_drop_shadow(self, "overlay", theme)
        apply_drop_shadow(self.line_flyout, "overlay", theme)
        apply_drop_shadow(self.point_flyout, "overlay", theme)
        retint_icons(self, theme)
        retint_icons(self.line_flyout, theme)
        retint_icons(self.point_flyout, theme)

    def set_history_state(self, *, can_undo: bool, can_redo: bool) -> None:
        self.undo_button.setEnabled(can_undo)
        self.redo_button.setEnabled(can_redo)

    def position_in_host(self, host_rect: QRect | None = None) -> None:
        """Place this toolbar at the left centre of the viewport host.

        The toolbar is anchored to the whole viewport, so switching the focused
        scene pane never moves it.
        """
        parent = self.parentWidget()
        if parent is None:
            return
        self.adjustSize()
        target = host_rect if host_rect is not None else parent.rect()
        self.move(
            target.x() + 12,
            target.y() + max(8, (target.height() - self.height()) // 2),
        )
        if self.line_flyout.isVisible():
            self._position_flyout()
        if self.point_flyout.isVisible():
            self._position_point_flyout()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.point_button or watched is self.point_flyout or watched in self.point_buttons.values():
            if event.type() == QEvent.Type.Enter:
                self._show_point_flyout()
            elif event.type() == QEvent.Type.Leave:
                QTimer.singleShot(90, self._hide_point_flyout_if_unhovered)
            elif watched in self.point_buttons.values() and event.type() == QEvent.Type.KeyPress:
                buttons = list(self.point_buttons.values())
                index = buttons.index(watched)
                key = event.key()
                if key in (Qt.Key.Key_Up, Qt.Key.Key_Left, Qt.Key.Key_Down, Qt.Key.Key_Right):
                    delta = -1 if key in (Qt.Key.Key_Up, Qt.Key.Key_Left) else 1
                    self._focus_point_button((index + delta) % len(buttons))
                    return True
                if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
                    buttons[index].click()
                    return True
                if key == Qt.Key.Key_Escape:
                    self._close_point_flyout()
                    return True
        if (
            hasattr(self, "line_flyout")
            and (
                watched is self.line_button
                or watched is self.line_flyout
                or watched in self.line_buttons.values()
            )
        ):
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

    def _toggle_point_flyout(self) -> None:
        """Toggle the point-tool menu without selecting an abstract tool."""
        if self.point_flyout.isVisible():
            self._close_point_flyout()
            return
        self.point_button.setChecked(self._active_tool in self.point_buttons)
        self._show_point_flyout()
        self._focus_point_button(0)

    def _focus_line_button(self, index: int) -> None:
        buttons = list(self.line_buttons.values())
        if not buttons:
            return
        buttons[index % len(buttons)].setFocus(Qt.FocusReason.OtherFocusReason)

    def _focus_point_button(self, index: int) -> None:
        buttons = list(self.point_buttons.values())
        if buttons:
            buttons[index % len(buttons)].setFocus(Qt.FocusReason.OtherFocusReason)

    def _close_line_flyout(self, return_focus: bool = True) -> None:
        self._flyout_animation.stop()
        self.line_flyout.hide()
        if return_focus:
            self.line_button.setFocus(Qt.FocusReason.OtherFocusReason)

    def _close_point_flyout(self, return_focus: bool = True) -> None:
        self._point_flyout_animation.stop()
        self.point_flyout.hide()
        if return_focus:
            self.point_button.setFocus(Qt.FocusReason.OtherFocusReason)

    def _select_tool(self, tool: ToolKind | None) -> None:
        if tool is not None and tool == self._active_tool:
            tool = None
        self.set_active_tool(tool)
        self.tool_selected.emit(tool)
        if tool is not None:
            self.line_flyout.hide()
            self.point_flyout.hide()

    def _show_line_flyout(self) -> None:
        if not self.isVisible():
            return
        self.point_flyout.hide()
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
        # 线型菜单在纵向工具栏右侧对齐展开。
        origin = self.mapTo(parent, QPoint(self.width() + 8, self.line_button.y()))
        x = min(max(8, origin.x()), max(8, parent.width() - self.line_flyout.width() - 8))
        y = min(max(8, origin.y()), max(8, parent.height() - self.line_flyout.height() - 8))
        self.line_flyout.move(x, y)

    def _show_point_flyout(self) -> None:
        if not self.isVisible():
            return
        if hasattr(self, "line_flyout"):
            self.line_flyout.hide()
        self._position_point_flyout()
        self.point_flyout.setWindowOpacity(0.0)
        self.point_flyout.show()
        self._point_flyout_animation.stop()
        self._point_flyout_animation.setStartValue(0.0)
        self._point_flyout_animation.setEndValue(1.0)
        self._point_flyout_animation.start()
        self.point_flyout.raise_()

    def _position_point_flyout(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        origin = self.mapTo(parent, QPoint(self.width() + 8, self.point_button.y()))
        x = min(max(8, origin.x()), max(8, parent.width() - self.point_flyout.width() - 8))
        y = min(max(8, origin.y()), max(8, parent.height() - self.point_flyout.height() - 8))
        self.point_flyout.move(x, y)

    def _hide_flyout_if_unhovered(self) -> None:
        concrete_focused = any(button.hasFocus() for button in self.line_buttons.values())
        if (
            not self.line_button.underMouse()
            and not self.line_flyout.underMouse()
            and not self.line_button.hasFocus()
            and not concrete_focused
        ):
            self._close_line_flyout(return_focus=False)

    def _hide_point_flyout_if_unhovered(self) -> None:
        concrete_focused = any(button.hasFocus() for button in self.point_buttons.values())
        if (
            not self.point_button.underMouse()
            and not self.point_flyout.underMouse()
            and not self.point_button.hasFocus()
            and not concrete_focused
        ):
            self._close_point_flyout(return_focus=False)

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
