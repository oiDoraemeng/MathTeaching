"""二维画布点线工具的坐标和对象生命周期测试。"""

import unittest
from unittest.mock import MagicMock

from PySide6.QtCore import Qt

from models.curve_layer import CurveLayer, Plot2DDomain
from models.geometry_2d import Annotation2D, Linear2D, Point2D, geometry_latex
from models.scene_mode import SceneMode
from rendering.geometry_scene import GeometrySceneController
from rendering.curve_scene import CurveSceneController
from ui.scene_pane_manager import ScenePaneManager
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
        self.label_calls: list[dict[str, object]] = []
        self.render_count = 0

    def add_mesh(self, _mesh, *, name: str, **_kwargs) -> FakeActor:
        actor = FakeActor()
        self.actors[name] = actor
        return actor

    def remove_actor(self, name: str, **_kwargs) -> None:
        self.actors.pop(name, None)

    def add_point_labels(self, _points, _labels, **kwargs) -> None:
        self.label_calls.append(kwargs)

    def render(self) -> None:
        self.render_count += 1


class FakeAlgebraPanel:
    def __init__(self) -> None:
        self.layers: list[object] = []
        self.statuses: list[tuple[str, bool]] = []
        self.annotation_commit_count = 0
        self.removed_matrix_panes: list[str] = []

    def set_layers(self, layers) -> None:
        self.layers = list(layers)

    def set_status(self, text: str, is_error: bool = False) -> None:
        self.statuses.append((text, is_error))

    def sync_layer(self, _layer_id: str, _layer: object, **_kwargs: object) -> None:
        pass

    def set_selected_layer(self, layer_id: str | None) -> None:
        self.selected_layer_id = layer_id

    def begin_geometry_edit(self, _layer_id: str) -> None:
        pass

    def begin_annotation_edit(self, _layer_id: str) -> None:
        pass

    def commit_annotation_edit(self) -> None:
        self.annotation_commit_count += 1

    def finish_edit(self) -> None:
        pass

    def remove_matrix_transform_tab(self, pane_id: str) -> None:
        self.removed_matrix_panes.append(pane_id)


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
    window.pane_manager = ScenePaneManager()
    window._pane_scene().scene_mode = SceneMode.TWO_D
    window._pane().renderer_2d = window._pane().renderer_3d = FakePlotter()
    window._pane_scene().geometry_points = []
    window._pane_scene().linear_objects = []
    window._pane_scene().annotations = []
    window._pane_scene().curve_layers = []
    window._pane_scene()._two_d_object_order = []
    window._pane_scene()._agent_teaching_2d = {}
    window._pane_scene()._linear_algebra_pending_vector_ids = []
    window._pane_scene()._linear_algebra_polygon_point_ids = []
    window._pane_scene()._linear_algebra_tool_sequence = 0
    window._pane_scene().geometry_controller = GeometrySceneController(
        window._pane_renderer(),
        window._current_2d_bounds(),
    )
    window.algebra_panel = FakeAlgebraPanel()
    window.scene_command_service = MagicMock()
    window._pane_scene()._active_2d_tool = None
    window._pane_scene()._pending_geometry_point_id = None
    window._pane_scene()._snap_to_grid = False
    window._pane_scene()._two_d_guide_spacing = None
    window._pane_scene()._dragging_point_id = None
    window._pane_scene()._drag_moved = False
    return window


