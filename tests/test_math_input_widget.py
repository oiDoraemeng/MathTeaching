"""可复用 MathLive Qt 控件公开 API 的测试。"""

import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")

from PySide6.QtWidgets import QApplication, QComboBox

from MathInputWidget import FormulaEditorPopup, MathInputWidget


class MathInputWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def test_set_latex_is_immediately_available_through_the_public_getter(self) -> None:
        widget = MathInputWidget()

        widget.set_latex(r"\frac{x^2}{a^2}=1")

        self.assertEqual(widget.get_latex(), r"\frac{x^2}{a^2}=1")
        self.assertIsNone(widget.web_view)
        widget.close()

    def test_explicit_keyboard_hiding_restores_the_compact_editor_height(self) -> None:
        widget = MathInputWidget()
        visibility: list[bool] = []
        widget.keyboardVisibilityChanged.connect(visibility.append)

        widget._bridge.virtualKeyboardHeightChanged(218)
        self.assertGreaterEqual(widget.height(), 286)
        widget.hide_virtual_keyboard()

        self.assertEqual(widget.height(), 56)
        self.assertEqual(visibility, [True, False])

    def test_formula_content_height_is_preserved_when_keyboard_hides(self) -> None:
        widget = MathInputWidget()

        widget._bridge.contentHeightChanged(112)
        widget._bridge.virtualKeyboardHeightChanged(218)
        self.assertGreaterEqual(widget.height(), 330)
        widget.hide_virtual_keyboard()

        self.assertEqual(widget.height(), 112)

    def test_new_formula_popup_is_larger_without_a_surface_type_selector(self) -> None:
        popup = FormulaEditorPopup()

        self.assertGreaterEqual(popup.minimumWidth(), 560)
        self.assertGreaterEqual(popup.minimumHeight(), 420)
        self.assertIsNone(popup.findChild(QComboBox))
        popup.close()

        popup_source = Path(__file__).parents[1] / "MathInputWidget" / "formula_popup.py"
        self.assertNotIn("QComboBox", popup_source.read_text(encoding="utf-8"))

    def test_formula_popup_does_not_open_virtual_keyboard_on_focus(self) -> None:
        html_source = (Path(__file__).parents[1] / "MathInputWidget" / "mathlive.html").read_text(
            encoding="utf-8"
        )

        focusin_block = html_source.split("field.addEventListener('focusin'", 1)[1].split("});", 1)[0]
        self.assertNotIn("mathVirtualKeyboard.show()", focusin_block)
        self.assertIn("focus: (showKeyboard = false)", html_source)

    def test_formula_list_uses_manual_virtual_keyboard_policy(self) -> None:
        list_source = (Path(__file__).parents[1] / "MathInputWidget" / "formula_list.html").read_text(
            encoding="utf-8"
        )

        self.assertIn("field.mathVirtualKeyboardPolicy = 'manual'", list_source)
        start_edit = list_source.split("const startEdit =", 1)[1].split("const bindRow =", 1)[0]
        self.assertNotIn("showKeyboard(field", start_edit)


if __name__ == "__main__":
    unittest.main()
