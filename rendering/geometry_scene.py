"""二维点和线类对象的增量演员管理，含选中/悬浮高亮与命中测试。"""

from __future__ import annotations

from collections.abc import Iterable
from math import hypot

import numpy as np
import pyvista as pv

from models.geometry_2d import Linear2D, LinearKind, Point2D, format_number
from rendering.ticks import ViewportBounds

_DRAFT_ACTOR = "geometry:draft"
_LABEL_ACTOR = "geometry:labels"

_HOVER_HALO_COLOR = "#f0c674"
_SELECTED_HALO_COLOR = "#8ab4f8"
# 悬浮/选中时线宽的放大量。
_LINE_HALO_WIDTH = 7.0
_POINT_SIZE = 11.0
_POINT_HALO_SIZE = 24.0


def linear_mesh(
    kind: LinearKind,
    start: Point2D | tuple[float, float],
    end: Point2D | tuple[float, float],
    bounds: ViewportBounds,
) -> pv.PolyData:
    """生成适合当前视口的直线、线段、射线或向量网格。

    向量在末端附带一个填充三角形箭头（作为面单元），其余类型仅包含线段。
    """
    start_xy = _coordinates(start)
    end_xy = _coordinates(end)
    if kind == "line":
        segment = _line_extent(start_xy, end_xy, bounds)
        return _segments_mesh([segment] if segment is not None else [])
    if kind == "ray":
        segment = _ray_extent(start_xy, end_xy, bounds)
        return _segments_mesh([segment] if segment is not None else [])
    if kind == "vector":
        return _vector_mesh(start_xy, end_xy, bounds)
    return _segments_mesh([(start_xy, end_xy)])


