"""PyVista adapter for the reusable three-dimensional teaching primitives."""

from __future__ import annotations

import math
from typing import Iterable

import numpy as np
import pyvista as pv

from models.geometry_3d import (
    Linear3D,
    Parallelogram3D,
    Parallelepiped3D,
    Plane3D,
    Vector3,
)
from rendering.line_arrow_3d import line_arrow_mesh



# 箭杆是 VTK 线段，线宽本来就是屏幕像素；箭头头部则必须是实体几何（锥体），
# 所以它的世界尺寸由「像素尺寸 × 当前相机下每像素代表多少世界单位」换算得到，
# 这样拉近/推远/滚轮缩放都不会改变它在屏幕上看到的大小。
# 相机与视口都取不到时（无渲染窗口的宿主）退回固定世界尺寸。
_VECTOR_TIP_LENGTH = 0.14 # 箭头长度（兜底）
_VECTOR_TIP_RADIUS = 0.025 # 箭头半径，也就是粗细（兜底）
# Use the same compact visual target as a default toolbar-created vector.
# The world dimensions are derived from each tip's camera depth, keeping this
# pixel size consistent for lesson vectors at different depths as well.
_VECTOR_TIP_LENGTH_PX = 15.0 # 箭头长度，屏幕像素
_VECTOR_TIP_RADIUS_PX = 4.0 # 箭头半径，也就是粗细，屏幕像素
# 头部再大也不能吃掉半支箭头：超过这个比例就等比缩小。
_VECTOR_TIP_MAX_VECTOR_RATIO = 0.3
_VECTOR_LINE_WIDTH = 3.2


