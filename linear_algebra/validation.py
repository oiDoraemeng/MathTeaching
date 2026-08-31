"""Development validators for the checked-in linear algebra curriculum."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable

from linear_algebra.catalog.model import LessonEntry
from linear_algebra.registry import CurriculumRegistry, catalog_registry
from linear_algebra.visualizations.common import RenderContext
from services.scene_commands import SceneCommandService

_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_CHAPTER = re.compile(r"^第([1-3])章(?:\s|$)")
_SECTION = re.compile(r"^\d+\.\d+(?:\s|$)")
_EXCLUDED = ("自检", "练习", "挑战")


@dataclass(frozen=True)
class HeadingRecord:
    path: tuple[str, ...]
    level: int
    occurrence: int
    line_number: int


def validate_registry(registry: CurriculumRegistry) -> tuple[str, ...]:
    errors: list[str] = []
    topic_ids = [topic.id for topic in registry.topics]
    if len(topic_ids) != len(set(topic_ids)):
        errors.append("catalog: duplicate topic IDs")
    if Counter(topic.chapter_number for topic in registry.topics) != Counter({1: 24, 2: 15, 3: 15}):
        errors.append("catalog: expected chapter topic counts 24/15/15")
    node_ids = [node.id for node in registry.nodes]
    if len(node_ids) != len(set(node_ids)):
        errors.append("catalog: duplicate node IDs")
    validator = SceneCommandService()
    for topic in registry.topics:
        try:
            explanation = registry.get_explanation(topic.explanation_id)
        except KeyError as error:
            errors.append(f"{topic.id}: {error}")
        else:
            if explanation.id != topic.explanation_id:
                errors.append(f"{topic.id}: explanation ID mismatch: {explanation.id}")
        try:
            recipe = registry.get_recipe(topic.visualization_id)
        except KeyError as error:
            errors.append(f"{topic.id}: {error}")
            continue
        missing = sorted(set(topic.required_capabilities) - set(registry.capabilities))
        if missing:
            errors.append(f"{topic.id}: missing capabilities: {', '.join(missing)}")
        if recipe.required_capabilities != topic.required_capabilities:
            errors.append(f"{topic.id}: recipe capability declaration differs from catalog")
        try:
            plan = recipe.builder(RenderContext.default(topic.id))
        except Exception as error:
            errors.append(f"{topic.id}: recipe build failed: {error}")
            continue
        result = validator.validate(plan)
        if not result.valid:
            errors.append(f"{topic.id}: invalid command plan: {'; '.join(result.messages)}")
    expected_explanations = {topic.explanation_id for topic in registry.topics}
    expected_recipes = {topic.visualization_id for topic in registry.topics}
    for orphan in sorted(set(registry.explanations) - expected_explanations):
        errors.append(f"orphan explanation: {orphan}")
    for orphan in sorted(set(registry.recipes) - expected_recipes):
        errors.append(f"orphan recipe: {orphan}")
    return tuple(errors)


def validate_lecture_source(path: Path, entries: Iterable[LessonEntry]) -> tuple[str, ...]:
    if not path.is_file():
        return (f"lecture source does not exist: {path}",)
    records = _heading_records(path.read_text(encoding="utf-8"))
    by_key = {(record.path, record.level, record.occurrence): record for record in records}
    errors: list[str] = []
    last_line = 0
    for entry in entries:
        if any(word in " / ".join(entry.source_path) for word in _EXCLUDED):
            errors.append(f"{entry.id}: excluded source path: {' / '.join(entry.source_path)}")
            continue
        anchor = entry.source_anchor
        key = (anchor.heading_path, anchor.heading_level, anchor.occurrence)
        record = by_key.get(key)
        if record is None:
            errors.append(
                f"{entry.id}: missing source anchor level {anchor.heading_level}: "
                f"{' / '.join(anchor.heading_path)} (occurrence {anchor.occurrence})"
            )
            continue
        if record.line_number < last_line:
            errors.append(f"{entry.id}: source anchor is out of lecture order")
        last_line = max(last_line, record.line_number)
    return tuple(errors)


def _heading_records(source: str) -> tuple[HeadingRecord, ...]:
    active_chapter: str | None = None
    stack: list[tuple[int, str]] = []
    counts: Counter[tuple[str, ...]] = Counter()
    records: list[HeadingRecord] = []
    for line_number, line in enumerate(source.splitlines(), start=1):
        match = _HEADING.match(line)
        if match is None:
            continue
        level = len(match.group(1))
        title = match.group(2).strip()
        if _CHAPTER.match(title):
            active_chapter = title
            # The source occasionally uses a second-level heading for a section.
            # Keep the active chapter at a synthetic root level so those headings
            # remain children of the chapter in the conceptual curriculum path.
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
        records.append(HeadingRecord(path, level, counts[path], line_number))
    return tuple(records)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the linear algebra lecture curriculum")
    parser.add_argument("source", nargs="?", type=Path, default=Path(__file__).parents[1] / ".agents" / "线性代数讲义.md")
    args = parser.parse_args(argv)
    registry = catalog_registry()
    errors = (*validate_registry(registry), *validate_lecture_source(args.source, registry.topics))
    if errors:
        for error in errors:
            print(error)
        return 1
    print(f"{len(registry.topics)} topics validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
