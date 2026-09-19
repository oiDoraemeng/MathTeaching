"""二维点和线类对象的增量演员管理，含选中/悬浮高亮与命中测试。"""

from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterable, Iterator
from math import acos, atan2, cos, hypot, pi, sin

import numpy as np
import pyvista as pv

from models.geometry_2d import Annotation2D, Linear2D, LinearKind, LinearLabelSide, Point2D, format_number
from rendering import math_labels
from rendering.ticks import ViewportBounds

_DRAFT_ACTOR = "geometry:draft"
_LABEL_ACTOR = "geometry:labels"
_ANNOTATION_ACTOR = "geometry:annotations"

_HOVER_HALO_COLOR = "#f0c674"
_SELECTED_HALO_COLOR = "#8ab4f8"
# 教学标注字号，同时用于文本排版度量；与所有案例标签共用统一入口。
_ANNOTATION_FONT_SIZE = math_labels.CASE_LABEL_FONT_SIZE
# 悬浮/选中时线宽的放大量。
_LINE_HALO_WIDTH = 7.0
_POINT_SIZE = 11.0
_POINT_HALO_SIZE = 24.0
# 虚线节距按视口跨度的比例取值。同一窗格里所有虚线共用同一个节距，长短不同的
# 虚线因此疏密一致；缩放时只改变它的世界尺寸，屏幕上的疏密保持不变。
# 调小 = 虚线更密，调大 = 更疏。
_DASH_LENGTH_RATIO = 0.012
# 每段虚线在自身节距里占的比例：0.62 表示约六成实线、四成间隙。
_DASH_DUTY = 0.62


def linear_mesh(
    kind: LinearKind,
    start: Point2D | tuple[float, float],
    end: Point2D | tuple[float, float],
    bounds: ViewportBounds,
    *,
    style: str = "solid",
) -> pv.PolyData:
    """生成适合当前视口的直线、线段、射线或向量网格。

    向量在末端附带一个填充三角形箭头（作为面单元），其余类型仅包含线段。
    """
    start_xy = _coordinates(start)
    end_xy = _coordinates(end)
    dash_length = dashed_length_for(bounds)
    if kind == "line":
        segment = _line_extent(start_xy, end_xy, bounds)
        return _styled_segment_mesh(segment, style, dash_length=dash_length)
    if kind == "ray":
        segment = _ray_extent(start_xy, end_xy, bounds)
        return _styled_segment_mesh(segment, style, dash_length=dash_length)
    if kind == "vector":
        return _vector_mesh(start_xy, end_xy, bounds)
    return _styled_segment_mesh((start_xy, end_xy), style, dash_length=dash_length)


