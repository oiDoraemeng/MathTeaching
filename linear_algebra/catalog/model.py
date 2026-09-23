from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal


@dataclass(frozen=True)
class SourceAnchor:
    heading_path: tuple[str, ...]
    heading_level: int
    occurrence: int = 1


@dataclass(frozen=True)
class LessonEntry:
    id: str
    chapter_number: int
    section_id: str
    title: str
    source_path: tuple[str, str, str]
    source_anchor: SourceAnchor
    explanation_id: str
    visualization_id: str
    required_capabilities: tuple[str, ...]
    # 目录显示名覆盖。讲义标题原样保留在 source_path / source_anchor 里用于锚定
    # Markdown 原文（改动它会破坏来源校验），个别小节在软件目录里要用更短的
    # 名字时只覆盖显示名，例如 2.9 合并后只讲线性无关与秩。
    display_title: str = ""


@dataclass(frozen=True)
class LessonNode:
    id: str
    kind: Literal["chapter", "section", "topic"]
    title: str
    order: tuple[int, ...]
    parent_id: str | None
    children: tuple[str, ...]
    source_path: tuple[str, ...]
    explanation_id: str | None
    visualization_id: str | None
    required_capabilities: tuple[str, ...]


_INLINE_MATH_SYMBOLS: tuple[tuple[str, str], ...] = (
    (r"\times", "×"),
    (r"\cdot", "·"),
    (r"\div", "÷"),
    (r"\pm", "±"),
    (r"\neq", "≠"),
    (r"\leq", "≤"),
    (r"\geq", "≥"),
    (r"\rightarrow", "→"),
    (r"\to", "→"),
    (r"\det", "det"),
)

_SUBSCRIPT_TRANSLATION = str.maketrans("0123456789+-", "₀₁₂₃₄₅₆₇₈₉₊₋")


def display_math_text(text: str) -> str:
    """Convert short TeX-like UI labels to readable plain text.

    Tab bars and the application status bar do not render TeX.  Feeding them
    lecture source such as ``$\\boldsymbol v_1$`` exposes markup instead of a
    student-facing label, so normalize only the small inline subset used by
    those controls.
    """

    rendered = str(text or "")
    for command, symbol in _INLINE_MATH_SYMBOLS:
        rendered = rendered.replace(command, symbol)
    rendered = re.sub(
        r"\\(?:boldsymbol|mathbf|vec)\s*\{([^{}]+)\}",
        r"\1",
        rendered,
    )
    rendered = re.sub(
        r"\\(?:boldsymbol|mathbf|vec)\s+([A-Za-z])",
        r"\1",
        rendered,
    )

    def subscript(match: re.Match[str]) -> str:
        digits = match.group(1) or match.group(2) or ""
        return digits.translate(_SUBSCRIPT_TRANSLATION)

    rendered = re.sub(r"_\{([0-9+-]+)\}|_([0-9]+)", subscript, rendered)
    return rendered.replace("$", "").strip()


def display_heading(heading: str) -> str:
    """Return a lecture heading rendered for display instead of source anchoring.

    Lecture headings keep their verbatim TeX so the catalog can anchor them back
    to the Markdown source (``2.5 矩阵 $\\times$ 向量（核心节）``).  The lecture
    tree shows the same heading, so the raw commands have to be replaced by the
    symbols they stand for before they reach the user.
    """

    return display_math_text(heading)


def topic_entry(
    *,
    topic_id: str,
    chapter_number: int,
    section_id: str,
    title: str,
    source_path: tuple[str, str, str],
    heading_path: tuple[str, ...],
    heading_level: int,
    required_capabilities: tuple[str, ...],
    occurrence: int = 1,
    display_title: str = "",
) -> LessonEntry:
    return LessonEntry(
        id=topic_id,
        chapter_number=chapter_number,
        section_id=section_id,
        title=title,
        source_path=source_path,
        source_anchor=SourceAnchor(heading_path, heading_level, occurrence),
        explanation_id=f"explain.{topic_id}",
        visualization_id=f"draw.{topic_id}",
        required_capabilities=required_capabilities,
        display_title=display_title,
    )
