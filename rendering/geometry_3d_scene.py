"""PyVista adapter for the reusable three-dimensional teaching primitives."""

from __future__ import annotations

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


# Teaching vectors should read as directional arrows rather than thick rods.
# The arrowhead geometry is kept modest, while the shaft itself is a VTK line
# whose width is specified in screen pixels and therefore is zoom invariant.
_VECTOR_TIP_LENGTH = 0.14
_VECTOR_TIP_RADIUS = 0.045
_VECTOR_LINE_WIDTH = 2.0


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

    def clear(self) -> None:
        for name in tuple(self.actors):
            self._remove(name)
        self.linears.clear()
        self.planes.clear()
        self.solids.clear()

    def remove_alias(self, alias: str) -> None:
        """Remove every actor owned by one lesson alias."""
        for prefix in (f"geometry3d:linear:{alias}", f"geometry3d:plane:{alias}", f"geometry3d:solid:{alias}", f"geometry3d:annotation:{alias}"):
            self._remove(prefix)
        self.linears.pop(alias, None)
        self.planes.pop(alias, None)
        self.solids.pop(alias, None)

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
    ) -> object:
        model = Linear3D(alias, _v3(start), _v3(end), kind=kind, color=color, line_width=line_width, role=role)  # type: ignore[arg-type]
        name = f"geometry3d:linear:{alias}"
        self._remove(name)
        if model.kind == "vector":
            mesh = line_arrow_mesh(
                model.start,
                model.end,
                tip_length_ratio=_VECTOR_TIP_LENGTH,
                tip_radius_ratio=_VECTOR_TIP_RADIUS,
            )
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

    def add_projection3d(self, alias: str, vector: Vector3, foot: Vector3, residual: Vector3, *, color: str = "#2777b6") -> None:
        """Render bounded projection foot/residual geometry with stable aliases."""
        self.add_linear(f"{alias}__projection", (0.0, 0.0, 0.0), _v3(foot), color=color, kind="segment")
        self.add_linear(f"{alias}__residual", _v3(foot), _v3(vector), color="#d97845", kind="segment")

    def add_orthogonalization_stage(self, alias: str, residual: Vector3, normalized: Vector3, *, color: str = "#4c9f70") -> None:
        """Render one Gram–Schmidt residual and normalized direction."""
        self.add_linear(f"{alias}__residual", (0.0, 0.0, 0.0), _v3(residual), color="#d97845", kind="segment")
        self.add_linear(f"{alias}__normalized", (0.0, 0.0, 0.0), _v3(normalized), color=color, kind="vector")

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
