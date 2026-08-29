from copy import deepcopy
import inspect
import json
import os
from pathlib import Path
import re
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect, QHBoxLayout, QWidget
from PySide6.QtCore import Qt
from unittest.mock import MagicMock

from models.scene_mode import SceneAppearance, SceneMode
from ui.designer_window import MainWindow
from ui.lighting_dialog import LightingDialog
from ui.scene_settings import SceneSettingsPanel
from ui.tokens import TokenError, _shadow_effect_values, build_qss, flatten_theme, load_tokens
from ui.two_d_tools import TwoDGeometryToolbar
from rendering.lighting import LightSettings

AGENT_SELECTOR_ALLOWLIST = {"#agentsidebar", "#agentsidebarweb", "#agentbutton"}
RETIRED_COLORS = ("#d9dde3", "#d0d7df", "#cbd3dd", "#dfe3e8", "#e0e5ea", "#3794ff", "#006ab1")
_SELECTOR_PREAMBLE = re.compile(r"(?:\A|\})\s*([^{}]+?)\s*\{", re.DOTALL)


def _selectors(qss: str) -> list[str]:
    return [
        selector.strip()
        for preamble in _SELECTOR_PREAMBLE.findall(qss)
        for selector in preamble.split(",")
        if selector.strip()
    ]


def _normalized_qss(value: str) -> str:
    return "\n".join(line.rstrip() for line in value.splitlines()).rstrip() + "\n"


def _block_for_selector(qss: str, selector: str) -> str:
    match = re.search(rf"([^{{}}]*{re.escape(selector)}[^{{}}]*)\{{([^{{}}]+)\}}", qss)
    assert match is not None
    return match.group(2)


def _assert_shadow(widget: QWidget, level: str, theme: str = "light") -> None:
    effect = widget.graphicsEffect()
    assert isinstance(effect, QGraphicsDropShadowEffect)
    offset_x, offset_y, blur, color = _shadow_effect_values(level, theme)
    assert effect.blurRadius() == blur
    assert effect.xOffset() == offset_x
    assert effect.yOffset() == offset_y
    assert effect.color().getRgb() == color.getRgb()


@pytest.fixture(scope="module", autouse=True)
def _application() -> QApplication:
    return QApplication.instance() or QApplication([])

@pytest.mark.parametrize("theme", ["light", "dark"])
def test_qss_template_is_fully_substituted(theme: str) -> None:
    qss = build_qss(theme)
    assert "$" not in qss
    assert "#viewportToolbar" in qss
    assert "QLineEdit:focus" in qss
    assert "min-height: 32px" in qss


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_qss_has_required_and_no_retired_content(theme: str) -> None:
    qss = build_qss(theme)
    agent_selectors = {
        agent_selector.lower()
        for selector in _selectors(qss)
        for agent_selector in re.findall(r"#agent[\w-]*", selector, flags=re.IGNORECASE)
    }

    assert "#scenesettingspanel" in qss.lower()
    assert agent_selectors <= AGENT_SELECTOR_ALLOWLIST
    assert not any(color in qss.lower() for color in RETIRED_COLORS)


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_overlay_and_dialog_chrome_use_token_metrics(theme: str) -> None:
    flat = flatten_theme(theme)
    qss = build_qss(theme)
    for selector in ("#viewportToolbar", "#twoDGeometryToolbar", "#twoDLineFlyout", "#sceneSettingsPanel"):
        block = _block_for_selector(qss, selector)
        assert f"background: {flat['bg_overlay']}" in block
        assert f"border: 1px solid {flat['border_subtle']}" in block
        assert f"border-radius: {flat['radius_md']}px" in block

    dialog_block = _block_for_selector(qss, "QDialog")
    assert f"border-radius: {flat['radius_lg']}px" in dialog_block


