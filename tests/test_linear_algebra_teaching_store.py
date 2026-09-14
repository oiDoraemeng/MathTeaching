"""Filesystem persistence tests for teaching artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from linear_algebra.teaching.model import TeachingArtifact
from linear_algebra.teaching.store import TeachingArtifactStore
from tests.teaching_fixtures import composition_artifact_payload
from tests.test_linear_algebra_teaching_publish import _reviewed_valid_artifact
from linear_algebra.visualizations.contracts import contract_for
from linear_algebra.visualizations.snapshots import contract_digest_for


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


def test_published_reader_uses_the_index_as_the_activation_boundary(tmp_path: Path) -> None:
    store = TeachingArtifactStore(tmp_path)
    artifact = TeachingArtifact.from_dict(composition_artifact_payload())
    first = store.save_published(artifact)
    store.upsert_published_topic(first)

    second = store.save_published(artifact)

    assert second.revision == 2
    assert store.published(artifact.topic_id).artifact.revision == 1

    store.upsert_published_topic(second)

    assert store.published(artifact.topic_id).artifact.revision == 2


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


def test_failed_chapter_publish_leaves_previous_index_unchanged(tmp_path: Path) -> None:
    store = TeachingArtifactStore(tmp_path)
    before = store.index_payload()
    with pytest.raises(ValueError):
        store.publish_chapter(4, {"ch04.unknown": 1})
    assert store.index_payload() == before


def test_unpublish_chapter_removes_only_requested_entries(tmp_path: Path) -> None:
    store = TeachingArtifactStore(tmp_path)
    store._write_stable_json(tmp_path / "index.json", {"schema_version": 1, "topics": [
        {"topic_id": "ch01.keep", "published_revision": 1},
        {"topic_id": "ch04.drop", "published_revision": 2},
        {"topic_id": "ch05.keep", "published_revision": 3},
    ]})
    payload = store.unpublish_chapter(4)
    assert [item["topic_id"] for item in payload["topics"]] == ["ch01.keep", "ch05.keep"]


def test_publish_chapter_requires_compiled_snapshot(tmp_path: Path) -> None:
    store = TeachingArtifactStore(tmp_path)
    artifact = _reviewed_valid_artifact()
    store.save_published(artifact)
    before = store.index_payload()
    with pytest.raises(ValueError, match="compiled snapshot"):
        store.publish_chapter(2, {artifact.topic_id: 1})
    assert store.index_payload() == before


def test_publish_chapter_rejects_stale_snapshot_source(tmp_path: Path) -> None:
    store = TeachingArtifactStore(tmp_path)
    artifact = _reviewed_valid_artifact()
    store.save_published(artifact)
    path = tmp_path / "snapshots" / "ch02" / artifact.topic_id / "r1.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "topic_id": artifact.topic_id, "artifact_revision": 1, "source_hash": "sha256:stale",
        "compiler_version": "v1", "render_profile": "teaching", "plan_digest": "sha256:p",
        "stage_ids": [], "required_entity_roles": [], "required_relations": [], "invariants": [],
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="stale compiled snapshot"):
        store.publish_chapter(2, {artifact.topic_id: 1})


def test_publish_chapter_rejects_empty_or_mismatched_contract_digest(tmp_path: Path) -> None:
    store = TeachingArtifactStore(tmp_path)
    artifact = _reviewed_valid_artifact()
    store.save_published(artifact)
    path = tmp_path / "snapshots" / "ch02" / artifact.topic_id / "r1.json"
    path.parent.mkdir(parents=True)
    base = {
        "topic_id": artifact.topic_id, "artifact_revision": 1,
        "source_hash": artifact.source.source_hash, "compiler_version": "v1",
        "render_profile": "teaching", "plan_digest": "sha256:p", "stage_ids": [],
        "required_entity_roles": [], "required_relations": [], "invariants": [],
    }
    for digest in ("", "sha256:not-the-contract"):
        payload = {**base, "contract_digest": digest}
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(ValueError, match="contract mismatch"):
            store.publish_chapter(2, {artifact.topic_id: 1})
        assert store.index_payload() == {"schema_version": 1, "topics": []}


def test_populated_index_preserves_chapter_1_to_3_entries_on_failed_gate(tmp_path: Path) -> None:
    bundled_index = Path(__file__).parents[1] / "linear_algebra" / "teaching" / "data" / "index.json"
    payload = json.loads(bundled_index.read_text(encoding="utf-8"))
    payload["topics"].extend([
        {"topic_id": "ch02.matrix.composition", "published_revision": 1},
        {"topic_id": "ch03.det.ad-bc", "published_revision": 1},
    ])
    store = TeachingArtifactStore(tmp_path)
    store._write_stable_json(tmp_path / "index.json", payload)
    before = store.index_payload()
    with pytest.raises(ValueError):
        store.publish_chapter(2, {"ch02.matrix.composition": 1})
    after = store.index_payload()
    assert after == before
    ids = {item["topic_id"] for item in after["topics"]}
    assert "ch01.vector.magnitude" in ids
    assert "ch02.matrix.composition" in ids
    assert "ch03.det.ad-bc" in ids


@pytest.mark.parametrize("failure", ["stale", "empty", "mismatch"])
def test_populated_index_release_gates_preserve_complete_payload(tmp_path: Path, failure: str) -> None:
    bundled_index = Path(__file__).parents[1] / "linear_algebra" / "teaching" / "data" / "index.json"
    payload = json.loads(bundled_index.read_text(encoding="utf-8"))
    artifact = _reviewed_valid_artifact()
    payload["topics"].append({
        "topic_id": artifact.topic_id, "published_revision": 1,
        "source_hash": artifact.source.source_hash, "artifact_digest": artifact.generated.artifact_digest,
    })
    store = TeachingArtifactStore(tmp_path)
    store.save_published(artifact)
    store._write_stable_json(tmp_path / "index.json", payload)
    snapshot = {
        "topic_id": artifact.topic_id, "artifact_revision": 1,
        "source_hash": artifact.source.source_hash, "compiler_version": "v1",
        "render_profile": "teaching", "plan_digest": "sha256:p", "stage_ids": [],
        "required_entity_roles": [], "required_relations": [], "invariants": [],
        "contract_digest": contract_digest_for(contract_for(artifact.topic_id)),
    }
    if failure == "stale":
        snapshot["source_hash"] = "sha256:stale"
    elif failure == "empty":
        snapshot["contract_digest"] = ""
    else:
        snapshot["contract_digest"] = "sha256:mismatch"
    snapshot_path = tmp_path / "snapshots" / "ch02" / artifact.topic_id / "r1.json"
    snapshot_path.parent.mkdir(parents=True)
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
    before = store.index_payload()
    with pytest.raises(ValueError):
        store.publish_chapter(2, {artifact.topic_id: 1})
    assert store.index_payload() == before
    retained = next(item for item in before["topics"] if item["topic_id"] == "ch01.vector.magnitude")
    assert retained == next(item for item in store.index_payload()["topics"] if item["topic_id"] == retained["topic_id"])
