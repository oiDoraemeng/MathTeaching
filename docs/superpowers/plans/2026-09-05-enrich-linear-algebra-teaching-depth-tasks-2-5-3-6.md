# Linear Algebra Teaching Artifact and Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic teaching-depth checks, numeric example verification, versioned raw-reply storage, review/publish workflows, and legacy compatibility.

**Architecture:** This plan builds on the types and validators from plan 1. `TeachingArtifactStore` keeps exact accepted model replies in an audit area while the runtime index points only to normalized published artifacts. Numeric checks are a typed evaluator, not general-purpose expression evaluation. Legacy explanation resources remain read-only through an adapter.

**Tech Stack:** Python 3.11+, dataclasses, `jsonschema`, `hashlib`, `tempfile`, `pathlib`, NumPy/SymPy only through bounded typed math helpers, pytest.

**Spec:** `openspec/changes/enrich-linear-algebra-teaching-depth/design.md`, `linear-algebra-explanation-depth`, `linear-algebra-teaching-artifact`, and `linear-algebra-explanation-agent` specs.

## Global Constraints

- Runtime content reads `published` only; `draft` and `reviewed` never enter the runtime index.
- Accepted raw JSON is audit data, not a scene or renderer input.
- Failed publication keeps the previous published revision readable.
- Numeric verification must be bounded and deterministic; do not use `eval`/`exec`.
- A stale source hash blocks publication but does not delete the prior published revision.
- Existing `ExplanationContent` reads remain compatible until all 54 topics migrate.

## File Structure

- Modify `linear_algebra/teaching/validation.py`: depth and numeric validation.
- Create `linear_algebra/teaching/examples.py`: typed numeric checks.
- Create `linear_algebra/teaching/store.py`: draft/reviewed/published persistence.
- Create `linear_algebra/teaching/revisions.py`: digest, diff, and revision index.
- Create `linear_algebra/teaching/legacy.py`: old explanation adapter.
- Create tests under `tests/test_linear_algebra_teaching_depth.py`, `..._examples.py`, `..._store.py`, `..._revisions.py`, and `..._legacy.py`.

---

<!-- openspec-task: 2.5 -->
### Task 1: Enforce the L0-L4 Teaching Profile

**Files:**
- Modify: `linear_algebra/teaching/validation.py`
- Modify: `linear_algebra/teaching/profiles.py`
- Test: `tests/test_linear_algebra_teaching_depth.py`

**Interfaces:**
- Consumes: `TeachingArtifact.teaching_profile` and `TeachingArtifact.explanation`.
- Produces: `validate_teaching_depth(artifact) -> tuple[ValidationIssue, ...]`.

- [x] **Step 1: Write failing L2/L3/L4 completeness tests**

```python
def test_l3_requires_example_geometry_and_invariant() -> None:
    artifact = artifact_with_profile("L3", worked_examples=(), geometric_meaning="", invariants=())
    issues = validate_teaching_depth(artifact)
    codes = {issue.code for issue in issues}
    assert {"missing_worked_example", "missing_geometric_meaning", "missing_invariant"} <= codes


def test_l4_requires_connection_and_variant() -> None:
    artifact = artifact_with_profile("L4", connections=(), transfer_note="")
    issues = validate_teaching_depth(artifact)
    assert "missing_connection" in {issue.code for issue in issues}
```

- [x] **Step 2: Run depth tests and verify failure**

Run: `pytest tests/test_linear_algebra_teaching_depth.py -q`

Expected: FAIL because `validate_teaching_depth` is missing.

- [x] **Step 3: Implement profile-driven field checks**

