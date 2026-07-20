"""教材风格的笛卡尔坐标轴。"""

import numpy as np
import pyvista as pv

from rendering.materials import AXIS_COLOR, AXIS_LABEL_COLOR, AXIS_MATERIAL


def add_cartesian_axes(plotter: pv.Plotter, extent: float) -> None:
    """添加细箭头坐标轴及 X/Y/Z 标签。"""
    directions = np.eye(3) 
    labels = ("X", "Y", "Z")
    for direction, label in zip(directions, labels):
        start = -extent * direction
        arrow = pv.Arrow(
            start=start, direction=direction, 
            scale=2.0 * extent,
            tip_length=0.06, 
            tip_radius=0.0016, # 箭头粗细
            shaft_radius=0.0005, # 轴线粗细
        )
        plotter.add_mesh(arrow, color=AXIS_COLOR, name=f"axis_{label}", **AXIS_MATERIAL)
        plotter.add_point_labels(
            [extent * 1.13 * direction], [label], font_size=17, text_color=AXIS_LABEL_COLOR,
            shape=None, always_visible=True, name=f"axis_label_{label}", render_points_as_spheres=False,
        )
    plotter.add_point_labels([[0.0, 0.0, 0.0]], ["O"], font_size=15, text_color=AXIS_LABEL_COLOR, shape=None,
                             always_visible=True, name="origin_label", render_points_as_spheres=False)