class TwoDGeometryInteractionTests(unittest.TestCase):
    def test_parameter_change_rebuilds_curve_and_shows_the_numeric_formula(self) -> None:
        window = _make_window()
        layer = CurveLayer(
            "line",
            "explicit",
            "y = a*x + b",
            parameters={"a": 1.0, "b": 0.0},
            latex="y=x",
        )
        controller = CurveSceneController(window._pane_renderer(), Plot2DDomain())
        controller.add_layer(layer)
        window._pane_scene().curve_controller = controller
        window._pane_scene().curve_layers = [layer]

        window._set_layer_parameter(layer.id, "b", 1.0)

        updated = window._pane_scene().curve_layers[0]
        self.assertEqual(updated.parameters, {"a": 1.0, "b": 1.0})
        self.assertEqual(updated.latex, "y=x + 1")
        self.assertNotIn("a", updated.latex)
        self.assertNotIn("b", updated.latex)

    def test_select_tool_can_select_a_rendered_curve(self) -> None:
        window = _make_window()
        layer = CurveLayer("axis", "explicit", "y = 0")
        controller = CurveSceneController(window._pane_renderer(), Plot2DDomain())
        controller.add_layer(layer)
        window._pane_scene().curve_controller = controller
        window._pane_scene().curve_layers = [layer]

        self.assertTrue(window._begin_select_or_drag(0.0, 0.0))

        self.assertEqual(controller.selected_id, layer.id)
        self.assertEqual(window._pane().selected_object_ids, [layer.id])
        self.assertEqual(window.algebra_panel.selected_layer_id, layer.id)

    def test_vector_addition_relation_tracks_input_drag_and_result_drag(self) -> None:
        window = _make_window()
        for operation in (
            {"op": "point.upsert", "alias": "O", "name": "O", "coordinates": [0, 0]},
            {"op": "point.upsert", "alias": "A", "name": "A", "coordinates": [2, 1]},
            {"op": "point.upsert", "alias": "B0", "name": "B", "coordinates": [4, 4]},
            # 用户已有 C 时，结果端点不能再取相同名称。
            {"op": "point.upsert", "alias": "B", "name": "C", "coordinates": [5, 6]},
        ):
            window._command_upsert_point(operation)
        window._command_upsert_linear(
            {"op": "linear.upsert", "alias": "a", "kind": "vector", "start": "O", "end": "A"}
        )
        window._command_upsert_linear(
            {"op": "linear.upsert", "alias": "b", "kind": "vector", "start": "B0", "end": "B"}
        )
        window._command_register_vector_addition(
            {
                "op": "geometry.vector_addition",
                "alias": "la_addition_1",
                "vector_a": "a",
                "vector_b": "b",
                "result_vector": "sum",
                "result_start": "sum_origin",
                "result_end": "sum_end",
                "translated_vector": "translated_b",
                "construction_aliases": ["construction_b", "construction_a"],
                "polygon_aliases": ["parallelogram"],
                "annotation_alias": "formula",
            }
        )

        scene = window._pane_scene()
        second = next(item for item in scene.linear_objects if item.agent_alias == "b")
        second_start = window._geometry_point_ref(second.start_point_id)
        assert second_start is not None
        # 向量加法只画独立的平移副本，不能改写第二条输入向量。
        self.assertEqual((second_start.x, second_start.y), (4.0, 4.0))
        first = next(item for item in scene.linear_objects if item.agent_alias == "a")
        result = window._geometry_linear_ref("sum")
        assert result is not None
        self.assertEqual(result.label, "a+b")
        self.assertTrue(
            {result.start_point_id, result.end_point_id}.isdisjoint(
                {
                    first.start_point_id,
                    first.end_point_id,
                    second.start_point_id,
                    second.end_point_id,
                }
            )
        )
        result_end_point = window._geometry_point_ref(result.end_point_id)
        assert result_end_point is not None
        self.assertEqual(result_end_point.name, "D")
        self.assertEqual(first.label, "a")
        self.assertEqual(second.label, "b")
        self.assertEqual(
            geometry_latex(result, {point.id: point for point in scene.geometry_points}),
            r"\vec{a}+\vec{b}=\overrightarrow{OD}",
        )
        self.assertEqual(result.display_start_name, "O")
        self.assertEqual(result.display_end_name, "D")
        # 新建关系会立即刷新代数区：辅助点与辅助虚线不应显示为内部对象。
        panel_layers = window.algebra_panel.layers
        self.assertTrue(panel_layers)
        self.assertFalse(any(isinstance(item, Point2D) and not item.name for item in panel_layers))
        self.assertFalse(
            any(
                isinstance(item, Linear2D)
                and item.agent_alias in {"translated_b", "construction_b", "construction_a"}
                for item in panel_layers
            )
        )
        # 窗格恢复时会再次刷新关系，结果端点的已分配名称必须保持稳定。
        window._refresh_vector_addition(scene._vector_additions[0], create_missing=True)
        self.assertEqual(result_end_point.name, "D")
        self.assertFalse(any(item.agent_alias == "formula" for item in scene.annotations))
        first_end = window._geometry_point_ref(first.end_point_id)
        assert first_end is not None
        window._move_addition_point(first_end, (3.0, 2.0))
        window._update_vector_additions_for_point(first_end.id)

        result_end = window._geometry_point_ref("sum_end")
        assert result_end is not None
        self.assertEqual((result_end.x, result_end.y), (4.0, 4.0))
        algebra_result = next(item for item in window.algebra_panel.layers if getattr(item, "agent_alias", None) == "sum")
        self.assertEqual(
            geometry_latex(algebra_result, {point.id: point for point in scene.geometry_points}),
            r"\vec{a}+\vec{b}=\overrightarrow{OD}",
        )
        polygon = scene._agent_teaching_2d["parallelogram"]
        self.assertEqual(polygon["vertices"], [[0.0, 0.0], [3.0, 2.0], [4.0, 4.0], [1.0, 2.0]])
        translated = next(item for item in scene.linear_objects if item.agent_alias == "translated_b")
        translated_start = window._geometry_point_ref(translated.start_point_id)
        translated_end = window._geometry_point_ref(translated.end_point_id)
        assert translated_start is not None and translated_end is not None
        self.assertEqual((translated_start.x, translated_start.y), (3.0, 2.0))
        self.assertEqual((translated_end.x, translated_end.y), (4.0, 4.0))

        window._select_geometry_object(second.id)
        window._move_addition_point(result_end, (10.0, 10.0))
        window._update_vector_additions_for_point(result_end.id)
        second_end = window._geometry_point_ref(second.end_point_id)
        second_start = window._geometry_point_ref(second.start_point_id)
        assert second_end is not None and second_start is not None
        self.assertEqual(
            (second_end.x - second_start.x, second_end.y - second_start.y),
            (7.0, 8.0),
        )
        self.assertEqual((result_end.x, result_end.y), (10.0, 10.0))

        window._hidden_linear_algebra_aliases = {"sum"}
        window._refresh_vector_addition(scene._vector_additions[0], create_missing=True)
        result = window._geometry_linear_ref("sum")
        assert result is not None
        self.assertFalse(result.visible)
        self.assertFalse(window._pane_renderer().actors[f"geometry:linear:{result.id}"].visibility)

    def test_select_drag_marquee_copies_only_enclosed_objects(self) -> None:
        window = _make_window()
        points = [Point2D("A", 0, 0), Point2D("B", 1, 1), Point2D("C", 7, 7)]
        window._pane_scene().geometry_points = points
        for point in points:
            window._pane_scene().geometry_controller.add_point(point)
        window._pane_scene()._active_2d_tool = "select"
        self.assertTrue(window._handle_geometry_mouse_press(FakeMouseEvent(40, 60)))
        self.assertTrue(window._handle_geometry_mouse_release(FakeMouseEvent(60, 40)))
        self.assertEqual(set(window._pane().selected_object_ids), {points[0].id, points[1].id})
        from services.scene_clipboard import parse_payload
        payload = parse_payload(window.copy_selected_scene_objects())
        self.assertEqual({record["data"]["name"] for record in payload["objects"]}, {"A", "B"})

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
        self.assertAlmostEqual(window._pane_renderer().camera.focal_point[0], -2.5)
        self.assertAlmostEqual(window._pane_renderer().camera.focal_point[1], 2.0)
        self.assertAlmostEqual(window._pane_renderer().camera.position[0], -2.5)
        self.assertAlmostEqual(window._pane_renderer().camera.position[1], 2.0)
        window._refresh_2d_viewport.assert_called_once_with(resample=True, render=True)
        window._queue_viewport_refresh.assert_called_once_with()

    def test_point_tool_reuses_nearby_points(self) -> None:
        window = _make_window()
        window._pane_scene()._active_2d_tool = "point"

        self.assertTrue(window._handle_geometry_mouse_press(FakeMouseEvent(50, 50)))
        self.assertTrue(window._handle_geometry_mouse_press(FakeMouseEvent(51, 50)))

        self.assertEqual(len(window._pane_scene().geometry_points), 1)
        self.assertEqual(window._pane_scene().geometry_points[0].name, "A")
        self.assertEqual(len(window.algebra_panel.layers), 1)

    def test_annotation_tool_creates_an_editable_text_row_at_the_clicked_position(self) -> None:
        window = _make_window()
        window._pane_scene()._active_2d_tool = "annotation"

        event = FakeMouseEvent(40, 60)
        self.assertTrue(window._handle_geometry_mouse_press(event))

        annotation = window._pane_scene().annotations[0]
        self.assertTrue(event.accepted)
        self.assertTrue(annotation.editable)
        self.assertEqual((annotation.x, annotation.y), (-2.0, -2.0))
        self.assertEqual(annotation.text, "")
        self.assertEqual(annotation.color, "#263241")
        self.assertIsNone(window._pane_scene()._active_2d_tool)
        self.assertIn(annotation, window.algebra_panel.layers)
        self.assertEqual(window.algebra_panel.annotation_commit_count, 1)

        window._update_annotation_from_algebra(
            window._pane().pane_id, annotation.id, r"\text{中文 English 标记}"
        )
        self.assertEqual(annotation.text, "中文 English 标记")
        self.assertEqual(annotation.latex, r"\text{中文 English 标记}")

        window._undo_2d_geometry()
        self.assertEqual(window._pane_scene().annotations[0].text, "")

    def test_annotation_tool_uses_a_light_label_on_a_dark_scene(self) -> None:
        window = _make_window()
        window.effective_theme = "dark"
        window._pane_scene()._active_2d_tool = "annotation"

        self.assertTrue(window._handle_geometry_mouse_press(FakeMouseEvent(50, 50)))

        self.assertEqual(window._pane_scene().annotations[0].color, "#f3f6fa")

    def test_editable_annotation_uses_hand_cursor_and_can_be_dragged(self) -> None:
        window = _make_window()
        annotation = Annotation2D("标记 1", "拖动我", 0.0, 0.0, editable=True)
        window._pane_scene().annotations = [annotation]
        window._pane_scene().geometry_controller.add_annotation(annotation)
        window._pane_scene()._active_2d_tool = None

        window._handle_geometry_mouse_move(FakeMouseEvent(50, 50))
        self.assertEqual(
            window._pane_renderer().interactor.cursor,
            Qt.CursorShape.OpenHandCursor,
        )
        self.assertEqual(window._pane_scene().geometry_controller._hover_id, annotation.id)
        self.assertEqual(window._pane_renderer().label_calls[-1]["shape"], "rounded_rect")

        self.assertFalse(window._handle_geometry_mouse_move(FakeMouseEvent(90, 50)))
        self.assertEqual(window._pane_renderer().interactor.cursor, Qt.CursorShape.ArrowCursor)
        self.assertIsNone(window._pane_scene().geometry_controller._hover_id)
        self.assertIsNone(window._pane_renderer().label_calls[-1]["shape"])

        window._handle_geometry_mouse_move(FakeMouseEvent(50, 50))
        self.assertTrue(window._handle_geometry_mouse_press(FakeMouseEvent(50, 50)))
        self.assertEqual(
            window._pane_renderer().interactor.cursor,
            Qt.CursorShape.ClosedHandCursor,
        )
        self.assertTrue(window._handle_geometry_mouse_move(FakeMouseEvent(70, 40)))
        window._handle_geometry_mouse_release(FakeMouseEvent(70, 40))

        self.assertEqual((annotation.x, annotation.y), (4.0, 2.0))
        self.assertTrue(window.pane_manager.can_undo)
        window._undo_2d_geometry()
        restored = window._pane_scene().annotations[0]
        self.assertEqual((restored.x, restored.y), (0.0, 0.0))

    def test_point_tool_preserves_cursor_coordinates_when_grid_snap_is_disabled(self) -> None:
        window = _make_window()
        window._pane_scene()._active_2d_tool = "point"
        window._pane_scene()._snap_to_grid = False

        window._handle_geometry_mouse_press(FakeMouseEvent(37, 43))

        self.assertEqual(len(window._pane_scene().geometry_points), 1)
        self.assertAlmostEqual(window._pane_scene().geometry_points[0].x, -2.6)
        self.assertAlmostEqual(window._pane_scene().geometry_points[0].y, 1.4)

    def test_geometry_creation_supports_undo_and_redo(self) -> None:
        window = _make_window()
        point, created = window._get_or_create_geometry_point(-2.0, 1.0)

        self.assertTrue(created)
        self.assertEqual([point.name], [item.name for item in window._pane_scene().geometry_points])

        window._undo_2d_geometry()
        self.assertEqual(window._pane_scene().geometry_points, [])
        self.assertEqual(window._pane_scene().linear_objects, [])

        window._redo_2d_geometry()
        self.assertEqual(len(window._pane_scene().geometry_points), 1)
        self.assertEqual(window._pane_scene().geometry_points[0].id, point.id)
        self.assertEqual(window._pane_scene().geometry_points[0].x, -2.0)

    def test_undo_redo_restores_annotation_and_curve_controllers(self) -> None:
        window = _make_window()
        annotation = Annotation2D("note", "hello", 1.0, 2.0)
        curve = CurveLayer("f", "explicit", "x")
        window._pane_scene().annotations = [annotation]
        window._pane_scene().curve_layers = [curve]
        window._pane_scene().geometry_controller.add_annotation(annotation)
        window._pane_scene().curve_controller = MagicMock()
        window._pane_scene().curve_controller.layers = []

        state = window._capture_geometry_state()
        window._pane_scene().annotations = []
        window._pane_scene().curve_layers = []
        window._restore_geometry_state(state)

        assert window._pane_scene().annotations[0].id == annotation.id
        window._pane_scene().curve_controller.add_layer.assert_called_once()

    def test_hidden_pane_restore_does_not_require_renderer(self) -> None:
        window = _make_window()
        hidden_id = window.pane_manager.create_pane()
        hidden = window._pane(hidden_id)
        hidden.renderer_2d = hidden.renderer_3d = None
        with window._using_pane(hidden_id):
            state = window._capture_scene_command_state()
            window._restore_scene_command_state(state)
        assert window._pane_renderer(hidden_id, required=False) is None

        # Switching a retained pane's mode must also avoid using the renderer
        # belonging to its previous mode.
        with window._using_pane(hidden_id):
            state = window._capture_scene_command_state()
            state = state.__class__(**{**state.__dict__, "scene_mode": SceneMode.THREE_D})
            window._restore_scene_command_state(state)
        assert window._pane_scene(hidden_id).scene_mode is SceneMode.THREE_D

    def test_algebra_layers_include_annotations(self) -> None:
        window = _make_window()
        annotation = Annotation2D("note", "hello", 1.0, 2.0)
        window._pane_scene().annotations = [annotation]
        layers = window._two_d_panel_layers()
        assert annotation in layers

    def test_algebra_layers_deduplicate_same_named_point_at_same_coordinates(self) -> None:
        window = _make_window()
        first_origin = Point2D("O", 0.0, 0.0)
        second_origin = Point2D("O", 0.0, 0.0)
        window._pane_scene().geometry_points = [first_origin, second_origin]

        layers = window._two_d_panel_layers()

        origins = [
            layer
            for layer in layers
            if isinstance(layer, Point2D) and layer.name == "O"
        ]
        assert origins == [first_origin]

    def test_keyboard_shortcuts_route_to_undo_and_redo(self) -> None:
        window = _make_window()
        point, _created = window._get_or_create_geometry_point(-2.0, 1.0)

        from PySide6.QtCore import Qt

        self.assertTrue(
            window._handle_geometry_key_press(
                FakeKeyEvent(Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
            )
        )
        self.assertEqual(window._pane_scene().geometry_points, [])

        self.assertTrue(
            window._handle_geometry_key_press(
                FakeKeyEvent(
                    Qt.Key.Key_Z,
                    Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier,
                )
            )
        )
        self.assertEqual(window._pane_scene().geometry_points[0].id, point.id)

    def test_deleting_point_can_be_undone_with_its_dependent_line(self) -> None:
        window = _make_window()
        first = Point2D("A", -1, 0)
        second = Point2D("B", 1, 0)
        window._pane_scene().geometry_points = [first, second]
        window._pane_scene().geometry_controller.add_point(first)
        window._pane_scene().geometry_controller.add_point(second)
        linear = window._create_linear_geometry("segment", first, second)

        window._remove_geometry_object(first.id)
        self.assertEqual(window._pane_scene().linear_objects, [])

        window._undo_2d_geometry()
        self.assertEqual({point.id for point in window._pane_scene().geometry_points}, {first.id, second.id})
        self.assertEqual(len(window._pane_scene().linear_objects), 1)
        self.assertEqual(window._pane_scene().linear_objects[0].id, linear.id)
        self.assertEqual(window._pane_scene().linear_objects[0].start_point_id, first.id)

    def test_dragging_point_records_one_undoable_change(self) -> None:
        window = _make_window()
        point = Point2D("A", 0, 0)
        window._pane_scene().geometry_points = [point]
        window._pane_scene().geometry_controller.add_point(point)
        window._pane_scene()._active_2d_tool = "select"

        self.assertTrue(window._begin_select_or_drag(0, 0))
        window._pane_scene().geometry_controller.move_point(point.id, 1, 0)
        point.x, point.y = 1, 0
        window._pane_scene()._drag_moved = True
        window._handle_geometry_mouse_release(FakeMouseEvent(60, 50))

        self.assertEqual(len(window._pane_scene()._geometry_undo_stack), 1)
        window._undo_2d_geometry()
        self.assertEqual((window._pane_scene().geometry_points[0].x, window._pane_scene().geometry_points[0].y), (0, 0))

    def test_line_tool_creates_two_points_and_a_line_then_escape_cancels_it(self) -> None:
        window = _make_window()
        window._pane_scene()._active_2d_tool = "line"

        window._handle_geometry_mouse_press(FakeMouseEvent(20, 50))
        window._handle_geometry_mouse_move(FakeMouseEvent(80, 50))
        self.assertIn("geometry:draft", window._pane_renderer().actors)
        window._handle_geometry_mouse_press(FakeMouseEvent(80, 50))

        self.assertEqual(len(window._pane_scene().geometry_points), 2)
        self.assertEqual(len(window._pane_scene().linear_objects), 1)
        self.assertEqual(window._pane_scene().linear_objects[0].kind, "line")
        self.assertNotIn("geometry:draft", window._pane_renderer().actors)
        self.assertEqual(len(window.algebra_panel.layers), 3)
        self.assertEqual(
            [object_.id for object_ in window.algebra_panel.layers],
            [point.id for point in window._pane_scene().geometry_points] + [window._pane_scene().linear_objects[0].id],
        )

        window._handle_geometry_key_press(FakeKeyEvent())
        self.assertIsNone(window._pane_scene()._active_2d_tool)

    def test_complete_line_click_is_one_undoable_geometry_action(self) -> None:
        window = _make_window()
        window._pane_scene()._active_2d_tool = "line"

        window._handle_geometry_mouse_press(FakeMouseEvent(20, 50))
        window._handle_geometry_mouse_press(FakeMouseEvent(80, 50))

        self.assertEqual(len(window._pane_scene()._geometry_undo_stack), 2)
        window._undo_2d_geometry()
        self.assertEqual(len(window._pane_scene().geometry_points), 1)
        self.assertEqual(window._pane_scene().linear_objects, [])

    def test_deleting_a_point_cascades_to_its_dependent_linear_objects(self) -> None:
        window = _make_window()
        first = Point2D("A", -1, 0)
        second = Point2D("B", 1, 0)
        window._pane_scene().geometry_points = [first, second]
        window._pane_scene().geometry_controller.add_point(first)
        window._pane_scene().geometry_controller.add_point(second)
        linear = window._create_linear_geometry("segment", first, second)

        window._remove_geometry_object(first.id)

        self.assertEqual(window._pane_scene().geometry_points, [second])
        self.assertEqual(window._pane_scene().linear_objects, [])
        self.assertNotIn(window._pane_scene().geometry_controller.linear_actor_name(linear.id), window._pane_renderer().actors)

    def test_each_linear_tool_creates_its_requested_object_type(self) -> None:
        window = _make_window()
        first = Point2D("A", -1, 0)
        second = Point2D("B", 1, 0)
        window._pane_scene().geometry_points = [first, second]
        window._pane_scene().geometry_controller.add_point(first)
        window._pane_scene().geometry_controller.add_point(second)

        for kind in ("line", "segment", "ray", "vector"):
            window._create_linear_geometry(kind, first, second)

        self.assertEqual(
            [linear.kind for linear in window._pane_scene().linear_objects],
            ["line", "segment", "ray", "vector"],
        )

    def test_dashed_segment_tool_persists_a_dashed_segment(self) -> None:
        window = _make_window()
        window._pane_scene()._active_2d_tool = "dashed_segment"

        self.assertTrue(window._handle_geometry_mouse_press(FakeMouseEvent(25, 75)))
        self.assertTrue(window._handle_geometry_mouse_press(FakeMouseEvent(75, 25)))

        self.assertEqual(len(window._pane_scene().linear_objects), 1)
        dashed = window._pane_scene().linear_objects[0]
        self.assertEqual(dashed.kind, "segment")
        self.assertEqual(dashed.style, "dashed")

    def test_linear_algebra_vector_tools_execute_after_two_vector_clicks(self) -> None:
        window = _make_window()
        origin = Point2D("O", 0, 0)
        first_end = Point2D("A", 8, 0)
        second_end = Point2D("B", 0, 8)
        window._pane_scene().geometry_points = [origin, first_end, second_end]
        for point in window._pane_scene().geometry_points:
            window._pane_scene().geometry_controller.add_point(point)
        first = window._create_linear_geometry("vector", origin, first_end)
        second = window._create_linear_geometry("vector", origin, second_end)

        for tool, expected_operation in (
            ("angle", "geometry.angle_arc"),
            ("projection", "geometry.projection"),
            ("subspace", "geometry.subspace_region"),
            ("area", "geometry.oriented_area"),
        ):
            window._pane_scene()._active_linear_algebra_tool = tool
            window._pane_scene()._linear_algebra_pending_vector_ids = []
            window.scene_command_service.reset_mock()

            self.assertTrue(window._handle_linear_algebra_vector_click(4, 0))
            self.assertTrue(window._handle_linear_algebra_vector_click(0, 4))

            window.scene_command_service.execute.assert_called_once()
            plan = window.scene_command_service.execute.call_args.args[0]
            self.assertEqual(plan.scene, "2d")
            self.assertIn(expected_operation, [operation["op"] for operation in plan.operations])
            self.assertEqual(window._pane_scene()._linear_algebra_pending_vector_ids, [])

        self.assertEqual(first.kind, "vector")
        self.assertEqual(second.kind, "vector")

    def test_angle_and_projection_use_a_translated_copy_without_moving_inputs(self) -> None:
        for tool in ("angle", "projection"):
            window = _make_window()
            points = [
                Point2D("O", 0, 0),
                Point2D("A", 8, 0),
                Point2D("B0", 8, -8),
                Point2D("B", 8, 0),
            ]
            window._pane_scene().geometry_points = points
            for point in points:
                window._pane_scene().geometry_controller.add_point(point)
            first = window._create_linear_geometry("vector", points[0], points[1])
            second = window._create_linear_geometry("vector", points[2], points[3])
            window._pane_scene()._active_linear_algebra_tool = tool

            self.assertTrue(window._handle_linear_algebra_vector_click(4, 0))
            self.assertTrue(window._handle_linear_algebra_vector_click(8, -4))

            second_start = window._geometry_point_ref(second.start_point_id)
            second_end = window._geometry_point_ref(second.end_point_id)
            assert second_start is not None and second_end is not None
            self.assertEqual((second_start.x, second_start.y), (8.0, -8.0))
            self.assertEqual((second_end.x, second_end.y), (8.0, 0.0))
            plan = window.scene_command_service.execute.call_args.args[0]
            overlay = plan.operations[0]
            self.assertEqual(overlay["source_vector_id"], first.id)
            self.assertEqual(overlay["direction_vector_id"], second.id)
            window._apply_scene_command(dict(overlay))
            copy_name = f"geometry:teaching:translated-vector:{overlay['alias']}"
            self.assertIn(copy_name, window._pane_scene().geometry_controller._teaching_meshes)

    def test_live_angle_and_projection_follow_vector_endpoint_changes(self) -> None:
        from ui.linear_algebra_tools import build_vector_tool_plan

        window = _make_window()
        points = [Point2D("O", 0, 0), Point2D("A", 3, 4), Point2D("B", 2, 0)]
        window._pane_scene().geometry_points = points
        for point in points:
            window._pane_scene().geometry_controller.add_point(point)
        first = window._create_linear_geometry("vector", points[0], points[1])
        second = window._create_linear_geometry("vector", points[0], points[2])
        point_map = {point.id: point for point in points}

        projection_plan = build_vector_tool_plan(
            "projection",
            (first, second),
            point_map,
            window._current_2d_bounds(),
            "la_tool_projection_test",
        )
        assert projection_plan is not None
        for operation in projection_plan.operations:
            window._apply_scene_command(dict(operation))
        projection = window._pane_scene()._agent_teaching_2d["la_tool_projection_test"]
        self.assertEqual(projection["style"], "dashed")
        projection_label = next(
            item for item in window._pane_scene().annotations
            if item.agent_alias == "la_tool_projection_test_label"
        )
        self.assertEqual(projection_label.text, "proj_b(a)=(3, 0)")

        points[1].x, points[1].y = 4.0, 2.0
        window._pane_scene().geometry_controller.move_point(points[1].id, 4.0, 2.0)
        window._update_vector_additions_for_point(points[1].id)
        projection = window._pane_scene()._agent_teaching_2d["la_tool_projection_test"]
        self.assertEqual(projection["vector"], [4.0, 2.0])
        self.assertEqual(projection_label.text, "proj_b(a)=(4, 0)")

        window._pane_scene().geometry_controller.clear_teaching_prefix("la_tool_projection_test")
        window._pane_scene()._agent_teaching_2d.pop("la_tool_projection_test")
        angle_plan = build_vector_tool_plan(
            "angle",
            (first, second),
            point_map,
            window._current_2d_bounds(),
            "la_tool_angle_test",
        )
        assert angle_plan is not None
        for operation in angle_plan.operations:
            window._apply_scene_command(dict(operation))
        angle_label = next(
            item for item in window._pane_scene().annotations
            if item.agent_alias == "la_tool_angle_test_label"
        )

        points[2].x, points[2].y = 2.0, 2.0
        window._pane_scene().geometry_controller.move_point(points[2].id, 2.0, 2.0)
        window._update_vector_additions_for_point(points[2].id)
        angle = window._pane_scene()._agent_teaching_2d["la_tool_angle_test"]
        self.assertEqual(angle["second"], [2.0, 2.0])
        self.assertEqual(angle_label.text, "θ=18.4°")

    def test_vector_addition_keeps_dashed_copy_and_refreshes_live_tools(self) -> None:
        from ui.linear_algebra_tools import build_vector_tool_plan

        for tool in ("angle", "projection"):
            window = _make_window()
            points = [
                Point2D("O", 0, 0),
                Point2D("A", 3, 0),
                Point2D("B", 0, 0),
                Point2D("C", 0, 4),
            ]
            window._pane_scene().geometry_points = points
            for point in points:
                window._pane_scene().geometry_controller.add_point(point)
            first = window._create_linear_geometry("vector", points[0], points[1])
            second = window._create_linear_geometry("vector", points[2], points[3])

            plan = build_vector_tool_plan(
                tool,
                (first, second),
                {point.id: point for point in points},
                window._current_2d_bounds(),
                f"la_tool_{tool}_addition",
            )
            assert plan is not None
            for operation in plan.operations:
                window._apply_scene_command(dict(operation))

            self.assertTrue(window._create_vector_addition_relation(first, second))
            relation = window._pane_scene()._vector_additions[-1]
            translated = window._geometry_linear_ref(relation["translated_vector"])
            assert translated is not None
            self.assertEqual(translated.style, "dashed")
            self.assertTrue(translated.visible)
            actor_name = window._pane_scene().geometry_controller.linear_actor_name(translated.id)
            self.assertTrue(window._pane_renderer().actors[actor_name].visibility)

            result = window._geometry_linear_ref(relation["result_vector"])
            assert result is not None
            result_end = window._geometry_point_ref(result.end_point_id)
            assert result_end is not None
            window._move_addition_point(result_end, (4, 4))
            window._update_vector_additions_for_point(result_end.id)

            live_operation = window._pane_scene()._agent_teaching_2d[f"la_tool_{tool}_addition"]
            self.assertEqual(live_operation["second" if tool == "angle" else "direction"], [1.0, 4.0])

    def test_midpoint_tool_creates_and_attaches_live_points(self) -> None:
        window = _make_window()
        points = [
            Point2D("A", -4, 0),
            Point2D("B", 4, 0),
            Point2D("P", 0, 6),
        ]
        window._pane_scene().geometry_points = points
        for point in points:
            window._pane_scene().geometry_controller.add_point(point)
        segment = window._create_linear_geometry("segment", points[0], points[1])

        self.assertTrue(window._handle_midpoint_tool_click(0, 0))
        midpoint = next(
            point for point in window._pane_scene().geometry_points
            if point.constraint_kind == "midpoint" and point.id != points[2].id
        )
        self.assertEqual((midpoint.x, midpoint.y), (0.0, 0.0))
        self.assertEqual(midpoint.constraint_refs, (segment.id,))
        self.assertTrue(midpoint.constraint_owned)

        self.assertTrue(window._handle_midpoint_tool_click(points[2].x, points[2].y))
        self.assertEqual(window._pane_scene()._pending_point_tool_point_id, points[2].id)
        self.assertTrue(window._handle_midpoint_tool_click(2, 0))
        self.assertEqual((points[2].x, points[2].y), (0.0, 0.0))
        self.assertEqual(points[2].constraint_refs, (segment.id,))
        self.assertFalse(points[2].constraint_owned)

        window._move_addition_point(points[1], (8, 4))
        window._update_vector_additions_for_point(points[1].id)
        self.assertEqual((midpoint.x, midpoint.y), (2.0, 2.0))
        self.assertEqual((points[2].x, points[2].y), (2.0, 2.0))

        window._remove_geometry_object(segment.id)
        self.assertIsNone(window._point_2d(midpoint.id))
        self.assertIsNotNone(window._point_2d(points[2].id))
        self.assertIsNone(points[2].constraint_kind)

    def test_intersection_tool_supports_direct_and_two_object_selection(self) -> None:
        window = _make_window()
        points = [
            Point2D("A", -4, 0),
            Point2D("B", 4, 0),
            Point2D("C", 0, -4),
            Point2D("D", 0, 4),
        ]
        window._pane_scene().geometry_points = points
        for point in points:
            window._pane_scene().geometry_controller.add_point(point)
        horizontal = window._create_linear_geometry("segment", points[0], points[1])
        vertical = window._create_linear_geometry("segment", points[2], points[3])

        self.assertTrue(window._handle_intersection_tool_click(0, 0))
        intersection = next(
            point for point in window._pane_scene().geometry_points
            if point.constraint_kind == "intersection"
        )
        self.assertEqual((intersection.x, intersection.y), (0.0, 0.0))
        self.assertEqual(set(intersection.constraint_refs), {horizontal.id, vertical.id})

        window._move_addition_point(points[2], (2, -4))
        window._move_addition_point(points[3], (2, 4))
        window._update_vector_additions_for_point(points[3].id)
        self.assertEqual((intersection.x, intersection.y), (2.0, 0.0))

        intersection.constraint_kind = None
        intersection.constraint_refs = ()
        self.assertTrue(window._handle_intersection_tool_click(-3.5, 0))
        self.assertEqual(window._pane_scene()._pending_point_tool_linear_id, horizontal.id)
        self.assertTrue(window._handle_intersection_tool_click(2, -3.5))
        constrained = [
            point for point in window._pane_scene().geometry_points
            if point.constraint_kind == "intersection"
        ]
        self.assertEqual(len(constrained), 1)
        self.assertEqual((constrained[0].x, constrained[0].y), (2.0, 0.0))

    def test_linear_algebra_polygon_finishes_on_double_click(self) -> None:
        window = _make_window()
        window._pane_scene()._active_linear_algebra_tool = "polygon"

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
        self.assertEqual(window._pane_scene()._linear_algebra_polygon_point_ids, [])

    def test_linear_algebra_polygon_can_close_by_clicking_its_first_point(self) -> None:
        window = _make_window()
        window._pane_scene()._active_linear_algebra_tool = "polygon"
        for coordinates in ((-4, 0), (0, 4), (4, 0)):
            window._handle_linear_algebra_polygon_click(*coordinates)

        self.assertTrue(window._handle_linear_algebra_polygon_click(-4, 0))

        plan = window.scene_command_service.execute.call_args.args[0]
        self.assertEqual(plan.operations[0]["op"], "geometry.polygon")
        self.assertEqual(window._pane_scene()._linear_algebra_polygon_point_ids, [])

    def test_linear_algebra_transform_draws_one_grid_in_the_current_pane(self) -> None:
        window = _make_window()
        pane_id = window.pane_manager.active_pane_id
        window._render_2d_scene = MagicMock()
        window._apply_matrix_transform_from_tab(
            pane_id,
            r"A=\begin{pmatrix}1&0\\0&2\end{pmatrix}",
            5,
        )

        plan = window.scene_command_service.execute.call_args.args[0]
        self.assertEqual(
            [operation["op"] for operation in plan.operations],
            ["geometry.transformed_grid"],
        )
        self.assertEqual(plan.operations[0]["bounds"], [-5.0, 5.0, -5.0, 5.0])
        self.assertFalse(plan.operations[0]["show_source_grid"])

    def test_matrix_transform_settings_can_delete_the_current_grid(self) -> None:
        window = _make_window()
        pane_id = window.pane_manager.active_pane_id
        window._render_2d_scene = MagicMock()
        window._sync_pane_state = MagicMock()
        window._pane_scene()._agent_teaching_2d["la_tool_transform_grid"] = {
            "op": "geometry.transformed_grid",
            "alias": "la_tool_transform_grid",
            "matrix": [[2.0, 1.0], [1.0, 2.0]],
            "bounds": [-8.0, 8.0, -8.0, 8.0],
        }
        window._pane_scene().geometry_controller.add_teaching_transformed_grid(
            ((2.0, 1.0), (1.0, 2.0)),
            (-8.0, 8.0, -8.0, 8.0),
            alias="la_tool_transform_grid",
        )

        window._delete_matrix_transform_grid(pane_id)

        self.assertNotIn(
            "la_tool_transform_grid",
            window._pane_scene()._agent_teaching_2d,
        )
        self.assertEqual(window._pane_scene()._matrix_transform_grid_range, 5.0)
        self.assertTrue(window._pane().scene_2d["matrix_transform_grid_deleted"])
        self.assertEqual(window.algebra_panel.removed_matrix_panes, [pane_id])

    def test_matrix_transform_multiplies_standard_latex_chain_before_dispatch(self) -> None:
        window = _make_window()
        pane_id = window.pane_manager.active_pane_id
        window._render_2d_scene = MagicMock()
        editor = MagicMock()
        window.algebra_panel.matrix_transform_editor = MagicMock(return_value=editor)

        window._apply_matrix_transform_from_tab(
            pane_id,
            r"A=\begin{pmatrix}1&2\\0&1\end{pmatrix}"
            r"\cdot\begin{pmatrix}2&0\\0&3\end{pmatrix}",
            5,
        )

        plan = window.scene_command_service.execute.call_args.args[0]
        self.assertEqual(plan.operations[0]["matrix"], [[2.0, 6.0], [0.0, 3.0]])
        editor.set_matrix_transform_value.assert_called_once_with(
            r"A=\begin{pmatrix}1&2\\0&1\end{pmatrix}"
            r"\cdot\begin{pmatrix}2&0\\0&3\end{pmatrix}",
            r"\begin{pmatrix}2&6\\0&3\end{pmatrix}",
        )

    def test_matrix_transform_recomputes_after_an_operand_is_edited(self) -> None:
        window = _make_window()
        pane_id = window.pane_manager.active_pane_id
        window._render_2d_scene = MagicMock()
        editor = MagicMock()
        window.algebra_panel.matrix_transform_editor = MagicMock(return_value=editor)

        window._apply_matrix_transform_from_tab(
            pane_id,
            r"A=\begin{pmatrix}1&2\\0&1\end{pmatrix}"
            r"\cdot\begin{pmatrix}2&0\\0&3\end{pmatrix}"
            r"=\begin{pmatrix}2&6\\0&3\end{pmatrix}",
            5,
        )
        window._apply_matrix_transform_from_tab(
            pane_id,
            r"A=\begin{pmatrix}2&2\\0&1\end{pmatrix}"
            r"\cdot\begin{pmatrix}2&0\\0&3\end{pmatrix}"
            r"=\begin{pmatrix}2&6\\0&3\end{pmatrix}",
            5,
        )

        latest_plan = window.scene_command_service.execute.call_args.args[0]
        self.assertEqual(latest_plan.operations[0]["matrix"], [[4.0, 6.0], [0.0, 3.0]])
        editor.set_matrix_transform_value.assert_called_with(
            r"A=\begin{pmatrix}2&2\\0&1\end{pmatrix}"
            r"\cdot\begin{pmatrix}2&0\\0&3\end{pmatrix}",
            r"\begin{pmatrix}4&6\\0&3\end{pmatrix}",
        )

    def test_invalid_matrix_expression_does_not_dispatch_or_change_scene(self) -> None:
        window = _make_window()
        pane_id = window.pane_manager.active_pane_id

        window._apply_matrix_transform_from_tab(
            pane_id,
            r"A=\begin{pmatrix}1&0\\0&1\end{pmatrix}"
            r"\times\begin{pmatrix}1&0\\0&1\end{pmatrix}",
            5,
        )

        window.scene_command_service.execute.assert_not_called()
        self.assertTrue(window.algebra_panel.statuses[-1][1])

    def test_escape_cancels_linear_algebra_tool(self) -> None:
        window = _make_window()
        window._pane_scene()._active_linear_algebra_tool = "area"
        window._pane_scene()._linear_algebra_pending_vector_ids = ["v"]
        event = FakeKeyEvent()

        self.assertTrue(window._handle_geometry_key_press(event))
        self.assertTrue(event.accepted)
        self.assertIsNone(window._pane_scene()._active_linear_algebra_tool)
        self.assertIsNone(window._pane_scene()._active_2d_tool)
        self.assertEqual(window._pane_scene()._linear_algebra_pending_vector_ids, [])


if __name__ == "__main__":
    unittest.main()