```python
def validate_teaching_depth(artifact: TeachingArtifact) -> tuple[ValidationIssue, ...]:
    profile = profile_for(artifact.topic_id)
    explanation = artifact.explanation
    issues: list[ValidationIssue] = []
    required = set(profile.required_sections)
    values = explanation.section_presence()
    for section in sorted(required):
        if not values.get(section):
            issues.append(ValidationIssue("missing_profile_section", f"$.explanation.{section}", section))
    if profile.minimum_level >= TeachingLevel.CALCULATE and not explanation.worked_examples:
        issues.append(ValidationIssue("missing_worked_example", "$.explanation.worked_examples", artifact.topic_id))
    if profile.minimum_level >= TeachingLevel.EXPLAIN and not explanation.invariants:
        issues.append(ValidationIssue("missing_invariant", "$.explanation.invariants", artifact.topic_id))
    if profile.minimum_level >= TeachingLevel.TRANSFER and not explanation.connections:
        issues.append(ValidationIssue("missing_connection", "$.explanation.connections", artifact.topic_id))
    if profile.requires_analogy_boundary and not explanation.analogy_boundary:
        issues.append(ValidationIssue("missing_analogy_boundary", "$.explanation.analogy_boundary", artifact.topic_id))
    return tuple(issues)
```

Treat empty strings, empty arrays, and whitespace-only Markdown as missing. Do not infer depth from word count.

- [x] **Step 4: Run depth and artifact validation tests**

Run: `pytest tests/test_linear_algebra_teaching_depth.py tests/test_linear_algebra_artifact_validation.py -q`

Expected: PASS.

- [x] **Step 5: Commit depth validation**

```bash
git add linear_algebra/teaching/validation.py linear_algebra/teaching/profiles.py tests/test_linear_algebra_teaching_depth.py
git commit -m "feat: validate teaching depth profiles"
```

<!-- openspec-task: 2.6 -->
### Task 2: Add a Bounded Numeric Example Verifier

**Files:**
- Create: `linear_algebra/teaching/examples.py`
- Modify: `linear_algebra/teaching/validation.py`
- Test: `tests/test_linear_algebra_teaching_examples.py`

**Interfaces:**
- Consumes: `WorkedExample` typed inputs and checks.
- Produces: `ExampleCheckResult`, `verify_worked_example(example)`, and `validate_worked_examples(artifact)`.

- [ ] **Step 1: Write exact and tolerance-bound tests**

```python
def test_matrix_transform_example_is_recomputed() -> None:
    example = matrix_transform_example()
    result = verify_worked_example(example)
    assert result.valid is True
    assert result.checks[0].expected == (-2.0, 1.0)


def test_wrong_determinant_is_rejected() -> None:
    example = determinant_example(expected=6.0)
    result = verify_worked_example(example)
    assert result.valid is False
    assert result.checks[0].code == "value_mismatch"
```

- [ ] **Step 2: Run numeric tests and verify missing verifier failure**

Run: `pytest tests/test_linear_algebra_teaching_examples.py -q`

Expected: FAIL because `examples.py` is missing.

- [ ] **Step 3: Implement typed calculators only**

```python
SUPPORTED_KINDS = frozenset({
    "vector_addition", "inner_product", "projection", "matrix_transform",
    "determinant", "oriented_area", "oriented_volume",
})


def verify_worked_example(example: WorkedExample) -> ExampleCheckResult:
    if example.kind not in SUPPORTED_KINDS:
        return ExampleCheckResult.manual("unsupported_example_kind")
    actual = _calculate(example.kind, example.given)
    checks = tuple(_compare_check(check, actual) for check in example.checks)
    return ExampleCheckResult(valid=all(item.valid for item in checks), checks=checks)
```

Use explicit matrix/vector operations and `math.isclose` with a documented absolute/relative tolerance. Reject unsupported symbolic calculations as `manual_review_required`; never execute strings as Python.

- [ ] **Step 4: Integrate numeric checks into artifact validation**

```python
def validate_worked_examples(artifact: TeachingArtifact) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    for index, example in enumerate(artifact.explanation.worked_examples):
        result = verify_worked_example(example)
        if result.manual_review:
            issues.append(ValidationIssue("manual_review_required", f"$.explanation.worked_examples[{index}]", example.kind))
        elif not result.valid:
            issues.append(ValidationIssue("worked_example_mismatch", f"$.explanation.worked_examples[{index}]", example.kind))
    return tuple(issues)
```

- [ ] **Step 5: Run all numeric and artifact tests**

Run: `pytest tests/test_linear_algebra_teaching_examples.py tests/test_linear_algebra_artifact_validation.py -q`

