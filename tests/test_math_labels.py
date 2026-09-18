"""教学标注的数学排版测试：竖线替换与堆叠分数。"""

from __future__ import annotations

from rendering import math_labels

_FONT_SIZE = 14


def test_normalize_bars_replaces_abs_bars_with_renderable_glyph() -> None:
    assert math_labels.normalize_bars("|a| = 5") == "IaI = 5"


def test_display_text_without_latex_only_normalizes_bars() -> None:
    assert (
        math_labels.display_text("|p| = 4/√5", None, font_size=_FONT_SIZE, bold=True)
        == "IpI = 4/√5"
    )


def test_display_text_stacks_latex_fraction_into_three_lines() -> None:
    rendered = math_labels.display_text(
        "|p| = 4/√5",
        r"|p| = \frac{4}{\sqrt{5}}",
        font_size=_FONT_SIZE,
        bold=True,
    )

    lines = rendered.split("\n")
    assert len(lines) == 3
    assert lines[0].strip() == "4"
    assert lines[1].startswith("IpI = ") and "—" in lines[1]
    assert lines[2].strip() == "√5"


def test_stacked_latex_rejects_unsupported_commands() -> None:
    assert math_labels.stacked_latex(r"\frac{1}{\alpha}", font_size=_FONT_SIZE, bold=True) is None


def test_stacked_latex_returns_none_without_fraction() -> None:
    assert math_labels.stacked_latex(r"|a| = \sqrt{5}", font_size=_FONT_SIZE, bold=True) is None
