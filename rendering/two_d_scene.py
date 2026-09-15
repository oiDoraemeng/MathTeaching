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

# A 2 x 2 matrix maps coordinates from the source basis into the displayed
# world coordinates.  Keeping this as a small tuple (rather than a numpy
# matrix) makes it safe to carry in a pane snapshot.
CoordinateTransform = tuple[tuple[float, float], tuple[float, float]]


def coordinate_source_bounds(
    bounds: ViewportBounds,
    matrix: CoordinateTransform,
) -> ViewportBounds:
    """Return source-coordinate bounds that cover a displayed viewport.

    The visible camera bounds are expressed in the transformed/world basis.
    Grid ticks are generated in source coordinates, so the four viewport
    corners are mapped through the inverse matrix first.
    """
    a, b = matrix[0]
    c, d = matrix[1]
    determinant = a * d - b * c
    if abs(determinant) <= 1e-12:
        raise ValueError("Coordinate transform matrix must be invertible")
    inverse = ((d / determinant, -b / determinant), (-c / determinant, a / determinant))
    corners = (
        (bounds.x_range[0], bounds.y_range[0]),
        (bounds.x_range[0], bounds.y_range[1]),
        (bounds.x_range[1], bounds.y_range[0]),
        (bounds.x_range[1], bounds.y_range[1]),
    )
    source = tuple(
        (
            inverse[0][0] * x + inverse[0][1] * y,
            inverse[1][0] * x + inverse[1][1] * y,
        )
        for x, y in corners
    )
    return ViewportBounds(
        (min(point[0] for point in source), max(point[0] for point in source)),
        (min(point[1] for point in source), max(point[1] for point in source)),
    )


def _transform_point(
    point: tuple[float, float, float], matrix: CoordinateTransform
) -> tuple[float, float, float]:
    x, y, z = point
    return (
        matrix[0][0] * x + matrix[0][1] * y,
        matrix[1][0] * x + matrix[1][1] * y,
        z,
    )


def _transform_segments(
    segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]],
    matrix: CoordinateTransform,
) -> list[tuple[tuple[float, float, float], tuple[float, float, float]]]:
    return [(_transform_point(start, matrix), _transform_point(end, matrix)) for start, end in segments]


def _overscan_bounds(bounds: ViewportBounds, fraction: float = 0.10) -> ViewportBounds:
    """Return bounds expanded for line geometry while retaining visible ticks.

    The extra span ensures grid and axis actors continue past the viewport;
    rendering remains clipped by VTK's viewport instead of by finite world
    endpoints.
    """
    x_margin = max(abs(bounds.x_span) * fraction, 1e-6)
    y_margin = max(abs(bounds.y_span) * fraction, 1e-6)
    return ViewportBounds(
        (bounds.x_range[0] - x_margin, bounds.x_range[1] + x_margin),
        (bounds.y_range[0] - y_margin, bounds.y_range[1] + y_margin),
    )


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
        self.plotter = plotter # 保存绘图器实例
        self._meshes: dict[str, pv.PolyData] = {} # 保存网格、坐标轴和刻度的网格数据
        self._actors: dict[str, object] = {}  # 保存网格、坐标轴和刻度的演员引用
        self._has_labels = False   # 用于判断是否需要重建点标签演员

    def render(
        self,
        bounds: ViewportBounds,
        appearance: SceneAppearance,
        *,
        effective_theme: str = "light",
        previous_spacing: float | None = None,
        spacing: float | None = None,
        coordinate_transform: CoordinateTransform | None = None,
    ) -> float:
        """按给定可见范围就地更新所有二维辅助线。"""
        source_bounds = (
            coordinate_source_bounds(bounds, coordinate_transform)
            if coordinate_transform is not None
            else bounds
        )
        if spacing is None:
            spacing = tick_spacing(
                source_bounds.y_span,
                appearance.tick_spacing_mode,
                appearance.tick_spacing,
                previous_spacing=previous_spacing,
            )
        x_ticks = tick_values(source_bounds.x_range, spacing)
        y_ticks = tick_values(source_bounds.y_range, spacing)
        # Extend guide geometry beyond the visible viewport.  VTK clips actors
        # to the viewport, so terminating lines exactly at the current bounds
        # creates a faint artificial frame when zooming or panning.  Keeping
        # the sampled ticks tied to ``bounds`` while overscanning line
        # endpoints preserves pointer anchored camera interaction and lets the
        # viewport provide the only clipping boundary.
        draw_bounds = _overscan_bounds(source_bounds)

        grid_color = _grid_color(appearance, effective_theme)
        grid_mesh = self._grid_mesh(draw_bounds, spacing, x_ticks, y_ticks) if appearance.show_grid else pv.PolyData()
        if coordinate_transform is not None and grid_mesh.n_points:
            grid_mesh = self._transform_mesh(grid_mesh, coordinate_transform)
        self._set_geometry(
            _GRID_KEY,
            grid_mesh,
            color=grid_color,
            line_width=1.0, # 网格线宽度
        )

        x_axis = [((draw_bounds.x_range[0], 0, 0), (draw_bounds.x_range[1], 0, 0))]
        y_axis = [((0, draw_bounds.y_range[0], 0), (0, draw_bounds.y_range[1], 0))]
        if coordinate_transform is not None:
            x_axis = _transform_segments(x_axis, coordinate_transform)
            y_axis = _transform_segments(y_axis, coordinate_transform)
        self._set_geometry(
            _AXIS_X_KEY,
            _segments_to_polydata(x_axis),
            color=_axis_color(appearance, "X", effective_theme),
            line_width=2,  # X 轴线 宽度
        )
        self._set_geometry(
            _AXIS_Y_KEY,
            _segments_to_polydata(y_axis),
            color=_axis_color(appearance, "Y", effective_theme),
            line_width=2, # Y 轴线 宽度
        )

        label_color = appearance.contrast_axis_color(effective_theme)
        if appearance.show_ticks:
            segments, points, labels = self._tick_geometry(source_bounds, spacing, x_ticks, y_ticks)
            if coordinate_transform is not None:
                segments = _transform_segments(segments, coordinate_transform)
                points = [_transform_point(point, coordinate_transform) for point in points]
            self._set_geometry(_TICK_KEY, _segments_to_polydata(segments), color=label_color, line_width=1.4)
            self._set_labels(points, labels, label_color)
        else:
            self._set_geometry(_TICK_KEY, pv.PolyData(), color=label_color, line_width=1.4) # 刻度线宽度
            self._set_labels([], [], label_color)
        return spacing

    @staticmethod
    def _transform_mesh(mesh: pv.PolyData, matrix: CoordinateTransform) -> pv.PolyData:
        transformed = mesh.copy()
        transformed.points = np.asarray(
            [_transform_point(tuple(point), matrix) for point in mesh.points],
            dtype=float,
        )
        return transformed

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
        tick_length = min(bounds.x_span, bounds.y_span) * 0.003
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


def _grid_color(appearance: SceneAppearance, effective_theme: str) -> str:
    """Use the legacy explicit grid colors and resolve auto by active theme."""
    is_dark = appearance.background == "dark" or (
        appearance.background == "auto" and effective_theme == "dark"
    )
    return "#3d4650" if is_dark else "#d8e0e7"


def _axis_color(appearance: SceneAppearance, axis: str, effective_theme: str = "light") -> str:
    if appearance.axis_color_mode == "color":
        return {"X": "#d64545", "Y": "#2f9e5b"}[axis]
    return appearance.contrast_axis_color(effective_theme)
