"""可复用 MathLive Qt 控件公开 API 的测试。"""

import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")

from PySide6.QtWidgets import QApplication, QComboBox, QWidget

from MathInputWidget import (
    FloatingMathKeyboard,
    FormulaEditorPopup,
    FormulaPreviewWidget,
    MathInputWidget,
)


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

    def test_floating_keyboard_has_no_visible_formula_input(self) -> None:
        source = (
            Path(__file__).parents[1] / "MathInputWidget" / "floating_math_keyboard.html"
        ).read_text(encoding="utf-8")

        self.assertIn('id="keyboard-proxy"', source)
        self.assertIn("left: -10000px", source)
        self.assertIn("window.mathVirtualKeyboard.show()", source)
        self.assertNotIn('id="formula"', source)

    def test_floating_keyboard_uses_a_wide_centered_host_overlay(self) -> None:
        host = QWidget()
        host.resize(1200, 800)
        keyboard = FloatingMathKeyboard(host)

        keyboard.open_keyboard("")

        self.assertEqual(keyboard.parentWidget(), host)
        self.assertGreaterEqual(keyboard.width(), keyboard.MINIMUM_WIDTH)
        self.assertEqual(keyboard.width(), keyboard.PREFERRED_WIDTH)
        self.assertEqual(keyboard.x(), (host.width() - keyboard.width()) // 2)
        self.assertEqual(keyboard.y(), host.height() - keyboard.height() - keyboard.OUTER_MARGIN)
        keyboard.dismiss()
        host.close()

    def test_floating_keyboard_stays_to_the_right_of_its_anchor(self) -> None:
        host = QWidget()
        host.resize(1200, 800)
        anchor = QWidget(host)
        anchor.setGeometry(320, 0, 600, 800)
        keyboard = FloatingMathKeyboard(host)
        keyboard.set_anchor_widget(anchor)

        keyboard.open_keyboard("")

        self.assertGreaterEqual(keyboard.x(), anchor.x())
        self.assertGreaterEqual(keyboard.width(), keyboard.MINIMUM_WIDTH)
        keyboard.dismiss()
        host.close()

    def test_floating_keyboard_does_not_restore_itself_after_focus_moves_away(self) -> None:
        source = (
            Path(__file__).parents[1] / "MathInputWidget" / "floating_math_keyboard.html"
        ).read_text(encoding="utf-8")

        self.assertNotIn("proxy.addEventListener('blur'", source)
        self.assertIn("const hide = () =>", source)

    def test_formula_preview_keeps_fallback_until_page_and_first_paint_are_ready(self) -> None:
        preview = FormulaPreviewWidget(r"y=\frac{1}{x}")
        preview.web_view = MagicMock()
        preview._theme_bridge = MagicMock()

        preview._on_browser_painted()

        preview.web_view.setVisible.assert_not_called()
        self.assertFalse(preview._fallback_label.isHidden())

        preview._on_load_finished(True)

        preview.web_view.setVisible.assert_called_once_with(True)
        self.assertTrue(preview._fallback_label.isHidden())


if __name__ == "__main__":
    unittest.main()
