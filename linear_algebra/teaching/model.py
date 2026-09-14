"""Immutable, JSON-safe records for lecture-grounded teaching artifacts.

The records in this module deliberately describe mathematics and storyboard
semantics only.  They carry no rendering commands or host application objects.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from types import MappingProxyType
from typing import Literal, Mapping, TypeAlias

from .source import SourceContext, SourceSpan
from .vocabulary import (
    ENTITY_KINDS,
    LAYOUTS,
    RELATION_KINDS,
    RELATION_STYLES,
    VECTOR_DIMENSIONS,
    validate_semantic_value,
)


ArtifactStatus: TypeAlias = Literal["draft", "reviewed", "published"]
SceneKind: TypeAlias = Literal["2d", "3d"]
StageLayout: TypeAlias = Literal["overlay", "side_by_side", "sequence"]
JsonScalar: TypeAlias = None | bool | int | float | str
JsonValue: TypeAlias = JsonScalar | tuple["JsonValue", ...] | Mapping[str, "JsonValue"]


@dataclass(frozen=True)
class SourceRecord:
    """A filesystem-free snapshot of the context used to create an artifact."""

    source_path: tuple[str, ...]
    heading_path: tuple[str, ...]
    heading_level: int
    occurrence: int
    excerpt: str
    source_hash: str
    spans: tuple[SourceSpan, ...]
    neighboring_titles: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_path", _constructor_string_tuple(self.source_path, "source_path"))
        object.__setattr__(self, "heading_path", _constructor_string_tuple(self.heading_path, "heading_path"))
        object.__setattr__(self, "heading_level", _constructor_integer(self.heading_level, "heading_level"))
        object.__setattr__(self, "occurrence", _constructor_integer(self.occurrence, "occurrence"))
        object.__setattr__(self, "excerpt", _constructor_string(self.excerpt, "excerpt"))
        object.__setattr__(self, "source_hash", _constructor_string(self.source_hash, "source_hash"))
        object.__setattr__(self, "spans", _constructor_instance_tuple(self.spans, "spans", SourceSpan))
        object.__setattr__(self, "neighboring_titles", _constructor_string_tuple(self.neighboring_titles, "neighboring_titles"))

    @classmethod
    def from_context(cls, context: SourceContext) -> "SourceRecord":
        return cls(
            source_path=context.source_path,
            heading_path=context.heading_path,
            heading_level=context.heading_level,
            occurrence=context.occurrence,
            excerpt=context.excerpt,
            source_hash=context.source_hash,
            spans=context.spans,
            neighboring_titles=context.neighboring_titles,
        )


@dataclass(frozen=True)
class TeachingProfileRecord:
    """Serialized teaching-depth requirements independent of profile policies."""

    minimum_level: int
    required_sections: tuple[str, ...]
    requires_analogy_boundary: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "minimum_level", _constructor_integer(self.minimum_level, "minimum_level"))
        object.__setattr__(self, "required_sections", _constructor_string_tuple(self.required_sections, "required_sections"))
        object.__setattr__(self, "requires_analogy_boundary", _constructor_boolean(self.requires_analogy_boundary, "requires_analogy_boundary"))


@dataclass(frozen=True)
class Claim:
    """One student-readable mathematical statement and its evidence links."""

    id: str
    statement: str
    formula: str | None
    formula_symbols: tuple[str, ...]
    source_refs: tuple[str, ...]
    explanation_refs: tuple[str, ...]
    entity_refs: tuple[str, ...]
    relation_refs: tuple[str, ...]
    stage_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _constructor_string(self.id, "id"))
        object.__setattr__(self, "statement", _constructor_string(self.statement, "statement"))
        object.__setattr__(self, "formula", _constructor_optional_string(self.formula, "formula"))
        for field in ("formula_symbols", "source_refs", "explanation_refs", "entity_refs", "relation_refs", "stage_refs"):
            object.__setattr__(self, field, _constructor_string_tuple(getattr(self, field), field))


@dataclass(frozen=True)
class TopicConnection:
    """A stable, claim-backed edge from this topic to a related topic."""

    id: str
    target_topic_id: str
    relation: str
    description: str
    claim_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _constructor_string(self.id, "id"))
        object.__setattr__(self, "target_topic_id", _constructor_string(self.target_topic_id, "target_topic_id"))
        object.__setattr__(self, "relation", _constructor_string(self.relation, "relation"))
        object.__setattr__(self, "description", _constructor_string(self.description, "description"))
        object.__setattr__(self, "claim_refs", _constructor_string_tuple(self.claim_refs, "claim_refs"))


@dataclass(frozen=True)
class ExplanationSection:
    """A claim-linked explanatory section, kept separate from the legacy type."""

    id: str
    title: str
    text: str
    claim_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _constructor_string(self.id, "id"))
        object.__setattr__(self, "title", _constructor_string(self.title, "title"))
        object.__setattr__(self, "text", _constructor_string(self.text, "text"))
        object.__setattr__(self, "claim_refs", _constructor_string_tuple(self.claim_refs, "claim_refs"))


@dataclass(frozen=True)
class WorkedExampleCheck:
    """One numeric assertion attached to a worked example."""

    name: str
    expected: JsonValue
    tolerance: float = 1e-9

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _constructor_string(self.name, "name"))
        object.__setattr__(self, "expected", _freeze_json(self.expected, "$.expected"))
        tolerance = _constructor_finite_float(self.tolerance, "tolerance")
        if tolerance < 0:
            raise ValueError("tolerance: expected non-negative number")
        object.__setattr__(self, "tolerance", tolerance)


@dataclass(frozen=True)
class WorkedExample:
    """Typed, bounded inputs for a reproducible mathematical calculation."""

    kind: str = "manual"
    given: JsonValue = None
    calculation: tuple[str, ...] = ()
    result: JsonValue = None
    checks: tuple[WorkedExampleCheck, ...] = ()
    id: str = ""
    title: str = ""
    claim_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", _constructor_string(self.kind, "kind"))
        object.__setattr__(self, "given", _freeze_json(self.given, "$.given"))
        object.__setattr__(self, "calculation", _constructor_string_tuple(self.calculation, "calculation"))
        object.__setattr__(self, "result", _freeze_json(self.result, "$.result"))
        object.__setattr__(
            self,
            "checks",
            _constructor_instance_tuple(self.checks, "checks", WorkedExampleCheck),
        )
        object.__setattr__(self, "id", _constructor_string(self.id, "id"))
        object.__setattr__(self, "title", _constructor_string(self.title, "title"))
        object.__setattr__(self, "claim_refs", _constructor_string_tuple(self.claim_refs, "claim_refs"))


@dataclass(frozen=True)
class TeachingCase:
    """One independently renderable, claim-backed teaching case."""

    id: str
    topic_id: str
    example_ref: str
    claim_refs: tuple[str, ...]
    stage_refs: tuple[str, ...]
    purpose: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _constructor_string(self.id, "id"))
        object.__setattr__(self, "topic_id", _constructor_string(self.topic_id, "topic_id"))
        object.__setattr__(self, "example_ref", _constructor_string(self.example_ref, "example_ref"))
        object.__setattr__(self, "claim_refs", _constructor_string_tuple(self.claim_refs, "claim_refs"))
        object.__setattr__(self, "stage_refs", _constructor_string_tuple(self.stage_refs, "stage_refs"))
        object.__setattr__(self, "purpose", _constructor_string(self.purpose, "purpose"))


@dataclass(frozen=True)
class CaseLayoutSpec:
    """Declarative case collection; pane count remains user-selectable at runtime."""

    default_pane_count: int
    cases: tuple[TeachingCase, ...]

    def __post_init__(self) -> None:
        count = _constructor_integer(self.default_pane_count, "default_pane_count")
        if count not in (1, 2, 3, 4):
            raise ValueError("default_pane_count: expected 1, 2, 3, or 4")
        object.__setattr__(self, "default_pane_count", count)
        object.__setattr__(self, "cases", _constructor_instance_tuple(self.cases, "cases", TeachingCase))


@dataclass(frozen=True)
class ExplanationContentV2:
    """Structured prose and the symbol-to-teaching-role mapping it uses."""

    title: str
    summary: str
    sections: tuple[ExplanationSection, ...]
    symbol_roles: Mapping[str, str]
    definition: str = ""
    formula: str = ""
    derivation: tuple[str, ...] = ()
    worked_examples: tuple[WorkedExample, ...] = ()
    intuition: str = ""
    geometric_meaning: str = ""
    conclusion: str = ""
    pitfalls: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()
    connections: tuple[str, ...] = ()
    analogy_boundary: str = ""
    transfer_note: str = ""
    read_guide: tuple[str, ...] = ()
    searchable_text: tuple[str, ...] = ()
    case_layout: CaseLayoutSpec | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "title", _constructor_string(self.title, "title"))
        object.__setattr__(self, "summary", _constructor_string(self.summary, "summary"))
        object.__setattr__(self, "sections", _constructor_instance_tuple(self.sections, "sections", ExplanationSection))
        object.__setattr__(self, "symbol_roles", _constructor_string_mapping(self.symbol_roles, "symbol_roles"))
        if self.case_layout is not None:
            object.__setattr__(self, "case_layout", _constructor_instance(self.case_layout, "case_layout", CaseLayoutSpec))
        for field in (
            "definition",
            "formula",
            "intuition",
            "geometric_meaning",
            "conclusion",
            "analogy_boundary",
            "transfer_note",
        ):
            object.__setattr__(self, field, _constructor_string(getattr(self, field), field))
        object.__setattr__(self, "derivation", _constructor_string_tuple(self.derivation, "derivation"))
        object.__setattr__(self, "worked_examples", _constructor_instance_tuple(self.worked_examples, "worked_examples", WorkedExample))
        for field in ("pitfalls", "invariants", "connections", "read_guide", "searchable_text"):
            object.__setattr__(self, field, _constructor_string_tuple(getattr(self, field), field))

    def section_presence(self) -> dict[str, bool]:
        """Return explicit presence flags used by teaching-depth validation."""

        section_text = {
            section.id: section.text.strip()
            for section in self.sections
            if section.text.strip()
        }
        return {
            "definition": bool(self.definition.strip() or section_text.get("definition")),
            "formula": bool(self.formula.strip() or section_text.get("formula")),
            "derivation": bool(self.derivation or section_text.get("derivation")),
            "worked_examples": bool(self.worked_examples or section_text.get("worked_examples")),
            "intuition": bool(self.intuition.strip() or section_text.get("intuition")),
            "geometric_meaning": bool(self.geometric_meaning.strip() or section_text.get("geometric_meaning")),
            "conclusion": bool(self.conclusion.strip() or section_text.get("conclusion")),
            "pitfalls": bool(self.pitfalls or section_text.get("pitfalls")),
            "invariants": bool(self.invariants or section_text.get("invariants")),
            "connections": bool(self.connections or section_text.get("connections")),
            "analogy_boundary": bool(self.analogy_boundary.strip() or section_text.get("analogy_boundary")),
            "transfer_note": bool(self.transfer_note.strip() or section_text.get("transfer_note")),
            "read_guide": bool(self.read_guide or section_text.get("read_guide")),
        }


@dataclass(frozen=True)
class VisualEntity:
    """A mathematical object visible in one or more storyboard stages."""

    id: str
    kind: str
    dimension: int
    value: JsonValue
    role: str
    label: str
    claim_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _constructor_string(self.id, "id"))
        object.__setattr__(self, "kind", _constructor_vocabulary_choice(self.kind, "kind", ENTITY_KINDS))
        dimension = _constructor_integer(self.dimension, "dimension")
        if dimension not in VECTOR_DIMENSIONS:
            raise ValueError("dimension: expected 2 or 3")
        object.__setattr__(self, "dimension", dimension)
        object.__setattr__(self, "value", _freeze_semantic_value(self.value, "$.value"))
        object.__setattr__(self, "role", _constructor_string(self.role, "role"))
        object.__setattr__(self, "label", _constructor_string(self.label, "label"))
        object.__setattr__(self, "claim_refs", _constructor_string_tuple(self.claim_refs, "claim_refs"))


@dataclass(frozen=True)
class VisualRelation:
    """A non-executable mathematical relationship between two entities."""

    id: str
    kind: str
    source_ref: str
    target_ref: str
    parameters: Mapping[str, JsonValue]
    claim_refs: tuple[str, ...]
    style: str = "solid"

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _constructor_string(self.id, "id"))
        object.__setattr__(self, "kind", _constructor_vocabulary_choice(self.kind, "kind", RELATION_KINDS))
        object.__setattr__(self, "source_ref", _constructor_string(self.source_ref, "source_ref"))
        object.__setattr__(self, "target_ref", _constructor_string(self.target_ref, "target_ref"))
        parameters = _freeze_semantic_parameters(self.parameters, "$.parameters")
        object.__setattr__(self, "parameters", parameters)
        object.__setattr__(self, "claim_refs", _constructor_string_tuple(self.claim_refs, "claim_refs"))
        object.__setattr__(self, "style", _constructor_vocabulary_choice(self.style, "style", RELATION_STYLES))


@dataclass(frozen=True)
class VisualStage:
    """A static storyboard snapshot for a bounded mathematical comparison."""

    id: str
    title: str
    caption: str
    layout: StageLayout
    input_entity_refs: tuple[str, ...]
    output_entity_refs: tuple[str, ...]
    relation_refs: tuple[str, ...]
    expected_invariants: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _constructor_string(self.id, "id"))
        object.__setattr__(self, "title", _constructor_string(self.title, "title"))
        object.__setattr__(self, "caption", _constructor_string(self.caption, "caption"))
        object.__setattr__(self, "layout", _constructor_vocabulary_choice(self.layout, "layout", LAYOUTS))
        for field in ("input_entity_refs", "output_entity_refs", "relation_refs", "expected_invariants"):
            object.__setattr__(self, field, _constructor_string_tuple(getattr(self, field), field))


@dataclass(frozen=True)
class VisualSemantics:
    """Typed semantic graph that a later compiler can validate and render."""

    scene_kind: SceneKind
    entities: tuple[VisualEntity, ...]
    relations: tuple[VisualRelation, ...]
    stages: tuple[VisualStage, ...]
    scene_family: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "scene_kind", _constructor_choice(self.scene_kind, "scene_kind", ("2d", "3d")))
        object.__setattr__(self, "entities", _constructor_instance_tuple(self.entities, "entities", VisualEntity))
        object.__setattr__(self, "relations", _constructor_instance_tuple(self.relations, "relations", VisualRelation))
        object.__setattr__(self, "stages", _constructor_instance_tuple(self.stages, "stages", VisualStage))
        object.__setattr__(self, "scene_family", _constructor_string(self.scene_family, "scene_family"))

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "VisualSemantics":
        return _decode_visual_semantics(payload, "$.visual_semantics")

    def to_dict(self) -> dict[str, object]:
        return _encode_visual_semantics(self)


@dataclass(frozen=True)
class GenerationReceipt:
    """Reproducibility and audit metadata for a normalized artifact."""

    provider: str
    model: str
    prompt_version: str
    generated_at: str
    source_hash: str
    raw_reply_digest: str
    artifact_digest: str
    schema_version: int | None = None

    def __post_init__(self) -> None:
        for field in (
            "provider",
            "model",
            "prompt_version",
            "generated_at",
            "source_hash",
            "raw_reply_digest",
            "artifact_digest",
        ):
            object.__setattr__(self, field, _constructor_string(getattr(self, field), field))
        if self.schema_version is not None:
            object.__setattr__(self, "schema_version", _constructor_integer(self.schema_version, "schema_version"))


@dataclass(frozen=True)
class TeachingArtifact:
    """The versioned unit linking a topic's source, claims, prose, and graph."""

    schema_version: int
    topic_id: str
    revision: int
    status: ArtifactStatus
    source: SourceRecord
    teaching_profile: TeachingProfileRecord
    claims: tuple[Claim, ...]
    connections: tuple[TopicConnection, ...]
    explanation: ExplanationContentV2
    visual_semantics: VisualSemantics
    generated: GenerationReceipt

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", _constructor_integer(self.schema_version, "schema_version"))
        object.__setattr__(self, "topic_id", _constructor_string(self.topic_id, "topic_id"))
        object.__setattr__(self, "revision", _constructor_integer(self.revision, "revision"))
        object.__setattr__(self, "status", _constructor_choice(self.status, "status", ("draft", "reviewed", "published")))
        object.__setattr__(self, "source", _constructor_instance(self.source, "source", SourceRecord))
        object.__setattr__(self, "teaching_profile", _constructor_instance(self.teaching_profile, "teaching_profile", TeachingProfileRecord))
        object.__setattr__(self, "claims", _constructor_instance_tuple(self.claims, "claims", Claim))
        object.__setattr__(self, "connections", _constructor_instance_tuple(self.connections, "connections", TopicConnection))
        object.__setattr__(self, "explanation", _constructor_instance(self.explanation, "explanation", ExplanationContentV2))
        object.__setattr__(self, "visual_semantics", _constructor_instance(self.visual_semantics, "visual_semantics", VisualSemantics))
        object.__setattr__(self, "generated", _constructor_instance(self.generated, "generated", GenerationReceipt))

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "TeachingArtifact":
        return _decode_artifact(payload)

    def to_dict(self) -> dict[str, object]:
        return _encode_artifact(self)


