"""独立渲染二维曲线图层所使用的数据模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass(frozen=True)
class Plot2DDomain:
    """二维笛卡尔工作区的采样范围。"""

    x_range: tuple[float, float] = (-10.0, 10.0)
    y_range: tuple[float, float] = (-10.0, 10.0)
    curve_resolution: int = 900
    implicit_resolution: int = 280

    def __post_init__(self) -> None:
        for axis_range in (self.x_range, self.y_range):
            if len(axis_range) != 2 or axis_range[0] >= axis_range[1]:
                raise ValueError("Each 2D plot range must have an increasing lower and upper bound.")
        if self.curve_resolution < 16 or self.implicit_resolution < 16:
            raise ValueError("2D sampling resolutions must be at least 16.")

    def scaled(self, factor: float) -> "Plot2DDomain":
        if factor <= 0:
            raise ValueError("Domain scale must be positive.")

        def scale_axis(axis_range: tuple[float, float]) -> tuple[float, float]:
            # 始终以原范围中心缩放，避免调节单个图层范围时整体坐标系发生平移。
            center = (axis_range[0] + axis_range[1]) / 2
            half_width = (axis_range[1] - axis_range[0]) * factor / 2
            return center - half_width, center + half_width

        return Plot2DDomain(
            x_range=scale_axis(self.x_range),
            y_range=scale_axis(self.y_range),
            curve_resolution=self.curve_resolution,
            implicit_resolution=self.implicit_resolution,
        )


@dataclass
class CurveLayer:
    """一个可编辑二维曲线及其独立显示状态。"""

    name: str
    kind: str
    expression: str
    parameters: dict[str, float] = field(default_factory=dict)
    latex: str | None = None
    builtin_id: str | None = None
    visible: bool = True
    color: str = "#2777b6"
    line_width: float = 2.4
    range_scale: float = 1.0
    id: str = field(default_factory=lambda: uuid4().hex)
    agent_alias: str | None = None

    def __post_init__(self) -> None:
        self.line_width = max(1.0, min(8.0, float(self.line_width)))
        self.range_scale = max(1.0, min(5.0, float(self.range_scale)))
