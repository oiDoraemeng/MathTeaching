"""Bundled Lucide-style SVG icons for Qt controls."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QAbstractButton, QApplication


_SVG_HEAD = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
_SVG_TAIL = "</svg>"


def _svg(paths: str) -> str:
    return f"{_SVG_HEAD}{paths}{_SVG_TAIL}"


# These paths are intentionally bundled so controls do not depend on fonts,
# platform icon themes, or remote assets.
LUCIDE_SVG: Mapping[str, str] = MappingProxyType(
    {
        "settings-2": _svg('<path d="M20 7h-9"/><path d="M14 17H5"/><circle cx="17" cy="17" r="3"/><circle cx="7" cy="7" r="3"/>'),
        "sparkles": _svg('<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/><path d="M5 3v4"/><path d="M19 17v4"/><path d="M3 5h4"/><path d="M17 19h4"/>'),
        "play": _svg('<path d="m5 3 14 9-14 9V3z"/>'),
        "circle-dot": _svg('<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="1"/>'),
        "slash": _svg('<path d="m17 5-10 14"/>'),
        "type": _svg('<path d="M4 7V4h16v3"/><path d="M9 20h6"/><path d="M12 4v16"/>'),
        "undo-2": _svg('<path d="M9 14 4 9l5-5"/><path d="M4 9h11a5 5 0 0 1 5 5v1"/>'),
        "redo-2": _svg('<path d="m15 14 5-5-5-5"/><path d="M20 9H9a5 5 0 0 0-5 5v1"/>'),
        "plus": _svg('<path d="M5 12h14"/><path d="M12 5v14"/>'),
        "ellipsis": _svg('<circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/>'),
        "eye": _svg('<path d="M2.1 12.3a1 1 0 0 1 0-.6C3.5 7.6 7.2 5 12 5s8.5 2.6 9.9 6.7a1 1 0 0 1 0 .6C20.5 16.4 16.8 19 12 19S3.5 16.4 2.1 12.3Z"/><circle cx="12" cy="12" r="3"/>'),
        "eye-off": _svg('<path d="m2 2 20 20"/><path d="M6.7 6.7C4.6 8.1 3.1 10 2.1 11.7a1 1 0 0 0 0 .6C3.5 16.4 7.2 19 12 19c1.7 0 3.2-.3 4.5-.9"/><path d="M10.6 10.6a2 2 0 0 0 2.8 2.8"/><path d="M9.9 5.1A10.8 10.8 0 0 1 12 5c4.8 0 8.5 2.6 9.9 6.7a1 1 0 0 1 0 .6 12 12 0 0 1-2.2 3.1"/>'),
        "grid-3x3": _svg('<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/><path d="M9 3v18"/><path d="M15 3v18"/>'),
        "move": _svg('<path d="m5 9-3 3 3 3"/><path d="m9 5 3-3 3 3"/><path d="m15 19-3 3-3-3"/><path d="m19 9 3 3-3 3"/><path d="M2 12h20"/><path d="M12 2v20"/>'),
        "minus": _svg('<path d="M5 12h14"/>'),
        "arrow-up-right": _svg('<path d="M7 17 17 7"/><path d="M7 7h10v10"/>'),
    }
)

_ICON_CACHE: dict[tuple[str, str, int, float], QIcon] = {}


def _rgba(color: QColor | str) -> str:
    resolved = QColor(color) if isinstance(color, str) else QColor(color)
    if not resolved.isValid():
        raise ValueError(f"invalid icon color: {color!r}")
    return resolved.name(QColor.NameFormat.HexArgb)


def _screen_dpr(screen) -> float | None:
    if screen is None:
        return None
    dpr = getattr(screen, "devicePixelRatio", None)
    if callable(dpr):
        value = float(dpr())
        return value if value > 0 else None
    return None


def _button_dpr(button: QAbstractButton) -> float:
    window = button.window()
    if window is not None:
        window_handle = window.windowHandle()
        if window_handle is not None:
            window_dpr = _screen_dpr(window_handle.screen())
            if window_dpr is not None:
                return window_dpr
    return _screen_dpr(QApplication.primaryScreen()) or 1.0


def icon(name: str, color: QColor | str, size: int = 16, dpr: float = 1.0) -> QIcon:
    """Render a bundled SVG icon at the requested logical size and DPR."""
    if name not in LUCIDE_SVG:
        raise KeyError(name)
    if size <= 0 or dpr <= 0:
        raise ValueError("size and dpr must be positive")
    rgba = _rgba(color)
    key = (name, rgba, int(size), round(float(dpr), 2))
    cached = _ICON_CACHE.get(key)
    if cached is not None:
        return cached

    svg = LUCIDE_SVG[name].replace("currentColor", rgba).encode("utf-8")
    renderer = QSvgRenderer(svg)
    if not renderer.isValid():
        raise ValueError(f"unable to render icon: {name}")
    backing_size = max(1, round(size * dpr))
    pixmap = QPixmap(backing_size, backing_size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    try:
        renderer.render(painter)
    finally:
        painter.end()
    pixmap.setDevicePixelRatio(dpr)
    rendered = QIcon(pixmap)
    _ICON_CACHE[key] = rendered
    return rendered


def apply_icon(
    button: QAbstractButton,
    name: str,
    color: QColor | str,
    *,
    icon_size: int = 16,
    hit_size: int = 36,
) -> None:
    """Apply a bundled icon while preserving the button's existing behavior."""
    button.setText("")
    button.setIcon(icon(name, color, icon_size, _button_dpr(button)))
    button.setIconSize(QSize(icon_size, icon_size))
    button.setFixedSize(hit_size, hit_size)
