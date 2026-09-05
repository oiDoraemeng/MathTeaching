# Linear Algebra Teaching Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the lecture-grounded, claim-first data contract and safe explanation-agent boundary used by all later teaching artifacts.

**Architecture:** A new `linear_algebra.teaching` package owns source extraction, immutable teaching models, controlled vocabularies, validation, provider adaptation, prompting, parsing, and source-evidence checks. It consumes existing `LessonEntry` identities but does not import Qt, rendering, or `CommandPlan`.

**Tech Stack:** Python 3.11+, frozen dataclasses, `jsonschema`, SHA-256, existing OpenAI-compatible provider boundary, pytest.

**Spec:** `openspec/changes/enrich-linear-algebra-teaching-depth/design.md` and `openspec/changes/enrich-linear-algebra-teaching-depth/specs/`

## Global Constraints

- `.agents/线性代数讲义.md` is the only lecture source and must not be modified.
- The first three chapters remain exactly 54 topics in a 24/15/15 split.
- The explanation agent emits one JSON object containing mathematics and visual semantics; it never emits Python, Qt, HTML, `CommandPlan`, scene operations, or renderer objects.
- All persisted text is UTF-8; all numeric semantic values are finite; formulas remain KaTeX-compatible strings.
- New models are immutable and JSON-safe. No pickle, dynamic import, `eval`, or `exec` is permitted.
- Application code outside the files listed by a task is out of scope for that task.

## File Structure

- Create `linear_algebra/teaching/source.py`: lecture parsing, source spans, normalized hashes.
- Create `linear_algebra/teaching/model.py`: claims, explanation, visual semantics, and artifact models.
- Create `linear_algebra/teaching/profiles.py`: L0-L4 profiles and topic assignments.
- Create `linear_algebra/teaching/vocabulary.py`: controlled entity/relation/layout values and numeric guards.
- Create `linear_algebra/teaching/validation.py`: schema, reference, formula-binding, and source-evidence validation.
- Create `linear_algebra/teaching/agent.py`: explanation-agent protocol and provider adapter.
- Create `linear_algebra/teaching/prompt.py`: inert-source JSON prompt composition.
- Create `linear_algebra/teaching/parser.py`: safe model-response parsing and leakage rejection.
- Create `linear_algebra/teaching/__init__.py`: stable exports only.
- Create focused tests under `tests/test_linear_algebra_teaching_*.py`.

---

<!-- openspec-task: 1.1 -->
### Task 1: Extract Stable Lecture Source Context

**Files:**
- Create: `linear_algebra/teaching/source.py`
- Create: `linear_algebra/teaching/__init__.py`
- Test: `tests/test_linear_algebra_teaching_source.py`

**Interfaces:**
- Consumes: `LessonEntry.source_anchor` from `linear_algebra.catalog.model`.
- Produces: `SourceSpan`, `SourceContext`, `normalize_source_text(text: str) -> str`, and `LectureSourceRepository.context_for(entry: LessonEntry) -> SourceContext`.

- [x] **Step 1: Write failing source extraction tests**

```python
from pathlib import Path

from linear_algebra.catalog.chapter_02 import TOPICS
from linear_algebra.teaching.source import LectureSourceRepository


def test_context_for_matrix_composition_is_stable() -> None:
    entry = next(t for t in TOPICS if t.id == "ch02.matrix.composition")
    repo = LectureSourceRepository(Path(".agents/线性代数讲义.md"))

    context = repo.context_for(entry)

    assert context.topic_id == entry.id
    assert context.heading_path == entry.source_anchor.heading_path
    assert "矩阵" in context.excerpt
    assert context.source_hash.startswith("sha256:")
    assert context.spans


def test_excluded_headings_are_not_part_of_context() -> None:
    entry = next(t for t in TOPICS if t.id == "ch02.matrix.composition")
    context = LectureSourceRepository(Path(".agents/线性代数讲义.md")).context_for(entry)
    assert "自检" not in context.excerpt
    assert "挑战选做" not in context.excerpt
```

- [x] **Step 2: Run the focused test and verify the missing-module failure**

Run: `pytest tests/test_linear_algebra_teaching_source.py -q`

Expected: FAIL because `linear_algebra.teaching.source` does not exist.

- [x] **Step 3: Implement heading-aware extraction and normalized fingerprints**

