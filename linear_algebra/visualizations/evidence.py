"""Claim-to-plan evidence checks for compiled teaching artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from linear_algebra.teaching.model import TeachingArtifact

if TYPE_CHECKING:
    from .compiler import CompiledVisualization


@dataclass(frozen=True)
class EvidenceIssue:
    code: str
    claim_id: str
    path: str
    message: str


@dataclass(frozen=True)
class ClaimEvidence:
    claim_id: str
    entity_ids: tuple[str, ...]
    relation_ids: tuple[str, ...]
    stage_ids: tuple[str, ...]
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceLedger:
    entries: tuple[ClaimEvidence, ...]

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
        entry = ClaimEvidence(claim.id, entity_ids, relation_ids, tuple(stage_ids), aliases)
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
    return EvidenceLedger(tuple(entries)), tuple(sorted(issues, key=lambda issue: (issue.claim_id, issue.code, issue.path, issue.message)))


__all__ = ["ClaimEvidence", "EvidenceIssue", "EvidenceLedger", "build_evidence_ledger"]
