import pytest

from linear_algebra.catalog.manifest import topic_entries
from linear_algebra.visualizations.contracts import contract_for
from linear_algebra.visualizations.compiler import VisualCompileError
from linear_algebra.visualizations.families import family_compiler_for


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
