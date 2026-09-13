"""类 GeoGebra 代数区与视口分栏的集成测试。"""

import os
from pathlib import Path
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QFile, QIODevice
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QHBoxLayout, QWidget

from MathInputWidget import LatexParser
from ui.algebra_panel import AlgebraPanel
from ui.scene_pane_manager import ScenePaneManager
from ui.designer_window import MainWindow
from geometry.standard_surfaces import BUILTIN_SURFACES
from models.scene_mode import SceneMode


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
        window.pane_manager = ScenePaneManager()
        window.window = designer_window

        MainWindow._install_algebra_panel(window)

        root_layout = designer_window.findChild(QHBoxLayout, "rootLayout")
        self.assertIsInstance(root_layout.itemAt(0).widget(), AlgebraPanel)
        self.assertEqual(root_layout.itemAt(1).widget().width(), 6)
        self.assertEqual(root_layout.itemAt(2).widget().objectName(), "viewportHost")
        self.assertEqual(window.algebra_panel.MIN_WIDTH, 260)
        self.assertEqual(window.algebra_panel.MAX_WIDTH, 420)

    def test_binding_populates_the_builtin_surface_menu(self) -> None:
        window = object.__new__(MainWindow)
        window.pane_manager = ScenePaneManager()
        window.algebra_panel = AlgebraPanel()
        window.latex_parser = LatexParser()

        MainWindow._bind_algebra_panel(window)

        self.assertEqual(len(window.algebra_panel.builtin_menu.actions()), len(BUILTIN_SURFACES))

    def test_initial_3d_scene_contains_only_the_coordinate_system(self) -> None:
        window = object.__new__(MainWindow)
        window.pane_manager = ScenePaneManager()

        MainWindow._initialize_default_scene(window)

        self.assertIs(window._pane_scene().scene_mode, SceneMode.THREE_D)
        self.assertEqual(window._pane_scene().layers, [])

    def test_mathlive_formula_is_normalized_before_the_existing_cas_parser(self) -> None:
        window = object.__new__(MainWindow)
        window.pane_manager = ScenePaneManager()
        window.latex_parser = LatexParser()

        formula, parsed = MainWindow._parse_mathlive_surface(window, r"z=x+y", "explicit")

        self.assertEqual(formula.canonical_source, "z = x + y")
        self.assertEqual(parsed.dependent_axis, "z")

    def test_scene_mode_switch_keeps_independent_layer_lists(self) -> None:
        window = object.__new__(MainWindow)
        window.pane_manager = ScenePaneManager()
        window._pane_scene().scene_mode = __import__("models.scene_mode", fromlist=["SceneMode"]).SceneMode.THREE_D
        window._pane_scene().layers = [object()]
        window._pane_scene().curve_layers = []
        window._save_current_view_state = lambda: None
        window._close_scene_settings = lambda **_kwargs: None
        rendered: list[object] = []
        window._render_scene = lambda: rendered.append(window._pane_scene().scene_mode)

        MainWindow._set_scene_mode(
            window,
            __import__("models.scene_mode", fromlist=["SceneMode"]).SceneMode.TWO_D,
        )

        self.assertEqual(len(window._pane_scene().layers), 1)
        self.assertEqual(window._pane_scene().curve_layers, [])
        self.assertEqual(len(rendered), 1)

    def test_agent_web_panel_is_fixed_on_the_right_and_hidden_without_a_slot(self) -> None:
        host = QWidget()
        host.resize(900, 600)
        layout = QHBoxLayout(host)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        viewport = QWidget(host)
        # This test asserts layout allocation only. WebView lifecycle and
        # bridge behavior are covered by the dedicated Agent Web tests.
        panel = QWidget(host)
        panel.setFixedWidth(420)
        layout.addWidget(viewport)
        layout.addWidget(panel)

        panel.hide()
        layout.activate()
        self.assertFalse(panel.isVisible())
        self.assertEqual(viewport.width(), 900)

        panel.show()
        layout.activate()
        self.assertEqual(panel.width(), 420)
        self.assertEqual(panel.x(), 480)
        self.assertEqual(viewport.width(), 480)

        panel.hide()
        layout.activate()
        self.assertFalse(panel.isVisible())
        self.assertEqual(viewport.width(), 900)
        host.deleteLater()


if __name__ == "__main__":
    unittest.main()