class Geometry3DSceneController:
    """Owns only actors created for linear-algebra geometry.

    Actor names are stable, allowing command transactions and redraws to remove
    exactly the objects that this controller owns without clearing other scene
    layers such as surfaces or axes.
    """

    def __init__(self, plotter: object) -> None:
        self.plotter = plotter
        self.actors: dict[str, object] = {}
        self.linears: dict[str, Linear3D] = {}
        self.planes: dict[str, Plane3D] = {}
        self.solids: dict[str, Parallelogram3D | Parallelepiped3D] = {}
        # 每个向量头上一次使用的世界尺寸，用来跳过无意义的重复重建。
        self._arrow_tip_lengths: dict[str, float] = {}
        self._last_world_per_pixel: float | None = None

    def clear(self) -> None:
        for name in tuple(self.actors):
            self._remove(name)
        self.linears.clear()
        self.planes.clear()
        self.solids.clear()
        self._arrow_tip_lengths.clear()

    def remove_alias(self, alias: str) -> None:
        """Remove every actor owned by one lesson alias."""
        prefixes = (
            f"geometry3d:linear:{alias}",
            f"geometry3d:plane:{alias}",
            f"geometry3d:solid:{alias}",
            f"geometry3d:annotation:{alias}",
            f"geometry3d:quadratic:{alias}",
        )
        for name in tuple(self.actors):
            if any(
                name == prefix
                or name.startswith(f"{prefix}__")
                or name.startswith(f"{prefix}:")
                for prefix in prefixes
            ):
                self._remove(name)
        for collection in (self.linears, self.planes, self.solids):
            for child_alias in tuple(collection):
                if child_alias == alias or child_alias.startswith(f"{alias}__"):
                    collection.pop(child_alias, None)

    def set_visible(self, alias: str, visible: bool) -> None:
        """Show or hide all 3D actors belonging to one semantic alias."""
        for name, actor in self.actors.items():
            actor_alias = name.rsplit(":", 1)[-1]
            if actor_alias != alias and not actor_alias.startswith(f"{alias}__"):
                continue
            set_visibility = getattr(actor, "SetVisibility", None)
            if callable(set_visibility):
                set_visibility(bool(visible))
            elif hasattr(actor, "visibility"):
                actor.visibility = bool(visible)

    def add_linear(
        self,
        alias: str,
        start: Vector3,
        end: Vector3,
        *,
        kind: str = "vector",
        color: str = "#2777b6",
        line_width: float = _VECTOR_LINE_WIDTH,
        role: str = "primary",
        style: str = "solid",
    ) -> object:
        model = Linear3D(alias, _v3(start), _v3(end), kind=kind, color=color, line_width=line_width, role=role, style=style)  # type: ignore[arg-type]
        name = f"geometry3d:linear:{alias}"
        self._remove(name)
        if model.kind == "vector":
            tip_length, tip_radius = self._arrow_head(model.start, model.end)
            mesh = line_arrow_mesh(
                model.start,
                model.end,
                tip_length=tip_length,
                tip_radius=tip_radius,
            )
            self._arrow_tip_lengths[alias] = tip_length
        elif model.style == "dashed":
            # 被压到零的方向、投影连线等辅助构造按虚线画；用固定段数的短划线而不是
            # VTK line stipple，跨平台输出一致（与二维渲染器同一策略）。
            mesh = _dashed_segment_mesh(model.start, model.end)
        else:
            mesh = pv.Line(model.start, model.end)
        actor = self._add(
            mesh,
            name=name,
            color=model.color,
            line_width=model.line_width,
            lighting=False,
            render_lines_as_tubes=False,
        )
        self.linears[alias] = model
        return actor

    def refresh_vector_heads(self) -> bool:
        """Resize every vector head in place after a camera change.

        The head is solid geometry, so a dolly or a wheel zoom would visibly
        grow/shrink it; recomputing its world size from the current pixels keeps
        it constant on screen.  ``mapper.dataset`` is replaced in place rather
        than removing and re-adding the actor: a new actor would start visible
        and silently undo the storyboard mask of every case pane.

        The host calls this for each camera-interaction frame.  Coordinate axes
        remain ordinary world-space geometry and are never rebuilt here.
        """
        changed = False
        for alias, model in tuple(self.linears.items()):
            if model.kind != "vector":
                continue
            actor = self.actors.get(f"geometry3d:linear:{alias}")
            mapper = getattr(actor, "mapper", None)
            if mapper is None:
                continue
            tip_length, tip_radius = self._arrow_head(model.start, model.end)
            previous = self._arrow_tip_lengths.get(alias)
            if previous is not None and abs(tip_length - previous) <= max(1e-6, previous * 5e-3):
                continue
            mesh = line_arrow_mesh(model.start, model.end, tip_length=tip_length, tip_radius=tip_radius)
            try:
                mapper.dataset = mesh
            except AttributeError:
                continue
            self._arrow_tip_lengths[alias] = tip_length
            changed = True
        return changed

    def _viewport_height(self) -> float:
        """Return the renderer's pixel height, or 0 when it cannot be measured."""
        candidates: list[object] = []
        renderer = getattr(self.plotter, "renderer", None)
        get_size = getattr(renderer, "GetSize", None)
        if callable(get_size):
            candidates.append(get_size())
        render_window = getattr(self.plotter, "render_window", None)
        get_size = getattr(render_window, "GetSize", None)
        if callable(get_size):
            candidates.append(get_size())
        window_size = getattr(self.plotter, "window_size", None)
        if window_size is not None:
            candidates.append(window_size)
        interactor = getattr(self.plotter, "interactor", None)
        height = getattr(interactor, "height", None)
        if callable(height):
            candidates.append((0.0, height()))
        for size in candidates:
            try:
                value = float(size[1])  # type: ignore[index]
            except (IndexError, TypeError, ValueError):
                continue
            if value > 0.0:
                return value
        return 0.0

    def _world_per_pixel(self, point: Vector3 | None = None) -> float | None:
        """World units covered by one vertical pixel at a point's camera depth."""
        renderer = getattr(self.plotter, "renderer", None)
        camera = getattr(renderer, "camera", None)
        if camera is None:
            camera = getattr(self.plotter, "camera", None)
        height = self._viewport_height()
        if camera is None or height <= 0.0:
            return None
        try:
            if bool(camera.GetParallelProjection()):
                visible_height = 2.0 * float(camera.GetParallelScale())
            else:
                position = np.asarray(camera.GetPosition(), dtype=float)
                focal_point = np.asarray(camera.GetFocalPoint(), dtype=float)
                direction = focal_point - position
                distance = float(np.linalg.norm(direction))
                if not math.isfinite(distance) or distance <= 1e-9:
                    return None
                if point is not None:
                    # Perspective projection scales with view-axis depth, not
                    # Euclidean distance.  Use the head tip so vectors that
                    # point toward or away from the camera stay equal in pixels.
                    candidate = float(np.dot(np.asarray(point, dtype=float) - position, direction / distance))
                    if math.isfinite(candidate) and candidate > 1e-9:
                        distance = candidate
                view_angle = math.radians(float(camera.GetViewAngle()))
                visible_height = 2.0 * distance * math.tan(view_angle / 2.0)
        except (AttributeError, TypeError, ValueError):
            return None
        if not math.isfinite(visible_height) or visible_height <= 0.0:
            return None
        return visible_height / height

    def _arrow_head(self, start: Vector3, end: Vector3) -> tuple[float, float]:
        """Return the world-space head (length, radius) for one vector."""
        length = math.sqrt(sum((float(b) - float(a)) ** 2 for a, b in zip(start, end)))
        world_per_pixel = self._world_per_pixel(end)
        if world_per_pixel is not None:
            self._last_world_per_pixel = world_per_pixel
        else:
            # 视口还没准备好时沿用上一次量到的比例，避免头部突然缩回兜底尺寸。
            world_per_pixel = self._last_world_per_pixel
        if world_per_pixel is None:
            tip_length, tip_radius = _VECTOR_TIP_LENGTH, _VECTOR_TIP_RADIUS
        else:
            tip_length = _VECTOR_TIP_LENGTH_PX * world_per_pixel
            tip_radius = _VECTOR_TIP_RADIUS_PX * world_per_pixel
        cap = length * _VECTOR_TIP_MAX_VECTOR_RATIO
        if tip_length > cap > 0.0:
            shrink = cap / tip_length
            tip_length *= shrink
            tip_radius *= shrink
        return tip_length, tip_radius

    def add_projection3d(self, alias: str, vector: Vector3, foot: Vector3, residual: Vector3, *, color: str = "#2777b6") -> None:
        """Render bounded projection foot/residual geometry with stable aliases."""
        self.add_linear(f"{alias}__projection", (0.0, 0.0, 0.0), _v3(foot), color=color, kind="segment")
        self.add_linear(f"{alias}__residual", _v3(foot), _v3(vector), color="#d97845", kind="segment")

    def add_orthogonalization_stage(self, alias: str, residual: Vector3, normalized: Vector3, *, color: str = "#4c9f70") -> None:
        """Render one Gram–Schmidt residual and normalized direction."""
        self.add_linear(f"{alias}__residual", (0.0, 0.0, 0.0), _v3(residual), color="#d97845", kind="segment")
        self.add_linear(f"{alias}__normalized", (0.0, 0.0, 0.0), _v3(normalized), color=color, kind="vector")

    def add_quadratic_mesh(self, alias: str, vertices: Iterable[Vector3], faces: Iterable[tuple[int, int, int]], *, color: str = "#4c9f70") -> None:
        points = tuple(_v3(point) for point in vertices)
        cells = tuple(tuple(int(index) for index in face) for face in faces)
        if not points or not cells:
            return
        mesh = pv.PolyData(np.asarray(points), np.asarray([(3, *face) for face in cells], dtype=np.int64).ravel())
        self._add(mesh, name=f"geometry3d:quadratic:{alias}:mesh", color=color, opacity=0.35)
        self.actors[f"geometry3d:quadratic:{alias}:mesh"] = self.actors.get(f"geometry3d:quadratic:{alias}:mesh")

    def add_plane(
        self,
        alias: str,
        origin: Vector3,
        normal: Vector3,
        *,
        size: float = 2.0,
        opacity: float = 0.24,
        color: str = "#5b8def",
    ) -> object:
        model = Plane3D(alias, _v3(origin), _v3(normal), float(size), float(opacity), color)
        name = f"geometry3d:plane:{alias}"
        self._remove(name)
        mesh = pv.Plane(center=model.origin, direction=model.normal, i_size=model.size, j_size=model.size)
        actor = self._add(mesh, name=name, color=model.color, opacity=model.opacity)
        self.planes[alias] = model
        return actor

    def add_parallelogram(
        self,
        alias: str,
        origin: Vector3,
        vectors: Iterable[Vector3],
        *,
        opacity: float = 0.24,
        color: str = "#4c9f70",
    ) -> object:
        values = tuple(_v3(vector) for vector in vectors)
        if len(values) != 2:
            raise ValueError("A parallelogram requires two vectors")
        model = Parallelogram3D(alias, _v3(origin), (values[0], values[1]), float(opacity), color)
        name = f"geometry3d:solid:{alias}"
        self._remove(name)
        mesh = _parallelogram_mesh(model.origin, model.vectors)
        actor = self._add(mesh, name=name, color=model.color, opacity=model.opacity, show_edges=True)
        self.solids[alias] = model
        return actor

    def add_parallelepiped(
        self,
        alias: str,
        origin: Vector3,
        vectors: Iterable[Vector3],
        *,
        opacity: float = 0.2,
        color: str = "#4c9f70",
    ) -> object:
        values = tuple(_v3(vector) for vector in vectors)
        if len(values) != 3:
            raise ValueError("A parallelepiped requires three vectors")
        model = Parallelepiped3D(alias, _v3(origin), (values[0], values[1], values[2]), float(opacity), color)
        name = f"geometry3d:solid:{alias}"
        self._remove(name)
        mesh = _parallelepiped_mesh(model.origin, model.vectors)
        actor = self._add(mesh, name=name, color=model.color, opacity=model.opacity, show_edges=True)
        self.solids[alias] = model
        return actor

    def add_oriented_volume(
        self,
        alias: str,
        origin: Vector3,
        vectors: Iterable[Vector3],
        *,
        opacity: float = 0.2,
        color: str = "#d97845",
    ) -> object:
        """Render the parallelepiped used to explain a signed volume."""
        return self.add_parallelepiped(alias, origin, vectors, opacity=opacity, color=color)

    def _add(self, mesh: object, *, name: str, **kwargs: object) -> object:
        actor = self.plotter.add_mesh(mesh, name=name, render=False, **kwargs)
        self.actors[name] = actor
        return actor

    def _remove(self, name: str) -> None:
        if name not in self.actors:
            return
        remove_actor = getattr(self.plotter, "remove_actor", None)
        if callable(remove_actor):
            remove_actor(name, render=False)
        self.actors.pop(name, None)


