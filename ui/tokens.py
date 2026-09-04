"""Validated design-token loader shared by Qt UI and web tooling."""
import json
import re
from pathlib import Path
from typing import Literal
from collections.abc import Mapping

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QColor, QPainterPath, QRegion
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget

ThemeName = Literal["light", "dark"]
ShadowLevel = Literal["overlay", "modal"]
_ROOT = Path(__file__).resolve().parent.parent
_COLOR_GROUPS = {"bg", "text", "border", "accent", "status"}
_RGBA = re.compile(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(0|1|0?\.\d+)\s*\)")
_SHADOW_LAYER = re.compile(
    r"(-?\d+)(?:px)?\s+(-?\d+)(?:px)?\s+(\d+)(?:px)?\s+rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(0|1|0?\.\d+)\s*\)"
)

class TokenError(ValueError):
    pass

def _is_color(value: object) -> bool:
    if not isinstance(value, str): return False
    if QColor(value).isValid(): return True
    match = _RGBA.fullmatch(value)
    return bool(match and all(int(match.group(i)) <= 255 for i in (1, 2, 3)))

def _flatten(value: Mapping[str, object], prefix: str = "") -> dict[str, object]:
    result = {}
    for key, item in value.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(item, Mapping): result.update(_flatten(item, path))
        else: result[path] = item
    return result

def _flat_name(path: str) -> str:
    parts = path.split(".")
    if parts[:2] == ["font", "size"]: parts = parts[1:]
    elif parts[:2] == ["motion", "duration"]: parts = parts[1:]
    elif parts[:1] == ["motion"]: parts = parts[1:]
    return "_".join(parts)

def _validate(data: object) -> dict[str, object]:
    if not isinstance(data, Mapping): raise TokenError("token document must be an object")
    for section in ("font", "space", "radius", "motion", "themes"):
        if section not in data: raise TokenError(f"missing required section: {section}")
    sections = {name: data[name] for name in ("font", "space", "radius", "motion", "themes")}
    for name, value in sections.items():
        if not isinstance(value, Mapping): raise TokenError(f"{name} must be an object")
    if "size" not in sections["font"] or not isinstance(sections["font"]["size"], Mapping): raise TokenError("font.size must be an object")
    family_stack = sections["font"].get("family_stack")
    if (
        not isinstance(family_stack, list)
        or not family_stack
        or any(not isinstance(name, str) or not name.strip() for name in family_stack)
    ):
        raise TokenError("font.family_stack must be a non-empty string list")
    if "duration" not in sections["motion"] or not isinstance(sections["motion"]["duration"], Mapping): raise TokenError("motion.duration must be an object")
    themes = sections["themes"]
    if set(themes) != {"light", "dark"}: raise TokenError("themes must contain exactly light and dark")
    for mode in ("light", "dark"):
        if not isinstance(themes[mode], Mapping): raise TokenError(f"themes.{mode} must be an object")
    for name, group in (("font.size", sections["font"]["size"]), ("space", sections["space"]), ("radius", sections["radius"]), ("motion.duration", sections["motion"]["duration"])):
        for key, val in group.items():
            if not isinstance(val, int) or isinstance(val, bool) or val <= 0: raise TokenError(f"{name}.{key} must be a positive integer")
    light, dark = _flatten(themes["light"]), _flatten(themes["dark"])
    if set(light) != set(dark):
        missing_in_dark = sorted(set(light) - set(dark))
        missing_in_light = sorted(set(dark) - set(light))
        if missing_in_dark:
            raise TokenError(f"themes.dark.{missing_in_dark[0]}")
        raise TokenError(f"themes.light.{missing_in_light[0]}")
    for mode, theme in themes.items():
        for group in _COLOR_GROUPS:
            if group not in theme or not isinstance(theme[group], Mapping): raise TokenError(f"themes.{mode}.{group} must be an object")
            for key, val in theme[group].items():
                if not _is_color(val): raise TokenError(f"themes.{mode}.{group}.{key} is not a valid color")
        shadow = theme.get("shadow")
        if not isinstance(shadow, Mapping): raise TokenError(f"themes.{mode}.shadow must be an object")
        for key, val in shadow.items():
            if not isinstance(val, str) or not val.strip(): raise TokenError(f"themes.{mode}.shadow.{key} must be a non-empty string")
            if "rgba(" in val and val.count("rgba(") != len(re.findall(r"rgba\([^)]*\)", val)):
                raise TokenError(f"themes.{mode}.shadow.{key} has malformed color")
            for rgba in re.findall(r"rgba\([^)]*\)", val):
                if not _is_color(rgba): raise TokenError(f"themes.{mode}.shadow.{key} has invalid color")
    return data

