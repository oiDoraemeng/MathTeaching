import json
import re

import pytest

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
