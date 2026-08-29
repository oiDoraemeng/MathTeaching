"""Dialog theming contracts for token-backed Qt surfaces."""

from __future__ import annotations

import os
from pathlib import Path
import re
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect, QGroupBox, QPushButton, QWidget

from rendering.lighting import LightSettings
from ui.agent_settings import AgentSettingsDialog, InstructionsDialog, MemorySettingsDialog
from ui.designer_window import MainWindow
from ui.lighting_dialog import LightingDialog
from ui.tokens import _shadow_effect_values, build_qss, flatten_theme


@pytest.fixture(scope="module", autouse=True)
def _application() -> QApplication:
    return QApplication.instance() or QApplication([])


def _source_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _block_for_selector(qss: str, selector: str) -> str:
    match = re.search(rf"([^{{}}]*{re.escape(selector)}[^{{}}]*)\{{([^{{}}]+)\}}", qss)
    assert match is not None
    return match.group(2)


def _style_declarations(button: QPushButton) -> dict[str, str]:
    declarations: dict[str, str] = {}
    for item in button.styleSheet().split(";"):
        if ":" not in item:
            continue
        key, value = item.split(":", 1)
        declarations[key.strip()] = value.strip()
    return declarations


def _assert_modal_shadow(dialog, theme: str = "light") -> None:
    effect = dialog.graphicsEffect()
    assert isinstance(effect, QGraphicsDropShadowEffect)
    offset_x, offset_y, blur, color = _shadow_effect_values("modal", theme)
    assert effect.blurRadius() == blur
    assert effect.xOffset() == offset_x
    assert effect.yOffset() == offset_y
    assert effect.color().getRgb() == color.getRgb()


def _module_source() -> str:
    root = _source_root()
    sources = [
        root / "ui" / "lighting_dialog.py",
        root / "ui" / "agent_settings.py",
        root / "widgets" / "LightRotationWidget.py",
    ]
    return "\n".join(path.read_text(encoding="utf-8") for path in sources)


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_dialog_qss_uses_tokenized_modal_and_groupbox_rules(theme: str) -> None:
    flat = flatten_theme(theme)
    qss = build_qss(theme)

    dialog_block = _block_for_selector(qss, "QDialog")
    assert f"background: {flat['bg_overlay']}" in dialog_block
    assert f"border: 1px solid {flat['border_subtle']}" in dialog_block
    assert f"border-radius: {flat['radius_lg']}px" in dialog_block

    group_block = _block_for_selector(qss, "QGroupBox")
    assert f"color: {flat['text_primary']}" in group_block
    assert f"border: 1px solid {flat['border_default']}" in group_block
    assert f"border-radius: {flat['radius_md']}px" in group_block

    title_block = _block_for_selector(qss, "QGroupBox::title")
    assert f"color: {flat['text_secondary']}" in title_block
    assert f"background: {flat['bg_overlay']}" in title_block


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_dialog_instances_pick_up_effective_theme_on_creation(theme: str) -> None:
    window = QWidget()
    window.effective_theme = theme
    sidebar = QWidget(window)

    lighting = LightingDialog(LightSettings(), "光泽塑料", window, effective_theme=theme)
    settings = AgentSettingsDialog(window, effective_theme=theme)
    instructions = InstructionsDialog(settings, effective_theme=theme)
    memory = MemorySettingsDialog(sidebar, effective_theme=theme)

    for dialog in (lighting, settings, instructions, memory):
        assert "border:" not in dialog.styleSheet()
        assert "font-size" not in dialog.styleSheet()
        _assert_modal_shadow(dialog, theme)

    settings.set_effective_theme("dark" if theme == "light" else "light")
    instructions.set_effective_theme("dark" if theme == "light" else "light")
    memory.set_effective_theme("dark" if theme == "light" else "light")
    lighting.set_effective_theme("dark" if theme == "light" else "light")
    for dialog in (lighting, settings, instructions, memory):
        _assert_modal_shadow(dialog, "dark" if theme == "light" else "light")

    groups = lighting.findChildren(QGroupBox)
    assert groups
    assert all(group.styleSheet() == "" for group in groups)
    assert lighting.material_combo.styleSheet() == ""
    assert settings.provider_combo.styleSheet() == ""


def test_main_window_apply_style_refreshes_existing_modal_dialogs() -> None:
    window = object.__new__(MainWindow)
    window.effective_theme = "dark"
    window.window = QWidget()
    window.window.effective_theme = "dark"
    window.viewport_toolbar = None
    window.two_d_geometry_toolbar = None
    window.scene_settings_panel = None
    window._lighting_dialog = LightingDialog(LightSettings(), "光泽塑料", window.window, effective_theme="light")
    window._agent_settings_dialog = AgentSettingsDialog(window.window, effective_theme="light")
    window._agent_settings_dialog._instructions_dialog = InstructionsDialog(window._agent_settings_dialog, effective_theme="light")
    window.agent_sidebar = SimpleNamespace(
        _memory_dialog=MemorySettingsDialog(QWidget(window.window), effective_theme="light")
    )
    window.algebra_panel = SimpleNamespace(sync_overlay_theme=lambda _theme: None)

    MainWindow._apply_style(window)

    for dialog in (
        window._lighting_dialog,
        window._agent_settings_dialog,
        window._agent_settings_dialog._instructions_dialog,
        window.agent_sidebar._memory_dialog,
    ):
        _assert_modal_shadow(dialog, "dark")


def test_lighting_color_swatches_keep_only_fill_and_semantic_foreground() -> None:
    settings = LightSettings()
    settings.key["color"] = (1.0, 1.0, 1.0)
    settings.fill["color"] = (0.0, 0.0, 0.0)
    dialog = LightingDialog(settings, "光泽塑料")

    light_swatch = _style_declarations(dialog._color_buttons["key"])
    dark_swatch = _style_declarations(dialog._color_buttons["fill"])

    assert light_swatch == {
        "background": "#ffffff",
        "color": str(flatten_theme("dark")["text_on_accent"]),
    }
    assert dark_swatch == {
        "background": "#000000",
        "color": str(flatten_theme("light")["text_on_accent"]),
    }


def test_dialog_and_widget_sources_do_not_reintroduce_local_font_chrome() -> None:
    combined = _module_source()

    assert "font-size: 22pt" not in combined
    assert 'QFont("Segoe UI"' not in combined
    assert "font-family: Segoe UI" not in combined
    assert "border: 1px solid #687385" not in combined