class GeometrySceneController:
    """管理二维交互对象，同时避免影响函数曲线和坐标辅助线。

    与 :class:`~rendering.two_d_scene.TwoDGuides` 一样，本控制器为每个点、线及其
    高亮光晕保留持久化演员，并用 ``copy_from`` 就地更新几何数据、用属性更新样式，
    而不是每帧删除并重建演员。所有内部绘制均以 ``render=False`` 调用，仅由调用方在
    操作结束后统一 ``plotter.render()``，从而消除拖动点、悬浮或选中时的闪烁。
    """

    def __init__(
        self,
        plotter: pv.Plotter,
        bounds: ViewportBounds,
        *,
        annotation_font_size: int = _ANNOTATION_FONT_SIZE,
    ) -> None:
        self.plotter = plotter
        self.bounds = bounds
        self.annotation_font_size = max(1, int(annotation_font_size))
        self.points: dict[str, Point2D] = {}
        self.linears: dict[str, Linear2D] = {}
        self.annotations: dict[str, Annotation2D] = {}
        self.order: list[str] = []
        self._hover_id: str | None = None
        self._selected_id: str | None = None
        self._has_labels = False
        # 每个颜色一个标注标签演员，刷新时整组替换。
        self._annotation_actors: list[str] = []
        self._draft_kind: LinearKind | None = None
        self._draft_style = "solid"
        self._draft_start: tuple[float, float] | None = None
        self._draft_end: tuple[float, float] | None = None
        # 持久化演员与其就地更新的网格，键为演员名。
        self._meshes: dict[str, pv.PolyData] = {}
        self._actors: dict[str, object] = {}
        self._teaching_actors: dict[str, object] = {}
        self._teaching_meshes: dict[str, pv.PolyData] = {}
        # Label actors are relatively expensive in VTK. Defer them while a
        # scene command is adding or updating a group of objects.
        self._batch_depth = 0
        self._labels_dirty = False
        self._annotations_dirty = False

    @contextmanager
    def batch_update(self) -> Iterator[None]:
        """Defer aggregate label/annotation actors until a group is complete."""
        self._batch_depth += 1
        try:
            yield
        finally:
            self.end_batch_update()

    def begin_batch_update(self) -> None:
        """Start a batch that can be closed by :meth:`end_batch_update`."""
        self._batch_depth += 1

    def end_batch_update(self) -> None:
        """Close a batch started by :meth:`begin_batch_update`."""
        if self._batch_depth <= 0:
            return
        self._batch_depth -= 1
        if self._batch_depth != 0:
            return
        labels_dirty = self._labels_dirty
        annotations_dirty = self._annotations_dirty
        self._labels_dirty = False
        self._annotations_dirty = False
        if labels_dirty:
            self._refresh_labels()
        if annotations_dirty:
            self._refresh_annotations()

    def _request_labels_refresh(self) -> None:
        if self._batch_depth:
            self._labels_dirty = True
        else:
            self._refresh_labels()

    def _request_annotations_refresh(self) -> None:
        if self._batch_depth:
            self._annotations_dirty = True
        else:
            self._refresh_annotations()

    @staticmethod
    def point_actor_name(point_id: str) -> str:
        return f"geometry:point:{point_id}"

    @staticmethod
    def point_halo_name(point_id: str) -> str:
        return f"geometry:point:{point_id}:halo"

    @staticmethod
    def linear_actor_name(linear_id: str) -> str:
        return f"geometry:linear:{linear_id}"

    @staticmethod
    def linear_halo_name(linear_id: str) -> str:
        return f"geometry:linear:{linear_id}:halo"

    @staticmethod
    def annotation_actor_name(annotation_id: str) -> str:
        return f"geometry:annotation:{annotation_id}"

    def add_point(self, point: Point2D) -> None:
        self.points[point.id] = point
        if point.id not in self.order:
            self.order.append(point.id)
        self._sync_point(point)
        self._request_labels_refresh()

    def add_linear(self, linear: Linear2D) -> None:
        self.linears[linear.id] = linear
        if linear.id not in self.order:
            self.order.append(linear.id)
        self._sync_linear(linear)
        self._request_annotations_refresh()

    def add_annotation(self, annotation: Annotation2D) -> None:
        self.annotations[annotation.id] = annotation
        if annotation.id not in self.order:
            self.order.append(annotation.id)
        self._request_annotations_refresh()

    def move_point(self, point_id: str, x: float, y: float) -> None:
        """更新点坐标，并联动刷新依赖它的线类对象和标签。"""
        point = self.points.get(point_id)
        if point is None:
            return
        point.x = float(x)
        point.y = float(y)
        self._sync_point(point)
        for linear in self.linears.values():
            if point_id in {linear.start_point_id, linear.end_point_id}:
                self._sync_linear(linear)
        self._request_labels_refresh()
        self._request_annotations_refresh()

    def move_annotation(self, annotation_id: str, x: float, y: float) -> None:
        """Move a user mark while preserving its display offset and text."""
        annotation = self.annotations.get(annotation_id)
        if annotation is None or not annotation.editable:
            return
        annotation.x = float(x)
        annotation.y = float(y)
        self._request_annotations_refresh()

    def linear_label_position(self, linear_id: str) -> tuple[float, float] | None:
        """Return the current world position of a line or vector's label."""
        linear = self.linears.get(linear_id)
        if linear is None or not linear.visible or not linear.label:
            return None
        start = self.points.get(linear.start_point_id)
        end = self.points.get(linear.end_point_id)
        if start is None or end is None:
            return None
        position = self._linear_label_position(
            start,
            end,
            linear.label_side,
            linear.label_offset_x,
            linear.label_offset_y,
        )
        return position[0], position[1]

    def move_linear_label(self, linear_id: str, x: float, y: float) -> None:
        """Move a line or vector's label without altering its endpoints."""
        linear = self.linears.get(linear_id)
        if linear is None or not linear.label:
            return
        start = self.points.get(linear.start_point_id)
        end = self.points.get(linear.end_point_id)
        if start is None or end is None:
            return
        default = self._linear_label_position(start, end, linear.label_side)
        linear.label_offset_x = float(x) - default[0]
        linear.label_offset_y = float(y) - default[1]
        self._request_annotations_refresh()

    def remove_object(self, object_id: str) -> None:
        for name in (
            self.point_actor_name(object_id),
            self.point_halo_name(object_id),
            self.linear_actor_name(object_id),
            self.linear_halo_name(object_id),
            self.annotation_actor_name(object_id),
        ):
            self._drop_actor(name)
        self.points.pop(object_id, None)
        self.linears.pop(object_id, None)
        self.annotations.pop(object_id, None)
        self.order = [item for item in self.order if item != object_id]
        if self._hover_id == object_id:
            self._hover_id = None
        if self._selected_id == object_id:
            self._selected_id = None
        self._request_labels_refresh()
        self._request_annotations_refresh()

    def set_visible(self, object_id: str, visible: bool) -> None:
        if object_id in self.points:
            self.points[object_id].visible = visible
            self._sync_point(self.points[object_id])
            self._request_labels_refresh()
        if object_id in self.linears:
            self.linears[object_id].visible = visible
            self._sync_linear(self.linears[object_id])
            # 向量标签属于线对象：隐藏向量时它的标签必须一起消失。
            self._request_annotations_refresh()
        if object_id in self.annotations:
            self.annotations[object_id].visible = visible
            self._request_annotations_refresh()

    def set_agent_alias_visible(self, alias: str, visible: bool) -> None:
        """Show or hide regular scene objects owned by a semantic alias.

        Agent commands store their stable alias on the model object while the
        geometry controller indexes actors by generated object IDs.  Child
        aliases follow their semantic parent, so a composite operation such as
        ``sem__map__source`` is governed by ``sem__map`` as well.
        """
        prefix = f"{alias}__"

        def belongs_to(item: Point2D | Linear2D | Annotation2D) -> bool:
            agent_alias = getattr(item, "agent_alias", None)
            return isinstance(agent_alias, str) and (
                agent_alias == alias or agent_alias.startswith(prefix)
            )

        with self.batch_update():
            for point in tuple(self.points.values()):
                if belongs_to(point):
                    self.set_visible(point.id, visible)
            for linear in tuple(self.linears.values()):
                if belongs_to(linear):
                    self.set_visible(linear.id, visible)
            for annotation in tuple(self.annotations.values()):
                if belongs_to(annotation):
                    self.set_visible(annotation.id, visible)

    def set_hover(self, object_id: str | None) -> bool:
        """设置悬浮对象，返回悬浮目标是否发生变化。"""
        if object_id == self._hover_id:
            return False
        previous = self._hover_id
        self._hover_id = object_id
        self._restyle(previous)
        self._restyle(object_id)
        self._request_labels_refresh()
        if (
            previous in self.annotations
            or object_id in self.annotations
            or previous in self.linears
            or object_id in self.linears
        ):
            self._request_annotations_refresh()
        return True

    def set_selected(self, object_id: str | None) -> bool:
        """设置选中对象，返回选中目标是否发生变化。"""
        if object_id == self._selected_id:
            return False
        previous = self._selected_id
        self._selected_id = object_id
        self._restyle(previous)
        self._restyle(object_id)
        self._request_labels_refresh()
        return True

    @property
    def selected_id(self) -> str | None:
        return self._selected_id

    def hit_test(self, x: float, y: float, tolerance: float) -> str | None:
        """返回距离给定世界坐标最近、且在容差内的对象；点优先于线。"""
        best_point: tuple[float, str] | None = None
        for point in self.points.values():
            if not point.visible:
                continue
            distance = hypot(point.x - x, point.y - y)
            if distance <= tolerance and (best_point is None or distance < best_point[0]):
                best_point = (distance, point.id)
        if best_point is not None:
            return best_point[1]

        best_linear: tuple[float, str] | None = None
        for linear in self.linears.values():
            if not linear.visible:
                continue
            start = self.points.get(linear.start_point_id)
            end = self.points.get(linear.end_point_id)
            if start is None or end is None:
                continue
            distance = _distance_to_linear(linear.kind, (start.x, start.y), (end.x, end.y), (x, y))
            if distance <= tolerance and (best_linear is None or distance < best_linear[0]):
                best_linear = (distance, linear.id)
        if best_linear is not None:
            return best_linear[1]
        return self.hit_test_annotation(x, y, tolerance)

    def hit_test_annotation(
        self,
        x: float,
        y: float,
        tolerance: float,
        *,
        editable_only: bool = False,
    ) -> str | None:
        """Return the nearest annotation anchor within a touch-friendly radius."""
        best: tuple[float, str] | None = None
        radius = max(float(tolerance), 1e-9) * 1.5
        for annotation in self.annotations.values():
            if not annotation.visible or (editable_only and not annotation.editable):
                continue
            distance = hypot(
                annotation.x + annotation.offset_x - x,
                annotation.y + annotation.offset_y - y,
            )
            if distance <= radius and (best is None or distance < best[0]):
                best = (distance, annotation.id)
        return best[1] if best is not None else None

    def hit_test_label(
        self,
        x: float,
        y: float,
        tolerance: float,
        *,
        editable_annotations_only: bool = False,
    ) -> tuple[str, str] | None:
        """Return the nearest annotation or line-label target within tolerance."""
        best: tuple[float, str, str] | None = None
        radius = max(float(tolerance), 1e-9) * 1.5
        for annotation in self.annotations.values():
            if not annotation.visible or (editable_annotations_only and not annotation.editable):
                continue
            distance = hypot(
                annotation.x + annotation.offset_x - x,
                annotation.y + annotation.offset_y - y,
            )
            if distance <= radius and (best is None or distance < best[0]):
                best = (distance, "annotation", annotation.id)
        for linear in self.linears.values():
            position = self.linear_label_position(linear.id)
            if position is None:
                continue
            distance = hypot(position[0] - x, position[1] - y)
            if distance <= radius and (best is None or distance < best[0]):
                best = (distance, "linear", linear.id)
        return (best[1], best[2]) if best is not None else None

    def set_bounds(self, bounds: ViewportBounds) -> None:
        """更新依赖视口范围的直线、射线、向量箭头、标签和临时预览。"""
        self.bounds = bounds
        for linear in self.linears.values():
            self._sync_linear(linear)
        self._request_labels_refresh()
        self._request_annotations_refresh()
        if (
            self._draft_kind is not None
            and self._draft_start is not None
            and self._draft_end is not None
        ):
            self._replace_draft(self._draft_kind, self._draft_start, self._draft_end, style=self._draft_style)

    def set_draft(
        self,
        kind: LinearKind,
        start: Point2D | tuple[float, float],
        end: tuple[float, float],
        *,
        style: str = "solid",
    ) -> None:
        self._draft_kind = kind
        self._draft_style = style
        self._draft_start = _coordinates(start)
        self._draft_end = end
        self._replace_draft(kind, self._draft_start, end, style=style)

    def clear_draft(self) -> None:
        self._drop_actor(_DRAFT_ACTOR)
        self._draft_kind = None
        self._draft_style = "solid"
        self._draft_start = None
        self._draft_end = None

    def clear_teaching(self) -> None:
        """Remove actors created by linear-algebra teaching primitives."""
        for name in tuple(self._teaching_actors):
            self.plotter.remove_actor(name, render=False)
        self._teaching_actors.clear()
        self._teaching_meshes.clear()

    def clear_teaching_prefix(self, prefix: str) -> None:
        """Remove only teaching actors whose names contain a caller-owned prefix.

        Interactive tools use names such as ``la_tool_projection_1`` so they can
        replace their own overlays without clearing lecture-provided drawings.
        The method intentionally operates on the controller registry rather than
        scanning all plotter actors, keeping curves, guides, and geometry intact.
        """
        marker = f":{prefix}"
        for name in tuple(self._teaching_actors):
            if marker in name:
                self.plotter.remove_actor(name, render=False)
                self._teaching_actors.pop(name, None)
                self._teaching_meshes.pop(name, None)

    def set_teaching_visible(self, alias: str, visible: bool) -> None:
        """Show or hide every teaching actor owned by one semantic alias."""
        marker = f":{alias}"
        for name, actor in self._teaching_actors.items():
            if not (name.endswith(marker) or f"{marker}:" in name):
                continue
            set_visibility = getattr(actor, "SetVisibility", None)
            if callable(set_visibility):
                set_visibility(bool(visible))
            elif hasattr(actor, "visibility"):
                actor.visibility = bool(visible)

    def add_teaching_polygon(
        self,
        alias: str,
        vertices: Iterable[tuple[float, float]],
        *,
        color: str = "#5b8def",
        opacity: float = 0.24,
        outline: bool = True,
    ) -> None:
        points = tuple((float(x), float(y)) for x, y in vertices)
        if len(points) < 3:
            raise ValueError("A teaching polygon requires at least three vertices")
        mesh = _polygon_mesh(points)
        name = f"geometry:teaching:polygon:{alias}"
        self._replace_teaching_actor(name, mesh, color=color, opacity=opacity, show_edges=outline)

    def add_teaching_angle_arc(
        self,
        alias: str,
        vertex: tuple[float, float],
        first: tuple[float, float],
        second: tuple[float, float],
        *,
        radius: float,
        color: str = "#d97845",
    ) -> None:
        mesh = _angle_arc_mesh(vertex, first, second, radius)
        name = f"geometry:teaching:arc:{alias}"
        self._replace_teaching_actor(name, mesh, color=color, line_width=3.0)

    def add_teaching_right_angle_marker(
        self,
        alias: str,
        vertex: tuple[float, float],
        first: tuple[float, float],
        second: tuple[float, float],
        *,
        size: float,
        color: str = "#d97845",
    ) -> None:
        mesh = _right_angle_mesh(vertex, first, second, size)
        name = f"geometry:teaching:right-angle:{alias}"
        self._replace_teaching_actor(name, mesh, color=color, line_width=2.5)

    def add_teaching_projection(
        self,
        vector: tuple[float, float],
        direction: tuple[float, float],
        *,
        result_alias: str,
        foot_alias: str,
        residual_alias: str,
        alias: str | None = None,
        origin: tuple[float, float] = (0.0, 0.0),
        color: str = "#2777b6",
        style: str = "solid",
    ) -> None:
        vx, vy = vector
        dx, dy = direction
        denominator = dx * dx + dy * dy
        if denominator <= 1e-12:
            raise ValueError("Projection direction cannot be zero")
        scale = (vx * dx + vy * dy) / denominator
        ox, oy = origin
        foot = (ox + scale * dx, oy + scale * dy)
        endpoint_xy = (ox + vx, oy + vy)
        # 投影与垂足连线属于辅助构造，可按语义要求画成虚线。节距与普通虚线
        # 线段共用，因此投影垂线和 a·b 延长段的疏密一致。
        dash_length = dashed_length_for(self.bounds)
        projection = _styled_segment_mesh((origin, foot), style, dash_length=dash_length)
        residual = _styled_segment_mesh((foot, endpoint_xy), style, dash_length=dash_length)
        self._replace_teaching_actor(
            f"geometry:teaching:projection:{result_alias}", projection, color=color, line_width=3.0
        )
        self._replace_teaching_actor(
            f"geometry:teaching:projection:{residual_alias}", residual, color="#d97845", line_width=2.0
        )
        foot_mesh = _point_mesh(*foot)
        self._replace_teaching_actor(
            f"geometry:teaching:projection:{foot_alias}", foot_mesh, color="#d97845", point_size=10.0, render_points_as_spheres=True
        )
        endpoint = _point_mesh(*endpoint_xy)
        endpoint_name = (
            f"geometry:teaching:projection:{alias}:endpoint"
            if alias
            else "geometry:teaching:projection:endpoint"
        )
        self._replace_teaching_actor(
            endpoint_name, endpoint, color="#2777b6", point_size=10.0, render_points_as_spheres=True
        )

    def add_teaching_transformed_grid(
        self,
        matrix: tuple[tuple[float, float], tuple[float, float]],
        bounds: tuple[float, float, float, float],
        *,
        step: float = 1.0,
        alias: str | None = None,
        color: str = "#5b8def",
        origin: tuple[float, float] = (0.0, 0.0),
        show_source_grid: bool = True,
    ) -> None:
        """Draw a grid and its linear image.

        ``show_source_grid=False`` draws only the transformed grid, for views
        that already carry their own source coordinate system (the lecture case
        panes): the extra grey source grid would otherwise float on top of the
        original axes.  The default keeps the matrix-transform tool unchanged.
        """

        transformed = _grid_mesh(bounds, step, matrix=matrix)
        if origin != (0.0, 0.0):
            transformed.translate((origin[0], origin[1], 0.0), inplace=True)
        suffix = f":{alias}" if alias else ""
        source_name = f"geometry:teaching:grid{suffix}:original"
        if show_source_grid:
            original = _grid_mesh(bounds, step)
            if origin != (0.0, 0.0):
                original.translate((origin[0], origin[1], 0.0), inplace=True)
            self._replace_teaching_actor(source_name, original, color="#a6afbd", line_width=1.0)
        else:
            self._drop_actor(source_name)
        self._replace_teaching_actor(f"geometry:teaching:grid{suffix}:transformed", transformed, color=color, line_width=2.0)

    def add_teaching_basis_grid(
        self,
        basis_matrix: tuple[tuple[float, ...], ...],
        bounds: tuple[float, float, float, float],
        *,
        alias: str | None = None,
        color: str = "#5b8def",
    ) -> None:
        """Draw the standard grid and its linear image under a basis."""
        matrix = tuple(tuple(float(value) for value in row) for row in basis_matrix)
        self.add_teaching_transformed_grid(matrix, bounds, alias=alias, color=color)

    def add_teaching_coordinate_readout(
        self,
        standard_vector: tuple[float, float],
        alternate_coordinates: tuple[float, float],
        *,
        alias: str = "coordinate-readout",
        color: str = "#2777b6",
    ) -> None:
        endpoint = (float(standard_vector[0]), float(standard_vector[1]))
        mesh = _segments_mesh([((0.0, 0.0), endpoint)])
        self._replace_teaching_actor(f"geometry:teaching:coordinates:{alias}:standard", mesh, color=color, line_width=3.0)
        alt = (float(alternate_coordinates[0]), float(alternate_coordinates[1]))
        self._replace_teaching_actor(f"geometry:teaching:coordinates:{alias}:alternate", _point_mesh(*alt), color="#d97845", point_size=10.0, render_points_as_spheres=True)

    def add_teaching_least_squares(
        self,
        values: tuple[float, ...],
        fit: tuple[float, ...],
        residual: tuple[float, ...],
        *,
        alias: str = "least-squares",
    ) -> None:
        points = tuple((float(index), float(value)) for index, value in enumerate(values))
        fitted = tuple((float(index), float(value)) for index, value in enumerate(fit))
        self._replace_teaching_actor(f"geometry:teaching:least-squares:{alias}:data", _segments_mesh(list(zip(points, points[1:]))), color="#2777b6", line_width=2.0)
        self._replace_teaching_actor(f"geometry:teaching:least-squares:{alias}:fit", _segments_mesh(list(zip(fitted, fitted[1:]))), color="#4c9f70", line_width=3.0)

    def add_teaching_subspace_region(
        self,
        basis: Iterable[tuple[float, float]],
        bounds: tuple[float, float, float, float],
        *,
        alias: str | None = None,
        origin: tuple[float, float] = (0.0, 0.0),
        color: str = "#4c9f70",
        opacity: float = 0.2,
    ) -> None:
        vectors = tuple((float(x), float(y)) for x, y in basis)
        ox, oy = origin
        is_line = len(vectors) == 1 or (
            len(vectors) >= 2
            and abs(vectors[0][0] * vectors[1][1] - vectors[0][1] * vectors[1][0]) <= 1e-12
        )

        if is_line:
            vx, vy = next((vector for vector in vectors if hypot(*vector) > 1e-12), (0.0, 0.0))
            length = max(abs(bounds[1] - bounds[0]), abs(bounds[3] - bounds[2]))
            norm = hypot(vx, vy)
            if norm <= 1e-12:
                raise ValueError("Subspace basis cannot be zero")
            unit = (vx / norm, vy / norm)
            segment = (
                (ox - length * unit[0], oy - length * unit[1]),
                (ox + length * unit[0], oy + length * unit[1]),
            )
            mesh = _segments_mesh([segment])
        else:
            x_min, x_max, y_min, y_max = bounds
            mesh = _polygon_mesh(
                (
                    (x_min, y_min),
                    (x_max, y_min),
                    (x_max, y_max),
                    (x_min, y_max),
                )
            )
        name = f"geometry:teaching:subspace:{alias}" if alias else "geometry:teaching:subspace"
        self._replace_teaching_actor(name, mesh, color=color, opacity=opacity, show_edges=True)

    def add_teaching_quadratic_contour(self, vertices: Iterable[tuple[float, float]], *, segments=None, alias: str = "quadratic", color: str = "#4c9f70") -> None:
        points = tuple((float(x), float(y)) for x, y in vertices)
        if len(points) >= 2:
            edges = list(zip(points, points[1:] + points[:1])) if segments is None else [(points[i],points[j]) for i,j in segments]
            if edges:
                self._replace_teaching_actor(f"geometry:teaching:quadratic:{alias}:contour", _segments_mesh(edges), color=color, line_width=2.5)

    def add_teaching_quadratic_axes(self, axes: Iterable[tuple[tuple[float, float], tuple[float, float]]], *, alias: str = "quadratic") -> None:
        for index, (start, end) in enumerate(axes):
            self._replace_teaching_actor(f"geometry:teaching:quadratic:{alias}:axis:{index}", _segments_mesh([(start, end)]), color="#d97845", line_width=2.0)

    def add_teaching_staged_transform(
        self,
        matrices: Iterable[tuple[tuple[float, float], tuple[float, float]]],
        points: Iterable[tuple[float, float]],
        aliases: Iterable[str],
        *,
        alias: str | None = None,
        color: str = "#2777b6",
    ) -> None:
        stage_points = [(float(x), float(y)) for x, y in points]
        for stage_index, matrix in enumerate(matrices, start=1):
            stage_points = [_mat_vec(matrix, point) for point in stage_points]
            mesh = pv.PolyData(np.asarray([(x, y, 0.0) for x, y in stage_points], dtype=float))
            stage_name = (
                f"geometry:teaching:stage:{alias}:{stage_index}"
                if alias
                else f"geometry:teaching:stage:{stage_index}"
            )
            self._replace_teaching_actor(
                stage_name, mesh, color=color, point_size=10.0, render_points_as_spheres=True
            )
        # Keep aliases meaningful in exported actor metadata without affecting hit testing.
        for point_alias, point in zip(aliases, stage_points):
            mesh = _point_mesh(*point)
            point_name = (
                f"geometry:teaching:stage-point:{alias}:{point_alias}"
                if alias
                else f"geometry:teaching:stage-point:{point_alias}"
            )
            self._replace_teaching_actor(point_name, mesh, color="#d64545", point_size=9.0, render_points_as_spheres=True)

    def add_teaching_oriented_area(
        self,
        vectors: Iterable[tuple[float, float]],
        *,
        alias: str = "oriented-area",
        origin: tuple[float, float] = (0.0, 0.0),
        color: str = "#d97845",
        opacity: float = 0.28,
    ) -> None:
        values = tuple((float(x), float(y)) for x, y in vectors)
        if len(values) != 2:
            raise ValueError("Oriented area requires two vectors")
        a, b = values
        ox, oy = origin
        self._replace_teaching_actor(
            f"geometry:teaching:oriented-area:{alias}",
            _polygon_mesh(
                (
                    (ox, oy),
                    (ox + a[0], oy + a[1]),
                    (ox + a[0] + b[0], oy + a[1] + b[1]),
                    (ox + b[0], oy + b[1]),
                )
            ),
            color=color,
            opacity=opacity,
            show_edges=True,
        )

    def _replace_teaching_actor(self, name: str, mesh: pv.PolyData, **kwargs: object) -> object:
        old = self._teaching_actors.get(name)
        if old is not None:
            stored = self._teaching_meshes.get(name)
            if stored is not None:
                # Teaching overlays such as the vector-addition polygon are
                # updated on every drag. Keep the VTK actor and replace only
                # its data to avoid remove/add churn in the render window.
                stored.copy_from(mesh)
                _set_prop(old, **kwargs)
                return old
            self.plotter.remove_actor(name, render=False)
        stored = mesh.copy()
        actor = self.plotter.add_mesh(stored, name=name, render=False, **kwargs)
        self._teaching_actors[name] = actor
        self._teaching_meshes[name] = stored
        return actor

    def _drop_actor(self, name: str) -> None:
        """Remove one controller-owned actor and its persistent caches.

        A teaching grid may suppress its source-grid actor before that actor
        has ever been materialised.  Do not ask the underlying PyVista
        renderer to remove an unknown name in that case: some renderer
        adapters have no actor registry during initialisation.  The two local
        registries are the authoritative ownership boundary.
        """
        if name in self._actors or name in self._teaching_actors:
            self.plotter.remove_actor(name, render=False)
        self._meshes.pop(name, None)
        self._actors.pop(name, None)
        self._teaching_meshes.pop(name, None)
        self._teaching_actors.pop(name, None)

    def _restyle(self, object_id: str | None) -> None:
        if object_id is None:
            return
        if object_id in self.points:
            self._sync_point(self.points[object_id])
        elif object_id in self.linears:
            self._sync_linear(self.linears[object_id])

    # ------------------------------------------------------------------
    # 持久化演员辅助方法
    # ------------------------------------------------------------------

    def _get_or_create_point_actor(
        self,
        name: str,
        mesh: pv.PolyData,
        *,
        color: str,
        point_size: float,
        opacity: float = 1.0,
    ) -> object:
        """取出已有点演员，或首次创建并缓存；几何始终通过 copy_from 就地更新。"""
        actor = self._actors.get(name)
        if actor is None:
            stored = mesh.copy()
            actor = self.plotter.add_mesh(
                stored,
                name=name,
                color=color,
                opacity=opacity,
                lighting=False,
                point_size=point_size,
                render_points_as_spheres=True,
                render=False,
            )
            self._meshes[name] = stored
            self._actors[name] = actor
        else:
            self._meshes[name].copy_from(mesh)
            _set_prop(actor, color=color, point_size=point_size, opacity=opacity)
        return actor

    def _get_or_create_linear_actor(
        self,
        name: str,
        mesh: pv.PolyData,
        *,
        color: str,
        line_width: float,
        opacity: float = 1.0,
    ) -> object:
        """取出已有线演员，或首次创建并缓存；几何通过 copy_from 就地更新。"""
        actor = self._actors.get(name)
        if actor is None:
            stored = mesh.copy()
            actor = self.plotter.add_mesh(
                stored,
                name=name,
                color=color,
                opacity=opacity,
                line_width=line_width,
                render_lines_as_tubes=False,
                show_vertices=False,
                lighting=False,
                render=False,
            )
            self._meshes[name] = stored
            self._actors[name] = actor
        else:
            self._meshes[name].copy_from(mesh)
            _set_prop(actor, color=color, line_width=line_width, opacity=opacity)
        return actor

    def _sync_point(self, point: Point2D) -> None:
        """就地更新点和光晕演员的几何与样式，不销毁演员。"""
        halo_name = self.point_halo_name(point.id)
        actor_name = self.point_actor_name(point.id)

        if not point.visible:
            # 隐藏而非删除，保留演员以便下次快速恢复。
            for name in (halo_name, actor_name):
                actor = self._actors.get(name)
                if actor is not None:
                    actor.visibility = False
            return

        mesh = _point_mesh(point.x, point.y)
        halo_style = self._point_halo_style(point.id)

        # 主演员
        main_actor = self._get_or_create_point_actor(
            actor_name, mesh, color=point.color, point_size=_POINT_SIZE
        )
        main_actor.visibility = True

        # 光晕演员：有高亮时显示，否则隐藏（不删除）
        if halo_style is not None:
            halo_color, halo_multiplier = halo_style
            halo_size = _POINT_HALO_SIZE if halo_multiplier >= 2.0 else 18.0
            halo_actor = self._get_or_create_point_actor(
                halo_name, mesh, color=halo_color, point_size=halo_size, opacity=0.35
            )
            halo_actor.visibility = True
        else:
            actor = self._actors.get(halo_name)
            if actor is not None:
                actor.visibility = False

    def _point_halo_style(self, point_id: str) -> tuple[str, float] | None:
        if point_id == self._selected_id:
            return _SELECTED_HALO_COLOR, 2.2
        if point_id == self._hover_id:
            return _HOVER_HALO_COLOR, 1.8
        return None

    def _sync_linear(self, linear: Linear2D) -> None:
        """就地更新线和光晕演员的几何与样式，不销毁演员。"""
        halo_name = self.linear_halo_name(linear.id)
        actor_name = self.linear_actor_name(linear.id)

        start = self.points.get(linear.start_point_id)
        end = self.points.get(linear.end_point_id)
        visible = linear.visible and start is not None and end is not None

        if not visible:
            for name in (halo_name, actor_name):
                actor = self._actors.get(name)
                if actor is not None:
                    actor.visibility = False
            return

        mesh = linear_mesh(linear.kind, start, end, self.bounds, style=linear.style)
        has_geometry = mesh.n_points > 0 and mesh.n_cells > 0

        # 主演员
        main_actor = self._get_or_create_linear_actor(
            actor_name, mesh if has_geometry else pv.PolyData(),
            color=linear.color, line_width=linear.line_width,
        )
        main_actor.visibility = has_geometry

        # 光晕演员
        highlight = self._linear_highlight_color(linear.id)
        if highlight is not None and has_geometry:
            halo_actor = self._get_or_create_linear_actor(
                halo_name, mesh,
                color=highlight,
                line_width=linear.line_width + _LINE_HALO_WIDTH,
                opacity=0.4,
            )
            halo_actor.visibility = True
        else:
            actor = self._actors.get(halo_name)
            if actor is not None:
                actor.visibility = False

    def _linear_highlight_color(self, linear_id: str) -> str | None:
        if linear_id == self._selected_id:
            return _SELECTED_HALO_COLOR
        if linear_id == self._hover_id:
            return _HOVER_HALO_COLOR
        return None

    def _refresh_labels(self) -> None:
        add_labels = getattr(self.plotter, "add_point_labels", None)
        if add_labels is None:
            return
        if self._has_labels:
            self.plotter.remove_actor(_LABEL_ACTOR, render=False)
            self._has_labels = False
        positions: list[tuple[float, float, float]] = []
        texts: list[str] = []
        offset = self._label_offset()
        # 多个向量从同一原点出发时，编译出的计划会为每个向量各生成一个同名同坐标的点。
        # 若不去重，标签放置器会把重叠的“O”摊开成多个标签，看起来像有多个原点。
        seen: set[tuple[str, float, float]] = set()
        for point in self.points.values():
            if not point.visible:
                continue
            # 没有名字的点只是几何端点（读数拐点、分量端点），不是要说名的对象；
            # 给它画标记只会把内部编号摊到画面上。
            if not point.name:
                continue
            x = point.x + offset
            y = point.y + offset
            key = (point.name, round(x, 9), round(y, 9))
            if key in seen:
                continue
            seen.add(key)
            positions.append((x, y, 0.0))
            texts.append(self._point_label_text(point))
        if not positions:
            return
        add_labels(
            positions,
            texts,
            font_size=math_labels.CASE_LABEL_FONT_SIZE,
            text_color="#1f2937",
            shape=None,
            show_points=False,
            always_visible=True,
            name=_LABEL_ACTOR,
            font_file=math_labels.label_font_file(),
            render=False,
            render_points_as_spheres=False,
        )
        self._has_labels = True

    def _refresh_annotations(self) -> None:
        """刷新独立教学标注，不将其混入点名标签。

        每个颜色一个标签演员：共线的向量（例如 a 与 2a）标签紧挨在一起，只有让
        标签使用所在线段的颜色，才能一眼看出哪个标签属于哪个向量。
        """
        add_labels = getattr(self.plotter, "add_point_labels", None)
        if add_labels is None:
            return
        for name in self._annotation_actors:
            self.plotter.remove_actor(name, render=False)
        self._annotation_actors = []
        grouped: dict[tuple[str, bool], list[tuple[tuple[float, float, float], str]]] = {}
        for annotation in self.annotations.values():
            if not annotation.visible:
                continue
            text = self._annotation_text(annotation)
            if not text:
                continue
            position = (annotation.x + annotation.offset_x, annotation.y + annotation.offset_y, 0.0)
            is_hovered = annotation.id == self._hover_id
            grouped.setdefault((annotation.color, is_hovered), []).append((position, text))
        for linear in self.linears.values():
            if not linear.visible or not linear.label:
                continue
            start = self.points.get(linear.start_point_id)
            end = self.points.get(linear.end_point_id)
            if start is None or end is None:
                continue
            position = self.linear_label_position(linear.id)
            if position is None:
                continue
            grouped.setdefault((linear.color, linear.id == self._hover_id), []).append(
                ((position[0], position[1], 0.0), linear.label)
            )
        for (color, is_hovered), items in grouped.items():
            name = f"{_ANNOTATION_ACTOR}:{color.lstrip('#').lower()}:{'hover' if is_hovered else 'default'}"
            label_style: dict[str, object] = {}
            if is_hovered:
                label_style = {
                    "shape_color": "#1a73e8",
                    "fill_shape": False,
                    "shape_opacity": 1.0,
                    "margin": 6,
                }
            add_labels(
                [position for position, _text in items],
                [text for _position, text in items],
                font_size=self.annotation_font_size,
                text_color=color,
                shape=None if not is_hovered else "rounded_rect",
                show_points=False,
                always_visible=True,
                name=name,
                font_file=math_labels.label_font_file(),
                render=False,
                render_points_as_spheres=False,
                **label_style,
            )
            self._annotation_actors.append(name)

    def _annotation_text(self, annotation: Annotation2D) -> str:
        """标注显示文本，带 ``latex`` 的标注会排成堆叠分数等数学形式。"""
        return math_labels.display_text(
            annotation.text,
            annotation.latex,
            font_size=self.annotation_font_size,
            bold=True,
        )

    def _point_label_text(self, point: Point2D) -> str:
        if point.id in {self._selected_id, self._hover_id}:
            return f"{point.name} = ({format_number(point.x)}, {format_number(point.y)})"
        return point.name

    def _linear_label_position(
        self,
        start: Point2D,
        end: Point2D,
        side: LinearLabelSide = "below",
        offset_x: float = 0.0,
        offset_y: float = 0.0,
    ) -> tuple[float, float, float]:
        """Place a linear label above or below its primitive.

        取景由最大跨度决定，因此偏移量也按最大跨度取，视觉上接近固定的一行高度。
        """

        mid_x = (start.x + end.x) / 2.0
        mid_y = (start.y + end.y) / 2.0
        dx = end.x - start.x
        dy = end.y - start.y
        length = hypot(dx, dy)
        # 上方留白略大于下方：向量名紧贴线段，同时避免压到线下的模长标注。
        offset = max(self.bounds.x_span, self.bounds.y_span) * (0.012 if side == "above" else 0.02)
        if length <= 1e-12:
            return (
                mid_x + offset_x,
                mid_y + (offset if side == "above" else -offset) + offset_y,
                0.0,
            )
        normal_x, normal_y = -dy / length, dx / length
        # 两条法线里取指向下方的一条；竖直向量没有“下方”，固定取右侧。
        if normal_y > 0.0 or (normal_y == 0.0 and normal_x < 0.0):
            normal_x, normal_y = -normal_x, -normal_y
        if side == "above":
            normal_x, normal_y = -normal_x, -normal_y
        return (
            mid_x + normal_x * offset + offset_x,
            mid_y + normal_y * offset + offset_y,
            0.0,
        )

    def _label_offset(self) -> float:
        return min(self.bounds.x_span, self.bounds.y_span) * 0.015

    def _replace_draft(
        self,
        kind: LinearKind,
        start: tuple[float, float],
        end: tuple[float, float],
        *,
        style: str = "solid",
    ) -> None:
        mesh = linear_mesh(kind, start, end, self.bounds, style=style)
        has_geometry = mesh.n_points > 0 and mesh.n_cells > 0
        draft_actor = self._get_or_create_linear_actor(
            _DRAFT_ACTOR,
            mesh if has_geometry else pv.PolyData(),
            color="#6c7b8d",
            line_width=1.5,
            opacity=0.72,
        )
        draft_actor.visibility = has_geometry


