"""保持二维和三维相机模式独立的回归测试。"""

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6.QtCore import QEvent

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

        self.assertEqual(plotter.camera.position[0], ((9.6, -10.8, 8.55)))
        self.assertNotIn("reset_camera", plotter.calls)

    def test_3d_axis_extent_is_a_fixed_world_value(self) -> None:
        from ui.designer_window import MainWindow

        window = object.__new__(MainWindow)
        self.assertEqual(MainWindow._current_3d_axis_extent(window), DEFAULT_3D_AXIS_EXTENT)


    def test_wheel_input_activates_its_own_pane_before_zoom_handling(self) -> None:
        from ui.designer_window import _GeometryInputFilter
        from ui.scene_pane_manager import ScenePaneManager

        class WheelEvent:
            @staticmethod
            def type() -> QEvent.Type:
                return QEvent.Type.Wheel

        manager = ScenePaneManager()
        first, second = manager.set_layout(2)
        watched = object()
        owner = SimpleNamespace(
            pane_manager=manager,
            scene_pane_widget=SimpleNamespace(interactors={second: watched}),
        )
        _GeometryInputFilter(owner, None).eventFilter(watched, WheelEvent())

        self.assertEqual(manager.active_pane_id, second)
        self.assertNotEqual(manager.active_pane_id, first)

    def test_3d_interactions_update_vector_heads_without_rebuilding_axes(self) -> None:
        from models.scene_mode import SceneMode
        from ui.designer_window import MainWindow
        from ui.scene_pane_manager import ScenePaneManager

        window = object.__new__(MainWindow)
        window.pane_manager = ScenePaneManager()
        window._pane_scene().scene_mode = SceneMode.THREE_D
        window._pane_scene()._viewport_refreshing = False
        window._queue_viewport_refresh = MagicMock()
        window._refresh_3d_arrows_for_camera = MagicMock()
        window._save_current_view_state = MagicMock()

        MainWindow._on_viewport_interacting(window)
        MainWindow._on_viewport_interaction_finished(window)

        window._queue_viewport_refresh.assert_not_called()
        self.assertEqual(window._refresh_3d_arrows_for_camera.call_count, 2)
        window._save_current_view_state.assert_called_once_with()

    def test_3d_viewport_refresh_remeasures_vector_heads_after_resize(self) -> None:
        from models.scene_mode import SceneMode
        from ui.designer_window import MainWindow
        from ui.scene_pane_manager import ScenePaneManager

        window = object.__new__(MainWindow)
        window.pane_manager = ScenePaneManager()
        window._pane_scene().scene_mode = SceneMode.THREE_D
        window._pane_scene()._three_d_axes = None
        window._refresh_3d_arrows_for_camera = MagicMock()

        MainWindow._refresh_3d_viewport(window, render=False)

        window._refresh_3d_arrows_for_camera.assert_called_once_with()

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
