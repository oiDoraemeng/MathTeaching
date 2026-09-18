"""二维点线工具栏的可见性与悬浮展开测试。"""

import os
import unittest
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QBoxLayout, QWidget

from models.scene_mode import SceneAppearance, SceneMode
from ui.scene_pane_manager import ScenePaneManager
from ui.designer_window import MainWindow
from ui.two_d_tools import TwoDGeometryToolbar


class TwoDGeometryToolbarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def test_toolbar_stays_at_the_left_middle_and_line_hover_opens_the_flyout(self) -> None:
        host = QWidget()
        host.resize(800, 600)
        toolbar = TwoDGeometryToolbar(host)
        host.show()
        toolbar.show()
        toolbar.position_in_host()
        QApplication.processEvents()

        self.assertEqual(toolbar.x(), 12)
        self.assertEqual(toolbar.y(), max(8, (host.height() - toolbar.height()) // 2))
        self.assertEqual(toolbar.layout().direction(), QBoxLayout.Direction.TopToBottom)
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

    def test_dashed_segment_tool_is_available_in_the_line_flyout(self) -> None:
        host = QWidget()
        toolbar = TwoDGeometryToolbar(host)
        events: list[object] = []
        toolbar.tool_selected.connect(events.append)

        toolbar.line_buttons["dashed_segment"].click()

        self.assertEqual(events, ["dashed_segment"])
        self.assertTrue(toolbar.line_buttons["dashed_segment"].isChecked())
        self.assertEqual(
            toolbar.line_buttons["dashed_segment"].property("_kiro_icon_state")[0],
            "minus-dashed",
        )

    def test_vector_addition_tool_is_available_as_a_top_level_command(self) -> None:
        host = QWidget()
        toolbar = TwoDGeometryToolbar(host)
        events: list[object] = []
        toolbar.tool_selected.connect(events.append)

        toolbar.addition_button.click()

        self.assertEqual(events, ["addition"])
        self.assertTrue(toolbar.addition_button.isChecked())

    def test_annotation_tool_is_available_as_a_top_level_command(self) -> None:
        host = QWidget()
        toolbar = TwoDGeometryToolbar(host)
        events: list[object] = []
        toolbar.tool_selected.connect(events.append)

        toolbar.annotation_button.click()

        self.assertEqual(events, ["annotation"])
        self.assertTrue(toolbar.annotation_button.isChecked())
        self.assertEqual(toolbar.annotation_button.property("_kiro_icon_state")[0], "type")

    def test_line_button_click_toggles_flyout(self) -> None:
        host = QWidget()
        host.resize(800, 600)
        toolbar = TwoDGeometryToolbar(host)
        host.show()
        toolbar.show()
        toolbar.position_in_host()
        QApplication.processEvents()

        QTest.mouseClick(toolbar.line_button, Qt.MouseButton.LeftButton)
        self.assertTrue(toolbar.line_flyout.isVisible())
        QTest.mouseClick(toolbar.line_button, Qt.MouseButton.LeftButton)
        self.assertFalse(toolbar.line_flyout.isVisible())

    def test_line_flyout_keyboard_cycle_select_and_escape(self) -> None:
        host = QWidget()
        host.resize(800, 600)
        toolbar = TwoDGeometryToolbar(host)
        host.show()
        toolbar.show()
        toolbar.position_in_host()
        QApplication.processEvents()
        events: list[object] = []
        toolbar.tool_selected.connect(events.append)

        QTest.mouseClick(toolbar.line_button, Qt.MouseButton.LeftButton)
        self.assertTrue(toolbar.line_buttons["line"].hasFocus())
        QTest.keyClick(toolbar.line_buttons["line"], Qt.Key.Key_Down)
        self.assertTrue(toolbar.line_buttons["segment"].hasFocus())
        QTest.keyClick(toolbar.line_buttons["segment"], Qt.Key.Key_Return)
        self.assertEqual(events[-1], "segment")
        self.assertFalse(toolbar.line_flyout.isVisible())

        QTest.mouseClick(toolbar.line_button, Qt.MouseButton.LeftButton)
        QTest.keyClick(toolbar.line_buttons["line"], Qt.Key.Key_Escape)
        self.assertTrue(toolbar.line_button.hasFocus())
        self.assertFalse(toolbar.line_flyout.isVisible())

    def test_grid_snap_is_opt_in(self) -> None:
        host = QWidget()
        toolbar = TwoDGeometryToolbar(host)

        self.assertFalse(toolbar.snap_button.isChecked())

    def test_linear_algebra_mode_reuses_the_vertical_left_middle_toolbar(self) -> None:
        host = QWidget()
        host.resize(900, 600)
        toolbar = TwoDGeometryToolbar(host)
        host.show()
        toolbar.show()

        toolbar.set_linear_algebra_mode(True)
        toolbar.position_in_host()
        QApplication.processEvents()

        self.assertTrue(toolbar.is_linear_algebra_mode())
        self.assertEqual(toolbar.x(), 12)
        self.assertEqual(toolbar.y(), max(8, (host.height() - toolbar.height()) // 2))
        self.assertEqual(toolbar.layout().direction(), QBoxLayout.Direction.TopToBottom)
        self.assertTrue(toolbar.angle_button.isVisible())
        self.assertTrue(toolbar.area_button.isVisible())

        toolbar.set_linear_algebra_mode(False)
        self.assertTrue(toolbar.is_linear_algebra_mode())
        self.assertTrue(toolbar.angle_button.isVisible())

    def test_toolbar_icon_controls_use_consistent_metrics(self) -> None:
        host = QWidget()
        toolbar = TwoDGeometryToolbar(host)

        controls = (
            toolbar.select_button,
            toolbar.point_button,
            toolbar.annotation_button,
            toolbar.line_button,
            toolbar.vector_button,
            toolbar.addition_button,
            toolbar.angle_button,
            toolbar.projection_button,
            toolbar.polygon_button,
            toolbar.transform_button,
            toolbar.subspace_button,
            toolbar.area_button,
            toolbar.snap_button,
            toolbar.undo_button,
            toolbar.redo_button,
            *toolbar.line_buttons.values(),
        )
        for button in controls:
            self.assertEqual(button.text(), "")
            self.assertTrue(button.accessibleName())
            self.assertEqual(button.size(), QSize(36, 36))
            self.assertEqual(button.iconSize(), QSize(16, 16))

    def test_co_located_geometry_tools_use_distinct_icons(self) -> None:
        def icon_name(button) -> str:
            return button.property("_kiro_icon_state")[0]

        host = QWidget()
        toolbar = TwoDGeometryToolbar(host)
        names = [
            icon_name(toolbar.vector_button),
            icon_name(toolbar.addition_button),
            icon_name(toolbar.line_button),
            icon_name(toolbar.angle_button),
            icon_name(toolbar.projection_button),
            *(icon_name(button) for button in toolbar.line_buttons.values()),
        ]
        self.assertEqual(len(names), len(set(names)))

    def test_complete_toolbar_is_expanded_by_default(self) -> None:
        host = QWidget()
        toolbar = TwoDGeometryToolbar(host)

        self.assertTrue(toolbar.is_linear_algebra_mode())
        self.assertTrue(toolbar.angle_button.isVisibleTo(toolbar))
        self.assertTrue(toolbar.projection_button.isVisibleTo(toolbar))
        self.assertTrue(toolbar.area_button.isVisibleTo(toolbar))

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
        window.pane_manager = ScenePaneManager()
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

    def test_main_window_keeps_the_complete_toolbar_visible_in_both_scenes(self) -> None:
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
                self.linear_algebra_mode = None

            def setVisible(self, visible: bool) -> None:
                self.visible = visible

            def set_linear_algebra_mode(self, enabled: bool) -> None:
                self.linear_algebra_mode = enabled

        class FakeThreeDToolbar:
            def __init__(self) -> None:
                self.visible = None
                self.vector_active = None

            def setVisible(self, visible: bool) -> None:
                self.visible = visible

            def set_vector_active(self, active: bool) -> None:
                self.vector_active = active

        class FakeSettings:
            def set_mode(self, _mode) -> None:
                pass

            def set_values(self, **_kwargs) -> None:
                pass

        window = object.__new__(MainWindow)
        window.pane_manager = ScenePaneManager()
        window.scene_mode_button = FakeButton()
        window.two_d_geometry_toolbar = FakeToolbar()
        window.three_d_geometry_toolbar = FakeThreeDToolbar()
        window.scene_settings_panel = FakeSettings()
        window._pane_scene().scene_appearances = {
            SceneMode.TWO_D: SceneAppearance(),
            SceneMode.THREE_D: SceneAppearance(),
        }
        window._pane_scene().scene_mode = SceneMode.TWO_D
        window._active_linear_algebra_topic_id = None

        MainWindow._sync_scene_controls(window)
        self.assertTrue(window.two_d_geometry_toolbar.visible)
        self.assertTrue(window.two_d_geometry_toolbar.linear_algebra_mode)
        self.assertFalse(window.three_d_geometry_toolbar.visible)

        window._pane_scene().scene_mode = SceneMode.THREE_D
        MainWindow._sync_scene_controls(window)
        self.assertFalse(window.two_d_geometry_toolbar.visible)
        self.assertTrue(window.two_d_geometry_toolbar.line_flyout.hidden)
        self.assertTrue(window.three_d_geometry_toolbar.visible)


if __name__ == "__main__":
    unittest.main()
