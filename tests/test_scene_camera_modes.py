"""保持二维和三维相机模式独立的回归测试。"""

import unittest
from math import radians, tan
from unittest.mock import patch

from rendering.scene import DEFAULT_3D_AXIS_EXTENT, build_scene, configure_3d_camera_interaction
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

    def test_blank_3d_scene_keeps_explicit_camera_distance(self) -> None:
        plotter = FakePlotter()

        with patch("rendering.scene.setup_three_point_lighting"), patch(
            "rendering.scene.add_cartesian_axes"
        ):
            build_scene(plotter, show_axes=False, base_surface=False)

        self.assertEqual(plotter.camera.position[0], (12.8, -14.4, 11.4))
        self.assertNotIn("reset_camera", plotter.calls)

    def test_3d_axis_extent_is_a_fixed_world_value(self) -> None:
        from ui.designer_window import MainWindow
        from ui.scene_pane_manager import ScenePaneManager

        window = object.__new__(MainWindow)
        window.pane_manager = ScenePaneManager()
        window._pane_scene()._three_d_extent = None
        window._pane_renderer = lambda: object()  # type: ignore[method-assign]

        self.assertEqual(MainWindow._current_3d_axis_extent(window), DEFAULT_3D_AXIS_EXTENT)

        window._pane_scene()._three_d_extent = 7.0
        self.assertEqual(MainWindow._current_3d_axis_extent(window), DEFAULT_3D_AXIS_EXTENT)

    def test_3d_axis_compensation_accounts_for_view_angle_zoom(self) -> None:
        from models.scene_mode import SceneAppearance, SceneMode
        from ui.designer_window import MainWindow
        from ui.scene_pane_manager import ScenePaneManager

        class Camera:
            position = (12.8, -14.4, 11.4)
            focal_point = (0.0, 0.0, 0.0)
            view_angle = 30.0

        class Renderer:
            camera = Camera()

            def render(self) -> None:
                pass

        class Axes:
            def __init__(self) -> None:
                self.extents: list[float] = []

            def render(self, extent: float, **_kwargs: object) -> float:
                self.extents.append(extent)
                return 1.0

        window = object.__new__(MainWindow)
        window.pane_manager = ScenePaneManager()
        window._pane().renderer_2d = window._pane().renderer_3d = Renderer()
        window._pane_scene().scene_appearances = {SceneMode.THREE_D: SceneAppearance()}
        axes = Axes()
        window._pane_scene()._three_d_axes = axes
        window._pane_scene()._three_d_extent = DEFAULT_3D_AXIS_EXTENT
        window._pane_scene()._three_d_reference_projection_scale = MainWindow._camera_projection_scale(window)
        window._pane_scene()._three_d_spacing = 1.0
        window.effective_theme = "light"

        # VTK's camera.zoom(2) halves the view angle while keeping distance;
        # the axis world length must halve to keep the same screen size.
        Renderer.camera.view_angle = 15.0
        MainWindow._refresh_3d_axes_for_camera(window)

        expected_ratio = tan(radians(15.0 / 2.0)) / tan(radians(30.0 / 2.0))
        self.assertAlmostEqual(axes.extents[-1], DEFAULT_3D_AXIS_EXTENT * expected_ratio)

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
