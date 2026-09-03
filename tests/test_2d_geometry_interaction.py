"""二维画布点线工具的坐标和对象生命周期测试。"""

import unittest
from unittest.mock import MagicMock, patch

from models.geometry_2d import Point2D
from models.scene_mode import SceneMode
from rendering.geometry_scene import GeometrySceneController
from ui.designer_window import MainWindow


class FakeActor:
    def __init__(self) -> None:
        self.visibility = True


class FakeInteractor:
    def __init__(self) -> None:
        self.cursor = None

    @staticmethod
    def width() -> int:
        return 100

    @staticmethod
    def height() -> int:
        return 100

    def setCursor(self, cursor) -> None:
        self.cursor = cursor

    def setFocus(self) -> None:
        pass


class FakeCamera:
    def __init__(self) -> None:
        self.parallel_scale = 10.0
        self.focal_point = (0.0, 0.0, 0.0)
        self.position = (0.0, 0.0, 20.0)


class FakePlotter:
    def __init__(self) -> None:
        self.camera = FakeCamera()
        self.interactor = FakeInteractor()
        self.actors: dict[str, FakeActor] = {}
        self.render_count = 0

    def add_mesh(self, _mesh, *, name: str, **_kwargs) -> FakeActor:
        actor = FakeActor()
        self.actors[name] = actor
        return actor

    def remove_actor(self, name: str, **_kwargs) -> None:
        self.actors.pop(name, None)

    def render(self) -> None:
        self.render_count += 1


class FakeAlgebraPanel:
    def __init__(self) -> None:
        self.layers: list[object] = []
        self.statuses: list[tuple[str, bool]] = []

    def set_layers(self, layers) -> None:
        self.layers = list(layers)

    def set_status(self, text: str, is_error: bool = False) -> None:
        self.statuses.append((text, is_error))

    def sync_layer(self, _layer_id: str, _layer: object) -> None:
        pass

    def set_selected_layer(self, layer_id: str | None) -> None:
        self.selected_layer_id = layer_id

    def begin_geometry_edit(self, _layer_id: str) -> None:
        pass

    def finish_edit(self) -> None:
        pass


class FakePosition:
    def __init__(self, x: float, y: float) -> None:
        self._x = x
        self._y = y

    def x(self) -> float:
        return self._x

    def y(self) -> float:
        return self._y


class FakeMouseEvent:
    def __init__(self, x: float, y: float) -> None:
        self._position = FakePosition(x, y)
        self.accepted = False

    def button(self):
        from PySide6.QtCore import Qt

        return Qt.MouseButton.LeftButton

    def position(self) -> FakePosition:
        return self._position

    def accept(self) -> None:
        self.accepted = True


class FakeKeyEvent:
    def __init__(self, key=None, modifiers=None) -> None:
        from PySide6.QtCore import Qt

        self.accepted = False
        self._key = Qt.Key.Key_Escape if key is None else key
        self._modifiers = Qt.KeyboardModifier.NoModifier if modifiers is None else modifiers

    def key(self):
        return self._key

    def modifiers(self):
        return self._modifiers

    def accept(self) -> None:
        self.accepted = True


def _make_window() -> MainWindow:
    window = object.__new__(MainWindow)
    window.scene_mode = SceneMode.TWO_D
    window.plotter = FakePlotter()
    window.geometry_points = []
    window.linear_objects = []
    window.annotations = []
    window.curve_layers = []
    window._two_d_object_order = []
    window._agent_teaching_2d = {}
    window._linear_algebra_pending_vector_ids = []
    window._linear_algebra_polygon_point_ids = []
    window._linear_algebra_tool_sequence = 0
    window.geometry_controller = GeometrySceneController(
        window.plotter,
        window._current_2d_bounds(),
    )
    window.algebra_panel = FakeAlgebraPanel()
    window.scene_command_service = MagicMock()
    window._active_2d_tool = None
    window._pending_geometry_point_id = None
    window._snap_to_grid = False
    window._two_d_guide_spacing = None
    window._dragging_point_id = None
    window._drag_moved = False
    return window


