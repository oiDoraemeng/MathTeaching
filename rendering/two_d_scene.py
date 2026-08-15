"""跟随二维可见区域的持久化正交笛卡尔辅助线。

相机变化时不删除并重建大量线条演员，而是让网格线、刻度和坐标轴分别共享
一个持久化网格，并用 ``copy_from`` 就地更新几何数据。这样可以保留演员和
映射器，避免缩放、平移时出现明显闪烁。
"""

from __future__ import annotations

import numpy as np
import pyvista as pv

from models.scene_mode import SceneAppearance
from rendering.ticks import ViewportBounds, format_tick, tick_spacing, tick_values

_GRID_KEY = "grid_lines"
_AXIS_X_KEY = "axis_X"
_AXIS_Y_KEY = "axis_Y"
_TICK_KEY = "tick_marks"
_LABEL_KEY = "tick_labels"


def configure_2d_camera(plotter: pv.Plotter) -> None:
    """配置二维平移/缩放交互，不重置当前相机位置。"""
    plotter.enable_parallel_projection()
    if getattr(plotter, "iren", None) is not None:
        # 2D 视图中左右中键都不应产生三维轨迹球旋转；中键与左键统一用于平移。
        plotter.enable_custom_trackball_style(
            left="pan",
            shift_left="dolly",
            control_left="spin",
            middle="pan",
            shift_middle="pan",
            control_middle="pan",
            right="dolly",
            shift_right="dolly",
            control_right="rotate",
        )
    plotter.view_xy()


def _segments_to_polydata(
    segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]],
) -> pv.PolyData:
    """将独立线段打包为一个折线网格。"""
    if not segments:
        return pv.PolyData()
    points = np.asarray([point for segment in segments for point in segment], dtype=float)
    count = len(segments)
    lines = np.empty((count, 3), dtype=np.int64)
    lines[:, 0] = 2
    lines[:, 1] = np.arange(0, 2 * count, 2)
    lines[:, 2] = np.arange(1, 2 * count, 2)
    poly = pv.PolyData()
    poly.points = points
    poly.lines = lines
    return poly