def _set_prop(actor: object, **kwargs: object) -> None:
    """安全更新 VTK 演员属性；FakeActor 无 prop 属性时静默跳过。"""
    prop = getattr(actor, "prop", None)
    if prop is None:
        return
    for key, value in kwargs.items():
        if hasattr(prop, key):
            setattr(prop, key, value)


def _coordinates(point: Point2D | tuple[float, float]) -> tuple[float, float]:
    if isinstance(point, Point2D):
        return point.x, point.y
    return float(point[0]), float(point[1])


def _point_mesh(x: float, y: float) -> pv.PolyData:
    return pv.PolyData(np.array([[float(x), float(y), 0.0]], dtype=float))


def _line_extent(
    start: tuple[float, float],
    end: tuple[float, float],
    bounds: ViewportBounds,
) -> tuple[tuple[float, float], tuple[float, float]] | None:
    limits = _parameter_limits(start, end, bounds)
    if limits is None:
        return None
    lower, upper = limits
    direction = (end[0] - start[0], end[1] - start[1])
    return _advance(start, direction, lower), _advance(start, direction, upper)


def _ray_extent(
    start: tuple[float, float],
    end: tuple[float, float],
    bounds: ViewportBounds,
) -> tuple[tuple[float, float], tuple[float, float]] | None:
    limits = _parameter_limits(start, end, bounds)
    if limits is None:
        return None
    _lower, upper = limits
    if upper <= 1e-10:
        return None
    direction = (end[0] - start[0], end[1] - start[1])
    return start, _advance(start, direction, upper)


