"""已采样曲面网格的数值两两交线计算。"""

from __future__ import annotations

import pyvista as pv


def intersect_surface_meshes(first: pv.PolyData, second: pv.PolyData) -> pv.PolyData:
    """返回两个三角曲面网格共享的交线折线几何。"""
    if first.n_cells == 0 or second.n_cells == 0:
        return pv.PolyData()
    # 交线算法以三角面片为输入；预先三角化可兼容显式和隐式曲面的不同网格拓扑。
    intersection, _first_split, _second_split = first.triangulate().intersection(
        second.triangulate(),
        split_first=False,
        split_second=False,
    )
    return intersection.clean()
