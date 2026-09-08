import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication

from main import effective_theme, normalize_theme_mode
from ui.designer_window import MainWindow
from ui.scene_pane_manager import ScenePaneManager


def test_theme_mode_defaults_invalid_values_to_system() -> None:
    assert normalize_theme_mode(None) == "system"
    assert normalize_theme_mode("sepia") == "system"
    assert normalize_theme_mode("dark") == "dark"


def test_system_mode_tracks_qt_color_scheme() -> None:
    assert effective_theme("system", Qt.ColorScheme.Dark) == "dark"
    assert effective_theme("system", Qt.ColorScheme.Light) == "light"
    assert effective_theme("light", Qt.ColorScheme.Dark) == "light"


def test_set_theme_persists_without_rerendering_scene() -> None:
    app = QApplication.instance() or QApplication([])
    app.setOrganizationName("Math3DTeaching")
    app.setApplicationName("Math3DTeaching")
    settings = QSettings()
    settings.remove("ui/theme")
    window = object.__new__(MainWindow)
    window.pane_manager = ScenePaneManager()
    window._apply_style = lambda: None
    window._render_scene = lambda: (_ for _ in ()).throw(AssertionError("scene rerendered"))
    MainWindow.set_theme(window, "dark", "dark")
    assert settings.value("ui/theme") == "dark"
