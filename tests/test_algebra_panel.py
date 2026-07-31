"""Qt regression tests for the fixed algebra-layer panel workflow."""

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

    def test_enter_in_new_expression_field_requests_an_addition(self) -> None:
        panel = AlgebraPanel()
        events: list[tuple[str, str]] = []
        panel.add_requested.connect(lambda kind, expression: events.append((kind, expression)))
        panel.kind_combo.setCurrentIndex(1)
        panel.expression_edit.setText("x^2 + y^2 + z^2 = 1")

        panel.expression_edit.returnPressed.emit()

        self.assertEqual(events, [("implicit", "x^2 + y^2 + z^2 = 1")])

    def test_row_editor_submits_a_direct_formula_update_when_enter_is_pressed(self) -> None:
        layer = SurfaceLayer("sphere", "implicit", "x^2+y^2+z^2=1")
        panel = AlgebraPanel()
        updates: list[tuple[str, str, str]] = []
        panel.update_requested.connect(lambda layer_id, kind, expression: updates.append((layer_id, kind, expression)))
        panel.set_layers([layer])
        row = panel.rows[layer.id]
        row.expression_edit.setText("x^2 + y^2 + z^2 = r^2")

        row.expression_edit.returnPressed.emit()

        self.assertEqual(updates, [(layer.id, "implicit", "x^2 + y^2 + z^2 = r^2")])

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

        row.visible_check.setChecked(False)
        row.intersections_check.setChecked(False)

        self.assertEqual(visibility_events, [(layer.id, False)])
        self.assertEqual(intersection_events, [(layer.id, False)])

    def test_advanced_lighting_button_requests_the_existing_lighting_editor(self) -> None:
        panel = AlgebraPanel()
        events: list[bool] = []
        panel.lighting_requested.connect(lambda: events.append(True))

        panel.lighting_button.click()

        self.assertEqual(events, [True])

    def test_layer_range_slider_emits_only_the_selected_layer_scale_when_released(self) -> None:
        layer = SurfaceLayer("plane", "explicit", "z = x + y")
        panel = AlgebraPanel()
        events: list[tuple[str, float]] = []
        panel.range_changed.connect(lambda layer_id, scale: events.append((layer_id, scale)))
        panel.set_layers([layer])
        row = panel.rows[layer.id]
        row.range_slider.setValue(35)

        self.assertEqual(events, [])
        row.range_slider.sliderReleased.emit()

        self.assertEqual(events, [(layer.id, 3.5)])


if __name__ == "__main__":
    unittest.main()
