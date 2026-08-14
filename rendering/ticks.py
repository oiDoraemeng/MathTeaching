"""Camera-aware tick spacing and viewport range helpers."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor, isfinite, log10, tan


@dataclass(frozen=True)
class ViewportBounds:
    """Axis-aligned visible bounds used for 2D guides and sampling."""

    x_range: tuple[float, float]
    y_range: tuple[float, float]

    def __post_init__(self) -> None:
        if self.x_range[0] >= self.x_range[1] or self.y_range[0] >= self.y_range[1]:
            raise ValueError("Viewport bounds must be increasing.")

    @property
    def x_span(self) -> float:
        return self.x_range[1] - self.x_range[0]

    @property
    def y_span(self) -> float:
        return self.y_range[1] - self.y_range[0]

    def expanded(self, factor: float = 0.14) -> "ViewportBounds":
        if factor < 0:
            raise ValueError("Viewport expansion must not be negative.")
        return ViewportBounds(
            (self.x_range[0] - self.x_span * factor, self.x_range[1] + self.x_span * factor),
            (self.y_range[0] - self.y_span * factor, self.y_range[1] + self.y_span * factor),
        )

    def contains(self, other: "ViewportBounds") -> bool:
        """Report whether this region fully encloses another visible region."""
        return (
            self.x_range[0] <= other.x_range[0]
            and other.x_range[1] <= self.x_range[1]
            and self.y_range[0] <= other.y_range[0]
            and other.y_range[1] <= self.y_range[1]
        )


def visible_2d_bounds(
    focal_point: tuple[float, float] | tuple[float, float, float],
    parallel_scale: float,
    aspect_ratio: float,
) -> ViewportBounds:
    """Convert a VTK parallel camera state into visible XY bounds."""
    if not isfinite(parallel_scale) or parallel_scale <= 0:
        raise ValueError("Parallel scale must be a finite positive value.")
    if not isfinite(aspect_ratio) or aspect_ratio <= 0:
        raise ValueError("Viewport aspect ratio must be a finite positive value.")
    half_height = parallel_scale / 2.0
    half_width = half_height * aspect_ratio
    return ViewportBounds(
        (float(focal_point[0]) - half_width, float(focal_point[0]) + half_width),
        (float(focal_point[1]) - half_height, float(focal_point[1]) + half_height),
    )


def automatic_tick_spacing(span: float, *, target_intervals: int = 16) -> float:
    """Return the closest 1-2-5 spacing for the supplied visible span."""
    if not isfinite(span) or span <= 0:
        raise ValueError("Tick span must be a finite positive value.")
    if target_intervals < 1:
        raise ValueError("Target interval count must be positive.")
    ideal = span / target_intervals
    exponent = floor(log10(ideal))
    candidates = tuple(
        multiplier * (10.0 ** power)
        for power in (exponent - 1, exponent, exponent + 1)
        for multiplier in (1.0, 2.0, 5.0)
    )
    return min(candidates, key=lambda candidate: abs(log10(candidate / ideal)))


def stable_tick_spacing(
    span: float,
    previous_spacing: float | None,
    *,
    target_intervals: int = 16,
    min_intervals: int = 8,
    max_intervals: int = 24,
) -> float:
    """Keep the previous spacing until tick density leaves the healthy band.

    GeoGebra-style behaviour: a zoom only re-labels the axes when gridlines
    would become too dense or too sparse. While the visible interval count
    stays within ``[min_intervals, max_intervals]`` the previous spacing is
    reused verbatim, so small zooms never rebuild the guides.
    """
    if not isfinite(span) or span <= 0:
        raise ValueError("Tick span must be a finite positive value.")
    if previous_spacing is None or not isfinite(previous_spacing) or previous_spacing <= 0:
        return automatic_tick_spacing(span, target_intervals=target_intervals)
    intervals = span / previous_spacing
    if min_intervals <= intervals <= max_intervals:
        return float(previous_spacing)
    return automatic_tick_spacing(span, target_intervals=target_intervals)


def tick_spacing(
    span: float,
    mode: str = "auto",
    custom_spacing: float = 1.0,
    *,
    target_intervals: int = 16,
    previous_spacing: float | None = None,
) -> float:
    """Resolve a scene's automatic or fixed tick spacing."""
    if mode == "custom":
        if not isfinite(custom_spacing) or custom_spacing <= 0:
            raise ValueError("Custom tick spacing must be a finite positive value.")
        return float(custom_spacing)
    return stable_tick_spacing(
        span, previous_spacing, target_intervals=target_intervals
    )


def tick_values(axis_range: tuple[float, float], spacing: float) -> tuple[float, ...]:
    """Return stable inclusive tick positions without cumulative float drift."""
    if not isfinite(spacing) or spacing <= 0:
        raise ValueError("Tick spacing must be a finite positive value.")
    lower, upper = axis_range
    start = ceil(lower / spacing - 1e-10)
    end = floor(upper / spacing + 1e-10)
    return tuple(index * spacing for index in range(start, end + 1))


def format_tick(value: float, spacing: float) -> str:
    """Format numeric labels without visual floating-point noise."""
    tolerance = max(abs(spacing) * 1e-8, 1e-10)
    if abs(value) <= tolerance:
        return "0"
    absolute = abs(value)
    if absolute >= 1e6 or absolute < 1e-4:
        return f"{value:.3e}".replace("e+0", "e+").replace("e-0", "e-")
    decimals = max(0, min(8, int(ceil(-log10(spacing) + 1e-10))))
    text = f"{value:.{decimals}f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def visible_3d_axis_extent(
    camera_distance: float,
    view_angle_degrees: float,
    aspect_ratio: float,
) -> float:
    """Estimate a symmetric world-space axis extent from a perspective camera."""
    if not isfinite(camera_distance) or camera_distance <= 0:
        raise ValueError("Camera distance must be a finite positive value.")
    if not isfinite(view_angle_degrees) or view_angle_degrees <= 0:
        raise ValueError("Camera view angle must be a finite positive value.")
    if not isfinite(aspect_ratio) or aspect_ratio <= 0:
        raise ValueError("Viewport aspect ratio must be a finite positive value.")
    half_vertical = camera_distance * tan(view_angle_degrees * 3.141592653589793 / 360.0)
    return max(0.5, half_vertical * max(1.0, aspect_ratio))
