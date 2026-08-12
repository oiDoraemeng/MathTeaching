"""Public API tests for the reusable MathLive Qt widget."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")

from PySide6.QtWidgets import QApplication

from MathInputWidget import MathInputWidget


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


if __name__ == "__main__":
    unittest.main()
