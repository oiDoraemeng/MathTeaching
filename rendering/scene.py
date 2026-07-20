"""场景组装：几何、三点光照与材质。

build_scene() 是界面修改参数和导出截图时调用的统一入口。
"""

import numpy as np
import pyvista as pv
from dataclasses import replace

from geometry.hyperboloid import two_sheet_hyperboloid
from models.parameters import HyperboloidParameters
from rendering.axis import add_cartesian_axes
from rendering.helper import add_teaching_helpers
from rendering.lighting import LightSettings, setup_three_point_lighting
from rendering.materials import SURFACE_MATERIAL, material_preset

_CAMERA_POSITION = [(6.4, -7.2, 5.7), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0)]


def build_scene(
    plotter: pv.Plotter,
    parameters: HyperboloidParameters,
    show_axes: bool,
    show_helpers: bool,
    *,
    high_quality: bool = False,
    lighting: LightSettings | None = None,
    material_name: str = "光泽塑料",
    camera_position: list | tuple | None = None,
    interactive: bool = False,
) -> None:
    """清空并重建完整场景。

    high_quality=True 时使用 SSAA 抗锯齿导出清晰截图；交互过程使用
    MSAA 以保证响应速度。
    """
    plotter.clear()
    plotter.set_background("#f7f8fb")

    if interactive:
        # 拖动参数时使用较低网格密度，松开后由完整渲染恢复细节。
        parameters = replace(parameters, radial_resolution=32, angular_resolution=48)
    surface = two_sheet_hyperboloid(parameters)
    lighting = lighting or LightSettings()
    preset = material_preset(material_name)
    # 优先使用预设里的 outer_color/inner_color；回退到 lighting 的颜色设置
    outer = preset.get("outer_color", lighting.outer_color)
    inner = preset.get("inner_color", lighting.inner_color)
    material = {
        **preset,
        "color": outer,
        "ambient": lighting.ambient if material_name == "光泽塑料" else preset.get("ambient", lighting.ambient),
        "backface_params": {
            # 使用预设的 inner_color，使修改直接生效
            "color": inner,
            "opacity": preset.get("opacity", 1.0),
            "ambient": preset.get("ambient", lighting.ambient),
            "diffuse": preset.get("diffuse", 0.6),
            "specular": preset.get("specular", 0.2),
            "specular_power": preset.get("specular_power", 20),
        },
    }
    material.pop("outer_color", None)
    material.pop("inner_color", None)
    plotter.add_mesh(surface, name="hyperboloid", **material)

    extent = max(parameters.a, parameters.b, parameters.c * np.cosh(parameters.u_max)) * 1.45
    if show_axes:
        add_cartesian_axes(plotter, extent)
    if show_helpers:
        add_teaching_helpers(plotter, parameters)

    # 为半透明曲面启用正确的前后深度排序。
    if interactive:
        plotter.disable_depth_peeling()
    else:
        plotter.enable_depth_peeling(number_of_peels=8, occlusion_ratio=0.0)

    setup_three_point_lighting(plotter, lighting)
    plotter.enable_anti_aliasing("ssaa" if high_quality else "msaa")

    # 设置观察方向，再由自动相机适配场景边界。
    # direction but reframes the distance to fit the bounds — robust to any u_max.
    if camera_position is None:
        plotter.camera_position = _CAMERA_POSITION
        plotter.reset_camera()
    else:
        plotter.camera_position = camera_position
        plotter.reset_camera_clipping_range()


def update_lighting(plotter: pv.Plotter, settings: LightSettings) -> None:
    """不重建几何体，仅更新光照和双面材质。"""
    actor = plotter.renderer.actors.get("hyperboloid")
    if actor is None:
        return
    actor.prop.color = settings.outer_color
    actor.prop.ambient = settings.ambient
    actor.backface_prop.color = settings.inner_color
    actor.backface_prop.ambient = settings.ambient
    setup_three_point_lighting(plotter, settings)
    plotter.render()


def update_surface_geometry(plotter: pv.Plotter, parameters: HyperboloidParameters) -> None:
    """仅更新曲面顶点，保留坐标轴、辅助线、光源和当前相机。"""
    actor = plotter.renderer.actors.get("hyperboloid")
    if actor is None:
        return
    updated_surface = two_sheet_hyperboloid(parameters)
    current_surface = actor.mapper.dataset
    if current_surface.n_points == updated_surface.n_points and current_surface.n_cells == updated_surface.n_cells:
        current_surface.points = updated_surface.points
        current_surface.Modified()
    else:
        actor.mapper.dataset = updated_surface
    plotter.reset_camera_clipping_range()
    plotter.render()
