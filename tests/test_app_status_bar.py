from __future__ import annotations

from PySide6.QtWidgets import QApplication

from ui.status_bar import AppStatusBar


def test_status_bar_contract() -> None:
    app = QApplication.instance() or QApplication([])
    bar = AppStatusBar()
    assert bar.height() == 30
    assert bar.theme_button.width() == 28
    calls: list[bool] = []
    bar.agent_toggle_requested.connect(lambda: calls.append(True))
    bar.agent_button.click()
    assert calls == [True]

    assert bar.theme_mode == "system"
    assert bar.theme_button.accessibleName() == "系统主题"
    bar.set_theme_mode("light")
    assert bar.theme_mode == "light"
    assert bar.theme_button.accessibleName() == "浅色主题"
    bar.set_theme_mode("dark")
    assert bar.theme_button.accessibleName() == "深色主题"
