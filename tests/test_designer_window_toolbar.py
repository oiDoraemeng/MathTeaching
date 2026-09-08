import pytest
from PySide6.QtWidgets import QApplication, QToolButton, QWidget

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
