"""Filesystem persistence tests for teaching artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from linear_algebra.teaching.model import TeachingArtifact
from linear_algebra.teaching.store import TeachingArtifactStore
from tests.teaching_fixtures import composition_artifact_payload


def test_store_writes_stable_utf8_json(tmp_path: Path) -> None:
    store = TeachingArtifactStore(tmp_path)
    artifact = TeachingArtifact.from_dict(composition_artifact_payload())
    revision = store.save_draft(artifact, raw_reply=json.dumps(artifact.to_dict(), ensure_ascii=False))
    path = tmp_path / "drafts" / "ch02" / "ch02.matrix.composition" / "r1.json"

    assert revision.revision == 1
    assert path.read_text(encoding="utf-8").endswith("\n")
    assert json.loads(path.read_text(encoding="utf-8"))["artifact"]["topic_id"] == "ch02.matrix.composition"
    loaded = store.get("ch02.matrix.composition", 1, "draft")
    assert loaded.artifact.to_dict() == artifact.to_dict()
    assert loaded.raw_reply is not None


def test_store_allocates_revisions_and_published_is_separate(tmp_path: Path) -> None:
    store = TeachingArtifactStore(tmp_path)
    artifact = TeachingArtifact.from_dict(composition_artifact_payload())
    store.save_draft(artifact, raw_reply="{}")
    second = store.save_draft(artifact, raw_reply="{}")
    assert second.revision == 2
    assert store.published(artifact.topic_id) is None


@pytest.mark.parametrize("topic_id", ["../escape", "ch02/escape", "ch02..escape", "ch02."])
def test_store_rejects_path_traversal_topic_ids(tmp_path: Path, topic_id: str) -> None:
    store = TeachingArtifactStore(tmp_path)
    with pytest.raises(ValueError, match="unsafe topic id"):
        store.list_revisions(topic_id)
