"""A compact catalog of built-in axis-aligned teaching surfaces."""

from __future__ import annotations

from dataclasses import dataclass

from models.surface_layer import SurfaceLayer


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
    BuiltinSurface("ellipsoid", "椭球面", "implicit", "x^2/a^2 + y^2/b^2 + z^2/c^2 = 1", r"\frac{x^{2}}{a^{2}} + \frac{y^{2}}{b^{2}} + \frac{z^{2}}{c^{2}} = 1", {"a": 1.4, "b": 1.0, "c": 0.8}, "#4c9c74"),
    BuiltinSurface("elliptic_cone", "椭圆锥面", "implicit", "x^2/a^2 + y^2/b^2 = z^2/c^2", r"\frac{x^{2}}{a^{2}} + \frac{y^{2}}{b^{2}} = \frac{z^{2}}{c^{2}}", {"a": 1.0, "b": 1.0, "c": 1.0}, "#a16db7"),
    BuiltinSurface("elliptic_cylinder", "椭圆柱面", "implicit", "x^2/a^2 + y^2/b^2 = 1", r"\frac{x^{2}}{a^{2}} + \frac{y^{2}}{b^{2}} = 1", {"a": 1.2, "b": 0.8}, "#d49a3a"),
    BuiltinSurface("hyperbolic_cylinder", "双曲柱面", "implicit", "x^2/a^2 - y^2/b^2 = 1", r"\frac{x^{2}}{a^{2}} - \frac{y^{2}}{b^{2}} = 1", {"a": 1.0, "b": 1.0}, "#7985c5"),
    BuiltinSurface("parabolic_cylinder", "抛物柱面", "explicit", "z = x^2/a", r"z = \frac{x^{2}}{a}", {"a": 1.0}, "#3b9f9f"),
    BuiltinSurface("elliptic_paraboloid", "椭圆抛物面", "explicit", "z = x^2/a^2 + y^2/b^2", r"z = \frac{x^{2}}{a^{2}} + \frac{y^{2}}{b^{2}}", {"a": 1.2, "b": 1.0}, "#c96d87"),
    BuiltinSurface("hyperbolic_paraboloid", "双曲抛物面", "explicit", "z = x^2/a^2 - y^2/b^2", r"z = \frac{x^{2}}{a^{2}} - \frac{y^{2}}{b^{2}}", {"a": 1.2, "b": 1.0}, "#54a67e"),
    BuiltinSurface("one_sheet_hyperboloid", "单叶双曲面", "implicit", "x^2/a^2 + y^2/b^2 - z^2/c^2 = 1", r"\frac{x^{2}}{a^{2}} + \frac{y^{2}}{b^{2}} - \frac{z^{2}}{c^{2}} = 1", {"a": 1.0, "b": 1.0, "c": 1.4}, "#b77355"),
    BuiltinSurface("two_sheet_hyperboloid", "双叶双曲面", "implicit", "x^2/a^2 + y^2/b^2 - z^2/c^2 = -1", r"\frac{x^{2}}{a^{2}} + \frac{y^{2}}{b^{2}} - \frac{z^{2}}{c^{2}} = -1", {"a": 0.8, "b": 0.8, "c": 1.0}, "#5e87b5"),
)
BUILTIN_SURFACE_IDS = frozenset(surface.id for surface in BUILTIN_SURFACES)
DEFAULT_BUILTIN_ID = "two_sheet_hyperboloid"
_SURFACES_BY_ID = {surface.id: surface for surface in BUILTIN_SURFACES}


def create_builtin_layer(surface_id: str) -> SurfaceLayer:
    """Return an independently editable layer initialized from the catalog."""
    try:
        surface = _SURFACES_BY_ID[surface_id]
    except KeyError as error:
        raise KeyError(f"未知的内置曲面: {surface_id}") from error
    return SurfaceLayer(
        name=surface.name,
        kind=surface.kind,
        expression=surface.expression,
        latex=surface.latex,
        parameters=dict(surface.parameters),
        builtin_id=surface.id,
        color=surface.color,
    )
