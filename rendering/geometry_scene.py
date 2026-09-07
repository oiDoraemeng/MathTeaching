"""二维点和线类对象的增量演员管理，含选中/悬浮高亮与命中测试。"""

from __future__ import annotations

from collections.abc import Iterable
from math import acos, atan2, cos, hypot, pi, sin

import numpy as np
import pyvista as pv

from models.geometry_2d import Annotation2D, Linear2D, LinearKind, Point2D, format_number
from rendering.ticks import ViewportBounds

_DRAFT_ACTOR = "geometry:draft"
_LABEL_ACTOR = "geometry:labels"
_ANNOTATION_ACTOR = "geometry:annotations"

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
    *,
    style: str = "solid",
) -> pv.PolyData:
    """生成适合当前视口的直线、线段、射线或向量网格。

    向量在末端附带一个填充三角形箭头（作为面单元），其余类型仅包含线段。
    """
    start_xy = _coordinates(start)
    end_xy = _coordinates(end)
    if kind == "line":
        segment = _line_extent(start_xy, end_xy, bounds)
        return _styled_segment_mesh(segment, style)
    if kind == "ray":
        segment = _ray_extent(start_xy, end_xy, bounds)
        return _styled_segment_mesh(segment, style)
    if kind == "vector":
        return _vector_mesh(start_xy, end_xy, bounds)
    return _styled_segment_mesh((start_xy, end_xy), style)


class GeometrySceneController:
    """管理二维交互对象，同时避免影响函数曲线和坐标辅助线。

    与 :class:`~rendering.two_d_scene.TwoDGuides` 一样，本控制器为每个点、线及其
    高亮光晕保留持久化演员，并用 ``copy_from`` 就地更新几何数据、用属性更新样式，
    而不是每帧删除并重建演员。所有内部绘制均以 ``render=False`` 调用，仅由调用方在
    操作结束后统一 ``plotter.render()``，从而消除拖动点、悬浮或选中时的闪烁。
    """

    def __init__(self, plotter: pv.Plotter, bounds: ViewportBounds) -> None:
        self.plotter = plotter
        self.bounds = bounds
        self.points: dict[str, Point2D] = {}
        self.linears: dict[str, Linear2D] = {}
        self.annotations: dict[str, Annotation2D] = {}
        self.order: list[str] = []
        self._hover_id: str | None = None
        self._selected_id: str | None = None
        self._has_labels = False
        self._draft_kind: LinearKind | None = None
        self._draft_start: tuple[float, float] | None = None
        self._draft_end: tuple[float, float] | None = None
        # 持久化演员与其就地更新的网格，键为演员名。
        self._meshes: dict[str, pv.PolyData] = {}
        self._actors: dict[str, object] = {}
        self._teaching_actors: dict[str, object] = {}

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
        self._refresh_labels()

    def add_linear(self, linear: Linear2D) -> None:
        self.linears[linear.id] = linear
        if linear.id not in self.order:
            self.order.append(linear.id)
        self._sync_linear(linear)
        self._refresh_annotations()

    def add_annotation(self, annotation: Annotation2D) -> None:
        self.annotations[annotation.id] = annotation
        if annotation.id not in self.order:
            self.order.append(annotation.id)
        self._refresh_annotations()

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
        self._refresh_labels()
        self._refresh_annotations()

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
        self._refresh_labels()
        self._refresh_annotations()

    def set_visible(self, object_id: str, visible: bool) -> None:
        if object_id in self.points:
            self.points[object_id].visible = visible
            self._sync_point(self.points[object_id])
            self._refresh_labels()
        if object_id in self.linears:
            self.linears[object_id].visible = visible
            self._sync_linear(self.linears[object_id])
        if object_id in self.annotations:
            self.annotations[object_id].visible = visible
            self._refresh_annotations()

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
            self._sync_linear(linear)
        self._refresh_labels()
        self._refresh_annotations()
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
        self._drop_actor(_DRAFT_ACTOR)
        self._draft_kind = None
        self._draft_start = None
        self._draft_end = None

    def clear_teaching(self) -> None:
        """Remove actors created by linear-algebra teaching primitives."""
        for name in tuple(self._teaching_actors):
            self.plotter.remove_actor(name, render=False)
        self._teaching_actors.clear()

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
        projection = _segments_mesh([(origin, foot)])
        residual = _segments_mesh([(foot, endpoint_xy)])
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
    ) -> None:
        original = _grid_mesh(bounds, step)
        transformed = _grid_mesh(bounds, step, matrix=matrix)
        suffix = f":{alias}" if alias else ""
        self._replace_teaching_actor(f"geometry:teaching:grid{suffix}:original", original, color="#a6afbd", line_width=1.0)
        self._replace_teaching_actor(f"geometry:teaching:grid{suffix}:transformed", transformed, color=color, line_width=2.0)

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
            self.plotter.remove_actor(name, render=False)
        actor = self.plotter.add_mesh(mesh, name=name, render=False, **kwargs)
        self._teaching_actors[name] = actor
        return actor

    def _drop_actor(self, name: str) -> None:
        """移除演员并清理持久化缓存。"""
        self.plotter.remove_actor(name, render=False)
        self._meshes.pop(name, None)
        self._actors.pop(name, None)

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
            render=False,
            render_points_as_spheres=False,
        )
        self._has_labels = True

    def _refresh_annotations(self) -> None:
        """刷新独立教学标注，不将其混入点名标签。"""
        add_labels = getattr(self.plotter, "add_point_labels", None)
        if add_labels is None:
            return
        self.plotter.remove_actor(_ANNOTATION_ACTOR, render=False)
        positions: list[tuple[float, float, float]] = []
        texts: list[str] = []
        colors: list[str] = []
        for annotation in self.annotations.values():
            if not annotation.visible:
                continue
            positions.append((annotation.x + annotation.offset_x, annotation.y + annotation.offset_y, 0.0))
            texts.append(annotation.text)
            colors.append(annotation.color)
        for linear in self.linears.values():
            if not linear.visible or not linear.label:
                continue
            start = self.points.get(linear.start_point_id)
            end = self.points.get(linear.end_point_id)
            if start is None or end is None:
                continue
            positions.append(((start.x + end.x) / 2.0, (start.y + end.y) / 2.0, 0.0))
            texts.append(linear.label)
            colors.append(linear.color)
        if not positions:
            return
        # PyVista 点标签演员只支持一个颜色；使用首个标注颜色保持轻量，
        # 后续可在需要时按颜色拆分演员。
        add_labels(
            positions,
            texts,
            font_size=14,
            text_color=colors[0],
            shape=None,
            show_points=False,
            always_visible=True,
            name=_ANNOTATION_ACTOR,
            render=False,
            render_points_as_spheres=False,
        )

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
        mesh = linear_mesh(kind, start, end, self.bounds)
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
    size = min(length * 0.34, min(bounds.x_span, bounds.y_span) * 0.03)
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


def _styled_segment_mesh(
    segment: tuple[tuple[float, float], tuple[float, float]] | None,
    style: str,
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
    # 固定数量的短划线不依赖 VTK line stipple，跨平台输出一致。
    dash_count = 16
    pieces: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for index in range(dash_count):
        if index % 2:
            continue
        t0 = index / dash_count
        t1 = min(1.0, (index + 0.62) / dash_count)
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
