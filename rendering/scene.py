"""场景组装：几何、三点光照与材质。

build_scene() 是界面修改参数和导出截图时调用的统一入口。
"""

import pyvista as pv
from dataclasses import replace

from geometry.hyperboloid import two_sheet_hyperboloid
from models.parameters import HyperboloidParameters
from models.scene_mode import SceneAppearance
from models.surface_settings import SurfaceSettings
from rendering.axis import add_cartesian_axes
from rendering.helper import add_teaching_helpers
from rendering.lighting import LightSettings, setup_three_point_lighting
from rendering.materials import material_preset

# Keep the initial view far enough away to leave comfortable room around the
# origin.  The blank 3-D workspace has no geometry for ``reset_camera()`` to
# fit, so its camera must be positioned explicitly.
_CAMERA_POSITION = [(9.6, -10.8, 8.55), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0)]

# 每根轴从 -4.5 到 +4.5
DEFAULT_3D_AXIS_EXTENT = 4.5 # 


def configure_3d_camera_interaction(plotter: pv.Plotter) -> None:
    """配置三维原点旋转与中键平移交互。"""
    iren = getattr(plotter, "iren", None)
    if iren is None:
        return
    plotter.enable_custom_trackball_style(
        left="rotate",
        shift_left="pan",
        control_left="spin",
        middle="pan",
        shift_middle="pan",
        control_middle="pan",
        right="dolly",
        shift_right="environment_rotate",
        control_right="dolly",
    )
    style = getattr(iren, "style", None)
    if style is None:
        return

    def focus_origin_before_rotation(_caller: object, _event: object) -> None:
        interactor = getattr(iren, "interactor", None)
        if interactor is not None and (
            interactor.GetShiftKey() or interactor.GetControlKey()
        ):
            return
        plotter.camera.focal_point = (0.0, 0.0, 0.0)

    # 先于 PyVista 左键处理器执行，确保轨迹球开始旋转时焦点就是坐标原点。
    style.AddObserver("LeftButtonPressEvent", focus_origin_before_rotation, 1.0)


