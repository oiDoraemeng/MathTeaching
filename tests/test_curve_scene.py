"""二维曲线 actor 增量更新的回归测试。"""

import unittest

import pyvista as pv

from models.curve_layer import CurveLayer, Plot2DDomain
from rendering.curve_scene import CurveSceneController


class FakeActor:
    def __init__(self) -> None:
        self.visibility = True


class FakePlotter:
    def __init__(self) -> None:
        self.actors: dict[str, FakeActor] = {}
        self.mesh_kwargs: dict[str, dict] = {}

    def add_mesh(self, _mesh, *, name: str, **kwargs) -> FakeActor:
        actor = FakeActor()
        self.actors[name] = actor
        self.mesh_kwargs[name] = kwargs
        return actor

    def remove_actor(self, name: str, **_kwargs) -> None:
        self.actors.pop(name, None)
        self.mesh_kwargs.pop(name, None)


class CurveSceneControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.plotter = FakePlotter()
        self.controller = CurveSceneController(
            self.plotter,
            Plot2DDomain(curve_resolution=120, implicit_resolution=80),
        )
        self.layer = CurveLayer("curve", "explicit", "y = x^2 / 4", color="#2777b6")

    def test_curve_actor_uses_color_and_line_width(self) -> None:
        self.controller.add_layer(self.layer)

        actor_name = self.controller.actor_name(self.layer.id)
        self.assertEqual(self.plotter.mesh_kwargs[actor_name]["color"], "#2777b6")
        self.assertEqual(self.plotter.mesh_kwargs[actor_name]["line_width"], 2.4)

    def test_curve_display_settings_replace_only_its_actor(self) -> None:
        self.controller.add_layer(self.layer)
        actor_name = self.controller.actor_name(self.layer.id)

        self.controller.set_color(self.layer.id, "#d64545")
        self.controller.set_line_width(self.layer.id, 4.6)
        self.controller.set_visible(self.layer.id, False)

        self.assertEqual(self.plotter.mesh_kwargs[actor_name]["color"], "#d64545")
        self.assertEqual(self.plotter.mesh_kwargs[actor_name]["line_width"], 4.6)
        self.assertFalse(self.plotter.actors[actor_name].visibility)

    def test_resampling_keeps_all_layers_in_the_controller(self) -> None:
        second = CurveLayer("second", "explicit", "y = x + 2", color="#d64545")
        self.controller.add_layer(self.layer)
        self.controller.add_layer(second)

        self.controller.set_domain(Plot2DDomain(x_range=(-30, 30), y_range=(-30, 30)))

        self.assertEqual(set(self.controller.layers), {self.layer.id, second.id})
        self.assertEqual(set(self.controller.meshes), {self.layer.id, second.id})
        self.assertEqual(len([name for name in self.plotter.actors if name.startswith("curve:")]), 2)

    def test_coordinate_transform_maps_sampled_curve_points(self) -> None:
        controller = CurveSceneController(
            self.plotter,
            Plot2DDomain(x_range=(-1, 1), y_range=(-2, 2), curve_resolution=32, implicit_resolution=32),
            ((2.0, 0.0), (0.0, 1.0)),
        )
        controller.add_layer(self.layer)

        mesh = controller.meshes[self.layer.id]
        self.assertAlmostEqual(float(mesh.points[0, 0]), -2.0)
        self.assertAlmostEqual(float(mesh.points[0, 1]), 0.25)
        self.assertAlmostEqual(float(mesh.points[-1, 0]), 2.0)
        self.assertAlmostEqual(float(mesh.points[-1, 1]), 0.25)

    def test_curve_can_be_hit_tested_and_highlighted_as_the_selected_object(self) -> None:
        self.controller.add_layer(self.layer)

        hit_id = self.controller.hit_test(0.0, 0.0, 0.1)
        changed = self.controller.set_selected(hit_id)

        self.assertEqual(hit_id, self.layer.id)
        self.assertTrue(changed)
        self.assertEqual(self.controller.selected_id, self.layer.id)
        selection_name = self.controller.selection_actor_name(self.layer.id)
        self.assertIn(selection_name, self.plotter.actors)
        self.assertEqual(self.plotter.mesh_kwargs[selection_name]["color"], "#e59b00")

        self.controller.set_selected(None)
        self.assertNotIn(selection_name, self.plotter.actors)

    def test_selected_curve_highlight_is_removed_when_curve_has_no_visible_mesh(self) -> None:
        self.controller.add_layer(self.layer)
        self.controller.set_selected(self.layer.id)
        selection_name = self.controller.selection_actor_name(self.layer.id)

        self.controller.meshes[self.layer.id] = pv.PolyData()
        self.controller._replace_actor_if_present(self.layer)

        self.assertNotIn(selection_name, self.plotter.actors)


if __name__ == "__main__":
    unittest.main()
