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
    assert store.get(artifact.topic_id, 2, "draft").artifact.revision == 2
    assert store.published(artifact.topic_id) is None


def test_accepted_raw_reply_is_audited_but_not_in_published_payload(tmp_path: Path) -> None:
    store = TeachingArtifactStore(tmp_path)
    artifact = TeachingArtifact.from_dict(composition_artifact_payload())
    revision = store.save_reviewed(artifact, raw_reply='{"accepted":true}')
    published = store.save_published(artifact, raw_reply='{"accepted":true}')

    audit = store.audit_raw_reply(published)
    assert audit.raw_reply == '{"accepted":true}'
    assert audit.error_code is None
    assert "raw_reply" not in store.get_published_payload(published)
    assert revision.state == "reviewed"


def test_rejected_reply_keeps_only_bounded_diagnostics(tmp_path: Path) -> None:
    store = TeachingArtifactStore(tmp_path)
    audit = store.save_rejection(
        topic_id="ch02.matrix.composition",
        raw_reply="secret",
        code="executable_leakage",
        message="x" * 10000,
    )

    assert audit.raw_reply is None
    assert len(audit.message) <= 512
    assert audit.error_code == "executable_leakage"


@pytest.mark.parametrize("topic_id", ["../escape", "ch02/escape", "ch02..escape", "ch02."])
def test_store_rejects_path_traversal_topic_ids(tmp_path: Path, topic_id: str) -> None:
    store = TeachingArtifactStore(tmp_path)
    with pytest.raises(ValueError, match="unsafe topic id"):
        store.list_revisions(topic_id)
