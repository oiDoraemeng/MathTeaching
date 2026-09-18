"""Bundled Lucide-style SVG icons for Qt controls."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Literal

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QAbstractButton, QApplication, QWidget

from ui.tokens import ThemeName, flatten_theme


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
        "circle-filled": _svg('<circle cx="12" cy="12" r="7" fill="currentColor" stroke="none"/>'),
        "circle-outline": _svg('<circle cx="12" cy="12" r="7"/>'),
        "slash": _svg('<path d="m17 5-10 14"/>'),
        "pen-line": _svg('<path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4Z"/>'),
        "vector": _svg('<circle cx="5" cy="19" r="2" fill="currentColor" stroke="none"/><path d="M6.5 17.5 17 7"/><path d="M11 7h6v6"/>'),
        "angle": _svg('<path d="M5 19h13"/><path d="M5 19 16 8"/><path d="M10.5 19a5.5 5.5 0 0 0-3.9-1.6"/>'),
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
        "minus-dashed": _svg('<path d="M4 12h4"/><path d="M10 12h4"/><path d="M16 12h4"/>'),
        "arrow-up-right": _svg('<path d="M7 17 17 7"/><path d="M7 7h10v10"/>'),
        "mouse-pointer-2": _svg('<path d="m4 4 7.07 17 2.51-7.39L21 11.07Z"/>'),
        "corner-down-right": _svg('<path d="m15 10 5 5-5 5"/><path d="M4 4v7a4 4 0 0 0 4 4h12"/>'),
        "hexagon": _svg('<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/>'),
        "grid-2x2": _svg('<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 12h18"/><path d="M12 3v18"/>'),
        "layout-1": _svg('<rect width="18" height="18" x="3" y="3" rx="2"/>'),
        "layout-2": _svg('<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M12 3v18"/>'),
        "layout-3": _svg('<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M12 3v18"/><path d="M12 12h9"/>'),
        "layout-4": _svg('<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M12 3v18"/><path d="M3 12h18"/>'),
        "square-dashed": _svg('<path d="M5 3a2 2 0 0 0-2 2"/><path d="M19 3a2 2 0 0 1 2 2"/><path d="M21 19a2 2 0 0 1-2 2"/><path d="M5 21a2 2 0 0 1-2-2"/><path d="M9 3h1"/><path d="M9 21h1"/><path d="M14 3h1"/><path d="M14 21h1"/><path d="M3 9v1"/><path d="M21 9v1"/><path d="M3 14v1"/><path d="M21 14v1"/>'),
        "square": _svg('<rect width="18" height="18" x="3" y="3" rx="2"/>'),
        "x": _svg('<path d="M6 6l12 12"/><path d="M18 6 6 18"/>'),
        "sun": _svg('<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>'),
        "moon": _svg('<path d="M20.5 14.5A8.5 8.5 0 0 1 9.5 3.5 8.5 8.5 0 1 0 20.5 14.5Z"/>'),
        "monitor": _svg('<rect width="18" height="12" x="3" y="3" rx="2"/><path d="M8 21h8"/><path d="M12 15v6"/>'),
        "chevrons-down": _svg('<path d="m7 7 5 5 5-5"/><path d="m7 13 5 5 5-5"/>'),
        "chevrons-up": _svg('<path d="m17 11-5-5-5 5"/><path d="m17 17-5-5-5 5"/>'),
    }
)

_ICON_CACHE: dict[tuple[str, str, int, float], QIcon] = {}


def _svg_color(color: QColor | str) -> str:
    """Return an SVG-compatible ``#RRGGBB`` string.

    Qt's ``HexArgb`` form (``#AARRGGBB``) is *not* valid SVG/CSS, and Qt's own
    SVG parser silently drops the stroke when it sees one, rendering a fully
    transparent icon. Alpha is applied via painter opacity instead.
    """
    resolved = QColor(color)
    if not resolved.isValid():
        raise ValueError(f"invalid icon color: {color!r}")
    return resolved.name(QColor.NameFormat.HexRgb)


def _svg_alpha(color: QColor | str) -> float:
    resolved = QColor(color)
    if not resolved.isValid():
        raise ValueError(f"invalid icon color: {color!r}")
    return float(resolved.alphaF())


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
    stroke = _svg_color(color)
    alpha = _svg_alpha(color)
    key = (name, f"{stroke}@{alpha:.3f}", int(size), round(float(dpr), 2))
    cached = _ICON_CACHE.get(key)
    if cached is not None:
        return cached

    svg = LUCIDE_SVG[name].replace("currentColor", stroke).encode("utf-8")
    renderer = QSvgRenderer(svg)
    if not renderer.isValid():
        raise ValueError(f"unable to render icon: {name}")
    backing_size = max(1, round(size * dpr))
    pixmap = QPixmap(backing_size, backing_size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    try:
        if alpha < 1.0:
            painter.setOpacity(alpha)
        renderer.render(painter)
    finally:
        painter.end()
    pixmap.setDevicePixelRatio(dpr)
    rendered = QIcon(pixmap)
    _ICON_CACHE[key] = rendered
    return rendered


IconRole = Literal["default", "active", "muted"]

_ROLE_TOKENS: Mapping[IconRole, str] = MappingProxyType(
    {
        "default": "text_secondary",
        "active": "accent_default",
        "muted": "text_muted",
    }
)

# Buttons remember how they were tinted so a theme switch can re-render them.
# QSS cannot restyle a QIcon, so the pixmap has to be rebuilt by hand.
_ICON_STATE_PROPERTY = "_kiro_icon_state"


def icon_color(theme: ThemeName = "light", role: IconRole = "default") -> str:
    """Return the token icon color for a theme and semantic role."""
    if role not in _ROLE_TOKENS:
        raise KeyError(role)
    value = flatten_theme(theme)[_ROLE_TOKENS[role]]
    return str(value)


def retint_icons(root: QWidget, theme: ThemeName) -> int:
    """Re-render every token-tinted icon under ``root`` for ``theme``.

    Returns the number of buttons repainted so callers can assert on it.
    """
    repainted = 0
    candidates: list[QAbstractButton] = []
    if isinstance(root, QAbstractButton):
        candidates.append(root)
    candidates.extend(root.findChildren(QAbstractButton))
    for button in candidates:
        state = button.property(_ICON_STATE_PROPERTY)
        if not state:
            continue
        name, role, icon_size = state
        if name not in LUCIDE_SVG:
            continue
        button.setIcon(icon(name, icon_color(theme, role), icon_size, _button_dpr(button)))
        button.setIconSize(QSize(icon_size, icon_size))
        repainted += 1
    return repainted


def apply_icon(
    button: QAbstractButton,
    name: str,
    color: QColor | str,
    *,
    icon_size: int = 16,
    hit_size: int = 36,
    role: IconRole = "default",
) -> None:
    """Apply a bundled icon while preserving the button's existing behavior."""
    button.setText("")
    button.setIcon(icon(name, color, icon_size, _button_dpr(button)))
    button.setIconSize(QSize(icon_size, icon_size))
    button.setFixedSize(hit_size, hit_size)
    setter = getattr(button, "setProperty", None)
    if callable(setter):
        setter(_ICON_STATE_PROPERTY, (name, role, icon_size))