def build_scene(
    plotter: pv.Plotter,
    parameters: HyperboloidParameters | None = None,
    show_axes: bool = True,
    show_helpers: bool = True,
    *,
    high_quality: bool = False,
    lighting: LightSettings | None = None,
    surface_settings: SurfaceSettings | None = None,
    material_name: str = "光泽塑料",
    camera_position: list | tuple | None = None,
    background_color: str | None = None,
    appearance: SceneAppearance | None = None,
    effective_theme: str = "light",
    axis_color_mode: str = "contrast",
    contrast_axis_color: str | None = None,
    show_ticks: bool = True,
    tick_spacing_mode: str = "auto",
    custom_tick_spacing: float = 1.0,
    interactive: bool = False,
    base_surface: bool = True,
) -> None:
    """清空并重建完整场景。

    high_quality=True 时使用 SSAA 抗锯齿导出清晰截图；交互过程使用
    MSAA 以保证响应速度。
    """
    plotter.clear()
    resolved_background = (
        appearance.background_color(effective_theme)
        if appearance is not None
        else background_color or "#f7f8fb"
    )
    resolved_contrast_color = (
        appearance.contrast_axis_color(effective_theme)
        if appearance is not None and contrast_axis_color is None
        else contrast_axis_color
    )
    plotter.set_background(resolved_background)
    # 二维场景会在共享绘图器上开启平行投影，重建三维场景前必须恢复透视投影。
    plotter.disable_parallel_projection()
    lighting = lighting or LightSettings()

    if not base_surface:
        if show_axes:
            add_cartesian_axes(
                plotter,
                DEFAULT_3D_AXIS_EXTENT,
                axis_color_mode=axis_color_mode,
                contrast_color=resolved_contrast_color,
                show_ticks=show_ticks,
                tick_spacing_mode=tick_spacing_mode,
                custom_tick_spacing=custom_tick_spacing,
            )
        if interactive:
            plotter.disable_depth_peeling()
        else:
            plotter.enable_depth_peeling(number_of_peels=8, occlusion_ratio=0.0)
        setup_three_point_lighting(plotter, lighting)
        plotter.enable_anti_aliasing("ssaa" if high_quality else "msaa")
        if camera_position is None:
            plotter.camera_position = _CAMERA_POSITION
            # ``show_axes=False`` is used by the pane renderer, which adds its
            # persistent axes immediately afterwards.  Resetting an empty
            # plotter here collapses the camera onto the origin and makes the
            # initial view appear too close.
            if show_axes:
                plotter.reset_camera()
            else:
                plotter.reset_camera_clipping_range()
        else:
            plotter.camera_position = camera_position
            plotter.reset_camera_clipping_range()
        return

    parameters = parameters or HyperboloidParameters()

    if interactive:
        # 拖动参数时使用较低网格密度，松开后由完整渲染恢复细节。
        parameters = replace(parameters, radial_resolution=32, angular_resolution=48)
    surface = two_sheet_hyperboloid(parameters)
    inner_surface = surface.copy(deep=True)
    inner_surface.flip_faces(inplace=True)
    lighting = lighting or LightSettings()
    surface_settings = surface_settings or SurfaceSettings()
    preset = material_preset(material_name)
    # 凸面始终使用外部颜色，凹面始终使用内部颜色。
    # 若用户尚未手动配色，则采用当前材质预设的默认颜色。
    outer = preset["outer_color"] if surface_settings.use_preset_colors else surface_settings.outer_color
    inner = preset["inner_color"] if surface_settings.use_preset_colors else surface_settings.inner_color
    material = {
        **preset,
        "color": outer,
        "ambient": lighting.ambient if material_name == "光泽塑料" else preset.get("ambient", lighting.ambient),
        "backface_params": {
            # 背面对应凹面，使用内部颜色。
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
    material["culling"] = "back"
    inner_material = {**material, "color": inner}
    inner_material.pop("backface_params", None)
    plotter.add_mesh(surface, name="hyperboloid", **material)
    plotter.add_mesh(inner_surface, name="hyperboloid_inner", **inner_material)

    if show_axes:
        add_cartesian_axes(
            plotter,
            DEFAULT_3D_AXIS_EXTENT,
            axis_color_mode=axis_color_mode,
            contrast_color=resolved_contrast_color,
            show_ticks=show_ticks,
            tick_spacing_mode=tick_spacing_mode,
            custom_tick_spacing=custom_tick_spacing,
        )
    if show_helpers:
        add_teaching_helpers(plotter, parameters)

    # 为半透明曲面启用正确的前后深度排序。
    if interactive:
        plotter.disable_depth_peeling()
    else:
        plotter.enable_depth_peeling(number_of_peels=8, occlusion_ratio=0.0)

    setup_three_point_lighting(plotter, lighting)
    plotter.enable_anti_aliasing("ssaa" if high_quality else "msaa")

    # 先设置观察方向，再由自动相机根据场景边界调整距离，适配任意 u_max。
    if camera_position is None:
        plotter.camera_position = _CAMERA_POSITION
        plotter.reset_camera()
    else:
        plotter.camera_position = camera_position
        plotter.reset_camera_clipping_range()


def update_lighting(plotter: pv.Plotter, settings: LightSettings) -> None:
    """不重建几何体，仅更新光照和双面材质。"""
    actors = plotter.renderer.actors
    for name, actor in actors.items():
        if name in {"hyperboloid", "hyperboloid_inner"} or name.startswith("layer:"):
            actor.prop.ambient = settings.ambient
    setup_three_point_lighting(plotter, settings)
    plotter.render()


def update_surface_colors(plotter: pv.Plotter, settings: SurfaceSettings) -> None:
    """仅更新双曲面凸面和凹面的颜色，不改变任何灯光设置。"""
    outer_actor = plotter.renderer.actors.get("hyperboloid")
    inner_actor = plotter.renderer.actors.get("hyperboloid_inner")
    if outer_actor is not None:
        outer_actor.prop.color = settings.outer_color
    if inner_actor is not None:
        inner_actor.prop.color = settings.inner_color
    plotter.render()


def update_surface_geometry(plotter: pv.Plotter, parameters: HyperboloidParameters) -> None:
    """仅更新曲面顶点，保留坐标轴、辅助线、光源和当前相机。"""
    actor = plotter.renderer.actors.get("hyperboloid")
    if actor is None:
        return
    updated_surface = two_sheet_hyperboloid(parameters)
    updated_inner_surface = updated_surface.copy(deep=True)
    updated_inner_surface.flip_faces(inplace=True)
    current_surface = actor.mapper.dataset
    if current_surface.n_points == updated_surface.n_points and current_surface.n_cells == updated_surface.n_cells:
        current_surface.points = updated_surface.points
        current_surface.Modified()
    else:
        actor.mapper.dataset = updated_surface
    inner_actor = plotter.renderer.actors.get("hyperboloid_inner")
    if inner_actor is not None:
        current_inner_surface = inner_actor.mapper.dataset
        if current_inner_surface.n_points == updated_inner_surface.n_points and current_inner_surface.n_cells == updated_inner_surface.n_cells:
            current_inner_surface.points = updated_inner_surface.points
            current_inner_surface.Modified()
        else:
            inner_actor.mapper.dataset = updated_inner_surface
    plotter.reset_camera_clipping_range()
    plotter.render()
