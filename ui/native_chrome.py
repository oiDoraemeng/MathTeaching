"""Optional native title-bar theming with safe platform fallbacks."""

from __future__ import annotations

import ctypes
import sys

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QApplication, QWidget

DWMWA_USE_IMMERSIVE_DARK_MODE = 20


def apply_native_titlebar_theme(window: QWidget, effective_theme: str) -> bool:
    """Apply the Windows immersive title-bar flag when the API is available."""
    if sys.platform != "win32" or effective_theme not in ("light", "dark"):
        return False
    try:
        enabled = ctypes.c_int(1 if effective_theme == "dark" else 0)
        result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            int(window.winId()),
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(enabled),
            ctypes.sizeof(enabled),
        )
    except (AttributeError, OSError, TypeError, ValueError):
        return False
    return result == 0


class _TitlebarTracker(QObject):
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if (
            event.type() in (QEvent.Type.Show, QEvent.Type.WinIdChange)
            and isinstance(watched, QWidget)
            and watched.isWindow()
        ):
            app = QApplication.instance()
            theme = app.property("math3d_effective_theme") if app else None
            if theme in ("light", "dark"):
                apply_native_titlebar_theme(watched, theme)
        return False


def install_titlebar_tracker(app: QApplication) -> None:
    """Install one process-wide tracker for top-level window lifecycle events."""
    if app.property("math3d_titlebar_tracker") is None:
        tracker = _TitlebarTracker(app)
        app.setProperty("math3d_titlebar_tracker", tracker)
        app.installEventFilter(tracker)
