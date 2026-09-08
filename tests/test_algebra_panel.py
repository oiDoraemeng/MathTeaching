"""单 WebEngine 代数图层工作流的 Qt 回归测试。"""

import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QFrame, QLabel
from PySide6.QtWebEngineWidgets import QWebEngineView

from MathInputWidget import FormulaListWidget, FormulaPreviewWidget
from models.function_catalog import CatalogEntry
from models.scene_mode import SceneMode
from models.geometry_2d import Linear2D, Point2D
from models.surface_layer import SurfaceLayer
from ui.algebra_panel import AlgebraPanel
from ui.scene_pane_manager import ScenePaneManager
from ui.tokens import build_qss


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

    def test_catalog_previews_inherit_the_effective_theme_when_created_later(self) -> None:
        panel = AlgebraPanel()
        panel.sync_overlay_theme("dark")
        panel.set_catalog_entries([CatalogEntry("f", "测试", "f", "explicit", "y=x", "y=x", {}, "#123456", SceneMode.TWO_D)])
        previews = panel.catalog_popup.findChildren(FormulaPreviewWidget)
        self.assertTrue(previews)
        self.assertEqual(previews[0]._theme, "dark")

    def test_function_list_uses_one_webengine_for_all_layers(self) -> None:
        first = SurfaceLayer("sphere", "implicit", "x^2+y^2+z^2=1", latex=r"x^2+y^2+z^2=1")
        second = SurfaceLayer("plane", "explicit", "z=x+y", latex=r"z=x+y")
        panel = AlgebraPanel()

        panel.set_layers([first, second])

        self.assertIsInstance(panel.formula_list, FormulaListWidget)
        self.assertEqual(len(panel.formula_list.findChildren(QWebEngineView)), 1)
        self.assertEqual(list(panel.formula_list._layers), [first.id, second.id])

    def test_switching_tabs_commits_previous_formula_and_focuses_manager(self) -> None:
        class Manager:
            active_pane_id = "pane-1"
            def __init__(self): self.focused = []
            def focus_pane(self, pane_id): self.focused.append(pane_id)
            def pane(self, pane_id): return type("Pane", (), {"name": pane_id})()
        panel = AlgebraPanel()
        manager = Manager(); panel.set_pane_manager(manager)
        panel.set_pane_id("pane-2", "窗格 2")
        manager.focused.clear()
        first = panel._pane_models["pane-1"]
        first._active_layer_id = "layer-1"
        called = []
        first.accept_edit = lambda: called.append(True)
        panel.formula_tabs.setCurrentIndex(0)
        manager.focused.clear()
        panel.formula_tabs.setCurrentIndex(1)
        self.assertEqual(called, [True])
        self.assertEqual(manager.focused, ["pane-2"])

    def test_theme_sync_updates_every_retained_pane_model(self) -> None:
        panel = AlgebraPanel()
        panel.set_pane_id("pane-2")
        panel.sync_overlay_theme("dark")
        self.assertTrue(all(model._theme_bridge._pending_theme == "dark" for model in panel._pane_models.values()))

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

    def test_late_formula_submission_stays_bound_to_originating_pane(self) -> None:
        first = SurfaceLayer("first", "implicit", "x=1")
        second = SurfaceLayer("second", "explicit", "y=x")
        panel = AlgebraPanel()
        panel.set_layers([first])
        panel.set_pane_id("pane-2")
        panel.set_layers([second])
        updates: list[tuple[str, str, str]] = []
        panel.update_requested.connect(lambda *event: updates.append(event))
        panel.set_pane_id("pane-1")
        panel.set_pane_id("pane-2")
        panel._pane_models["pane-1"]._bridge.formula_submitted.emit(first.id, "x=2")
        self.assertEqual(updates, [(first.id, "implicit", "x=2")])

    def test_selecting_retained_hidden_tab_reveals_and_focuses_manager(self) -> None:
        panel = AlgebraPanel()
        manager = ScenePaneManager()
        manager.set_layout(2)
        panel.set_pane_manager(manager)
        requested: list[int] = []
        panel.pane_visibility_requested.connect(lambda _pane_id, count: (requested.append(count), manager.set_layout(count)))
        panel.set_pane_id("pane-2")
        manager.set_layout(1)
        panel.formula_tabs.setCurrentIndex(0)
        panel.formula_tabs.setCurrentIndex(1)
        self.assertEqual(requested, [2])
        self.assertIn("pane-2", manager.visible_pane_ids())
        self.assertEqual(manager.active_pane_id, "pane-2")

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

    def test_linear_algebra_button_emits_selected_topic_id(self) -> None:
        panel = AlgebraPanel()
        events: list[str] = []
        panel.linear_algebra_requested.connect(events.append)

        topic = panel.linear_algebra_popup.tree.topLevelItem(0).child(0).child(0)
        panel.linear_algebra_popup.activate_item(topic)

        self.assertEqual(events, ["ch01.vector.magnitude"])
        self.assertEqual(panel.linear_algebra_button.text(), "线性代数")

    def test_linear_algebra_button_announces_workspace_before_opening_catalog(self) -> None:
        panel = AlgebraPanel()
        events: list[tuple[str, bool]] = []
        panel.linear_algebra_opened.connect(
            lambda: events.append(("opened", panel.linear_algebra_popup.isVisible()))
        )

        panel.linear_algebra_button.click()

        self.assertEqual(events, [("opened", False)])
        self.assertTrue(panel.linear_algebra_popup.isVisible())

    def test_linear_algebra_button_toggles_popup_without_reopen_race(self) -> None:
        panel = AlgebraPanel()
        panel.linear_algebra_button.click()
        self.assertTrue(panel.linear_algebra_popup.isVisible())
        panel.linear_algebra_button.click()
        QApplication.processEvents()
        self.assertTrue(panel.linear_algebra_popup.isVisible())

    def test_scene_mode_and_other_catalog_do_not_force_close_linear_algebra_popup(self) -> None:
        panel = AlgebraPanel()
        panel.linear_algebra_button.click()
        self.assertTrue(panel.linear_algebra_popup.isVisible())

        panel.set_scene_mode(SceneMode.TWO_D)
        self.assertTrue(panel.linear_algebra_popup.isVisible())
        panel._open_catalog()
        self.assertTrue(panel.linear_algebra_popup.isVisible())

    def test_linear_algebra_popup_uses_tokenized_tree_surface(self) -> None:
        panel = AlgebraPanel()
        self.assertEqual(panel.linear_algebra_popup.tree.objectName(), "linearAlgebraTree")
        self.assertIn("#linearAlgebraTree", build_qss("light"))

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
