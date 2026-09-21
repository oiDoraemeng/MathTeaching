"""Primitive geometry builders for reusable visualization components."""

from __future__ import annotations

from typing import List

from ..palette import role_color


_ROLE_ALIASES = {
    "primary": "primary",
    "construction": "construction",
    "result": "result",
    # 将设计稿中的展示名称收敛到场景协议的三种语义角色。
    "secondary": "construction",
    "auxiliary": "construction",
}


def _normalize_role(role: str) -> str:
    """Map plan-facing role aliases to the scene command vocabulary."""
    try:
        return _ROLE_ALIASES[str(role)]
    except KeyError as error:
        raise ValueError(
            f"Unknown visualization role {role!r}; use primary, construction, or result."
        ) from error


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
            "role": _normalize_role(role),
            "color": role_color(role),
            "style": style,
        },
    ]


def make_label(
    text: str,
    position: List[float],
    offset: List[float] = None,
    alias: str | None = None,
) -> dict:
    """Create text label annotation."""
    if offset is None:
        offset = [0.0, 0.0]

    safe_alias = alias or f"label_{text.replace(' ', '_').replace('+', 'plus').replace('-', 'minus')}"
    return {
        # 标签复用公式标注命令及其校验、渲染路径。
        "op": "annotation.formula",
        "alias": safe_alias,
        "text": text,
        "position": position,
    }


def make_polygon(
    vertices: List[List[float]],
    color: str | None = None,
    opacity: float = 0.15,
    outline: bool = True,
    alias: str = "polygon",
) -> dict:
    """Create polygon shape."""
    return {
        "op": "geometry.polygon",
        "alias": alias,
        "vertices": vertices,
        "color": color or role_color("neutral"),
        "opacity": opacity,
        "outline": outline,
    }


def make_angle_arc(
    vertex: List[float],
    first: List[float],
    second: List[float],
    radius: float = 0.5,
    alias: str = "angle",
) -> dict:
    """Create angle arc between two vectors."""
    return {
        "op": "geometry.angle_arc",
        "alias": alias,
        "vertex": vertex,
        "first": first,
        "second": second,
        "radius": radius,
        "color": role_color("projection"),
    }


def make_projection(
    vector: List[float],
    direction: List[float],
    alias: str = "projection",
) -> dict:
    """Create projection visualization."""
    return {
        "op": "geometry.projection",
        "alias": alias,
        "vector": vector,
        "direction": direction,
        "result_alias": f"{alias}_result",
        "foot_alias": f"{alias}_foot",
        "residual_alias": f"{alias}_residual",
        "color": role_color("projection"),
    }


def make_right_angle_marker(
    vertex: List[float],
    first: List[float],
    second: List[float],
    size: float = 0.3,
    alias: str = "right_angle",
) -> dict:
    """Create right angle marker."""
    return {
        "op": "geometry.right_angle_marker",
        "alias": alias,
        "vertex": vertex,
        "first": first,
        "second": second,
        "size": size,
        "color": role_color("neutral"),
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
        "role": _normalize_role(role),
        "color": role_color(role),
    }


def make_plane_3d(
    origin: List[float],
    normal: List[float],
    size: float = 4.0,
    color: str | None = None,
    opacity: float = 0.18,
) -> dict:
    """Create 3D plane."""
    return {
        "op": "plane3d.upsert",
        "alias": "plane",
        "origin": origin,
        "normal": normal,
        "size": size,
        "color": color or role_color("neutral"),
        "opacity": opacity,
    }


def make_parallelepiped(
    origin: List[float],
    vectors: List[List[float]],
    color: str | None = None,
    opacity: float = 0.2,
) -> dict:
    """Create parallelepiped (3D parallelogram)."""
    return {
        "op": "geometry.parallelepiped",
        "alias": "parallelepiped",
        "origin": origin,
        "vectors": vectors,
        "color": color or role_color("volume"),
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
