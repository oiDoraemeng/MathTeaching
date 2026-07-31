"""Data models for independently rendered algebraic surface layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass(frozen=True)
class PlotDomain:
    """Shared sampling bounds used for all surface and intersection meshes."""

    x_range: tuple[float, float] = (-3.0, 3.0)
    y_range: tuple[float, float] = (-3.0, 3.0)
    z_range: tuple[float, float] = (-3.0, 3.0)
    explicit_resolution: int = 72
    implicit_resolution: int = 56

    def __post_init__(self) -> None:
        for axis_range in (self.x_range, self.y_range, self.z_range):
            if len(axis_range) != 2 or axis_range[0] >= axis_range[1]:
                raise ValueError("Each plot range must have an increasing lower and upper bound.")
        if self.explicit_resolution < 4 or self.implicit_resolution < 4:
            raise ValueError("Surface sampling resolutions must be at least 4.")

    def scaled(self, factor: float) -> "PlotDomain":
        if factor <= 0:
            raise ValueError("Domain scale must be positive.")

        def scale_axis(axis_range: tuple[float, float]) -> tuple[float, float]:
            center = (axis_range[0] + axis_range[1]) / 2
            half_width = (axis_range[1] - axis_range[0]) * factor / 2
            return (center - half_width, center + half_width)

        return PlotDomain(
            x_range=scale_axis(self.x_range),
            y_range=scale_axis(self.y_range),
            z_range=scale_axis(self.z_range),
            explicit_resolution=self.explicit_resolution,
            implicit_resolution=self.implicit_resolution,
        )


@dataclass
class SurfaceLayer:
    """One user-editable surface and its independent display controls."""

    name: str
    kind: str
    expression: str
    parameters: dict[str, float] = field(default_factory=dict)
    builtin_id: str | None = None
    visible: bool = True
    intersections_visible: bool = True
    color: str = "#4f7cac"
    opacity: float = 0.62
    range_scale: float = 1.0
    id: str = field(default_factory=lambda: uuid4().hex)

    def __post_init__(self) -> None:
        self.opacity = max(0.05, min(1.0, float(self.opacity)))
        self.range_scale = max(1.0, min(5.0, float(self.range_scale)))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "expression": self.expression,
            "parameters": self.parameters,
            "builtin_id": self.builtin_id,
            "visible": self.visible,
            "intersections_visible": self.intersections_visible,
            "color": self.color,
            "opacity": self.opacity,
            "range_scale": self.range_scale,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SurfaceLayer":
        return cls(
            id=str(data.get("id") or uuid4().hex),
            name=str(data["name"]),
            kind=str(data["kind"]),
            expression=str(data["expression"]),
            parameters={name: float(value) for name, value in dict(data.get("parameters", {})).items()},
            builtin_id=str(data["builtin_id"]) if data.get("builtin_id") is not None else None,
            visible=bool(data.get("visible", True)),
            intersections_visible=bool(data.get("intersections_visible", True)),
            color=str(data.get("color", "#4f7cac")),
            opacity=float(data.get("opacity", 0.62)),
            range_scale=float(data.get("range_scale", 1.0)),
        )
