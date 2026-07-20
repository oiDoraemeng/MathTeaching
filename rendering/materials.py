"""集中管理材质预设，便于统一调校光照与曲面外观。

主曲面使用 Phong 材质，通过集中且明亮的镜面高光呈现三点光照下的半透明
光泽效果。线条和辅助几何使用不受光照影响的颜色样式。
"""

# 主双曲面：半透明紫色。较低环境光加强阴影层次，较高镜面反射及其指数形成光泽高光。
SURFACE_MATERIAL = dict(
    color="#8d70d6",      # 紫色
    opacity=0.66,           # 透明度
    smooth_shading=True,    # 平滑着色
    ambient=0.20,           # 环境光
    diffuse=0.65,           # 漫反射
    specular=0.85,          # 镜面反射
    specular_power=45,      # 高光范围
)


# 材质预设不仅改变颜色，也改变表面对光的反应，从而呈现不同物质感。
MATERIAL_PRESETS = {
    "光泽塑料": {
        **SURFACE_MATERIAL,
        "outer_color": "#8d70d6",
        "inner_color": "#eee6d9",
    },
    "透明玻璃": {
        "outer_color": "#78c9f5",
        "inner_color": "#dff6ff",
        "opacity": 0.28,
        "smooth_shading": True,
        "ambient": 0.05,
        "diffuse": 0.30,
        "specular": 1.0,
        "specular_power": 110,
    },
    "磨砂陶瓷": {
        "outer_color": "#d6c9b5",
        "inner_color": "#eee6d9",
        "opacity": 1.0,
        "smooth_shading": True,
        "ambient": 0.30,
        "diffuse": 0.78,
        "specular": 0.10,
        "specular_power": 10,
    },
    "抛光金属": {
        "outer_color": "#b9873f",
        "inner_color": "#e5c47e",
        "opacity": 1.0,
        "smooth_shading": True,
        "pbr": True,
        "metallic": 0.92,
        "roughness": 0.16,
    },
    "半透明玉石": {
        "outer_color": "#57a88e",
        "inner_color": "#b7ead5",
        "opacity": 0.76,
        "smooth_shading": True,
        "ambient": 0.38,
        "diffuse": 0.62,
        "specular": 0.28,
        "specular_power": 24,
    },
}


def material_preset(name: str) -> dict:
    """返回指定材质的副本，避免运行时修改全局预设。"""
    return MATERIAL_PRESETS.get(name, MATERIAL_PRESETS["光泽塑料"]).copy()

# 坐标轴箭头参与光照，获得轻微的明暗变化。
AXIS_MATERIAL = dict(smooth_shading=True, ambient=0.40, diffuse=0.60)
AXIS_COLOR = "#39404b"
AXIS_LABEL_COLOR = "#252a33"

# Teaching helpers (lines) — unlit color styling.
SECTION_MATERIAL = dict(color="#d9bd79", line_width=2.6)
GENERATOR_MATERIAL = dict(color="#785cb8", opacity=0.55, line_width=1.0)
CONSTRUCTION_MATERIAL = dict(color="#4b5563", line_width=1.5)
