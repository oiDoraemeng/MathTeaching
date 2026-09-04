"""应用程序入口。"""

import sys
from typing import Literal

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from ui.designer_window import MainWindow
from ui.native_chrome import install_titlebar_tracker
from ui.tokens import font_family_stack, load_tokens

ThemeMode = Literal["light", "dark", "system"]
EffectiveTheme = Literal["light", "dark"]


def normalize_theme_mode(value: object) -> ThemeMode:
    """Return a supported persisted theme mode, defaulting invalid values to system."""
    if isinstance(value, str):
        mode = value.strip().lower()
        if mode in {"light", "dark", "system"}:
            return mode  # type: ignore[return-value]
    return "system"


def effective_theme(mode: object, color_scheme: object) -> EffectiveTheme:
    """Resolve a user mode to the concrete light/dark palette."""
    normalized = normalize_theme_mode(mode)
    if normalized == "dark":
        return "dark"
    if normalized == "light":
        return "light"
    return "dark" if color_scheme == Qt.ColorScheme.Dark else "light"


def build_application_font() -> QFont:
    """Build the token-defined application font using pixel sizing."""
    tokens = load_tokens()
    font_tokens = tokens["font"]
    font = QFont()
    font.setFamilies(font_family_stack(tokens))
    font.setPixelSize(int(font_tokens["size"]["body"]))
    font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
    return font


def main() -> int:
    app = QApplication(sys.argv)
    install_titlebar_tracker(app)
    app.setStyle("Fusion")
    settings = QSettings()
    mode = normalize_theme_mode(settings.value("ui/theme", "system"))
    effective = effective_theme(mode, app.styleHints().colorScheme())
    app.setFont(build_application_font())
    window = MainWindow(theme_mode=mode, effective_theme=effective)

    def _system_theme_changed(color_scheme: Qt.ColorScheme) -> None:
        if getattr(window, "theme_mode", "system") != "system":
            return
        window.set_theme("system", effective_theme("system", color_scheme))

    app.styleHints().colorSchemeChanged.connect(_system_theme_changed)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
