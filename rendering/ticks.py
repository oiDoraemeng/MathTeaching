"""感知相机状态的刻度间距和视口范围辅助函数。"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor, isfinite, log10, tan


@dataclass(frozen=True)
class ViewportBounds:
    """供二维辅助线与采样使用的轴对齐可见范围。"""

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
        """判断当前范围是否完整包含另一可见范围。"""
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
    """将 VTK 平行相机状态换算为可见的 XY 范围。"""
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
    """按给定可见跨度返回最接近的 1-2-5 刻度间距。"""
    if not isfinite(span) or span <= 0:
        raise ValueError("Tick span must be a finite positive value.")
    if target_intervals < 1:
        raise ValueError("Target interval count must be positive.")
    ideal = span / target_intervals
    exponent = floor(log10(ideal))
    # 同时比较相邻数量级，避免理想值处于数量级边界时跳过更合适的候选间距。
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
    min_intervals: int = 4,
    max_intervals: int = 8,
) -> float:
    """在刻度密度离开合理区间前保持上一刻度间距。

    采用类似 GeoGebra 的滞后策略：只有网格将变得过密或过疏时才重标坐标轴。
    可见区间数仍位于 ``[min_intervals, max_intervals]`` 时复用旧间距，避免
    轻微缩放导致辅助线反复重建。
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
    target_intervals: int = 6,
    previous_spacing: float | None = None,
) -> float:
    """解析场景应使用的自动或固定刻度间距。"""
    if mode == "custom":
        if not isfinite(custom_spacing) or custom_spacing <= 0:
            raise ValueError("Custom tick spacing must be a finite positive value.")
        return float(custom_spacing)
    return stable_tick_spacing(
        span, previous_spacing, target_intervals=target_intervals
    )


def tick_values(axis_range: tuple[float, float], spacing: float) -> tuple[float, ...]:
    """返回包含边界且不会累积浮点误差的稳定刻度位置。"""
    if not isfinite(spacing) or spacing <= 0:
        raise ValueError("Tick spacing must be a finite positive value.")
    lower, upper = axis_range
    # 给边界留出极小容差，避免 0.3 / 0.1 等浮点表示误差漏掉端点刻度。
    start = ceil(lower / spacing - 1e-10)
    end = floor(upper / spacing + 1e-10)
    return tuple(index * spacing for index in range(start, end + 1))


def format_tick(value: float, spacing: float) -> str:
    """格式化数值标签，避免显示浮点误差噪声。"""
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
    """根据透视相机估算对称的世界坐标轴范围。"""
    if not isfinite(camera_distance) or camera_distance <= 0:
        raise ValueError("Camera distance must be a finite positive value.")
    if not isfinite(view_angle_degrees) or view_angle_degrees <= 0:
        raise ValueError("Camera view angle must be a finite positive value.")
    if not isfinite(aspect_ratio) or aspect_ratio <= 0:
        raise ValueError("Viewport aspect ratio must be a finite positive value.")
    half_vertical = camera_distance * tan(view_angle_degrees * 3.141592653589793 / 360.0)
    return max(0.5, half_vertical * max(1.0, aspect_ratio))