Expected: PASS; wrong calculations never reach publish.

- [ ] **Step 6: Commit the verifier**

```bash
git add linear_algebra/teaching/examples.py linear_algebra/teaching/validation.py tests/test_linear_algebra_teaching_examples.py
git commit -m "feat: verify teaching numeric examples"
```

<!-- openspec-task: 2.7 -->
### Task 3: Add Draft Generation Fixtures and Stable Metadata

**Files:**
- Modify: `linear_algebra/teaching/agent.py`
- Create: `linear_algebra/teaching/generation.py`
- Create: `scripts/generate_linear_algebra_teaching.py`
- Test: `tests/test_linear_algebra_teaching_generation.py`

**Interfaces:**
- Consumes: `TeachingArtifactDraft` from plan 1.
- Produces: `GenerationRequest`, `GenerationReceipt`, `generate_draft(agent, request)`, and a chapter/topic CLI that writes drafts through `TeachingArtifactStore`.

- [ ] **Step 1: Write metadata determinism tests**

```python
def test_generation_receipt_records_source_and_prompt_versions(fake_agent, context, topic) -> None:
    draft = generate_draft(fake_agent, GenerationRequest(context=context, topic=topic, profile=profile_for(topic.id)))
    assert draft.artifact.generated.source_hash == context.source_hash
    assert draft.artifact.generated.prompt_version == "teaching-artifact-v1"
    assert draft.artifact.generated.schema_version == 1
    assert draft.artifact.generated.provider == "fake"


def test_cli_requires_exactly_one_topic_or_chapter() -> None:
    result = cli_runner(["--topic", "ch02.matrix.composition", "--chapter", "2"])
    assert result.exit_code == 2
```

- [ ] **Step 2: Run generation tests and verify missing function failure**

Run: `pytest tests/test_linear_algebra_teaching_generation.py -q`

Expected: FAIL because `generation.py` is missing.

- [ ] **Step 3: Implement request construction and receipt attachment**

```python
@dataclass(frozen=True)
class GenerationRequest:
    context: SourceContext
    topic: LessonEntry
    profile: TeachingProfile


def generate_draft(agent: ExplanationAgent, request: GenerationRequest) -> TeachingArtifactDraft:
    draft = agent.generate(request.context, request.topic, request.profile, VisualVocabulary.v1())
    receipt = replace(
        draft.artifact.generated,
        source_hash=request.context.source_hash,
        prompt_version=PROMPT_VERSION,
        schema_version=1,
    )
    return replace(draft, artifact=replace(draft.artifact, generated=receipt, status="draft"))
```

Use provider metadata supplied by the adapter; never invent a model identifier. Keep fixture generation deterministic by using a fake provider in tests.

Add a thin CLI with mutually exclusive `--topic TOPIC_ID` and `--chapter {1,2,3}`, required `--output-root`, and injected provider construction. It must save only drafts and print one JSON summary per topic; it must never publish automatically.

- [ ] **Step 4: Verify stable regeneration metadata**

Run: `pytest tests/test_linear_algebra_teaching_generation.py tests/test_linear_algebra_explanation_agent.py -q`

Run: `python scripts/generate_linear_algebra_teaching.py --help`

Expected: tests PASS and help lists `--topic`, `--chapter`, and `--output-root`.

- [ ] **Step 5: Commit draft generation**

```bash
git add linear_algebra/teaching/generation.py linear_algebra/teaching/agent.py scripts/generate_linear_algebra_teaching.py tests/test_linear_algebra_teaching_generation.py
git commit -m "feat: record teaching draft generation metadata"
```

<!-- openspec-task: 3.1 -->
### Task 4: Persist Versioned Teaching Artifacts

**Files:**
- Create: `linear_algebra/teaching/store.py`
- Modify: `linear_algebra/teaching/__init__.py`
- Test: `tests/test_linear_algebra_teaching_store.py`

**Interfaces:**
- Consumes: `TeachingArtifactDraft` and validated `TeachingArtifact`.
- Produces: `TeachingArtifactStore.save_draft`, `.get`, `.published`, `.list_revisions`, and deterministic JSON files.

