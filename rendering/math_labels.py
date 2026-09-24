"""处理 VTK 教学标注的数学排版与中文字体降级。"""

from __future__ import annotations

import os
import re
from functools import lru_cache

import vtk

#: 案例窗格中的向量名、结果和公式统一使用此字号。
CASE_LABEL_FONT_SIZE = 15

_BAR_SOURCE = "|"
#: 显示用竖线字形：无衬线 ``I`` 与 ``|`` 等宽，且能稳定绘制。
BAR_GLYPH = "I"
#: 分数线用长破折号拼接而成。
_FRACTION_BAR = "\u2014"
#: 分数线两端相对分子/分母留出的空隙（像素）。
_BAR_PADDING = 8
#: 堆叠分数使用的换行符。
_LINE_BREAK = "\n"

_SQRT = "\u221a"
_FRACTION_COMMAND = "\\frac"
_SQRT_PATTERN = re.compile(r"\\sqrt\{([^{}]+)\}")
_LATEX_COMMAND_PATTERN = re.compile(r"\\[a-zA-Z]+")
_CJK_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
#: 将 ``x_1`` 等纯文本下标转换为 Unicode 字形。
_SUBSCRIPT_DIGITS = str.maketrans("0123456789", "\u2080\u2081\u2082\u2083\u2084\u2085\u2086\u2087\u2088\u2089")
_SUBSCRIPT_PATTERN = re.compile(r"(?<=[A-Za-z])_([0-9]+)")
#: 可视化层用 ``\genfrac`` 的空定界符形式堆叠矩阵行。
_GENFRAC_PREFIX = r"\genfrac{}{}{0}{}"
#: 可视化层在数学模式里用 ``\quad`` 分隔矩阵的列。
_COLUMN_GAP = r"\quad"
#: 矩阵数学文本：``$A=\left[...\right]$``。
_MATRIX_TEXT_PATTERN = re.compile(
    r"^\$(?P<name>.*?)=\\left\[(?P<body>.*)\\right\]\$$", re.DOTALL
)
# VTK's MathText backend does not understand LaTeX matrix environments such as
# ``pmatrix``/``bmatrix``.  Keep accepting those standard forms from MathLive,
# then lower them to the ``genfrac`` representation used by the canvas labels.
_MATRIX_ENV_PATTERN = re.compile(
    r"\\begin\{(?P<env>pmatrix|bmatrix|Bmatrix|vmatrix|Vmatrix|matrix)\}"
    r"(?P<body>.*?)"
    r"\\end\{(?P=env)\}",
    re.DOTALL,
)

#: VTK 内置字体缺少中文字形，优先选用系统中文字体。
_LABEL_FONT_CANDIDATES = (
    # Windows 字体
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyh.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
    r"C:\Windows\Fonts\Deng.ttf",
    # macOS 字体
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    # Linux 字体
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
)


@lru_cache(maxsize=1)
def label_font_file() -> str | None:
    """返回能稳定绘制中文的字体文件路径。

    找不到候选中文字体时返回 ``None``，调用方应退回 VTK 内置字体（此时中文仍无法显示）。
    """
    for path in _LABEL_FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


def normalize_bars(text: str) -> str:
    """把标注中的绝对值竖线换成 VTK 能稳定绘制的字形。"""
    return text.replace(_BAR_SOURCE, BAR_GLYPH)


def normalize_subscripts(text: str) -> str:
    """把纯文本数字下标转换为 Unicode 字形。"""
    return _SUBSCRIPT_PATTERN.sub(lambda match: match.group(1).translate(_SUBSCRIPT_DIGITS), text)


def display_text(text: str, latex: str | None, *, font_size: int, bold: bool) -> str:
    """优先使用 MathText，失败时降级为堆叠分数或纯文本。"""
    if latex:
        normalized_latex = normalize_matrix_environments(latex)
        rendered = vtk_math_text(normalized_latex, font_size=font_size, bold=bold)
        if rendered is not None:
            return rendered
        stacked = stacked_latex(normalized_latex, font_size=font_size, bold=bold)
        if stacked is not None:
            return stacked
    if not math_text_available():
        fallback_source = _math_text_candidate(latex or text)
        if text.startswith("$") and not (latex or "").strip():
            fallback_source = _math_text_candidate(text)
        fallback = fallback_matrix_text(fallback_source)
        if fallback is not None:
            return fallback
    # 此处只处理未进入数学排版分支的纯文本。
    return normalize_subscripts(normalize_bars(text))


