"""Schema and closed-reference validation for teaching artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, Mapping

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from .model import TeachingArtifact
from .schema import load_artifact_schema


@dataclass(frozen=True)
class ValidationIssue:
    """A stable, JSON-path-addressed artifact validation diagnostic."""

    code: str
    path: str
    message: str


class ArtifactValidationError(ValueError):
    """Raised when an artifact fails schema or closed-reference validation."""

    def __init__(self, issues: Iterable[ValidationIssue]) -> None:
        self.issues = tuple(_sorted_issues(issues))
        super().__init__("; ".join(f"{issue.path}: {issue.message}" for issue in self.issues))


def validate_artifact_payload(payload: Mapping[str, object]) -> TeachingArtifact:
    """Decode a schema-valid payload whose graph contains no dangling references."""
    schema_issues = _jsonschema_issues(payload)
    if schema_issues:
        raise ArtifactValidationError(schema_issues)

    try:
        artifact = TeachingArtifact.from_dict(payload)
    except (TypeError, ValueError) as error:
        raise ArtifactValidationError((_model_issue(error),)) from None

    reference_issues = validate_closed_references(artifact)
    if reference_issues:
        raise ArtifactValidationError(reference_issues)
    return artifact


def validate_closed_references(artifact: TeachingArtifact) -> tuple[ValidationIssue, ...]:
    """Return deterministic diagnostics for duplicate IDs and unresolved graph edges."""
    issues: list[ValidationIssue] = []
    claims = artifact.claims
    entities = artifact.visual_semantics.entities
    relations = artifact.visual_semantics.relations
    stages = artifact.visual_semantics.stages
    sections = artifact.explanation.sections
    spans = artifact.source.spans

    claim_ids = _collect_ids(issues, claims, "$.claims", "claim")
    entity_ids = _collect_ids(issues, entities, "$.visual_semantics.entities", "entity")
    relation_ids = _collect_ids(issues, relations, "$.visual_semantics.relations", "relation")
    stage_ids = _collect_ids(issues, stages, "$.visual_semantics.stages", "stage")
    section_ids = _collect_ids(issues, sections, "$.explanation.sections", "explanation section")
    span_ids = _collect_ids(issues, spans, "$.source.spans", "source span")

    for claim_index, claim in enumerate(claims):
        path = f"$.claims[{claim_index}]"
        _append_missing_refs(issues, claim.source_refs, span_ids, f"{path}.source_refs", "source span")
        _append_missing_refs(issues, claim.explanation_refs, section_ids, f"{path}.explanation_refs", "explanation section")
        _append_missing_refs(issues, claim.entity_refs, entity_ids, f"{path}.entity_refs", "entity")
        _append_missing_refs(issues, claim.relation_refs, relation_ids, f"{path}.relation_refs", "relation")
        _append_missing_refs(issues, claim.stage_refs, stage_ids, f"{path}.stage_refs", "stage")

    for section_index, section in enumerate(sections):
        _append_missing_refs(
            issues,
            section.claim_refs,
            claim_ids,
            f"$.explanation.sections[{section_index}].claim_refs",
            "claim",
        )

    for entity_index, entity in enumerate(entities):
        _append_missing_refs(
            issues,
            entity.claim_refs,
            claim_ids,
            f"$.visual_semantics.entities[{entity_index}].claim_refs",
            "claim",
        )

    for relation_index, relation in enumerate(relations):
        path = f"$.visual_semantics.relations[{relation_index}]"
        _append_missing_refs(issues, (relation.source_ref,), entity_ids, f"{path}.source_ref", "entity")
        _append_missing_refs(issues, (relation.target_ref,), entity_ids, f"{path}.target_ref", "entity")
        _append_missing_refs(issues, relation.claim_refs, claim_ids, f"{path}.claim_refs", "claim")

    for stage_index, stage in enumerate(stages):
        path = f"$.visual_semantics.stages[{stage_index}]"
        _append_missing_refs(issues, stage.input_entity_refs, entity_ids, f"{path}.input_entity_refs", "entity")
        _append_missing_refs(issues, stage.output_entity_refs, entity_ids, f"{path}.output_entity_refs", "entity")
        _append_missing_refs(issues, stage.relation_refs, relation_ids, f"{path}.relation_refs", "relation")

    return tuple(_sorted_issues(issues))


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    return Draft202012Validator(load_artifact_schema())


def _jsonschema_issues(payload: object) -> tuple[ValidationIssue, ...]:
    errors = _validator().iter_errors(payload)
    return tuple(
        _sorted_issues(
            ValidationIssue("schema_validation", _json_path(error), error.message)
            for error in errors
        )
    )


def _model_issue(error: Exception) -> ValidationIssue:
    text = str(error)
    path, separator, message = text.partition(": ")
    if separator and path.startswith("$"):
        return ValidationIssue("model_validation", path, message)
    return ValidationIssue("model_validation", "$", text)


def _json_path(error: ValidationError) -> str:
    path = "$"
    for part in error.absolute_path:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    if error.validator == "required":
        missing = error.validator_value
        if isinstance(missing, list):
            for name in missing:
                if name not in error.instance:
                    return f"{path}.{name}"
    return path


def _collect_ids(
    issues: list[ValidationIssue], items: Iterable[object], path: str, label: str
) -> set[str]:
    identifiers: set[str] = set()
    for index, item in enumerate(items):
        identifier = item.id  # type: ignore[attr-defined]
        if identifier in identifiers:
            issues.append(
                ValidationIssue("duplicate_id", f"{path}[{index}].id", f"duplicate {label} id {identifier!r}")
            )
        identifiers.add(identifier)
    return identifiers


def _append_missing_refs(
    issues: list[ValidationIssue],
    references: Iterable[str],
    known_ids: set[str],
    path: str,
    label: str,
) -> None:
    for index, reference in enumerate(references):
        if reference not in known_ids:
            issue_path = path if path.endswith(("source_ref", "target_ref")) else f"{path}[{index}]"
            issues.append(
                ValidationIssue("dangling_reference", issue_path, f"unknown {label} reference {reference!r}")
            )


def _sorted_issues(issues: Iterable[ValidationIssue]) -> list[ValidationIssue]:
    return sorted(issues, key=lambda issue: (issue.path, issue.code, issue.message))


__all__ = [
    "ArtifactValidationError",
    "ValidationIssue",
    "validate_artifact_payload",
    "validate_closed_references",
]
