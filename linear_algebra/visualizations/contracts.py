"""Explicit topic-level contracts for claim-backed visual semantics."""

from __future__ import annotations

from dataclasses import dataclass

from linear_algebra.catalog.manifest import topic_entries
from linear_algebra.teaching.model import TeachingArtifact, VisualSemantics
from linear_algebra.chapter_04_semantics import semantic_for


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
    extended_family = {
        **{topic: "subspace_region" for topic in (
            "ch04.space.closure", "ch04.subspace.classification", "ch04.subspace.intersection", "ch04.subspace.col-null", "ch04.span.dimension", "ch04.dependence.redundancy", "ch04.nullspace.test", "ch04.rank.collapse", "ch04.basis.span", "ch04.dimension.ladder", "ch04.coordinates.readout", "ch04.linear-map.definition", "ch04.linear-map.compare", "ch04.linear-map.matrix-columns", "ch04.kernel-image", "ch04.rank-nullity")},
        **{topic: "affine_solution" for topic in ("ch05.homogeneous.solution-space", "ch05.affine.solution-set", "ch05.consistency.geometry", "ch05.gaussian-elimination", "ch05.least-squares.projection", "ch05.fundamental-solution-system", "ch05.elementary-matrix-elimination", "ch05.least-squares-derivation")},
        **{topic: "basis_change" for topic in ("ch06.basis-change.motivation", "ch06.basis-change.coordinates", "ch06.similarity-transform")},
        **{topic: "spectral_orthogonal" for topic in ("ch07.eigen.direction", "ch07.characteristic-polynomial", "ch07.eigenspace", "ch07.diagonalization", "ch07.gram-schmidt", "ch07.orthogonal-transform")},
        **{topic: "quadratic_level_set" for topic in ("ch08.quadratic.matrix-form", "ch08.quadratic.level-sets", "ch08.principal-axis", "ch08.definiteness", "ch08.completing-square", "ch08.congruence-inertia")},
    }
    if topic_id in extended_family:
        if topic_id.startswith("ch04."):
            semantic = semantic_for(topic_id)
            return VisualContract(
                topic_id,
                (f"claim.{topic_id}",),
                semantic.roles[:2],
                (semantic.relation,),
                (semantic.primitive,),
                1,
                ("finite numeric result",),
            )
        family = extended_family[topic_id]
        return VisualContract(topic_id, (f"claim.{topic_id}",), ("vector_a", "transformed_a"), ("maps_to",), (family,), 1, ("finite numeric result",))
    return overrides.get(topic_id, base)


def validate_contract(artifact: TeachingArtifact, contract: VisualContract) -> tuple[ContractIssue, ...]:
    """Report missing semantic evidence before a compiler can emit commands."""

    issues = list(validate_contract_semantics(artifact.visual_semantics, contract))
    claims = {claim.id for claim in artifact.claims}
    for claim_id in contract.required_claims:
        if claim_id not in claims:
            issues.append(ContractIssue("missing_claim", contract.topic_id, claim_id))
    return tuple(sorted(issues, key=lambda issue: (issue.code, issue.detail)))


def validate_contract_semantics(
    semantics: VisualSemantics, contract: VisualContract, *, topic_id: str | None = None
) -> tuple[ContractIssue, ...]:
    """Validate a semantic graph without requiring a complete artifact.

    The compiler uses this boundary after parsing an artifact.  Keeping the
    graph-only check separate also makes it impossible for a renderer to be
    reached when the semantic graph itself violates a topic contract.
    """

    issues: list[ContractIssue] = []
    if topic_id is not None and topic_id != contract.topic_id:
        issues.append(ContractIssue("topic_mismatch", contract.topic_id, topic_id))
    roles = {entity.role for entity in semantics.entities}
    relations = {relation.kind for relation in semantics.relations}
    primitives = {entity.kind for entity in semantics.entities} | relations
    scene_family = getattr(semantics, "scene_family", "")
    invariants = {
        invariant
        for stage in semantics.stages
        for invariant in stage.expected_invariants
    }
    for role in contract.required_entity_roles:
        if role not in roles:
            issues.append(ContractIssue("missing_entity_role", contract.topic_id, role))
    for relation in contract.required_relations:
        if relation not in relations:
            issues.append(ContractIssue("missing_relation", contract.topic_id, relation))
    for primitive in contract.required_primitives:
        if primitive not in primitives and primitive != scene_family:
            issues.append(ContractIssue("missing_primitive", contract.topic_id, primitive))
    if len(semantics.stages) < contract.minimum_stage_count:
        issues.append(ContractIssue("insufficient_stages", contract.topic_id, str(contract.minimum_stage_count)))
    for invariant in contract.required_invariants:
        if invariant not in invariants:
            issues.append(ContractIssue("missing_invariant", contract.topic_id, invariant))
    for group in contract.distinguishable_role_groups:
        present = [role for role in group if role in roles]
        if len(present) != len(group):
            issues.append(ContractIssue("roles_not_distinguishable", contract.topic_id, ",".join(group)))
    return tuple(sorted(issues, key=lambda issue: (issue.code, issue.detail)))


__all__ = [
    "ContractIssue",
    "VisualContract",
    "contract_for",
    "validate_contract",
    "validate_contract_semantics",
]
