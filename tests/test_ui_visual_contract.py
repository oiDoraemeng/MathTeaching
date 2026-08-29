"""Static visual contract checks for the Qt and Web surfaces."""

from pathlib import Path
import re

from ui.tokens import build_qss


ROOT = Path(__file__).parents[1]


def test_qss_removes_region_divider_and_adds_focus_ring() -> None:
    qss = build_qss("light")
    assert "border-right" not in qss
    assert ":focus-visible" in qss
    assert re.search(r":focus-visible[^{}]*\{[^{}]*2px solid \#?", qss)


def test_layer_rows_are_cards_with_color_strip_and_states() -> None:
    html = (ROOT / "MathInputWidget" / "formula_list.html").read_text(encoding="utf-8")
    assert ".layer-row::before" in html
    assert "width: 4px" in html
    assert "border-radius: 8px" in html
    assert ".layer-row:hover" in html
    assert ".layer-row.selected" in html
    assert "const eyeIcon" in html
    assert "const eyeOffIcon" in html
    assert "visible ? eyeIcon() : eyeOffIcon()" in html
    assert "const settingsIcon" in html
    assert "settings.innerHTML = settingsIcon()" in html
    assert "settings.textContent = '\\u22ee'" not in html


def test_control_dimensions_use_only_three_grades() -> None:
    sources = [
        ROOT / "ui" / "designer_window.py",
        ROOT / "ui" / "algebra_panel.py",
        ROOT / "ui" / "two_d_tools.py",
        ROOT / "ui" / "scene_settings.py",
        ROOT / "ui" / "agent_sidebar.py",
        ROOT / "widgets" / "LightRotationWidget.py",
        ROOT / "MathInputWidget" / "formula_list.html",
    ]
    text = "\n".join(path.read_text(encoding="utf-8") for path in sources)
    assert "setFixedSize(38" not in text
    assert "setFixedHeight(30" not in text
    assert "width: 40px" not in text
    assert "height: 40px" not in text
    assert "min-height: 38px" not in text


def test_motion_contract_is_explicit() -> None:
    designer = (ROOT / "ui" / "designer_window.py").read_text(encoding="utf-8")
    algebra = (ROOT / "ui" / "algebra_panel.py").read_text(encoding="utf-8")
    web = (ROOT / "ui" / "agent_web" / "src" / "styles" / "layout.css").read_text(encoding="utf-8")
    assert "setDuration(200)" in designer
    assert "OutCubic" in designer
    assert "setDuration(150)" in algebra
    assert "150ms" in web or ".15s" in web
    assert "@media (prefers-reduced-motion: reduce)" in web
