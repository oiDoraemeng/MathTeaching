"""Schema and closed-reference validation for teaching artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, Mapping

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from linear_algebra.catalog.model import LessonEntry
from linear_algebra.catalog.manifest import topic_entries

from .examples import verify_worked_example
from .model import TeachingArtifact
from .profiles import TeachingLevel, profile_for
from .schema import load_artifact_schema
from .source import SourceContext


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
    example_issues = validate_worked_examples(artifact)
    if reference_issues or example_issues:
        raise ArtifactValidationError((*reference_issues, *example_issues))
    return artifact


def validate_closed_references(artifact: TeachingArtifact) -> tuple[ValidationIssue, ...]:
    """Return deterministic diagnostics for duplicate IDs and unresolved graph edges."""
    issues: list[ValidationIssue] = []
    claims = artifact.claims
    connections = artifact.connections
    entities = artifact.visual_semantics.entities
    relations = artifact.visual_semantics.relations
    stages = artifact.visual_semantics.stages
    sections = artifact.explanation.sections
    spans = artifact.source.spans

    claim_ids = _collect_ids(issues, claims, "$.claims", "claim")
    _collect_ids(issues, connections, "$.connections", "connection")
    entity_ids = _collect_ids(issues, entities, "$.visual_semantics.entities", "entity")
    relation_ids = _collect_ids(issues, relations, "$.visual_semantics.relations", "relation")
    stage_ids = _collect_ids(issues, stages, "$.visual_semantics.stages", "stage")
    section_ids = _collect_ids(issues, sections, "$.explanation.sections", "explanation section")
    span_ids = _collect_ids(issues, spans, "$.source.spans", "source span")

    known_topic_ids = {topic.id for topic in topic_entries()}
    connected_topic_ids: set[str] = set()
    for connection_index, connection in enumerate(connections):
        path = f"$.connections[{connection_index}]"
        if connection.target_topic_id in connected_topic_ids:
            issues.append(
                ValidationIssue(
                    "duplicate_id",
                    f"{path}.target_topic_id",
                    f"duplicate connection topic id {connection.target_topic_id!r}",
                )
            )
        connected_topic_ids.add(connection.target_topic_id)
        _append_missing_refs(
            issues,
            (connection.target_topic_id,),
            known_topic_ids,
            f"{path}.target_topic_id",
            "topic",
        )
        _append_missing_refs(
            issues,
            connection.claim_refs,
            claim_ids,
            f"{path}.claim_refs",
            "claim",
        )

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


_VISUAL_SYMBOL_ROLES = frozenset(
    {
        "vector_a",
        "vector_b",
        "basis_e1",
        "basis_e2",
        "transformed_a",
        "transformed_b",
        "projection",
        "residual",
        "foot",
        "direction",
        "area",
        "volume",
    }
)


def validate_claim_bindings(artifact: TeachingArtifact) -> tuple[ValidationIssue, ...]:
    """Validate formula declarations and the visual evidence for every claim.

    Formula strings are presentation text.  They are deliberately not parsed as
    TeX here; the producer must declare the symbols in ``Claim.formula_symbols``.
    The declaration is checked against the explanation symbol table and visual
    entity IDs, while each evidence list is checked against the corresponding
    visual graph and its reverse claim link.
    """

    entities = artifact.visual_semantics.entities
    relations = artifact.visual_semantics.relations
    stages = artifact.visual_semantics.stages
    entity_ids = {entity.id for entity in entities}
    relation_ids = {relation.id for relation in relations}
    stage_ids = {stage.id for stage in stages}
    known_symbols = set(artifact.explanation.symbol_roles) | entity_ids
    issues: list[ValidationIssue] = []

    for claim_index, claim in enumerate(artifact.claims):
        path = f"$.claims[{claim_index}]"
        for symbol_index, symbol in enumerate(claim.formula_symbols):
            if symbol not in known_symbols:
                issues.append(
                    ValidationIssue(
                        "unbound_formula_symbol",
                        f"{path}.formula_symbols[{symbol_index}]",
                        f"formula symbol {symbol!r} is not declared in explanation.symbol_roles or visual entities",
                    )
                )

        evidence = (
            ("entity_refs", claim.entity_refs, entity_ids, entities, "entity"),
            ("relation_refs", claim.relation_refs, relation_ids, relations, "relation"),
        )
        for field, references, known_ids, records, label in evidence:
            field_path = f"{path}.{field}"
            if not references:
                issues.append(
                    ValidationIssue(
                        "claim_missing_evidence",
                        field_path,
                        f"claim {claim.id!r} has no visual {label} evidence",
                    )
                )
                continue
            _append_missing_refs(issues, references, known_ids, field_path, label)
            for reference_index, reference in enumerate(references):
                if reference not in known_ids:
                    continue
                record = next(item for item in records if item.id == reference)
                if claim.id not in record.claim_refs:
                    issues.append(
                        ValidationIssue(
                            "claim_missing_evidence",
                            f"{field_path}[{reference_index}]",
                            f"{label} {reference!r} does not link back to claim {claim.id!r}",
                        )
                    )

        stage_path = f"{path}.stage_refs"
        if not claim.stage_refs:
            issues.append(
                ValidationIssue(
                    "claim_missing_evidence",
                    stage_path,
                    f"claim {claim.id!r} has no visual stage evidence",
                )
            )
        else:
            _append_missing_refs(issues, claim.stage_refs, stage_ids, stage_path, "stage")
            referenced_relations = set(claim.relation_refs) & relation_ids
            referenced_entities = set(claim.entity_refs) & entity_ids
            for stage_index, stage_id in enumerate(claim.stage_refs):
                if stage_id not in stage_ids:
                    continue
                stage = next(item for item in stages if item.id == stage_id)
                visible = (
                    set(stage.input_entity_refs)
                    | set(stage.output_entity_refs)
                    | set(stage.relation_refs)
                )
                if not visible & (referenced_entities | referenced_relations):
                    issues.append(
                        ValidationIssue(
                            "claim_missing_evidence",
                            f"{stage_path}[{stage_index}]",
                            f"stage {stage_id!r} contains no evidence linked by claim {claim.id!r}",
                        )
                    )

        # A declared visual role is meaningful only when the claim actually
        # references a matching entity.  This catches, for example, a
        # projection formula that mentions a residual while the residual entity
        # was omitted from the storyboard.
        referenced_entities = set(claim.entity_refs) & entity_ids
        for symbol in claim.formula_symbols:
            role = artifact.explanation.symbol_roles.get(symbol)
            if role not in _VISUAL_SYMBOL_ROLES:
                continue
            if not any(
                entity.id in referenced_entities
                and (entity.id == symbol or entity.role == role)
                for entity in entities
            ):
                issues.append(
                    ValidationIssue(
                        "claim_missing_evidence",
                        f"{path}.entity_refs",
                        f"formula symbol {symbol!r} with visual role {role!r} has no referenced visual entity",
                    )
                )

    return tuple(_sorted_issues(issues))


def validate_source_evidence(
    artifact: TeachingArtifact,
    context: SourceContext,
    entry: LessonEntry,
) -> tuple[ValidationIssue, ...]:
    """Check that claims still cite the current lecture source context."""

    issues: list[ValidationIssue] = []
    entry_id = entry.id
    expected_heading_path = entry.source_anchor.heading_path

    if artifact.topic_id != entry_id:
        issues.append(ValidationIssue("topic_mismatch", "$.topic_id", artifact.topic_id))
    if artifact.source.heading_path != expected_heading_path:
        issues.append(
            ValidationIssue("source_anchor_mismatch", "$.source.heading_path", str(entry_id))
        )
    if artifact.source.source_hash != context.source_hash:
        issues.append(ValidationIssue("stale_source", "$.source.source_hash", str(entry_id)))

    allowed_spans = {span.id for span in context.spans}
    for claim_index, claim in enumerate(artifact.claims):
        for ref_index, span_id in enumerate(claim.source_refs):
            if span_id not in allowed_spans:
                issues.append(
                    ValidationIssue(
                        "source_ref_out_of_context",
                        f"$.claims[{claim_index}].source_refs[{ref_index}]",
                        span_id,
                    )
                )
    return tuple(_sorted_issues(issues))


def validate_teaching_depth(artifact: TeachingArtifact) -> tuple[ValidationIssue, ...]:
    """Check explicit L0-L4 content without inferring depth from prose length."""

    profile = profile_for(artifact.topic_id)
    explanation = artifact.explanation
    presence = explanation.section_presence()
    issues: list[ValidationIssue] = []

    for section in sorted(set(profile.required_sections)):
        if not presence.get(section, False):
            issues.append(
                ValidationIssue(
                    "missing_profile_section",
                    f"$.explanation.{section}",
                    section,
                )
            )

    if profile.minimum_level >= TeachingLevel.CALCULATE and not explanation.worked_examples:
        issues.append(
            ValidationIssue(
                "missing_worked_example",
                "$.explanation.worked_examples",
                artifact.topic_id,
            )
        )
    if profile.minimum_level >= TeachingLevel.EXPLAIN:
        if not explanation.geometric_meaning.strip():
            issues.append(
                ValidationIssue(
                    "missing_geometric_meaning",
                    "$.explanation.geometric_meaning",
                    artifact.topic_id,
                )
            )
        if not explanation.invariants:
            issues.append(
                ValidationIssue("missing_invariant", "$.explanation.invariants", artifact.topic_id)
            )
    if profile.minimum_level >= TeachingLevel.TRANSFER:
        if not explanation.connections:
            issues.append(
                ValidationIssue("missing_connection", "$.explanation.connections", artifact.topic_id)
            )
        if not explanation.transfer_note.strip():
            issues.append(
                ValidationIssue("missing_transfer_note", "$.explanation.transfer_note", artifact.topic_id)
            )
    if profile.requires_analogy_boundary and not explanation.analogy_boundary.strip():
        issues.append(
            ValidationIssue(
                "missing_analogy_boundary",
                "$.explanation.analogy_boundary",
                artifact.topic_id,
            )
        )
    return tuple(_sorted_issues(issues))


def validate_worked_examples(artifact: TeachingArtifact) -> tuple[ValidationIssue, ...]:
    """Return diagnostics for every machine-checkable worked example."""

    issues: list[ValidationIssue] = []
    for index, example in enumerate(artifact.explanation.worked_examples):
        result = verify_worked_example(example)
        path = f"$.explanation.worked_examples[{index}]"
        if result.manual_review:
            issues.append(ValidationIssue("manual_review_required", path, result.reason or example.kind))
        elif not result.valid:
            issues.append(ValidationIssue("worked_example_mismatch", path, example.kind))
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
            issue_path = path if path.endswith(("source_ref", "target_ref", "target_topic_id")) else f"{path}[{index}]"
            issues.append(
                ValidationIssue("dangling_reference", issue_path, f"unknown {label} reference {reference!r}")
            )


def _sorted_issues(issues: Iterable[ValidationIssue]) -> list[ValidationIssue]:
    return sorted(issues, key=lambda issue: (issue.path, issue.code, issue.message))


__all__ = [
    "ArtifactValidationError",
    "ValidationIssue",
    "validate_artifact_payload",
    "validate_claim_bindings",
    "validate_closed_references",
    "validate_source_evidence",
    "validate_teaching_depth",
    "validate_worked_examples",
]
