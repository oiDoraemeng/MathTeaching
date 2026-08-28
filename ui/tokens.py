"""Validated design-token loader shared by Qt UI and web tooling."""
import json
import re
from pathlib import Path
from typing import Literal, Mapping

from PySide6.QtGui import QColor

ThemeName = Literal["light", "dark"]
_ROOT = Path(__file__).resolve().parent.parent
_COLOR_GROUPS = {"bg", "text", "border", "accent", "status"}
_RGBA = re.compile(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(0|1|0?\.\d+)\s*\)")

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
    if parts[:2] == ["font", "size"]: parts = parts[2:]
    elif parts[:2] == ["motion", "duration"]: parts = parts[2:]
    elif parts[:1] == ["motion"]: parts = parts[1:]
    return "_".join(parts)

def _validate(data: object) -> dict[str, object]:
    if not isinstance(data, dict): raise TokenError("token document must be an object")
    for section in ("font", "space", "radius", "motion", "themes"):
        if section not in data: raise TokenError(f"missing required section: {section}")
    try: themes = data["themes"]
    except KeyError: raise TokenError("missing themes")
    if not isinstance(themes, dict) or set(themes) != {"light", "dark"}: raise TokenError("themes must contain exactly light and dark")
    for name, group in (("font.size", data["font"]["size"]), ("space", data["space"]), ("radius", data["radius"]), ("motion.duration", data["motion"]["duration"])):
        if not isinstance(group, dict): raise TokenError(f"{name} must be an object")
        for key, val in group.items():
            if not isinstance(val, int) or isinstance(val, bool) or val <= 0: raise TokenError(f"{name}.{key} must be a positive integer")
    light, dark = _flatten(themes["light"]), _flatten(themes["dark"])
    if set(light) != set(dark): raise TokenError("themes light and dark must have identical leaf keys")
    for mode, theme in themes.items():
        for group in _COLOR_GROUPS:
            if not isinstance(theme.get(group), dict): raise TokenError(f"themes.{mode}.{group} must be an object")
            for key, val in theme[group].items():
                if not _is_color(val): raise TokenError(f"themes.{mode}.{group}.{key} is not a valid color")
    return data

def load_tokens(path: Path | None = None) -> dict[str, object]:
    source = Path(path) if path is not None else _ROOT / "design" / "tokens.json"
    try: data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc: raise TokenError(f"unable to read tokens: {exc}") from exc
    return _validate(data)

def flatten_theme(theme: ThemeName, tokens: Mapping[str, object] | None = None) -> dict[str, str | int]:
    if theme not in ("light", "dark"): raise TokenError(f"unknown theme: {theme}")
    source = dict(tokens or load_tokens())
    common = _flatten({key: value for key, value in source.items() if key not in {"$schema", "$comment", "themes"}})
    themed = _flatten(source["themes"][theme])
    return {_flat_name(key): value for key, value in {**common, **themed}.items()}
