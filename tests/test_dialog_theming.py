"""Dialog theming contracts for token-backed Qt surfaces."""

from __future__ import annotations

import os
from pathlib import Path
import re

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect, QGroupBox, QPushButton

from rendering.lighting import LightSettings
from ui.agent_settings import AgentSettingsDialog, InstructionsDialog, MemorySettingsDialog
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


def _assert_modal_shadow(dialog) -> None:
    effect = dialog.graphicsEffect()
    assert isinstance(effect, QGraphicsDropShadowEffect)
    offset_x, offset_y, blur, color = _shadow_effect_values("modal", "light")
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


def test_dialog_instances_leave_chrome_to_global_selectors() -> None:
    lighting = LightingDialog(LightSettings(), "光泽塑料")
    settings = AgentSettingsDialog()
    instructions = InstructionsDialog()
    memory = MemorySettingsDialog()

    for dialog in (lighting, settings, instructions, memory):
        assert "border:" not in dialog.styleSheet()
        assert "font-size" not in dialog.styleSheet()
        _assert_modal_shadow(dialog)

    groups = lighting.findChildren(QGroupBox)
    assert groups
    assert all(group.styleSheet() == "" for group in groups)
    assert lighting.material_combo.styleSheet() == ""
    assert settings.provider_combo.styleSheet() == ""


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