def _parameter_limits(
    start: tuple[float, float],
    end: tuple[float, float],
    bounds: ViewportBounds,
) -> tuple[float, float] | None:
    direction = (end[0] - start[0], end[1] - start[1])
    if hypot(*direction) <= 1e-12:
        return None
    lower = float("-inf")
    upper = float("inf")
    for origin, delta, interval in (
        (start[0], direction[0], bounds.x_range),
        (start[1], direction[1], bounds.y_range),
    ):
        if abs(delta) <= 1e-12:
            if origin < interval[0] or origin > interval[1]:
                return None
            continue
        first = (interval[0] - origin) / delta
        second = (interval[1] - origin) / delta
        lower = max(lower, min(first, second))
        upper = min(upper, max(first, second))
    return (lower, upper) if lower <= upper else None


def _vector_mesh(
    start: tuple[float, float],
    end: tuple[float, float],
    bounds: ViewportBounds, # 视口边界对象
) -> pv.PolyData:
    """向量网格：一条线段作为杆，加一个填充三角形作为箭头。"""
    direction = (end[0] - start[0], end[1] - start[1]) 
    length = hypot(*direction) # 向量模长  
    if length <= 1e-12:
        return pv.PolyData()
    unit = (direction[0] / length, direction[1] / length) # 单位方向向量
    normal = (-unit[1], unit[0]) # 法向量，用于计算箭头底边的两个顶点
    # 0.34：箭头长度相对于向量长度的比例
    # 0.03：箭头最大长度 0.02：箭头最小长度
    size = min(length * 0.34, min(bounds.x_span, bounds.y_span) * 0.04)
    size = max(size, min(bounds.x_span, bounds.y_span) * 0.02)
    base = (end[0] - unit[0] * size, end[1] - unit[1] * size)
    half = size * 0.2
    left = (base[0] + normal[0] * half, base[1] + normal[1] * half)
    right = (base[0] - normal[0] * half, base[1] - normal[1] * half)
    # 杆延伸到箭头根部，避免线宽在尖端外露。
    points = np.array(
        [
            [start[0], start[1], 0.0],
            [base[0], base[1], 0.0],
            [end[0], end[1], 0.0],
            [left[0], left[1], 0.0],
            [right[0], right[1], 0.0],
        ],
        dtype=float,
    )
    mesh = pv.PolyData()
    mesh.points = points
    mesh.lines = np.array([2, 0, 1], dtype=np.int64)
    mesh.faces = np.array([3, 2, 3, 4], dtype=np.int64)
    return mesh