```python
@dataclass(frozen=True)
class SourceSpan:
    id: str
    heading_path: tuple[str, ...]
    start_line: int
    end_line: int
    fingerprint: str
    text: str


@dataclass(frozen=True)
class SourceContext:
    topic_id: str
    source_path: tuple[str, ...]
    heading_path: tuple[str, ...]
    heading_level: int
    occurrence: int
    excerpt: str
    source_hash: str
    spans: tuple[SourceSpan, ...]
    neighboring_titles: tuple[str, ...]


def normalize_source_text(text: str) -> str:
    lines = (" ".join(line.split()) for line in text.replace("\r\n", "\n").split("\n"))
    return "\n".join(line for line in lines if line)


class LectureSourceRepository:
    def __init__(self, path: Path) -> None:
        self.path = path

    def context_for(self, entry: LessonEntry) -> SourceContext:
        source = self.path.read_text(encoding="utf-8")
        records = _parse_heading_sections(source)
        section = _resolve_anchor(records, entry.source_anchor)
        excerpt, spans = _bounded_topic_excerpt(section, records, excluded=("自检", "练习", "挑战"))
        digest = hashlib.sha256(normalize_source_text(excerpt).encode("utf-8")).hexdigest()
        return SourceContext(
            topic_id=entry.id,
            source_path=entry.source_path,
            heading_path=entry.source_anchor.heading_path,
            heading_level=entry.source_anchor.heading_level,
            occurrence=entry.source_anchor.occurrence,
            excerpt=excerpt,
            source_hash=f"sha256:{digest}",
            spans=spans,
            neighboring_titles=_neighbor_titles(records, section),
        )
```

Keep line ranges diagnostic only; use `heading_path + occurrence + fingerprint` as identity. Reuse the heading semantics from `linear_algebra.validation` without importing private functions from that module.

- [x] **Step 4: Verify all 54 source contexts**

Run: `pytest tests/test_linear_algebra_teaching_source.py tests/test_lecture_source_validation.py -q`

Expected: PASS; contexts resolve in catalog order and contain no excluded heading blocks.

- [x] **Step 5: Commit the source contract**

```bash
git add linear_algebra/teaching/source.py linear_algebra/teaching/__init__.py tests/test_linear_algebra_teaching_source.py
git commit -m "feat: add lecture source contexts"
```

<!-- openspec-task: 1.2 -->
### Task 2: Define Claim-First Teaching Models

**Files:**
- Create: `linear_algebra/teaching/model.py`
- Modify: `linear_algebra/teaching/__init__.py`
- Test: `tests/test_linear_algebra_teaching_model.py`

**Interfaces:**
- Consumes: `SourceContext` from Task 1.
- Produces: immutable JSON-safe types `Claim`, `ExplanationContentV2`, `VisualEntity`, `VisualRelation`, `VisualStage`, `VisualSemantics`, `GenerationReceipt`, and `TeachingArtifact`.

- [x] **Step 1: Write a failing nested round-trip test**

```python
from linear_algebra.teaching.model import TeachingArtifact
from tests.teaching_fixtures import composition_artifact_payload


def test_teaching_artifact_round_trip_keeps_claim_links() -> None:
    payload = composition_artifact_payload()
    artifact = TeachingArtifact.from_dict(payload)

    assert artifact.claims[0].id == "claim.composition-order"
    assert artifact.claims[0].entity_refs == ("x", "Bx", "ABx")
    assert artifact.to_dict() == payload
```

Create `tests/teaching_fixtures.py` with a complete, small `ch02.matrix.composition` payload rather than mocking individual fields.

- [x] **Step 2: Run the model test and verify it fails**

Run: `pytest tests/test_linear_algebra_teaching_model.py -q`

Expected: FAIL because `TeachingArtifact` and the fixture do not exist.

- [x] **Step 3: Implement immutable models with explicit serializers**

```python
ArtifactStatus = Literal["draft", "reviewed", "published"]
SceneKind = Literal["2d", "3d"]


@dataclass(frozen=True)
class Claim:
    id: str
    statement: str
    formula: str | None
    source_refs: tuple[str, ...]
    explanation_refs: tuple[str, ...]
    entity_refs: tuple[str, ...]
    relation_refs: tuple[str, ...]
    stage_refs: tuple[str, ...]


@dataclass(frozen=True)
class TeachingArtifact:
    schema_version: int
    topic_id: str
    revision: int
    status: ArtifactStatus
    source: SourceRecord
    teaching_profile: TeachingProfileRecord
    claims: tuple[Claim, ...]
    explanation: ExplanationContentV2
    visual_semantics: VisualSemantics
    generated: GenerationReceipt

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "TeachingArtifact":
        return _decode_artifact(payload)

    def to_dict(self) -> dict[str, object]:
        return _encode_artifact(self)
```

