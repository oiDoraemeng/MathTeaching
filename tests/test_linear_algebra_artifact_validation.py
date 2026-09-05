import pytest

from linear_algebra.teaching.validation import (
    ArtifactValidationError,
    validate_artifact_payload,
    validate_closed_references,
)
from linear_algebra.teaching.model import TeachingArtifact
from tests.teaching_fixtures import composition_artifact_payload


def test_missing_claims_reports_json_path() -> None:
    payload = composition_artifact_payload()
    del payload["claims"]

    with pytest.raises(ArtifactValidationError) as raised:
        validate_artifact_payload(payload)

    assert raised.value.issues[0].path == "$.claims"


def test_dangling_entity_reference_is_rejected() -> None:
    payload = composition_artifact_payload()
    payload["claims"][0]["entity_refs"].append("missing")  # type: ignore[index]

    with pytest.raises(ArtifactValidationError, match="missing"):
        validate_artifact_payload(payload)


def test_closed_references_cover_reverse_links_and_relation_endpoints() -> None:
    payload = composition_artifact_payload()
    payload["explanation"]["sections"][0]["claim_refs"] = ["missing-claim"]  # type: ignore[index]
    payload["visual_semantics"]["relations"][0]["target_ref"] = "missing-entity"  # type: ignore[index]

    with pytest.raises(ArtifactValidationError) as raised:
        validate_artifact_payload(payload)

    assert [(issue.path, issue.code) for issue in raised.value.issues] == [
        ("$.explanation.sections[0].claim_refs[0]", "dangling_reference"),
        ("$.visual_semantics.relations[0].target_ref", "dangling_reference"),
    ]


def test_duplicate_ids_are_reported_before_membership_checks() -> None:
    payload = composition_artifact_payload()
    payload["visual_semantics"]["entities"].append(  # type: ignore[index]
        dict(payload["visual_semantics"]["entities"][0])  # type: ignore[index]
    )
    artifact = TeachingArtifact.from_dict(payload)

    issues = validate_closed_references(artifact)

    assert len(issues) == 1
    assert issues[0].path == "$.visual_semantics.entities[3].id"
    assert issues[0].code == "duplicate_id"
