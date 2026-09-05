# Linear Algebra Teaching Experience Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete storyboard interaction, deep search, claim/role synchronization, and end-to-end validation for all 54 teaching bundles.

**Architecture:** Web storyboard state selects an already-published stage projection and sends only a bounded display intent when a scene refresh is needed. Search remains local to the curriculum registry but indexes every normalized explanation field. A layered validator reports source, content, semantic-contract, and compiled-plan failures separately, producing a checked-in verification record and focus-topic screenshots.

**Tech Stack:** Python 3.11+/pytest, PySide6, React 18/TypeScript/Vitest, existing Web JSON bridge, existing `SceneCommandService`, application screenshot tooling.

**Spec:** `openspec/changes/enrich-linear-algebra-teaching-depth/design.md`, `linear-algebra-case-tabs`, `linear-algebra-visual-primitives`, `linear-algebra-color-contract`, and `linear-algebra-explanation-depth` specs.

## Global Constraints

- Storyboard navigation never calls the model, creates a case tab, or changes conversation history.
- Search results preserve chapter and section ancestors and never load a topic automatically.
- Claim IDs, stage IDs, formula symbols, semantic entity IDs, roles, and palette colors remain identical across Python and Web projections.
- Validation asserts mathematical relations and actual compiled operations, not operation count alone.
- Any failed topic load leaves the prior scene and explanation visible.
- Final evidence records exactly 54 topics in a 24/15/15 chapter split and includes the artifact/compiler digests used for screenshots.

## File Structure

- Modify Web case state/reader/styles for storyboard and claim highlighting.
- Modify tree search and case projection for deep indexed fields.
- Extend `linear_algebra/validation.py` and create focused validation helpers.
- Add integration tests spanning registry, compiler, bridge, Qt, and Web.
- Create `openspec/changes/enrich-linear-algebra-teaching-depth/verification/` only when the final verification tasks produce evidence.

---

<!-- openspec-task: 6.5 -->
### Task 1: Add Static Storyboard Navigation

**Files:**
- Modify: `ui/agent_web/src/types.ts`
- Modify: `ui/agent_web/src/state/reducer.ts`
- Modify: `ui/agent_web/src/App.tsx`
- Modify: `ui/agent_web/src/components/MathCaseView.tsx`
- Modify: `ui/agent_web/src/styles.css`
- Test: `ui/agent_web/src/state/reducer.test.ts`
- Test: `ui/agent_web/src/components/MathCaseView.test.tsx`

**Interfaces:**
- Consumes: published `CaseProjection.stages` and `claims`.
- Produces: per-case `activeStageId`, `select_case_stage` reducer action, and accessible sequence/side-by-side/overlay controls.

- [ ] **Step 1: Write reducer isolation tests**

```typescript
it("changes only the selected case stage", () => {
  const before = stateWithCompositionCase();
  const after = appReducer(before, { type: "select_case_stage", caseId: "ch02.matrix.composition", stageId: "after-b" });
  expect(after.cases[0].activeStageId).toBe("after-b");
  expect(after.sessions).toEqual(before.sessions);
  expect(after.cases).toHaveLength(1);
});
```

- [ ] **Step 2: Write reader interaction tests**

```tsx
it("navigates stages without sending a model message", async () => {
  const onSelectStage = vi.fn();
  render(<MathCaseView caseData={compositionCase} onSelectStage={onSelectStage} />);
  await user.click(screen.getByRole("button", { name: "先旋转再拉伸" }));
  expect(onSelectStage).toHaveBeenCalledWith("after-ab");
  expect(screen.getByText("A(Bx)=(-2,1)")).toBeInTheDocument();
});
```

- [ ] **Step 3: Run Web tests and verify missing navigation failure**

Run: `pnpm --dir ui/agent_web test -- --run src/state/reducer.test.ts src/components/MathCaseView.test.tsx`

Expected: FAIL because the active stage/action and controls do not exist.

