from __future__ import annotations

from PySide6.QtCore import QSettings
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
    handle = _PanelResizeHandle(PanelResizeSpec(360, 560, 440, "ui/agent_panel_width", "left"), settings=settings)
    assert handle.width_for_delta(start_width=440, delta_x=-50) == 490
    assert handle.width_for_delta(start_width=440, delta_x=200) == 360
