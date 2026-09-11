"""Strict, deterministic index for the chapter 4-8 drawing catalog."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class DrawingCatalogEntry:
    topic_id: str
    chapter_number: int
    source_path: tuple[str, ...]
    visual_claims: str
    existing_capabilities: tuple[str, ...]
    missing_capabilities: tuple[str, ...]


EXCLUDED_TOPIC_IDS = frozenset({"ch07.7", "ch08.6"})
EXCLUDED_SECTION_MARKERS = frozenset({"7.7", "8.6"})
_ROW = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$")
_CHAPTER = re.compile(r"^第\s*(4|5|6|7|8)\s*章")
_TOPIC_ID = re.compile(r"^ch(04|05|06|07|08)\.(?:[a-z0-9]+(?:-[a-z0-9]+)*\.)*[a-z0-9]+(?:-[a-z0-9]+)*$")


def _parts(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in re.split(r"[,、;/]", value) if item.strip())


def load_drawing_catalog(path: Path) -> tuple[DrawingCatalogEntry, ...]:
    entries: list[DrawingCatalogEntry] = []
    chapter: int | None = None
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        heading = _CHAPTER.match(line.strip().lstrip("# "))
        if heading:
            chapter = int(heading.group(1))
            continue
        if not line.lstrip().startswith("|") or "topic_id" in line:
            continue
        if re.match(r"^\|\s*-+\s*\|", line):
            continue
        match = _ROW.match(line)
        if match is None:
            raise ValueError(f"malformed drawing catalog row at line {line_number}")
        if chapter is None:
            raise ValueError(f"topic row before chapter at line {line_number}")
        topic_id, source, claims, existing, missing = match.groups()
        if not topic_id.startswith(f"ch{chapter:02d}.") or not source.strip() or not claims.strip() or not existing.strip():
            raise ValueError(f"invalid drawing catalog row at line {line_number}")
        if topic_id in EXCLUDED_TOPIC_IDS or any(marker in source for marker in EXCLUDED_SECTION_MARKERS):
            continue
        entries.append(DrawingCatalogEntry(topic_id, chapter, (source.strip(),), claims.strip(), _parts(existing), _parts(missing)))
    errors = validate_drawing_catalog(tuple(entries))
    if errors:
        raise ValueError("; ".join(errors))
    return tuple(entries)


def validate_drawing_catalog(entries: tuple[DrawingCatalogEntry, ...] | list[DrawingCatalogEntry]) -> tuple[str, ...]:
    errors: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        if entry.topic_id in seen:
            errors.append(f"duplicate topic_id: {entry.topic_id}")
        seen.add(entry.topic_id)
        if entry.chapter_number not in range(4, 9):
            errors.append(f"invalid chapter: {entry.topic_id}")
        if not _TOPIC_ID.fullmatch(entry.topic_id) or entry.topic_id.endswith(".bad"):
            errors.append(f"invalid topic_id: {entry.topic_id}")
        if not entry.source_path or not all(entry.source_path):
            errors.append(f"empty source path: {entry.topic_id}")
        if not entry.visual_claims.strip():
            errors.append(f"missing visual claims: {entry.topic_id}")
        if not entry.existing_capabilities and not entry.missing_capabilities:
            errors.append(f"missing expected operations: {entry.topic_id}")
    counts = {chapter: sum(entry.chapter_number == chapter for entry in entries) for chapter in range(4, 9)}
    expected = {4: 16, 5: 8, 6: 3, 7: 6, 8: 6}
    if len(entries) != 39:
        errors.append(f"expected 39 topics, got {len(entries)}")
    if counts != expected:
        errors.append(f"invalid chapter distribution: expected {expected}, got {counts}")
    return tuple(errors)


__all__ = ["DrawingCatalogEntry", "EXCLUDED_TOPIC_IDS", "EXCLUDED_SECTION_MARKERS", "load_drawing_catalog", "validate_drawing_catalog"]