- [ ] **Step 4: Implement stage state and fixed-dimension controls**

```typescript
export interface SelectCaseStageAction {
  type: "select_case_stage";
  caseId: string;
  stageId: string;
}

case "select_case_stage":
  return {
    ...state,
    cases: state.cases.map((item) => item.id === action.caseId && item.stages.some((stage) => stage.id === action.stageId)
      ? { ...item, activeStageId: action.stageId }
      : item),
  };
```

Add `SelectCaseStageAction` to the existing `AppAction` discriminated union. Render sequence stages as previous/next plus a compact stage list, side-by-side stages as a two-lane segmented comparison, and overlay stages as a single stage selector. Give the control a stable min-height so labels cannot shift the reader layout.

- [ ] **Step 5: Run Web tests and build**

Run: `pnpm --dir ui/agent_web test`

Run: `pnpm --dir ui/agent_web build`

Expected: PASS; switching stages neither sends `send_message` nor changes sessions/case count.

- [ ] **Step 6: Commit storyboard navigation**

```bash
git add ui/agent_web/src ui/agent_web/dist
git commit -m "feat: navigate teaching storyboards"
```

<!-- openspec-task: 6.6 -->
### Task 2: Index All Deep Explanation Fields in Tree Search

**Files:**
- Modify: `ui/linear_algebra_tree_model.py`
- Modify: `linear_algebra/registry.py`
- Test: `tests/test_linear_algebra_tree_model.py`

**Interfaces:**
- Consumes: published bundle explanation, claims, worked examples, pitfalls, connections, and reading hints.
- Produces: `searchable_text_for_bundle(bundle) -> str` and ancestor-preserving tree filtering.

- [ ] **Step 1: Write a derivation-only term search test**

```python
def test_search_finds_term_only_present_in_derivation_and_keeps_ancestors(tree) -> None:
    model = LinearAlgebraTreeModel(tree, catalog_registry())
    model.filter("从右向左读")
    assert "ch02.matrix.composition" in model.visible_topic_ids()
    assert model.item_for("ch02") is not None
    assert model.item_for("ch02.s26") is not None
```

- [ ] **Step 2: Run tree tests and verify current shallow-index failure**

Run: `pytest tests/test_linear_algebra_tree_model.py -q`

Expected: FAIL because the current index covers only title, path, summary, formula, and legacy searchable text.

- [ ] **Step 3: Build normalized searchable text from the bundle**

```python
def searchable_text_for_bundle(bundle: TeachingBundle) -> str:
    explanation = bundle.artifact.explanation
    values = (
        bundle.topic.title,
        *bundle.topic.source_path,
        explanation.summary,
        explanation.definition,
        explanation.formula,
        *explanation.steps,
        *explanation.derivation,
        *(item.search_text() for item in explanation.worked_examples),
        *explanation.pitfalls,
        *(item.search_text() for item in explanation.connections),
        explanation.interaction_hint,
        *(claim.statement for claim in bundle.artifact.claims),
    )
    return _normalize(" ".join(value for value in values if value))
```

Resolve bundle content when constructing the search index, not on each keystroke. For a stale but readable bundle, index its published content and retain stale metadata separately.

- [ ] **Step 4: Run tree and registry tests**

Run: `pytest tests/test_linear_algebra_tree_model.py tests/test_linear_algebra_bundle_registry.py -q`

Expected: PASS; no-match still shows an empty tree and does not trigger loading.

- [ ] **Step 5: Commit deep search**

```bash
git add ui/linear_algebra_tree_model.py linear_algebra/registry.py tests/test_linear_algebra_tree_model.py
git commit -m "feat: search deep teaching explanations"
```

<!-- openspec-task: 6.7 -->
### Task 3: Synchronize Claim Highlighting and Teaching Roles

