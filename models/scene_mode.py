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

    background: str = "auto"
    axis_color_mode: str = "contrast"
    show_grid: bool = True
    show_ticks: bool = True
    tick_spacing_mode: str = "auto"
    tick_spacing: float = 1.0
    show_intersections: bool = False

    def __post_init__(self) -> None:
        if self.background not in {"auto", "light", "dark"}:
            self.background = "auto"
        if self.tick_spacing_mode not in {"auto", "custom"}:
            self.tick_spacing_mode = "auto"
        if not isfinite(self.tick_spacing) or self.tick_spacing <= 0:
            self.tick_spacing = 1.0

    def background_color(self, effective_theme: str = "light") -> str:
        """Return the scene surface color for the selected background mode."""
        if self.background == "dark":
            return "#101317"
        if self.background == "light":
            return "#f7f8fb"
        return self._theme_color(effective_theme, "bg", "scene")

    def contrast_axis_color(self, effective_theme: str = "light") -> str:
        """Return the neutral axis color with sufficient scene contrast."""
        if self.background == "dark":
            return "#f5f7fa"
        if self.background == "light":
            return "#242a32"
        return self._theme_color(effective_theme, "text", "primary")

    @staticmethod
    def _theme_color(effective_theme: str, group: str, name: str) -> str:
        from ui.tokens import load_tokens

        theme = effective_theme if effective_theme in {"light", "dark"} else "light"
        tokens = load_tokens()
        return str(tokens["themes"][theme][group][name])
