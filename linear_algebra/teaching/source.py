"""Stable, heading-aware source contexts for the checked-in lecture."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re

from linear_algebra.catalog.model import LessonEntry, SourceAnchor


_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_CHAPTER = re.compile(r"^第(\d+)章(?:\s|[^A-Za-z0-9]|$)")
_SECTION = re.compile(r"^\d+\.\d+(?:\s|$)")
_EXCLUDED = ("自检", "练习", "挑战", "课后练习", "练习题", "挑战题")
_MERGED_TOPIC_PATHS: dict[str, tuple[tuple[str, ...], ...]] = {
    # 4.2 的目录项合并 4.2.1 与 4.2.2，但不能顺手把同一父节后面的 4.2.3、4.2.4
    # 纳入来源。路径仍是讲义原文标题，供锚点与哈希复核。
    "ch04.dependence.redundancy": (
        ("第4章 线性空间、线性无关与线性变换（全书核心枢纽）", "4.2 线性组合、线性相关与线性无关", "4.2.1 生成集 Span"),
        ("第4章 线性空间、线性无关与线性变换（全书核心枢纽）", "4.2 线性组合、线性相关与线性无关", "4.2.2 线性相关与线性无关"),
    ),
}


@dataclass(frozen=True)
class SourceOccurrence:
    """A heading occurrence with bounded and adjacent source context."""

    path: tuple[str, ...]
    level: int
    occurrence: int
    title: str
    start_line: int
    end_line: int
    text: str
    adjacent_before: str
    adjacent_after: str


def is_excluded_heading(title: str) -> bool:
    """Return whether a heading denotes exercises, checks, or challenges."""
    return _contains_excluded(title.strip(), _EXCLUDED)


def extract_heading_occurrences(
    source: str, chapter_range: tuple[int, int] = (4, 8)
) -> tuple[SourceOccurrence, ...]:
    """Extract heading occurrences for a chapter range at any Markdown depth."""
    if len(chapter_range) != 2 or chapter_range[0] > chapter_range[1]:
        raise ValueError("chapter_range must be an increasing pair")
    sections = parse_heading_sections(source)
    selected = [
        section for section in sections
        if section.path and (match := _CHAPTER.match(section.path[0]))
        and chapter_range[0] <= int(match.group(1)) <= chapter_range[1]
        and not is_excluded_heading(section.title)
    ]
    lines = source.replace("\r\n", "\n").splitlines()
    occurrences: list[SourceOccurrence] = []
    for index, section in enumerate(selected):
        previous = next((item for item in reversed(selected[:index]) if item.path[:-1] == section.path[:-1]), None)
        following = next((item for item in selected[index + 1:] if item.path[:-1] == section.path[:-1]), None)
        before = ""
        if previous is not None and previous.path[:-1] == section.path[:-1]:
            before = _adjacent_non_heading(previous.text)
        after = ""
        if following is not None and following.path[:-1] == section.path[:-1]:
            after = _adjacent_non_heading(following.text)
        occurrences.append(SourceOccurrence(section.path, section.level, section.occurrence, section.title, section.start_line, section.end_line, _without_excluded_blocks(section.text, _EXCLUDED), before, after))
    return tuple(occurrences)


def _adjacent_non_heading(text: str) -> str:
    return next((line.strip() for line in text.splitlines() if line.strip() and _HEADING.match(line) is None), "")


@dataclass(frozen=True)
class SourceSpan:
    """One non-overlapping selected heading block from the lecture."""

    id: str
    heading_path: tuple[str, ...]
    start_line: int
    end_line: int
    fingerprint: str
    text: str


@dataclass(frozen=True)
class SourceContext:
    """The stable source material selected for one catalog topic."""

    topic_id: str
    source_path: tuple[str, ...]
    heading_path: tuple[str, ...]
    heading_level: int
    occurrence: int
    excerpt: str
    source_hash: str
    spans: tuple[SourceSpan, ...]
    neighboring_titles: tuple[str, ...]


@dataclass(frozen=True)
class HeadingSection:
    """A lecture heading and its direct text range.

    ``start_line`` and ``end_line`` support diagnostics only. Stable identity is
    represented by ``path``, ``occurrence``, and the normalized text fingerprint.
    """

    path: tuple[str, ...]
    level: int
    occurrence: int
    title: str
    start_line: int
    end_line: int
    text: str


def normalize_source_text(text: str) -> str:
    """Normalize line endings and whitespace before hashing source text."""
    lines = (" ".join(line.split()) for line in text.replace("\r\n", "\n").split("\n"))
    return "\n".join(line for line in lines if line)


def parse_heading_sections(source: str) -> tuple[HeadingSection, ...]:
    """Parse lecture headings using the catalog's chapter-aware path semantics.

    The lecture sometimes makes sections level-two headings. The active chapter
    therefore remains a synthetic root so those sections retain their expected
    conceptual parent, independent of Markdown level inconsistencies.
    """
    lines = source.replace("\r\n", "\n").split("\n")
    active_chapter: str | None = None
    stack: list[tuple[int, str]] = []
    counts: Counter[tuple[str, ...]] = Counter()
    headings: list[tuple[tuple[str, ...], int, int, str, int]] = []

    for line_number, line in enumerate(lines, start=1):
        match = _HEADING.match(line)
        if match is None:
            continue
        level = len(match.group(1))
        title = match.group(2).strip()
        if _CHAPTER.match(title):
            active_chapter = title
            stack = [(1, title)]
        elif active_chapter is None:
            continue
        else:
            if level <= 3 and _SECTION.match(title):
                stack = [(1, active_chapter)]
            else:
                stack = [(item_level, item_title) for item_level, item_title in stack if item_level < level]
            if not stack or stack[0][1] != active_chapter:
                stack.insert(0, (1, active_chapter))
            stack.append((level, title))
        path = tuple(item[1] for item in stack)
        counts[path] += 1
        headings.append((path, level, counts[path], title, line_number))

    sections: list[HeadingSection] = []
    for index, (path, level, occurrence, title, start_line) in enumerate(headings):
        next_start = next(
            (
                candidate_start
                for candidate_path, _, _, _, candidate_start in headings[index + 1 :]
                if not _is_strict_descendant(candidate_path, path)
            ),
            len(lines) + 1,
        )
        end_line = next_start - 1
        text = "\n".join(lines[start_line - 1 : end_line]).strip()
        sections.append(HeadingSection(path, level, occurrence, title, start_line, end_line, text))
    return tuple(sections)


def _is_strict_descendant(candidate_path: tuple[str, ...], path: tuple[str, ...]) -> bool:
    return len(candidate_path) > len(path) and candidate_path[: len(path)] == path


class LectureSourceRepository:
    """Read deterministic, bounded contexts from a Markdown lecture source."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def context_for(self, entry: LessonEntry) -> SourceContext:
        source = self.path.read_text(encoding="utf-8")
        records = parse_heading_sections(source)
        merged_paths = _MERGED_TOPIC_PATHS.get(entry.id)
        if merged_paths is None:
            sections = (_resolve_anchor(records, entry.source_anchor),)
        else:
            sections = tuple(_resolve_merged_section(records, path) for path in merged_paths)
        excerpt, spans = _bounded_topic_excerpt(sections, excluded=_EXCLUDED)
        digest = _fingerprint(excerpt)
        return SourceContext(
            topic_id=entry.id,
            source_path=entry.source_path,
            heading_path=entry.source_anchor.heading_path,
            heading_level=entry.source_anchor.heading_level,
            occurrence=entry.source_anchor.occurrence,
            excerpt=excerpt,
            source_hash=f"sha256:{digest}",
            spans=spans,
            neighboring_titles=_neighbor_titles(records, sections[0]),
        )


