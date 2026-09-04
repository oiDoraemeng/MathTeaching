import json
import re

import pytest

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from ui.tokens import TokenError, flatten_theme
from MathInputWidget.theme_tokens import math_input_theme_css, math_input_theme_script

EXPECTED_VARIABLES = {
    "--mi-bg-panel", "--mi-text-primary", "--mi-row-bg", "--mi-border",
    "--mi-selected-bg", "--mi-selected-border", "--mi-btn-hover", "--mi-editing-bg",
    "--mi-editing-border", "--mi-focus", "--mi-toolbar-bg", "--mi-toolbar-accent",
    "--mi-toolbar-hover", "--mi-layer-fallback",
}


def test_math_input_css_has_complete_matching_theme_branches() -> None:
    css = math_input_theme_css()
    light, dark = css.split('[data-theme="dark"]', 1)
    assert set(re.findall(r"--mi-[a-z-]+", light)) == EXPECTED_VARIABLES
    assert set(re.findall(r"--mi-[a-z-]+", dark)) == EXPECTED_VARIABLES


def test_math_input_css_uses_design_token_values() -> None:
    css = math_input_theme_css()
    assert f"--mi-bg-panel: {flatten_theme('light')['bg_panel']}" in css
    assert f"--mi-bg-panel: {flatten_theme('dark')['bg_panel']}" in css
    assert f"--mi-focus: {flatten_theme('dark')['accent_default']}" in css


def test_math_input_theme_script_is_document_creation_safe() -> None:
    script = math_input_theme_script("dark")
    assert "mi-theme-vars" in script
    assert "dataset.theme" in script
    assert json.dumps(math_input_theme_css()) in script


def test_math_input_theme_script_rejects_unknown_theme() -> None:
    with pytest.raises(TokenError):
        math_input_theme_script("sepia")


def test_formula_list_uses_variables_with_light_fallbacks() -> None:
    html = (ROOT / "MathInputWidget" / "formula_list.html").read_text(encoding="utf-8")
    required = {
        "var(--mi-bg-panel, #ffffff)",
        "var(--mi-text-primary, #1f2937)",
        "var(--mi-row-bg, #f9fafb)",
        "var(--mi-border, #cfd8e1)",
        "var(--mi-selected-bg, #eaf2fd)",
        "var(--mi-selected-border, #8ab4f8)",
        "var(--mi-btn-hover, #eef2f5)",
        "var(--mi-editing-bg, #fffdf4)",
        "var(--mi-focus, #2f7ebd)",
    }
    assert required <= {match.group(0) for match in re.finditer(r"var\(--mi-[^)]+\)", html)}
    assert "--selection-background-color: var(--mi-selected-bg" in html
    assert "--contains-highlight-background-color:" in html

    for declaration in re.findall(r"(?:background|color|border(?:-color)?):\s*([^;]+)", html):
        if declaration.strip().startswith("var("):
            continue
        assert declaration.strip() not in {"#ffffff", "#1f2937", "#cfd8e1", "#eaf2fd", "#8ab4f8", "#eef2f5", "#fffdf4", "#2f7ebd"}


def test_formula_list_variables_are_emitted_by_theme_generator() -> None:
    html = (ROOT / "MathInputWidget" / "formula_list.html").read_text(encoding="utf-8")
    referenced = set(re.findall(r"var\((--mi-[a-z-]+)", html))
    emitted = set(re.findall(r"(--mi-[a-z-]+):", math_input_theme_css()))
    assert referenced <= emitted
    assert all("," in match.group(0) for match in re.finditer(r"var\(--mi-[^)]+\)", html))
