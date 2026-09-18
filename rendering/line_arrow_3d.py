"""Reusable 3-D arrows with a screen-width shaft and a conventional head."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pyvista as pv


def line_arrow_mesh(
    start: Iterable[float],
    end: Iterable[float],
    *,
    tip_length_ratio: float | None = None,
    tip_radius_ratio: float | None = None,
    tip_length: float | None = None,
    tip_radius: float | None = None,
    tip_resolution: int = 20,
) -> pv.PolyData:
    """Build an arrow whose shaft is a line cell and head is a solid cone.

    Keeping the shaft as a line cell means the actor's ``line_width`` is a
    screen-space VTK property.  The cone head remains a normal filled arrowhead
    so the result retains the expected 3-D coordinate-axis appearance.
    """
    origin = np.asarray(tuple(start), dtype=float)
    tip = np.asarray(tuple(end), dtype=float)
    direction = tip - origin
    length = float(np.linalg.norm(direction))
    if length <= 1e-9:
        return pv.PolyData()

    unit = direction / length
    if tip_length is None:
        if tip_length_ratio is None:
            raise ValueError("tip_length or tip_length_ratio is required")
        tip_length = length * max(0.0, min(float(tip_length_ratio), 0.4))
    else:
        tip_length = max(0.0, float(tip_length))
    if tip_radius is None:
        if tip_radius_ratio is None:
            raise ValueError("tip_radius or tip_radius_ratio is required")
        tip_radius = length * max(0.0, float(tip_radius_ratio))
    else:
        tip_radius = max(0.0, float(tip_radius))
    shaft = pv.Line(tuple(origin), tuple(tip))
    head = pv.Cone(
        center=tuple(tip - 0.5 * tip_length * unit),
        direction=tuple(unit),
        height=tip_length,
        radius=tip_radius,
        resolution=max(3, int(tip_resolution)),
        capping=True,
    )
    return shaft.merge(head, merge_points=False)