def _decode_artifact(payload: Mapping[str, object]) -> TeachingArtifact:
    record = _object(_mapping(payload, "$"), "$", _ARTIFACT_FIELDS)
    status = _string(record["status"], "$.status")
    if status not in {"draft", "reviewed", "published"}:
        raise ValueError("$.status: expected draft, reviewed, or published")
    return TeachingArtifact(
        schema_version=_integer(record["schema_version"], "$.schema_version"),
        topic_id=_string(record["topic_id"], "$.topic_id"),
        revision=_integer(record["revision"], "$.revision"),
        status=status,
        source=_decode_source_record(_mapping(record["source"], "$.source"), "$.source"),
        teaching_profile=_decode_teaching_profile(
            _mapping(record["teaching_profile"], "$.teaching_profile"), "$.teaching_profile"
        ),
        claims=tuple(
            _decode_claim(_mapping(item, f"$.claims[{index}]"), f"$.claims[{index}]")
            for index, item in enumerate(_array(record["claims"], "$.claims"))
        ),
        connections=tuple(
            _decode_topic_connection(_mapping(item, f"$.connections[{index}]"), f"$.connections[{index}]")
            for index, item in enumerate(_array(record["connections"], "$.connections"))
        ),
        explanation=_decode_explanation(
            _mapping(record["explanation"], "$.explanation"), "$.explanation"
        ),
        visual_semantics=_decode_visual_semantics(
            _mapping(record["visual_semantics"], "$.visual_semantics"), "$.visual_semantics"
        ),
        generated=_decode_generation_receipt(
            _mapping(record["generated"], "$.generated"), "$.generated"
        ),
    )


