"""视图使用的辅助作图几何。"""

import numpy as np
import pyvista as pv

from geometry.hyperboloid import section_ellipse
from models.parameters import HyperboloidParameters
from rendering.materials import CONSTRUCTION_MATERIAL, GENERATOR_MATERIAL, SECTION_MATERIAL


def _dashed_polyline(points: np.ndarray, dash_count: int = 20) -> list[pv.PolyData]:
    """将折线分割为可见的虚线段。"""
    pieces: list[pv.PolyData] = []
    for index in range(0, len(points) - 2, 2):
        if index % 4 >= 2:
            continue
        segment = pv.Line(points[index], points[min(index + 2, len(points) - 1)], resolution=1)
        pieces.append(segment)
    return pieces


def add_teaching_helpers(plotter: pv.Plotter, parameters: HyperboloidParameters) -> None:
    """添加高亮截线、中心轴和虚线投影。"""
    show_sections = False
    u = parameters.u_max  # 控制截线所在高度

    if show_sections:
        upper = section_ellipse(parameters, u) # 闭合的椭圆截线
        lower = upper.copy()
        lower[:, 2] *= -1

        for name, ellipse in (("upper_section", upper), ("lower_section", lower)):
            plotter.add_mesh(pv.lines_from_points(ellipse, close=True), name=name, **SECTION_MATERIAL)

    extent = parameters.c * np.cosh(parameters.u_max) * 1.15
    plotter.add_mesh(pv.Line((0, 0, -extent), (0, 0, extent)), name="center_axis", **CONSTRUCTION_MATERIAL)

    # 直径辅助线：横向/纵向穿过截面中心的虚线。
    center_z = parameters.c * np.cosh(u)
    radius_x = parameters.a * np.sinh(u)
    radius_y = parameters.b * np.sinh(u)
    constructions = [
        np.array([[-radius_x, 0, center_z], [radius_x, 0, center_z]]), # 直径辅助线 1：沿 x 方向的直径
        np.array([[0, -radius_y, center_z], [0, radius_y, center_z]]), # 直径辅助线 2：沿 y 方向的直径
        # np.array([[radius_x, 0, center_z], [radius_x, 0, 0.0]]),       # 到坐标轴的辅助线：从截面边缘垂直连到 z 轴  
    ]
    for index, endpoints in enumerate(constructions):
        points = np.linspace(endpoints[0], endpoints[1], 41)
        for dash_index, dash in enumerate(_dashed_polyline(points)):
            plotter.add_mesh(dash, name=f"dash_{index}_{dash_index}", **CONSTRUCTION_MATERIAL)

    # 母线使曲面的构造更加清晰。
    for angle in (0.25, 2.5, 4.2):
        uu = np.linspace(0, parameters.u_max, 48)
        line = np.column_stack((
            parameters.a * np.sinh(uu) * np.cos(angle),
            parameters.b * np.sinh(uu) * np.sin(angle),
            parameters.c * np.cosh(uu),
        ))
        plotter.add_mesh(pv.lines_from_points(line), **GENERATOR_MATERIAL)