- [ ] **Step 1: Write a filesystem round-trip test**

```python
def test_store_writes_stable_utf8_json(tmp_path) -> None:
    store = TeachingArtifactStore(tmp_path)
    artifact = TeachingArtifact.from_dict(composition_artifact_payload())
    store.save_draft(artifact, raw_reply=json.dumps(artifact.to_dict(), ensure_ascii=False))
    path = tmp_path / "drafts" / "ch02" / "ch02.matrix.composition" / "r1.json"
    assert path.read_text(encoding="utf-8").endswith("\n")
    assert json.loads(path.read_text(encoding="utf-8"))["topic_id"] == "ch02.matrix.composition"
```

- [ ] **Step 2: Run store test and verify missing store failure**

Run: `pytest tests/test_linear_algebra_teaching_store.py -q`

Expected: FAIL because `TeachingArtifactStore` is missing.

- [ ] **Step 3: Implement stable paths, serialization, and revision allocation**

```python
class TeachingArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def save_draft(self, artifact: TeachingArtifact, *, raw_reply: str) -> ArtifactRevision:
        revision = self._next_revision("drafts", artifact.topic_id)
        payload = {"artifact": artifact.to_dict(), "raw_reply": raw_reply}
        path = self._path("drafts", artifact.topic_id, revision)
        _write_stable_json(path, payload)
        return ArtifactRevision(artifact.topic_id, revision, "draft")

    def get(self, topic_id: str, revision: int, state: ArtifactStatus) -> StoredArtifact:
        payload = json.loads(self._path(_state_dir(state), topic_id, revision).read_text(encoding="utf-8"))
        return StoredArtifact.from_payload(payload)
```

Use `json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"`; write only within the configured store root and reject path traversal in topic IDs.

- [ ] **Step 4: Run store round-trip and path-safety tests**

Run: `pytest tests/test_linear_algebra_teaching_store.py -q`

Expected: PASS; exact raw JSON is recoverable and paths remain inside the store root.

- [ ] **Step 5: Commit artifact storage**

```bash
git add linear_algebra/teaching/store.py linear_algebra/teaching/__init__.py tests/test_linear_algebra_teaching_store.py
git commit -m "feat: persist versioned teaching artifacts"
```

<!-- openspec-task: 3.2 -->
### Task 5: Preserve Raw Replies and Audit Digests

**Files:**
- Modify: `linear_algebra/teaching/store.py`
- Modify: `linear_algebra/teaching/model.py`
- Test: `tests/test_linear_algebra_teaching_audit.py`

**Interfaces:**
- Consumes: accepted/rejected `TeachingArtifactDraft` results.
- Produces: `RawReplyAudit`, `reply_digest`, and store methods that never expose raw reply to compiler callers.

- [ ] **Step 1: Write audit isolation tests**

```python
def test_accepted_raw_reply_is_recoverable_but_not_in_runtime_artifact(tmp_path) -> None:
    store = TeachingArtifactStore(tmp_path)
    artifact = TeachingArtifact.from_dict(composition_artifact_payload())
    revision = store.save_reviewed(artifact, raw_reply='{"accepted":true}')
    assert store.audit_raw_reply(revision).raw_reply == '{"accepted":true}'
    assert "raw_reply" not in store.get_published_payload(revision)


def test_rejected_reply_keeps_only_bounded_diagnostics(tmp_path) -> None:
    store = TeachingArtifactStore(tmp_path)
    audit = store.save_rejection(topic_id="ch02.matrix.composition", raw_reply="secret", code="executable_leakage", message="x" * 10000)
    assert len(audit.message) <= 512
    assert audit.raw_reply is None
```

- [ ] **Step 2: Run audit tests and verify missing audit behavior**

Run: `pytest tests/test_linear_algebra_teaching_audit.py -q`

Expected: FAIL because audit methods are missing.

- [ ] **Step 3: Implement separate audit storage and digesting**

