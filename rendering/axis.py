"""三维工作区的持久化笛卡尔坐标轴。

坐标轴和刻度只创建一次。相机缩放或旋转后，仅通过 ``copy_from`` 或
``mapper.dataset`` 替换几何数据，保留演员及 VTK 映射器，从而避免每帧
重建渲染管线造成闪烁。
"""

from __future__ import annotations

import numpy as np
import pyvista as pv

from rendering.materials import AXIS_COLOR, AXIS_LABEL_COLOR, AXIS_MATERIAL
from rendering.ticks import format_tick, tick_spacing, tick_values


_AXIS_LABELS = ("X", "Y", "Z")
_AXIS_COLORS = {"X": "#d64545", "Y": "#2f9e5b", "Z": "#3478c7"}
_DIRECTIONS = np.eye(3)


class ThreeDAxes:
    """管理坐标轴箭头、刻度和标签演员，并就地更新它们。"""

    def __init__(self, plotter: pv.Plotter) -> None:
        self.plotter = plotter
        self._arrow_meshes: dict[str, pv.PolyData] = {}
        self._arrow_actors: dict[str, object] = {}
        self._tick_mesh: pv.PolyData | None = None
        self._tick_actor: object | None = None
        self._has_labels: set[str] = set()

    def render(
        self,
        extent: float,
        *,
        axis_color_mode: str = "contrast",
        contrast_color: str | None = None,
        show_ticks: bool = True,
        tick_spacing_mode: str = "auto",
        custom_tick_spacing: float = 1.0,
        previous_spacing: float | None = None,
    ) -> float:
        """按给定范围更新坐标轴几何，并返回最终采用的刻度间距。"""
        extent = max(0.5, float(extent))
        default_color = contrast_color or AXIS_COLOR
        label_color = contrast_color or AXIS_LABEL_COLOR

        for direction, label in zip(_DIRECTIONS, _AXIS_LABELS):
            arrow = pv.Arrow(
                start=-extent * direction,
                direction=direction,
                scale=2.0 * extent,
                tip_length=0.06,
                tip_radius=0.0016,
                shaft_radius=0.0005,
            )
            color = _AXIS_COLORS[label] if axis_color_mode == "color" else default_color
            self._set_arrow(f"axis_{label}", arrow, color)
            lbl_color = color if axis_color_mode == "color" else label_color
            self._set_label(
                f"axis_label_{label}",
                [extent * 1.13 * direction],
                [label],
                font_size=17,
                color=lbl_color,
            )
        self._set_label(
            "axis_origin_label",
            [[0.0, 0.0, 0.0]],
            ["O"],
            font_size=15,
            color=label_color,
        )

        spacing = tick_spacing(
            2.0 * extent,
            tick_spacing_mode,
            custom_tick_spacing,
            target_intervals=10,
            previous_spacing=previous_spacing,
        )
        if show_ticks:
            self._set_ticks(extent, spacing, label_color)
        else:
            self._clear_ticks()
        return spacing

    def clear(self) -> None:
        """在绘图器被清空后丢弃已缓存的演员引用。"""
        self._arrow_meshes.clear()
        self._arrow_actors.clear()
        self._tick_mesh = None
        self._tick_actor = None
        self._has_labels.clear()

    # ------------------------------------------------------------------ #
    # 内部更新逻辑
    # ------------------------------------------------------------------ #

    def _set_arrow(self, key: str, mesh: pv.PolyData, color: str) -> None:
        actor = self._arrow_actors.get(key)
        if actor is None:
            stored = mesh.copy()
            actor = self.plotter.add_mesh(stored, color=color, name=key, **AXIS_MATERIAL)
            self._arrow_meshes[key] = stored
            self._arrow_actors[key] = actor
        else:
            stored = self._arrow_meshes[key]
            if stored.n_points == mesh.n_points and stored.n_cells == mesh.n_cells:
                # 拓扑未变化时只复制顶点数据，避免 VTK 重新创建映射器。
                stored.copy_from(mesh)
            else:
                # 箭头范围变化可能改变拓扑，此时才替换映射器的数据集。
                mapper = getattr(actor, "mapper", None)
                if mapper is not None:
                    mapper.dataset = mesh
                self._arrow_meshes[key] = mesh
            prop = getattr(actor, "prop", None)
            if prop is not None:
                prop.color = color

    def _set_label(
        self,
        key: str,
        points: list,
        labels: list[str],
        *,
        font_size: int = 12,
        color: str = "#252a33",
    ) -> None:
        if key in self._has_labels:
            self.plotter.remove_actor(key, render=False)
        self.plotter.add_point_labels(
            points,
            labels,
            font_size=font_size,
            text_color=color,
            shape=None,
            always_visible=True,
            name=key,
            render_points_as_spheres=False,
        )
        self._has_labels.add(key)

    def _set_ticks(self, extent: float, spacing: float, color: str) -> None:
        values = tuple(
            v for v in tick_values((-extent, extent), spacing)
            if abs(v) > spacing * 1e-9
        )
        tick_length = extent * 0.025
        label_offset = tick_length * 1.4
        segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []
        points: list[tuple[float, float, float]] = []
        labels: list[str] = []
        for axis_index in range(3):
            for value in values:
                # 刻度短线与数字分别位于轴的两侧，防止数字遮挡轴线和刻度。
                if axis_index == 0:
                    s, e, lp = (
                        (value, 0, 0),
                        (value, tick_length, 0),
                        (value, -label_offset, 0),
                    )
                elif axis_index == 1:
                    s, e, lp = (
                        (0, value, 0),
                        (-tick_length, value, 0),
                        (label_offset, value, 0),
                    )
                else:
                    s, e, lp = (
                        (0, 0, value),
                        (-tick_length, 0, value),
                        (label_offset, 0, value),
                    )
                segments.append((s, e))
                points.append(lp)
                labels.append(format_tick(value, spacing))

        mesh = _segments_to_polydata(segments)
        if self._tick_actor is None:
            stored = mesh.copy()
            self._tick_actor = self.plotter.add_mesh(
                stored, name="tick3d_marks", color=color, line_width=1.2, lighting=False,
            )
            self._tick_mesh = stored
        else:
            # 刻度网格的拓扑固定，只更新点坐标即可响应缩放。
            self._tick_mesh.copy_from(mesh)
            prop = getattr(self._tick_actor, "prop", None)
            if prop is not None:
                prop.color = color
        self._tick_actor.visibility = mesh.n_points > 0

        if "tick3d_labels" in self._has_labels:
            self.plotter.remove_actor("tick3d_labels", render=False)
            self._has_labels.discard("tick3d_labels")
        if points:
            self.plotter.add_point_labels(
                points, labels, font_size=11, text_color=color, shape=None,
                always_visible=True, name="tick3d_labels", render_points_as_spheres=False,
            )
            self._has_labels.add("tick3d_labels")

    def _clear_ticks(self) -> None:
        if self._tick_actor is not None:
            self._tick_actor.visibility = False
        if "tick3d_labels" in self._has_labels:
            self.plotter.remove_actor("tick3d_labels", render=False)
            self._has_labels.discard("tick3d_labels")


