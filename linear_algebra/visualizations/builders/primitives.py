"""Primitive geometry builders for reusable visualization components."""

from __future__ import annotations

from typing import List


def make_vector_2d(
    start: List[float],
    end: List[float],
    alias: str,
    role: str = "primary",
    style: str = "solid",
) -> List[dict]:
    """Create 2D vector with points and line segment."""
    return [
        {
            "op": "point.upsert",
            "alias": f"{alias}_start",
            "coordinates": start,
            "name": "",
        },
        {
            "op": "point.upsert",
            "alias": f"{alias}_end",
            "coordinates": end,
            "name": "",
        },
        {
            "op": "linear.upsert",
            "alias": alias,
            "start": f"{alias}_start",
            "end": f"{alias}_end",
            "kind": "vector",
            "role": role,
            "style": style,
        },
    ]


def make_label(text: str, position: List[float], offset: List[float] = None) -> dict:
    """Create text label annotation."""
    if offset is None:
        offset = [0.0, 0.0]

    return {
        "op": "annotation.label",
        "alias": f"label_{text.replace(' ', '_').replace('+', 'plus').replace('-', 'minus')}",
        "text": text,
        "position": position,
        "offset": offset,
    }


def make_polygon(
    vertices: List[List[float]],
    color: str = "#5b8def",
    opacity: float = 0.15,
    outline: bool = True,
) -> dict:
    """Create polygon shape."""
    return {
        "op": "geometry.polygon",
        "alias": "polygon",
        "vertices": vertices,
        "color": color,
        "opacity": opacity,
        "outline": outline,
    }


def make_angle_arc(
    vertex: List[float],
    first: List[float],
    second: List[float],
    radius: float = 0.5,
) -> dict:
    """Create angle arc between two vectors."""
    return {
        "op": "geometry.angle_arc",
        "alias": "angle",
        "vertex": vertex,
        "first": first,
        "second": second,
        "radius": radius,
    }


def make_projection(vector: List[float], direction: List[float]) -> dict:
    """Create projection visualization."""
    return {
        "op": "geometry.projection",
        "alias": "projection",
        "vector": vector,
        "direction": direction,
        "result_alias": "proj_result",
        "foot_alias": "proj_foot",
        "residual_alias": "proj_residual",
    }


def make_right_angle_marker(
    vertex: List[float],
    first: List[float],
    second: List[float],
    size: float = 0.3,
) -> dict:
    """Create right angle marker."""
    return {
        "op": "geometry.right_angle_marker",
        "alias": "right_angle",
        "vertex": vertex,
        "first": first,
        "second": second,
        "size": size,
    }


def make_view_fit(padding: float = 1.15) -> dict:
    """Create view fit operation."""
    return {"op": "view.fit", "padding": padding}


def make_vector_3d(
    start: List[float],
    end: List[float],
    alias: str,
    role: str = "primary",
) -> dict:
    """Create 3D vector."""
    return {
        "op": "linear3d.upsert",
        "alias": alias,
        "start": start,
        "end": end,
        "kind": "vector",
        "role": role,
    }


def make_plane_3d(
    origin: List[float],
    normal: List[float],
    size: float = 4.0,
    color: str = "#5b8def",
    opacity: float = 0.18,
) -> dict:
    """Create 3D plane."""
    return {
        "op": "plane3d.upsert",
        "alias": "plane",
        "origin": origin,
        "normal": normal,
        "size": size,
        "color": color,
        "opacity": opacity,
    }


def make_parallelepiped(
    origin: List[float],
    vectors: List[List[float]],
    color: str = "#4c9f70",
    opacity: float = 0.2,
) -> dict:
    """Create parallelepiped (3D parallelogram)."""
    return {
        "op": "geometry.parallelepiped",
        "alias": "parallelepiped",
        "origin": origin,
        "vectors": vectors,
        "color": color,
        "opacity": opacity,
    }


__all__ = [
    "make_vector_2d",
    "make_vector_3d",
    "make_label",
    "make_polygon",
    "make_angle_arc",
    "make_projection",
    "make_right_angle_marker",
    "make_plane_3d",
    "make_parallelepiped",
    "make_view_fit",
]
