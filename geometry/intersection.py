"""Numerical pairwise intersection curves for sampled surface meshes."""

from __future__ import annotations

import pyvista as pv


def intersect_surface_meshes(first: pv.PolyData, second: pv.PolyData) -> pv.PolyData:
    """Return the polyline geometry shared by two triangular surface meshes."""
    if first.n_cells == 0 or second.n_cells == 0:
        return pv.PolyData()
    intersection, _first_split, _second_split = first.triangulate().intersection(
        second.triangulate(),
        split_first=False,
        split_second=False,
    )
    return intersection.clean()