def _distance_to_linear(
    kind: LinearKind,
    start: tuple[float, float],
    end: tuple[float, float],
    query: tuple[float, float],
) -> float:
    """点到直线/线段/射线/向量的最短距离（世界单位）。"""
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length_squared = dx * dx + dy * dy
    if length_squared <= 1e-18:
        return hypot(query[0] - start[0], query[1] - start[1])
    parameter = ((query[0] - start[0]) * dx + (query[1] - start[1]) * dy) / length_squared
    if kind in {"segment", "vector"}:
        parameter = max(0.0, min(1.0, parameter))
    elif kind == "ray":
        parameter = max(0.0, parameter)
    projection = (start[0] + parameter * dx, start[1] + parameter * dy)
    return hypot(query[0] - projection[0], query[1] - projection[1])


def _advance(
    point: tuple[float, float],
    direction: tuple[float, float],
    parameter: float,
) -> tuple[float, float]:
    return point[0] + direction[0] * parameter, point[1] + direction[1] * parameter


def _segments_mesh(
    segments: Iterable[tuple[tuple[float, float], tuple[float, float]]],
) -> pv.PolyData:
    packed = list(segments)
    if not packed:
        return pv.PolyData()
    points = np.asarray(
        [(x, y, 0.0) for segment in packed for x, y in segment],
        dtype=float,
    )
    lines = np.empty((len(packed), 3), dtype=np.int64)
    lines[:, 0] = 2
    lines[:, 1] = np.arange(0, 2 * len(packed), 2)
    lines[:, 2] = np.arange(1, 2 * len(packed), 2)
    mesh = pv.PolyData()
    mesh.points = points
    mesh.lines = lines
    return mesh


