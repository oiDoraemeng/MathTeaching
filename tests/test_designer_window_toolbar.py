import pytest
from PySide6.QtWidgets import QApplication, QToolButton, QVBoxLayout, QWidget

from ui.designer_window import MainWindow
from ui.icons import LUCIDE_SVG, retint_icons


@pytest.fixture
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_layout_icons_are_bundled() -> None:
    assert all(f"layout-{count}" in LUCIDE_SVG for count in range(1, 5))


def test_layout_button_sync_uses_visible_pane_count(qapp: QApplication) -> None:
    host = QWidget()
    buttons = {count: QToolButton(host) for count in range(1, 5)}
    for button in buttons.values():
        button.setCheckable(True)
    manager = type("Manager", (), {"visible_pane_ids": lambda self: ("p1", "p2", "p3")})()
    window = MainWindow.__new__(MainWindow)
    window.layout_buttons = buttons
    window.pane_manager = manager
    MainWindow._sync_layout_buttons(window)
    assert buttons[3].isChecked()
    assert not buttons[1].isChecked()
    host.deleteLater()


def test_layout_icons_retint_with_theme(qapp: QApplication) -> None:
    host = QWidget()
    button = QToolButton(host)
    from ui.icons import apply_icon, icon_color
    apply_icon(button, "layout-1", icon_color("light"))
    assert retint_icons(host, "dark") == 1
    host.deleteLater()


def test_main_window_installs_four_layout_buttons_and_routes_click(qapp: QApplication) -> None:
    host = QWidget()
    window = MainWindow.__new__(MainWindow)
    window.viewport_toolbar = host
    window.effective_theme = "light"
    calls = []
    window.pane_manager = type("Manager", (), {"visible_pane_ids": lambda self: ("p1",), "set_layout": lambda self, n: calls.append(n)})()
    layout = QVBoxLayout(host)
    MainWindow._install_layout_buttons(window, layout)
    assert [b.accessibleName() for b in window.layout_buttons.values()] == ["单窗格布局", "双窗格布局", "三窗格布局", "四窗格布局"]
    assert all(b.toolTip() for b in window.layout_buttons.values())
    window.layout_buttons[4].click()
    assert calls == [4]
    host.deleteLater()


def test_layout_checked_selector_is_in_stylesheet() -> None:
    from ui.tokens import build_qss
    assert "#viewportToolbar QToolButton:checked" in build_qss("light")
