"""Current-source authorization checks for teaching claims."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from linear_algebra.catalog.chapter_02 import TOPICS
from linear_algebra.teaching.model import TeachingArtifact
from linear_algebra.teaching.source import LectureSourceRepository
from linear_algebra.teaching.validation import validate_source_evidence

from tests.teaching_fixtures import composition_artifact_payload


def _inputs():
    topic = next(item for item in TOPICS if item.id == "ch02.matrix.composition")
    context = LectureSourceRepository(Path(".agents/线性代数讲义.md")).context_for(topic)
    return context, topic


def test_claim_source_refs_must_resolve_in_current_context() -> None:
    context, topic = _inputs()
    artifact = TeachingArtifact.from_dict(composition_artifact_payload())

    assert validate_source_evidence(artifact, context, topic) == ()


def test_changed_excerpt_reports_stale_source() -> None:
    context, topic = _inputs()
    changed = replace(context, source_hash="sha256:changed")
    artifact = TeachingArtifact.from_dict(composition_artifact_payload())

    issues = validate_source_evidence(artifact, changed, topic)

    assert [issue.code for issue in issues] == ["stale_source"]


def test_claim_source_ref_outside_current_context_is_rejected() -> None:
    context, topic = _inputs()
    payload = composition_artifact_payload()
    payload["claims"][0]["source_refs"] = ["old-span"]  # type: ignore[index]
    artifact = TeachingArtifact.from_dict(payload)

    issues = validate_source_evidence(artifact, context, topic)

    assert [(issue.path, issue.code) for issue in issues] == [
        ("$.claims[0].source_refs[0]", "source_ref_out_of_context")
    ]
