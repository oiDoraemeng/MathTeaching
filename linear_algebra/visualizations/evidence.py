"""Claim-to-plan evidence checks for compiled teaching artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Mapping

from linear_algebra.teaching.model import TeachingArtifact

if TYPE_CHECKING:
    from .compiler import CompiledVisualization


@dataclass(frozen=True)
class EvidenceIssue:
    code: str
    claim_id: str
    path: str
    message: str
    topic_id: str = ""


@dataclass(frozen=True)
class ClaimEvidence:
    claim_id: str
    entity_ids: tuple[str, ...]
    relation_ids: tuple[str, ...]
    stage_ids: tuple[str, ...]
    aliases: tuple[str, ...]
    operation_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvidenceLedger:
    entries: tuple[ClaimEvidence, ...]
    endpoint_error: float | None = None
    cross_term_after_rotation: float | None = None

    def for_claim(self, claim_id: str) -> ClaimEvidence | None:
        return next((entry for entry in self.entries if entry.claim_id == claim_id), None)


def build_evidence_ledger(
    artifact: TeachingArtifact, compiled: "CompiledVisualization"
) -> tuple[EvidenceLedger, tuple[EvidenceIssue, ...]]:
    """Build deterministic claim evidence from aliases emitted by a plan."""

    entities = {entity.id: entity for entity in artifact.visual_semantics.entities}
    relations = {relation.id: relation for relation in artifact.visual_semantics.relations}
    stages = {stage.id: stage for stage in artifact.visual_semantics.stages}
    entries: list[ClaimEvidence] = []
    issues: list[EvidenceIssue] = []
    for claim in artifact.claims:
        entity_ids = tuple(ref for ref in claim.entity_refs if compiled.aliases_for(ref))
        relation_ids = tuple(ref for ref in claim.relation_refs if compiled.aliases_for(ref))
        aliases = tuple(
            alias
            for ref in (*entity_ids, *relation_ids)
            for alias in compiled.aliases_for(ref)
        )
        stage_ids: list[str] = []
        for stage_id in claim.stage_refs:
            stage = stages.get(stage_id)
            if stage is None:
                continue
            visible_refs = (*stage.input_entity_refs, *stage.output_entity_refs, *stage.relation_refs)
            if any(compiled.aliases_for(ref) for ref in visible_refs):
                stage_ids.append(stage_id)
        claim_aliases = set(aliases)
        operation_names = tuple(sorted({
            str(operation.get("op"))
            for operation in getattr(getattr(compiled, "plan", None), "operations", ())
            if isinstance(operation, Mapping)
            and str(operation.get("alias", "")) in claim_aliases
        }))
        entry = ClaimEvidence(claim.id, entity_ids, relation_ids, tuple(stage_ids), aliases, operation_names)
        entries.append(entry)

        for index, ref in enumerate(claim.entity_refs):
            if ref not in entities or not compiled.aliases_for(ref):
                issues.append(EvidenceIssue("missing_entity_alias", claim.id, f"$.claims[{claim.id}].entity_refs[{index}]", ref))
        for index, ref in enumerate(claim.relation_refs):
            relation = relations.get(ref)
            if relation is None or not compiled.aliases_for(ref):
                issues.append(EvidenceIssue("missing_relation_alias", claim.id, f"$.claims[{claim.id}].relation_refs[{index}]", ref))
                continue
            for endpoint in (relation.source_ref, relation.target_ref):
                if not compiled.aliases_for(endpoint):
                    issues.append(EvidenceIssue("missing_endpoint_evidence", claim.id, f"$.claims[{claim.id}].relation_refs[{index}]", endpoint))
        if not entity_ids:
            issues.append(EvidenceIssue("missing_entity_evidence", claim.id, "$.claims", "claim has no compiled entity evidence"))
        if not relation_ids:
            issues.append(EvidenceIssue("missing_relation_evidence", claim.id, "$.claims", "claim has no compiled relation evidence"))
        if not stage_ids:
            issues.append(EvidenceIssue("missing_stage_evidence", claim.id, "$.claims", "claim has no visible compiled stage"))
        for index, stage_id in enumerate(claim.stage_refs):
            if stage_id in stages and stage_id not in stage_ids:
                issues.append(EvidenceIssue("stage_without_visible_evidence", claim.id, f"$.claims[{claim.id}].stage_refs[{index}]", stage_id))
    family_evidence = getattr(compiled, 'family_evidence', None)
    endpoint_error = family_evidence.get('endpoint_error') if isinstance(family_evidence, Mapping) else None
    cross_term = family_evidence.get('cross_term_after_rotation') if isinstance(family_evidence, Mapping) else None
    return EvidenceLedger(tuple(entries), endpoint_error, cross_term), tuple(sorted(issues, key=lambda issue: (issue.claim_id, issue.code, issue.path, issue.message)))


def validate_extended_evidence(
    bundle: Any,
    *,
    registry: Any | None = None,
) -> tuple[EvidenceIssue, ...]:
    """Validate the cross-layer evidence contract for one topic bundle.

    The function accepts a ``CurriculumBundle`` as well as a small test
    fixture exposing ``topic``, ``artifact`` and ``compiled`` attributes (or
    a two-item ``(artifact, compiled)`` tuple).  It only follows stable IDs;
    it never infers evidence from labels or command text.
    """

    topic = getattr(bundle, "topic", None)
    artifact = getattr(bundle, "artifact", None)
    compiled = getattr(bundle, "compiled", None)
    if artifact is None and isinstance(bundle, (tuple, list)) and len(bundle) >= 2:
        artifact, compiled = bundle[0], bundle[1]
    topic_id = str(getattr(topic, "id", getattr(artifact, "topic_id", "")))
    issues: list[EvidenceIssue] = []
    if artifact is None or compiled is None:
        return (EvidenceIssue("missing_bundle_surface", "", "$.bundle", "artifact and compiled surfaces are required", topic_id),)

    if registry is None:
        from linear_algebra.registry import catalog_registry
        registry = catalog_registry()
    try:
        topic = topic or registry.get_topic(topic_id)
    except (AttributeError, KeyError):
        topic = None

    plan = getattr(compiled, "plan", None)
    operation_names: set[str] = set()
    if plan is not None:
        try:
            from services.scene_commands import SceneCommandService
            validation = SceneCommandService().validate(plan)
            operation_names = {
                str(item.get("op"))
                for item in validation.expanded_operations
                if isinstance(item, Mapping)
            }
        except Exception:
            operation_names = {
                str(item.get("op"))
                for item in getattr(plan, "operations", ())
                if isinstance(item, Mapping)
            }
    if topic is not None:
        capabilities = getattr(registry, "capabilities", {})
        declarative_skips = {
            "vector_3d", "oriented_area_2d", "transformed_grid",
            "subspace_region", "parallelepiped_3d", "oriented_volume_3d",
        }
        family_equivalents = {
            "transformed_grid": {"geometry.mapping_bundle", "geometry.basis_grid", "geometry.staged_transform", "geometry.transformed_grid"},
            "subspace_region": {"geometry.subspace3d", "geometry.affine_solution", "geometry.constraint", "geometry.intersection", "geometry.matrix_tableau", "geometry.elimination_tableau", "geometry.least_squares"},
            "staged_transform": {"geometry.mapping_bundle", "geometry.basis_grid", "geometry.transformed_grid"},
            "parallelepiped_3d": {"geometry.subspace3d", "geometry.oriented_volume", "geometry.parallelogram3d"},
            "oriented_volume_3d": {"geometry.subspace3d", "geometry.oriented_volume"},
        }
        for capability in tuple(getattr(topic, "required_capabilities", ())):
            expected = capabilities.get(capability) if isinstance(capabilities, Mapping) else None
            if expected is None:
                issues.append(EvidenceIssue("unknown_capability", "", "$.required_capabilities", capability, topic_id))
            elif expected not in operation_names:
                scene = str(getattr(plan, "scene", ""))
                if capability in declarative_skips and (
                    (capability in {"vector_3d", "oriented_volume_3d", "parallelepiped_3d"} and scene == "2d")
                    or (capability == "oriented_area_2d" and scene == "3d")
                    or (capability in {"transformed_grid", "subspace_region"} and scene == "3d")
                ):
                    continue
                if capability in family_equivalents and operation_names.intersection(family_equivalents[capability]):
                    continue
                issues.append(EvidenceIssue("missing_actual_operation", "", "$.plan.operations", expected, topic_id))

    entities = {str(item.id): item for item in tuple(getattr(artifact.visual_semantics, "entities", ())) }
    relations = {str(item.id): item for item in tuple(getattr(artifact.visual_semantics, "relations", ())) }
    aliases_for = getattr(compiled, "aliases_for", lambda _ref: ())
    explanation = getattr(artifact, "explanation", None)
    symbol_roles = getattr(explanation, "symbol_roles", {})
    if not isinstance(symbol_roles, Mapping):
        symbol_roles = {}
    entity_tokens = {
        token
        for entity in entities.values()
        for token in (str(getattr(entity, "id", "")), str(getattr(entity, "label", "")), str(getattr(entity, "role", "")))
        if token
    }
    for claim in tuple(getattr(artifact, "claims", ())):
        for index, symbol in enumerate(tuple(getattr(claim, "formula_symbols", ()) )):
            symbol = str(symbol)
            if symbol not in symbol_roles and symbol not in entity_tokens:
                issues.append(EvidenceIssue("unbound_formula_variable", str(claim.id), f"$.claims[{claim.id}].formula_symbols[{index}]", symbol, topic_id))
        for index, ref in enumerate(tuple(getattr(claim, "relation_refs", ()) )):
            relation = relations.get(str(ref))
            if relation is None:
                issues.append(EvidenceIssue("missing_relation_contract", str(claim.id), f"$.claims[{claim.id}].relation_refs[{index}]", str(ref), topic_id))
                continue
            if not aliases_for(str(ref)):
                issues.append(EvidenceIssue("missing_relation_alias", str(claim.id), f"$.claims[{claim.id}].relation_refs[{index}]", str(ref), topic_id))
            for endpoint in (getattr(relation, "source_ref", ""), getattr(relation, "target_ref", "")):
                if str(endpoint) not in entities or not aliases_for(str(endpoint)):
                    issues.append(EvidenceIssue("missing_endpoint_evidence", str(claim.id), f"$.relations[{ref}].endpoint", str(endpoint), topic_id))

    _, ledger_issues = build_evidence_ledger(artifact, compiled)
    for issue in ledger_issues:
        issues.append(EvidenceIssue(issue.code, issue.claim_id, issue.path, issue.message, topic_id))
    return tuple(sorted(set(issues), key=lambda issue: (issue.topic_id, issue.claim_id, issue.code, issue.path, issue.message)))


__all__ = ["ClaimEvidence", "EvidenceIssue", "EvidenceLedger", "build_evidence_ledger", "validate_extended_evidence"]
