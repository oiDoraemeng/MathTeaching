"""独立的二维讲案例窗格。

本模块只消费已经通过 ``SceneCommandService`` 校验的教学计划；它不接受
模型文本或任意绘图代码。每个窗格拥有自己的 QtInteractor、相机和几何
控制器，因此切换窗格焦点不会隐藏其他案例。
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget
from pyvistaqt import QtInteractor

from models.geometry_2d import Annotation2D, Linear2D, Point2D
from models.scene_mode import SceneAppearance
from rendering.geometry_scene import GeometrySceneController
from rendering.ticks import ViewportBounds, visible_2d_bounds
from rendering.two_d_scene import TwoDGuides, configure_2d_camera
from services.scene_commands import CommandPlan, SceneCommandService
from ui.scene_pane_widget import PaneChrome


PANE_COUNTS = (1, 2, 3, 4)
PANE_LAYOUTS: dict[int, tuple[int, int]] = {
    1: (1, 1),
    2: (1, 2),
    3: (2, 2),
    4: (2, 2),
}


def case_pane_layout(count: int) -> tuple[int, int]:
    """Return the bounded row/column layout for one to four panes."""

    try:
        return PANE_LAYOUTS[int(count)]
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("案例窗格数量必须是 1、2、3 或 4。") from error


def case_pane_placement(count: int, index: int) -> tuple[int, int, int, int]:
    """Return row, column, row span and column span for one visible pane."""

    placements = {
        1: ((0, 0, 1, 1),),
        2: ((0, 0, 1, 1), (0, 1, 1, 1)),
        3: ((0, 0, 2, 1), (0, 1, 1, 1), (1, 1, 1, 1)),
        4: ((0, 0, 1, 1), (0, 1, 1, 1), (1, 0, 1, 1), (1, 1, 1, 1)),
    }
    try:
        return placements[int(count)][int(index)]
    except (IndexError, KeyError, TypeError, ValueError) as error:
        raise ValueError("案例窗格位置无效。") from error


def _operation_visible(operation: Mapping[str, Any], controlled: set[str], visible: set[str]) -> bool:
    alias = operation.get("alias")
    if not isinstance(alias, str):
        return True
    if alias == "cap__polygon":
        # 能力覆盖图形不是某个案例的证据，避免它在多个窗格中重复出现。
        return False
    return alias not in controlled or alias in visible


def case_plan(compiled: Any, stage_id: str) -> CommandPlan:
    """Build a validated, stage-filtered plan for one independent pane."""

    from linear_algebra.visualizations.compiler import storyboard_visibility

    controlled_aliases, visible_aliases = storyboard_visibility(compiled, stage_id)
    controlled = set(controlled_aliases)
    visible = set(visible_aliases)
    operations = tuple(
        dict(operation)
        for operation in compiled.plan.operations
        if _operation_visible(operation, controlled, visible)
    )
    plan = CommandPlan(
        scene=compiled.plan.scene,
        summary=compiled.plan.summary,
        operations=operations,
    )
    validation = SceneCommandService().validate(plan)
    if not validation.valid:
        raise ValueError("；".join(validation.messages))
    return CommandPlan(scene=plan.scene, summary=plan.summary, operations=validation.expanded_operations)


class TeachingCasePane(PaneChrome):
    """One independently camera-controlled 2D case viewport."""

    focused = Signal(str, str)

    def __init__(self, case: Any, compiled: Any, parent: QFrame | None = None) -> None:
        content = QWidget(parent)
        super().__init__(str(getattr(case, "purpose", "案例")), content=content, parent=parent)
        self.case = case
        self.compiled = compiled
        self.setObjectName("teachingCasePane")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._selected = False

        layout = QVBoxLayout(content)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        self.plotter = QtInteractor(self)
        self.plotter.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.plotter.interactor.setMouseTracking(True)
        self.plotter.interactor.installEventFilter(self)
        iren = getattr(self.plotter, "iren", None)
        add_observer = getattr(iren, "add_observer", None)
        if callable(add_observer):
            add_observer("InteractionEvent", lambda *_args: self._sync_viewport_bounds())
            add_observer("EndInteractionEvent", lambda *_args: self._sync_viewport_bounds())
        layout.addWidget(self.plotter.interactor, 1)

        # Bounds are initialized before the renderer has a valid size, then
        # replaced from the camera immediately during the first render.
        self.bounds = ViewportBounds((-1.0, 1.0), (-1.0, 1.0))
        self.guides = TwoDGuides(self.plotter)
        self.geometry = GeometrySceneController(self.plotter, self.bounds)
        self._render_case()

    def set_selected(self, selected: bool) -> None:
        self._selected = bool(selected)
        self.setProperty("selected", self._selected)
        self.style().unpolish(self)
        self.style().polish(self)

    def eventFilter(self, watched: object, event: QEvent) -> bool:  # noqa: N802
        if watched is self.plotter.interactor and event.type() == QEvent.Type.MouseButtonPress:
            self.setFocus(Qt.FocusReason.MouseFocusReason)
            self.focused.emit(str(getattr(self.case, "id", "")), self._stage_id())
        if watched is self.plotter.interactor and event.type() in (
            QEvent.Type.MouseMove, QEvent.Type.Resize, QEvent.Type.Wheel
        ):
            self._sync_viewport_bounds()
        return super().eventFilter(watched, event)

    def _stage_id(self) -> str:
        refs = tuple(getattr(self.case, "stage_refs", ()))
        return str(refs[0]) if refs else ""

    def _render_case(self) -> None:
        plan = case_plan(self.compiled, self._stage_id())
        configure_2d_camera(self.plotter)
        self.plotter.set_background(SceneAppearance().background_color("light"))
        self.bounds = self._current_bounds()
        self.guides.render(self.bounds, SceneAppearance(show_grid=True), effective_theme="light")
        points: dict[str, Point2D] = {}
        for operation in plan.operations:
            name = str(operation.get("op", ""))
            alias = str(operation.get("alias", ""))
            if name == "point.upsert":
                coordinates = tuple(float(value) for value in operation["coordinates"])
                point = Point2D(str(operation.get("name", alias)), *coordinates, agent_alias=alias)
                points[alias] = point
                self.geometry.add_point(point)
            elif name == "linear.upsert":
                start = points.get(str(operation.get("start", "")))
                end = points.get(str(operation.get("end", "")))
                if start is None or end is None:
                    continue
                linear = Linear2D(
                    str(operation.get("name", alias)),
                    str(operation.get("kind", "vector")),
                    start.id,
                    end.id,
                    color=str(operation.get("color", "#2777b6")),
                    role=str(operation.get("role", "primary")),
                    label=str(operation.get("label")) if operation.get("label") is not None else None,
                    agent_alias=alias,
                )
                self.geometry.add_linear(linear)
            elif name == "annotation.upsert":
                x, y = (float(value) for value in operation["position"])
                self.geometry.add_annotation(
                    Annotation2D(alias, str(operation.get("text", "")), x, y, agent_alias=alias)
                )
            elif name == "geometry.polygon":
                vertices = tuple(tuple(float(value) for value in point) for point in operation["vertices"])
                self.geometry.add_teaching_polygon(
                    alias,
                    vertices,
                    color=str(operation.get("color", "#5b8def")),
                    opacity=float(operation.get("opacity", 0.24)),
                    outline=bool(operation.get("outline", True)),
                )
        self.plotter.reset_camera()
        configure_2d_camera(self.plotter)
        self.plotter.camera.parallel_scale = max(6.5, float(self.plotter.camera.parallel_scale))
        self._sync_viewport_bounds()
        self.plotter.render()

    def _sync_viewport_bounds(self) -> None:
        """Update geometry and guide extents after camera or viewport changes."""
        try:
            bounds = self._current_bounds()
            self.bounds = bounds
            self.geometry.set_bounds(bounds)
            self.guides.render(bounds, SceneAppearance(show_grid=True), effective_theme="light")
        except (AttributeError, RuntimeError, ValueError):
            return

    def _current_bounds(self) -> ViewportBounds:
        interactor = getattr(self.plotter, "interactor", None)
        width = max(1, int(interactor.width())) if interactor is not None else 1
        height = max(1, int(interactor.height())) if interactor is not None else 1
        camera = self.plotter.camera
        focal = tuple(float(value) for value in camera.focal_point)
        return visible_2d_bounds(focal, float(camera.parallel_scale), width / height)

    def close(self) -> None:
        try:
            self.plotter.close()
        finally:
            super().close()


class TeachingCasePaneGrid(QFrame):
    """Container that keeps every selected case visible simultaneously."""

    case_focused = Signal(str, str)
    case_closed = Signal(str)
    layout_rejected = Signal(str)

    def __init__(self, compiled: Any, cases: Iterable[Any], parent: QFrame | None = None) -> None:
        super().__init__(parent)
        self.compiled = compiled
        self.cases = tuple(cases)[:4]
        self.pane_count = 1
        self.selected_case_id = str(getattr(self.cases[0], "id", "")) if self.cases else ""
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(6)
        self.panes: list[TeachingCasePane | QFrame] = []

    def set_pane_count(self, count: int) -> bool:
        try:
            rows, columns = case_pane_layout(count)
        except ValueError as error:
            self.layout_rejected.emit(str(error))
            return False
        self.pane_count = int(count)
        self._clear()
        visible_cases = self.cases[:self.pane_count]
        if self.pane_count == 1:
            selected_case = next((item for item in self.cases if str(getattr(item, "id", "")) == self.selected_case_id), None)
            visible_cases = (selected_case,) if selected_case is not None else self.cases[:1]
        for index in range(self.pane_count):
            row, column, row_span, column_span = case_pane_placement(self.pane_count, index)
            if index < len(visible_cases):
                pane = TeachingCasePane(visible_cases[index], self.compiled, self)
                pane.focused.connect(self._on_pane_focused)
                pane.close_requested.connect(lambda cid=str(getattr(visible_cases[index], "id", "")): self.case_closed.emit(cid))
                pane.set_selected(str(getattr(visible_cases[index], "id", "")) == self.selected_case_id)
            else:
                pane = QFrame(self)
                pane.setObjectName("teachingCasePaneEmpty")
                empty_layout = QVBoxLayout(pane)
                empty_layout.addWidget(QLabel("暂无案例", pane), alignment=Qt.AlignmentFlag.AlignCenter)
            self.panes.append(pane)
            self._layout.addWidget(pane, row, column, row_span, column_span)
        for row in range(rows):
            self._layout.setRowStretch(row, 1)
        for column in range(columns):
            self._layout.setColumnStretch(column, 1)
        return True

    def select_case(self, case_id: str, stage_id: str | None = None, *, emit: bool = True) -> bool:
        if not any(str(getattr(item, "id", "")) == case_id for item in self.cases):
            return False
        if self.pane_count == 1 and self.selected_case_id != case_id:
            self.selected_case_id = case_id
            if not self.set_pane_count(1):
                return False
        pane = next((item for item in self.panes if isinstance(item, TeachingCasePane) and str(getattr(item.case, "id", "")) == case_id), None)
        if pane is None:
            return False
        self.selected_case_id = case_id
        for item in self.panes:
            if isinstance(item, TeachingCasePane):
                item.set_selected(item is pane)
        if emit:
            self.case_focused.emit(case_id, stage_id or pane._stage_id())
        return True

    def _on_pane_focused(self, case_id: str, stage_id: str) -> None:
        self.select_case(case_id, stage_id, emit=True)

    def _clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.close()
                widget.deleteLater()
        self.panes.clear()

    def close(self) -> None:
        self._clear()
        super().close()


__all__ = ["PANE_COUNTS", "PANE_LAYOUTS", "TeachingCasePane", "TeachingCasePaneGrid", "case_pane_layout", "case_pane_placement", "case_plan"]
