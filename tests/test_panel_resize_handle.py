from __future__ import annotations

from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from ui.panel_resize_handle import PanelResizeSpec, _PanelResizeHandle


def test_left_panel_handle_clamps_and_persists(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    handle = _PanelResizeHandle(PanelResizeSpec(260, 420, 320, "ui/algebra_panel_width", "right"), settings=settings)
    assert handle.set_width(99) == 260
    assert handle.set_width(999) == 420
    assert settings.value("ui/algebra_panel_width", type=int) == 420
    assert handle.restore_width() == 420
    handle.set_width(320)
    assert handle.restore_width() == 320


def test_right_panel_drag_uses_inverse_delta(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    handle = _PanelResizeHandle(PanelResizeSpec(360, 720, 440, "ui/agent_panel_width", "left"), settings=settings)
    assert handle.width_for_delta(start_width=440, delta_x=-50) == 490
    assert handle.width_for_delta(start_width=440, delta_x=200) == 360


def test_resize_handle_exposes_drag_state_and_discoverability(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    handle = _PanelResizeHandle(
        PanelResizeSpec(260, 420, 320, "ui/algebra_panel_width", "right"),
        settings=QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat),
    )
    handle.resize(6, 20)
    handle.show()
    assert handle.width() == 6
    assert handle.objectName() == "panelResizeHandle"
    assert handle.toolTip() == "拖动调整宽度，双击复位"
    QTest.mousePress(handle, Qt.MouseButton.LeftButton, pos=QPoint(2, 2))
    assert handle.property("dragging") is True
    QTest.mouseRelease(handle, Qt.MouseButton.LeftButton, pos=QPoint(2, 2))
    assert handle.property("dragging") is False


def test_agent_panel_restores_values_above_the_old_limit(tmp_path) -> None:
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    settings.setValue("ui/agent_panel_width", 680)
    handle = _PanelResizeHandle(
        PanelResizeSpec(360, 720, 440, "ui/agent_panel_width", "left"),
        settings=settings,
    )
    assert handle.restore_width() == 680
    assert handle.set_width(999) == 720


def test_drag_follows_pointer_and_clamps_at_both_edges(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    cases = (
        (PanelResizeSpec(260, 420, 320, "ui/algebra_panel_width", "right"), 320, 180, 420),
        (PanelResizeSpec(360, 720, 440, "ui/agent_panel_width", "left"), 440, -400, 720),
    )
    for spec, start, delta, expected in cases:
        settings = QSettings(str(tmp_path / f"{spec.edge}.ini"), QSettings.Format.IniFormat)
        handle = _PanelResizeHandle(spec, settings=settings)
        handle.set_width(start)
        handle.resize(6, 24)
        handle.show()
        QApplication.processEvents()
        seen: list[int] = []
        handle.width_changed.connect(seen.append)
        QTest.mousePress(handle, Qt.MouseButton.LeftButton, pos=QPoint(2, 2))
        QTest.mouseMove(handle, QPoint(2 + delta, 2))
        QTest.mouseRelease(handle, Qt.MouseButton.LeftButton, pos=QPoint(2 + delta, 2))
        assert seen[-1] == expected
        assert settings.value(spec.settings_key, type=int) == expected
        handle.deleteLater()


def test_double_click_resets_and_new_handle_restores_width(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    spec = PanelResizeSpec(360, 720, 440, "ui/agent_panel_width", "left")
    handle = _PanelResizeHandle(spec, settings=settings)
    handle.set_width(680)
    handle.resize(6, 24)
    handle.show()
    QTest.mouseDClick(handle, Qt.MouseButton.LeftButton, pos=QPoint(2, 2))
    assert settings.value(spec.settings_key, type=int) == 440
    restored = _PanelResizeHandle(spec, settings=settings)
    assert restored.restore_width() == 440
