from dataclasses import replace

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


def test_direct_construction_rejects_invalid_scalar_values() -> None:
    artifact = TeachingArtifact.from_dict(composition_artifact_payload())

    invalid_constructions = (
        lambda: replace(artifact.source, heading_level=True),
        lambda: replace(artifact.teaching_profile, requires_analogy_boundary=1),
        lambda: replace(artifact.claims[0], formula=1),
        lambda: replace(artifact.explanation.sections[0], text=1),
        lambda: replace(artifact.explanation, title=1),
        lambda: replace(artifact.visual_semantics.entities[0], dimension=True),
        lambda: replace(artifact.visual_semantics.relations[0], source_ref=1),
        lambda: replace(artifact.visual_semantics.stages[0], layout="grid"),
        lambda: replace(artifact.visual_semantics, scene_kind="4d"),
        lambda: replace(artifact.generated, provider=1),
        lambda: replace(artifact, status="queued"),
    )

    for construct in invalid_constructions:
        with pytest.raises(TypeError):
            construct()
