import json
from pathlib import Path

from linear_algebra.teaching.schema import load_artifact_schema
from linear_algebra.teaching.vocabulary import ENTITY_KINDS, RELATION_KINDS
from linear_algebra.teaching.model import TeachingArtifact
from tests.teaching_fixtures import composition_artifact_payload


def test_vocabulary_contains_chapter_4_8_controlled_kinds():
    assert {"subspace", "affine_set", "constraint", "eigenspace", "principal_axis", "quadratic_level_set"} <= ENTITY_KINDS
    assert {"span", "contains", "maps_to", "collapses_to", "affine_translation", "constraint_state", "row_operation", "coordinate_equivalence", "eigen_binding", "orthogonal_to", "principal_axis", "classification"} <= RELATION_KINDS


def test_schema_accepts_extended_profile_and_scene_family():
    schema = load_artifact_schema()
    assert "analogy_boundary" in json.dumps(schema)
    assert "scene_family" in json.dumps(schema)


def test_complete_artifact_round_trip_preserves_extended_fields():
    payload = composition_artifact_payload()
    payload["explanation"]["analogy_boundary"] = "not a geometric analogy"
    payload["visual_semantics"]["scene_family"] = "spectral_orthogonal"
    artifact = TeachingArtifact.from_dict(payload)
    encoded = artifact.to_dict()
    assert encoded["explanation"]["analogy_boundary"] == "not a geometric analogy"
    assert encoded["visual_semantics"]["scene_family"] == "spectral_orthogonal"
    assert encoded["source"]["occurrence"] == payload["source"]["occurrence"]
    assert encoded["claims"][0]["entity_refs"] == payload["claims"][0]["entity_refs"]
    assert encoded["visual_semantics"]["stages"] == payload["visual_semantics"]["stages"]


def test_unknown_fields_and_visual_kinds_are_rejected():
    payload = composition_artifact_payload()
    payload["visual_semantics"]["unknown"] = True
    try:
        TeachingArtifact.from_dict(payload)
    except ValueError:
        pass
    else:
        raise AssertionError("unknown visual semantics field was accepted")
    payload = composition_artifact_payload()
    payload["visual_semantics"]["entities"][0]["kind"] = "not-a-kind"
    try:
        TeachingArtifact.from_dict(payload)
    except ValueError:
        pass
    else:
        raise AssertionError("unknown entity kind was accepted")
    payload = composition_artifact_payload()
    payload["visual_semantics"]["relations"][0]["kind"] = "not-a-relation-kind"
    try:
        TeachingArtifact.from_dict(payload)
    except ValueError:
        pass
    else:
        raise AssertionError("unknown relation kind was accepted")
