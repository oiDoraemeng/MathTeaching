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
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget
from pyvistaqt import QtInteractor

from models.geometry_2d import Annotation2D, Linear2D, Point2D, operation_label
from models.scene_mode import SceneAppearance
from rendering import math_labels
from rendering.geometry_scene import GeometrySceneController
from rendering.ticks import ViewportBounds, visible_2d_bounds
from rendering.two_d_scene import TwoDGuides, configure_2d_camera
from services.scene_commands import CommandPlan, SceneCommandService
from ui.scene_pane_widget import PaneChrome
from ui.scene_pane_manager import ScenePaneManager
from ui.linear_algebra_tools import build_matrix_grid_tool_plan


PANE_COUNTS = (1, 2, 3, 4)
PANE_LAYOUTS: dict[int, tuple[int, int]] = {
    1: (1, 1),
    2: (1, 2),
    3: (2, 2),
    4: (2, 2),
}

_CASE_LABEL_FONT_SIZE = math_labels.CASE_LABEL_FONT_SIZE
_MATRIX_TOOL_CASE_TOPICS = frozenset(
    {
        "ch02.matrix.additive-distributivity",
        "ch02.matrix.transformed-grid",
        "ch02.matrix.composition",
        "ch02.matrix.basis",
        "ch02.matrix.powers",
        "ch04.basis.definition",
        "ch04.linear-map.definition",
        "ch06.basis-change.coordinates",
        "ch06.similarity-transform",
        "ch07.eigen.direction",
        "ch07.characteristic-polynomial",
        "ch07.eigenspace",
        "ch07.diagonalization",
    }
)
_MATRIX_WORKSPACE_CASE_TOPICS = frozenset(
    {
        "ch03.det.basic-properties",
        "ch03.det.multiplicativity",
        "ch03.det.transpose",
    }
)


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


def _toolbar_matrix_grid(
    operation: Mapping[str, Any], *, preserve_color: bool = False,
    grid_range: float | None = None,
) -> dict[str, Any]:
    """Rebuild one lesson grid through the same plan factory as the 2-D toolbar."""

    matrix_value = operation.get("basis_matrix", operation.get("matrix", ()))
    matrix = tuple(
        tuple(float(value) for value in row)
        for row in matrix_value
    )
    bounds = tuple(float(value) for value in operation.get("bounds", ()))
    extent = (
        max(1.0, min(float(grid_range), 100.0))
        if grid_range is not None
        else max((abs(value) for value in bounds), default=5.0)
    )
    alias = str(operation.get("alias", "teaching_matrix"))
    tool_operation = dict(
        build_matrix_grid_tool_plan(matrix, extent, alias).operations[0]  # type: ignore[arg-type]
    )
    # Storyboard visibility is keyed by the compiler's semantic alias.
    tool_operation["alias"] = alias
    if preserve_color and operation.get("color") is not None:
        tool_operation["color"] = str(operation["color"])
    return tool_operation


def _uses_matrix_toolbar_grid(topic_id: str, operation: Mapping[str, Any]) -> bool:
    """Return whether one lesson grid is representable by the matrix tool."""

    if operation.get("op") not in {"geometry.basis_grid", "geometry.transformed_grid"}:
        return False
    if topic_id == "ch04.linear-map.definition":
        # The translation witness is intentionally affine.  A matrix toolbar
        # row for its linear part would incorrectly present T(v)=v+b as A=I.
        origin = operation.get("origin", (0.0, 0.0))
        try:
            return all(abs(float(value)) <= 1e-12 for value in origin)
        except (TypeError, ValueError):
            return False
    return True


