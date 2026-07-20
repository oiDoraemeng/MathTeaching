"""几何层与显示层共用的参数。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class HyperboloidParameters:
    """方程 x^2/a^2 + y^2/b^2 - z^2/c^2 = -1 的半轴参数。"""

    a: float = 0.2
    b: float = 0.2
    c: float = 1
    u_max: float = 1.35
    radial_resolution: int = 72
    angular_resolution: int = 96
    