class GeometrySceneController:
    """管理二维交互对象，同时避免影响函数曲线和坐标辅助线。"""

    def __init__(self, plotter: pv.Plotter, bounds: ViewportBounds) -> None:
        self.plotter = plotter
        self.bounds = bounds
        self.points: dict[str, Point2D] = {}
        self.linears: dict[str, Linear2D] = {}
        self.order: list[str] = []
        self._hover_id: str | None = None
        self._selected_id: str | None = None
        self._has_labels = False
        self._draft_kind: LinearKind | None = None
        self._draft_start: tuple[float, float] | None = None
        self._draft_end: tuple[float, float] | None = None

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

    def add_point(self, point: Point2D) -> None:
        self.points[point.id] = point
        if point.id not in self.order:
            self.order.append(point.id)
        self._replace_point_actor(point)
        self._refresh_labels()

    def add_linear(self, linear: Linear2D) -> None:
        self.linears[linear.id] = linear
        if linear.id not in self.order:
            self.order.append(linear.id)
        self._replace_linear_actor(linear)

    def move_point(self, point_id: str, x: float, y: float) -> None:
        """更新点坐标，并联动刷新依赖它的线类对象和标签。"""
        point = self.points.get(point_id)
        if point is None:
            return
        point.x = float(x)
        point.y = float(y)
        self._replace_point_actor(point)
        for linear in self.linears.values():
            if point_id in {linear.start_point_id, linear.end_point_id}:
                self._replace_linear_actor(linear)
        self._refresh_labels()

    def remove_object(self, object_id: str) -> None:
        for name in (
            self.point_actor_name(object_id),
            self.point_halo_name(object_id),
            self.linear_actor_name(object_id),
            self.linear_halo_name(object_id),
        ):
            self.plotter.remove_actor(name, render=False)
        self.points.pop(object_id, None)
        self.linears.pop(object_id, None)
        self.order = [item for item in self.order if item != object_id]
        if self._hover_id == object_id:
            self._hover_id = None
        if self._selected_id == object_id:
            self._selected_id = None
        self._refresh_labels()

    def set_visible(self, object_id: str, visible: bool) -> None:
        if object_id in self.points:
            self.points[object_id].visible = visible
            self._replace_point_actor(self.points[object_id])
            self._refresh_labels()
        if object_id in self.linears:
            self.linears[object_id].visible = visible
            self._replace_linear_actor(self.linears[object_id])

    def set_hover(self, object_id: str | None) -> bool:
        """设置悬浮对象，返回悬浮目标是否发生变化。"""
        if object_id == self._hover_id:
            return False
        previous = self._hover_id
        self._hover_id = object_id
        self._restyle(previous)
        self._restyle(object_id)
        self._refresh_labels()
        return True

    def set_selected(self, object_id: str | None) -> bool:
        """设置选中对象，返回选中目标是否发生变化。"""
        if object_id == self._selected_id:
            return False
        previous = self._selected_id
        self._selected_id = object_id
        self._restyle(previous)
        self._restyle(object_id)
        self._refresh_labels()
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
        return best_linear[1] if best_linear is not None else None

    def set_bounds(self, bounds: ViewportBounds) -> None:
        """更新依赖视口范围的直线、射线、向量箭头、标签和临时预览。"""
        self.bounds = bounds
        for linear in self.linears.values():
            self._replace_linear_actor(linear)
        self._refresh_labels()
        if (
            self._draft_kind is not None
            and self._draft_start is not None
            and self._draft_end is not None
        ):
            self._replace_draft(self._draft_kind, self._draft_start, self._draft_end)

    def set_draft(
        self,
        kind: LinearKind,
        start: Point2D | tuple[float, float],
        end: tuple[float, float],
    ) -> None:
        self._draft_kind = kind
        self._draft_start = _coordinates(start)
        self._draft_end = end
        self._replace_draft(kind, self._draft_start, end)

    def clear_draft(self) -> None:
        self.plotter.remove_actor(_DRAFT_ACTOR, render=False)
        self._draft_kind = None
        self._draft_start = None
        self._draft_end = None

    def _restyle(self, object_id: str | None) -> None:
        if object_id is None:
            return
        if object_id in self.points:
            self._replace_point_actor(self.points[object_id])
        elif object_id in self.linears:
            self._replace_linear_actor(self.linears[object_id])

    def _replace_point_actor(self, point: Point2D) -> None:
        halo_name = self.point_halo_name(point.id)
        actor_name = self.point_actor_name(point.id)
        self.plotter.remove_actor(halo_name, render=False)
        self.plotter.remove_actor(actor_name, render=False)
        if not point.visible:
            return
        # Point sprites keep a stable screen-space size while preserving the
        # exact world coordinate of the point.
        point_mesh = _point_mesh(point.x, point.y)
        halo = self._point_halo_style(point.id)
        if halo is not None:
            halo_color, halo_multiplier = halo
            halo_size = _POINT_HALO_SIZE if halo_multiplier >= 2.0 else 18.0
            halo_actor = self.plotter.add_mesh(
                point_mesh.copy(),
                name=halo_name,
                color=halo_color,
                opacity=0.35,
                lighting=False,
                point_size=halo_size,
                render_points_as_spheres=True,
            )
            halo_actor.visibility = True
        actor = self.plotter.add_mesh(
            point_mesh,
            name=actor_name,
            color=point.color,
            lighting=False,
            point_size=_POINT_SIZE,
            render_points_as_spheres=True,
        )
        actor.visibility = True

    def _point_halo_style(self, point_id: str) -> tuple[str, float] | None:
        if point_id == self._selected_id:
            return _SELECTED_HALO_COLOR, 2.2  # 光晕倍数
        if point_id == self._hover_id:
            return _HOVER_HALO_COLOR, 1.8
        return None

    def _replace_linear_actor(self, linear: Linear2D) -> None:
        halo_name = self.linear_halo_name(linear.id)
        actor_name = self.linear_actor_name(linear.id)
        self.plotter.remove_actor(halo_name, render=False)
        self.plotter.remove_actor(actor_name, render=False)
        start = self.points.get(linear.start_point_id)
        end = self.points.get(linear.end_point_id)
        if start is None or end is None or not linear.visible:
            return
        mesh = linear_mesh(linear.kind, start, end, self.bounds)
        if mesh.n_points == 0 or mesh.n_cells == 0:
            return
        highlight = self._linear_highlight_color(linear.id)
        if highlight is not None:
            halo_actor = self.plotter.add_mesh(
                mesh.copy(),
                name=halo_name,
                color=highlight,
                line_width=linear.line_width + _LINE_HALO_WIDTH,
                opacity=0.4,
                render_lines_as_tubes=False,
                show_vertices=False,
                lighting=False,
            )
            halo_actor.visibility = True
        actor = self.plotter.add_mesh(
            mesh,
            name=actor_name,
            color=linear.color,
            line_width=linear.line_width,
            render_lines_as_tubes=False,
            show_vertices=False,
            lighting=False,
        )
        actor.visibility = True

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
        for point in self.points.values():
            if not point.visible:
                continue
            positions.append((point.x + offset, point.y + offset, 0.0))
            texts.append(self._point_label_text(point))
        if not positions:
            return
        add_labels(
            positions,
            texts,
            font_size=13,
            text_color="#1f2937",
            shape=None,
            show_points=False,
            always_visible=True,
            name=_LABEL_ACTOR,
            render_points_as_spheres=False,
        )
        self._has_labels = True

    def _point_label_text(self, point: Point2D) -> str:
        if point.id in {self._selected_id, self._hover_id}:
            return f"{point.name} = ({format_number(point.x)}, {format_number(point.y)})"
        return point.name

    def _label_offset(self) -> float:
        return min(self.bounds.x_span, self.bounds.y_span) * 0.015

    def _replace_draft(
        self,
        kind: LinearKind,
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> None:
        self.plotter.remove_actor(_DRAFT_ACTOR, render=False)
        mesh = linear_mesh(kind, start, end, self.bounds)
        if mesh.n_points == 0 or mesh.n_cells == 0:
            return
        actor = self.plotter.add_mesh(
            mesh,
            name=_DRAFT_ACTOR,
            color="#6c7b8d",
            opacity=0.72,
            line_width=1.5,
            render_lines_as_tubes=False,
            show_vertices=False,
            lighting=False,
        )
        actor.visibility = True


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
    bounds: ViewportBounds,
) -> pv.PolyData:
    """向量网格：一条线段作为杆，加一个填充三角形作为箭头。"""
    direction = (end[0] - start[0], end[1] - start[1])
    length = hypot(*direction)
    if length <= 1e-12:
        return pv.PolyData()
    unit = (direction[0] / length, direction[1] / length)
    normal = (-unit[1], unit[0])
    size = min(length * 0.34, min(bounds.x_span, bounds.y_span) * 0.035)
    size = max(size, min(bounds.x_span, bounds.y_span) * 0.014)
    base = (end[0] - unit[0] * size, end[1] - unit[1] * size)
    half = size * 0.5
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