Use tuples internally, lists in JSON, ordered mappings for symbol roles, and reject implicit coercion such as a string where a list is required.

- [x] **Step 4: Run round-trip and existing explanation tests**

Run: `pytest tests/test_linear_algebra_teaching_model.py tests/test_linear_algebra_explanations.py -q`

Expected: PASS; existing `ExplanationContent` remains unchanged in this task.

- [x] **Step 5: Commit the teaching models**

```bash
git add linear_algebra/teaching/model.py linear_algebra/teaching/__init__.py tests/teaching_fixtures.py tests/test_linear_algebra_teaching_model.py
git commit -m "feat: define claim-first teaching models"
```

<!-- openspec-task: 1.3 -->
### Task 3: Assign L0-L4 Teaching Profiles

**Files:**
- Create: `linear_algebra/teaching/profiles.py`
- Modify: `linear_algebra/teaching/model.py`
- Test: `tests/test_linear_algebra_teaching_profiles.py`

**Interfaces:**
- Consumes: the 54 topic IDs from `linear_algebra.catalog.manifest.topic_entries()`.
- Produces: `TeachingLevel`, `TeachingProfile`, `profile_for(topic_id: str) -> TeachingProfile`, and `validate_profile_coverage() -> tuple[str, ...]`.

- [x] **Step 1: Write failing profile coverage tests**

```python
from linear_algebra.catalog.manifest import topic_entries
from linear_algebra.teaching.profiles import TeachingLevel, profile_for, validate_profile_coverage


def test_every_topic_has_a_teaching_profile() -> None:
    assert validate_profile_coverage() == ()
    assert {topic.id for topic in topic_entries()} == {
        topic.id for topic in topic_entries() if profile_for(topic.id)
    }


def test_bridge_and_analogy_profiles_are_explicit() -> None:
    assert profile_for("ch02.matrix.composition").minimum_level >= TeachingLevel.EXPLAIN
    analogy = profile_for("ch02.high-dimensional.analogy")
    assert analogy.minimum_level == TeachingLevel.EXPLAIN
    assert analogy.requires_analogy_boundary is True
```

- [x] **Step 2: Run the test and verify missing profile behavior**

Run: `pytest tests/test_linear_algebra_teaching_profiles.py -q`

Expected: FAIL because `profiles.py` is missing.

- [x] **Step 3: Implement explicit profiles, not title heuristics**

```python
class TeachingLevel(IntEnum):
    SEE = 0
    READ = 1
    CALCULATE = 2
    EXPLAIN = 3
    TRANSFER = 4


@dataclass(frozen=True)
class TeachingProfile:
    minimum_level: TeachingLevel
    required_sections: tuple[str, ...]
    requires_analogy_boundary: bool = False


_CORE = TeachingProfile(
    TeachingLevel.EXPLAIN,
    ("definition", "formula", "derivation", "worked_examples", "geometric_meaning", "pitfalls"),
)
_BRIDGE = TeachingProfile(
    TeachingLevel.TRANSFER,
    (*_CORE.required_sections, "connections"),
)
_ANALOGY = TeachingProfile(
    TeachingLevel.EXPLAIN,
    ("definition", "intuition", "geometric_meaning", "connections"),
    requires_analogy_boundary=True,
)
```

Define `_PROFILES` with every concrete topic ID. Use `_CORE`, `_BRIDGE`, and `_ANALOGY` values to reduce duplication, but do not infer a profile from the topic title at runtime.

- [x] **Step 4: Verify the catalog/profile join**

Run: `pytest tests/test_linear_algebra_teaching_profiles.py tests/test_linear_algebra_catalog.py -q`

Expected: PASS with exactly 54 assigned profiles and no unknown IDs.

- [x] **Step 5: Commit profile assignments**

```bash
git add linear_algebra/teaching/profiles.py linear_algebra/teaching/model.py tests/test_linear_algebra_teaching_profiles.py
git commit -m "feat: define teaching depth profiles"
```

<!-- openspec-task: 1.4 -->
### Task 4: Enforce the Controlled Visual Vocabulary

