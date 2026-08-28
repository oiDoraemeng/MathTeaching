"""应用程序入口。"""

import sys
from typing import Literal

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from ui.designer_window import MainWindow
from ui.tokens import load_tokens

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


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    settings = QSettings()
    tokens = load_tokens()
    mode = normalize_theme_mode(settings.value("ui/theme", "system"))
    effective = effective_theme(mode, app.styleHints().colorScheme())
    font = tokens["font"]
    app.setFont(QFont(str(font["family_default"]), int(font["size"]["body"])))
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