@lru_cache(maxsize=1)
def math_text_available() -> bool:
    """VTK 的数学排版器依赖 matplotlib，缺失时 ``$...$`` 会被原样画出来。"""
    factory = getattr(vtk, "vtkMathTextUtilities", None)
    if factory is None:
        return False
    try:
        return bool(factory.GetInstance().IsAvailable())
    except Exception:  # pragma: no cover - 取决于 VTK 构建
        return False


def vtk_math_text(latex: str, *, font_size: int, bold: bool) -> str | None:
    """返回可安全渲染的 VTK MathText 文本。"""
    source = latex.strip()
    if not source or _CJK_PATTERN.search(source) or not math_text_available():
        return None
    candidate = _math_text_candidate(source)
    return candidate if _math_text_renders(candidate, font_size, bold) else None


def _math_text_candidate(source: str) -> str:
    """将公式规范为 VTK MathText 格式。"""
    source = normalize_matrix_environments(source)
    # MathText 会把竖线当作表格分隔符，改用等价命令。
    source = source.replace(r"\lvert", r"\vert").replace(r"\rvert", r"\vert")
    source = source.replace("|", r"\vert{}")
    if source.startswith("$$") and source.endswith("$$") and len(source) >= 4:
        return f"${source[2:-2].strip()}$"
    if "$" in source:
        return source
    return f"${source}$"


def normalize_matrix_environments(source: str) -> str:
    """Convert common LaTeX matrix environments to VTK-compatible MathText.

    MathLive emits ``\\begin{pmatrix}...\\end{pmatrix}`` for a matrix typed in
    the left algebra editor.  Matplotlib/VTK MathText rejects that environment
    even though it accepts the equivalent ``\\genfrac`` row stack, so normalize
    only the matrix environment and leave all other LaTeX untouched.
    """

    def replace(match: re.Match[str]) -> str:
        env = match.group("env")
        body = match.group("body").strip()
        raw_rows = re.split(r"\\\\\s*", body) if body else []
        rows: list[str] = []
        for raw_row in raw_rows:
            cells = [cell.strip() for cell in raw_row.split("&")]
            if not cells or any(not cell for cell in cells):
                return match.group(0)
            rows.append(r"\quad ".join(cells))
        if not rows or len({len(row.split(r"\quad ")) for row in rows}) != 1:
            return match.group(0)

        stacked = rows[-1]
        for row in reversed(rows[:-1]):
            stacked = rf"\genfrac{{}}{{}}{{0}}{{}}{{{row}}}{{{stacked}}}"
        delimiters = {
            "pmatrix": (r"\left(", r"\right)"),
            "bmatrix": (r"\left[", r"\right]"),
            "Bmatrix": (r"\left\{", r"\right\}"),
            "vmatrix": (r"\left|", r"\right|"),
            "Vmatrix": (r"\left\Vert", r"\right\Vert"),
            "matrix": ("", ""),
        }
        left, right = delimiters[env]
        return f"{left}{stacked}{right}"

    return _MATRIX_ENV_PATTERN.sub(replace, source)


@lru_cache(maxsize=512)
def _math_text_renders(candidate: str, font_size: int, bold: bool) -> bool:
    """检查 VTK MathText 是否接受该表达式。"""
    factory = getattr(vtk, "vtkMathTextUtilities", None)
    if factory is None:
        return False
    try:
        text_property = vtk.vtkTextProperty()
        text_property.SetFontSize(font_size)
        text_property.SetBold(bold)
        bounds = [0, 0, 0, 0]
        return bool(factory.GetInstance().GetBoundingBox(text_property, candidate, 72, bounds))
    except Exception:  # pragma: no cover - depends on the VTK/Matplotlib build
        return False