class TwoDGeometryInteractionTests(unittest.TestCase):
    def test_viewport_coordinates_match_the_camera_bounds(self) -> None:
        window = _make_window()

        self.assertEqual(window._viewport_to_world(0, 0), (-10.0, 10.0))
        self.assertEqual(window._viewport_to_world(100, 100), (10.0, -10.0))
        self.assertEqual(window._viewport_to_world(50, 50), (0.0, 0.0))

    def test_zoom_keeps_cursor_world_coordinate_fixed(self) -> None:
        window = _make_window()
        window._refresh_2d_viewport = MagicMock()
        window._queue_viewport_refresh = MagicMock()
        anchor_before = window._viewport_to_world(25, 30)

        self.assertTrue(window._zoom_2d_at_viewport(25, 30, 0.5))

        anchor_after = window._viewport_to_world(25, 30)
        self.assertIsNotNone(anchor_before)
        self.assertIsNotNone(anchor_after)
        self.assertAlmostEqual(anchor_after[0], anchor_before[0])
        self.assertAlmostEqual(anchor_after[1], anchor_before[1])
        self.assertAlmostEqual(window.plotter.camera.focal_point[0], -2.5)
        self.assertAlmostEqual(window.plotter.camera.focal_point[1], 2.0)
        self.assertAlmostEqual(window.plotter.camera.position[0], -2.5)
        self.assertAlmostEqual(window.plotter.camera.position[1], 2.0)
        window._refresh_2d_viewport.assert_called_once_with(resample=True, render=True)
        window._queue_viewport_refresh.assert_called_once_with()

    def test_point_tool_reuses_nearby_points(self) -> None:
        window = _make_window()
        window._active_2d_tool = "point"

        self.assertTrue(window._handle_geometry_mouse_press(FakeMouseEvent(50, 50)))
        self.assertTrue(window._handle_geometry_mouse_press(FakeMouseEvent(51, 50)))

        self.assertEqual(len(window.geometry_points), 1)
        self.assertEqual(window.geometry_points[0].name, "A")
        self.assertEqual(len(window.algebra_panel.layers), 1)

    def test_point_tool_preserves_cursor_coordinates_when_grid_snap_is_disabled(self) -> None:
        window = _make_window()
        window._active_2d_tool = "point"
        window._snap_to_grid = False

        window._handle_geometry_mouse_press(FakeMouseEvent(37, 43))

        self.assertEqual(len(window.geometry_points), 1)
        self.assertAlmostEqual(window.geometry_points[0].x, -2.6)
        self.assertAlmostEqual(window.geometry_points[0].y, 1.4)

    def test_geometry_creation_supports_undo_and_redo(self) -> None:
        window = _make_window()
        point, created = window._get_or_create_geometry_point(-2.0, 1.0)

        self.assertTrue(created)
        self.assertEqual([point.name], [item.name for item in window.geometry_points])

        window._undo_2d_geometry()
        self.assertEqual(window.geometry_points, [])
        self.assertEqual(window.linear_objects, [])

        window._redo_2d_geometry()
        self.assertEqual(len(window.geometry_points), 1)
        self.assertEqual(window.geometry_points[0].id, point.id)
        self.assertEqual(window.geometry_points[0].x, -2.0)

    def test_keyboard_shortcuts_route_to_undo_and_redo(self) -> None:
        window = _make_window()
        point, _created = window._get_or_create_geometry_point(-2.0, 1.0)

        from PySide6.QtCore import Qt

        self.assertTrue(
            window._handle_geometry_key_press(
                FakeKeyEvent(Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
            )
        )
        self.assertEqual(window.geometry_points, [])

        self.assertTrue(
            window._handle_geometry_key_press(
                FakeKeyEvent(
                    Qt.Key.Key_Z,
                    Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier,
                )
            )
        )
        self.assertEqual(window.geometry_points[0].id, point.id)

    def test_deleting_point_can_be_undone_with_its_dependent_line(self) -> None:
        window = _make_window()
        first = Point2D("A", -1, 0)
        second = Point2D("B", 1, 0)
        window.geometry_points = [first, second]
        window.geometry_controller.add_point(first)
        window.geometry_controller.add_point(second)
        linear = window._create_linear_geometry("segment", first, second)

        window._remove_geometry_object(first.id)
        self.assertEqual(window.linear_objects, [])

        window._undo_2d_geometry()
        self.assertEqual({point.id for point in window.geometry_points}, {first.id, second.id})
        self.assertEqual(len(window.linear_objects), 1)
        self.assertEqual(window.linear_objects[0].id, linear.id)
        self.assertEqual(window.linear_objects[0].start_point_id, first.id)

    def test_dragging_point_records_one_undoable_change(self) -> None:
        window = _make_window()
        point = Point2D("A", 0, 0)
        window.geometry_points = [point]
        window.geometry_controller.add_point(point)
        window._active_2d_tool = "select"

        self.assertTrue(window._begin_select_or_drag(0, 0))
        window.geometry_controller.move_point(point.id, 1, 0)
        point.x, point.y = 1, 0
        window._drag_moved = True
        window._handle_geometry_mouse_release(FakeMouseEvent(60, 50))

        self.assertEqual(len(window._geometry_undo_stack), 1)
        window._undo_2d_geometry()
        self.assertEqual((window.geometry_points[0].x, window.geometry_points[0].y), (0, 0))

    def test_line_tool_creates_two_points_and_a_line_then_escape_cancels_it(self) -> None:
        window = _make_window()
        window._active_2d_tool = "line"

        window._handle_geometry_mouse_press(FakeMouseEvent(20, 50))
        window._handle_geometry_mouse_move(FakeMouseEvent(80, 50))
        self.assertIn("geometry:draft", window.plotter.actors)
        window._handle_geometry_mouse_press(FakeMouseEvent(80, 50))

        self.assertEqual(len(window.geometry_points), 2)
        self.assertEqual(len(window.linear_objects), 1)
        self.assertEqual(window.linear_objects[0].kind, "line")
        self.assertNotIn("geometry:draft", window.plotter.actors)
        self.assertEqual(len(window.algebra_panel.layers), 3)
        self.assertEqual(
            [object_.id for object_ in window.algebra_panel.layers],
            [point.id for point in window.geometry_points] + [window.linear_objects[0].id],
        )

        window._handle_geometry_key_press(FakeKeyEvent())
        self.assertIsNone(window._active_2d_tool)

    def test_complete_line_click_is_one_undoable_geometry_action(self) -> None:
        window = _make_window()
        window._active_2d_tool = "line"

        window._handle_geometry_mouse_press(FakeMouseEvent(20, 50))
        window._handle_geometry_mouse_press(FakeMouseEvent(80, 50))

        self.assertEqual(len(window._geometry_undo_stack), 2)
        window._undo_2d_geometry()
        self.assertEqual(len(window.geometry_points), 1)
        self.assertEqual(window.linear_objects, [])

    def test_deleting_a_point_cascades_to_its_dependent_linear_objects(self) -> None:
        window = _make_window()
        first = Point2D("A", -1, 0)
        second = Point2D("B", 1, 0)
        window.geometry_points = [first, second]
        window.geometry_controller.add_point(first)
        window.geometry_controller.add_point(second)
        linear = window._create_linear_geometry("segment", first, second)

        window._remove_geometry_object(first.id)

        self.assertEqual(window.geometry_points, [second])
        self.assertEqual(window.linear_objects, [])
        self.assertNotIn(window.geometry_controller.linear_actor_name(linear.id), window.plotter.actors)

    def test_each_linear_tool_creates_its_requested_object_type(self) -> None:
        window = _make_window()
        first = Point2D("A", -1, 0)
        second = Point2D("B", 1, 0)
        window.geometry_points = [first, second]
        window.geometry_controller.add_point(first)
        window.geometry_controller.add_point(second)

        for kind in ("line", "segment", "ray", "vector"):
            window._create_linear_geometry(kind, first, second)

        self.assertEqual(
            [linear.kind for linear in window.linear_objects],
            ["line", "segment", "ray", "vector"],
        )

    def test_linear_algebra_vector_tools_execute_after_two_vector_clicks(self) -> None:
        window = _make_window()
        origin = Point2D("O", 0, 0)
        first_end = Point2D("A", 8, 0)
        second_end = Point2D("B", 0, 8)
        window.geometry_points = [origin, first_end, second_end]
        for point in window.geometry_points:
            window.geometry_controller.add_point(point)
        first = window._create_linear_geometry("vector", origin, first_end)
        second = window._create_linear_geometry("vector", origin, second_end)

        for tool, expected_operation in (
            ("angle", "geometry.angle_arc"),
            ("projection", "geometry.projection"),
            ("subspace", "geometry.subspace_region"),
            ("area", "geometry.oriented_area"),
        ):
            window._active_linear_algebra_tool = tool
            window._linear_algebra_pending_vector_ids = []
            window.scene_command_service.reset_mock()

            self.assertTrue(window._handle_linear_algebra_vector_click(4, 0))
            self.assertTrue(window._handle_linear_algebra_vector_click(0, 4))

            window.scene_command_service.execute.assert_called_once()
            plan = window.scene_command_service.execute.call_args.args[0]
            self.assertEqual(plan.scene, "2d")
            self.assertIn(expected_operation, [operation["op"] for operation in plan.operations])
            self.assertEqual(window._linear_algebra_pending_vector_ids, [])

        self.assertEqual(first.kind, "vector")
        self.assertEqual(second.kind, "vector")

    def test_linear_algebra_polygon_finishes_on_double_click(self) -> None:
        window = _make_window()
        window._active_linear_algebra_tool = "polygon"

        for x, y in ((25, 50), (50, 25), (75, 50)):
            event = FakeMouseEvent(x, y)
            self.assertTrue(window._handle_geometry_mouse_press(event))
            self.assertTrue(event.accepted)

        event = FakeMouseEvent(75, 50)
        self.assertTrue(window._handle_geometry_double_click(event))
        self.assertTrue(event.accepted)
        plan = window.scene_command_service.execute.call_args.args[0]
        self.assertEqual(plan.operations[0]["op"], "geometry.polygon")
        self.assertEqual(len(plan.operations[0]["vertices"]), 3)
        self.assertEqual(window._linear_algebra_polygon_point_ids, [])

    def test_linear_algebra_polygon_can_close_by_clicking_its_first_point(self) -> None:
        window = _make_window()
        window._active_linear_algebra_tool = "polygon"
        for coordinates in ((-4, 0), (0, 4), (4, 0)):
            window._handle_linear_algebra_polygon_click(*coordinates)

        self.assertTrue(window._handle_linear_algebra_polygon_click(-4, 0))

        plan = window.scene_command_service.execute.call_args.args[0]
        self.assertEqual(plan.operations[0]["op"], "geometry.polygon")
        self.assertEqual(window._linear_algebra_polygon_point_ids, [])

    def test_linear_algebra_transform_uses_matrix_dialog_and_separate_overlays(self) -> None:
        window = _make_window()
        window._active_linear_algebra_tool = "transform"
        with patch("ui.designer_window.QInputDialog.getText", return_value=("1,0;0,2", True)):
            event = FakeMouseEvent(50, 50)
            self.assertTrue(window._handle_geometry_mouse_press(event))

        plan = window.scene_command_service.execute.call_args.args[0]
        self.assertEqual(
            [operation["op"] for operation in plan.operations],
            ["geometry.transformed_grid", "geometry.staged_transform", "annotation.formula"],
        )
        self.assertNotEqual(plan.operations[0]["alias"], plan.operations[1]["alias"])
        self.assertEqual(plan.operations[1]["matrices"], [[[1.0, 0.0], [0.0, 2.0]]])

    def test_escape_cancels_linear_algebra_tool(self) -> None:
        window = _make_window()
        window._active_linear_algebra_tool = "area"
        window._linear_algebra_pending_vector_ids = ["v"]
        event = FakeKeyEvent()

        self.assertTrue(window._handle_geometry_key_press(event))
        self.assertTrue(event.accepted)
        self.assertIsNone(window._active_linear_algebra_tool)
        self.assertIsNone(window._active_2d_tool)
        self.assertEqual(window._linear_algebra_pending_vector_ids, [])


if __name__ == "__main__":
    unittest.main()
