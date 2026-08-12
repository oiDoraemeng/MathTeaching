"""Integration tests for the GeoGebra-style algebra/viewport split."""

import os
from pathlib import Path
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QFile, QIODevice
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QHBoxLayout

from MathInputWidget import LatexParser
from ui.algebra_panel import AlgebraPanel
from ui.designer_window import MainWindow
from geometry.standard_surfaces import BUILTIN_SURFACES


class MainWindowLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def test_algebra_panel_replaces_the_legacy_sidebar_at_the_left_of_the_viewport(self) -> None:
        form = QFile(str(Path("ui/main_window.ui")))
        self.assertTrue(form.open(QIODevice.OpenModeFlag.ReadOnly))
        try:
            designer_window = QUiLoader().load(form)
        finally:
            form.close()
        self.assertIsNotNone(designer_window)
        window = object.__new__(MainWindow)
        window.window = designer_window

        MainWindow._install_algebra_panel(window)

        root_layout = designer_window.findChild(QHBoxLayout, "rootLayout")
        self.assertIsInstance(root_layout.itemAt(0).widget(), AlgebraPanel)
        self.assertEqual(root_layout.itemAt(1).widget().objectName(), "viewportHost")

    def test_binding_populates_the_builtin_surface_menu(self) -> None:
        window = object.__new__(MainWindow)
        window.algebra_panel = AlgebraPanel()
        window.latex_parser = LatexParser()

        MainWindow._bind_algebra_panel(window)

        self.assertEqual(len(window.algebra_panel.builtin_menu.actions()), len(BUILTIN_SURFACES))

    def test_mathlive_formula_is_normalized_before_the_existing_cas_parser(self) -> None:
        window = object.__new__(MainWindow)
        window.latex_parser = LatexParser()

        formula, parsed = MainWindow._parse_mathlive_surface(window, r"z=x+y", "explicit")

        self.assertEqual(formula.canonical_source, "z = x + y")
        self.assertEqual(parsed.dependent_axis, "z")


if __name__ == "__main__":
    unittest.main()
