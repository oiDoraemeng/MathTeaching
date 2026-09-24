"""单 WebEngine 代数图层工作流的 Qt 回归测试。"""

import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent
from PySide6.QtGui import QFocusEvent
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QWidget
from PySide6.QtWebEngineWidgets import QWebEngineView

from MathInputWidget import FormulaListWidget, FormulaPreviewWidget
from models.function_catalog import CatalogEntry
from models.curve_layer import CurveLayer
from models.scene_mode import SceneMode
from models.geometry_2d import Annotation2D, Linear2D, Point2D
from models.surface_layer import SurfaceLayer
from ui.algebra_panel import AlgebraPanel, FormulaDraft
from ui.scene_pane_manager import ScenePaneManager
from ui.scene_pane_widget import ScenePaneWidget
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

    def test_new_formula_action_is_labeled_add(self) -> None:
        panel = AlgebraPanel()

        self.assertEqual(panel.new_formula_button.text(), "新增")

    def test_function_catalog_is_removed_from_the_algebra_toolbar(self) -> None:
        panel = AlgebraPanel()

        self.assertFalse(panel.function_catalog_button.isVisibleTo(panel))

    def test_viewport_toolbar_can_open_the_function_catalog(self) -> None:
        panel = AlgebraPanel()

        panel.open_function_catalog()

        self.assertTrue(panel.catalog_popup.isVisible())

    def test_new_formula_action_inserts_an_inline_draft_without_a_popup(self) -> None:
        panel = AlgebraPanel()

        panel._open_new_formula()

        drafts = [layer for layer in panel._layers if isinstance(layer, FormulaDraft)]
        self.assertEqual(len(drafts), 1)
        self.assertIn(drafts[0].id, panel.formula_list._layers)
        self.assertEqual(panel._inline_active_layer_id, drafts[0].id)
        self.assertFalse(panel.formula_popup.isVisible())

    def test_inline_draft_submits_through_the_existing_add_signal(self) -> None:
        panel = AlgebraPanel()
        events: list[tuple[str, str]] = []
        panel.add_requested.connect(lambda kind, expression: events.append((kind, expression)))
        panel._open_new_formula()
        draft = next(layer for layer in panel._layers if isinstance(layer, FormulaDraft))

        panel._submit_inline_formula_from_model(panel.formula_list, draft.id, r"y=x^2")

        self.assertEqual(events, [("explicit", r"y=x^2")])

    def test_cancelling_an_inline_draft_removes_its_row(self) -> None:
        panel = AlgebraPanel()
        panel._open_new_formula()
        draft = next(layer for layer in panel._layers if isinstance(layer, FormulaDraft))

        panel._cancel_inline_formula_edit(draft.id)

        self.assertNotIn(draft.id, panel.formula_list._layers)
        self.assertFalse(any(isinstance(layer, FormulaDraft) for layer in panel._layers))

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

    def test_restore_render_surface_reloads_active_formula_page(self) -> None:
        panel = AlgebraPanel()
        model = panel.formula_list
        model._page_ready = True
        model._active_layer_id = "layer-1"
        model.web_view.reload = MagicMock()

        panel.restore_render_surface()

        self.assertFalse(model._page_ready)
        self.assertEqual(model._pending_edit_id, "layer-1")
        model.web_view.reload.assert_called_once_with()

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
        panel.pane_visibility_requested.connect(lambda _pane_id, count: requested.append(count))
        panel.set_pane_id("pane-2")
        manager.set_layout(1)
        panel.formula_tabs.setCurrentIndex(0)
        panel.formula_tabs.setCurrentIndex(1)
        self.assertEqual(requested, [1])
        self.assertIn("pane-2", manager.visible_pane_ids())
        self.assertEqual(manager.active_pane_id, "pane-2")

    def test_closing_scene_pane_removes_its_algebra_tab(self) -> None:
        panel = AlgebraPanel()
        manager = ScenePaneManager()
        manager.set_layout(2)
        panel.set_pane_manager(manager)
        panel.set_pane_id("pane-2", "窗格 2")

        manager.delete_pane("pane-2")

        self.assertEqual(list(panel._pane_models), ["pane-1"])
        self.assertEqual(panel.formula_tabs.count(), 1)

    def test_retained_pane_limit_keeps_algebra_tabs_bounded_and_evicts_case_tab(self) -> None:
        panel = AlgebraPanel()
        manager = ScenePaneManager()
        panel.set_pane_manager(manager)
        panel.set_pane_id(manager.active_pane_id)
        for _ in range(7):
            pane_id = manager.create_pane()
            panel.set_pane_id(pane_id)
        case_ids = []
        for index in range(2):
            pane_id = manager.register_case(f"case-{index}")
            case_ids.append(pane_id)
            panel.set_pane_id(pane_id)

        replacement = manager.create_pane()
        panel.set_pane_id(replacement)

        self.assertEqual(len(manager.panes), manager.MAX_RETAINED_PANES)
        self.assertEqual(panel.formula_tabs.count(), manager.MAX_RETAINED_PANES)
        self.assertNotIn(case_ids[0], panel._pane_models)
        self.assertIn(case_ids[1], panel._pane_models)

    def test_closing_algebra_tab_removes_scene_pane(self) -> None:
        panel = AlgebraPanel()
        manager = ScenePaneManager()
        manager.set_layout(2)
        panel.set_pane_manager(manager)
        panel.set_pane_id("pane-2", "窗格 2")

        panel._close_tab(1)

        self.assertNotIn("pane-2", manager.panes)
        self.assertEqual(manager.visible_pane_ids(), ("pane-1",))
        self.assertEqual(list(panel._pane_models), ["pane-1"])

    def test_hidden_tab_reveal_uses_scene_order_after_out_of_order_visits(self) -> None:
        from ui.designer_window import MainWindow

        panel = AlgebraPanel()
        manager = ScenePaneManager()
        container = ScenePaneWidget(manager, interactor_factory=QWidget)
        window = MainWindow.__new__(MainWindow)
        window.scene_pane_widget = container
        first, second, third = container.set_layout(3)
        panel.set_pane_manager(manager)
        requested: list[tuple[str, int]] = []
        panel.pane_visibility_requested.connect(lambda pane_id, count: requested.append((pane_id, count)))
        panel.pane_visibility_requested.connect(window._reveal_algebra_pane)
        panel.set_pane_id(third)
        panel.set_pane_id(second)
        self.assertEqual(list(panel._pane_models), [first, third, second])
        container.set_layout(1)
        panel.set_pane_id(first)
        self.assertIsNone(container.interactor(third))

        panel.formula_tabs.setCurrentIndex(1)

        self.assertEqual(requested, [(third, 1)])
        self.assertEqual(manager.visible_pane_ids(), (third,))
        self.assertIsNotNone(container.interactor(third))
        self.assertEqual(manager.active_pane_id, third)
        self.assertEqual(panel._pane_id, third)
        container.close()

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
        self.assertIn("bridge.keyboardRequested", html)
        self.assertIn("applyExternalEdit", html)

    def test_floating_keyboard_edits_are_applied_to_the_visible_list_field(self) -> None:
        widget = FormulaListWidget()
        widget._active_layer_id = "draft-1"
        widget._page_ready = True
        widget._run_javascript = MagicMock()

        widget.apply_external_edit(r"y=x^2", 5)

        script = widget._run_javascript.call_args.args[0]
        self.assertIn("applyExternalEdit", script)
        self.assertIn(r"y=x^2", script)
        self.assertIn(", 5);", script)

    def test_formula_focus_can_move_to_the_floating_keyboard_without_finishing_edit(self) -> None:
        layer = SurfaceLayer("plane", "explicit", "z=x+y", latex=r"z=x+y")
        widget = FormulaListWidget()
        widget._layers = {layer.id: layer}
        widget._active_layer_id = layer.id
        widget.commit_active_mark = MagicMock()

        widget.eventFilter(widget.web_view, QFocusEvent(QEvent.Type.FocusOut))

        widget.commit_active_mark.assert_not_called()

    def test_focus_leaving_formula_list_finishes_the_edit(self) -> None:
        widget = FormulaListWidget()
        widget._active_layer_id = "draft-1"
        widget._page_ready = True
        widget._run_javascript = MagicMock()

        widget.finish_edit_on_focus_out()

        self.assertIsNone(widget._active_layer_id)
        widget._run_javascript.assert_called_once_with(
            "if (window.formulaListReady) window.formulaList.finishEditOnFocusOut();"
        )

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

    def test_linear_algebra_button_opens_catalog_before_announcing_workspace(self) -> None:
        panel = AlgebraPanel()
        events: list[tuple[str, bool]] = []
        panel.linear_algebra_opened.connect(
            lambda: events.append(("opened", panel.linear_algebra_popup.isVisible()))
        )

        panel.linear_algebra_button.click()

        self.assertTrue(panel.linear_algebra_popup.isVisible())
        self.assertEqual(events, [])
        QApplication.processEvents()
        self.assertEqual(events, [("opened", True)])

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

    def test_parameter_sliders_use_the_shared_numeric_range_and_update_live(self) -> None:
        layer = CurveLayer(
            "line",
            "explicit",
            "y = a*x + b",
            parameters={"a": 1.0, "b": 0.0},
            latex="y=x",
        )
        panel = AlgebraPanel()
        events: list[tuple[str, str, float]] = []
        panel.parameter_changed.connect(lambda *event: events.append(event))

        panel.settings_popup.open_layer(layer, None)
        slider, value_label = panel.settings_popup._parameter_rows["b"]
        slider.setValue(10)

        self.assertEqual((slider.minimum(), slider.maximum(), slider.singleStep()), (-100, 100, 1))
        self.assertEqual(value_label.text(), "1")
        self.assertEqual(events, [(layer.id, "b", 1.0)])

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
        self.assertEqual(segment_payload["latex"], "s_1")
        self.assertNotIn("?", segment_payload["latex"])

    def test_unnamed_geometry_helpers_do_not_create_blank_algebra_rows(self) -> None:
        helper_point = Point2D("", 0.0, 0.0)
        named_point = Point2D("A", 1.0, 2.0)
        helper_segment = Linear2D("", "segment", helper_point.id, "missing")
        panel = AlgebraPanel()

        panel.set_layers([helper_point, named_point, helper_segment])

        self.assertNotIn(helper_point.id, panel.formula_list._layers)
        self.assertNotIn(helper_segment.id, panel.formula_list._layers)
        self.assertIn(named_point.id, panel.formula_list._layers)

    def test_user_annotation_rows_commit_and_close_immediately(self) -> None:
        annotation = Annotation2D("标记 1", "标记", 1.0, 2.0, latex="标记", editable=True)
        panel = AlgebraPanel()
        panel.set_layers([annotation])

        payload = panel.formula_list._serialize_layer(annotation)
        assert payload["editable"] is True
        assert payload["commitImmediately"] is True

        html = Path(__file__).parents[1] / "MathInputWidget" / "formula_list.html"
        source = html.read_text(encoding="utf-8")
        assert "if (active.commitImmediately)" in source
        assert "finishEdit(false);" in source
        assert "commitActiveMark" in source

    def test_scene_click_commits_the_active_annotation_row(self) -> None:
        annotation = Annotation2D("标记 1", "标记", 1.0, 2.0, latex="标记", editable=True)
        panel = AlgebraPanel()
        panel.set_layers([annotation])
        panel._inline_active_layer_id = annotation.id
        panel.formula_list.commit_active_mark = MagicMock()

        panel.commit_annotation_edit()

        panel.formula_list.commit_active_mark.assert_called_once_with()
        self.assertIsNone(panel._inline_active_layer_id)

    def test_formula_list_forwards_mark_commit_to_the_web_page(self) -> None:
        widget = FormulaListWidget()
        widget._run_javascript = MagicMock()

        widget.commit_active_mark()

        widget._run_javascript.assert_called_once_with(
            "if (window.formulaListReady) window.formulaList.commitActiveMark();"
        )

    def test_matrix_transform_uses_one_standard_matrix_row_with_ellipsis_settings(self) -> None:
        html = Path(__file__).parents[1] / "MathInputWidget" / "formula_list.html"
        source = html.read_text(encoding="utf-8")

        self.assertIn("layer-row matrix-transform-editor", source)
        self.assertIn(r"\\begin{pmatrix}1&0\\\\0&1\\end{pmatrix}", source)
        self.assertIn("matrix-transform-input", source)
        self.assertIn("matrix-transform-result", source)
        self.assertIn("setReadOnly(result, true)", source)
        self.assertIn("bridge.matrixSettingsRequested", source)
        self.assertNotIn("matrix-transform-grid", source)
        self.assertNotIn("matrix-transform-range", source)

    def test_matrix_transform_keeps_the_product_separate_from_editable_factors(self) -> None:
        widget = FormulaListWidget()
        widget._page_ready = True
        widget._run_javascript = MagicMock()

        widget.set_matrix_transform_value(
            r"A=\begin{pmatrix}1&2\\0&1\end{pmatrix}"
            r"\cdot\begin{pmatrix}2&0\\0&3\end{pmatrix}",
            r"\begin{pmatrix}2&6\\0&3\end{pmatrix}",
        )

        self.assertNotIn("=\\begin{pmatrix}2&6", widget._matrix_transform_text)
        self.assertEqual(
            widget._matrix_transform_result,
            r"\begin{pmatrix}2&6\\0&3\end{pmatrix}",
        )
        script = widget._run_javascript.call_args.args[0]
        self.assertIn("setMatrixTransformValue", script)
        self.assertIn(r"\\begin{pmatrix}2&6\\\\0&3\\end{pmatrix}", script)

    def test_matrix_transform_row_can_be_display_only_for_teaching_cases(self) -> None:
        widget = FormulaListWidget()
        widget._page_ready = True
        widget._run_javascript = MagicMock()

        widget.set_matrix_transform_editor(True, editable=False)

        scripts = [call.args[0] for call in widget._run_javascript.call_args_list]
        self.assertTrue(widget._matrix_transform_enabled)
        self.assertFalse(widget._matrix_transform_editable)
        self.assertTrue(any("setMatrixTransformEditable(false)" in script for script in scripts))
        html = Path(__file__).parents[1] / "MathInputWidget" / "formula_list.html"
        source = html.read_text(encoding="utf-8")
        self.assertIn("if (!matrixTransformEditable", source)
        self.assertNotIn("settings.hidden = !matrixTransformEditable", source)
        self.assertIn("bridge.matrixSettingsRequested", source)

    def test_matrix_ellipsis_settings_reapply_current_matrix_with_new_grid_size(self) -> None:
        panel = AlgebraPanel()
        model = panel.add_matrix_transform_tab("pane-1")
        events: list[tuple[str, str, int]] = []
        panel.matrix_transform_settings_requested.connect(
            lambda pane_id, text, size: events.append((pane_id, text, size))
        )

        model.matrix_settings_requested.emit(None)
        panel.matrix_settings_popup.grid_size_spin.setValue(8)

        self.assertTrue(panel.matrix_settings_popup.isVisible())
        self.assertEqual(events, [("pane-1", model._matrix_transform_text, 8)])

    def test_matrix_settings_can_request_grid_deletion_and_remove_the_row(self) -> None:
        panel = AlgebraPanel()
        model = panel.add_matrix_transform_tab("pane-1")
        deleted: list[str] = []
        panel.matrix_transform_delete_requested.connect(deleted.append)

        model.matrix_settings_requested.emit(None)
        panel.matrix_settings_popup.delete_button.click()

        self.assertEqual(deleted, ["pane-1"])
        panel.remove_matrix_transform_tab("pane-1")
        self.assertIsNone(panel.matrix_transform_editor("pane-1"))
        self.assertFalse(model._matrix_transform_enabled)
        self.assertEqual(
            model._matrix_transform_text,
            r"A=\begin{pmatrix}1&0\\0&1\end{pmatrix}",
        )
        self.assertEqual(model.matrix_transform_grid_range(), 5)

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
