"""界面与渲染器共用的场景模式和视口外观状态。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite


class SceneMode(StrEnum):
    """两个相互独立的教学工作区。"""

    THREE_D = "3d"
    TWO_D = "2d"


@dataclass
class SceneAppearance:
    """单个工作区的运行时外观偏好。"""

    background: str = "light"
    axis_color_mode: str = "contrast"
    show_grid: bool = True
    show_ticks: bool = True
    tick_spacing_mode: str = "auto"
    tick_spacing: float = 1.0
    show_intersections: bool = False

    def __post_init__(self) -> None:
        if self.tick_spacing_mode not in {"auto", "custom"}:
            self.tick_spacing_mode = "auto"
        if not isfinite(self.tick_spacing) or self.tick_spacing <= 0:
            self.tick_spacing = 1.0

    @property
    def background_color(self) -> str:
        return "#101317" if self.background == "dark" else "#f7f8fb"

    @property
    def contrast_axis_color(self) -> str:
        return "#f5f7fa" if self.background == "dark" else "#242a32"