**Files:**
- Create: `linear_algebra/teaching/vocabulary.py`
- Modify: `linear_algebra/teaching/model.py`
- Test: `tests/test_linear_algebra_visual_vocabulary.py`

**Interfaces:**
- Consumes: raw JSON fields used by `VisualEntity`, `VisualRelation`, and `VisualStage`.
- Produces: vocabulary constants and `validate_semantic_value(value: object, path: str) -> tuple[SemanticIssue, ...]`.

- [x] **Step 1: Write rejection tests for unsafe or unbounded values**

```python
import math

import pytest

from linear_algebra.teaching.model import VisualSemantics


@pytest.mark.parametrize("value", [math.nan, math.inf, "__import__('os')", {"op": "linear.upsert"}])
def test_semantics_reject_unsafe_values(value: object) -> None:
    payload = composition_artifact_payload()["visual_semantics"]
    payload["entities"][0]["value"] = value
    with pytest.raises(ValueError):
        VisualSemantics.from_dict(payload)


def test_semantics_reject_literal_color() -> None:
    payload = composition_artifact_payload()["visual_semantics"]
    payload["entities"][0]["color"] = "#ff0000"
    with pytest.raises(ValueError, match="color"):
        VisualSemantics.from_dict(payload)
```

- [x] **Step 2: Run the vocabulary tests and verify they fail**

Run: `pytest tests/test_linear_algebra_visual_vocabulary.py -q`

Expected: FAIL because visual models currently accept unvalidated values.

- [x] **Step 3: Add finite typed values and exact enums**

```python
ENTITY_KINDS = frozenset({"point", "vector", "basis", "matrix", "grid", "region", "area", "volume"})
RELATION_KINDS = frozenset({
    "sum", "difference", "scalar_multiple", "maps_to", "spans",
    "projects_to", "orthogonal_to", "collapses_to", "composition_order",
    "compare", "orientation", "decomposes_into", "has_foot",
    "has_residual", "batch_maps_to", "endpoint_diff", "same_measure",
    "invariant",
})
LAYOUTS = frozenset({"overlay", "side_by_side", "sequence"})


def require_finite_number(value: object, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{path}: expected number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{path}: expected finite number")
    return number
```

Permit only scalar values, 2D/3D vectors, and rectangular matrices with bounded dimensions. Reject unknown keys during model decoding.

- [x] **Step 4: Verify valid composition semantics and unsafe rejections**

Run: `pytest tests/test_linear_algebra_visual_vocabulary.py tests/test_linear_algebra_teaching_model.py -q`

Expected: PASS; valid fixtures decode and every unsafe parameter is rejected at its JSON path.

- [x] **Step 5: Commit the controlled vocabulary**

```bash
git add linear_algebra/teaching/vocabulary.py linear_algebra/teaching/model.py tests/test_linear_algebra_visual_vocabulary.py tests/teaching_fixtures.py
git commit -m "feat: constrain visual semantics vocabulary"
```

<!-- openspec-task: 1.5 -->
### Task 5: Validate Artifact Schema and Closed References

**Files:**
- Create: `linear_algebra/teaching/schema.py`
- Create: `linear_algebra/teaching/validation.py`
- Create: `linear_algebra/teaching/artifact.schema.json`
- Test: `tests/test_linear_algebra_artifact_validation.py`

**Interfaces:**
- Consumes: a raw artifact mapping or `TeachingArtifact`.
- Produces: `ValidationIssue`, `ArtifactValidationError`, `validate_artifact_payload(payload)`, and `validate_closed_references(artifact)`.

- [ ] **Step 1: Write failing field-path and dangling-reference tests**

```python
import pytest

from linear_algebra.teaching.validation import ArtifactValidationError, validate_artifact_payload


def test_missing_claims_reports_json_path() -> None:
    payload = composition_artifact_payload()
    del payload["claims"]
    with pytest.raises(ArtifactValidationError) as raised:
        validate_artifact_payload(payload)
    assert raised.value.issues[0].path == "$.claims"


def test_dangling_entity_reference_is_rejected() -> None:
    payload = composition_artifact_payload()
    payload["claims"][0]["entity_refs"].append("missing")
    with pytest.raises(ArtifactValidationError, match="missing"):
        validate_artifact_payload(payload)
```

- [ ] **Step 2: Run validation tests and verify failure**

Run: `pytest tests/test_linear_algebra_artifact_validation.py -q`

