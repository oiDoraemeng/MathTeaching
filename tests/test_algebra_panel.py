"""Qt regression tests for the compact algebra-layer workflow."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

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

    def test_compact_row_has_only_visibility_formula_and_settings_actions(self) -> None:
        layer = SurfaceLayer("sphere", "implicit", "x^2+y^2+z^2=1", latex=r"x^2+y^2+z^2=1")
        panel = AlgebraPanel()
        panel.set_layers([layer])
        row = panel.rows[layer.id]

        self.assertEqual(row.minimumHeight(), 40)
        self.assertTrue(hasattr(row, "visible_button"))
        self.assertTrue(hasattr(row, "expression_button"))
        self.assertTrue(hasattr(row, "settings_button"))
        self.assertFalse(hasattr(row, "opacity_slider"))
        self.assertFalse(hasattr(row, "range_slider"))

    def test_formula_submission_updates_only_the_selected_layer(self) -> None:
        layer = SurfaceLayer("sphere", "implicit", "x^2+y^2+z^2=1", latex=r"x^2+y^2+z^2=1")
        panel = AlgebraPanel()
        updates: list[tuple[str, str, str]] = []
        panel.update_requested.connect(lambda layer_id, kind, formula: updates.append((layer_id, kind, formula)))
        panel.set_layers([layer])

        panel._active_layer_id = layer.id
        panel._submit_formula("implicit", r"x^2+y^2+z^2=r^2")

        self.assertEqual(updates, [(layer.id, "implicit", r"x^2+y^2+z^2=r^2")])

    def test_each_row_exposes_independent_surface_and_intersection_toggles(self) -> None:
        layer = SurfaceLayer("sphere", "implicit", "x^2+y^2+z^2=1")
        panel = AlgebraPanel()
        visibility_events: list[tuple[str, bool]] = []
        intersection_events: list[tuple[str, bool]] = []
        panel.visibility_changed.connect(lambda layer_id, visible: visibility_events.append((layer_id, visible)))
        panel.intersections_visibility_changed.connect(
            lambda layer_id, visible: intersection_events.append((layer_id, visible))
        )
        panel.set_layers([layer])
        row = panel.rows[layer.id]

        row.visible_button.click()
        panel.settings_popup.open_layer(layer, None)
        panel.settings_popup.intersections_check.setChecked(False)

        self.assertEqual(visibility_events, [(layer.id, False)])
        self.assertEqual(intersection_events, [(layer.id, False)])

    def test_advanced_lighting_button_requests_the_existing_lighting_editor(self) -> None:
        panel = AlgebraPanel()
        events: list[bool] = []
        panel.lighting_requested.connect(lambda: events.append(True))

        panel.lighting_button.click()

        self.assertEqual(events, [True])

    def test_layer_settings_popup_emits_range_only_when_slider_is_released(self) -> None:
        layer = SurfaceLayer("plane", "explicit", "z = x + y")
        panel = AlgebraPanel()
        events: list[tuple[str, float]] = []
        panel.range_changed.connect(lambda layer_id, scale: events.append((layer_id, scale)))
        panel.set_layers([layer])
        panel.settings_popup.open_layer(layer, None)
        panel.settings_popup.range_slider.setValue(35)

        self.assertEqual(events, [])
        panel.settings_popup.range_slider.sliderReleased.emit()

        self.assertEqual(events, [(layer.id, 3.5)])

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

        panel._open_formula_for_layer(layer.id, layer.kind, layer.latex or layer.expression, None)
        panel._open_settings(layer.id, None)

        self.assertFalse(panel.formula_popup.isVisible())
        self.assertTrue(panel.settings_popup.isVisible())
        self.assertIsNone(panel._active_layer_id)


if __name__ == "__main__":
    unittest.main()
