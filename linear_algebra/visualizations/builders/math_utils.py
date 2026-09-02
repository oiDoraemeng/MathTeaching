"""Mathematical utility functions for visualization builders."""

from __future__ import annotations

import math
from typing import List


def dot_product(v1: List[float], v2: List[float]) -> float:
    """Calculate dot product of two vectors."""
    return sum(a * b for a, b in zip(v1, v2))


def project_vector(v: List[float], u: List[float]) -> List[float]:
    """Project vector v onto direction u."""
    u_dot_u = dot_product(u, u)
    if u_dot_u == 0:
        return [0.0] * len(v)

    v_dot_u = dot_product(v, u)
    scalar = v_dot_u / u_dot_u
    return [scalar * ui for ui in u]


def angle_between(v1: List[float], v2: List[float]) -> float:
    """Calculate angle between two vectors in radians (0 to π)."""
    dot = dot_product(v1, v2)
    mag1 = math.sqrt(dot_product(v1, v1))
    mag2 = math.sqrt(dot_product(v2, v2))

    if mag1 == 0 or mag2 == 0:
        return 0.0

    cos_angle = dot / (mag1 * mag2)
    cos_angle = max(-1.0, min(1.0, cos_angle))
    return math.acos(cos_angle)


def cross_product(v1: List[float], v2: List[float]) -> List[float]:
    """Calculate 3D cross product of two vectors."""
    if len(v1) != 3 or len(v2) != 3:
        raise ValueError("Cross product requires 3D vectors")

    return [
        v1[1] * v2[2] - v1[2] * v2[1],
        v1[2] * v2[0] - v1[0] * v2[2],
        v1[0] * v2[1] - v1[1] * v2[0],
    ]


__all__ = ["dot_product", "project_vector", "angle_between", "cross_product"]
