"""Icon tinting contracts across themes.

`ui-design-system` spec, "Icon tinting per theme": when the effective theme
changes, Qt icon buttons must re-render their SVG icons in the token icon
colors for that theme. Hardcoded light-theme greys stay dark on a dark panel,
so assert the colors come from tokens and that a theme switch re-tints.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QToolButton

from ui.icons import apply_icon, icon_color, retint_icons
from ui.tokens import flatten_theme


@pytest.fixture(scope="module", autouse=True)
def _application() -> QApplication:
    return QApplication.instance() or QApplication([])


def _dominant(button: QToolButton):
    image = button.icon().pixmap(16, 16).toImage()
    return max(
        (image.pixelColor(x, y) for y in range(16) for x in range(16)),
        key=lambda color: color.alpha(),
    )


def test_icon_color_comes_from_theme_tokens() -> None:
    for theme in ("light", "dark"):
        flat = flatten_theme(theme)
        assert icon_color(theme) == flat["text_secondary"]
        assert icon_color(theme, "active") == flat["accent_default"]
    assert icon_color("light") != icon_color("dark")


def test_retint_icons_repaints_for_dark_theme() -> None:
    button = QToolButton()
    apply_icon(button, "settings-2", icon_color("light"))
    light_pixel = _dominant(button)

    retint_icons(button, "dark")
    dark_pixel = _dominant(button)

    assert dark_pixel.alpha() > 0, "icon must remain visible after retint"
    assert dark_pixel.name() != light_pixel.name(), "theme switch must change the tint"
    assert dark_pixel.lightness() > light_pixel.lightness(), "dark theme needs a lighter icon"


def test_retint_walks_nested_buttons() -> None:
    from PySide6.QtWidgets import QVBoxLayout, QWidget

    host = QWidget()
    layout = QVBoxLayout(host)
    buttons = []
    for name in ("plus", "ellipsis", "eye"):
        button = QToolButton(host)
        apply_icon(button, name, icon_color("light"))
        layout.addWidget(button)
        buttons.append(button)

    before = [_dominant(button).name() for button in buttons]
    retint_icons(host, "dark")
    after = [_dominant(button).name() for button in buttons]
    assert before != after
    assert all(_dominant(button).alpha() > 0 for button in buttons)


def test_no_hardcoded_icon_colors_remain_in_ui_sources() -> None:
    root = Path(__file__).resolve().parents[1]
    offenders: list[str] = []
    for relative in (
        "ui/designer_window.py",
        "ui/two_d_tools.py",
        "ui/algebra_panel.py",
        "ui/status_bar.py",
    ):
        source = (root / relative).read_text(encoding="utf-8")
        for match in re.finditer(r"apply_icon\((?:[^()]|\([^()]*\))*\)", source):
            if re.search(r"#[0-9a-fA-F]{6}", match.group(0)):
                offenders.append(f"{relative}: {match.group(0)[:70]}")
    assert not offenders, "apply_icon must take a token color, not a literal: " + "; ".join(offenders)
