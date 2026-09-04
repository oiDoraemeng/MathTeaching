"""Generate semantic MathInput CSS variables from the shared design tokens."""

from __future__ import annotations

import json
from collections.abc import Mapping

from ui.tokens import TokenError, flatten_theme

TOKEN_VARIABLES = {
    "bg-panel": "bg_panel",
    "text-primary": "text_primary",
    "row-bg": "bg_elevated",
    "border": "border_default",
    "selected-bg": "accent_soft_bg",
    "selected-border": "accent_default",
    "btn-hover": "bg_elevated",
    "editing-bg": "bg_overlay",
    "focus": "accent_default",
    "toolbar-accent": "accent_default",
    "layer-fallback": "accent_default",
}

CONSTANTS = {
    "light": {"editing-border": "#e59b00", "toolbar-bg": "#2c2e2f", "toolbar-hover": "#eeeeee"},
    "dark": {"editing-border": "#e59b00", "toolbar-bg": "#2c2e2f", "toolbar-hover": "#3a3d40"},
}


def _branch(theme: str, tokens: Mapping[str, object] | None = None) -> dict[str, str]:
    if theme not in CONSTANTS:
        raise TokenError(f"unknown theme: {theme}")
    flat = flatten_theme(theme, tokens)
    values = {variable: str(flat[token]) for variable, token in TOKEN_VARIABLES.items()}
    values.update(CONSTANTS[theme])
    return values


def math_input_theme_css(tokens: Mapping[str, object] | None = None) -> str:
    """Return deterministic light/dark MathInput variable branches."""
    branches = []
    for theme, selector in (("light", ":root"), ("dark", '[data-theme="dark"]')):
        values = _branch(theme, tokens)
        lines = [f"{selector} {{"]
        lines.extend(f"  --mi-{name}: {values[name]};" for name in sorted(values))
        lines.append("}")
        branches.append("\n".join(lines))
    return "\n\n".join(branches) + "\n"


def math_input_theme_script(theme: str, tokens: Mapping[str, object] | None = None) -> str:
    """Return a self-contained script suitable for DocumentCreation injection."""
    if theme not in CONSTANTS:
        raise TokenError(f"unknown theme: {theme}")
    css = json.dumps(math_input_theme_css(tokens), ensure_ascii=False)
    selected = json.dumps(theme)
    return (
        "(() => {"
        f"window.__math3dTheme = {selected};"
        "const apply = () => {"
        "const root = document.documentElement; if (!root) return false;"
        "const theme = window.__math3dTheme || 'light';"
        "let style = document.getElementById('mi-theme-vars');"
        "if (!style) { style = document.createElement('style'); style.id = 'mi-theme-vars'; root.appendChild(style); }"
        f"if (style.textContent !== {css}) style.textContent = {css};"
        "root.dataset.theme = theme; root.style.colorScheme = theme;"
        "if (document.body) { document.body.dataset.theme = theme; document.body.style.colorScheme = theme; }"
        "document.querySelectorAll('math-field').forEach((field) => field.setAttribute('theme', theme));"
        "return true;"
        "};"
        "window.__math3dThemeObserver?.disconnect();"
        "window.__math3dThemeObserver = new MutationObserver(apply);"
        "window.__math3dThemeObserver.observe(document, { childList: true, subtree: true });"
        "apply();"
        "})();"
    )


def math_input_theme_runtime_script(theme: str) -> str:
    """Return a runtime script that synchronizes MathLive-owned theme state."""
    if theme not in CONSTANTS:
        raise TokenError(f"unknown theme: {theme}")
    selected = json.dumps(theme)
    return (
        "(() => {"
        f"window.__math3dTheme = {selected};"
        "const root = document.documentElement; if (!root) return;"
        "const theme = window.__math3dTheme;"
        "root.dataset.theme = theme; root.style.colorScheme = theme;"
        "if (document.body) { document.body.dataset.theme = theme; document.body.style.colorScheme = theme; }"
        "document.querySelectorAll('math-field').forEach((field) => field.setAttribute('theme', theme));"
        "})();"
    )
