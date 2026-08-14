"""Regression tests for keeping 2D and 3D camera modes independent."""

import unittest
from unittest.mock import patch

from rendering.scene import build_scene, configure_3d_camera_interaction
from rendering.two_d_scene import configure_2d_camera


class FakeCamera:
    def __init__(self) -> None:
        self.position = None
        self.focal_point = (2.0, -1.0, 3.0)


class FakeStyle:
    def __init__(self) -> None:
        self.observers: list[tuple[str, object, float]] = []

    def AddObserver(self, event: str, callback: object, priority: float) -> int:
        self.observers.append((event, callback, priority))
        return len(self.observers)


class FakeInputState:
    def GetShiftKey(self) -> bool:
        return False

    def GetControlKey(self) -> bool:
        return False


class FakeRenderWindowInteractor:
    def __init__(self) -> None:
        self.style = FakeStyle()
        self.interactor = FakeInputState()


class FakePlotter:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.camera = FakeCamera()
        self.iren = FakeRenderWindowInteractor()
        self.interaction_options: dict[str, str] = {}

    def clear(self) -> None:
        self.calls.append("clear")

    def set_background(self, _color: str) -> None:
        self.calls.append("set_background")

    def disable_parallel_projection(self) -> None:
        self.calls.append("disable_parallel_projection")

    def enable_parallel_projection(self) -> None:
        self.calls.append("enable_parallel_projection")

    def enable_custom_trackball_style(self, **options: str) -> None:
        self.calls.append("enable_custom_trackball_style")
        self.interaction_options = options

    def view_xy(self) -> None:
        self.calls.append("view_xy")

    def enable_depth_peeling(self, **_kwargs: object) -> None:
        self.calls.append("enable_depth_peeling")

    def enable_anti_aliasing(self, _mode: str) -> None:
        self.calls.append("enable_anti_aliasing")

    def reset_camera(self) -> None:
        self.calls.append("reset_camera")

    def reset_camera_clipping_range(self) -> None:
        self.calls.append("reset_camera_clipping_range")

    @property
    def camera_position(self):
        return self.camera.position

    @camera_position.setter
    def camera_position(self, value) -> None:
        self.camera.position = value


class SceneCameraModeTests(unittest.TestCase):
    def test_3d_scene_disables_parallel_projection_left_by_2d_mode(self) -> None:
        plotter = FakePlotter()

        with patch("rendering.scene.setup_three_point_lighting"), patch(
            "rendering.scene.add_cartesian_axes"
        ):
            build_scene(plotter, base_surface=False)

        self.assertIn("disable_parallel_projection", plotter.calls)
        self.assertLess(
            plotter.calls.index("disable_parallel_projection"),
            plotter.calls.index("reset_camera"),
        )

    def test_2d_middle_button_pans_instead_of_spinning(self) -> None:
        plotter = FakePlotter()

        configure_2d_camera(plotter)

        self.assertEqual(plotter.interaction_options["left"], "pan")
        self.assertEqual(plotter.interaction_options["middle"], "pan")
        self.assertEqual(plotter.interaction_options["shift_middle"], "pan")
        self.assertEqual(plotter.interaction_options["control_middle"], "pan")

    def test_3d_left_rotation_focuses_origin_and_middle_button_pans(self) -> None:
        plotter = FakePlotter()

        configure_3d_camera_interaction(plotter)

        self.assertEqual(plotter.interaction_options["left"], "rotate")
        self.assertEqual(plotter.interaction_options["middle"], "pan")
        event, callback, priority = plotter.iren.style.observers[0]
        self.assertEqual(event, "LeftButtonPressEvent")
        self.assertEqual(priority, 1.0)
        callback(None, None)
        self.assertEqual(plotter.camera.focal_point, (0.0, 0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
