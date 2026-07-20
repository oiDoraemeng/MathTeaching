"""双曲面材质的可编辑显示状态。"""

from dataclasses import dataclass


@dataclass
class SurfaceSettings:
    """凸面和凹面的独立颜色，以及材质预设颜色的使用状态。"""

    outer_color: str = "#8d70d6"
    inner_color: str = "#d0c3f0"
    use_preset_colors: bool = True
