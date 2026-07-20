"""基于 vtkLight（经由 pyvista.Light）的三点光源系统。

三盏灯均为相机光源：位置使用相机坐标系定义（相机位于原点并朝向 -z，
+x 向右、+y 向上），因此旋转模型时主光、补光和轮廓光的关系保持稳定。
"""

from dataclasses import dataclass, field

import pyvista as pv

# 在相机坐标系中的方向与强度，按参考图的半透明光泽效果调校。
# 位置是从焦点（原点）指向各光源的大致单位方向向量。
_KEY = dict(position=(0.6, 0.55, 1.0), intensity=1.05, color=(1.00, 0.97, 0.92))  # 主光
_FILL = dict(position=(-0.7, -0.15, 0.8), intensity=0.45, color=(0.90, 0.94, 1.00)) # 补光
_RIM = dict(position=(-0.2, 0.6, -1.0), intensity=0.70, color=(0.95, 0.95, 1.00)) # 轮廓光


@dataclass
class LightSettings:
    """视图中可编辑的光照状态。"""

    ambient: float = 0.20
    outer_color: str = "#8d70d6"
    inner_color: str = "#d0c3f0"
    key: dict = field(default_factory=lambda: _KEY.copy())
    fill: dict = field(default_factory=lambda: _FILL.copy())
    rim: dict = field(default_factory=lambda: _RIM.copy())


def _camera_light(position, intensity, color) -> pv.Light:
    light = pv.Light(light_type="camera light")
    light.position = position
    light.focal_point = (0.0, 0.0, 0.0)
    light.intensity = intensity
    light.color = color
    return light


def setup_three_point_lighting(plotter: pv.Plotter, settings: LightSettings | None = None) -> None:
    """Clear existing lights and install a key/fill/rim camera-light rig.

    Idempotent: safe to call on every scene rebuild — always leaves exactly
    three lights on the renderer.
    """
    settings = settings or LightSettings()
    plotter.remove_all_lights()
    plotter.add_light(_camera_light(**settings.key))
    plotter.add_light(_camera_light(**settings.fill))
    plotter.add_light(_camera_light(**settings.rim))
