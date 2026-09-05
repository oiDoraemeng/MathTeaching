"""Topic visual contract coverage and semantic evidence tests."""

from __future__ import annotations

from linear_algebra.catalog.manifest import topic_entries
from linear_algebra.teaching.model import TeachingArtifact
from linear_algebra.visualizations.contracts import contract_for, validate_contract
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
    assert len(contracts) == 54
    assert {contract.topic_id for contract in contracts} == {topic.id for topic in topic_entries()}
