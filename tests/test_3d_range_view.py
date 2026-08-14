"""Regression tests for 3D surface range behaviour."""

import unittest

from models.surface_layer import PlotDomain, SurfaceLayer
from rendering.layer_scene import LayerSceneController


class FakeCamera:
    def __init__(self) -> None:
        self.focal_point = (0.0, 0.0, 0.0)
        self.position = (3.0, -4.0, 5.0)


class FakePlotter:
    def __init__(self) -> None:
        self.camera = FakeCamera()
        self.render_count = 0

    def render(self) -> None:
        self.render_count += 1


class FakeAlgebraPanel:
    def sync_layer(self, *_args: object) -> None:
        pass

    def set_status(self, *_args: object, **_kwargs: object) -> None:
        pass


class FakeActor:
    def __init__(self) -> None:
        self.visibility = True


class ActorPlotter:
    def __init__(self) -> None:
        self.actors: dict[str, FakeActor] = {}

    def add_mesh(self, _mesh, *, name: str, **_kwargs: object) -> FakeActor:
        actor = FakeActor()
        self.actors[name] = actor
        return actor

    def remove_actor(self, name: str, **_kwargs: object) -> None:
        self.actors.pop(name, None)


class RangeViewTests(unittest.TestCase):
    def test_surface_range_change_does_not_move_camera(self) -> None:
        from ui.designer_window import MainWindow

        window = object.__new__(MainWindow)
        window.layers = [SurfaceLayer("plane", "explicit", "z = x + y")]
        window.plotter = FakePlotter()
        window.algebra_panel = FakeAlgebraPanel()
        window.layer_controller = LayerSceneController(
            ActorPlotter(),
            PlotDomain(explicit_resolution=20, implicit_resolution=20),
        )
        window.layer_controller.add_layer(window.layers[0])

        original_position = window.plotter.camera.position
        MainWindow._set_surface_range(window, window.layers[0].id, 0.5)

        self.assertEqual(window.plotter.camera.position, original_position)
        self.assertEqual(window.layers[0].range_scale, 0.5)

    def test_default_range_scale_is_golden_ratio(self) -> None:
        layer = SurfaceLayer("plane", "explicit", "z = x + y")
        self.assertAlmostEqual(layer.range_scale, 0.618)

    def test_range_scale_clamped_to_unit_interval(self) -> None:
        layer_low = SurfaceLayer("p", "explicit", "z = 0", range_scale=0.01)
        layer_high = SurfaceLayer("p", "explicit", "z = 0", range_scale=5.0)
        self.assertEqual(layer_low.range_scale, 0.1)
        self.assertEqual(layer_high.range_scale, 1.0)


if __name__ == "__main__":
    unittest.main()