def dashed_length_for(bounds: ViewportBounds) -> float:
    """Return the dash pitch shared by every dashed line in one viewport.

    节距只取决于视口跨度，与线段本身的长短无关，因此同一个窗格里的投影虚线、
    延长虚线等看起来疏密一致。
    """
    return max(min(bounds.x_span, bounds.y_span), 1e-9) * _DASH_LENGTH_RATIO


def _styled_segment_mesh(
    segment: tuple[tuple[float, float], tuple[float, float]] | None,
    style: str,
    *,
    dash_length: float | None = None,
) -> pv.PolyData:
    if segment is None:
        return pv.PolyData()
    if style != "dashed":
        return _segments_mesh([segment])
    start, end = segment
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = hypot(dx, dy)
    if length <= 1e-12:
        return pv.PolyData()
    # 短划线不依赖 VTK line stipple，跨平台输出一致。段数由线长除以统一节距换算，
    # 而不是固定段数：固定段数会让短线每段很短、长线每段很长，看起来一密一疏。
    if dash_length is not None and dash_length > 1e-12:
        dash_count = max(2, int(round(length / dash_length)))
    else:
        dash_count = 24
    if dash_count % 2:
        dash_count += 1
    pieces: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for index in range(dash_count):
        if index % 2:
            continue
        t0 = index / dash_count
        t1 = min(1.0, (index + _DASH_DUTY) / dash_count)
        pieces.append(
            (
                (start[0] + dx * t0, start[1] + dy * t0),
                (start[0] + dx * t1, start[1] + dy * t1),
            )
        )
    return _segments_mesh(pieces)


