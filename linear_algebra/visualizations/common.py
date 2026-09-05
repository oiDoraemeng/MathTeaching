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
    render_profile: str = "lecture-v1"

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
