import json
from pathlib import Path

from linear_algebra.teaching.schema import load_artifact_schema
from linear_algebra.teaching.vocabulary import ENTITY_KINDS, RELATION_KINDS


def test_vocabulary_contains_chapter_4_8_controlled_kinds():
    assert {"subspace", "affine_set", "constraint", "eigenspace", "principal_axis", "quadratic_level_set"} <= ENTITY_KINDS
    assert {"span", "contains", "maps_to", "collapses_to", "affine_translation", "constraint_state", "row_operation", "coordinate_equivalence", "eigen_binding", "orthogonal_to", "principal_axis", "classification"} <= RELATION_KINDS


def test_schema_accepts_extended_profile_and_scene_family():
    schema = load_artifact_schema()
    assert "analogy_boundary" in json.dumps(schema)
    assert "scene_family" in json.dumps(schema)