def _polygon_mesh(vertices: tuple[tuple[float, float], ...]) -> pv.PolyData:
    points = np.asarray([(x, y, 0.0) for x, y in vertices], dtype=float)
    faces = np.asarray([len(points), *range(len(points))], dtype=np.int64)
    return pv.PolyData(points, faces)


def _angle_arc_mesh(
    vertex: tuple[float, float],
    first: tuple[float, float],
    second: tuple[float, float],
    radius: float,
) -> pv.PolyData:
    v1 = (first[0] - vertex[0], first[1] - vertex[1])
    v2 = (second[0] - vertex[0], second[1] - vertex[1])
    n1 = hypot(*v1)
    n2 = hypot(*v2)
    if n1 <= 1e-12 or n2 <= 1e-12 or radius <= 0:
        return pv.PolyData()
    start = atan2(v1[1], v1[0])
    end = atan2(v2[1], v2[0])
    delta = (end - start) % (2 * pi)
    if delta > pi:
        delta -= 2 * pi
    angles = np.linspace(start, start + delta, 32)
    points = np.asarray(
        [(vertex[0] + radius * cos(angle), vertex[1] + radius * sin(angle), 0.0) for angle in angles],
        dtype=float,
    )
    lines = np.asarray([len(points), *range(len(points))], dtype=np.int64)
    mesh = pv.PolyData()
    mesh.points = points
    mesh.lines = lines
    return mesh