def _v3(value: Iterable[float]) -> Vector3:
    values = tuple(float(item) for item in value)
    if len(values) != 3 or not all(np.isfinite(values)):
        raise ValueError("A 3D vector must contain three finite numbers")
    return values  # type: ignore[return-value]


def _dashed_segment_mesh(start: Vector3, end: Vector3) -> pv.PolyData:
    """Return a dashed polyline from ``start`` to ``end`` in world space."""

    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dz = end[2] - start[2]
    if math.sqrt(dx * dx + dy * dy + dz * dz) <= 1e-12:
        return pv.PolyData()
    dash_count = 16
    pieces: list[tuple[Vector3, Vector3]] = []
    for index in range(dash_count):
        if index % 2:
            continue
        t0 = index / dash_count
        t1 = min(1.0, (index + 0.62) / dash_count)
        pieces.append(
            (
                (start[0] + dx * t0, start[1] + dy * t0, start[2] + dz * t0),
                (start[0] + dx * t1, start[1] + dy * t1, start[2] + dz * t1),
            )
        )
    points = np.asarray([point for piece in pieces for point in piece], dtype=float)
    lines = np.empty((len(pieces), 3), dtype=np.int64)
    lines[:, 0] = 2
    lines[:, 1] = np.arange(0, 2 * len(pieces), 2)
    lines[:, 2] = np.arange(1, 2 * len(pieces), 2)
    mesh = pv.PolyData()
    mesh.points = points
    mesh.lines = lines
    return mesh