def _resolve_anchor(records: tuple[HeadingSection, ...], anchor: SourceAnchor) -> HeadingSection:
    for record in records:
        if (record.path, record.level, record.occurrence) == (
            anchor.heading_path,
            anchor.heading_level,
            anchor.occurrence,
        ):
            return record
    anchor_name = " / ".join(anchor.heading_path)
    raise ValueError(f"missing lecture source anchor level {anchor.heading_level}: {anchor_name} (occurrence {anchor.occurrence})")


def _resolve_merged_section(
    records: tuple[HeadingSection, ...], path: tuple[str, ...]
) -> HeadingSection:
    """Return one exact source heading used by a reviewed merged catalog topic."""

    for record in records:
        if record.path == path and record.occurrence == 1:
            return record
    raise ValueError(f"missing merged lecture source heading: {' / '.join(path)}")


def _bounded_topic_excerpt(
    sections: tuple[HeadingSection, ...], *, excluded: tuple[str, ...]
) -> tuple[str, tuple[SourceSpan, ...]]:
    """Return one or more explicitly selected heading blocks, never their siblings."""

    spans: list[SourceSpan] = []
    text_parts: list[str] = []
    for section in sections:
        text = _without_excluded_blocks(section.text, excluded)
        fingerprint = _fingerprint(text)
        spans.append(
            SourceSpan(
                id=_span_id(section.path, section.occurrence, fingerprint),
                heading_path=section.path,
                start_line=section.start_line,
                end_line=section.end_line,
                fingerprint=f"sha256:{fingerprint}",
                text=text,
            )
        )
        text_parts.append(text)
    return "\n\n".join(text_parts), tuple(spans)


def _without_excluded_blocks(text: str, excluded: tuple[str, ...]) -> str:
    """Remove excluded Markdown sections and legacy standalone self-checks."""
    kept: list[str] = []
    excluding_level: int | None = None
    for line in text.splitlines():
        match = _HEADING.match(line)
        if match is not None:
            level = len(match.group(1))
            title = match.group(2).strip()
            if excluding_level is not None and level <= excluding_level:
                excluding_level = None
            if _contains_excluded(title, excluded):
                excluding_level = level
                continue
        elif _is_legacy_excluded_marker(line, excluded):
            excluding_level = 7
            continue
        if excluding_level is None:
            kept.append(line)
    return "\n".join(kept).strip()


def _is_legacy_excluded_marker(line: str, excluded: tuple[str, ...]) -> bool:
    return line.strip() == "自检" or (
        line.strip().startswith("📖") and _contains_excluded(line.strip(), excluded)
    )


def _contains_excluded(title: str, excluded: tuple[str, ...]) -> bool:
    return any(word in title for word in excluded)


def _neighbor_titles(records: tuple[HeadingSection, ...], section: HeadingSection) -> tuple[str, ...]:
    siblings = [
        record
        for record in records
        if record.level == section.level
        and record.path[:-1] == section.path[:-1]
        and not _is_excluded(record.path[-1])
    ]
    index = siblings.index(section)
    neighbors: list[str] = []
    if index:
        neighbors.append(siblings[index - 1].title)
    if index + 1 < len(siblings):
        neighbors.append(siblings[index + 1].title)
    return tuple(neighbors)


def _is_excluded(title: str) -> bool:
    return _contains_excluded(title, _EXCLUDED)


def _fingerprint(text: str) -> str:
    return hashlib.sha256(normalize_source_text(text).encode("utf-8")).hexdigest()


def _span_id(path: tuple[str, ...], occurrence: int, fingerprint: str) -> str:
    return f"{' / '.join(path)}::{occurrence}::sha256:{fingerprint}"