```python
def reply_digest(raw_reply: str) -> str:
    return "sha256:" + hashlib.sha256(raw_reply.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RawReplyAudit:
    reply_digest: str
    raw_reply: str | None
    error_code: str | None
    message: str


def save_rejection(self, *, topic_id, raw_reply, code, message):
    audit = RawReplyAudit(reply_digest(raw_reply), None, code, message[:512])
    self._write_audit(topic_id, audit)
    return audit
```

Store raw accepted replies under an audit-only path. `get_published_payload` strips audit fields and returns only normalized artifact data.

- [ ] **Step 4: Run store, audit, and parser tests**

Run: `pytest tests/test_linear_algebra_teaching_store.py tests/test_linear_algebra_teaching_audit.py tests/test_linear_algebra_explanation_parser.py -q`

Expected: PASS.

- [ ] **Step 5: Commit raw-reply audit isolation**

```bash
git add linear_algebra/teaching/store.py linear_algebra/teaching/model.py tests/test_linear_algebra_teaching_audit.py
git commit -m "feat: preserve teaching reply audit records"
```

<!-- openspec-task: 3.3 -->
### Task 6: Add Atomic Review and Publish

**Files:**
- Modify: `linear_algebra/teaching/store.py`
- Modify: `linear_algebra/teaching/validation.py`
- Create: `scripts/review_linear_algebra_teaching.py`
- Test: `tests/test_linear_algebra_teaching_publish.py`
- Test: `tests/test_linear_algebra_teaching_review_cli.py`

**Interfaces:**
- Consumes: stored draft revision, explicit reviewer decision, current source context, validation pipeline.
- Produces: `review_draft(topic_id, revision, reviewer)`, `publish(reviewed_artifact, ...)`, `PublishResult`, and an interactive chapter review CLI.

- [ ] **Step 1: Write publish rollback tests**

```python
def test_publish_replaces_index_only_after_all_validation_passes(tmp_path, source_context, topic) -> None:
    store = seeded_store(tmp_path)
    old = store.published(topic.id)
    broken = artifact_with_wrong_determinant(status="reviewed")
    result = store.publish(broken, source_context=source_context, topic=topic)
    assert result.ok is False
    assert store.published(topic.id).artifact_digest == old.artifact_digest


def test_publish_rejects_a_valid_but_unreviewed_draft(tmp_path, source_context, topic) -> None:
    store = seeded_store(tmp_path)
    result = store.publish(valid_artifact(status="draft"), source_context=source_context, topic=topic)
    assert result.ok is False
    assert result.issues[0].code == "review_required"
```

- [ ] **Step 2: Run publish tests and verify missing workflow failure**

Run: `pytest tests/test_linear_algebra_teaching_publish.py -q`

Expected: FAIL because review/publish methods are missing.

- [ ] **Step 3: Implement review gate and temporary-file replacement**

```python
def publish(self, artifact, *, source_context, topic) -> PublishResult:
    if artifact.status != "reviewed":
        return PublishResult(
            ok=False,
            issues=(ValidationIssue("status", "review_required", "publish requires an explicitly reviewed revision"),),
        )
    try:
        validate_artifact_payload(artifact.to_dict())
    except ArtifactValidationError as error:
        return PublishResult(ok=False, issues=error.issues)
    issues = (
        *validate_source_evidence(artifact, source_context, topic),
        *validate_teaching_depth(artifact),
        *validate_worked_examples(artifact),
    )
    if issues:
        return PublishResult(ok=False, issues=tuple(issues))
    published = replace(artifact, status="published")
    temp_path = self._write_temp(published)
    self._replace_revision_and_index(temp_path, published)
    return PublishResult(ok=True, revision=published.revision)
```

Implement `review_draft` as a separate transition that copies an immutable draft into the reviewed area and writes reviewer ID, UTC timestamp, source hash, artifact digest, and decision to the audit log. The CLI displays the exact source excerpt, structured explanation, claim bindings, numeric checks, and visual semantics before accepting `review` or `reject`; it must refuse non-interactive bulk approval. Use `os.replace` only after all validations and fsync the temporary file before replacement. Do not remove the old index until the new index is in place.

- [ ] **Step 4: Verify failure injection and successful publication**