def _right_angle_mesh(
    vertex: tuple[float, float],
    first: tuple[float, float],
    second: tuple[float, float],
    size: float,
) -> pv.PolyData:
    v1 = (first[0] - vertex[0], first[1] - vertex[1])
    v2 = (second[0] - vertex[0], second[1] - vertex[1])
    n1 = hypot(*v1)
    n2 = hypot(*v2)
    if n1 <= 1e-12 or n2 <= 1e-12 or size <= 0:
        return pv.PolyData()
    u1 = (v1[0] / n1, v1[1] / n1)
    u2 = (v2[0] / n2, v2[1] / n2)
    p1 = (vertex[0] + size * u1[0], vertex[1] + size * u1[1])
    p2 = (vertex[0] + size * (u1[0] + u2[0]), vertex[1] + size * (u1[1] + u2[1]))
    p3 = (vertex[0] + size * u2[0], vertex[1] + size * u2[1])
    return _segments_mesh(((p1, p2), (p2, p3)))


def _mat_vec(matrix: tuple[tuple[float, float], tuple[float, float]], point: tuple[float, float]) -> tuple[float, float]:
    return (
        matrix[0][0] * point[0] + matrix[0][1] * point[1],
        matrix[1][0] * point[0] + matrix[1][1] * point[1],
    )


def _grid_mesh(
    bounds: tuple[float, float, float, float],
    step: float,
    *,
    matrix: tuple[tuple[float, float], tuple[float, float]] | None = None,
) -> pv.PolyData:
    xmin, xmax, ymin, ymax = bounds
    if step <= 0:
        return pv.PolyData()
    segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
    x_values = np.arange(xmin, xmax + step * 0.5, step)
    y_values = np.arange(ymin, ymax + step * 0.5, step)
    for x in x_values:
        segments.append(((float(x), ymin), (float(x), ymax)))
    for y in y_values:
        segments.append(((xmin, float(y)), (xmax, float(y))))
    if matrix is None:
        return _segments_mesh(segments)
    transformed = [(_mat_vec(matrix, start), _mat_vec(matrix, end)) for start, end in segments]
    return _segments_mesh(transformed)
