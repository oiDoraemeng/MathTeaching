"""独立的二维讲案例窗格。

本模块只消费已经通过 ``SceneCommandService`` 校验的教学计划；它不接受
模型文本或任意绘图代码。每个窗格拥有自己的 QtInteractor、相机和几何
控制器，因此切换窗格焦点不会隐藏其他案例。
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget
from pyvistaqt import QtInteractor

from models.geometry_2d import Annotation2D, Linear2D, Point2D, operation_label
from models.scene_mode import SceneAppearance
from rendering.geometry_scene import GeometrySceneController
from rendering.ticks import ViewportBounds, visible_2d_bounds
from rendering.two_d_scene import TwoDGuides, configure_2d_camera
from services.scene_commands import CommandPlan, SceneCommandService
from ui.scene_pane_widget import PaneChrome
from ui.scene_pane_manager import ScenePaneManager


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


# 编译计划里声明式能力补出的对象统一使用 cap__ 前缀；它们属于整节的证据，
# 不属于任何一个案例步骤。
_CAPABILITY_ALIAS_KEYS = (
    "alias",
    "result_alias",
    "foot_alias",
    "residual_alias",
    "annotation_alias",
    "aliases",
)


def _capability_alias(operation: Mapping[str, Any]) -> bool:
    """Return True when an operation carries capability-evidence aliases."""

    for key in _CAPABILITY_ALIAS_KEYS:
        candidate = operation.get(key)
        values = candidate if isinstance(candidate, (list, tuple)) else (candidate,)
        if any(isinstance(value, str) and value.startswith("cap__") for value in values):
            return True
    return False


def _operation_visible(operation: Mapping[str, Any], controlled: set[str], visible: set[str]) -> bool:
    # 能力覆盖图形不是某个案例的证据，避免它在多个窗格中重复出现。例如向量减法
    # 声明 projection_2d，编译器补出的投影残差正好从 B 连到 A，若不过滤会让每一步
    # 窗格都多出一条把 A、B 连起来的线段。
    if _capability_alias(operation):
        return False
    alias = operation.get("alias")
    if not isinstance(alias, str):
        return True
    return alias not in controlled or alias in visible


@dataclass(frozen=True)
class StoryboardVisibility:
    """The immutable result of selecting one compiled storyboard stage.

    The selector deliberately keeps the stage metadata next to the aliases
    that it controls.  Qt hosts can therefore update captions/highlights after
    applying the visibility mask without re-reading (or interpreting) a
    command plan.
    """

    stage_id: str
    title: str
    caption: str
    layout: str
    controlled_aliases: tuple[str, ...]
    visible_aliases: tuple[str, ...]
    hidden_aliases: tuple[str, ...]
    visible_refs: tuple[str, ...]
    anchor: tuple[float, float]


class StoryboardVisibilityController:
    """Shared, topic-agnostic controller for compiled storyboard stages.

    ``select`` is intentionally pure: resolving an unknown ID raises before
    any host object is touched.  ``apply`` only toggles actors already owned by
    the pane's runtime controllers; it never executes a command or creates a
    pane.  Matrix tableaux, mapping bundles, and quadratic visuals all use
    this same path.
    """

    def __init__(self, compiled: Any) -> None:
        self.compiled = compiled

    def select(self, stage_id: str) -> StoryboardVisibility:
        from linear_algebra.visualizations.compiler import storyboard_visibility

        # Resolve the immutable compiled stage first.  This is the atomic
        # rejection boundary used by both headless tests and the Qt host.
        stage = next((item for item in tuple(getattr(self.compiled, "storyboard", ()))
                      if str(getattr(item, "id", "")) == str(stage_id)), None)
        if stage is None:
            # Keep the canonical diagnostic from the compiler API.
            storyboard_visibility(self.compiled, str(stage_id))
            raise ValueError(f"unknown storyboard stage: {stage_id}")
        controlled, visible = storyboard_visibility(self.compiled, str(stage_id))
        visible_set = set(visible)
        return StoryboardVisibility(
            stage_id=str(stage.id),
            title=str(getattr(stage, "title", "")),
            caption=str(getattr(stage, "caption", "")),
            layout=str(getattr(stage, "layout", "")),
            controlled_aliases=tuple(controlled),
            visible_aliases=tuple(visible),
            hidden_aliases=tuple(alias for alias in controlled if alias not in visible_set),
            visible_refs=tuple(str(value) for value in getattr(stage, "visible_refs", ())),
            anchor=tuple(float(value) for value in getattr(stage, "anchor", ())),
        )

    def apply(self, runtime: Any, stage_id: str, *, render: bool = True) -> StoryboardVisibility:
        """Apply a validated mask to actors in an already materialized pane."""

        selection = self.select(stage_id)
        visible = set(selection.visible_aliases)
        geometry = getattr(runtime, "geometry_controller", None)
        geometry3d = getattr(runtime, "geometry3d_controller", None)
        # All calls happen only after ``select`` succeeds, preserving current
        # visibility when callers pass an unknown stage ID.
        for alias in selection.controlled_aliases:
            is_visible = alias in visible
            if geometry is not None:
                setter = getattr(geometry, "set_agent_alias_visible", None)
                if callable(setter):
                    setter(alias, is_visible)
                setter = getattr(geometry, "set_teaching_visible", None)
                if callable(setter):
                    setter(alias, is_visible)
            if geometry3d is not None:
                setter = getattr(geometry3d, "set_visible", None)
                if callable(setter):
                    setter(alias, is_visible)
        if render:
            renderer = getattr(runtime, "renderer", None)
            render_fn = getattr(renderer, "render", None)
            if callable(render_fn):
                render_fn()
        return selection


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

    def __init__(self, case: Any, compiled: Any, parent: QFrame | None = None, *, pane_id: str | None = None, pane_manager: ScenePaneManager | None = None) -> None:
        content = QWidget(parent)
        super().__init__(str(getattr(case, "purpose", "案例")), content=content, parent=parent)
        self.case = case
        self.compiled = compiled
        self.setObjectName("teachingCasePane")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._selected = False
        self.pane_id, self.pane_manager = pane_id, pane_manager

        layout = QVBoxLayout(content)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        self.plotter = QtInteractor(self)
        if pane_manager is not None and pane_id is not None:
            pane_manager.pane(pane_id).renderer_2d = self.plotter
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
        self.coordinate_transform = None
        self.geometry = GeometrySceneController(self.plotter, self.bounds)
        self._render_case()

    def set_selected(self, selected: bool) -> None:
        self._selected = bool(selected)
        self.setProperty("selected", self._selected)
        self.style().unpolish(self)
        self.style().polish(self)

    def focus_pane(self) -> None:
        if self.pane_manager is not None and self.pane_id is not None:
            self.pane_manager.focus_pane(self.pane_id)
        self.setFocus(Qt.FocusReason.OtherFocusReason)

    def eventFilter(self, watched: object, event: QEvent) -> bool:  # noqa: N802
        if watched is self.plotter.interactor and event.type() == QEvent.Type.MouseButtonPress:
            self.focus_pane()
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
        transform_operation = next(
            (
                operation
                for operation in plan.operations
                if operation.get("op") == "linear_algebra.coordinate_transform"
            ),
            None,
        )
        self.coordinate_transform = (
            tuple(tuple(float(value) for value in row) for row in transform_operation["matrix"])
            if transform_operation is not None
            else None
        )
        configure_2d_camera(self.plotter)
        state = self.pane_manager.pane(self.pane_id) if self.pane_manager and self.pane_id else None
        saved_camera = dict(state.camera_2d) if state is not None else {}
        self.plotter.set_background(SceneAppearance().background_color("light"))
        self.bounds = self._current_bounds()
        self.guides.render(
            self.bounds,
            SceneAppearance(show_grid=True),
            effective_theme="light",
            coordinate_transform=self.coordinate_transform,
        )
        points: dict[str, Point2D] = {}
        grid_aliases: list[str] = []
        for operation in plan.operations:
            name = str(operation.get("op", ""))
            alias = str(operation.get("alias", ""))
            if name == "point.upsert":
                coordinates = tuple(float(value) for value in operation["coordinates"])
                point = Point2D(operation_label(operation), *coordinates, agent_alias=alias)
                points[alias] = point
                self.geometry.add_point(point)
            elif name == "linear.upsert":
                start = points.get(str(operation.get("start", "")))
                end = points.get(str(operation.get("end", "")))
                if start is None or end is None:
                    continue
                linear = Linear2D(
                    operation_label(operation),
                    str(operation.get("kind", "vector")),
                    start.id,
                    end.id,
                    color=str(operation.get("color", "#2777b6")),
                    role=str(operation.get("role", "primary")),
                    # 计划里声明的虚线必须传下去：投影连线、外接矩形等辅助构造
                    # 全靠它，否则案例窗格会把虚线画成实线。
                    style=str(operation.get("style", "solid")),
                    label=str(operation.get("label")) if operation.get("label") is not None else None,
                    agent_alias=alias,
                )
                self.geometry.add_linear(linear)
            elif name == "annotation.upsert":
                x, y = (float(value) for value in operation["position"])
                self.geometry.add_annotation(
                    Annotation2D(
                        alias,
                        str(operation.get("text", "")),
                        x,
                        y,
                        latex=str(operation.get("latex"))
                        if operation.get("latex") is not None
                        else None,
                        agent_alias=alias,
                    )
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
            elif name == "geometry.transformed_grid":
                # 矩阵案例窗格用已有的线性变换图元：同一条命令在这里只画该步
                # 变换后的网格（作为这个窗格自己的坐标系）。多画的那层灰色原始
                # 网格会叠在窗格本来就有的坐标网格上，看起来像悬浮的第二套网格。
                matrix = tuple(
                    tuple(float(value) for value in row) for row in operation["matrix"]
                )
                bounds = tuple(float(value) for value in operation["bounds"])
                self.geometry.add_teaching_transformed_grid(
                    matrix,  # type: ignore[arg-type]
                    bounds,  # type: ignore[arg-type]
                    step=float(operation.get("step", 1.0)),
                    alias=alias or None,
                    color=str(operation.get("color", "#5b8def")),
                    origin=tuple(float(value) for value in operation.get("origin", (0.0, 0.0))),  # type: ignore[arg-type]
                    show_source_grid=False,
                )
                if alias:
                    grid_aliases.append(alias)
            elif name == "geometry.staged_transform":
                # 矩阵变换功能的另一半：若干样本点经过矩阵后落到的位置。
                matrices = tuple(
                    tuple(tuple(float(value) for value in row) for row in matrix)
                    for matrix in operation["matrices"]
                )
                staged_points = tuple(
                    tuple(float(value) for value in point) for point in operation["points"]
                )
                self.geometry.add_teaching_staged_transform(
                    matrices,  # type: ignore[arg-type]
                    staged_points,  # type: ignore[arg-type]
                    tuple(str(value) for value in operation.get("aliases", ())),
                    alias=alias or None,
                    color=str(operation.get("color", "#2777b6")),
                )
        # 网格演员的取样范围覆盖整个视野、变形后更大，若一起参与取景会把相机
        # 拉远。取景时先隐藏它们，取景完成后再显示，由视口负责裁切。
        for grid_alias in grid_aliases:
            self.geometry.set_teaching_visible(grid_alias, False)
        self.plotter.reset_camera()
        configure_2d_camera(self.plotter)
        self.plotter.camera.parallel_scale = max(6.5, float(self.plotter.camera.parallel_scale))
        for grid_alias in grid_aliases:
            self.geometry.set_teaching_visible(grid_alias, True)
        if saved_camera:
            try:
                if saved_camera.get("camera_position") is not None:
                    self.plotter.camera.position = tuple(saved_camera["camera_position"])
                self.plotter.camera.focal_point = tuple(saved_camera.get("focal_point", self.plotter.camera.focal_point))
                if saved_camera.get("view_up") is not None:
                    self.plotter.camera.up = tuple(saved_camera["view_up"])
                self.plotter.camera.parallel_scale = float(saved_camera.get("parallel_scale", self.plotter.camera.parallel_scale))
            except (TypeError, ValueError):
                pass
        if state is not None:
            state.scene_2d = {"case_id": str(getattr(self.case, "id", "")), "stage_id": self._stage_id(),
                              "operations": [dict(op) for op in plan.operations]}
            state.algebra_model = {"case_id": str(getattr(self.case, "id", ""))}
            state.selected_object_ids = list(getattr(state, "selected_object_ids", []))
        self._sync_viewport_bounds()
        self.plotter.render()

    def _sync_viewport_bounds(self) -> None:
        """Update geometry and guide extents after camera or viewport changes."""
        try:
            bounds = self._current_bounds()
            self.bounds = bounds
            if self.pane_manager is not None and self.pane_id is not None:
                state = self.pane_manager.pane(self.pane_id)
                camera = self.plotter.camera
                state.camera_2d = {
                    "camera_position": [float(value) for value in camera.position],
                    "focal_point": [float(value) for value in camera.focal_point],
                    "view_up": [float(value) for value in camera.up],
                    "parallel_scale": float(camera.parallel_scale),
                }
            self.geometry.set_bounds(bounds)
            self.guides.render(
                bounds,
                SceneAppearance(show_grid=True),
                effective_theme="light",
                coordinate_transform=self.coordinate_transform,
            )
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

    def __init__(self, compiled: Any, cases: Iterable[Any], parent: QFrame | None = None, *, pane_manager: ScenePaneManager | None = None) -> None:
        super().__init__(parent)
        self.compiled = compiled
        self.pane_manager = pane_manager
        case_capacity = 4
        if pane_manager is not None:
            user_pane_count = sum(
                pane.source == "user" for pane in pane_manager.panes.values()
            )
            case_capacity = min(
                case_capacity,
                max(1, pane_manager.MAX_RETAINED_PANES - user_pane_count),
            )
        self.cases = tuple(cases)[:case_capacity]
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
                case = visible_cases[index]
                pane_id = self.pane_manager.register_case(str(getattr(case, "id", "")), name=str(getattr(case, "purpose", "案例"))) if self.pane_manager else None
                pane = TeachingCasePane(case, self.compiled, self, pane_id=pane_id, pane_manager=self.pane_manager)
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
        if self.pane_manager is not None:
            ids = [self.pane_manager.register_case(str(getattr(case, "id", ""))) for case in visible_cases]
            if ids:
                self.pane_manager.set_visible_panes(ids)
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
        if self.pane_manager is not None:
            pane_id = self.pane_manager.register_case(case_id)
            if pane_id not in self.pane_manager.visible_pane_ids() and len(self.pane_manager.visible_pane_ids()) < self.pane_manager.MAX_PANES:
                self.pane_manager.set_visible_panes(list(self.pane_manager.visible_pane_ids()) + [pane_id])
            if pane_id in self.pane_manager.visible_pane_ids():
                self.pane_manager.focus_pane(pane_id)
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
                if isinstance(widget, TeachingCasePane) and widget.pane_manager is not None and widget.pane_id is not None:
                    widget._sync_viewport_bounds()
                    try:
                        state = widget.pane_manager.pane(widget.pane_id)
                        state.renderer_2d = None
                    except ValueError:
                        pass
                widget.close()
                widget.deleteLater()
        self.panes.clear()

    def close(self) -> None:
        self._clear()
        super().close()


__all__ = [
    "PANE_COUNTS",
    "PANE_LAYOUTS",
    "StoryboardVisibility",
    "StoryboardVisibilityController",
    "TeachingCasePane",
    "TeachingCasePaneGrid",
    "case_pane_layout",
    "case_pane_placement",
    "case_plan",
]