Run: `pytest tests/test_linear_algebra_teaching_publish.py tests/test_linear_algebra_teaching_review_cli.py tests/test_linear_algebra_teaching_store.py -q`

Expected: PASS; publication is all-or-nothing and old revision remains readable.

- [ ] **Step 5: Commit review/publish workflow**

```bash
git add linear_algebra/teaching/store.py linear_algebra/teaching/validation.py scripts/review_linear_algebra_teaching.py tests/test_linear_algebra_teaching_publish.py tests/test_linear_algebra_teaching_review_cli.py
git commit -m "feat: add atomic teaching artifact publish"
```

<!-- openspec-task: 3.4 -->
### Task 7: Add Stale-Source Detection and Rollback Reads

**Files:**
- Modify: `linear_algebra/teaching/store.py`
- Modify: `linear_algebra/teaching/validation.py`
- Test: `tests/test_linear_algebra_teaching_stale.py`

**Interfaces:**
- Consumes: published index and current `SourceContext`.
- Produces: `load_published(topic_id, current_context) -> StoredArtifact` with stale status.

- [ ] **Step 1: Write stale read and stale publish tests**

```python
def test_stale_published_revision_remains_readable(tmp_path, source_context, topic) -> None:
    store = seeded_store(tmp_path)
    changed = replace(source_context, source_hash="sha256:new")
    loaded = store.load_published(topic.id, current_context=changed)
    assert loaded.stale is True
    assert loaded.artifact.topic_id == topic.id
```

- [ ] **Step 2: Run stale tests and verify missing behavior**

Run: `pytest tests/test_linear_algebra_teaching_stale.py -q`

Expected: FAIL because stale-aware loading is missing.

- [ ] **Step 3: Implement diagnostic stale status without destructive cleanup**

```python
def load_published(self, topic_id: str, *, current_context: SourceContext) -> LoadedArtifact:
    stored = self.published(topic_id)
    stale = stored.artifact.source.source_hash != current_context.source_hash
    return LoadedArtifact(
        artifact=stored.artifact,
        stale=stale,
        diagnostic=("stale_source", stored.artifact.source.source_hash, current_context.source_hash) if stale else None,
    )
```

Publishing with a stale draft returns `stale_source`; reading the prior revision remains supported and must expose the diagnostic to the UI.

- [ ] **Step 4: Verify stale and publish regression tests**

Run: `pytest tests/test_linear_algebra_teaching_stale.py tests/test_linear_algebra_teaching_publish.py -q`

Expected: PASS.

- [ ] **Step 5: Commit stale-source handling**

```bash
git add linear_algebra/teaching/store.py linear_algebra/teaching/validation.py tests/test_linear_algebra_teaching_stale.py
git commit -m "feat: diagnose stale lecture artifacts"
```

<!-- openspec-task: 3.5 -->
### Task 8: Compare Artifact Revisions Without Rendering

**Files:**
- Create: `linear_algebra/teaching/revisions.py`
- Test: `tests/test_linear_algebra_teaching_revisions.py`

**Interfaces:**
- Consumes: two normalized artifact payloads or revisions.
- Produces: `ArtifactDiff`, `diff_artifacts(old, new)`, and field-level claim/explanation/semantic changes.

- [ ] **Step 1: Write a diff test**

```python
def test_revision_diff_reports_claim_and_visual_changes() -> None:
    old = TeachingArtifact.from_dict(composition_artifact_payload())
    new = TeachingArtifact.from_dict(composition_artifact_payload_with_extra_claim())
    diff = diff_artifacts(old, new)
    assert "claims" in diff.changed_sections
    assert diff.render_requested is False
```

- [ ] **Step 2: Run the diff test and verify missing module failure**

Run: `pytest tests/test_linear_algebra_teaching_revisions.py -q`

Expected: FAIL because `revisions.py` is missing.

- [ ] **Step 3: Implement canonical field comparison**