def _parallelogram_mesh(origin: Vector3, vectors: tuple[Vector3, Vector3]) -> pv.PolyData:
    a, b = vectors
    points = np.asarray([origin, _add(origin, a), _add(_add(origin, a), b), _add(origin, b)], dtype=float)
    return pv.PolyData(points, np.asarray([4, 0, 1, 2, 3], dtype=np.int64))


def _parallelepiped_mesh(origin: Vector3, vectors: tuple[Vector3, Vector3, Vector3]) -> pv.PolyData:
    a, b, c = vectors
    p0 = origin
    p1 = _add(p0, a)
    p2 = _add(p0, b)
    p3 = _add(p1, b)
    p4 = _add(p0, c)
    p5 = _add(p1, c)
    p6 = _add(p2, c)
    p7 = _add(p3, c)
    points = np.asarray([p0, p1, p2, p3, p4, p5, p6, p7], dtype=float)
    faces = np.asarray(
        [4, 0, 1, 3, 2, 4, 4, 6, 7, 5, 4, 0, 2, 6, 4, 4, 1, 5, 7, 3, 4, 0, 4, 5, 1, 4, 2, 3, 7, 6],
        dtype=np.int64,
    )
    return pv.PolyData(points, faces)


def _add(a: Vector3, b: Vector3) -> Vector3:
    return a[0] + b[0], a[1] + b[1], a[2] + b[2]