**Files:**
- Modify: `linear_algebra/loading.py`
- Modify: `ui/linear_algebra_content_view.py`
- Modify: `ui/agent_sidebar_web.py`
- Modify: `ui/agent_web/src/components/MathCaseView.tsx`
- Modify: `ui/agent_web/src/styles.css`
- Test: `tests/test_linear_algebra_case_projection.py`
- Test: `ui/agent_web/src/components/MathCaseView.test.tsx`

**Interfaces:**
- Consumes: active stage ID, claim refs, symbol roles, and shared palette.
- Produces: identical claim/role projections in Qt and Web plus stage-driven highlight state.

- [ ] **Step 1: Write cross-projection equality tests**

```python
def test_qt_and_web_case_projections_share_claim_ids_and_roles() -> None:
    bundle = catalog_registry().get_bundle("ch02.matrix.composition")
    qt = project_qt_case(bundle)
    web = project_case(bundle)
    assert tuple(item.id for item in qt.claims) == tuple(item["id"] for item in web["claims"])
    assert qt.symbol_roles == web["symbol_roles"]
    assert qt.palette == web["palette"]
```

- [ ] **Step 2: Write active-stage highlight tests**

```tsx
it("highlights only claims referenced by the active stage", () => {
  render(<MathCaseView caseData={{ ...compositionCase, activeStageId: "after-ab" }} onSelectStage={() => {}} />);
  expect(screen.getByTestId("claim-composition-order")).toHaveAttribute("data-active", "true");
  expect(screen.getByTestId("claim-area-invariant")).toHaveAttribute("data-active", "false");
});
```

- [ ] **Step 3: Run projection and Web tests and verify failure**

Run: `pytest tests/test_linear_algebra_case_projection.py -q`

Run: `pnpm --dir ui/agent_web test -- --run src/components/MathCaseView.test.tsx`

Expected: FAIL because claim highlighting and shared projection helpers are absent.

- [ ] **Step 4: Implement one canonical projection shape**

```python
@dataclass(frozen=True)
class TeachingCaseProjection:
    topic_id: str
    revision: int
    claims: tuple[ClaimProjection, ...]
    stages: tuple[StageProjection, ...]
    symbol_roles: Mapping[str, str]
    palette: Mapping[str, str]


def active_claim_ids(case: TeachingCaseProjection, stage_id: str) -> tuple[str, ...]:
    stage = next(stage for stage in case.stages if stage.id == stage_id)
    return stage.claim_ids
```

Qt/Web serializers consume this projection. Use `data-role` and CSS custom properties for formula legends and claim markers; do not inject inline arbitrary colors from payload values outside the validated palette.

- [ ] **Step 5: Run projection, Qt, and Web tests**

Run: `pytest tests/test_linear_algebra_case_projection.py tests/test_linear_algebra_content_view.py tests/test_agent_bridge.py -q`

Run: `pnpm --dir ui/agent_web test`

Expected: PASS with matching IDs and colors for every tested stage.

- [ ] **Step 6: Commit synchronized highlighting**

```bash
git add linear_algebra/loading.py ui/linear_algebra_content_view.py ui/agent_sidebar_web.py ui/agent_web/src ui/agent_web/dist tests/test_linear_algebra_case_projection.py
git commit -m "feat: link teaching claims to visual stages"
```

<!-- openspec-task: 7.1 -->
### Task 4: Extend the Curriculum Validator to Published Bundles

**Files:**
- Modify: `linear_algebra/validation.py`
- Modify: `linear_algebra/teaching/content_validation.py`
- Test: `tests/test_linear_algebra_validation.py`

**Interfaces:**
- Consumes: catalog, source repository, artifact store, contract registry, and compiled store.
- Produces: layered `ValidationReport` and CLI output for all 54 bundles.

- [ ] **Step 1: Write a four-layer validation report test**

```python
def test_full_validation_reports_source_content_semantics_and_execution() -> None:
    report = validate_curriculum(catalog_registry())
    assert report.topic_count_by_chapter == {1: 24, 2: 15, 3: 15}
    assert report.source_errors == ()
    assert report.content_errors == ()
    assert report.semantic_errors == ()
    assert report.execution_errors == ()
```

