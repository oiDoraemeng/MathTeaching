"""Qt tests for mode-aware scene setting controls."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from models.scene_mode import SceneMode
from ui.scene_settings import SceneSettingsPanel


class SceneSettingsPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def test_2d_exposes_grid_and_hides_3d_only_controls(self) -> None:
        panel = SceneSettingsPanel()
        panel.set_mode(SceneMode.TWO_D)

        self.assertTrue(panel.grid_check.isVisibleTo(panel))
        self.assertFalse(panel.intersections_check.isVisibleTo(panel))
        self.assertFalse(panel.lighting_button.isVisibleTo(panel))

    def test_3d_exposes_intersections_and_lighting(self) -> None:
        panel = SceneSettingsPanel()
        panel.set_mode(SceneMode.THREE_D)

        self.assertFalse(panel.grid_check.isVisibleTo(panel))
        self.assertTrue(panel.intersections_check.isVisibleTo(panel))
        self.assertTrue(panel.lighting_button.isVisibleTo(panel))

    def test_values_are_set_without_emitting_change_events(self) -> None:
        panel = SceneSettingsPanel()
        backgrounds: list[str] = []
        panel.background_changed.connect(backgrounds.append)

        panel.set_values(
            background="dark",
            axis_color_mode="color",
            grid=False,
            ticks=False,
            tick_spacing_mode="custom",
            tick_spacing=0.5,
            intersections=True,
        )

        self.assertEqual(panel.background_combo.currentData(), "dark")
        self.assertEqual(panel.axis_combo.currentData(), "color")
        self.assertFalse(panel.ticks_check.isChecked())
        self.assertEqual(panel.tick_spacing_combo.currentData(), "custom")
        self.assertEqual(panel.tick_spacing_input.value(), 0.5)
        self.assertEqual(backgrounds, [])


if __name__ == "__main__":
    unittest.main()