def _matrix_case_view_bounds(compiled: Any) -> list[float] | None:
    """Return one shared viewport from toolbar grid ranges and lesson points."""

    coordinates: list[tuple[float, float]] = []
    chapter_six = str(getattr(compiled, "topic_id", "")).startswith("ch06.")
    for operation in compiled.plan.operations:
        if operation.get("op") in {"geometry.basis_grid", "geometry.transformed_grid"}:
            try:
                if chapter_six:
                    # Chapter 6 case grids are rebuilt by the matrix toolbar
                    # with its default range of 5. Fit their transformed
                    # corners, not the compiler's old untransformed +/-6 box.
                    left, right, bottom, top = -5.0, 5.0, -5.0, 5.0
                else:
                    left, right, bottom, top = (
                        float(value) for value in operation["bounds"]
                    )
            except (KeyError, TypeError, ValueError):
                continue
            corners = (
                (left, bottom),
                (left, top),
                (right, bottom),
                (right, top),
            )
            matrix_value = operation.get("basis_matrix", operation.get("matrix"))
            if chapter_six and matrix_value is not None:
                try:
                    ((a, b), (c, d)) = tuple(
                        tuple(float(value) for value in row) for row in matrix_value
                    )
                    origin_x, origin_y = (
                        float(value) for value in operation.get("origin", (0.0, 0.0))
                    )
                except (TypeError, ValueError):
                    continue
                coordinates.extend(
                    (a * x + b * y + origin_x, c * x + d * y + origin_y)
                    for x, y in corners
                )
            else:
                coordinates.extend(corners)
        elif operation.get("op") == "point.upsert":
            try:
                x, y = (float(value) for value in operation["coordinates"])
            except (KeyError, TypeError, ValueError):
                continue
            coordinates.append((x, y))
    if not coordinates:
        return None
    xs = [point[0] for point in coordinates]
    ys = [point[1] for point in coordinates]
    return [min(xs), max(xs), min(ys), max(ys)]


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

        # 先解析不可变阶段，失败时不触碰当前场景。
        stage = next((item for item in tuple(getattr(self.compiled, "storyboard", ()))
                      if str(getattr(item, "id", "")) == str(stage_id)), None)
        if stage is None:
            # 保留编译器返回的标准诊断。
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
        # 阶段选择成功后才修改可见性。
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
    operations = [
        dict(operation)
        for operation in compiled.plan.operations
        if _operation_visible(operation, controlled, visible)
    ]
    topic_id = str(getattr(compiled, "topic_id", ""))
    if topic_id == "ch01.ops.addition" and str(stage_id) == "stage.flow.objects":
        # 第一窗格只展示两个输入向量。即使完整计划中带有合成向量或平行四边形
        # 的关系操作，也不能让第二步的图元泄漏到第一步。
        allowed_aliases = {
            "sem__flow_a__origin",
            "sem__flow_a__end",
            "sem__flow_a",
            "sem__flow_b__origin",
            "sem__flow_b__end",
            "sem__flow_b",
        }
        operations = [
            operation
            for operation in operations
            if operation.get("op") in {"scene.set_mode", "view.fit"}
            or operation.get("alias") in allowed_aliases
        ]
    if topic_id in _MATRIX_WORKSPACE_CASE_TOPICS:
        # 这些案例的网格由宿主现有的矩阵变换工具创建。阶段计划
        # 只保留本节数学对象与取景，避免先画一层教学网格再叠加工具网格。
        operations = [
            operation
            for operation in operations
            if operation.get("op") != "geometry.transformed_grid"
        ]
    if topic_id in _MATRIX_TOOL_CASE_TOPICS:
        is_chapter_seven = topic_id.startswith("ch07.")
        is_chapter_six = topic_id.startswith("ch06.")
        if is_chapter_seven or is_chapter_six:
            # 第六、七章的每个案例窗格只保留当前阶段的对象；端点属于可见向量，
            # 即使它们没有单独列在 storyboard visible_aliases 中也要一并保留。
            def belongs_to_stage(alias: object) -> bool:
                if not isinstance(alias, str):
                    return False
                if alias in visible:
                    return True
                for suffix in ("__origin", "__end"):
                    if alias.endswith(suffix) and alias[: -len(suffix)] in visible:
                        return True
                return False

            operations = [
                operation
                for operation in operations
                if operation.get("op") in {"scene.set_mode", "view.fit"}
                or belongs_to_stage(operation.get("alias"))
            ]
            if is_chapter_seven:
                # The compiled direction stages contain a reference grid and
                # its transformed copy. The matrix toolbar owns one
                # transformed grid; keeping the reference copy would make the
                # algebra pane select A=I instead of the stage matrix.
                transformed_aliases = {
                    str(operation.get("alias"))
                    for operation in operations
                    if operation.get("op") == "geometry.transformed_grid"
                    and str(operation.get("alias", "")).endswith("__transformed")
                }
                if transformed_aliases:
                    operations = [
                        operation
                        for operation in operations
                        if operation.get("op") != "geometry.transformed_grid"
                        or str(operation.get("alias")) in transformed_aliases
                    ]
        operations = [
            _toolbar_matrix_grid(
                operation,
                preserve_color=topic_id == "ch02.matrix.powers",
                grid_range=5.0 if (is_chapter_seven or is_chapter_six) else None,
            )
            if _uses_matrix_toolbar_grid(topic_id, operation)
            else operation
            for operation in operations
        ]
        if topic_id.startswith("ch06."):
            bounds = [-8.0, 8.0, -8.0, 8.0]
            padding = 1.0
        elif topic_id.startswith("ch07."):
            bounds = [-5.0, 5.0, -5.0, 5.0]
            padding = 1.15
        else:
            bounds = _matrix_case_view_bounds(compiled) if topic_id != "ch02.matrix.powers" else None
            padding = 1.15
        if bounds is not None:
            fit = {"op": "view.fit", "padding": padding, "bounds": bounds}
            operations = [
                fit if operation.get("op") == "view.fit" else operation
                for operation in operations
            ]
            if not any(operation.get("op") == "view.fit" for operation in operations):
                operations.append(fit)
    plan = CommandPlan(
        scene=compiled.plan.scene,
        summary=compiled.plan.summary,
        operations=tuple(operations),
    )
    validation = SceneCommandService().validate(plan)
    if not validation.valid:
        raise ValueError("；".join(validation.messages))
    return CommandPlan(scene=plan.scene, summary=plan.summary, operations=validation.expanded_operations)


