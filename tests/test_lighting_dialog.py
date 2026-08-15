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


if __name__ == "__main__":
    unittest.main()