def fallback_matrix_text(text: str) -> str | None:
    """把矩阵数学文本降级成多行纯文本，供数学排版器不可用时使用。

    只识别可视化层生成的写法 ``$A=\\left[\\genfrac{}{}{0}{}{...}{...}\\right]$``，
    识别不了就返回 ``None``，由调用方原样显示。各行按列宽右对齐，尽量还原矩阵排版。
    """
    match = _MATRIX_TEXT_PATTERN.match(text)
    left, right = "[", "]"
    if match is None:
        # The normalizer preserves the delimiter selected by the user.  Keep
        # the no-MathText fallback useful for pmatrix/bmatrix and friends too.
        for left_token, right_token, left_glyph, right_glyph in (
            (r"\left(", r"\right)", "(", ")"),
            (r"\left\{", r"\right\}", "{", "}"),
            (r"\left|", r"\right|", "|", "|"),
            (r"\left\Vert", r"\right\Vert", "‖", "‖"),
            (r"\left[", r"\right]", "[", "]"),
        ):
            candidate = re.fullmatch(
                rf"\$(?P<name>.*?)={re.escape(left_token)}"
                rf"(?P<body>\\genfrac.*)"
                rf"{re.escape(right_token)}\$",
                text,
                re.DOTALL,
            )
            if candidate is not None:
                match = candidate
                left, right = left_glyph, right_glyph
                break
    if match is None:
        # A plain ``matrix`` environment has no delimiters after normalization.
        match = re.fullmatch(
            r"\$(?P<name>.*?)=(?P<body>\\genfrac.*)\$",
            text,
            re.DOTALL,
        )
    if match is None:
        return None
    rows = _matrix_rows(match.group("body"))
    if not rows or not any(rows):
        return None
    name = match.group("name")
    widths = [
        max((len(row[index]) for row in rows if index < len(row)), default=0)
        for index in range(max(len(row) for row in rows))
    ]
    indent = " " * (len(name) + 1)
    lines = [
        (
            f"{name}={left}{_matrix_row_text(row, widths)}{right}"
            if position == 0
            else f"{indent}{left}{_matrix_row_text(row, widths)}{right}"
        )
        for position, row in enumerate(rows)
    ]
    return _LINE_BREAK.join(lines)


def _matrix_row_text(row: list[str], widths: list[int]) -> str:
    """把一行的单元格按列宽右对齐，列间用两个空格分隔。"""
    return "  ".join(
        cell.rjust(widths[index]) for index, cell in enumerate(row)
    )


def _matrix_rows(body: str) -> list[list[str]] | None:
    """展开 ``\\genfrac`` 堆叠，返回每一行的单元格纯文本。"""
    if not body.startswith(_GENFRAC_PREFIX):
        cells = _matrix_cells(body)
        return None if cells is None else [cells]
    numerator, cursor = _group(body, len(_GENFRAC_PREFIX))
    denominator, cursor = _group(body, cursor)
    if numerator is None or denominator is None or body[cursor:].strip():
        return None
    upper = _matrix_rows(numerator)
    lower = _matrix_rows(denominator)
    if upper is None or lower is None:
        return None
    return upper + lower


def _matrix_cells(fragment: str) -> list[str] | None:
    """按列分隔符拆出一行的单元格，遇到无法识别的命令返回 ``None``。"""
    cells: list[str] = []
    for part in fragment.split(_COLUMN_GAP):
        plain = _plain_spacing(part).strip()
        if _LATEX_COMMAND_PATTERN.search(plain):
            return None
        cells.append(plain)
    return cells


def _plain_spacing(fragment: str) -> str:
    """把数学间距命令换回普通空格。"""
    return (
        fragment.replace(r"\quad ", "  ")
        .replace(r"\quad", "  ")
        .replace(r"\ ", " ")
        .replace(r"\,", " ")
    )


