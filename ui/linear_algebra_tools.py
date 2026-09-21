"""Pure planning helpers for the linear-algebra toolbar.

The main window owns input state and scene transactions; this module owns the
mathematical interpretation of a selection and the command plans used to draw
it.  Keeping these pieces independent makes it possible to add a new tool or
change its explanation without editing Qt event plumbing.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
import re

from linear_algebra.visualizations.common import matrix_label_text
from models.geometry_2d import Linear2D, Point2D
from rendering.ticks import ViewportBounds
from services.scene_commands import CommandPlan


def vector_components(
    linear: Linear2D,
    points: Mapping[str, Point2D],
) -> tuple[tuple[float, float], tuple[float, float]] | None:
    """Return ``(start, displacement)`` for a stored vector."""
    start = points.get(linear.start_point_id)
    end = points.get(linear.end_point_id)
    if start is None or end is None:
        return None
    return (start.x, start.y), (end.x - start.x, end.y - start.y)


def build_vector_tool_plan(
    tool: str,
    vectors: tuple[Linear2D, Linear2D],
    points: Mapping[str, Point2D],
    bounds: ViewportBounds,
    alias: str,
) -> CommandPlan | None:
    """Build the command plan for a two-vector toolbar tool."""
    first = vector_components(vectors[0], points)
    second = vector_components(vectors[1], points)
    if first is None or second is None:
        return None
    vertex, v1 = first
    _second_vertex, v2 = second
    first_length = math.hypot(*v1)
    second_length = math.hypot(*v2)
    if first_length <= 1e-12 or second_length <= 1e-12:
        return None

    annotation_alias = f"{alias}_label"
    operations: list[dict[str, object]] = []
    if tool == "angle":
        endpoint_1 = [vertex[0] + v1[0], vertex[1] + v1[1]]
        endpoint_2 = [vertex[0] + v2[0], vertex[1] + v2[1]]
        cosine = (v1[0] * v2[0] + v1[1] * v2[1]) / (first_length * second_length)
        angle = math.degrees(math.acos(max(-1.0, min(1.0, cosine))))
        operations.extend(
            [
                {
                    "op": "geometry.angle_arc",
                    "alias": alias,
                    "vertex": list(vertex),
                    "first": endpoint_1,
                    "second": endpoint_2,
                    "radius": max(0.25, min(0.8, min(first_length, second_length) * 0.22)),
                },
                {
                    "op": "annotation.formula",
                    "alias": annotation_alias,
                    "text": f"θ={angle:.1f}°",
                    "position": [
                        vertex[0] + 0.55 * (v1[0] + v2[0]),
                        vertex[1] + 0.55 * (v1[1] + v2[1]),
                    ],
                },
            ]
        )
    elif tool == "projection":
        denominator = v2[0] * v2[0] + v2[1] * v2[1]
        if denominator <= 1e-12:
            return None
        scale = (v1[0] * v2[0] + v1[1] * v2[1]) / denominator
        operations.extend(
            [
                {
                    "op": "geometry.projection",
                    "alias": alias,
                    "vector": list(v1),
                    "direction": list(v2),
                    "origin": list(vertex),
                    "result_alias": f"{alias}_result",
                    "foot_alias": f"{alias}_foot",
                    "residual_alias": f"{alias}_residual",
                },
                {
                    "op": "annotation.formula",
                    "alias": annotation_alias,
                    "text": f"投影系数={scale:.2f}",
                    "position": [vertex[0] + 0.5 * v1[0], vertex[1] + 0.5 * v1[1]],
                },
            ]
        )
    elif tool == "subspace":
        basis = [list(v1), list(v2)]
        if abs(v1[0] * v2[1] - v1[1] * v2[0]) <= 1e-12:
            basis = [list(v1)]
        operations.extend(
            [
                {
                    "op": "geometry.subspace_region",
                    "alias": alias,
                    "basis": basis,
                    "origin": list(vertex),
                    "bounds": [*bounds.x_range, *bounds.y_range],
                    "color": "#4c9f70",
                    "opacity": 0.2,
                },
                {
                    "op": "annotation.formula",
                    "alias": annotation_alias,
                    "text": "span(v₁)" if len(basis) == 1 else "span(v₁,v₂)",
                    "position": [vertex[0], vertex[1]],
                },
            ]
        )
    elif tool == "area":
        determinant = v1[0] * v2[1] - v1[1] * v2[0]
        operations.extend(
            [
                {
                    "op": "geometry.oriented_area",
                    "alias": alias,
                    "vectors": [list(v1), list(v2)],
                    "origin": list(vertex),
                    "color": "#d97845",
                    "opacity": 0.28,
                },
                {
                    "op": "annotation.formula",
                    "alias": annotation_alias,
                    "text": f"det={determinant:.2f}",
                    "position": [
                        vertex[0] + 0.45 * (v1[0] + v2[0]),
                        vertex[1] + 0.45 * (v1[1] + v2[1]),
                    ],
                },
            ]
        )
    else:
        return None
    return CommandPlan(scene="2d", operations=tuple(operations), summary=f"线性代数工具：{tool}")


def parse_matrix(text: str) -> tuple[tuple[float, float], tuple[float, float]] | None:
    """Parse a 2x2 matrix from plain text or MathLive matrix LaTeX."""
    source = str(text).strip()
    if not source:
        return None
    source = source.replace(r"\left", "").replace(r"\right", "")
    source = re.sub(r"\\begin\{[pbBvV]?matrix\}", "", source)
    source = re.sub(r"\\end\{[pbBvV]?matrix\}", "", source)
    source = re.sub(r"\\begin\{array\}\{[^{}]*\}", "", source)
    source = source.replace(r"\end{array}", "")
    source = source.strip("()[] ")
    if r"\\" in source or "&" in source:
        row_sources = re.split(r"\\\\", source)
        rows = [" ".join(cell.strip() for cell in row.split("&")) for row in row_sources]
    else:
        rows = [row.strip() for row in source.split(";") if row.strip()]
    if len(rows) != 2:
        return None
    parsed: list[tuple[float, float]] = []
    try:
        for row in rows:
            values = [_parse_matrix_scalar(value) for value in row.replace(",", " ").split()]
            if len(values) != 2 or not all(math.isfinite(value) for value in values):
                return None
            parsed.append((values[0], values[1]))
    except (ValueError, ZeroDivisionError):
        return None
    return parsed[0], parsed[1]


def _parse_matrix_scalar(source: str) -> float:
    """Parse the numeric LaTeX forms MathLive commonly emits in matrix cells."""
    value = source.strip().replace("−", "-").replace(r"\,", "")
    fraction = re.fullmatch(r"([+-]?)\\(?:d?frac)\{([^{}]+)\}\{([^{}]+)\}", value)
    if fraction is not None:
        sign = -1.0 if fraction.group(1) == "-" else 1.0
        return sign * _parse_matrix_scalar(fraction.group(2)) / _parse_matrix_scalar(
            fraction.group(3)
        )
    return float(value)


def build_polygon_tool_plan(points: Sequence[Point2D], alias: str) -> CommandPlan:
    """Build the polygon drawing and its concise explanatory label."""
    center_x = sum(point.x for point in points) / len(points)
    center_y = sum(point.y for point in points) / len(points)
    return CommandPlan(
        scene="2d",
        operations=(
            {
                "op": "geometry.polygon",
                "alias": alias,
                "vertices": [[point.x, point.y] for point in points],
                "color": "#5b8def",
                "opacity": 0.2,
                "outline": True,
            },
            {
                "op": "annotation.formula",
                "alias": f"{alias}_label",
                "text": f"多边形（{len(points)} 边）",
                "position": [center_x, center_y],
            },
        ),
        summary="线性代数工具：polygon",
    )


def build_transform_tool_plan(
    matrix: tuple[tuple[float, float], tuple[float, float]],
    points: Sequence[tuple[float, float]],
    bounds: ViewportBounds,
    alias: str,
) -> CommandPlan:
    """Build a transformed grid, staged point transform, and matrix label."""
    grid_alias = f"{alias}_grid"
    staged_alias = f"{alias}_staged"
    point_aliases = [f"{staged_alias}_p{index}" for index in range(len(points))]
    annotation_alias = f"{alias}_label"
    return CommandPlan(
        scene="2d",
        operations=(
            {
                "op": "geometry.transformed_grid",
                "alias": grid_alias,
                "matrix": [list(matrix[0]), list(matrix[1])],
                "bounds": [*bounds.x_range, *bounds.y_range],
                "step": 1.0,
            },
            {
                "op": "geometry.staged_transform",
                "alias": staged_alias,
                "matrices": [[list(matrix[0]), list(matrix[1])]],
                "points": [list(point) for point in points],
                "aliases": point_aliases,
            },
            {
                "op": "annotation.formula",
                "alias": annotation_alias,
                "text": matrix_label_text("A", (matrix[0], matrix[1])),
                "position": [bounds.x_range[0] + 0.8, bounds.y_range[1] - 0.8],
            },
        ),
        summary="线性代数工具：transform",
    )


def build_matrix_grid_tool_plan(
    matrix: tuple[tuple[float, float], tuple[float, float]],
    grid_range: float,
    alias: str,
) -> CommandPlan:
    """Build the toolbar matrix preview inside the current coordinate plane.

    The regular 2-D guides remain the source grid.  This operation contributes
    only the matrix image, so the tool never replaces the pane's coordinate
    system or opens another pane.
    """
    extent = max(1.0, min(float(grid_range), 100.0))
    return CommandPlan(
        scene="2d",
        operations=(
            {
                "op": "geometry.transformed_grid",
                "alias": f"{alias}_grid",
                "matrix": [list(matrix[0]), list(matrix[1])],
                "bounds": [-extent, extent, -extent, extent],
                "step": 1.0,
                "show_source_grid": False,
                "show_basis": True,
                "color": "#2f7ebd",
            },
        ),
        summary="线性代数工具：矩阵网格",
    )