- [ ] **Step 2: Run validator tests and verify report fields are missing**

Run: `pytest tests/test_linear_algebra_validation.py -q`

Expected: FAIL because the existing validator checks only catalog IDs, legacy explanation IDs, recipes, plan validity, and source anchors.

- [ ] **Step 3: Implement layered bundle validation**

```python
@dataclass(frozen=True)
class ValidationReport:
    topic_count_by_chapter: Mapping[int, int]
    source_errors: tuple[str, ...]
    content_errors: tuple[str, ...]
    semantic_errors: tuple[str, ...]
    execution_errors: tuple[str, ...]

    @property
    def errors(self) -> tuple[str, ...]:
        return (*self.source_errors, *self.content_errors, *self.semantic_errors, *self.execution_errors)
```

For each topic: resolve source, load published revision, validate depth/examples/claims, validate contract/evidence, reproduce compiled digest, and validate the plan. Prefix every error with layer and topic ID.

- [ ] **Step 4: Run validator and source tests**

Run: `pytest tests/test_linear_algebra_validation.py tests/test_lecture_source_validation.py -q`

Run: `python -m linear_algebra.validation`

Expected: PASS and CLI prints `54 topics validated: source=54 content=54 semantics=54 plans=54`.

- [ ] **Step 5: Commit layered validation**

```bash
git add linear_algebra/validation.py linear_algebra/teaching/content_validation.py tests/test_linear_algebra_validation.py
git commit -m "feat: validate published teaching bundles"
```

<!-- openspec-task: 7.2 -->
### Task 5: Validate Explanation-to-Visual Consistency

**Files:**
- Modify: `linear_algebra/teaching/validation.py`
- Modify: `linear_algebra/validation.py`
- Test: `tests/test_linear_algebra_explanation_visual_consistency.py`

**Interfaces:**
- Consumes: formula symbol declarations, claim graph, visual graph, and contract.
- Produces: `validate_explanation_visual_consistency(bundle)`.

- [ ] **Step 1: Write wrong-topic and missing-relation tests**

```python
def test_formula_symbol_without_visual_entity_is_reported() -> None:
    bundle = bundle_with_unbound_symbol("det(A)")
    issues = validate_explanation_visual_consistency(bundle)
    assert any(issue.code == "unbound_formula_symbol" for issue in issues)


def test_relation_without_claim_or_contract_is_reported() -> None:
    bundle = bundle_with_orphan_relation("projects_to")
    issues = validate_explanation_visual_consistency(bundle)
    assert any(issue.code == "orphan_visual_relation" for issue in issues)
```

- [ ] **Step 2: Run consistency tests and verify failure**

Run: `pytest tests/test_linear_algebra_explanation_visual_consistency.py -q`

Expected: FAIL because cross-layer orphan detection is absent.

- [ ] **Step 3: Implement bidirectional graph checks**

```python
def validate_explanation_visual_consistency(bundle: TeachingBundle) -> tuple[ValidationIssue, ...]:
    issues = list(validate_claim_bindings(bundle.artifact))
    claim_relations = {relation_id for claim in bundle.artifact.claims for relation_id in claim.relation_refs}
    contract_relations = set(bundle.contract.required_relations)
    for relation in bundle.artifact.visual_semantics.relations:
        if relation.id not in claim_relations and relation.kind not in contract_relations:
            issues.append(ValidationIssue("orphan_visual_relation", f"$.visual_semantics.relations.{relation.id}", bundle.topic.id))
    return tuple(sorted(issues, key=lambda issue: (issue.path, issue.code)))
```

Also verify `topic_id`, source anchor, stage claims, connection topic IDs, and numeric results referenced by annotations.

- [ ] **Step 4: Run consistency and full validation tests**

Run: `pytest tests/test_linear_algebra_explanation_visual_consistency.py tests/test_linear_algebra_validation.py -q`