def _segments_to_polydata(
    segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]],
) -> pv.PolyData:
    if not segments:
        return pv.PolyData()
    points = np.asarray([p for seg in segments for p in seg], dtype=float)
    count = len(segments)
    lines = np.empty((count, 3), dtype=np.int64)
    lines[:, 0] = 2
    lines[:, 1] = np.arange(0, 2 * count, 2)
    lines[:, 2] = np.arange(1, 2 * count, 2)
    poly = pv.PolyData()
    poly.points = points
    poly.lines = lines
    return poly


# ---------------------------------------------------------------------- #
# 兼容 build_scene 在清空绘图器后的单次创建入口
# ---------------------------------------------------------------------- #

def add_cartesian_axes(
    plotter: pv.Plotter,
    extent: float,
    *,
    axis_color_mode: str = "contrast",
    contrast_color: str | None = None,
    show_ticks: bool = True,
    tick_spacing_mode: str = "auto",
    custom_tick_spacing: float = 1.0,
) -> float:
    """供 scene.py 在 ``plotter.clear()`` 后一次性创建坐标轴。"""
    axes = ThreeDAxes(plotter)
    return axes.render(
        extent,
        axis_color_mode=axis_color_mode,
        contrast_color=contrast_color,
        show_ticks=show_ticks,
        tick_spacing_mode=tick_spacing_mode,
        custom_tick_spacing=custom_tick_spacing,
    )


def remove_cartesian_axes(plotter: pv.Plotter) -> None:
    """只删除命名的坐标轴和刻度演员，不影响函数几何图层。"""
    actors = getattr(getattr(plotter, "renderer", None), "actors", None) or plotter.actors
    for name in tuple(actors):
        if name.startswith(("axis_", "tick3d_")):
            plotter.remove_actor(name, render=False)
