"""Persistent orthographic Cartesian guides that follow the visible 2D view.

Instead of deleting and rebuilding dozens of line actors on every camera
change (which forces VTK to rebuild its render pipeline and produces the
visible flicker), all grid lines share a single persistent mesh, all tick
marks share another, and the axes are one mesh each. Camera changes update
the geometry in place via ``copy_from`` so the actors and their mappers are
never torn down.
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
    """Apply the 2D pan/zoom interaction style without resetting the camera."""
    plotter.enable_parallel_projection()
    if getattr(plotter, "iren", None) is not None:
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
    """Pack independent line segments into one poly-line mesh."""
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
    """Own the grid, axes, ticks, and labels as a small pool of reused actors."""

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
        """Update every guide in place for the supplied visible bounds."""
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
        """Forget cached actors after the plotter itself has been cleared."""
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
        # Point-label actors cannot be resized in place, so they are the one
        # guide we rebuild — but only when the visible region actually changed,
        # which the caller already gates on.
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
            segments.append(((x, x_label_y, 0), (x, x_label_y + tick_length, 0)))
            if abs(x) > spacing * 1e-9:
                points.append((x, x_label_y - label_offset, 0))
                labels.append(format_tick(x, spacing))
        for y in y_ticks:
            segments.append(((y_label_x, y, 0), (y_label_x - tick_length, y, 0)))
            if abs(y) > spacing * 1e-9:
                points.append((y_label_x + label_offset, y, 0))
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
