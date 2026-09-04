import json
import re

import pytest

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from ui.tokens import TokenError, flatten_theme
from MathInputWidget.theme_tokens import math_input_theme_css, math_input_theme_runtime_script, math_input_theme_script
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
    assert "colorScheme" in script
    assert "document.body" in script
    assert "math-field" in script
    assert "MutationObserver" in script
    assert json.dumps(math_input_theme_css()) in script


def test_math_input_runtime_script_syncs_mathlive_owned_theme_state() -> None:
    script = math_input_theme_runtime_script("dark")
    assert 'root.style.colorScheme = theme' in script
    assert 'document.body.dataset.theme = theme' in script
    assert "setAttribute('theme', theme)" in script


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
    assert 'root.style.colorScheme = theme' in view.page_value.javascript[-1]
    assert 'document.body.dataset.theme = theme' in view.page_value.javascript[-1]
    url_calls = view.set_url_calls
    bridge.set_theme("light")
    assert 'const theme = "light"' in view.page_value.javascript[-1]
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
    assert 'const theme = "dark"' in view.page_value.javascript[-1]


def test_formula_cell_scrolls_long_content_without_visible_scrollbar() -> None:
    html = (ROOT / "MathInputWidget" / "formula_list.html").read_text(encoding="utf-8")
    assert re.search(r"\.formula-cell\s*\{[^}]*overflow-x:\s*auto", html, re.S)
    assert re.search(r"\.formula-cell\s*\{[^}]*scrollbar-width:\s*none", html, re.S)
    assert re.search(r"\.formula-cell::?-webkit-scrollbar\s*\{[^}]*display:\s*none", html, re.S)
    assert re.search(r"html, body\s*\{[^}]*overflow-x:\s*hidden", html, re.S)
    row_block = re.search(r"\.layer-row\s*\{([^}]*)\}", html, re.S)
    assert row_block is not None and "white-space: nowrap" not in row_block.group(1)


@pytest.mark.parametrize("filename", ["mathlive.html", "inline_formula_overlay.html", "formula_preview.html"])
def test_math_input_document_uses_theme_variables(filename: str) -> None:
    html = (ROOT / "MathInputWidget" / filename).read_text(encoding="utf-8")
    assert "var(--mi-bg-panel," in html or "var(--mi-editing-bg," in html
    assert "var(--mi-text-primary," in html
    assert "var(--mi-focus," in html
    assert "--selection-background-color: var(--mi-selected-bg" in html
    assert "color-scheme: light" not in html


def test_formula_preview_fallback_has_no_inline_theme_color() -> None:
    source = (ROOT / "MathInputWidget" / "formula_preview.py").read_text(encoding="utf-8")
    assert "#1f2937" not in source
    assert 'setObjectName("formulaPreviewFallback")' in source


def test_formula_list_user_copy_is_chinese() -> None:
    html = (ROOT / "MathInputWidget" / "formula_list.html").read_text(encoding="utf-8")
    for expected in ("隐藏函数", "显示函数", "函数显示与采样设置", "公式", "几何对象", "删除"):
        assert expected in html
    for retired in ("Hide function", "Show function", "Function display and sampling settings", 'aria-label="Formula"', 'aria-label="Geometry object"', ">Delete<"):
        assert retired not in html


def test_agent_web_user_copy_has_no_retired_english_labels() -> None:
    root = ROOT / "ui" / "agent_web" / "src" / "components"
    files = ["HistoryView.tsx", "SettingsView.tsx", "AttachmentActions.tsx", "SessionTabs.tsx", "Timeline.tsx", "ModeSelector.tsx"]
    retired = ("History", "No conversations", "Hidden", "Back to conversation", "Settings", "Skills", "Memory", "Rules", "Add image", "Add file")
    for filename in files:
        source = (root / filename).read_text(encoding="utf-8")
        for phrase in retired:
            assert not re.search(rf'(?:"|>)\s*{re.escape(phrase)}\s*(?:<|"|`)', source)
