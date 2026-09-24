"""教学标注的数学排版测试：竖线替换与堆叠分数。"""

from __future__ import annotations

from rendering import math_labels

_FONT_SIZE = 14


def test_normalize_bars_replaces_abs_bars_with_renderable_glyph() -> None:
    assert math_labels.normalize_bars("|a| = 5") == "IaI = 5"


def test_normalize_subscripts_replaces_letter_digits_with_unicode_glyphs() -> None:
    assert math_labels.normalize_subscripts("x_1") == "x₁"
    assert math_labels.normalize_subscripts("Ax_2") == "Ax₂"
    assert math_labels.normalize_subscripts("e_12") == "e₁₂"
    # Unicode 下标字形只覆盖数字；字母下标保持原样，避免误改成读不出来的字形。
    assert math_labels.normalize_subscripts("alpha_n") == "alpha_n"
    # No letter immediately before the underscore → leave untouched.
    assert math_labels.normalize_subscripts("_1") == "_1"
    assert math_labels.normalize_subscripts("Col(A)") == "Col(A)"
    assert math_labels.normalize_subscripts("x_") == "x_"


def test_display_text_without_latex_only_normalizes_bars() -> None:
    assert (
        math_labels.display_text("|p| = 4/√5", None, font_size=_FONT_SIZE, bold=True)
        == "IpI = 4/√5"
    )


def test_display_text_promotes_letter_subscripts_for_4_1_labels() -> None:
    # 4.1 节柱空间里的向量标签；ASCII 写法保留在数据层，渲染后变成数学下标。
    assert (
        math_labels.display_text("x_1", None, font_size=_FONT_SIZE, bold=True)
        == "x₁"
    )
    assert (
        math_labels.display_text("Ax_2", None, font_size=_FONT_SIZE, bold=True)
        == "Ax₂"
    )
    assert (
        math_labels.display_text("Ax_3", None, font_size=_FONT_SIZE, bold=True)
        == "Ax₃"
    )


def test_display_text_stacks_latex_fraction_into_three_lines() -> None:
    rendered = math_labels.display_text(
        "|p| = 4/√5",
        r"|p| = \frac{4}{\sqrt{5}}",
        font_size=_FONT_SIZE,
        bold=True,
    )

    if math_labels.math_text_available():
        assert rendered == r"$\vert{}p\vert{} = \frac{4}{\sqrt{5}}$"
        return
    lines = rendered.split("\n")
    assert len(lines) == 3
    assert lines[0].strip() == "4"
    assert lines[1].startswith("IpI = ") and "—" in lines[1]
    assert lines[2].strip() == "√5"


def test_display_text_wraps_supported_latex_for_vtk_mathtext() -> None:
    rendered = math_labels.display_text(
        "rho gh, x1",
        r"p=\rho gh,\quad x_1=\frac{1}{\sqrt{2}}",
        font_size=_FONT_SIZE,
        bold=True,
    )

    if math_labels.math_text_available():
        assert rendered == r"$p=\rho gh,\quad x_1=\frac{1}{\sqrt{2}}$"
    else:
        assert rendered == "rho gh, x1"


def test_display_text_normalizes_display_math_delimiters() -> None:
    rendered = math_labels.display_text(
        "x squared",
        r"$$x^2$$",
        font_size=_FONT_SIZE,
        bold=True,
    )

    if math_labels.math_text_available():
        assert rendered == r"$x^2$"
    else:
        assert rendered == "x squared"


def test_display_text_keeps_cjk_latex_on_plain_text_path() -> None:
    assert (
        math_labels.display_text(
            "中文 English 标记",
            r"\text{中文 English 标记}",
            font_size=_FONT_SIZE,
            bold=True,
        )
        == "中文 English 标记"
    )


def test_stacked_latex_rejects_unsupported_commands() -> None:
    assert math_labels.stacked_latex(r"\frac{1}{\alpha}", font_size=_FONT_SIZE, bold=True) is None


def test_stacked_latex_returns_none_without_fraction() -> None:
    assert math_labels.stacked_latex(r"|a| = \sqrt{5}", font_size=_FONT_SIZE, bold=True) is None


def test_matrix_label_text_paints_rows_inside_tall_brackets() -> None:
    from linear_algebra.visualizations.common import matrix_label_text

    assert (
        matrix_label_text("A", [[2, 0], [0, 1]])
        == r"$A=\left[\genfrac{}{}{0}{}{2\quad 0}{0\quad 1}\right]$"
    )
    assert (
        matrix_label_text("B", [[-3, -5], [2, 3]])
        == r"$B=\left[\genfrac{}{}{0}{}{-3\quad -5}{\ 2\quad \ 3}\right]$"
    )


def test_display_text_keeps_math_text_for_the_math_renderer() -> None:
    text = r"$A=\left[\genfrac{}{}{0}{}{2\quad 0}{0\quad 1}\right]$"

    rendered = math_labels.display_text(text, None, font_size=_FONT_SIZE, bold=True)

    if math_labels.math_text_available():
        assert rendered == text
    else:
        assert rendered == "A=[2  0]\n  [0  1]"


def test_display_text_normalizes_standard_matrix_environments() -> None:
    """MathLive matrix input must render as a matrix instead of raw LaTeX."""
    source = r"A=\begin{pmatrix}1&2\\3&4\end{pmatrix}"
    normalized = math_labels.normalize_matrix_environments(source)

    assert normalized == r"A=\left(\genfrac{}{}{0}{}{1\quad 2}{3\quad 4}\right)"
    rendered = math_labels.display_text("matrix", source, font_size=_FONT_SIZE, bold=True)
    if math_labels.math_text_available():
        assert rendered == rf"${normalized}$"
    else:
        assert "1" in rendered and "4" in rendered
        assert "\\begin" not in rendered


def test_fallback_matrix_text_rebuilds_plain_literal() -> None:
    assert (
        math_labels.fallback_matrix_text(r"$A=\left[\genfrac{}{}{0}{}{2\quad 0}{0\quad 1}\right]$")
        == "A=[2  0]\n  [0  1]"
    )


def test_fallback_matrix_text_expands_nested_rows_with_padding() -> None:
    text = r"$T=\left[\genfrac{}{}{0}{}{1\quad 2}{\genfrac{}{}{0}{}{-3\quad 4}{5\quad 6}}\right]$"

    assert math_labels.fallback_matrix_text(text) == "T=[ 1  2]\n  [-3  4]\n  [ 5  6]"


def test_fallback_matrix_text_ignores_texts_it_cannot_parse() -> None:
    assert math_labels.fallback_matrix_text(r"$A=\left[\alpha\right]$") is None
    assert math_labels.fallback_matrix_text("A=[2 0]") is None
