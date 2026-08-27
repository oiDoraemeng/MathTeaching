"""二维点线工具栏的可见性与悬浮展开测试。"""

import os
import unittest
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication, QWidget

from models.scene_mode import SceneAppearance, SceneMode
from ui.designer_window import MainWindow
from ui.two_d_tools import TwoDGeometryToolbar


class TwoDGeometryToolbarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def test_toolbar_stays_at_the_right_middle_and_line_hover_opens_the_flyout(self) -> None:
        host = QWidget()
        host.resize(800, 600)
        toolbar = TwoDGeometryToolbar(host)
        host.show()
        toolbar.show()
        toolbar.position_in_host()
        QApplication.processEvents()

        self.assertEqual(toolbar.x(), 800 - toolbar.width() - 12)
        self.assertEqual(toolbar.y(), (600 - toolbar.height()) // 2)
        QApplication.sendEvent(toolbar.line_button, QEvent(QEvent.Type.Enter))
        QApplication.processEvents()
        self.assertTrue(toolbar.line_flyout.isVisible())

    def test_line_tool_selection_emits_the_concrete_tool(self) -> None:
        host = QWidget()
        toolbar = TwoDGeometryToolbar(host)
        events: list[object] = []
        toolbar.tool_selected.connect(events.append)

        toolbar.line_buttons["ray"].click()
        toolbar.line_buttons["ray"].click()

        self.assertEqual(events, ["ray", None])
        self.assertFalse(toolbar.line_button.isChecked())

    def test_grid_snap_is_opt_in(self) -> None:
        host = QWidget()
        toolbar = TwoDGeometryToolbar(host)

        self.assertFalse(toolbar.snap_button.isChecked())

    def test_undo_and_redo_buttons_emit_actions_and_follow_history_state(self) -> None:
        host = QWidget()
        toolbar = TwoDGeometryToolbar(host)
        undo_events: list[bool] = []
        redo_events: list[bool] = []
        toolbar.undo_requested.connect(lambda: undo_events.append(True))
        toolbar.redo_requested.connect(lambda: redo_events.append(True))

        self.assertFalse(toolbar.undo_button.isEnabled())
        self.assertFalse(toolbar.redo_button.isEnabled())

        toolbar.set_history_state(can_undo=True, can_redo=False)
        self.assertTrue(toolbar.undo_button.isEnabled())
        self.assertFalse(toolbar.redo_button.isEnabled())
        toolbar.undo_button.click()

        toolbar.set_history_state(can_undo=False, can_redo=True)
        toolbar.redo_button.click()

        self.assertEqual(undo_events, [True])
        self.assertEqual(redo_events, [True])

    def test_main_window_registers_undo_and_redo_shortcuts(self) -> None:
        window = object.__new__(MainWindow)
        window.window = QWidget()
        window._undo_2d_geometry = MagicMock()
        window._redo_2d_geometry = MagicMock()

        MainWindow._configure_2d_history_shortcuts(window)

        self.assertEqual(window._undo_2d_shortcut.key(), QKeySequence("Ctrl+Z"))
        self.assertEqual(window._redo_2d_shortcut.key(), QKeySequence("Ctrl+Shift+Z"))
        window._undo_2d_shortcut.activated.emit()
        window._redo_2d_shortcut.activated.emit()
        window._undo_2d_geometry.assert_called_once_with()
        window._redo_2d_geometry.assert_called_once_with()

    def test_main_window_only_shows_the_geometry_toolbar_in_two_d_mode(self) -> None:
        class FakeButton:
            def __init__(self) -> None:
                self.text = ""

            def setText(self, text: str) -> None:
                self.text = text

        class FakeFlyout:
            def __init__(self) -> None:
                self.hidden = False

            def hide(self) -> None:
                self.hidden = True

        class FakeToolbar:
            def __init__(self) -> None:
                self.visible = None
                self.line_flyout = FakeFlyout()

            def setVisible(self, visible: bool) -> None:
                self.visible = visible

        class FakeSettings:
            def set_mode(self, _mode) -> None:
                pass

            def set_values(self, **_kwargs) -> None:
                pass

        window = object.__new__(MainWindow)
        window.scene_mode_button = FakeButton()
        window.two_d_geometry_toolbar = FakeToolbar()
        window.scene_settings_panel = FakeSettings()
        window.scene_appearances = {
            SceneMode.TWO_D: SceneAppearance(),
            SceneMode.THREE_D: SceneAppearance(),
        }
        window.scene_mode = SceneMode.TWO_D

        MainWindow._sync_scene_controls(window)
        self.assertTrue(window.two_d_geometry_toolbar.visible)

        window.scene_mode = SceneMode.THREE_D
        MainWindow._sync_scene_controls(window)
        self.assertFalse(window.two_d_geometry_toolbar.visible)
        self.assertTrue(window.two_d_geometry_toolbar.line_flyout.hidden)


if __name__ == "__main__":
    unittest.main()