def _decode_source_record(payload: Mapping[str, object], path: str) -> SourceRecord:
    record = _object(payload, path, _SOURCE_FIELDS)
    spans = tuple(
        _decode_source_span(_mapping(item, f"{path}.spans[{index}]"), f"{path}.spans[{index}]")
        for index, item in enumerate(_array(record["spans"], f"{path}.spans"))
    )
    return SourceRecord(
        source_path=_string_tuple(record["source_path"], f"{path}.source_path"),
        heading_path=_string_tuple(record["heading_path"], f"{path}.heading_path"),
        heading_level=_integer(record["heading_level"], f"{path}.heading_level"),
        occurrence=_integer(record["occurrence"], f"{path}.occurrence"),
        excerpt=_string(record["excerpt"], f"{path}.excerpt"),
        source_hash=_string(record["source_hash"], f"{path}.source_hash"),
        spans=spans,
        neighboring_titles=_string_tuple(record["neighboring_titles"], f"{path}.neighboring_titles"),
    )


def _decode_source_span(payload: Mapping[str, object], path: str) -> SourceSpan:
    record = _object(payload, path, _SOURCE_SPAN_FIELDS)
    return SourceSpan(
        id=_string(record["id"], f"{path}.id"),
        heading_path=_string_tuple(record["heading_path"], f"{path}.heading_path"),
        start_line=_integer(record["start_line"], f"{path}.start_line"),
        end_line=_integer(record["end_line"], f"{path}.end_line"),
        fingerprint=_string(record["fingerprint"], f"{path}.fingerprint"),
        text=_string(record["text"], f"{path}.text"),
    )


