"""Explicit topic-level contracts for claim-backed visual semantics."""

from __future__ import annotations

from dataclasses import dataclass

from linear_algebra.catalog.manifest import topic_entries
from linear_algebra.teaching.model import TeachingArtifact


@dataclass(frozen=True)
class ContractIssue:
    code: str
    topic_id: str
    detail: str


@dataclass(frozen=True)
class VisualContract:
    topic_id: str
    required_claims: tuple[str, ...]
    required_entity_roles: tuple[str, ...]
    required_relations: tuple[str, ...]
    required_primitives: tuple[str, ...]
    minimum_stage_count: int
    required_invariants: tuple[str, ...] = ()
    distinguishable_role_groups: tuple[tuple[str, ...], ...] = ()


def contract_for(topic_id: str) -> VisualContract:
    """Return a stable contract for every catalog topic ID."""

    if topic_id not in {topic.id for topic in topic_entries()}:
        raise KeyError(f"unknown visual contract topic: {topic_id}")
    base = VisualContract(topic_id, (), (), (), (), 1)
    overrides = {
        "ch01.projection.definition": VisualContract(
            topic_id, (), ("vector_a", "direction", "projection", "foot", "residual"),
            ("projects_to", "decomposes_into", "orthogonal_to"), (), 3,
            ("orthogonality",), (("projection", "residual"),),
        ),
        "ch02.matrix.transformed-grid": VisualContract(
            topic_id, (), (), ("invariant",), ("grid",), 2,
        ),
        "ch02.matrix.composition": VisualContract(
            topic_id, (), ("vector_a", "transformed_a", "transformed_b"),
            ("composition_order", "endpoint_diff", "compare"), (), 5,
            distinguishable_role_groups=(("transformed_a", "transformed_b"),),
        ),
        "ch02.subspace.null": VisualContract(
            topic_id, (), ("vector_a",), ("collapses_to",), (), 2,
        ),
        "ch03.det.multiplicativity": VisualContract(
            topic_id, (), (), ("same_measure", "composition_order"), (), 3,
        ),
        "ch01.ops.cross-product": VisualContract(
            topic_id, (), (), ("orientation", "orthogonal_to"), ("vector",), 2,
        ),
        "ch03.inverse.undo": VisualContract(
            topic_id, (), (), ("composition_order", "compare"), (), 3,
        ),
    }
    return overrides.get(topic_id, base)


def validate_contract(artifact: TeachingArtifact, contract: VisualContract) -> tuple[ContractIssue, ...]:
    """Report missing semantic evidence before a compiler can emit commands."""

    issues: list[ContractIssue] = []
    if artifact.topic_id != contract.topic_id:
        issues.append(ContractIssue("topic_mismatch", contract.topic_id, artifact.topic_id))
    claims = {claim.id for claim in artifact.claims}
    roles = {entity.role for entity in artifact.visual_semantics.entities}
    relations = {relation.kind for relation in artifact.visual_semantics.relations}
    primitives = {entity.kind for entity in artifact.visual_semantics.entities} | relations
    invariants = {
        invariant
        for stage in artifact.visual_semantics.stages
        for invariant in stage.expected_invariants
    }
    for claim_id in contract.required_claims:
        if claim_id not in claims:
            issues.append(ContractIssue("missing_claim", contract.topic_id, claim_id))
    for role in contract.required_entity_roles:
        if role not in roles:
            issues.append(ContractIssue("missing_entity_role", contract.topic_id, role))
    for relation in contract.required_relations:
        if relation not in relations:
            issues.append(ContractIssue("missing_relation", contract.topic_id, relation))
    for primitive in contract.required_primitives:
        if primitive not in primitives:
            issues.append(ContractIssue("missing_primitive", contract.topic_id, primitive))
    if len(artifact.visual_semantics.stages) < contract.minimum_stage_count:
        issues.append(ContractIssue("insufficient_stages", contract.topic_id, str(contract.minimum_stage_count)))
    for invariant in contract.required_invariants:
        if invariant not in invariants:
            issues.append(ContractIssue("missing_invariant", contract.topic_id, invariant))
    for group in contract.distinguishable_role_groups:
        present = [role for role in group if role in roles]
        if len(present) != len(group):
            issues.append(ContractIssue("roles_not_distinguishable", contract.topic_id, ",".join(group)))
    return tuple(sorted(issues, key=lambda issue: (issue.code, issue.detail)))


__all__ = ["ContractIssue", "VisualContract", "contract_for", "validate_contract"]
