"""Tests for automatic and manually selected intersection actors."""

from dataclasses import replace
import unittest

from models.surface_layer import PlotDomain, SurfaceLayer
from rendering.layer_scene import LayerSceneController


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


class LayerSceneControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.plotter = FakePlotter()
        self.controller = LayerSceneController(
            self.plotter,
            PlotDomain(explicit_resolution=20, implicit_resolution=20),
        )
        self.sphere = SurfaceLayer(
            name="sphere",
            kind="implicit",
            expression="x^2 + y^2 + z^2 = 1",
            color="#3f7fbf",
            opacity=0.35,
        )
        self.plane = SurfaceLayer(name="plane", kind="explicit", expression="z = 0", color="#cb684b")

    def test_visible_layers_automatically_create_an_intersection_actor(self) -> None:
        self.controller.add_layer(self.sphere)
        self.controller.add_layer(self.plane)

        intersection_name = self.controller.intersection_actor_name(self.sphere.id, self.plane.id)

        self.assertIn(intersection_name, self.plotter.actors)
        self.assertTrue(self.plotter.actors[intersection_name].visibility)

    def test_turning_off_auto_mode_requires_an_explicit_pair_selection(self) -> None:
        self.controller.add_layer(self.sphere)
        self.controller.add_layer(self.plane)
        intersection_name = self.controller.intersection_actor_name(self.sphere.id, self.plane.id)

        self.controller.set_auto_intersections(False)
        self.assertNotIn(intersection_name, self.plotter.actors)

        self.controller.set_manual_intersection_pair(self.sphere.id, self.plane.id, True)
        self.assertIn(intersection_name, self.plotter.actors)

    def test_layer_color_and_opacity_are_passed_to_its_surface_actor(self) -> None:
        self.controller.add_layer(self.sphere)

        mesh_kwargs = self.plotter.mesh_kwargs[f"layer:{self.sphere.id}:surface"]

        self.assertEqual(mesh_kwargs["color"], "#3f7fbf")
        self.assertEqual(mesh_kwargs["opacity"], 0.35)

    def test_layer_actors_receive_the_scene_ambient_light_level(self) -> None:
        controller = LayerSceneController(
            self.plotter,
            PlotDomain(explicit_resolution=20, implicit_resolution=20),
            ambient=0.43,
        )
        controller.add_layer(self.sphere)

        mesh_kwargs = self.plotter.mesh_kwargs[f"layer:{self.sphere.id}:surface"]
        self.assertEqual(mesh_kwargs["ambient"], 0.43)

    def test_appearance_updates_replace_only_the_surface_actor_without_resampling(self) -> None:
        self.controller.add_layer(self.sphere)

        self.controller.set_color(self.sphere.id, "#8e5aa7")
        self.controller.set_opacity(self.sphere.id, 0.5)

        mesh_kwargs = self.plotter.mesh_kwargs[f"layer:{self.sphere.id}:surface"]
        self.assertEqual(mesh_kwargs["color"], "#8e5aa7")
        self.assertEqual(mesh_kwargs["opacity"], 0.5)

    def test_material_preset_updates_reflection_without_overwriting_layer_color_or_opacity(self) -> None:
        self.controller.add_layer(self.sphere)

        self.controller.set_material("抛光金属")

        mesh_kwargs = self.plotter.mesh_kwargs[f"layer:{self.sphere.id}:surface"]
        self.assertEqual(mesh_kwargs["color"], "#3f7fbf")
        self.assertEqual(mesh_kwargs["opacity"], 0.35)
        self.assertEqual(mesh_kwargs["diffuse"], 0.62)
        self.assertEqual(mesh_kwargs["specular"], 1.0)
        self.assertEqual(mesh_kwargs["specular_power"], 110)

    def test_intersection_curve_is_rendered_as_a_thin_black_line(self) -> None:
        self.controller.add_layer(self.sphere)
        self.controller.add_layer(self.plane)

        intersection_name = self.controller.intersection_actor_name(self.sphere.id, self.plane.id)
        mesh_kwargs = self.plotter.mesh_kwargs[intersection_name]

        self.assertEqual(mesh_kwargs["color"], "#111111")
        self.assertEqual(mesh_kwargs["line_width"], 1.5)
        self.assertFalse(mesh_kwargs["render_lines_as_tubes"])

    def test_layer_range_scale_resamples_only_that_layer_beyond_the_default_domain(self) -> None:
        self.controller.add_layer(self.plane)

        self.controller.update_layer(replace(self.plane, range_scale=2.0))

        mesh = self.controller.meshes[self.plane.id]
        self.assertEqual(mesh.bounds.x_min, -6.0)
        self.assertEqual(mesh.bounds.x_max, 6.0)


if __name__ == "__main__":
    unittest.main()