def load_tokens(path: Path | None = None) -> dict[str, object]:
    source = Path(path) if path is not None else _ROOT / "design" / "tokens.json"
    try: data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc: raise TokenError(f"unable to read tokens: {exc}") from exc
    return _validate(data)


def font_family_stack(
    tokens: Mapping[str, object] | None = None,
) -> list[str]:
    source = dict(tokens or load_tokens())
    _validate(source)
    font = source["font"]
    assert isinstance(font, Mapping)
    return [str(name) for name in font["family_stack"]]


def _common_scalar_tokens(source: Mapping[str, object]) -> dict[str, object]:
    common = {
        key: value
        for key, value in source.items()
        if key not in {"$schema", "$comment", "themes"}
    }
    font = dict(common["font"])
    font.pop("family_stack", None)
    common["font"] = font
    return common

def flatten_theme(theme: ThemeName, tokens: Mapping[str, object] | None = None) -> dict[str, str | int]:
    if theme not in ("light", "dark"): raise TokenError(f"unknown theme: {theme}")
    if tokens is not None and not isinstance(tokens, Mapping): raise TokenError("tokens must be a mapping")
    source = dict(tokens or load_tokens())
    _validate(source)
    common = _flatten(_common_scalar_tokens(source))
    themed = _flatten(source["themes"][theme])
    return {_flat_name(key): value for key, value in {**common, **themed}.items()}

def build_qss(theme: ThemeName) -> str:
    """Render the global Qt stylesheet from the validated design tokens."""
    template_path = Path(__file__).with_name("styles") / "base.qss.in"
    from string import Template
    return Template(template_path.read_text(encoding="utf-8")).substitute(flatten_theme(theme))

RadiusLevel = Literal["sm", "md", "lg"]


def radius(level: RadiusLevel, theme: ThemeName = "light") -> int:
    """Return the pixel radius for a semantic radius token."""
    value = flatten_theme(theme).get(f"radius_{level}")
    if not isinstance(value, int):
        raise TokenError(f"unknown radius token: {level}")
    return value


class _RoundedMaskFilter(QObject):
    """Keep a rounded mask in sync with its widget's size.

    Qt clips a QSS ``border-radius`` only when it owns the paint surface. A
    frameless top-level window, or a child that Qt force-promotes to a native
    window because it is a sibling of the native VTK interactor, is painted
    straight into platform backing store — the corners then expose whatever the
    compositor left there, which is black on Windows. An explicit mask makes the
    rounding real instead of merely painted.
    """

    def __init__(self, widget: QWidget, corner_radius: int) -> None:
        super().__init__(widget)
        self._radius = corner_radius
        self._widget = widget
        widget.installEventFilter(self)
        self.apply()

    def apply(self) -> None:
        widget = self._widget
        width, height = widget.width(), widget.height()
        if width <= 0 or height <= 0:
            return
        path = QPainterPath()
        path.addRoundedRect(0, 0, width, height, self._radius, self._radius)
        widget.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self._widget and event.type() in (
            QEvent.Type.Resize,
            QEvent.Type.Show,
        ):
            self.apply()
        return False


def apply_rounded_overlay(
    widget: QWidget, level: RadiusLevel = "md", theme: ThemeName = "light"
) -> None:
    """Make a widget's token radius render as real rounded corners.

    Top-level frameless chrome opts into ``WA_TranslucentBackground`` so Qt
    composites the rounded QSS background over a transparent surface, which
    keeps the corners antialiased. Child overlays have no window of their own,
    so translucency does not apply to them; they get a resize-tracking mask
    instead, which is the only way to clip a natively promoted child.
    """
    if widget.isWindow():
        widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        return
    existing = widget.findChild(_RoundedMaskFilter)
    if existing is not None:
        existing.deleteLater()
    _RoundedMaskFilter(widget, radius(level, theme))


def _shadow_effect_values(level: ShadowLevel, theme: ThemeName) -> tuple[int, int, int, QColor]:
    """Map the strongest CSS shadow layer to Qt's single drop-shadow effect."""
    shadow = str(flatten_theme(theme)[f"shadow_{level}"])
    matches = _SHADOW_LAYER.findall(shadow)
    if not matches:
        raise TokenError(f"themes.{theme}.shadow.{level} cannot be mapped to a Qt shadow")
    x, y, blur, red, green, blue, alpha = matches[-1]
    color = QColor(int(red), int(green), int(blue))
    color.setAlphaF(float(alpha))
    return int(x), int(y), int(blur), color

def apply_drop_shadow(widget: QWidget, level: ShadowLevel, theme: ThemeName = "light") -> None:
    """Apply a token-backed drop shadow to floating Qt chrome."""
    offset_x, offset_y, blur, color = _shadow_effect_values(level, theme)
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(offset_x, offset_y)
    effect.setColor(color)
    widget.setGraphicsEffect(effect)
