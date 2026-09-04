import json
import re

import pytest

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from ui.tokens import TokenError, flatten_theme
from MathInputWidget.theme_tokens import math_input_theme_css, math_input_theme_script
from MathInputWidget.theme_bridge import ThemeBridge
from PySide6.QtWebEngineCore import QWebEngineScript

EXPECTED_VARIABLES = {
    "--mi-bg-panel", "--mi-text-primary", "--mi-row-bg", "--mi-border",
    "--mi-selected-bg", "--mi-selected-border", "--mi-btn-hover", "--mi-editing-bg",
    "--mi-editing-border", "--mi-focus", "--mi-toolbar-bg", "--mi-toolbar-accent",
    "--mi-toolbar-hover", "--mi-layer-fallback",
}


class _FakeScripts:
    def __init__(self) -> None:
        self.inserted = []

    def insert(self, script) -> None:
        self.inserted.append(script)


class _FakePage:
    def __init__(self) -> None:
        self.scripts_value = _FakeScripts()
        self.javascript = []

    def scripts(self):
        return self.scripts_value

    def runJavaScript(self, source: str) -> None:
        self.javascript.append(source)


class _FakeView:
    def __init__(self) -> None:
        self.page_value = _FakePage()
        self.set_url_calls = []

    def page(self):
        return self.page_value


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


def test_theme_bridge_caches_until_load_then_switches_without_reload() -> None:
    view = _FakeView()
    bridge = ThemeBridge(view, "light")
    bridge.install("dark")
    assert view.page_value.scripts_value.inserted[0].injectionPoint() == QWebEngineScript.InjectionPoint.DocumentCreation
    bridge.set_theme("dark")
    assert view.page_value.javascript == []
    bridge.on_load_finished(True)
    assert view.page_value.javascript[-1] == 'document.documentElement.dataset.theme = "dark";'
    url_calls = view.set_url_calls
    bridge.set_theme("light")
    assert view.page_value.javascript[-1] == 'document.documentElement.dataset.theme = "light";'
    assert view.set_url_calls == url_calls


def test_theme_bridge_rejects_invalid_theme_and_retains_failed_load_state() -> None:
    view = _FakeView()
    bridge = ThemeBridge(view, "light")
    with pytest.raises(TokenError):
        bridge.set_theme("sepia")
    bridge.set_theme("dark")
    bridge.on_load_finished(False)
    assert view.page_value.javascript == []
    bridge.on_load_finished(True)
    assert view.page_value.javascript[-1].endswith('"dark";')


def test_formula_cell_scrolls_long_content_without_visible_scrollbar() -> None:
    html = (ROOT / "MathInputWidget" / "formula_list.html").read_text(encoding="utf-8")
    assert re.search(r"\.formula-cell\s*\{[^}]*overflow-x:\s*auto", html, re.S)
    assert re.search(r"\.formula-cell\s*\{[^}]*scrollbar-width:\s*none", html, re.S)
    assert re.search(r"\.formula-cell::?-webkit-scrollbar\s*\{[^}]*display:\s*none", html, re.S)
    assert re.search(r"html, body\s*\{[^}]*overflow-x:\s*hidden", html, re.S)
    row_block = re.search(r"\.layer-row\s*\{([^}]*)\}", html, re.S)
    assert row_block is not None and "white-space: nowrap" not in row_block.group(1)
