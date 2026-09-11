"""Deterministic resource budgets for renderer-independent visual plans."""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class RenderLimits:
    profile: str
    max_entities_2d: int
    max_entities_3d: int
    max_stages: int
    max_samples_2d: int
    max_samples_3d: int
    absolute_tolerance: float
    relative_tolerance: float


_PROFILES = {
    "lecture-v1": RenderLimits("lecture-v1", 48, 32, 6, 128 * 128, 64 * 64 * 64, 1e-9, 1e-7),
}


def limits_for(profile: str) -> RenderLimits:
    try:
        return _PROFILES[profile]
    except KeyError:
        raise ValueError(f"unknown render profile: {profile}") from None


def validate_budget(
    profile: str,
    *,
    scene: str,
    entity_count: int,
    stage_count: int,
    sample_count: int,
    bounds: tuple[float, ...],
) -> tuple[str, ...]:
    limits = limits_for(profile)
    errors: list[str] = []
    if scene not in {"2d", "3d"}:
        errors.append(f"scene: expected 2d or 3d, got {scene!r}")
    expected_bounds = 4 if scene == "2d" else 6
    if len(bounds) != expected_bounds:
        errors.append(f"bounds: expected {expected_bounds} values for {scene}")
    if any(not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)) for value in bounds):
        errors.append("bounds: all values must be finite numbers")
    if len(bounds) == expected_bounds:
        for index in range(0, expected_bounds, 2):
            if bounds[index] >= bounds[index + 1]:
                errors.append("bounds: each lower bound must be less than its upper bound")
    for name, value in (("entities", entity_count), ("stages", stage_count), ("samples", sample_count)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            errors.append(f"{name}: count must be a non-negative integer")
    max_entities = limits.max_entities_3d if scene == "3d" else limits.max_entities_2d
    max_samples = limits.max_samples_3d if scene == "3d" else limits.max_samples_2d
    if isinstance(entity_count, int) and not isinstance(entity_count, bool) and entity_count > max_entities:
        errors.append(f"entities: exceeds {scene} budget of {max_entities}")
    if isinstance(stage_count, int) and not isinstance(stage_count, bool) and stage_count > limits.max_stages:
        errors.append(f"stages: exceeds budget of {limits.max_stages}")
    if isinstance(sample_count, int) and not isinstance(sample_count, bool) and sample_count > max_samples:
        errors.append(f"samples: exceeds {scene} budget of {max_samples}")
    return tuple(dict.fromkeys(errors))


__all__ = ["RenderLimits", "limits_for", "validate_budget"]
