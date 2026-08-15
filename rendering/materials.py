"""集中管理材质预设，便于统一调校光照与曲面外观。

主曲面使用 Phong 材质，通过集中且明亮的镜面高光呈现三点光照下的半透明
光泽效果。线条和辅助几何使用不受光照影响的颜色样式。
"""

# 材质预设不仅改变颜色，也改变表面对光的反应，从而呈现不同物质感。
MATERIAL_PRESETS = {
    "光泽塑料": {
        "outer_color": "#8d70d6",
        "inner_color": "#eee6d9",
        "color": "#8d70d6",
        "opacity": 0.66,         # 透明度
        "smooth_shading": True,  # 平滑度
        "ambient": 0.20,         # 环境光系数
        "diffuse": 0.65,         # 漫反射光系数
        "specular": 0.85,        # 镜面高光系数
        "specular_power": 45,    # 镜面高光强度
       
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
        "outer_color": "#c89b49",
        "inner_color": "#f1ce89",
        "opacity": 1.0,
        "smooth_shading": True,
        "ambient": 0.30,
        "diffuse": 0.62,
        "specular": 1.0,
        "specular_power": 110,
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

# 教学辅助线使用不受光照影响的纯色样式，保证在深浅背景下均清晰可见。
SECTION_MATERIAL = dict(color="#d9bd79", line_width=2.6)
GENERATOR_MATERIAL = dict(color="#785cb8", opacity=0.55, line_width=1.0)
CONSTRUCTION_MATERIAL = dict(color="#4b5563", line_width=1.5)