Expected: FAIL because validation entry points do not exist.

- [x] **Step 3: Implement schema-first then graph-reference validation**

```python
@dataclass(frozen=True)
class ValidationIssue:
    code: str
    path: str
    message: str


class ArtifactValidationError(ValueError):
    def __init__(self, issues: Iterable[ValidationIssue]) -> None:
        self.issues = tuple(issues)
        super().__init__("; ".join(f"{i.path}: {i.message}" for i in self.issues))


def validate_artifact_payload(payload: Mapping[str, object]) -> TeachingArtifact:
    schema_issues = _jsonschema_issues(payload)
    if schema_issues:
        raise ArtifactValidationError(schema_issues)
    artifact = TeachingArtifact.from_dict(payload)
    reference_issues = validate_closed_references(artifact)
    if reference_issues:
        raise ArtifactValidationError(reference_issues)
    return artifact
```

Check uniqueness before membership: claim IDs, entity IDs, relation IDs, stage IDs, source span IDs, and connection topic IDs. Keep issues deterministically sorted by path then code.

- [x] **Step 4: Run schema, model, and source tests**

Run: `pytest tests/test_linear_algebra_artifact_validation.py tests/test_linear_algebra_teaching_model.py tests/test_linear_algebra_teaching_source.py -q`

Expected: PASS with exact JSON-path diagnostics.

- [x] **Step 5: Commit schema validation**

```bash
git add linear_algebra/teaching/schema.py linear_algebra/teaching/validation.py linear_algebra/teaching/artifact.schema.json tests/test_linear_algebra_artifact_validation.py
git commit -m "feat: validate teaching artifact graphs"
```

<!-- openspec-task: 1.6 -->
### Task 6: Bind Claims, Formula Symbols, and Visual Evidence

**Files:**
- Modify: `linear_algebra/teaching/validation.py`
- Modify: `tests/teaching_fixtures.py`
- Test: `tests/test_linear_algebra_claim_bindings.py`

**Interfaces:**
- Consumes: `TeachingArtifact.claims`, `ExplanationContentV2.symbol_roles`, and visual graph IDs.
- Produces: `validate_claim_bindings(artifact: TeachingArtifact) -> tuple[ValidationIssue, ...]`.

- [ ] **Step 1: Write failing binding tests for composition and projection**

```python
from linear_algebra.teaching.validation import validate_claim_bindings


def test_composition_claim_binds_formula_symbols_and_two_stages() -> None:
    artifact = TeachingArtifact.from_dict(composition_artifact_payload())
    assert validate_claim_bindings(artifact) == ()


def test_projection_claim_without_residual_evidence_fails() -> None:
    artifact = TeachingArtifact.from_dict(projection_artifact_payload(with_residual=False))
    issues = validate_claim_bindings(artifact)
    assert any(issue.code == "claim_missing_evidence" for issue in issues)
```

- [ ] **Step 2: Run claim-binding tests and verify failure**

Run: `pytest tests/test_linear_algebra_claim_bindings.py -q`

Expected: FAIL because `validate_claim_bindings` is missing.

- [x] **Step 3: Implement explicit symbol and evidence checks**

```python
def validate_claim_bindings(artifact: TeachingArtifact) -> tuple[ValidationIssue, ...]:
    entity_ids = {entity.id for entity in artifact.visual_semantics.entities}
    relation_ids = {relation.id for relation in artifact.visual_semantics.relations}
    stage_ids = {stage.id for stage in artifact.visual_semantics.stages}
    known_symbols = set(artifact.explanation.symbol_roles)
    issues: list[ValidationIssue] = []
    for index, claim in enumerate(artifact.claims):
        path = f"$.claims[{index}]"
        if claim.formula:
            for symbol in _declared_formula_symbols(claim.formula):
                if symbol not in known_symbols and symbol not in entity_ids:
                    issues.append(ValidationIssue("unbound_formula_symbol", f"{path}.formula", symbol))
        if claim.entity_refs and not (set(claim.entity_refs) & entity_ids):
            issues.append(ValidationIssue("claim_missing_evidence", path, claim.id))
        _append_missing_refs(issues, path, claim, entity_ids, relation_ids, stage_ids)
    return tuple(sorted(issues, key=lambda issue: (issue.path, issue.code)))
```

Do not attempt general TeX parsing. Require `formula_symbols` in the claim payload and verify those declared symbols against `symbol_roles`/entity IDs; use the formula string only for presentation.

