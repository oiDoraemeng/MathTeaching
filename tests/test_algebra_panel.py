"""单 WebEngine 代数图层工作流的 Qt 回归测试。"""

import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView

from MathInputWidget import FormulaListWidget
from models.geometry_2d import Linear2D, Point2D
from models.surface_layer import SurfaceLayer
from ui.algebra_panel import AlgebraPanel


class AlgebraPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def test_formula_editor_submission_requests_an_addition(self) -> None:
        panel = AlgebraPanel()
        events: list[tuple[str, str]] = []
        panel.add_requested.connect(lambda kind, expression: events.append((kind, expression)))

        panel._submit_formula("implicit", r"x^2+y^2+z^2=1")

        self.assertEqual(events, [("implicit", r"x^2+y^2+z^2=1")])

    def test_function_list_uses_one_webengine_for_all_layers(self) -> None:
        first = SurfaceLayer("sphere", "implicit", "x^2+y^2+z^2=1", latex=r"x^2+y^2+z^2=1")
        second = SurfaceLayer("plane", "explicit", "z=x+y", latex=r"z=x+y")
        panel = AlgebraPanel()

        panel.set_layers([first, second])

        self.assertIsInstance(panel.formula_list, FormulaListWidget)
        self.assertEqual(len(panel.formula_list.findChildren(QWebEngineView)), 1)
        self.assertEqual(list(panel.formula_list._layers), [first.id, second.id])

    def test_formula_list_bridge_starts_editing_only_for_the_selected_layer(self) -> None:
        first = SurfaceLayer("sphere", "implicit", "x^2+y^2+z^2=1", latex=r"x^2+y^2+z^2=1")
        second = SurfaceLayer("plane", "explicit", "z=x+y", latex=r"z=x+y")
        panel = AlgebraPanel()
        panel.set_layers([first, second])

        panel.formula_list._bridge.edit_requested.emit(second.id)

        self.assertEqual(panel._inline_active_layer_id, second.id)
        self.assertEqual(set(panel.formula_list._layers), {first.id, second.id})

    def test_formula_submission_updates_only_the_selected_layer(self) -> None:
        layer = SurfaceLayer("sphere", "implicit", "x^2+y^2+z^2=1", latex=r"x^2+y^2+z^2=1")
        panel = AlgebraPanel()
        updates: list[tuple[str, str, str]] = []
        panel.update_requested.connect(
            lambda layer_id, kind, formula: updates.append((layer_id, kind, formula))
        )
        panel.set_layers([layer])

        panel._inline_active_layer_id = layer.id
        panel._submit_inline_formula(layer.id, r"x^2+y^2+z^2=r^2")

        self.assertEqual(updates, [(layer.id, "implicit", r"x^2+y^2+z^2=r^2")])

    def test_formula_list_bridge_submits_the_selected_layer(self) -> None:
        first = SurfaceLayer("sphere", "implicit", "x^2+y^2+z^2=1", latex=r"x^2+y^2+z^2=1")
        second = SurfaceLayer("plane", "explicit", "z=x+y", latex=r"z=x+y")
        panel = AlgebraPanel()
        updates: list[tuple[str, str, str]] = []
        panel.update_requested.connect(
            lambda layer_id, kind, formula: updates.append((layer_id, kind, formula))
        )
        panel.set_layers([first, second])

        panel.formula_list._bridge.formula_submitted.emit(second.id, r"z=2*x+y")

        self.assertEqual(updates, [(second.id, "explicit", r"z=2*x+y")])
        self.assertEqual(panel._inline_active_layer_id, second.id)

    def test_formula_list_visibility_is_scoped_to_the_selected_layer(self) -> None:
        first = SurfaceLayer("sphere", "implicit", "x^2+y^2+z^2=1")
        second = SurfaceLayer("plane", "explicit", "z=x+y")
        panel = AlgebraPanel()
        events: list[tuple[str, bool]] = []
        panel.visibility_changed.connect(lambda layer_id, visible: events.append((layer_id, visible)))
        panel.set_layers([first, second])

        panel.formula_list._bridge.visibility_changed.emit(second.id, False)

        self.assertEqual(events, [(second.id, False)])

    def test_formula_list_html_contains_inline_editor_and_bridge_contract(self) -> None:
        html_path = Path(__file__).parents[1] / "MathInputWidget" / "formula_list.html"
        html = html_path.read_text(encoding="utf-8")

        self.assertIn("qrc:///qtwebchannel/qwebchannel.js", html)
        self.assertIn("window.formulaList", html)
        self.assertIn("bridge.formulaSubmitted", html)
        self.assertIn("bridge.editCancelled", html)
        self.assertIn("setLayers,", html)
        self.assertIn("setReadOnly(field, false)", html)

    def test_advanced_lighting_button_requests_the_existing_lighting_editor(self) -> None:
        panel = AlgebraPanel()
        events: list[bool] = []
        panel.lighting_requested.connect(lambda: events.append(True))

        panel.lighting_button.click()

        self.assertEqual(events, [True])

    def test_linear_algebra_button_emits_selected_case_id(self) -> None:
        panel = AlgebraPanel()
        events: list[str] = []
        panel.linear_algebra_requested.connect(events.append)

        panel.linear_algebra_popup._request("vector-subtraction")

        self.assertEqual(events, ["vector-subtraction"])
        self.assertEqual(panel.linear_algebra_button.text(), "线性代数")

    def test_each_layer_keeps_independent_surface_and_intersection_events(self) -> None:
        layer = SurfaceLayer("sphere", "implicit", "x^2+y^2+z^2=1")
        panel = AlgebraPanel()
        visibility_events: list[tuple[str, bool]] = []
        intersection_events: list[tuple[str, bool]] = []
        panel.visibility_changed.connect(
            lambda layer_id, visible: visibility_events.append((layer_id, visible))
        )
        panel.intersections_visibility_changed.connect(
            lambda layer_id, visible: intersection_events.append((layer_id, visible))
        )
        panel.set_layers([layer])

        panel.formula_list._bridge.visibility_changed.emit(layer.id, False)
        panel.settings_popup.open_layer(layer, None)
        panel.settings_popup.intersections_check.setChecked(False)

        self.assertEqual(visibility_events, [(layer.id, False)])
        self.assertEqual(intersection_events, [(layer.id, False)])

    def test_layer_settings_omits_the_nonfunctional_surface_type_selector(self) -> None:
        panel = AlgebraPanel()

        self.assertFalse(hasattr(panel.settings_popup, "kind_combo"))

    def test_layer_settings_popup_emits_range_only_when_slider_is_released(self) -> None:
        layer = SurfaceLayer("plane", "explicit", "z = x + y")
        panel = AlgebraPanel()
        events: list[tuple[str, float]] = []
        panel.range_changed.connect(lambda layer_id, scale: events.append((layer_id, scale)))
        panel.set_layers([layer])
        panel.settings_popup.open_layer(layer, None)
        panel.settings_popup.range_slider.setValue(50)

        self.assertEqual(events, [])
        panel.settings_popup.range_slider.sliderReleased.emit()

        self.assertEqual(events, [(layer.id, 0.5)])

    def test_surface_settings_expose_a_narrower_sampling_minimum(self) -> None:
        layer = SurfaceLayer("plane", "explicit", "z = x + y")
        panel = AlgebraPanel()

        panel.settings_popup.open_layer(layer, None)

        self.assertEqual(panel.settings_popup.range_slider.minimum(), 10)

    def test_opening_manual_intersection_selection_turns_off_automatic_intersections(self) -> None:
        panel = AlgebraPanel()
        events: list[bool] = []
        panel.auto_intersections_changed.connect(events.append)

        panel._open_manual_intersection_popup()

        self.assertFalse(panel.auto_intersections_action.isChecked())
        self.assertEqual(events, [False])

    def test_opening_settings_dismisses_an_unsubmitted_formula_edit(self) -> None:
        layer = SurfaceLayer("plane", "explicit", "z=x+y", latex=r"z=x+y")
        panel = AlgebraPanel()
        panel.set_layers([layer])
        panel._inline_active_layer_id = layer.id
        panel.formula_list._active_layer_id = layer.id

        panel._open_settings(layer.id, None)

        self.assertTrue(panel.settings_popup.isVisible())
        self.assertIsNone(panel._inline_active_layer_id)

    def test_point_rows_are_editable_but_linear_rows_are_read_only(self) -> None:
        first = Point2D("A", 1.0, 2.0)
        segment = Linear2D("s_1", "segment", first.id, "other_id")
        panel = AlgebraPanel()
        panel.set_layers([first, segment])

        point_payload = panel.formula_list._serialize_layer(first)
        segment_payload = panel.formula_list._serialize_layer(segment)

        self.assertTrue(point_payload["editable"])
        self.assertEqual(point_payload["latex"], "A=(1, 2)")
        self.assertFalse(segment_payload["editable"])
        self.assertIn(r"\overline{", segment_payload["latex"])

    def test_geometry_objects_use_the_geometry_delete_menu(self) -> None:
        first = Point2D("A", 1.0, 2.0)
        segment = Linear2D("s_1", "segment", first.id, "other_id")
        panel = AlgebraPanel()
        removed: list[str] = []
        panel.delete_requested.connect(removed.append)
        panel.set_layers([first, segment])

        panel._open_settings(first.id, None)
        panel.geometry_settings_popup.delete_button.click()

        self.assertEqual(removed, [first.id])


if __name__ == "__main__":
    unittest.main()
