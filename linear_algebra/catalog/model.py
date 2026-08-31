from __future__ import annotations

from dataclasses import dataclass
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
    )