- [x] **Step 4: Verify all fixture claim graphs**

Run: `pytest tests/test_linear_algebra_claim_bindings.py tests/test_linear_algebra_artifact_validation.py -q`

Expected: PASS for complete fixtures and deterministic failures for missing residual, endpoint, or area evidence.

- [x] **Step 5: Commit claim bindings**

```bash
git add linear_algebra/teaching/validation.py tests/teaching_fixtures.py tests/test_linear_algebra_claim_bindings.py
git commit -m "feat: bind claims to visual evidence"
```

<!-- openspec-task: 2.1 -->
### Task 7: Add the Explanation Agent Protocol and Provider Adapter

**Files:**
- Create: `linear_algebra/teaching/agent.py`
- Modify: `linear_algebra/teaching/__init__.py`
- Test: `tests/test_linear_algebra_explanation_agent.py`

**Interfaces:**
- Consumes: `SourceContext`, `LessonEntry`, `TeachingProfile`, `VisualVocabulary`, and an injected provider.
- Produces: `ExplanationAgent.generate(...) -> TeachingArtifactDraft` and `ProviderExplanationAgent`.

- [x] **Step 1: Write a failing fake-provider contract test**

```python
class FakeProvider:
    def request_json(self, *, system: str, user: str) -> str:
        self.request = (system, user)
        return json.dumps(composition_artifact_payload(), ensure_ascii=False)


def test_provider_adapter_returns_a_draft_without_scene_access(source_context, topic) -> None:
    provider = FakeProvider()
    agent = ProviderExplanationAgent(provider)
    draft = agent.generate(source_context, topic, profile_for(topic.id), VisualVocabulary.v1())
    assert draft.artifact.topic_id == topic.id
    assert draft.raw_reply.startswith("{")
    assert "CommandPlan" not in provider.request[1]
```

- [x] **Step 2: Run the agent test and verify missing protocol failure**

Run: `pytest tests/test_linear_algebra_explanation_agent.py -q`

Expected: FAIL because the explanation-agent module is absent.

- [x] **Step 3: Implement an injected, non-rendering adapter**

```python
class JsonTextProvider(Protocol):
    def request_json(self, *, system: str, user: str) -> str: ...


class ExplanationAgent(Protocol):
    def generate(
        self,
        context: SourceContext,
        topic: LessonEntry,
        profile: TeachingProfile,
        vocabulary: VisualVocabulary,
    ) -> TeachingArtifactDraft: ...


class ProviderExplanationAgent:
    def __init__(self, provider: JsonTextProvider) -> None:
        self.provider = provider

    def generate(self, context, topic, profile, vocabulary) -> TeachingArtifactDraft:
        system, user = build_explanation_prompt(context, topic, profile, vocabulary)
        raw_reply = self.provider.request_json(system=system, user=user)
        artifact = parse_agent_reply(raw_reply, expected_topic_id=topic.id)
        return TeachingArtifactDraft(artifact=artifact, raw_reply=raw_reply)
```

The adapter must not accept a scene host or `SceneCommandService`. Cancellation is delegated to the injected provider and must surface without writing a draft.

- [x] **Step 4: Run fake-provider and existing provider tests**

Run: `pytest tests/test_linear_algebra_explanation_agent.py tests/test_agent_provider.py -q`

Expected: PASS; existing command-plan providers are unchanged.

- [x] **Step 5: Commit the agent boundary**

```bash
git add linear_algebra/teaching/agent.py linear_algebra/teaching/__init__.py tests/test_linear_algebra_explanation_agent.py
git commit -m "feat: add teaching explanation agent boundary"
```

<!-- openspec-task: 2.2 -->
### Task 8: Compose the Inert-Source JSON Prompt

**Files:**
- Create: `linear_algebra/teaching/prompt.py`
- Test: `tests/test_linear_algebra_explanation_prompt.py`

**Interfaces:**
- Consumes: the four inputs of `ExplanationAgent.generate`.
- Produces: `PROMPT_VERSION` and `build_explanation_prompt(...) -> tuple[str, str]`.

- [x] **Step 1: Write a failing prompt snapshot test**

