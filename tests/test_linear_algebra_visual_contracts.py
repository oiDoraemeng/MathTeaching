import pytest

from linear_algebra.catalog.manifest import topic_entries
from linear_algebra.visualizations.contracts import contract_for
from linear_algebra.visualizations.compiler import VisualCompileError
from linear_algebra.visualizations.families import family_compiler_for
from linear_algebra.teaching.model import VisualSemantics
from linear_algebra.visualizations.contracts import validate_contract_semantics


def test_all_new_topics_have_explicit_family_contracts():
    topics = [topic for topic in topic_entries() if 4 <= topic.chapter_number <= 8]
    assert len(topics) == 39
    for topic in topics:
        contract = contract_for(topic.id)
        assert contract.topic_id == topic.id
        assert len(contract.required_primitives) == 1
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