Expected: PASS.

- [ ] **Step 5: Commit consistency validation**

```bash
git add linear_algebra/teaching/validation.py linear_algebra/validation.py tests/test_linear_algebra_explanation_visual_consistency.py
git commit -m "feat: validate explanation visual consistency"
```

<!-- openspec-task: 7.3 -->
### Task 6: Validate Declared Capabilities Against Actual Operations

**Files:**
- Modify: `linear_algebra/registry.py`
- Modify: `linear_algebra/validation.py`
- Test: `tests/test_linear_algebra_capability_coverage.py`

**Interfaces:**
- Consumes: catalog `required_capabilities`, compiler evidence, and actual plan operations.
- Produces: `validate_capability_coverage(bundle)` with explicit skip reasons for non-operation capabilities.

- [ ] **Step 1: Write missing-operation and declared-skip tests**

```python
def test_transformed_grid_capability_requires_actual_grid_op() -> None:
    bundle = bundle_without_operation("ch02.matrix.transformed-grid", "geometry.transformed_grid")
    issues = validate_capability_coverage(bundle)
    assert any(issue.code == "declared_capability_missing_operation" for issue in issues)


def test_annotation_capability_skip_has_reason() -> None:
    skip = capability_skip("annotation_formula")
    assert skip.reason
```

- [ ] **Step 2: Run capability coverage tests and verify failure**

Run: `pytest tests/test_linear_algebra_capability_coverage.py -q`

Expected: FAIL because current validation checks only whether capability names exist in the registry.

- [ ] **Step 3: Implement exact capability-to-operation coverage**

```python
CAPABILITY_OPERATIONS = MappingProxyType({
    "projection_2d": frozenset({"geometry.projection"}),
    "transformed_grid": frozenset({"geometry.transformed_grid"}),
    "staged_transform": frozenset({"geometry.staged_transform"}),
    "subspace_region": frozenset({"geometry.subspace_region"}),
    "oriented_area_2d": frozenset({"geometry.oriented_area"}),
    "oriented_volume_3d": frozenset({"geometry.oriented_volume"}),
})


def validate_capability_coverage(bundle):
    actual_ops = {operation["op"] for operation in bundle.compiled.plan.operations}
    return _missing_capability_ops(bundle.topic, actual_ops, CAPABILITY_OPERATIONS, DECLARATIVE_CAPABILITY_SKIPS)
```

Every skip record contains capability, scope, and reason. Do not use an empty/global ignore set.

- [ ] **Step 4: Run capability and compiler coverage tests**

Run: `pytest tests/test_linear_algebra_capability_coverage.py tests/test_linear_algebra_visual_compiler_coverage.py tests/test_linear_algebra_capabilities.py -q`

Expected: PASS.

- [ ] **Step 5: Commit operation coverage validation**

```bash
git add linear_algebra/registry.py linear_algebra/validation.py tests/test_linear_algebra_capability_coverage.py
git commit -m "test: enforce linear algebra capability operations"
```

<!-- openspec-task: 7.4 -->
### Task 7: Align Palette and Scene Role Vocabularies

**Files:**
- Modify: `linear_algebra/visualizations/palette.py`
- Modify: `linear_algebra/visualizations/builders/primitives.py`
- Modify: `services/scene_commands.py`
- Test: `tests/test_linear_algebra_role_contract.py`

**Interfaces:**
- Consumes: semantic teaching roles and the scene service's `primary|construction|result` roles.
- Produces: explicit `scene_role_for(teaching_role)` and complete role validation.

- [ ] **Step 1: Write all-topic role compatibility tests**

```python
def test_every_teaching_role_maps_to_a_valid_scene_role() -> None:
    for role in TEACHING_PALETTE:
        assert scene_role_for(role) in {"primary", "construction", "result"}


def test_all_compiled_plans_have_known_roles() -> None:
    for bundle in all_bundles():
        for operation in bundle.compiled.plan.operations:
            if "role" in operation:
                assert operation["role"] in {"primary", "construction", "result"}
```