class TwoDGuides:
    """以可复用的少量演员管理网格、坐标轴、刻度和标签。"""

    def __init__(self, plotter: pv.Plotter) -> None:
        self.plotter = plotter
        self._meshes: dict[str, pv.PolyData] = {}
        self._actors: dict[str, object] = {}
        self._has_labels = False

    def render(
        self,
        bounds: ViewportBounds,
        appearance: SceneAppearance,
        *,
        previous_spacing: float | None = None,
        spacing: float | None = None,
    ) -> float:
        """按给定可见范围就地更新所有二维辅助线。"""
        if spacing is None:
            spacing = tick_spacing(
                bounds.y_span,
                appearance.tick_spacing_mode,
                appearance.tick_spacing,
                previous_spacing=previous_spacing,
            )
        x_ticks = tick_values(bounds.x_range, spacing)
        y_ticks = tick_values(bounds.y_range, spacing)

        grid_color = "#3d4650" if appearance.background == "dark" else "#d8e0e7"
        self._set_geometry(
            _GRID_KEY,
            self._grid_mesh(bounds, spacing, x_ticks, y_ticks) if appearance.show_grid else pv.PolyData(),
            color=grid_color,
            line_width=1.0,
        )

        self._set_geometry(
            _AXIS_X_KEY,
            _segments_to_polydata([((bounds.x_range[0], 0, 0), (bounds.x_range[1], 0, 0))]),
            color=_axis_color(appearance, "X"),
            line_width=2.5,
        )
        self._set_geometry(
            _AXIS_Y_KEY,
            _segments_to_polydata([((0, bounds.y_range[0], 0), (0, bounds.y_range[1], 0))]),
            color=_axis_color(appearance, "Y"),
            line_width=2.5,
        )

        label_color = appearance.contrast_axis_color
        if appearance.show_ticks:
            segments, points, labels = self._tick_geometry(bounds, spacing, x_ticks, y_ticks)
            self._set_geometry(_TICK_KEY, _segments_to_polydata(segments), color=label_color, line_width=1.4)
            self._set_labels(points, labels, label_color)
        else:
            self._set_geometry(_TICK_KEY, pv.PolyData(), color=label_color, line_width=1.4)
            self._set_labels([], [], label_color)
        return spacing

    def clear(self) -> None:
        """在绘图器清空后丢弃已缓存的演员引用。"""
        self._meshes.clear()
        self._actors.clear()
        self._has_labels = False

    def _set_geometry(self, key: str, mesh: pv.PolyData, *, color: str, line_width: float) -> None:
        actor = self._actors.get(key)
        if actor is None:
            stored = mesh.copy()
            actor = self.plotter.add_mesh(
                stored, name=key, color=color, line_width=line_width, lighting=False
            )
            self._meshes[key] = stored
            self._actors[key] = actor
        else:
            # 网格、坐标轴和刻度的拓扑固定，只复制几何数据以避免演员闪烁。
            self._meshes[key].copy_from(mesh)
            self._style(actor, color, line_width)
        actor.visibility = mesh.n_points > 0

    @staticmethod
    def _style(actor: object, color: str, line_width: float) -> None:
        prop = getattr(actor, "prop", None)
        if prop is not None:
            prop.color = color
            prop.line_width = line_width

    def _set_labels(
        self, points: list[tuple[float, float, float]], labels: list[str], color: str
    ) -> None:
        # 点标签演员无法像网格一样就地调整，只能重建；调用方已在可见范围不变时
        # 跳过刷新，因此不会在每一帧都重复创建标签。
        if self._has_labels:
            self.plotter.remove_actor(_LABEL_KEY, render=False)
            self._has_labels = False
        if not points:
            return
        self.plotter.add_point_labels(
            points, labels, font_size=12, text_color=color, shape=None,
            always_visible=True, name=_LABEL_KEY, render_points_as_spheres=False,
        )
        self._has_labels = True

    @staticmethod
    def _grid_mesh(
        bounds: ViewportBounds,
        spacing: float,
        x_ticks: tuple[float, ...],
        y_ticks: tuple[float, ...],
    ) -> pv.PolyData:
        segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]] = []
        for x in x_ticks:
            if abs(x) <= spacing * 1e-9:
                continue
            segments.append(((x, bounds.y_range[0], 0), (x, bounds.y_range[1], 0)))
        for y in y_ticks:
            if abs(y) <= spacing * 1e-9:
                continue
            segments.append(((bounds.x_range[0], y, 0), (bounds.x_range[1], y, 0)))
        return _segments_to_polydata(segments)

    @staticmethod
    def _tick_geometry(
        bounds: ViewportBounds,
        spacing: float,
        x_ticks: tuple[float, ...],
        y_ticks: tuple[float, ...],
    ) -> tuple[list, list[tuple[float, float, float]], list[str]]:
        tick_length = min(bounds.x_span, bounds.y_span) * 0.012
        label_offset = tick_length * 1.4
        x_label_y = _label_axis_position(0.0, bounds.y_range, spacing)
        y_label_x = _label_axis_position(0.0, bounds.x_range, spacing)
        segments: list = []
        points: list[tuple[float, float, float]] = []
        labels: list[str] = []
        for x in x_ticks:
            # X 轴数字位于轴下方，刻度短线位于对侧上方。
            segments.append(((x, x_label_y, 0), (x, x_label_y + tick_length, 0)))
            if abs(x) > spacing * 1e-9:
                points.append((x, x_label_y - label_offset, 0))
                labels.append(format_tick(x, spacing))
        for y in y_ticks:
            # Y 轴数字位于轴左侧，刻度短线位于对侧右方。
            segments.append(((y_label_x, y, 0), (y_label_x + tick_length, y, 0)))
            if abs(y) > spacing * 1e-9:
                points.append((y_label_x - label_offset, y, 0))
                labels.append(format_tick(y, spacing))
        return segments, points, labels


def _label_axis_position(value: float, axis_range: tuple[float, float], spacing: float) -> float:
    margin = (axis_range[1] - axis_range[0]) * 0.065
    if axis_range[0] + margin <= value <= axis_range[1] - margin:
        return value
    return axis_range[0] + margin if value < axis_range[0] + margin else axis_range[1] - margin


def _axis_color(appearance: SceneAppearance, axis: str) -> str:
    if appearance.axis_color_mode == "color":
        return {"X": "#d64545", "Y": "#2f9e5b"}[axis]
    return appearance.contrast_axis_color