def _decode_teaching_profile(payload: Mapping[str, object], path: str) -> TeachingProfileRecord:
    record = _object(payload, path, _PROFILE_FIELDS)
    return TeachingProfileRecord(
        minimum_level=_integer(record["minimum_level"], f"{path}.minimum_level"),
        required_sections=_string_tuple(record["required_sections"], f"{path}.required_sections"),
        requires_analogy_boundary=_boolean(
            record["requires_analogy_boundary"], f"{path}.requires_analogy_boundary"
        ),
    )


def _decode_claim(payload: Mapping[str, object], path: str) -> Claim:
    record = _object(payload, path, _CLAIM_FIELDS)
    formula = record["formula"]
    if formula is not None:
        formula = _string(formula, f"{path}.formula")
    return Claim(
        id=_string(record["id"], f"{path}.id"),
        statement=_string(record["statement"], f"{path}.statement"),
        formula=formula,
        formula_symbols=_string_tuple(record["formula_symbols"], f"{path}.formula_symbols"),
        source_refs=_string_tuple(record["source_refs"], f"{path}.source_refs"),
        explanation_refs=_string_tuple(record["explanation_refs"], f"{path}.explanation_refs"),
        entity_refs=_string_tuple(record["entity_refs"], f"{path}.entity_refs"),
        relation_refs=_string_tuple(record["relation_refs"], f"{path}.relation_refs"),
        stage_refs=_string_tuple(record["stage_refs"], f"{path}.stage_refs"),
    )


def _decode_topic_connection(payload: Mapping[str, object], path: str) -> TopicConnection:
    record = _object(payload, path, _TOPIC_CONNECTION_FIELDS)
    return TopicConnection(
        id=_string(record["id"], f"{path}.id"),
        target_topic_id=_string(record["target_topic_id"], f"{path}.target_topic_id"),
        relation=_string(record["relation"], f"{path}.relation"),
        description=_string(record["description"], f"{path}.description"),
        claim_refs=_optional_string_tuple(record, "claim_refs", path),
    )


def _decode_explanation(payload: Mapping[str, object], path: str) -> ExplanationContentV2:
    record = _object_optional(payload, path, _EXPLANATION_REQUIRED_FIELDS, _EXPLANATION_FIELDS)
    sections = tuple(
        _decode_explanation_section(
            _mapping(item, f"{path}.sections[{index}]"), f"{path}.sections[{index}]"
        )
        for index, item in enumerate(_array(record["sections"], f"{path}.sections"))
    )
    return ExplanationContentV2(
        title=_string(record["title"], f"{path}.title"),
        summary=_string(record["summary"], f"{path}.summary"),
        sections=sections,
        symbol_roles=_string_mapping(record["symbol_roles"], f"{path}.symbol_roles"),
        definition=_optional_string(record, "definition", path),
        formula=_optional_string(record, "formula", path),
        derivation=_optional_string_tuple(record, "derivation", path),
        worked_examples=_optional_worked_examples(record, path),
        intuition=_optional_string(record, "intuition", path),
        geometric_meaning=_optional_string(record, "geometric_meaning", path),
        conclusion=_optional_string(record, "conclusion", path),
        pitfalls=_optional_string_tuple(record, "pitfalls", path),
        invariants=_optional_string_tuple(record, "invariants", path),
        connections=_optional_string_tuple(record, "connections", path),
        analogy_boundary=_optional_string(record, "analogy_boundary", path),
        transfer_note=_optional_string(record, "transfer_note", path),
        read_guide=_optional_string_tuple(record, "read_guide", path),
        searchable_text=_optional_string_tuple(record, "searchable_text", path),
        case_layout=_optional_case_layout(record, path),
    )


def _decode_explanation_section(payload: Mapping[str, object], path: str) -> ExplanationSection:
    record = _object(payload, path, _EXPLANATION_SECTION_FIELDS)
    return ExplanationSection(
        id=_string(record["id"], f"{path}.id"),
        title=_string(record["title"], f"{path}.title"),
        text=_string(record["text"], f"{path}.text"),
        claim_refs=_optional_string_tuple(record, "claim_refs", path),
    )


