"""UI 字体层级与局部样式回归测试。"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from ui.algebra_panel import AlgebraPanel
from ui.tokens import build_qss
from widgets.LightRotationWidget import LightRotationWidget


@pytest.fixture(scope="module", autouse=True)
def _application() -> QApplication:
    return QApplication.instance() or QApplication([])


def _source_path() -> Path:
    return Path(__file__).resolve().parents[1]


def test_algebra_panel_title_and_section_labels_follow_global_tokens() -> None:
    qss = build_qss("light")
    assert "#algebraTitle { color: #17212e; font-size: 15px; font-weight: 600; }" in qss
    assert "#sectionHeader { color: #3f4c5c; font-size: 11px; letter-spacing: 0.2px; }" in qss


def test_algebra_panel_uses_object_names_for_title_and_section_headers() -> None:
    panel = AlgebraPanel()
    title = panel.findChild(type(panel.status_label), "algebraTitle")
    assert title is not None
    section_headers = panel.findChildren(type(panel.status_label), "sectionHeader")
    assert section_headers


def test_light_rotation_widget_derives_fonts_from_application_font() -> None:
    source = (_source_path() / "widgets" / "LightRotationWidget.py").read_text(encoding="utf-8")
    assert 'QFont("Segoe UI"' not in source
    assert "QFont(self.font())" in source

    widget = LightRotationWidget()
    assert widget.font().weight() == QFont.Weight.Normal


def test_color_button_styles_only_set_swatch_background() -> None:
    source = (_source_path() / "ui" / "algebra_panel.py").read_text(encoding="utf-8")
    block = source.split("def _set_color_button")[1].split("def _emit_opacity")[0]
    assert 'setStyleSheet(f"background: {color};")' in source
    assert "border: 1px solid #687385" not in block
    assert "font:" not in block
