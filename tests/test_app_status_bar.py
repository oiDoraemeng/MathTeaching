from __future__ import annotations

from PySide6.QtWidgets import QApplication

from ui.status_bar import AppStatusBar


def test_status_bar_contract() -> None:
    app = QApplication.instance() or QApplication([])
    bar = AppStatusBar()
    assert bar.height() == 30
    assert bar.theme_button.width() == 28
    assert bar.render_label.isHidden()
    bar.set_render_status("二维场景已准备好")
    assert bar.render_label.text() == "二维场景已准备好"
    assert not bar.render_label.isHidden()
    bar.set_render_status(r"正在比较 $\boldsymbol v_1$ 与 $\boldsymbol v_2$")
    assert bar.render_label.text() == "正在比较 v₁ 与 v₂"

    assert bar.theme_mode == "system"
    assert bar.theme_button.accessibleName() == "系统主题"
    bar.set_theme_mode("light")
    assert bar.theme_mode == "light"
    assert bar.theme_button.accessibleName() == "浅色主题"
    bar.set_theme_mode("dark")
    assert bar.theme_button.accessibleName() == "深色主题"