```python
def test_prompt_requires_claims_math_and_visual_semantics(source_context, topic) -> None:
    system, user = build_explanation_prompt(
        source_context, topic, profile_for(topic.id), VisualVocabulary.v1()
    )
    assert PROMPT_VERSION == "teaching-artifact-v1"
    assert "只返回一个 JSON 对象" in system
    assert "不得输出绘图命令" in system
    assert "claims" in user
    assert source_context.excerpt in user
    assert "<lecture-source" in user and "</lecture-source>" in user
```

- [x] **Step 2: Run the prompt test and verify failure**

Run: `pytest tests/test_linear_algebra_explanation_prompt.py -q`

Expected: FAIL because `prompt.py` is missing.

- [x] **Step 3: Implement explicit prompt sections and schema projection**

```python
PROMPT_VERSION = "teaching-artifact-v1"


def build_explanation_prompt(context, topic, profile, vocabulary) -> tuple[str, str]:
    system = (
        "你是线性代数数学解释子智能体。只依据提供的讲义材料，"
        "只返回一个符合 schema 的 JSON 对象。不得输出绘图命令、代码、Qt、HTML、"
        "CommandPlan 或 scene op。视觉字段只描述数学对象、关系、阶段和不变量。"
    )
    contract = {
        "topic_id": topic.id,
        "teaching_profile": profile.to_dict(),
        "visual_vocabulary": vocabulary.to_dict(),
        "required_top_level_fields": REQUIRED_ARTIFACT_FIELDS,
    }
    user = (
        json.dumps(contract, ensure_ascii=False, sort_keys=True)
        + "\n<lecture-source data-is-inert=\"true\">\n"
        + context.excerpt
        + "\n</lecture-source>"
    )
    return system, user
```

Include the exact expected JSON shape, L0-L4 requirements, numeric check shape, source span IDs, and relation enum in the contract. Do not include scene-operation names as examples.

- [x] **Step 4: Verify prompt snapshot stability**

Run: `pytest tests/test_linear_algebra_explanation_prompt.py -q`

Expected: PASS; changing the prompt requires an intentional `PROMPT_VERSION` update.

- [x] **Step 5: Commit the prompt contract**

```bash
git add linear_algebra/teaching/prompt.py tests/test_linear_algebra_explanation_prompt.py
git commit -m "feat: define lecture-grounded teaching prompt"
```

<!-- openspec-task: 2.3 -->
### Task 9: Parse JSON and Reject Executable Leakage

**Files:**
- Create: `linear_algebra/teaching/parser.py`
- Modify: `linear_algebra/teaching/agent.py`
- Test: `tests/test_linear_algebra_explanation_parser.py`

**Interfaces:**
- Consumes: exact provider response text and expected topic ID.
- Produces: `parse_agent_reply(raw_reply: str, expected_topic_id: str) -> TeachingArtifact` and `AgentReplyError`.

- [ ] **Step 1: Write failing malicious-reply tests**

```python
@pytest.mark.parametrize("raw", [
    "```json\n{}\n```",
    '{"op":"geometry.staged_transform"}',
    '{"note":"PySide6.QtWidgets.QWidget"}',
    '{"note":"linear.upsert"}',
])
def test_parser_rejects_non_contract_or_executable_reply(raw: str) -> None:
    with pytest.raises(AgentReplyError):
        parse_agent_reply(raw, expected_topic_id="ch02.matrix.composition")


def test_parser_rejects_wrong_topic_id() -> None:
    raw = json.dumps(composition_artifact_payload() | {"topic_id": "other"})
    with pytest.raises(AgentReplyError, match="topic_id"):
        parse_agent_reply(raw, expected_topic_id="ch02.matrix.composition")
```

- [ ] **Step 2: Run parser tests and verify failure**

Run: `pytest tests/test_linear_algebra_explanation_parser.py -q`

Expected: FAIL because parser and error types do not exist.

- [ ] **Step 3: Implement exact-JSON parsing and recursive key/value scanning**

```python
FORBIDDEN_KEYS = frozenset({"op", "operations", "command_plan", "python", "html", "qt"})
FORBIDDEN_TEXT = re.compile(r"(?:geometry\.|linear(?:3d)?\.|CommandPlan|PySide6|PyVista|<script)", re.I)


def parse_agent_reply(raw_reply: str, expected_topic_id: str) -> TeachingArtifact:
    if raw_reply.lstrip().startswith("```"):
        raise AgentReplyError("markdown_fence", "reply must be a bare JSON object")
    try:
        payload = json.loads(raw_reply)
    except json.JSONDecodeError as error:
        raise AgentReplyError("invalid_json", error.msg) from error
    if not isinstance(payload, dict):
        raise AgentReplyError("invalid_root", "reply root must be an object")
    leakage = _find_forbidden(payload, path="$")
    if leakage:
        raise AgentReplyError("executable_leakage", leakage)
    artifact = validate_artifact_payload(payload)
    if artifact.topic_id != expected_topic_id:
        raise AgentReplyError("topic_mismatch", artifact.topic_id)
    return artifact
