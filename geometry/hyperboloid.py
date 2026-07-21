"""双叶双曲面的参数化几何生成。"""

import numpy as np
import pyvista as pv

from models.parameters import HyperboloidParameters


def two_sheet_hyperboloid(parameters: HyperboloidParameters) -> pv.PolyData:
    """生成双叶双曲面的两个互不相连曲面。
    x = a * sinh(u) * cos(v)
    y = b * sinh(u) * sin(v)
    z = c * cosh(u)
    参数范围为 u in [0, u_max]、v in [0, 2*pi]。
    """
    u = np.linspace(0.0, parameters.u_max, parameters.radial_resolution) 
    v = np.linspace(0.0, 2.0 * np.pi, parameters.angular_resolution)
    uu, vv = np.meshgrid(u, v, indexing="ij")  # 网格化参数空间

    x = parameters.a * np.sinh(uu) * np.cos(vv)
    y = parameters.b * np.sinh(uu) * np.sin(vv)
    z = parameters.c * np.cosh(uu)

    upper = pv.StructuredGrid(x, y, z).extract_surface(algorithm="dataset_surface")
    lower = pv.StructuredGrid(x, y, -z).extract_surface(algorithm="dataset_surface")
    # 上叶的默认面绕序朝向凹侧；翻转后，两个曲面的正面均朝向凸侧。
    upper.flip_faces(inplace=True)
    return upper.merge(lower).clean()


def section_ellipse(parameters: HyperboloidParameters, u: float) -> np.ndarray:
    """返回给定 u 值处的闭合椭圆截线。"""
    angle = np.linspace(0.0, 2.0 * np.pi, 121)
    return np.column_stack(
        (
            parameters.a * np.sinh(u) * np.cos(angle),
            parameters.b * np.sinh(u) * np.sin(angle),
            np.full_like(angle, parameters.c * np.cosh(u)),
        )
    )