def _decode_worked_example(payload: Mapping[str, object], path: str) -> WorkedExample:
    record = _object_optional(payload, path, _WORKED_EXAMPLE_REQUIRED_FIELDS, _WORKED_EXAMPLE_FIELDS)
    checks = tuple(
        _decode_worked_example_check(
            _mapping(item, f"{path}.checks[{index}]"), f"{path}.checks[{index}]"
        )
        for index, item in enumerate(_array(record["checks"], f"{path}.checks"))
    )
    return WorkedExample(
        kind=_string(record["kind"], f"{path}.kind"),
        given=_freeze_json(record["given"], f"{path}.given"),
        calculation=_string_tuple(record["calculation"], f"{path}.calculation"),
        result=_freeze_json(record["result"], f"{path}.result"),
        checks=checks,
        id=_optional_string(record, "id", path),
        title=_optional_string(record, "title", path),
        claim_refs=_optional_string_tuple(record, "claim_refs", path),
    )


def _decode_worked_example_check(payload: Mapping[str, object], path: str) -> WorkedExampleCheck:
    record = _object(payload, path, _WORKED_EXAMPLE_CHECK_FIELDS)
    return WorkedExampleCheck(
        name=_string(record["name"], f"{path}.name"),
        expected=_freeze_json(record["expected"], f"{path}.expected"),
        tolerance=_finite_float(record["tolerance"], f"{path}.tolerance"),
    )


def _decode_teaching_case(payload: Mapping[str, object], path: str) -> TeachingCase:
    record = _object_optional(payload, path, _CASE_REQUIRED_FIELDS, _CASE_FIELDS)
    return TeachingCase(
        id=_string(record["id"], f"{path}.id"),
        topic_id=_string(record["topic_id"], f"{path}.topic_id"),
        example_ref=_string(record["example_ref"], f"{path}.example_ref"),
        claim_refs=_optional_string_tuple(record, "claim_refs", path),
        stage_refs=_string_tuple(record["stage_refs"], f"{path}.stage_refs"),
        purpose=_string(record["purpose"], f"{path}.purpose"),
    )


def _optional_case_layout(record: Mapping[str, object], path: str) -> CaseLayoutSpec | None:
    value = record.get("case_layout")
    if value is None:
        return None
    layout = _object(value, f"{path}.case_layout", _CASE_LAYOUT_FIELDS)
    cases = tuple(
        _decode_teaching_case(_mapping(item, f"{path}.case_layout.cases[{index}]"), f"{path}.case_layout.cases[{index}]")
        for index, item in enumerate(_array(layout["cases"], f"{path}.case_layout.cases"))
    )
    return CaseLayoutSpec(
        default_pane_count=_integer(layout["default_pane_count"], f"{path}.case_layout.default_pane_count"),
        cases=cases,
    )


def _decode_visual_semantics(payload: Mapping[str, object], path: str) -> VisualSemantics:
    record = _mapping(payload, path)
    missing = [field for field in _VISUAL_SEMANTICS_REQUIRED_FIELDS if field not in record]
    if missing:
        raise ValueError(f"{path}.{missing[0]}: required field is missing")
    unknown = [key for key in record if key not in _VISUAL_SEMANTICS_FIELDS]
    if unknown:
        raise ValueError(f"{path}.{unknown[0]}: unknown field")
    scene_kind = _string(record["scene_kind"], f"{path}.scene_kind")
    if scene_kind not in {"2d", "3d"}:
        raise ValueError(f"{path}.scene_kind: expected 2d or 3d")
    return VisualSemantics(
        scene_kind=scene_kind,
        entities=tuple(
            _decode_visual_entity(
                _mapping(item, f"{path}.entities[{index}]"), f"{path}.entities[{index}]"
            )
            for index, item in enumerate(_array(record["entities"], f"{path}.entities"))
        ),
        relations=tuple(
            _decode_visual_relation(
                _mapping(item, f"{path}.relations[{index}]"), f"{path}.relations[{index}]"
            )
            for index, item in enumerate(_array(record["relations"], f"{path}.relations"))
        ),
        stages=tuple(
            _decode_visual_stage(_mapping(item, f"{path}.stages[{index}]"), f"{path}.stages[{index}]")
            for index, item in enumerate(_array(record["stages"], f"{path}.stages"))
        ),
        scene_family=_optional_string(record, "scene_family", path) or "",
    )


def _decode_visual_entity(payload: Mapping[str, object], path: str) -> VisualEntity:
    record = _object(payload, path, _ENTITY_FIELDS)
    kind = _vocabulary_choice(record["kind"], f"{path}.kind", ENTITY_KINDS)
    dimension = _integer(record["dimension"], f"{path}.dimension")
    if dimension not in VECTOR_DIMENSIONS:
        raise ValueError(f"{path}.dimension: expected 2 or 3")
    return VisualEntity(
        id=_string(record["id"], f"{path}.id"),
        kind=kind,
        dimension=dimension,
        value=_freeze_semantic_value(record["value"], f"{path}.value"),
        role=_string(record["role"], f"{path}.role"),
        label=_string(record["label"], f"{path}.label"),
        claim_refs=_string_tuple(record["claim_refs"], f"{path}.claim_refs"),
    )


def _decode_visual_relation(payload: Mapping[str, object], path: str) -> VisualRelation:
    record = _object_optional(payload, path, _RELATION_FIELDS, (*_RELATION_FIELDS, "style"))
    return VisualRelation(
        id=_string(record["id"], f"{path}.id"),
        kind=_vocabulary_choice(record["kind"], f"{path}.kind", RELATION_KINDS),
        source_ref=_string(record["source_ref"], f"{path}.source_ref"),
        target_ref=_string(record["target_ref"], f"{path}.target_ref"),
        parameters=_freeze_semantic_parameters(record["parameters"], f"{path}.parameters"),
        claim_refs=_string_tuple(record["claim_refs"], f"{path}.claim_refs"),
        style=_vocabulary_choice(record.get("style", "solid"), f"{path}.style", RELATION_STYLES),
    )


