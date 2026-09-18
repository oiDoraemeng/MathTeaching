"""替换视口辅助线时不替换公式 actor 的回归测试。"""

import unittest

from models.scene_mode import SceneAppearance
from rendering.axis import ThreeDAxes, add_cartesian_axes
from rendering.ticks import ViewportBounds, tick_values
from rendering.two_d_scene import TwoDGuides


class FakeActor:
    def __init__(self) -> None:
        self.visibility = True

    @property
    def prop(self):
        return None


class FakePlotter:
    def __init__(self) -> None:
        self.actors: dict[str, FakeActor] = {}
        self.meshes: dict[str, object] = {}
        self.mesh_kwargs: dict[str, dict[str, object]] = {}

    def add_mesh(self, mesh, *, name: str, **kwargs) -> FakeActor:
        actor = FakeActor()
        self.actors[name] = actor
        self.meshes[name] = mesh
        self.mesh_kwargs[name] = kwargs
        return actor

    def add_point_labels(self, _points, _labels, *, name: str, **_kwargs) -> FakeActor:
        actor = FakeActor()
        self.actors[name] = actor
        return actor

    def remove_actor(self, name: str, **_kwargs) -> None:
        self.actors.pop(name, None)


class ViewportGuideTests(unittest.TestCase):
    def test_2d_guide_refresh_leaves_curve_actors_alone(self) -> None:
        plotter = FakePlotter()
        plotter.actors["curve:one"] = FakeActor()
        appearance = SceneAppearance()
        guides = TwoDGuides(plotter)

        guides.render(ViewportBounds((-10, 10), (-10, 10)), appearance)
        self.assertIn("grid_lines", plotter.actors)

        guides.render(ViewportBounds((-100, 100), (-100, 100)), appearance)
        self.assertIn("curve:one", plotter.actors)
        self.assertIn("grid_lines", plotter.actors)

    def test_2d_ticks_can_be_hidden_while_axes_and_grid_remain(self) -> None:
        plotter = FakePlotter()
        appearance = SceneAppearance(show_ticks=False)
        guides = TwoDGuides(plotter)

        guides.render(ViewportBounds((-5, 5), (-5, 5)), appearance)

        self.assertIn("grid_lines", plotter.actors)
        self.assertIn("axis_X", plotter.actors)
        # 刻度线 actor 应存在，但当前设置下不应包含可见几何。
        tick_actor = plotter.actors.get("tick_marks")
        self.assertIsNotNone(tick_actor)
        self.assertNotIn("tick_labels", plotter.actors)

    def test_2d_guides_can_keep_original_and_transformed_actors_separate(self) -> None:
        plotter = FakePlotter()
        appearance = SceneAppearance()
        original = TwoDGuides(plotter)
        original.actor_prefix = "original_"
        transformed = TwoDGuides(plotter)

        original.render(ViewportBounds((-2, 2), (-2, 2)), appearance, muted=True)
        transformed.render(
            ViewportBounds((-2, 2), (-2, 2)),
            appearance,
            coordinate_transform=((2.0, 0.0), (0.0, 1.0)),
        )

        self.assertIn("original_grid_lines", plotter.actors)
        self.assertIn("original_axis_X", plotter.actors)
        self.assertIn("grid_lines", plotter.actors)
        self.assertIn("axis_X", plotter.actors)
        self.assertNotEqual(
            plotter.meshes["original_grid_lines"].points.tolist(),
            plotter.meshes["grid_lines"].points.tolist(),
        )

    def test_3d_ticks_can_be_hidden_while_axes_remain(self) -> None:
        plotter = FakePlotter()

        add_cartesian_axes(plotter, 5.0, show_ticks=False)

        self.assertIn("axis_X", plotter.actors)
        self.assertFalse(any(name.startswith("tick3d_") for name in plotter.actors))

    def test_3d_axes_use_screen_width_shafts_and_cone_heads(self) -> None:
        plotter = FakePlotter()

        add_cartesian_axes(plotter, 5.0, show_ticks=False)

        for name in ("axis_X", "axis_Y", "axis_Z"):
            mesh = plotter.meshes[name]
            kwargs = plotter.mesh_kwargs[name]
            self.assertEqual(mesh.n_lines, 1)
            self.assertGreater(mesh.n_faces, 0)
            self.assertEqual(kwargs["line_width"], 1.6)
            self.assertIs(kwargs["render_lines_as_tubes"], False)

    def test_2d_tick_marks_extend_only_away_from_their_number_labels(self) -> None:
        bounds = ViewportBounds((-5, 5), (-5, 5))
        spacing = 1.0
        x_ticks = tick_values(bounds.x_range, spacing)
        y_ticks = tick_values(bounds.y_range, spacing)

        segments, points, _labels = TwoDGuides._tick_geometry(
            bounds, spacing, x_ticks, y_ticks
        )

        x_segments = segments[:len(x_ticks)]
        y_segments = segments[len(x_ticks):]
        self.assertTrue(all(start[1] == 0 and end[1] > 0 for start, end in x_segments))
        self.assertTrue(all(start[0] == 0 and end[0] > 0 for start, end in y_segments))
        nonzero_x_count = sum(abs(value) > spacing * 1e-9 for value in x_ticks)
        y_label_points = points[nonzero_x_count:]
        self.assertTrue(all(point[0] < 0 for point in y_label_points))

    def test_3d_tick_marks_extend_only_away_from_their_number_labels(self) -> None:
        plotter = FakePlotter()
        axes = ThreeDAxes(plotter)

        axes._set_ticks(5.0, 1.0, "#252a33")

        points = axes._tick_mesh.points
        values_per_axis = len(
            [value for value in tick_values((-5.0, 5.0), 1.0) if value != 0]
        )
        x_segments = points[:2 * values_per_axis].reshape((-1, 2, 3))
        y_segments = points[2 * values_per_axis:4 * values_per_axis].reshape((-1, 2, 3))
        z_segments = points[4 * values_per_axis:].reshape((-1, 2, 3))
        self.assertTrue(all(start[1] == 0 and end[1] > 0 for start, end in x_segments))
        self.assertTrue(all(start[0] == 0 and end[0] < 0 for start, end in y_segments))
        self.assertTrue(all(start[0] == 0 and end[0] < 0 for start, end in z_segments))
        self.assertEqual(plotter.mesh_kwargs["tick3d_marks"]["line_width"], 1.2)
        self.assertIs(
            plotter.mesh_kwargs["tick3d_marks"]["render_lines_as_tubes"], False
        )


if __name__ == "__main__":
    unittest.main()