- [ ] **Step 2: Run role tests and verify mismatches**

Run: `pytest tests/test_linear_algebra_role_contract.py -q`

Expected: FAIL for any teaching role that lacks an explicit scene-role mapping.

- [ ] **Step 3: Implement a complete immutable role map**

```python
TEACHING_TO_SCENE_ROLE = MappingProxyType({
    "vector_a": "primary",
    "vector_b": "construction",
    "basis_e1": "primary",
    "basis_e2": "construction",
    "transformed_a": "result",
    "transformed_b": "result",
    "area": "result",
    "projection": "result",
    "residual": "construction",
    "neutral": "construction",
})


def scene_role_for(teaching_role: str) -> str:
    return TEACHING_TO_SCENE_ROLE.get(teaching_role, "construction")
```

Keep `SceneCommandService`'s public three-role protocol unchanged unless a rendered distinction cannot be carried by color/evidence metadata.

- [ ] **Step 4: Run role, palette, and scene-command tests**

Run: `pytest tests/test_linear_algebra_role_contract.py tests/test_linear_algebra_teaching_palette.py tests/test_scene_commands.py -q`

Expected: PASS for all 54 compiled plans.

- [ ] **Step 5: Commit role alignment**

```bash
git add linear_algebra/visualizations/palette.py linear_algebra/visualizations/builders/primitives.py services/scene_commands.py tests/test_linear_algebra_role_contract.py
git commit -m "feat: align teaching and scene roles"
```

<!-- openspec-task: 7.5 -->
### Task 8: Add Full Unit, Integration, and Web Regression Coverage

**Files:**
- Create: `tests/test_linear_algebra_teaching_e2e.py`
- Modify: `tests/test_linear_algebra_loading.py`
- Modify: `tests/test_agent_bridge.py`
- Modify: `ui/agent_web/src/components/MathCaseView.test.tsx`
- Modify: `ui/agent_web/src/state/reducer.test.ts`

**Interfaces:**
- Consumes: complete published bundle pipeline.
- Produces: end-to-end tests for restart, stale source, atomic selection, storyboard, role continuity, and legacy reads.

- [ ] **Step 1: Write an end-to-end happy-path test**

```python
def test_tree_topic_resolves_compiles_executes_and_projects_one_case(tmp_path) -> None:
    registry = bundled_registry()
    bundle = registry.get_bundle("ch02.matrix.composition")
    prepared = prepare_topic_selection(registry, bundle.topic.id)
    host = RecordingSceneHost()
    SceneCommandService(host).execute(prepared.plan)
    assert prepared.case_payload["case_id"] == bundle.topic.id
    assert prepared.case_payload["artifact_revision"] == bundle.artifact.revision
    assert any(op["op"] == "geometry.staged_transform" for op in prepared.plan.operations)
```

- [ ] **Step 2: Add failure matrix tests**

Parameterize source stale, wrong topic ID, wrong digest, missing relation, invalid plan, scene execution failure, and case projection failure. Assert no partial scene/case commit for every case.

```python
@pytest.mark.parametrize("failure", ["topic", "digest", "relation", "plan", "execute", "projection"])
def test_topic_load_failure_is_atomic(failure: str) -> None:
    window = window_with_injected_failure(failure)
    before = window.observable_teaching_state()
    window._load_linear_algebra_topic("ch02.matrix.composition")
    assert window.observable_teaching_state() == before
```

- [ ] **Step 3: Run the new integration tests and inspect failures**

Run: `pytest tests/test_linear_algebra_teaching_e2e.py tests/test_linear_algebra_loading.py tests/test_agent_bridge.py -q`

Expected: PASS after Tasks 1-7; any failure must identify an actual uncovered integration gap.

- [ ] **Step 4: Run the full Web test suite**

Run: `pnpm --dir ui/agent_web test`

