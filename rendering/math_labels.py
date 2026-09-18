"""教学标注的数学排版工具。

VTK 的点标签只能绘制纯文本：既没有 LaTeX 渲染器，也无法控制单行对齐。这里负责三件事：

* 竖线替换：VTK 内置字体绘制 ``|`` 时既不保证可见，又会被标签放置器当成分隔符，
  于是显示层统一换成等宽且能稳定绘制的 ``I``（标注原始文本保持不变）。
* 堆叠分数：把 ``\\frac{a}{b}`` 排成“分子 / 分数线 / 分母”三行文本，并用真实字体度量
  计算前导空格，让分子与分母在分数线上居中。
* 字体选择：内置 Arial 没有中文字形，中文标注会整段绘制不出来，因此优先加载系统中
  带 CJK 字形的字体文件。
"""

from __future__ import annotations

import os
import re
from functools import lru_cache

import vtk

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

#: 优先使用带中文字形的字体文件。VTK 内置 Arial 缺少 CJK 字形，中文标注（含默认的
#: “标记”占位文字）会因为量不出字形宽度而整段不显示。
_LABEL_FONT_CANDIDATES = (
    # Windows
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyh.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
    r"C:\Windows\Fonts\Deng.ttf",
    # macOS
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    # Linux
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


def display_text(text: str, latex: str | None, *, font_size: int, bold: bool) -> str:
    """返回标注最终显示文本。

    带 ``latex`` 且能排成堆叠分数时优先使用排版结果；否则退回 ``text``，只做竖线替换。
    """
    if latex:
        stacked = stacked_latex(latex, font_size=font_size, bold=bold)
        if stacked is not None:
            return stacked
    return normalize_bars(text)


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
