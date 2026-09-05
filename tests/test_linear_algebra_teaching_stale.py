"""Stale source diagnostics preserve readable published revisions."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from linear_algebra.catalog.chapter_02 import TOPICS
from linear_algebra.teaching.model import TeachingArtifact
from linear_algebra.teaching.source import LectureSourceRepository
from linear_algebra.teaching.store import TeachingArtifactStore
from tests.test_linear_algebra_teaching_publish import _reviewed_valid_artifact


def test_stale_published_revision_remains_readable(tmp_path: Path) -> None:
    topic = next(item for item in TOPICS if item.id == "ch02.matrix.composition")
    context = LectureSourceRepository(Path(".agents/线性代数讲义.md")).context_for(topic)
    store = TeachingArtifactStore(tmp_path)
    store.save_published(_reviewed_valid_artifact())

    changed = replace(context, source_hash="sha256:new")
    loaded = store.load_published(topic.id, current_context=changed)

    assert loaded is not None
    assert loaded.stale is True
    assert loaded.artifact.topic_id == topic.id
    assert loaded.diagnostic == ("stale_source", context.source_hash, "sha256:new")


def test_matching_source_is_not_stale(tmp_path: Path) -> None:
    topic = next(item for item in TOPICS if item.id == "ch02.matrix.composition")
    context = LectureSourceRepository(Path(".agents/线性代数讲义.md")).context_for(topic)
    artifact = _reviewed_valid_artifact()
    store = TeachingArtifactStore(tmp_path)
    store.save_published(artifact)
    # The fixture carries the same source hash as the repository context.
    loaded = store.load_published(topic.id, current_context=context)

    assert loaded is not None
    assert loaded.stale is False
    assert loaded.diagnostic is None