def _apply_planned_view_fit(plotter: Any, operations: Iterable[Mapping[str, Any]]) -> bool:
    """Apply an explicit 2D ``view.fit`` using the pane's real aspect ratio."""

    fit = next((operation for operation in operations if operation.get("op") == "view.fit"), None)
    if fit is None or len(fit.get("bounds", ())) != 4:
        return False
    try:
        left, right, bottom, top = (float(value) for value in fit["bounds"])
        padding = float(fit.get("padding", 1.15))
    except (TypeError, ValueError):
        return False
    if right <= left or top <= bottom or padding <= 0.0:
        return False
    interactor = plotter.interactor
    aspect = max(1, int(interactor.width())) / max(1, int(interactor.height()))
    plotter.camera.focal_point = ((left + right) / 2, (bottom + top) / 2, 0.0)
    plotter.camera.parallel_scale = max(
        (top - bottom) / 2,
        (right - left) / (2 * aspect),
    ) * padding
    return True


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
        self._dragging_label: tuple[str, str] | None = None
        self._annotation_positions: dict[str, tuple[float, float]] = {}
        self._linear_label_offsets: dict[str, tuple[float, float]] = {}

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

        # 首次渲染时再用有效相机范围替换初值。
        self.bounds = ViewportBounds((-1.0, 1.0), (-1.0, 1.0))
        self.guides = TwoDGuides(self.plotter)
        self.coordinate_transform = None
        self.geometry = GeometrySceneController(
            self.plotter,
            self.bounds,
            annotation_font_size=_CASE_LABEL_FONT_SIZE,
        )
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
        if watched is self.plotter.interactor:
            if event.type() == QEvent.Type.MouseButtonPress and isinstance(event, QMouseEvent):
                self.focus_pane()
                self.focused.emit(str(getattr(self.case, "id", "")), self._stage_id())
                if self._begin_label_drag(event):
                    return True
            if event.type() == QEvent.Type.MouseMove:
                self._sync_viewport_bounds()
                if isinstance(event, QMouseEvent) and self._handle_label_mouse_move(event):
                    return True
            if event.type() == QEvent.Type.MouseButtonRelease and isinstance(event, QMouseEvent):
                if self._finish_label_drag(event):
                    return True
            if event.type() == QEvent.Type.Leave:
                self._clear_label_hover()
            if event.type() in (QEvent.Type.Resize, QEvent.Type.Wheel):
                self._sync_viewport_bounds()
        return super().eventFilter(watched, event)

    def _begin_label_drag(self, event: QMouseEvent) -> bool:
        if event.button() != Qt.MouseButton.LeftButton:
            return False
        target = self._label_target_at(event)
        if target is None:
            return False
        self._dragging_label = target
        self.geometry.set_hover(target[1])
        self._set_label_cursor(Qt.CursorShape.ClosedHandCursor)
        self.plotter.render()
        event.accept()
        return True

    def _handle_label_mouse_move(self, event: QMouseEvent) -> bool:
        if self._dragging_label is not None:
            coordinates = self._viewport_to_world(event)
            if coordinates is None:
                return True
            kind, object_id = self._dragging_label
            if kind == "annotation":
                self.geometry.move_annotation(object_id, *coordinates)
            else:
                self.geometry.move_linear_label(object_id, *coordinates)
            self._save_label_positions()
            self.plotter.render()
            event.accept()
            return True
        target = self._label_target_at(event)
        target_id = target[1] if target is not None else None
        if self.geometry.set_hover(target_id):
            self.plotter.render()
        self._set_label_cursor(
            Qt.CursorShape.OpenHandCursor if target is not None else Qt.CursorShape.ArrowCursor
        )
        return False

    def _finish_label_drag(self, event: QMouseEvent) -> bool:
        if self._dragging_label is None:
            return False
        self._dragging_label = None
        target = self._label_target_at(event)
        target_id = target[1] if target is not None else None
        if self.geometry.set_hover(target_id):
            self.plotter.render()
        self._set_label_cursor(
            Qt.CursorShape.OpenHandCursor if target is not None else Qt.CursorShape.ArrowCursor
        )
        event.accept()
        return True

    def _clear_label_hover(self) -> None:
        if self._dragging_label is not None:
            return
        if self.geometry.set_hover(None):
            self.plotter.render()
        self._set_label_cursor(Qt.CursorShape.ArrowCursor)

    def _label_target_at(self, event: QMouseEvent) -> tuple[str, str] | None:
        coordinates = self._viewport_to_world(event)
        if coordinates is None:
            return None
        return self.geometry.hit_test_label(
            *coordinates,
            self._label_hit_tolerance(),
            editable_annotations_only=True,
        )

    def _label_hit_tolerance(self) -> float:
        return max(self.bounds.x_span, self.bounds.y_span) * 0.025

    def _viewport_to_world(self, event: QMouseEvent) -> tuple[float, float] | None:
        interactor = getattr(self.plotter, "interactor", None)
        if interactor is None:
            return None
        width = max(1, int(interactor.width()))
        height = max(1, int(interactor.height()))
        x = float(event.position().x())
        y = float(event.position().y())
        if not 0.0 <= x <= width or not 0.0 <= y <= height:
            return None
        bounds = self._current_bounds()
        return (
            bounds.x_range[0] + x / width * bounds.x_span,
            bounds.y_range[1] - y / height * bounds.y_span,
        )

    def _set_label_cursor(self, cursor: Qt.CursorShape) -> None:
        interactor = getattr(self.plotter, "interactor", None)
        set_cursor = getattr(interactor, "setCursor", None)
        if callable(set_cursor):
            set_cursor(cursor)

    def _load_label_positions(self, state: Any | None) -> None:
        self._annotation_positions = {}
        self._linear_label_offsets = {}
        stored = getattr(state, "scene_2d", {}).get("label_positions", {})
        if not isinstance(stored, Mapping):
            return
        for key, target in (
            ("annotations", self._annotation_positions),
            ("linears", self._linear_label_offsets),
        ):
            records = stored.get(key, {})
            if not isinstance(records, Mapping):
                continue
            for alias, position in records.items():
                try:
                    x, y = float(position[0]), float(position[1])  # type: ignore[index]
                except (IndexError, TypeError, ValueError):
                    continue
                target[str(alias)] = (x, y)

    def _save_label_positions(self) -> None:
        for annotation in self.geometry.annotations.values():
            if annotation.agent_alias:
                self._annotation_positions[annotation.agent_alias] = (annotation.x, annotation.y)
        for linear in self.geometry.linears.values():
            if linear.agent_alias and linear.label:
                self._linear_label_offsets[linear.agent_alias] = (
                    linear.label_offset_x,
                    linear.label_offset_y,
                )
        if self.pane_manager is None or self.pane_id is None:
            return
        state = self.pane_manager.pane(self.pane_id)
        state.scene_2d["label_positions"] = {
            "annotations": {
                alias: [position[0], position[1]]
                for alias, position in self._annotation_positions.items()
            },
            "linears": {
                alias: [position[0], position[1]]
                for alias, position in self._linear_label_offsets.items()
            },
        }

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
        self._load_label_positions(state)
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
                    label_offset_x=self._linear_label_offsets.get(alias, (0.0, 0.0))[0],
                    label_offset_y=self._linear_label_offsets.get(alias, (0.0, 0.0))[1],
                    agent_alias=alias,
                )
                self.geometry.add_linear(linear)
            elif name == "annotation.upsert":
                x, y = (float(value) for value in operation["position"])
                x, y = self._annotation_positions.get(alias, (x, y))
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
                        editable=True,
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
            elif name == "geometry.projection":
                # 案例窗格也要执行投影图元；否则编译计划中的投影线、垂线和垂足
                # 只会出现在主画布，数学案例自己的二维窗格会只剩输入向量。
                self.geometry.add_teaching_projection(
                    tuple(float(value) for value in operation["vector"]),  # type: ignore[arg-type]
                    tuple(float(value) for value in operation["direction"]),  # type: ignore[arg-type]
                    result_alias=str(operation["result_alias"]),
                    foot_alias=str(operation["foot_alias"]),
                    residual_alias=str(operation["residual_alias"]),
                    alias=alias or None,
                    origin=tuple(float(value) for value in operation.get("origin", (0.0, 0.0))),  # type: ignore[arg-type]
                    color=str(operation.get("color", "#2777b6")),
                    style=str(operation.get("style", "solid")),
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
        topic_id = str(getattr(self.compiled, "topic_id", ""))
        if topic_id in {
            "ch01.ops.addition",
            "ch02.matrix.powers",
            # 4.3 的计划已经声明了 [-5, 5]×[-5, 5] 的共享视窗；此前
            # 案例窗格走通用 reset_camera，导致窄窗格里端点显得过近。
            "ch04.basis.definition",
        }:
            _apply_planned_view_fit(self.plotter, plan.operations)
        elif topic_id in _MATRIX_TOOL_CASE_TOPICS:
            # 矩阵案例统一使用计划中的共享边界，避免按少量端点 reset_camera
            # 后在窄窗格里把绘图区拉得过近。
            _apply_planned_view_fit(self.plotter, plan.operations)
        else:
            self.plotter.camera.parallel_scale = max(
                6.5,
                float(self.plotter.camera.parallel_scale),
            )
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
        self._save_label_positions()
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
