import pytest

from linear_algebra.catalog.manifest import topic_entries
from linear_algebra.teaching.model import TeachingArtifact, VisualSemantics
from linear_algebra.visualizations.contracts import contract_for, validate_contract, validate_contract_semantics
from linear_algebra.visualizations.compiler import VisualCompileError
from linear_algebra.visualizations.families import family_compiler_for
from tests.teaching_fixtures import projection_artifact_payload


def test_composition_contract_requires_two_paths_and_endpoint_difference() -> None:
    contract = contract_for("ch02.matrix.composition")
    assert contract.minimum_stage_count == 5
    assert {"composition_order", "endpoint_diff", "compare"} <= set(contract.required_relations)


def test_projection_contract_rejects_missing_residual() -> None:
    artifact = TeachingArtifact.from_dict(projection_artifact_payload(with_residual=False))
    issues = validate_contract(artifact, contract_for("ch01.projection.definition"))
    assert "missing_entity_role" in {issue.code for issue in issues}


def test_all_catalog_topics_resolve_explicit_contracts() -> None:
    contracts = tuple(contract_for(topic.id) for topic in topic_entries())
    assert len(contracts) == 90
    assert {contract.topic_id for contract in contracts} == {topic.id for topic in topic_entries()}


def test_all_new_topics_have_explicit_family_contracts():
    topics = [topic for topic in topic_entries() if 4 <= topic.chapter_number <= 8]
    assert len(topics) == 39
    for topic in topics:
        contract = contract_for(topic.id)
        assert contract.topic_id == topic.id
        assert len(contract.required_primitives) <= 1
        assert contract.required_claims == (f"claim.{topic.id}",)


def test_unknown_family_is_rejected_without_generic_fallback():
    with pytest.raises(VisualCompileError, match="unsupported_scene_family"):
        family_compiler_for("generic_vector")


def test_extended_contract_accepts_registered_scene_family_as_primitive():
    contract = contract_for("ch04.space.closure")
    semantics = VisualSemantics(
        scene_kind="2d", scene_family="subspace_region", entities=(), relations=(), stages=()
    )
    issues = validate_contract_semantics(semantics, contract)
    assert {issue.code for issue in issues} == {"missing_entity_role", "missing_relation", "insufficient_stages", "missing_invariant"}
