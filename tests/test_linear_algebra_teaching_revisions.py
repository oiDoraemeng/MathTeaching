"""Revision comparison never requests rendering."""

from __future__ import annotations

from dataclasses import replace

from linear_algebra.teaching.model import TeachingArtifact
from linear_algebra.teaching.revisions import diff_artifacts
from tests.teaching_fixtures import composition_artifact_payload


def test_revision_diff_reports_claim_and_visual_changes() -> None:
    old = TeachingArtifact.from_dict(composition_artifact_payload())
    payload = composition_artifact_payload()
    payload["claims"].append(  # type: ignore[index]
        {
            **payload["claims"][0],  # type: ignore[index]
            "id": "claim.extra",
            "statement": "一个额外论断。",
        }
    )
    payload["visual_semantics"]["entities"][0]["label"] = "x_0"  # type: ignore[index]
    new = TeachingArtifact.from_dict(payload)

    diff = diff_artifacts(old, new)

    assert "claims" in diff.changed_sections
    assert "visual_semantics" in diff.changed_sections
    assert diff.claim_changes
    assert diff.visual_changes
    assert diff.render_requested is False


def test_revision_diff_redacts_provider_metadata() -> None:
    old = TeachingArtifact.from_dict(composition_artifact_payload())
    payload = composition_artifact_payload()
    payload["generated"]["model"] = "private-model"  # type: ignore[index]
    new = TeachingArtifact.from_dict(payload)

    diff = diff_artifacts(old, new)

    assert all("private-model" not in repr(change) for change in diff.explanation_changes + diff.visual_changes)
