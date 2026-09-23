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
    required_role_types: tuple[tuple[str, str, int], ...] = ()
    required_relation_endpoints: tuple[tuple[str, str, str, str], ...] = ()
    # 保留旧首关系字段，并以完整集合执行第 4 章严格校验。
    required_relation_kinds: tuple[str, ...] = ()
    required_parameters: tuple[tuple[str, tuple[str, ...]], ...] = ()
    expected_operations: tuple[str, ...] = ()
    required_stage_names: tuple[str, ...] = ()


def contract_for(topic_id: str) -> VisualContract:
    """Return a stable contract for every catalog topic ID."""

    topic = next((item for item in topic_entries() if item.id == topic_id), None)
    if topic is None:
        raise KeyError(f"unknown visual contract topic: {topic_id}")
    base = VisualContract(topic_id, (), (), (), (), 0 if not topic.required_capabilities else 1)
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
            topic_id, (), ("neutral", "vector_a", "vector_b"),
            ("composition_order", "endpoint_diff", "compare"), (), 4,
            distinguishable_role_groups=(("vector_a", "vector_b"),),
        ),
        "ch02.matrix.powers": VisualContract(
            topic_id, (), ("vector_a", "vector_b"), ("invariant",), ("grid",), 2,
            distinguishable_role_groups=(("vector_a", "vector_b"),),
        ),
        "ch03.det.multiplicativity": VisualContract(
            topic_id, (), (), ("same_measure", "composition_order"), (), 3,
        ),
        "ch03.det.basic-properties": VisualContract(
            topic_id, (), (), ("same_measure",), (), 4,
        ),
        "ch03.det.transpose": VisualContract(
            topic_id, (), (), ("same_measure",), (), 2,
        ),
    }
    extended_family = {
        **{topic: "subspace_region" for topic in (
            "ch04.subspace.col-null", "ch04.dependence.redundancy", "ch04.basis.definition", "ch04.linear-map.definition")},
        **{topic: "affine_solution" for topic in ("ch05.homogeneous.solution-space", "ch05.affine.solution-set", "ch05.consistency.geometry", "ch05.gaussian-elimination", "ch05.least-squares.projection")},
        **{topic: "basis_change" for topic in ("ch06.basis-change.coordinates", "ch06.similarity-transform")},
        **{topic: "spectral_orthogonal" for topic in ("ch07.eigen.direction", "ch07.characteristic-polynomial", "ch07.eigenspace", "ch07.diagonalization")},
        **{topic: "quadratic_level_set" for topic in ("ch08.quadratic.matrix-form", "ch08.quadratic.level-sets", "ch08.principal-axis", "ch08.definiteness")},
    }
    if topic_id in extended_family:
        if topic_id.startswith("ch04."):
            semantic = semantic_for(topic_id)
            return VisualContract(
                topic_id,
                (f"claim.{topic_id}",),
                semantic.roles,
                (semantic.relation,),
                (semantic.primitive,),
                len(semantic.stages),
                semantic.invariants,
                required_role_types=tuple((item.role, item.kind, item.dimension) for item in semantic.entities),
                required_relation_endpoints=tuple(
                    (item.name, item.kind, item.source_role, item.target_role)
                    for item in semantic.relations
                ),
                required_relation_kinds=tuple(dict.fromkeys(item.kind for item in semantic.relations)),
                required_parameters=tuple(
                    (item.name, item.parameter_names) for item in semantic.relations
                ),
                expected_operations=semantic.expected_operations,
            )
        family = extended_family[topic_id]
        if topic_id.startswith("ch05."):
            from linear_algebra.chapter_05_semantics import spec_for
            spec = spec_for(topic_id.removeprefix("ch05."))
            relation_name = spec.relation
            return VisualContract(
                topic_id, (f"claim.{topic_id}",), spec.roles, (relation_name,), (spec.primitive,),
                len(spec.stages), spec.invariants,
                required_relation_kinds=(relation_name,),
                required_parameters=((relation_name, tuple(spec.params)),),
                expected_operations=(spec.operation,),
                required_role_types=tuple((role, spec.kind_for(role), spec.dimension_for(role)) for role in spec.roles),
                required_relation_endpoints=((relation_name, relation_name, spec.roles[0], spec.roles[-1]),),
                required_stage_names=spec.stages,
            )
        if topic_id.startswith("ch06."):
            from linear_algebra.chapter_06_semantics import spec_for
            spec=spec_for(topic_id.removeprefix('ch06.'))
            kinds=tuple(dict.fromkeys(r.kind for r in spec.relations)); names=tuple(r.name for r in spec.relations)
            params=tuple((r.name,tuple(name for name,_ in r.parameters)) for r in spec.relations)
            endpoints=tuple((r.name,r.kind,r.source_role,r.target_role) for r in spec.relations)
            return VisualContract(topic_id,(f'claim.{topic_id}',),spec.roles,kinds,(spec.operations[0],),len(spec.stages),spec.invariants,required_relation_kinds=kinds,required_parameters=params,expected_operations=spec.operations,required_role_types=tuple((e.role,e.kind,e.dimension) for e in spec.entities),required_relation_endpoints=endpoints,required_stage_names=tuple(s.name for s in spec.stages))
        if topic_id.startswith(("ch07.", "ch08.")):
            if topic_id.startswith('ch08.'):
                from linear_algebra.chapter_08_semantics import spec_for
            else:
                from linear_algebra.chapter_07_semantics import spec_for
            spec = spec_for(topic_id)
            kinds = tuple(dict.fromkeys(r.kind for r in spec.relations))
            names = tuple(r.name for r in spec.relations)
            endpoints = tuple((r.name, r.kind, r.source_role, r.target_role) for r in spec.relations)
            params = tuple((r.name, tuple(name for name, _ in r.parameters)) for r in spec.relations)
            return VisualContract(topic_id, (f"claim.{topic_id}",), spec.roles, kinds, (), len(spec.stages), spec.invariants, required_relation_kinds=kinds, required_parameters=params, expected_operations=spec.operations, required_role_types=tuple((e.role,e.kind,e.dimension) for e in spec.entities), required_relation_endpoints=endpoints, required_stage_names=tuple(s.name for s in spec.stages))
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
    entities_by_role = {entity.role: entity for entity in semantics.entities}
    entities_by_id = {entity.id: entity for entity in semantics.entities}
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
    for relation in contract.required_relation_kinds:
        if relation not in relations:
            issues.append(ContractIssue("missing_relation", contract.topic_id, relation))
    # 第 4 章校验完整类型图，其余章节仍使用旧图元校验。
    if not contract.topic_id.startswith(("ch04.", "ch05.", "ch06.")):
        for primitive in contract.required_primitives:
            if primitive not in primitives:
                issues.append(ContractIssue("missing_primitive", contract.topic_id, primitive))
    if len(semantics.stages) < contract.minimum_stage_count:
        issues.append(ContractIssue("insufficient_stages", contract.topic_id, str(contract.minimum_stage_count)))
    for invariant in contract.required_invariants:
        if invariant not in invariants:
            issues.append(ContractIssue("missing_invariant", contract.topic_id, invariant))
    if contract.required_stage_names:
        stage_names = {stage.id.rsplit(".", 1)[-1] for stage in semantics.stages}
        stage_titles = {stage.title for stage in semantics.stages}
        for name in contract.required_stage_names:
            if name not in stage_names and name not in stage_titles:
                issues.append(ContractIssue("missing_stage", contract.topic_id, name))
    for group in contract.distinguishable_role_groups:
        present = [role for role in group if role in roles]
        if len(present) != len(group):
            issues.append(ContractIssue("roles_not_distinguishable", contract.topic_id, ",".join(group)))
    for role, kind, dimension in contract.required_role_types:
        entity = entities_by_role.get(role)
        if entity is not None and (entity.kind != kind or entity.dimension != dimension):
            issues.append(ContractIssue("entity_type_mismatch", contract.topic_id, f"{role}:{kind}:{dimension}"))
    relations_by_name = {
        relation.id.rsplit(".", 1)[-1]: relation for relation in semantics.relations
    }
    if semantics.relations:
        for name, kind, source_role, target_role in contract.required_relation_endpoints:
            relation = relations_by_name.get(name)
            if relation is None:
                issues.append(ContractIssue("missing_relation_spec", contract.topic_id, name))
                continue
            source = entities_by_id.get(relation.source_ref)
            target = entities_by_id.get(relation.target_ref)
            if relation.kind != kind or source is None or target is None or source.role != source_role or target.role != target_role:
                issues.append(ContractIssue("relation_endpoint_mismatch", contract.topic_id, name))
    for name, parameter_names in contract.required_parameters:
        relation = relations_by_name.get(name)
        if relation is None:
            continue
        for parameter in parameter_names:
            if parameter not in relation.parameters:
                issues.append(ContractIssue("missing_relation_parameter", contract.topic_id, f"{name}.{parameter}"))
    return tuple(sorted(issues, key=lambda issue: (issue.code, issue.detail)))


__all__ = [
    "ContractIssue",
    "VisualContract",
    "contract_for",
    "validate_contract",
    "validate_contract_semantics",
]
