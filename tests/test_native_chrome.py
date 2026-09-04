import ctypes
import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent
import pytest
from PySide6.QtWidgets import QApplication, QDialog, QWidget

from ui import native_chrome
from ui.native_chrome import apply_native_titlebar_theme, install_titlebar_tracker
from ui.designer_window import MainWindow


@pytest.fixture(scope="module", autouse=True)
def _application() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_dwm_receives_dark_and_light_integer_values(monkeypatch) -> None:
    calls = []

    class DwmApi:
        def DwmSetWindowAttribute(self, hwnd, attribute, value, size):
            calls.append((int(hwnd), attribute, value._obj.value, size))
            return 0

    monkeypatch.setattr(native_chrome.sys, "platform", "win32")
    monkeypatch.setattr(native_chrome.ctypes, "windll", SimpleNamespace(dwmapi=DwmApi()), raising=False)
    window = QWidget()
    assert apply_native_titlebar_theme(window, "dark") is True
    assert apply_native_titlebar_theme(window, "light") is True
    assert [call[2] for call in calls] == [1, 0]
    assert all(call[1] == 20 for call in calls)
    assert all(call[3] == ctypes.sizeof(ctypes.c_int) for call in calls)


def test_native_chrome_fallbacks_never_raise(monkeypatch) -> None:
    window = QWidget()
    monkeypatch.setattr(native_chrome.sys, "platform", "linux")
    assert apply_native_titlebar_theme(window, "dark") is False
    monkeypatch.setattr(native_chrome.sys, "platform", "win32")
    monkeypatch.delattr(native_chrome.ctypes, "windll", raising=False)
    assert apply_native_titlebar_theme(window, "dark") is False
    monkeypatch.setattr(native_chrome.ctypes, "windll", SimpleNamespace(dwmapi=SimpleNamespace(DwmSetWindowAttribute=lambda *args: (_ for _ in ()).throw(OSError()))), raising=False)
    assert apply_native_titlebar_theme(window, "dark") is False
    monkeypatch.setattr(native_chrome.ctypes, "windll", SimpleNamespace(dwmapi=SimpleNamespace(DwmSetWindowAttribute=lambda *args: 1)), raising=False)
    assert apply_native_titlebar_theme(window, "dark") is False
    assert apply_native_titlebar_theme(window, "sepia") is False


def test_titlebar_tracker_is_idempotent_and_handles_window_events(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    app.setProperty("math3d_effective_theme", "dark")
    calls = []
    monkeypatch.setattr(native_chrome, "apply_native_titlebar_theme", lambda window, theme: calls.append((window, theme)) or True)
    install_titlebar_tracker(app)
    tracker = app.property("math3d_titlebar_tracker")
    install_titlebar_tracker(app)
    assert app.property("math3d_titlebar_tracker") is tracker
    window = QWidget()
    tracker.eventFilter(window, QEvent(QEvent.Type.Show))
    tracker.eventFilter(window, QEvent(QEvent.Type.WinIdChange))
    assert calls == [(window, "dark"), (window, "dark")]


def test_apply_style_updates_app_property_and_all_top_level_windows(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    shell = QWidget()
    dialog = QDialog()
    seen = []
    monkeypatch.setattr(QApplication, "topLevelWidgets", staticmethod(lambda: [shell, dialog]))
    monkeypatch.setattr("ui.designer_window.apply_native_titlebar_theme", lambda widget, theme: seen.append((widget, theme)) or True)

    window = object.__new__(MainWindow)
    window.window = shell
    window.effective_theme = "dark"
    MainWindow._apply_style(window)
    assert app.property("math3d_effective_theme") == "dark"
    assert seen == [(shell, "dark"), (dialog, "dark")]

    seen.clear()
    window.effective_theme = "light"
    MainWindow._apply_style(window)
    assert app.property("math3d_effective_theme") == "light"
    assert seen == [(shell, "light"), (dialog, "light")]
