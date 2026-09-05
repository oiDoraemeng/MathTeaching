import pytest

from linear_algebra.teaching.model import TeachingArtifact, VisualRelation
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


def test_directly_constructed_nested_json_is_immutable() -> None:
    parameters = {"matrix": [[2, 0], [0, 1]]}

    relation = VisualRelation(
        id="B_maps_x_to_Bx",
        kind="maps_to",
        source_ref="x",
        target_ref="Bx",
        parameters=parameters,
        claim_refs=["claim.composition-order"],
    )
    parameters["matrix"][0][0] = 99

    assert relation.parameters["matrix"] == ((2, 0), (0, 1))
    assert relation.claim_refs == ("claim.composition-order",)
    with pytest.raises(TypeError):
        relation.parameters["matrix"] = ()  # type: ignore[index]


def test_artifact_requires_an_object_root() -> None:
    with pytest.raises(ValueError, match=r"\$: expected object"):
        TeachingArtifact.from_dict([])  # type: ignore[arg-type]
