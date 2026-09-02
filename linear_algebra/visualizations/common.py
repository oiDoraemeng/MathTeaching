"""Deterministic, renderer-independent visualization recipe primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

from linear_algebra.catalog.model import LessonEntry
from services.scene_commands import CommandPlan


@dataclass(frozen=True)
class RenderContext:
    topic_id: str
    bounds: tuple[float, float, float, float] = (-3.0, 3.0, -3.0, 3.0)
    seed: int = 17

    @classmethod
    def default(cls, topic_id: str) -> "RenderContext":
        # A stable seed is useful when a future lesson adds parameterized samples.
        return cls(topic_id=topic_id, seed=17)


@dataclass(frozen=True)
class VisualizationRecipe:
    id: str
    scene: Literal["2d", "3d"]
    required_capabilities: tuple[str, ...]
    builder: Callable[[RenderContext], CommandPlan]


def recipe_for_entry(entry: LessonEntry) -> VisualizationRecipe:
    """Create visualization recipe from lesson entry using topic-specific builders."""
    from .builders import get_builder_for

    # Get topic-specific builder
    builder_func = get_builder_for(entry.visualization_id)

    if builder_func is None:
        # All 54 topics must have builders - no fallback
        raise ValueError(
            f"No builder found for {entry.visualization_id}. "
            f"All topics must have a specific builder."
        )

    scene: Literal["2d", "3d"] = "3d" if _uses_3d(entry.required_capabilities) else "2d"

    return VisualizationRecipe(
        id=entry.visualization_id,
        scene=scene,
        required_capabilities=entry.required_capabilities,
        builder=builder_func,
    )



def _uses_3d(capabilities: tuple[str, ...]) -> bool:
    return any(
        capability in capabilities
        for capability in ("vector_3d", "right_hand_3d", "parallelepiped_3d", "oriented_volume_3d")
    )


def _build_plan(context: RenderContext, entry: LessonEntry, scene: Literal["2d", "3d"]) -> CommandPlan:
    capabilities = set(entry.required_capabilities)
    operations: list[dict[str, object]] = []
    if scene == "3d":
        operations.extend(_three_d_geometry(capabilities))
    else:
        operations.extend(_two_d_geometry(capabilities))
    if "annotation_formula" in capabilities:
        position: list[float] = [1.1, 2.0, 1.1] if scene == "3d" else [1.1, 2.0]
        operations.append({"op": "annotation.formula", "alias": "formula", "text": _formula_for(entry.title), "position": position})
    operations.append({"op": "view.fit", "padding": 1.15})
    return CommandPlan(scene=scene, operations=tuple(operations), summary=entry.title)


def _two_d_geometry(capabilities: set[str]) -> list[dict[str, object]]:
    operations: list[dict[str, object]] = []
    if "vector_2d" in capabilities or "angle_2d" in capabilities or "right_angle_2d" in capabilities or "projection_2d" in capabilities:
        operations.extend(_vector_2d_operations())
    if "polygon_2d" in capabilities:
        operations.append({"op": "geometry.polygon", "alias": "parallelogram", "vertices": [[0, 0], [2, 1], [3, 3], [1, 2]], "color": "#5b8def", "opacity": 0.24, "outline": True})
    if "angle_2d" in capabilities:
        operations.append({"op": "geometry.angle_arc", "alias": "angle", "vertex": [0, 0], "first": [2, 0], "second": [1, 2], "radius": 0.45})
    if "right_angle_2d" in capabilities:
        operations.append({"op": "geometry.right_angle_marker", "alias": "right-angle", "vertex": [0, 0], "first": [2, 0], "second": [0, 2], "size": 0.3})
    if "projection_2d" in capabilities:
        operations.append({"op": "geometry.projection", "vector": [2.5, 1.8], "direction": [2, 0.8], "result_alias": "projection", "foot_alias": "H", "residual_alias": "residual"})
    if "transformed_grid" in capabilities:
        operations.append({"op": "geometry.transformed_grid", "matrix": [[1.2, 0.4], [-0.2, 1.1]], "bounds": [-3, 3, -3, 3], "step": 1.0})
    if "subspace_region" in capabilities:
        operations.append({"op": "geometry.subspace_region", "basis": [[1, 0], [0.5, 0.5]], "bounds": [-3, 3, -3, 3], "color": "#4c9f70", "opacity": 0.2})
    if "staged_transform" in capabilities:
        operations.append({"op": "geometry.staged_transform", "matrices": [[[1.2, 0], [0, 0.8]], [[0, -1], [1, 0]]], "points": [[1, 0], [0, 1], [1, 1]], "aliases": ["p", "q", "r"]})
    if "oriented_area_2d" in capabilities:
        operations.append({"op": "geometry.oriented_area", "alias": "oriented-area", "vectors": [[2, 0.5], [0.6, 1.8]], "color": "#d97845", "opacity": 0.28})
    return operations


def _vector_2d_operations() -> list[dict[str, object]]:
    return [
        {"op": "point.upsert", "alias": "O", "coordinates": [0, 0], "name": "O"},
        {"op": "point.upsert", "alias": "A", "coordinates": [2.5, 1.8], "name": "A"},
        {"op": "linear.upsert", "alias": "v", "start": "O", "end": "A", "kind": "vector", "role": "primary", "style": "solid"},
    ]


def _three_d_geometry(capabilities: set[str]) -> list[dict[str, object]]:
    operations: list[dict[str, object]] = [
        {"op": "linear3d.upsert", "alias": "u", "start": [0, 0, 0], "end": [2, 0.5, 1.5], "kind": "vector", "role": "primary"},
        {"op": "linear3d.upsert", "alias": "v", "start": [0, 0, 0], "end": [-0.3, 2, 0.8], "kind": "vector", "role": "result"},
    ]
    if "parallelepiped_3d" in capabilities or "oriented_volume_3d" in capabilities:
        operations.append({"op": "geometry.parallelepiped", "alias": "volume-box", "origin": [0, 0, 0], "vectors": [[2, 0.5, 1.5], [-0.3, 2, 0.8], [0.2, -0.4, 2.2]], "color": "#4c9f70", "opacity": 0.2})
    else:
        operations.append({"op": "plane3d.upsert", "alias": "span-plane", "origin": [0, 0, 0], "normal": [0, 0, 1], "size": 4, "color": "#5b8def", "opacity": 0.18})
    return operations


def _formula_for(title: str) -> str:
    if "行列式" in title or "面积" in title:
        return r"\det(A)=ad-bc"
    if "内积" in title or "投影" in title:
        return r"\operatorname{proj}_{u}v=\frac{v\cdot u}{u\cdot u}u"
    if "秩" in title or "空间" in title:
        return r"\dim(\operatorname{im}A)+\dim(\ker A)=n"
    if "体积" in title or "混合积" in title:
        return r"V=|a\cdot(b\times c)|"
    return r"v=(x,y),\quad \|v\|=\sqrt{x^2+y^2}"