def test_floating_widget_construction_names_and_token_shadows(monkeypatch) -> None:
    class FakeInteractor:
        def __init__(self, parent: QWidget) -> None:
            self.interactor = QWidget(parent)
            self.iren = None

        def setFocusPolicy(self, policy: Qt.FocusPolicy) -> None:
            self.interactor.setFocusPolicy(policy)

    monkeypatch.setattr("ui.designer_window.QtInteractor", FakeInteractor)
    shell = QWidget()
    viewport_host = QWidget(shell)
    viewport_host.setObjectName("viewportHost")
    QHBoxLayout(shell).addWidget(viewport_host)
    window = object.__new__(MainWindow)
    window.window = shell
    window.scene_mode = SceneMode.THREE_D
    window.scene_appearances = {
        SceneMode.TWO_D: SceneAppearance(),
        SceneMode.THREE_D: SceneAppearance(),
    }
    window._update_geometry_history_controls = MagicMock()

    MainWindow._configure_viewport(window)
    toolbar = TwoDGeometryToolbar(viewport_host)
    settings = SceneSettingsPanel(viewport_host)
    dialog = LightingDialog(LightSettings(), "光泽塑料", shell)

    widgets = (
        (window.viewport_toolbar, "viewportToolbar", "overlay"),
        (toolbar, "twoDGeometryToolbar", "overlay"),
        (toolbar.line_flyout, "twoDLineFlyout", "overlay"),
        (settings, "sceneSettingsPanel", "overlay"),
        (dialog, "lightingDialog", "modal"),
    )
    for widget, object_name, level in widgets:
        assert widget.objectName() == object_name
        _assert_shadow(widget, level)


def test_main_window_apply_style_has_no_inline_qss() -> None:
    source = inspect.getsource(MainWindow._apply_style)
    assert "setStyleSheet(build_qss(" in source
    assert not re.search(r"setStyleSheet\(\s*['\"]", source)


@pytest.mark.parametrize(
    ("label", "mutate", "error_path"),
    [
        ("missing theme leaf", lambda data: data["themes"]["dark"]["bg"].pop("scene"), r"^themes\.dark\.bg\.scene$"),
        ("mismatched theme key sets", lambda data: data["themes"]["dark"]["bg"].__setitem__("extra", "#fff"), r"^themes\.light\.bg\.extra$"),
        ("zero font size", lambda data: data["font"]["size"].__setitem__("title", 0), "font.size.title"),
        ("negative duration", lambda data: data["motion"]["duration"].__setitem__("normal", -1), "motion.duration.normal"),
        ("invalid color", lambda data: data["themes"]["light"]["bg"].__setitem__("scene", "not-a-color"), "themes.light.bg.scene"),
    ],
)
def test_malformed_token_matrix(tmp_path, label, mutate, error_path):
    data = deepcopy(load_tokens())
    mutate(data)
    path = tmp_path / f"{label.replace(' ', '_')}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(TokenError, match=error_path):
        load_tokens(path)


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_qss_matches_normalized_snapshot(theme: str) -> None:
    snapshot = (Path(__file__).parent / "snapshots" / f"base-{theme}.qss").read_text(encoding="utf-8")
    assert _normalized_qss(build_qss(theme)) == _normalized_qss(snapshot)

def test_light_and_dark_themes_have_identical_leaf_keys():
    tokens = load_tokens(); light = flatten_theme("light", tokens); dark = flatten_theme("dark", tokens)
    themed = {key for key in light if key.startswith(("bg_", "text_", "border_", "accent_", "status_", "shadow_"))}
    assert themed == {key for key in dark if key.startswith(("bg_", "text_", "border_", "accent_", "status_", "shadow_"))}
    assert light["bg_scene"] == "#f4f6f9"; assert dark["bg_scene"] == "#1e1f23"

def test_invalid_color_fails_fast(tmp_path):
    data = deepcopy(load_tokens()); data["themes"]["dark"]["accent"]["default"] = "not-a-color"
    path = tmp_path / "tokens.json"; path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(TokenError, match="themes.dark.accent.default"): load_tokens(path)

@pytest.mark.parametrize("path_key", ["font", "space", "radius", "motion", "themes"])
def test_missing_or_wrong_sections_fail(tmp_path, path_key):
    data = deepcopy(load_tokens()); data[path_key] = None
    path = tmp_path / "tokens.json"; path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(TokenError): load_tokens(path)

def test_flattened_names_and_invalid_theme():
    flat = flatten_theme("light")
    assert flat["size_title"] == 15 and flat["duration_normal"] == 150
    assert flat["easing_out"] and flat["shadow_overlay"]
    with pytest.raises(TokenError): flatten_theme("sepia")

def test_theme_shape_and_shadow_validation(tmp_path):
    data = deepcopy(load_tokens()); data["themes"]["dark"]["shadow"]["overlay"] = ""
    path = tmp_path / "tokens.json"; path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(TokenError, match="shadow.overlay"): load_tokens(path)

@pytest.mark.parametrize("shadow", ["0 1px rgba(0,0,0,.4", "0 1px rgba(0,0,0,2)"])
def test_malformed_shadow_color_fails(tmp_path, shadow):
    data = deepcopy(load_tokens()); data["themes"]["dark"]["shadow"]["overlay"] = shadow
    path = tmp_path / "tokens.json"; path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(TokenError, match="shadow.overlay"): load_tokens(path)