Expected: PASS with case navigation isolated from conversation state.

- [ ] **Step 5: Run the complete Python test suite**

Run: `pytest -q`

Expected: PASS with no legacy curriculum regression.

- [ ] **Step 6: Commit regression coverage**

```bash
git add tests ui/agent_web/src ui/agent_web/dist
git commit -m "test: cover teaching artifact workflow end to end"
```

<!-- openspec-task: 7.6 -->
### Task 9: Produce the Automated Verification Record

**Files:**
- Create: `scripts/write_linear_algebra_verification.py`
- Create: `openspec/changes/enrich-linear-algebra-teaching-depth/verification/automated-validation.md`
- Create: `openspec/changes/enrich-linear-algebra-teaching-depth/verification/topic-digests.json`
- Test: `tests/test_linear_algebra_verification_writer.py`

**Interfaces:**
- Consumes: final validator, Python/Web test and build commands, and 54 bundle digests.
- Produces: `VerificationCheck`, `run_verification(command_runner, output_dir)`, a CLI, and reproducible automated evidence containing observed exit codes and output summaries.

- [ ] **Step 1: Write failing verification-writer tests**

```python
def test_writer_stops_on_failed_check_and_does_not_claim_success(tmp_path) -> None:
    runner = fake_runner({"python-validation": completed(1, "invalid topic ch03.inverse")})
    with pytest.raises(VerificationFailed, match="python-validation"):
        run_verification(runner, tmp_path)
    assert not (tmp_path / "automated-validation.md").exists()


def test_writer_records_exact_success_output_and_sorted_digests(tmp_path) -> None:
    run_verification(successful_fake_runner(), tmp_path)
    report = (tmp_path / "automated-validation.md").read_text(encoding="utf-8")
    assert "54 topics validated: source=54 content=54 semantics=54 plans=54" in report
    assert "exit code: 0" in report
    digests = json.loads((tmp_path / "topic-digests.json").read_text(encoding="utf-8"))
    assert [item["topic_id"] for item in digests] == sorted(item["topic_id"] for item in digests)
```

- [ ] **Step 2: Run the writer test and verify the script is missing**

Run: `pytest tests/test_linear_algebra_verification_writer.py -q`

Expected: FAIL because the verification writer is missing.

- [ ] **Step 3: Implement fail-closed command capture and report writing**

```python
CHECKS = (
    VerificationCheck("python-validation", (sys.executable, "-m", "linear_algebra.validation")),
    VerificationCheck("python-tests", (sys.executable, "-m", "pytest", "-q")),
    VerificationCheck("web-tests", (resolve_pnpm(), "--dir", "ui/agent_web", "test")),
    VerificationCheck("web-build", (resolve_pnpm(), "--dir", "ui/agent_web", "build")),
)


def run_verification(command_runner, output_dir: Path) -> None:
    results = [command_runner(check) for check in CHECKS]
    failed = next((result for result in results if result.exit_code != 0), None)
    if failed is not None:
        raise VerificationFailed(failed.name, failed.exit_code, failed.output)
    digests = compile_all_topic_digests()
    if len(digests) != 54:
        raise VerificationFailed("topic-digests", 1, f"expected 54, got {len(digests)}")
    write_digest_json(output_dir / "topic-digests.json", digests)
    write_automated_report(output_dir / "automated-validation.md", results, digests)
```

Capture stdout and stderr without a shell, retain each exact command and exit code, and write files only after every check succeeds. Redact environment variables and provider credentials. Add a `walkthrough-index` subcommand that reads the digest file and creates seven focus-topic rows with status `not-checked` for Task 7.7.

- [ ] **Step 4: Run the complete verification workflow**

Run: `python scripts/write_linear_algebra_verification.py automated --output-dir openspec/changes/enrich-linear-algebra-teaching-depth/verification`

Expected: validation reports `54 topics validated: source=54 content=54 semantics=54 plans=54`; all Python tests and Web tests pass; the Web production build succeeds; both evidence files are written atomically.

