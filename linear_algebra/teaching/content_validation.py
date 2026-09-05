"""Chapter-level coverage checks for published teaching artifacts.

This module deliberately treats missing content as a diagnostic rather than
silently falling back to legacy explanations.  Generation and review can run
incrementally by chapter, while the report remains deterministic and suitable
for CI or an editor panel.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from linear_algebra.catalog.manifest import topic_entries
from linear_algebra.registry import CurriculumRegistry, catalog_registry
from linear_algebra.teaching.profiles import TeachingLevel, profile_for
from linear_algebra.teaching.source import LectureSourceRepository
from linear_algebra.teaching.store import TeachingArtifactStore
from linear_algebra.teaching.validation import (
    validate_claim_bindings,
    validate_closed_references,
    validate_source_evidence,
    validate_teaching_depth,
    validate_worked_examples,
)
from linear_algebra.visualizations.compiler import VisualCompileError, VisualSemanticsCompiler
from linear_algebra.visualizations.common import RenderContext
from linear_algebra.visualizations.contracts import contract_for, validate_contract


@dataclass(frozen=True)
class ChapterArtifactReport:
    chapter_number: int
    topic_count: int
    expected_topic_count: int
    published_topic_ids: tuple[str, ...]
    minimum_level_counts: tuple[tuple[str, int], ...]
    errors: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return self.topic_count == self.expected_topic_count and not self.errors

    def to_dict(self) -> dict[str, object]:
        return {
            "chapter_number": self.chapter_number,
            "topic_count": self.topic_count,
            "expected_topic_count": self.expected_topic_count,
            "published_topic_ids": list(self.published_topic_ids),
            "minimum_level_counts": dict(self.minimum_level_counts),
            "errors": list(self.errors),
        }


def bundled_store(root: str | Path | None = None) -> TeachingArtifactStore:
    """Return the conventional repository-local teaching artifact store."""

    path = Path(root) if root is not None else Path(__file__).with_name("data")
    return TeachingArtifactStore(path)


def lecture_source_repository(path: str | Path | None = None) -> LectureSourceRepository:
    """Return a source repository for the checked-in lecture."""

    source = Path(path) if path is not None else Path(__file__).parents[2] / ".agents" / "线性代数讲义.md"
    return LectureSourceRepository(source)


def validate_chapter_artifacts(
    chapter: int,
    store: TeachingArtifactStore,
    source_repo: LectureSourceRepository,
    *,
    registry: CurriculumRegistry | None = None,
) -> ChapterArtifactReport:
    """Validate publication, source, depth, graph, and compiler coverage."""

    if chapter not in {1, 2, 3}:
        raise ValueError("chapter must be 1, 2, or 3")
    registry = registry or catalog_registry()
    topics = tuple(topic for topic in registry.topics if topic.chapter_number == chapter)
    errors: list[str] = []
    published: list[str] = []
    levels = Counter(f"L{int(profile_for(topic.id).minimum_level)}" for topic in topics)
    compiler = VisualSemanticsCompiler()
    for topic in topics:
        stored = store.published(topic.id)
        if stored is None:
            errors.append(f"{topic.id}: missing published artifact")
            continue
        published.append(topic.id)
        artifact = stored.artifact
        try:
            context = source_repo.context_for(topic)
        except (OSError, ValueError) as error:
            errors.append(f"{topic.id}: source context failed: {error}")
            context = None
        if context is not None:
            for issue in validate_source_evidence(artifact, context, topic):
                errors.append(f"{topic.id}: {issue.code} {issue.path}: {issue.message}")
        for issue in (
            *validate_closed_references(artifact),
            *validate_claim_bindings(artifact),
            *validate_teaching_depth(artifact),
            *validate_worked_examples(artifact),
        ):
            errors.append(f"{topic.id}: {issue.code} {issue.path}: {issue.message}")
        contract = contract_for(topic.id)
        for issue in validate_contract(artifact, contract):
            errors.append(f"{topic.id}: {issue.code}: {issue.detail}")
        try:
            compiler.compile(artifact, contract, RenderContext.default(topic.id))
        except VisualCompileError as error:
            errors.append(f"{topic.id}: visual compilation failed: {error}")
    return ChapterArtifactReport(
        chapter_number=chapter,
        topic_count=len(published),
        expected_topic_count=len(topics),
        published_topic_ids=tuple(published),
        minimum_level_counts=tuple(sorted(levels.items())),
        errors=tuple(errors),
    )


def validate_all_chapters(
    store: TeachingArtifactStore,
    source_repo: LectureSourceRepository,
    *,
    registry: CurriculumRegistry | None = None,
) -> tuple[ChapterArtifactReport, ...]:
    registry = registry or catalog_registry()
    return tuple(
        validate_chapter_artifacts(chapter, store, source_repo, registry=registry)
        for chapter in (1, 2, 3)
    )


__all__ = [
    "ChapterArtifactReport",
    "bundled_store",
    "lecture_source_repository",
    "validate_all_chapters",
    "validate_chapter_artifacts",
]
