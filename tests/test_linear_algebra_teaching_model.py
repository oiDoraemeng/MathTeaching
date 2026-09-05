import pytest

from linear_algebra.teaching.model import TeachingArtifact
from tests.teaching_fixtures import composition_artifact_payload


def test_teaching_artifact_round_trip_keeps_claim_links() -> None:
    payload = composition_artifact_payload()

    artifact = TeachingArtifact.from_dict(payload)

    assert artifact.claims[0].id == "claim.composition-order"
    assert artifact.claims[0].entity_refs == ("x", "Bx", "ABx")
    assert artifact.to_dict() == payload


def test_list_fields_do_not_accept_strings() -> None:
    payload = composition_artifact_payload()
    payload["claims"][0]["entity_refs"] = "x"  # type: ignore[index]

    with pytest.raises(ValueError, match="entity_refs"):
        TeachingArtifact.from_dict(payload)
