"""内置教学曲面的紧凑目录。"""

from __future__ import annotations

from dataclasses import dataclass

from models.surface_layer import SurfaceLayer
from geometry.cas_surface import parse_surface_expression
from geometry.parameter_display import format_parameterized_latex


@dataclass(frozen=True)
class BuiltinSurface:
    id: str
    name: str
    kind: str
    expression: str
    latex: str
    parameters: dict[str, float]
    color: str


BUILTIN_SURFACES = (
    BuiltinSurface("plane", "平面", "explicit", "z = a*x + b*y + c", r"z = ax + by + c", {"a": 0.0, "b": 0.0, "c": 0.0}, "#d1664a"),
    BuiltinSurface("sphere", "球面", "implicit", "x^2 + y^2 + z^2 = r^2", r"x^{2} + y^{2} + z^{2} = r^{2}", {"r": 1.0}, "#3f7fbf"),
    BuiltinSurface("ellipsoid", "椭球面", "implicit", "x^2/a^2 + y^2/b^2 + z^2/c^2 = 1", r"\frac{x^{2}}{a^{2}} + \frac{y^{2}}{b^{2}} + \frac{z^{2}}{c^{2}} = 1", {"a": 2.0, "b": 1.0, "c": 1.0}, "#4c9c74"),
    BuiltinSurface("elliptic_cone", "椭圆锥面", "implicit", "x^2/a^2 + y^2/b^2 = z^2/c^2", r"\frac{x^{2}}{a^{2}} + \frac{y^{2}}{b^{2}} = \frac{z^{2}}{c^{2}}", {"a": 1.0, "b": 1.0, "c": 1.0}, "#a16db7"),
    BuiltinSurface("elliptic_cylinder", "椭圆柱面", "implicit", "x^2/a^2 + y^2/b^2 = 1", r"\frac{x^{2}}{a^{2}} + \frac{y^{2}}{b^{2}} = 1", {"a": 2.0, "b": 1.0}, "#d49a3a"),
    BuiltinSurface("hyperbolic_cylinder", "双曲柱面", "implicit", "x^2/a^2 - y^2/b^2 = 1", r"\frac{x^{2}}{a^{2}} - \frac{y^{2}}{b^{2}} = 1", {"a": 1.0, "b": 1.0}, "#7985c5"),
    BuiltinSurface("parabolic_cylinder", "抛物柱面", "explicit", "z = x^2/a", r"z = \frac{x^{2}}{a}", {"a": 1.0}, "#3b9f9f"),
    BuiltinSurface("elliptic_paraboloid", "椭圆抛物面", "explicit", "z = x^2/a^2 + y^2/b^2", r"z = \frac{x^{2}}{a^{2}} + \frac{y^{2}}{b^{2}}", {"a": 2.0, "b": 1.0}, "#c96d87"),
    BuiltinSurface("hyperbolic_paraboloid", "双曲抛物面", "explicit", "z = x^2/a^2 - y^2/b^2", r"z = \frac{x^{2}}{a^{2}} - \frac{y^{2}}{b^{2}}", {"a": 2.0, "b": 1.0}, "#54a67e"),
    BuiltinSurface("one_sheet_hyperboloid", "单叶双曲面", "implicit", "x^2/a^2 + y^2/b^2 - z^2/c^2 = 1", r"\frac{x^{2}}{a^{2}} + \frac{y^{2}}{b^{2}} - \frac{z^{2}}{c^{2}} = 1", {"a": 1.0, "b": 1.0, "c": 2.0}, "#b77355"),
    BuiltinSurface("two_sheet_hyperboloid", "双叶双曲面", "implicit", "x^2/a^2 + y^2/b^2 - z^2/c^2 = -1", r"\frac{x^{2}}{a^{2}} + \frac{y^{2}}{b^{2}} - \frac{z^{2}}{c^{2}} = -1", {"a": 1.0, "b": 1.0, "c": 1.0}, "#5e87b5"),
)
BUILTIN_SURFACE_IDS = frozenset(surface.id for surface in BUILTIN_SURFACES)
DEFAULT_BUILTIN_ID = "two_sheet_hyperboloid"
_SURFACES_BY_ID = {surface.id: surface for surface in BUILTIN_SURFACES}


def create_builtin_layer(surface_id: str) -> SurfaceLayer:
    """从目录创建一个可独立编辑的曲面图层。"""
    try:
        surface = _SURFACES_BY_ID[surface_id]
    except KeyError as error:
        raise KeyError(f"未知的内置曲面: {surface_id}") from error
    parameters = dict(surface.parameters)
    parsed = parse_surface_expression(surface.expression, surface.kind)
    display_latex = format_parameterized_latex(
        kind=parsed.kind,
        simplified=parsed.simplified,
        parameters=parameters,
        source=parsed.source,
        dependent_axis=parsed.dependent_axis,
        parameter_ranges=parsed.parameter_ranges,
        fallback=surface.latex,
    )
    return SurfaceLayer(
        name=surface.name,
        kind=surface.kind,
        expression=surface.expression,
        latex=display_latex,
        parameters=parameters,
        builtin_id=surface.id,
        color=surface.color,
    )
