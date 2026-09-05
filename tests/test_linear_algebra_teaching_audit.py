"""Raw-reply audit isolation tests."""

from __future__ import annotations

from pathlib import Path

from linear_algebra.teaching.model import TeachingArtifact
from linear_algebra.teaching.store import TeachingArtifactStore
from tests.teaching_fixtures import composition_artifact_payload


def test_accepted_raw_reply_is_recoverable_but_not_runtime_input(tmp_path: Path) -> None:
    store = TeachingArtifactStore(tmp_path)
    artifact = TeachingArtifact.from_dict(composition_artifact_payload())
    revision = store.save_published(artifact, raw_reply='{"accepted":true}')

    assert store.audit_raw_reply(revision).raw_reply == '{"accepted":true}'
    assert "raw_reply" not in store.get_published_payload(revision)


def test_rejected_reply_keeps_only_bounded_diagnostics(tmp_path: Path) -> None:
    store = TeachingArtifactStore(tmp_path)
    audit = store.save_rejection(
        topic_id="ch02.matrix.composition",
        raw_reply="secret",
        code="executable_leakage",
        message="x" * 10000,
    )

    assert len(audit.message) <= 512
    assert audit.raw_reply is None
