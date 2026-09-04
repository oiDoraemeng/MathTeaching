"""高级光照编辑器中材质选择的 Qt 测试。"""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from rendering.lighting import LightSettings
from ui.lighting_dialog import LightingDialog


class LightingDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def test_material_combo_emits_the_selected_preset(self) -> None:
        dialog = LightingDialog(LightSettings(), "光泽塑料")
        events: list[str] = []
        dialog.material_changed.connect(events.append)

        dialog.material_combo.setCurrentText("抛光金属")

        self.assertEqual(events, ["抛光金属"])

    def test_slider_readouts_update_live(self) -> None:
        dialog = LightingDialog(LightSettings())
        dialog.ambient_slider.setValue(37)
        dialog._intensity_sliders["key"].setValue(126)
        self.assertEqual(dialog.ambient_value_label.text(), "37%")
        self.assertEqual(dialog._intensity_value_labels["key"].text(), "126%")

    def test_reset_updates_controls_without_closing(self) -> None:
        dialog = LightingDialog(LightSettings())
        settings_events: list[LightSettings] = []
        material_events: list[str] = []
        dialog.settings_changed.connect(settings_events.append)
        dialog.material_changed.connect(material_events.append)
        dialog.show()
        dialog.ambient_slider.setValue(80)
        dialog._intensity_sliders["fill"].setValue(150)
        dialog.rotation_widget.set_angle(90)
        dialog.material_combo.setCurrentText("抛光金属")
        material_events.clear()
        settings_events.clear()
        dialog._reset_defaults()
        self.assertTrue(dialog.isVisible())
        self.assertEqual(dialog.ambient_slider.value(), 20)
        self.assertEqual(dialog._intensity_sliders["key"].value(), 105)
        self.assertEqual(dialog._intensity_sliders["fill"].value(), 45)
        self.assertEqual(dialog._intensity_sliders["rim"].value(), 70)
        self.assertEqual(dialog.rotation_widget.angle, 0)
        self.assertEqual(dialog.material_combo.currentText(), "光泽塑料")
        self.assertEqual(material_events, ["光泽塑料"])
        self.assertEqual(len(settings_events), 1)
        self.assertEqual(settings_events[-1].ambient, 0.20)
        self.assertEqual(settings_events[-1].key["intensity"], 1.05)
        dialog.close()


if __name__ == "__main__":
    unittest.main()