```python
@dataclass(frozen=True)
class ArtifactDiff:
    changed_sections: tuple[str, ...]
    claim_changes: tuple[FieldChange, ...]
    explanation_changes: tuple[FieldChange, ...]
    visual_changes: tuple[FieldChange, ...]
    render_requested: bool = False


def diff_artifacts(old, new) -> ArtifactDiff:
    return ArtifactDiff(
        changed_sections=_changed_top_level_sections(old.to_dict(), new.to_dict()),
        claim_changes=_diff_keyed("claims", old.claims, new.claims),
        explanation_changes=_diff_dataclass(old.explanation, new.explanation),
        visual_changes=_diff_visual_semantics(old.visual_semantics, new.visual_semantics),
    )
```

Sort changes by JSON path and redact raw replies/provider credentials.

- [ ] **Step 4: Run revision and store tests**

Run: `pytest tests/test_linear_algebra_teaching_revisions.py tests/test_linear_algebra_teaching_store.py -q`

Expected: PASS and no scene service is imported by the diff module.

- [ ] **Step 5: Commit revision comparison**

```bash
git add linear_algebra/teaching/revisions.py tests/test_linear_algebra_teaching_revisions.py
git commit -m "feat: compare teaching artifact revisions"
```

<!-- openspec-task: 3.6 -->
### Task 9: Add the Legacy Explanation Adapter

**Files:**
- Create: `linear_algebra/teaching/legacy.py`
- Modify: `linear_algebra/registry.py`
- Test: `tests/test_linear_algebra_teaching_legacy.py`

**Interfaces:**
- Consumes: current `ExplanationContent` catalog values.
- Produces: `adapt_legacy_explanation(topic, content) -> LegacyTeachingArtifact` marked `migration_pending` and read-only.

- [ ] **Step 1: Write compatibility and publication-block tests**

```python
def test_legacy_explanation_can_be_read_as_pending_artifact() -> None:
    topic = catalog_registry().get_topic("ch01.ops.addition")
    artifact = adapt_legacy_explanation(topic, explanation_for(topic.id))
    assert artifact.migration_state == "migration_pending"
    assert artifact.visual_semantics is None


def test_legacy_artifact_cannot_be_published() -> None:
    topic = catalog_registry().get_topic("ch01.ops.addition")
    with pytest.raises(ValueError, match="visual_semantics"):
        publish_legacy_artifact(adapt_legacy_explanation(topic, explanation_for(topic.id)))
```

- [ ] **Step 2: Run legacy tests and verify missing adapter failure**

Run: `pytest tests/test_linear_algebra_teaching_legacy.py -q`

Expected: FAIL because the adapter is missing.

- [ ] **Step 3: Implement a read-only migration adapter**

```python
def adapt_legacy_explanation(entry: LessonEntry, content: ExplanationContent) -> LegacyTeachingArtifact:
    return LegacyTeachingArtifact(
        topic_id=entry.id,
        title=content.title,
        explanation=content,
        migration_state="migration_pending",
        visual_semantics=None,
    )
```

Keep this adapter independent of `catalog_registry()` and `explanation_for()` so `registry.py` can inject both values without a circular import. Keep it outside the published `TeachingArtifact` model; the important contract is read compatibility and an explicit block on new publication without claims/visual semantics.

- [ ] **Step 4: Verify registry compatibility**

Run: `pytest tests/test_linear_algebra_teaching_legacy.py tests/test_linear_algebra_registry.py tests/test_linear_algebra_explanations.py -q`

Expected: PASS; old explanations remain readable and no legacy artifact enters the published index.

- [ ] **Step 5: Run all plan-2 tests**

Run: `pytest tests/test_linear_algebra_teaching_depth.py tests/test_linear_algebra_teaching_examples.py tests/test_linear_algebra_teaching_generation.py tests/test_linear_algebra_teaching_store.py tests/test_linear_algebra_teaching_audit.py tests/test_linear_algebra_teaching_publish.py tests/test_linear_algebra_teaching_stale.py tests/test_linear_algebra_teaching_revisions.py tests/test_linear_algebra_teaching_legacy.py -q`

Expected: PASS.

- [ ] **Step 6: Commit the complete artifact workflow**

```bash
git add linear_algebra/teaching linear_algebra/registry.py tests/test_linear_algebra_teaching_*.py
git commit -m "feat: add reviewed teaching artifact workflow"
```