- [ ] **Step 5: Inspect evidence completeness**

Run: `pytest tests/test_linear_algebra_verification_writer.py -q`

Run: `python -m linear_algebra.teaching.compile_resources --verify --write-digests openspec/changes/enrich-linear-algebra-teaching-depth/verification/topic-digests.check.json`

Expected: writer tests PASS; the check file is byte-identical to `topic-digests.json`. Delete only `topic-digests.check.json` after this equality check.

- [ ] **Step 6: Commit automated evidence**

```bash
git add scripts/write_linear_algebra_verification.py tests/test_linear_algebra_verification_writer.py openspec/changes/enrich-linear-algebra-teaching-depth/verification ui/agent_web/dist
git commit -m "docs: record teaching artifact verification"
```

<!-- openspec-task: 7.7 -->
### Task 10: Perform the Manual Chapter Walkthrough

**Files:**
- Create: `openspec/changes/enrich-linear-algebra-teaching-depth/verification/manual-walkthrough.md`
- Create: `openspec/changes/enrich-linear-algebra-teaching-depth/verification/screenshots/*.png`

**Interfaces:**
- Consumes: packaged application and the final topic digest file.
- Produces: chapter-by-chapter visual evidence for explanation depth, claim linkage, storyboard stages, and rollback behavior.

- [ ] **Step 1: Start the application and open the linear algebra tree**

Run: `python main.py`

Expected: application opens, the linear algebra catalog shows three chapters and 54 topics, and no topic loads from a branch click.

- [ ] **Step 2: Capture the seven focus-topic workflows**

Open and capture at least these topics: vector projection, cross product, transformed grid, `AB != BA`, null space, `det(AB)`, and inverse undo. For each topic inspect definition, derivation, numeric example, misconception, claim highlight, stage controls, and the corresponding visible mathematical relationship.

Expected screenshots:

```text
01-projection-residual.png
02-cross-product-orientation.png
03-transformed-grid.png
04-composition-ab-ba.png
05-null-space-collapse.png
06-determinant-stages.png
07-inverse-undo.png
```

- [ ] **Step 3: Verify narrow and normal reader widths**

At the sidebar minimum and default widths, check that stage labels, formulas, claims, and buttons remain readable without overlap or horizontal page scrolling. Record each checked viewport width in `manual-walkthrough.md`.

- [ ] **Step 4: Verify failure rollback**

Using a test fixture or development-only injected invalid bundle, select a topic with a missing required relation. Confirm that the previous scene and previous explanation remain visible and the status identifies topic ID, revision, and failing phase.

- [ ] **Step 5: Create and complete the walkthrough record with exact digests**

Run: `python scripts/write_linear_algebra_verification.py walkthrough-index --digests openspec/changes/enrich-linear-algebra-teaching-depth/verification/topic-digests.json --output openspec/changes/enrich-linear-algebra-teaching-depth/verification/manual-walkthrough.md`

Expected: the report contains exactly seven sorted focus-topic rows. Each row already contains its actual topic ID, revision, source hash, artifact digest, compiler version, and plan digest, with explanation/visual/storyboard/result fields set to `not-checked`.

After inspecting each workflow, replace its four `not-checked` states with the observed result and link the corresponding screenshot. Add a separate rollback section with the injected failure, retained topic revision, retained plan digest, failing phase, and status text.

Run: `rg -n 'not-checked' openspec/changes/enrich-linear-algebra-teaching-depth/verification/manual-walkthrough.md`

Expected: exit code 1 with no matches before the report is committed.

- [ ] **Step 6: Re-run validation after the walkthrough**

Run: `python -m linear_algebra.validation`

Expected: 54 topics still validate after all UI checks.

- [ ] **Step 7: Commit manual evidence**

```bash
git add openspec/changes/enrich-linear-algebra-teaching-depth/verification
git commit -m "docs: record teaching experience walkthrough"
```
