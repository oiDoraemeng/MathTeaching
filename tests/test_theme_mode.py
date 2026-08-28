from PySide6.QtCore import Qt

from main import effective_theme, normalize_theme_mode


def test_theme_mode_defaults_invalid_values_to_system() -> None:
    assert normalize_theme_mode(None) == "system"
    assert normalize_theme_mode("sepia") == "system"
    assert normalize_theme_mode("dark") == "dark"


def test_system_mode_tracks_qt_color_scheme() -> None:
    assert effective_theme("system", Qt.ColorScheme.Dark) == "dark"
    assert effective_theme("system", Qt.ColorScheme.Light) == "light"
    assert effective_theme("light", Qt.ColorScheme.Dark) == "light"