def _decode_visual_stage(payload: Mapping[str, object], path: str) -> VisualStage:
    record = _object(payload, path, _STAGE_FIELDS)
    layout = _vocabulary_choice(record["layout"], f"{path}.layout", LAYOUTS)
    return VisualStage(
        id=_string(record["id"], f"{path}.id"),
        title=_string(record["title"], f"{path}.title"),
        caption=_string(record["caption"], f"{path}.caption"),
        layout=layout,
        input_entity_refs=_string_tuple(record["input_entity_refs"], f"{path}.input_entity_refs"),
        output_entity_refs=_string_tuple(record["output_entity_refs"], f"{path}.output_entity_refs"),
        relation_refs=_string_tuple(record["relation_refs"], f"{path}.relation_refs"),
        expected_invariants=_string_tuple(record["expected_invariants"], f"{path}.expected_invariants"),
    )


def _decode_generation_receipt(payload: Mapping[str, object], path: str) -> GenerationReceipt:
    record = _object_optional(payload, path, _GENERATION_REQUIRED_FIELDS, _GENERATION_FIELDS)
    return GenerationReceipt(
        provider=_string(record["provider"], f"{path}.provider"),
        model=_string(record["model"], f"{path}.model"),
        prompt_version=_string(record["prompt_version"], f"{path}.prompt_version"),
        generated_at=_string(record["generated_at"], f"{path}.generated_at"),
        source_hash=_string(record["source_hash"], f"{path}.source_hash"),
        raw_reply_digest=_string(record["raw_reply_digest"], f"{path}.raw_reply_digest"),
        artifact_digest=_string(record["artifact_digest"], f"{path}.artifact_digest"),
        schema_version=(
            _integer(record["schema_version"], f"{path}.schema_version")
            if "schema_version" in record
            else None
        ),
    )


def _encode_artifact(artifact: TeachingArtifact) -> dict[str, object]:
    return {
        "schema_version": artifact.schema_version,
        "topic_id": artifact.topic_id,
        "revision": artifact.revision,
        "status": artifact.status,
        "source": _encode_source_record(artifact.source),
        "teaching_profile": _encode_teaching_profile(artifact.teaching_profile),
        "claims": [_encode_claim(claim) for claim in artifact.claims],
        "connections": [_encode_topic_connection(connection) for connection in artifact.connections],
        "explanation": _encode_explanation(artifact.explanation),
        "visual_semantics": _encode_visual_semantics(artifact.visual_semantics),
        "generated": _encode_generation_receipt(artifact.generated),
    }


def _encode_source_record(source: SourceRecord) -> dict[str, object]:
    return {
        "source_path": list(source.source_path),
        "heading_path": list(source.heading_path),
        "heading_level": source.heading_level,
        "occurrence": source.occurrence,
        "excerpt": source.excerpt,
        "source_hash": source.source_hash,
        "spans": [
            {
                "id": span.id,
                "heading_path": list(span.heading_path),
                "start_line": span.start_line,
                "end_line": span.end_line,
                "fingerprint": span.fingerprint,
                "text": span.text,
            }
            for span in source.spans
        ],
        "neighboring_titles": list(source.neighboring_titles),
    }


def _encode_teaching_profile(profile: TeachingProfileRecord) -> dict[str, object]:
    return {
        "minimum_level": profile.minimum_level,
        "required_sections": list(profile.required_sections),
        "requires_analogy_boundary": profile.requires_analogy_boundary,
    }


def _encode_claim(claim: Claim) -> dict[str, object]:
    return {
        "id": claim.id,
        "statement": claim.statement,
        "formula": claim.formula,
        "formula_symbols": list(claim.formula_symbols),
        "source_refs": list(claim.source_refs),
        "explanation_refs": list(claim.explanation_refs),
        "entity_refs": list(claim.entity_refs),
        "relation_refs": list(claim.relation_refs),
        "stage_refs": list(claim.stage_refs),
    }


def _encode_topic_connection(connection: TopicConnection) -> dict[str, object]:
    return {
        "id": connection.id,
        "target_topic_id": connection.target_topic_id,
        "relation": connection.relation,
        "description": connection.description,
        "claim_refs": list(connection.claim_refs),
    }


def _encode_explanation(explanation: ExplanationContentV2) -> dict[str, object]:
    encoded: dict[str, object] = {
        "title": explanation.title,
        "summary": explanation.summary,
        "sections": [
            {
                "id": section.id,
                "title": section.title,
                "text": section.text,
                "claim_refs": list(section.claim_refs),
            }
            for section in explanation.sections
        ],
        "symbol_roles": dict(explanation.symbol_roles),
    }
    optional_values: dict[str, object] = {
        "definition": explanation.definition,
        "formula": explanation.formula,
        "derivation": list(explanation.derivation),
        "worked_examples": [_encode_worked_example(item) for item in explanation.worked_examples],
        "intuition": explanation.intuition,
        "geometric_meaning": explanation.geometric_meaning,
        "conclusion": explanation.conclusion,
        "pitfalls": list(explanation.pitfalls),
        "invariants": list(explanation.invariants),
        "connections": list(explanation.connections),
        "analogy_boundary": explanation.analogy_boundary,
        "transfer_note": explanation.transfer_note,
        "read_guide": list(explanation.read_guide),
        "searchable_text": list(explanation.searchable_text),
        "case_layout": _encode_case_layout(explanation.case_layout) if explanation.case_layout is not None else None,
    }
    encoded.update({key: value for key, value in optional_values.items() if value not in (None, "", [], ())})
    return encoded


def _encode_case_layout(layout: CaseLayoutSpec) -> dict[str, object]:
    return {
        "default_pane_count": layout.default_pane_count,
        "cases": [
            {
                "id": case.id,
                "topic_id": case.topic_id,
                "example_ref": case.example_ref,
                "claim_refs": list(case.claim_refs),
                "stage_refs": list(case.stage_refs),
                "purpose": case.purpose,
            }
            for case in layout.cases
        ],
    }