def stacked_latex(latex: str, *, font_size: int, bold: bool) -> str | None:
    """把含 ``\\frac{a}{b}`` 的 LaTeX 片段排成三行堆叠分数。

    只处理分数位于末尾且分子分母可解析的情况；出现无法识别的命令时返回 ``None``，
    由调用方退回原始文本。
    """
    index = latex.find(_FRACTION_COMMAND)
    if index < 0:
        return None
    prefix = _plain(latex[:index])
    numerator, cursor = _group(latex, index + len(_FRACTION_COMMAND))
    denominator, cursor = _group(latex, cursor)
    if prefix is None or numerator is None or denominator is None:
        return None
    if latex[cursor:].strip():
        return None
    plain_numerator = _plain(numerator)
    plain_denominator = _plain(denominator)
    if plain_numerator is None or plain_denominator is None:
        return None
    return _stacked_fraction(
        prefix=prefix,
        numerator=plain_numerator,
        denominator=plain_denominator,
        metrics=_metrics(font_size, bold),
    )


def _group(text: str, start: int) -> tuple[str | None, int]:
    """读取从 ``start`` 开始的 ``{...}`` 分组，返回分组内容与下一个位置。"""
    if start >= len(text) or text[start] != "{":
        return None, start
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1 : index], index + 1
    return None, start


def _plain(text: str) -> str | None:
    """把受支持的 LaTeX 片段转换为可直接绘制的字符，遇到未知命令返回 ``None``。"""
    rendered = _SQRT_PATTERN.sub(lambda match: _SQRT + match.group(1), text)
    if "{" in rendered or "}" in rendered:
        return None
    if _LATEX_COMMAND_PATTERN.search(rendered):
        return None
    return normalize_bars(rendered)


def _stacked_fraction(
    *, prefix: str, numerator: str, denominator: str, metrics: _TextMetrics
) -> str:
    """用实际字体度量把分子、分数线、分母排成三行，并在分数线上居中。"""
    prefix_advance = metrics.advance(prefix)
    numerator_width = metrics.width(numerator)
    denominator_width = metrics.width(denominator)
    bar_advance = max(1, metrics.advance(_FRACTION_BAR))
    needed = max(numerator_width, denominator_width) + _BAR_PADDING
    bar_width = max(1, int(round(needed / bar_advance))) * bar_advance

    def indent(part: str, part_width: int) -> int:
        target = prefix_advance + (bar_width - part_width) / 2.0
        offset = (target - metrics.bounds(part)[0]) / metrics.space_advance
        return max(0, int(offset + 0.5))

    return _LINE_BREAK.join(
        [
            " " * indent(numerator, numerator_width) + numerator,
            prefix + _FRACTION_BAR * (bar_width // bar_advance),
            " " * indent(denominator, denominator_width) + denominator,
        ]
    )


@lru_cache(maxsize=None)
def _metrics(font_size: int, bold: bool) -> _TextMetrics:
    return _TextMetrics(font_size=font_size, bold=bold)


class _TextMetrics:
    """按字体度量文本宽度，供多行标注手动对齐。

    标签由 ``vtkPointSetToLabelHierarchy`` 绘制，其字体度量与 ``vtkTextRenderer`` 一致，
    因此可以先用度量值算好空格数，再交给标签渲染。
    """

    def __init__(self, *, font_size: int, bold: bool) -> None:
        self._property = vtk.vtkTextProperty()
        font_file = label_font_file()
        # 度量必须与标签实际使用的字体保持一致，否则堆叠分数的居中会整体偏移。
        if font_file:
            self._property.SetFontFamily(vtk.VTK_FONT_FILE)
            self._property.SetFontFile(font_file)
        else:
            self._property.SetFontFamilyToArial()
        self._property.SetFontSize(font_size)
        self._property.SetBold(bold)
        self._renderer = vtk.vtkTextRenderer.GetInstance()

    def bounds(self, text: str) -> tuple[int, int]:
        """返回文本在像素坐标系里的左右边界，左侧可能为负，对应字形悬挑。"""
        window = [0, 0, 0, 0]
        self._renderer.GetBoundingBox(self._property, text, window, 72)
        return int(window[0]), int(window[1])

    def width(self, text: str) -> int:
        left, right = self.bounds(text)
        return right - left + 1

    def advance(self, text: str) -> int:
        """返回文本推进宽度，即下一个字形开始的位置。"""
        return self.bounds(text)[1] + 1

    @property
    def space_advance(self) -> int:
        return max(1, self.advance(" "))