```

Scan all keys and string values with bounded recursion and message length. Allow mathematical words such as “operation” only when they do not match a namespaced scene command.

- [ ] **Step 4: Run parser and agent tests**

Run: `pytest tests/test_linear_algebra_explanation_parser.py tests/test_linear_algebra_explanation_agent.py -q`

Expected: PASS; rejected replies never produce a `TeachingArtifactDraft`.

- [ ] **Step 5: Commit safe response parsing**

```bash
git add linear_algebra/teaching/parser.py linear_algebra/teaching/agent.py tests/test_linear_algebra_explanation_parser.py
git commit -m "feat: reject executable teaching replies"
```

<!-- openspec-task: 2.4 -->
### Task 10: Validate Claim Source Evidence and Staleness

**Files:**
- Modify: `linear_algebra/teaching/validation.py`
- Test: `tests/test_linear_algebra_source_evidence.py`

**Interfaces:**
- Consumes: `TeachingArtifact`, current `SourceContext`, and catalog `LessonEntry`.
- Produces: `validate_source_evidence(artifact, context, entry) -> tuple[ValidationIssue, ...]`.

- [ ] **Step 1: Write failing source evidence tests**

```python
def test_claim_source_refs_must_resolve_in_current_context(source_context, topic) -> None:
    artifact = TeachingArtifact.from_dict(composition_artifact_payload())
    assert validate_source_evidence(artifact, source_context, topic) == ()


def test_changed_excerpt_reports_stale_source(source_context, topic) -> None:
    changed = replace(source_context, source_hash="sha256:changed")
    issues = validate_source_evidence(
        TeachingArtifact.from_dict(composition_artifact_payload()), changed, topic
    )
    assert [issue.code for issue in issues] == ["stale_source"]
```

- [ ] **Step 2: Run evidence tests and verify failure**

Run: `pytest tests/test_linear_algebra_source_evidence.py -q`

Expected: FAIL because the source-evidence validator is missing.

- [ ] **Step 3: Implement anchor, hash, and span-reference checks**

```python
def validate_source_evidence(artifact, context, entry) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    if artifact.topic_id != entry.id:
        issues.append(ValidationIssue("topic_mismatch", "$.topic_id", artifact.topic_id))
    if artifact.source.heading_path != entry.source_anchor.heading_path:
        issues.append(ValidationIssue("source_anchor_mismatch", "$.source.heading_path", entry.id))
    if artifact.source.source_hash != context.source_hash:
        issues.append(ValidationIssue("stale_source", "$.source.source_hash", entry.id))
    allowed_spans = {span.id: span for span in context.spans}
    for claim_index, claim in enumerate(artifact.claims):
        for span_id in claim.source_refs:
            if span_id not in allowed_spans:
                issues.append(ValidationIssue(
                    "source_ref_out_of_context", f"$.claims[{claim_index}].source_refs", span_id
                ))
    return tuple(sorted(issues, key=lambda issue: (issue.path, issue.code)))
```

If source references include a quote fingerprint, recompute it against the referenced span. Neighboring titles may support `connections`, but not definitions or formulas.

- [ ] **Step 4: Run all plan-1 tests**

Run: `pytest tests/test_linear_algebra_teaching_source.py tests/test_linear_algebra_teaching_model.py tests/test_linear_algebra_teaching_profiles.py tests/test_linear_algebra_visual_vocabulary.py tests/test_linear_algebra_artifact_validation.py tests/test_linear_algebra_claim_bindings.py tests/test_linear_algebra_explanation_agent.py tests/test_linear_algebra_explanation_prompt.py tests/test_linear_algebra_explanation_parser.py tests/test_linear_algebra_source_evidence.py -q`

Expected: PASS.

- [ ] **Step 5: Commit source evidence validation**

```bash
git add linear_algebra/teaching/validation.py tests/test_linear_algebra_source_evidence.py
git commit -m "feat: validate teaching source evidence"
```