def _encode_worked_example(example: WorkedExample) -> dict[str, object]:
    encoded: dict[str, object] = {
        "kind": example.kind,
        "given": _thaw_json(example.given),
        "calculation": list(example.calculation),
        "result": _thaw_json(example.result),
        "checks": [_encode_worked_example_check(item) for item in example.checks],
    }
    if example.id:
        encoded["id"] = example.id
    if example.title:
        encoded["title"] = example.title
    if example.claim_refs:
        encoded["claim_refs"] = list(example.claim_refs)
    return encoded


def _encode_worked_example_check(check: WorkedExampleCheck) -> dict[str, object]:
    return {
        "name": check.name,
        "expected": _thaw_json(check.expected),
        "tolerance": check.tolerance,
    }


def _encode_visual_relation(relation: VisualRelation) -> dict[str, object]:
    encoded: dict[str, object] = {
        "id": relation.id,
        "kind": relation.kind,
        "source_ref": relation.source_ref,
        "target_ref": relation.target_ref,
        "parameters": _thaw_json(relation.parameters),
        "claim_refs": list(relation.claim_refs),
    }
    # 默认实线不写字段，保持既有产物字节稳定。
    if relation.style != "solid":
        encoded["style"] = relation.style
    return encoded


def _encode_visual_semantics(semantics: VisualSemantics) -> dict[str, object]:
    encoded = {
        "scene_kind": semantics.scene_kind,
        "entities": [
            {
                "id": entity.id,
                "kind": entity.kind,
                "dimension": entity.dimension,
                "value": _thaw_json(entity.value),
                "role": entity.role,
                "label": entity.label,
                "claim_refs": list(entity.claim_refs),
            }
            for entity in semantics.entities
        ],
        "relations": [_encode_visual_relation(relation) for relation in semantics.relations],
        "stages": [
            {
                "id": stage.id,
                "title": stage.title,
                "caption": stage.caption,
                "layout": stage.layout,
                "input_entity_refs": list(stage.input_entity_refs),
                "output_entity_refs": list(stage.output_entity_refs),
                "relation_refs": list(stage.relation_refs),
                "expected_invariants": list(stage.expected_invariants),
            }
            for stage in semantics.stages
        ],
    }
    if semantics.scene_family:
        encoded["scene_family"] = semantics.scene_family
    return encoded


def _encode_generation_receipt(receipt: GenerationReceipt) -> dict[str, object]:
    encoded = {
        "provider": receipt.provider,
        "model": receipt.model,
        "prompt_version": receipt.prompt_version,
        "generated_at": receipt.generated_at,
        "source_hash": receipt.source_hash,
        "raw_reply_digest": receipt.raw_reply_digest,
        "artifact_digest": receipt.artifact_digest,
    }
    if receipt.schema_version is not None:
        encoded["schema_version"] = receipt.schema_version
    return encoded


def _object(payload: Mapping[str, object], path: str, fields: tuple[str, ...]) -> Mapping[str, object]:
    payload = _mapping(payload, path)
    missing = [field for field in fields if field not in payload]
    if missing:
        raise ValueError(f"{path}.{missing[0]}: required field is missing")
    unknown = [key for key in payload if key not in fields]
    if unknown:
        raise ValueError(f"{path}.{unknown[0]}: unknown field")
    return payload


def _object_optional(
    payload: Mapping[str, object],
    path: str,
    required_fields: tuple[str, ...],
    allowed_fields: tuple[str, ...],
) -> Mapping[str, object]:
    payload = _mapping(payload, path)
    missing = [field for field in required_fields if field not in payload]
    if missing:
        raise ValueError(f"{path}.{missing[0]}: required field is missing")
    unknown = [key for key in payload if key not in allowed_fields]
    if unknown:
        raise ValueError(f"{path}.{unknown[0]}: unknown field")
    return payload


def _mapping(value: object, path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path}: expected object")
    if not all(isinstance(key, str) for key in value):
        raise ValueError(f"{path}: expected string object keys")
    return value


def _array(value: object, path: str) -> list[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, list):
        raise ValueError(f"{path}: expected array")
    return value


def _string(value: object, path: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{path}: expected string")
    return value


def _integer(value: object, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{path}: expected integer")
    return value


def _finite_float(value: object, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{path}: expected number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{path}: expected finite number")
    return number


def _boolean(value: object, path: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{path}: expected boolean")
    return value


def _string_tuple(value: object, path: str) -> tuple[str, ...]:
    return tuple(_string(item, f"{path}[{index}]") for index, item in enumerate(_array(value, path)))


def _string_mapping(value: object, path: str) -> Mapping[str, str]:
    mapping = _mapping(value, path)
    return MappingProxyType({key: _string(item, f"{path}.{key}") for key, item in mapping.items()})


def _optional_string(record: Mapping[str, object], field: str, path: str) -> str:
    value = record.get(field, "")
    return _string(value, f"{path}.{field}")


def _optional_string_tuple(record: Mapping[str, object], field: str, path: str) -> tuple[str, ...]:
    value = record.get(field, [])
    return _string_tuple(value, f"{path}.{field}")


def _optional_worked_examples(record: Mapping[str, object], path: str) -> tuple[WorkedExample, ...]:
    value = record.get("worked_examples", [])
    return tuple(
        _decode_worked_example(_mapping(item, f"{path}.worked_examples[{index}]"), f"{path}.worked_examples[{index}]")
        for index, item in enumerate(_array(value, f"{path}.worked_examples"))
    )


def _constructor_tuple(value: object, field: str) -> tuple[object, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise TypeError(f"{field}: expected tuple or list")
    return tuple(value)


def _constructor_instance_tuple(value: object, field: str, expected_type: type[object]) -> tuple[object, ...]:
    return tuple(
        _constructor_instance(item, f"{field}[{index}]", expected_type)
        for index, item in enumerate(_constructor_tuple(value, field))
    )


def _constructor_instance(value: object, field: str, expected_type: type[object]) -> object:
    if not isinstance(value, expected_type):
        raise TypeError(f"{field}: expected {expected_type.__name__}")
    return value


def _constructor_string_tuple(value: object, field: str) -> tuple[str, ...]:
    return tuple(_constructor_string(item, f"{field}[{index}]") for index, item in enumerate(_constructor_tuple(value, field)))


def _constructor_string(item: object, field: str) -> str:
    if not isinstance(item, str):
        raise TypeError(f"{field}: expected string")
    return item


def _constructor_optional_string(value: object, field: str) -> str | None:
    if value is None:
        return None
    return _constructor_string(value, field)


def _constructor_integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field}: expected integer")
    return value


def _constructor_finite_float(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field}: expected number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field}: expected finite number")
    return number


def _constructor_boolean(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{field}: expected boolean")
    return value


def _constructor_choice(value: object, field: str, choices: tuple[str, ...]) -> str:
    value = _constructor_string(value, field)
    if value not in choices:
        raise TypeError(f"{field}: expected one of {', '.join(choices)}")
    return value


def _constructor_vocabulary_choice(value: object, field: str, choices: frozenset[str]) -> str:
    value = _constructor_string(value, field)
    if value not in choices:
        raise TypeError(f"{field}: unsupported value {value!r}")
    return value


def _constructor_string_mapping(value: object, field: str) -> Mapping[str, str]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field}: expected mapping")
    if not all(isinstance(key, str) for key in value):
        raise TypeError(f"{field}: expected string object keys")
    return MappingProxyType({key: _constructor_string(item, f"{field}.{key}") for key, item in value.items()})


def _freeze_json(value: object, path: str) -> JsonValue:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{path}: expected finite JSON number")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item, f"{path}[{index}]") for index, item in enumerate(value))
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ValueError(f"{path}: expected string object keys")
        return MappingProxyType(
            {key: _freeze_json(item, f"{path}.{key}") for key, item in value.items()}
        )
    raise ValueError(f"{path}: expected JSON-safe value")


def _vocabulary_choice(value: object, path: str, choices: frozenset[str]) -> str:
    value = _string(value, path)
    if value not in choices:
        raise ValueError(f"{path}: unsupported value {value!r}")
    return value


def _freeze_semantic_value(value: object, path: str) -> JsonValue:
    issues = validate_semantic_value(value, path)
    if issues:
        raise ValueError(str(issues[0]))
    return _freeze_json(value, path)


def _freeze_semantic_parameters(value: object, path: str) -> Mapping[str, JsonValue]:
    parameters = _mapping(value, path)
    frozen: dict[str, JsonValue] = {}
    for key, parameter in parameters.items():
        frozen[key] = _freeze_semantic_value(parameter, f"{path}.{key}")
    return MappingProxyType(frozen)


def _thaw_json(value: JsonValue) -> object:
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    return value


_ARTIFACT_FIELDS = (
    "schema_version",
    "topic_id",
    "revision",
    "status",
    "source",
    "teaching_profile",
    "claims",
    "connections",
    "explanation",
    "visual_semantics",
    "generated",
)
_SOURCE_FIELDS = (
    "source_path",
    "heading_path",
    "heading_level",
    "occurrence",
    "excerpt",
    "source_hash",
    "spans",
    "neighboring_titles",
)
_SOURCE_SPAN_FIELDS = ("id", "heading_path", "start_line", "end_line", "fingerprint", "text")
_PROFILE_FIELDS = ("minimum_level", "required_sections", "requires_analogy_boundary")
_CLAIM_FIELDS = (
    "id",
    "statement",
    "formula",
    "formula_symbols",
    "source_refs",
    "explanation_refs",
    "entity_refs",
    "relation_refs",
    "stage_refs",
)
_TOPIC_CONNECTION_FIELDS = ("id", "target_topic_id", "relation", "description", "claim_refs")
_EXPLANATION_REQUIRED_FIELDS = ("title", "summary", "sections", "symbol_roles")
_EXPLANATION_FIELDS = (
    *_EXPLANATION_REQUIRED_FIELDS,
    "definition",
    "formula",
    "derivation",
    "worked_examples",
    "intuition",
    "geometric_meaning",
    "conclusion",
    "pitfalls",
    "invariants",
    "connections",
    "analogy_boundary",
    "transfer_note",
    "read_guide",
    "searchable_text",
    "case_layout",
)
_EXPLANATION_SECTION_FIELDS = ("id", "title", "text", "claim_refs")
_WORKED_EXAMPLE_REQUIRED_FIELDS = ("kind", "given", "calculation", "result", "checks")
_WORKED_EXAMPLE_FIELDS = (*_WORKED_EXAMPLE_REQUIRED_FIELDS, "id", "title", "claim_refs")
_WORKED_EXAMPLE_CHECK_FIELDS = ("name", "expected", "tolerance")
_CASE_LAYOUT_FIELDS = ("default_pane_count", "cases")
_CASE_REQUIRED_FIELDS = ("id", "topic_id", "example_ref", "stage_refs", "purpose")
_CASE_FIELDS = (*_CASE_REQUIRED_FIELDS, "claim_refs")
_VISUAL_SEMANTICS_REQUIRED_FIELDS = ("scene_kind", "entities", "relations", "stages")
_VISUAL_SEMANTICS_FIELDS = (*_VISUAL_SEMANTICS_REQUIRED_FIELDS, "scene_family")
_ENTITY_FIELDS = ("id", "kind", "dimension", "value", "role", "label", "claim_refs")
_RELATION_FIELDS = ("id", "kind", "source_ref", "target_ref", "parameters", "claim_refs")
_STAGE_FIELDS = (
    "id",
    "title",
    "caption",
    "layout",
    "input_entity_refs",
    "output_entity_refs",
    "relation_refs",
    "expected_invariants",
)
_GENERATION_REQUIRED_FIELDS = (
    "provider",
    "model",
    "prompt_version",
    "generated_at",
    "source_hash",
    "raw_reply_digest",
    "artifact_digest",
)
_GENERATION_FIELDS = (*_GENERATION_REQUIRED_FIELDS, "schema_version")


__all__ = [
    "ArtifactStatus",
    "Claim",
    "ExplanationContentV2",
    "ExplanationSection",
    "GenerationReceipt",
    "SceneKind",
    "SourceRecord",
    "StageLayout",
    "TeachingArtifact",
    "TeachingProfileRecord",
    "TopicConnection",
    "WorkedExample",
    "WorkedExampleCheck",
    "TeachingCase",
    "CaseLayoutSpec",
    "VisualEntity",
    "VisualRelation",
    "VisualSemantics",
    "VisualStage",
]
