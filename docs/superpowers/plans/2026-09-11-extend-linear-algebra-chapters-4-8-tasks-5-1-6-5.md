# 线性代数第 4–8 章扩展（运行时、UI 与交付）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `openspec-executing-plans` to implement this plan task-by-task and sync completed work back to OpenSpec tasks. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把已发布的第 4–8 章主题原子接入 registry、Qt/Web 解释视图和 storyboard，并完成 93 个主题的校验、回归与交付证据。

**Architecture:** 运行时只消费完整 `CurriculumBundle` 和 published snapshot；UI 不解析命令 JSON，场景和解释通过同一事务提交。验证器从来源、artifact、contract、plan 到 renderer 建立可追溯覆盖，并以章节截图和 digest 报告作为交付证据。

**Tech Stack:** Python 3.11、PySide6、React/TypeScript/Vite、pytest、Vitest、OpenSpec CLI、现有 pane manager 和 teaching case bridge。

**Spec:** `docs/superpowers/specs/2026-09-11-linear-algebra-chapters-4-8-design.md`、`openspec/changes/extend-linear-algebra-chapters-4-8/`。

## Global Constraints

- 本计划依赖前三份计划已经发布 39 个主题和完整 renderer/replay 能力。
- UI 只能通过 `topic_id` 和 registry 加载主题；禁止按标题或 capability 构造场景。
- 章/节节点不触发加载；叶子加载必须同时提交解释和场景，失败时二者都保持不变。
- 不创建第二个线性代数工具栏，不改变当前左上角工具栏及前三章行为。
- Web payload 展示数学语义和来源，不暴露 CommandPlan 操作或内部 renderer 字段。
- 每个任务使用 TDD 和隔离提交，不加入工作区无关修改。

---

<!-- openspec-task: 5.1 -->
### Task 1: 扩展 registry 和原子主题加载事务

**Files:**
- Modify: `linear_algebra/registry.py`
- Modify: `linear_algebra/teaching/load_states.py`
- Modify: `ui/designer_window.py`
- Test: `tests/test_linear_algebra_registry_chapters_4_8.py`
- Test: `tests/test_teaching_case_panes.py`

**Interfaces:**
- `CurriculumRegistry.resolve_bundle(topic_id, ...)` returns only a matched topic/artifact/contract/recipe/compiled/snapshot set.
- Produces `commit_curriculum_bundle(bundle, *, pane_id) -> LoadTransaction` that stages explanation and scene before one host transaction.
- On rejection, `LoadDiagnostic` includes code/topic/phase/field and the previous canvas/explanation fingerprints remain unchanged.

- [ ] **Step 1: Add complete-bundle and rollback tests**

```python
def test_extended_topic_bundle_is_one_to_one():
    bundle = catalog_registry().resolve_bundle("ch08.principal-axis", artifact_store=bundled_teaching_store())
    assert bundle.topic.id == bundle.artifact.topic_id == bundle.contract.topic_id == bundle.compiled.topic_id
    assert bundle.snapshot.plan_digest == bundle.compiled.plan_digest

def test_failed_extended_topic_keeps_previous_scene_and_explanation(window):
    before = window.teaching_fingerprints()
    window.load_topic("ch08.principal-axis", inject_failure="plan_invalid")
    assert window.teaching_fingerprints() == before
```

- [ ] **Step 2: Run registry and pane tests before transaction integration**

Run: `pytest tests/test_linear_algebra_registry_chapters_4_8.py tests/test_teaching_case_panes.py -q`

Expected: FAIL for incomplete bundle state or partial UI mutation.

- [ ] **Step 3: Stage bundle validation and one host transaction**

Advance through source/artifact/contract/compiled/plan/staged phases, verify renderer capability and bind pane once. Stage the explanation payload without displaying it; execute the scene; publish both only after commit. Roll back both surfaces on validation or host failure.

- [ ] **Step 4: Run registry, store and pane regressions**

Run: `pytest tests/test_linear_algebra_registry_chapters_4_8.py tests/test_linear_algebra_registry.py tests/test_teaching_case_panes.py tests/test_agent_workspace_restore.py -q`

Expected: PASS with stable previous state for every injected phase failure.

- [ ] **Step 5: Commit atomic extended topic loading**

```bash
git add linear_algebra/registry.py linear_algebra/teaching/load_states.py ui/designer_window.py tests/test_linear_algebra_registry_chapters_4_8.py tests/test_teaching_case_panes.py
git commit -m "feat: load chapter 4-8 topics atomically"
```

<!-- openspec-task: 5.2 -->
### Task 2: 扩展 Qt 解释视图和 Web math_case payload

**Files:**
- Modify: `ui/linear_algebra_content_view.py`
- Modify: `ui/agent_sidebar_web.py`
- Modify: `ui/agent_web/src/components/MathCaseView.tsx`
- Modify: `ui/agent_web/src/components/MathCaseView.structured.test.tsx`
- Test: `tests/test_linear_algebra_dialog.py`
- Test: `tests/test_agent_bridge.py`

**Interfaces:**
- Qt/Web payload exposes source path/hash, claims, formula, derivation, numeric example, symbol roles, geometric meaning, misconception, read guide and analogy boundary.
- Payload never includes `operations`, scene op names, renderer objects or unrestricted expressions.
- Both clients render the same `topic_id`, revision and source diagnostic.

- [ ] **Step 1: Add structured payload and secrecy tests**

```python
def test_math_case_payload_contains_semantics_but_not_scene_ops():
    payload = bridge_payload_for("ch08.principal-axis")
    assert payload["source"]["heading_path"]
    assert payload["explanation"]["analogy_boundary"]
    assert "operations" not in json.dumps(payload)
    assert "geometry.quadratic_level_set" not in json.dumps(payload)
```

- [ ] **Step 2: Run Python and Web component tests before payload extension**

Run: `pytest tests/test_linear_algebra_dialog.py tests/test_agent_bridge.py -q` and `npm --prefix ui/agent_web test -- --run MathCaseView.structured.test.tsx`

Expected: FAIL for missing chapter/source/claim/read-guide fields.

- [ ] **Step 3: Extend the bridge schema and render sections**

Build the payload from `CurriculumBundle`/artifact fields, not command plans. Render source, formula, steps, example, meaning, misconception, read guide and analogy boundary with existing Markdown/KaTeX conventions; show a concise stale-source diagnostic.

- [ ] **Step 4: Run Qt, bridge and Web tests**

Run: `pytest tests/test_linear_algebra_dialog.py tests/test_agent_bridge.py -q` and `npm --prefix ui/agent_web test -- --run MathCaseView.structured.test.tsx`

Expected: PASS with no internal operation data in serialized payloads.

- [ ] **Step 5: Commit extended explanation surfaces**

```bash
git add ui/linear_algebra_content_view.py ui/agent_sidebar_web.py ui/agent_web/src/components/MathCaseView.tsx ui/agent_web/src/components/MathCaseView.structured.test.tsx tests/test_linear_algebra_dialog.py tests/test_agent_bridge.py
git commit -m "feat: show chapter 4-8 teaching explanations"
```

<!-- openspec-task: 5.3 -->
### Task 3: 接入高级 storyboard 导航

**Files:**
- Modify: `ui/linear_algebra_content_view.py`
- Modify: `ui/teaching_case_panes.py`
- Modify: `ui/designer_window.py`
- Test: `tests/test_linear_algebra_extended_storyboard.py`
- Test: `tests/test_teaching_case_panes.py`

**Interfaces:**
- Storyboard navigation consumes `CompiledStoryboardStage` IDs and `storyboard_visibility(compiled, stage_id)`.
- Switching stages updates visible aliases in the existing teaching pane; it does not call an Agent/provider, create a new pane/tab or mutate artifact/session state.
- Matrix tableau, mapping bundle and quadratic stages reuse one navigation component.

- [ ] **Step 1: Add no-regeneration and stable-pane tests**

```python
def test_switching_extended_storyboard_only_changes_visibility(window, provider_spy):
    pane_id = window.load_topic("ch08.principal-axis")
    session_before = window.agent_session_snapshot()
    window.select_storyboard_stage("standard")
    assert window.active_teaching_pane_id == pane_id
    assert provider_spy.calls == []
    assert window.agent_session_snapshot() == session_before
```

- [ ] **Step 2: Run storyboard/pane tests before advanced stage wiring**

Run: `pytest tests/test_linear_algebra_extended_storyboard.py tests/test_teaching_case_panes.py -q`

Expected: FAIL because advanced stages are not navigable through the existing visibility API.

- [ ] **Step 3: Wire stage metadata to one visibility controller**

Use compiled `visible_aliases` and stable pane ID. Update captions/highlights from stage metadata, retain the same scene objects, and reject unknown stage IDs without changing current visibility. Do not add topic-specific UI branches.

- [ ] **Step 4: Run storyboard, workspace restore and bridge tests**

Run: `pytest tests/test_linear_algebra_extended_storyboard.py tests/test_teaching_case_panes.py tests/test_agent_workspace_restore.py tests/test_agent_bridge.py -q`

Expected: PASS for tableau, domain/image, principal-axis and quadratic stages.

- [ ] **Step 5: Commit storyboard navigation**

```bash
git add ui/linear_algebra_content_view.py ui/teaching_case_panes.py ui/designer_window.py tests/test_linear_algebra_extended_storyboard.py tests/test_teaching_case_panes.py
git commit -m "feat: navigate advanced linear algebra storyboards"
```

<!-- openspec-task: 5.4 -->
### Task 4: 保持单一工具栏和前三章行为

**Files:**
- Modify: `ui/designer_window.py`
- Modify: `ui/two_d_tools.py`
- Test: `tests/test_linear_algebra_loading.py`
- Test: `tests/test_designer_window_toolbar.py`
- Create: `tests/test_linear_algebra_chapters_1_3_regression.py`

**Interfaces:**
- The existing top-left `TwoDGeometryToolbar` is created once and remains visible independent of selected lecture chapter.
- Loading chapter 4–8 changes the teaching bundle/pane only; toolbar identity, position, actions and shortcuts do not change.
- Existing chapter 1–3 topic plan digests and load behavior remain recorded in a regression fixture.

- [ ] **Step 1: Add toolbar identity and old-topic digest tests**

```python
def test_loading_new_chapters_does_not_create_second_toolbar(window):
    toolbar = window.two_d_geometry_toolbar
    for topic_id in ("ch04.space.closure", "ch08.principal-axis"):
        window.load_topic(topic_id)
        assert window.two_d_geometry_toolbar is toolbar
        assert len(window.findChildren(TwoDGeometryToolbar)) == 1
```

- [ ] **Step 2: Run toolbar and chapter regression tests**

Run: `pytest tests/test_linear_algebra_loading.py tests/test_designer_window_toolbar.py tests/test_linear_algebra_chapters_1_3_regression.py -q`

Expected: FAIL if topic loading hides, moves or duplicates the toolbar or changes recorded digests.

- [ ] **Step 3: Remove chapter-dependent toolbar branching**

Create the toolbar only during window initialization, place it at the existing top-left anchor, and route actions through the focused pane. Ensure lecture dialog open/close and topic selection never instantiate or relocate it. Preserve existing shortcuts and theme updates.

- [ ] **Step 4: Run toolbar, window and teaching regressions**

Run: `pytest tests/test_linear_algebra_loading.py tests/test_designer_window_toolbar.py tests/test_linear_algebra_chapters_1_3_regression.py tests/test_teaching_case_panes.py -q`

Expected: PASS with one toolbar and unchanged first-three-chapter behavior.

- [ ] **Step 5: Commit toolbar compatibility**

```bash
git add ui/designer_window.py ui/two_d_tools.py tests/test_linear_algebra_loading.py tests/test_designer_window_toolbar.py tests/test_linear_algebra_chapters_1_3_regression.py
git commit -m "test: preserve linear algebra toolbar and legacy topics"
```

<!-- openspec-task: 6.1 -->
### Task 5: 扩展 93 主题全量验证

**Files:**
- Modify: `linear_algebra/validation.py`
- Test: `tests/test_linear_algebra_validation_chapters_4_8.py`

**Interfaces:**
- Produces `validate_all_topics(...) -> ValidationReport` with chapter counts, source, artifact, contract, published status and plan digest sections.
- Validation requires 93 unique topic IDs and exact counts 24/15/15/16/8/3/6/6.
- Report issues include chapter/topic/category/path and stable error code.

- [ ] **Step 1: Add full count and stale-resource tests**

```python
def test_full_validation_accepts_exact_93_topic_distribution():
    report = validate_all_topics(repository_root())
    assert report.chapter_counts == {1: 24, 2: 15, 3: 15, 4: 16, 5: 8, 6: 3, 7: 6, 8: 6}
    assert report.issues == ()
```

- [ ] **Step 2: Run validation tests against the current three-chapter assumptions**

Run: `pytest tests/test_linear_algebra_validation_chapters_4_8.py -q`

Expected: FAIL on topic totals or missing chapter resource checks.

- [ ] **Step 3: Aggregate validation without swallowing individual failures**

Validate catalog, source, reviewed/published artifact, contract, compiled snapshot and renderer operation parity for every topic. Sort issues deterministically and make the CLI nonzero on any issue. Preserve existing diagnostic detail.

- [ ] **Step 4: Run validation and CLI**

Run: `pytest tests/test_linear_algebra_validation_chapters_4_8.py tests/test_lecture_source_validation.py tests/test_linear_algebra_content_validation.py -q` and `python -m linear_algebra.validation`

Expected: PASS and a 93-topic summary.

- [ ] **Step 5: Commit full-course validation**

```bash
git add linear_algebra/validation.py tests/test_linear_algebra_validation_chapters_4_8.py
git commit -m "feat: validate all 93 linear algebra topics"
```

<!-- openspec-task: 6.2 -->
### Task 6: 增加语义、解释与实际操作一致性校验

**Files:**
- Modify: `linear_algebra/validation.py`
- Modify: `linear_algebra/visualizations/evidence.py`
- Test: `tests/test_linear_algebra_extended_evidence.py`

**Interfaces:**
- Produces evidence checks for `declared capability → actual plan op`, `explanation variable → visual entity`, and `relation → claim/contract`.
- `build_evidence_ledger()` exposes topic/claim/entity/relation/alias/operation links and reports unbound/ambiguous evidence.
- Every new capability-map entry has at least one published topic and one negative fixture.

- [ ] **Step 1: Add missing-operation and unbound-variable tests**

```python
def test_declared_quadratic_capability_requires_actual_level_set_op():
    issues = validate_extended_evidence(bundle_without_quadratic_op())
    assert any(issue.code == "missing_actual_operation" and issue.topic_id == "ch08.principal-axis" for issue in issues)

def test_formula_variable_requires_visual_or_explanation_binding():
    issues = validate_extended_evidence(bundle_with_unbound_lambda())
    assert any(issue.code == "unbound_formula_variable" for issue in issues)
```

- [ ] **Step 2: Run evidence tests before the extended ledger exists**

Run: `pytest tests/test_linear_algebra_extended_evidence.py -q`

Expected: FAIL because chapter 4–8 operation and variable bindings are not checked.

- [ ] **Step 3: Build deterministic cross-layer evidence joins**

Join by stable IDs only. Map semantic primitives through `capability_map.py`, aliases through `CompiledVisualization.aliases`, claims through artifact refs and operations through validated plan names. Report the first missing edge without inventing evidence.

- [ ] **Step 4: Run evidence and validation regressions**

Run: `pytest tests/test_linear_algebra_extended_evidence.py tests/test_linear_algebra_source_evidence.py tests/test_linear_algebra_visual_contracts.py tests/test_linear_algebra_validation_chapters_4_8.py -q`

Expected: PASS for all published topics and expected failure codes for negative fixtures.

- [ ] **Step 5: Commit evidence consistency validation**

```bash
git add linear_algebra/validation.py linear_algebra/visualizations/evidence.py tests/test_linear_algebra_extended_evidence.py
git commit -m "feat: validate chapter 4-8 visual evidence links"
```

<!-- openspec-task: 6.3 -->
### Task 7: 建立章节级单元、集成、Qt 和 Web 回归矩阵

**Files:**
- Create: `tests/test_linear_algebra_chapters_4_8_integration.py`
- Create: `tests/test_linear_algebra_chapters_4_8_qt.py`
- Create: `ui/agent_web/src/components/MathCaseView.chapters-4-8.test.tsx`
- Create: `tests/snapshots/linear_algebra_chapters_4_8_plans.json`

**Interfaces:**
- Integration matrix enumerates all 39 topic IDs and records expected scene, stage IDs, command operations and plan digest.
- Qt matrix exercises search/select/load/reject/stage switching for one representative topic per chapter.
- Web tests render source, formula, claim, read guide and analogy boundary for structured payloads.

- [ ] **Step 1: Add the parameterized end-to-end matrices**

```python
@pytest.mark.parametrize("topic_id", new_topic_ids())
def test_every_new_topic_compiles_and_replays(topic_id, recording_host):
    bundle = resolve_published(topic_id)
    validation = SceneCommandService(recording_host).execute(bundle.compiled.plan)
    assert validation.valid
    assert bundle.snapshot.plan_digest == bundle.compiled.plan_digest
```

- [ ] **Step 2: Run Python and Web matrices and capture failures**

Run: `pytest tests/test_linear_algebra_chapters_4_8_integration.py tests/test_linear_algebra_chapters_4_8_qt.py -q` and `npm --prefix ui/agent_web test -- --run MathCaseView.chapters-4-8.test.tsx`

Expected: FAIL for any missing topic operation, UI field or stage navigation path.

- [ ] **Step 3: Fix only matrix-discovered integration gaps and write golden snapshot**

Record canonical operation names, stage IDs and digests after all validation passes. Do not normalize away semantic differences or update expected digests to conceal failures.

- [ ] **Step 4: Re-run the complete chapter 4–8 matrix**

Run: `pytest tests/test_linear_algebra_chapters_4_8_integration.py tests/test_linear_algebra_chapters_4_8_qt.py -q` and `npm --prefix ui/agent_web test -- --run MathCaseView.chapters-4-8.test.tsx`

Expected: PASS for 39 topics and five UI representative cases.

- [ ] **Step 5: Commit integration and golden coverage**

```bash
git add tests/test_linear_algebra_chapters_4_8_integration.py tests/test_linear_algebra_chapters_4_8_qt.py ui/agent_web/src/components/MathCaseView.chapters-4-8.test.tsx tests/snapshots/linear_algebra_chapters_4_8_plans.json
git commit -m "test: cover chapters 4-8 end to end"
```

<!-- openspec-task: 6.4 -->
### Task 8: 运行全量校验并生成覆盖报告

**Files:**
- Create: `docs/verification/linear-algebra-chapters-4-8-report.md`
- Modify: `openspec/changes/extend-linear-algebra-chapters-4-8/tasks.md`（仅由执行器同步完成勾选）

**Interfaces:**
- Report records commands, exit status, test totals, chapter counts, capability-to-operation coverage, source/artifact/contract/compiler digests and known skipped tests.
- This task does not change implementation to make failing checks disappear; failures return to the owning task.

- [ ] **Step 1: Run OpenSpec and lecture validators**

Run: `openspec validate extend-linear-algebra-chapters-4-8 --strict`, `openspec validate --all`, and `python -m linear_algebra.validation`

Expected: all commands exit 0; lecture summary reports 93 topics.

- [ ] **Step 2: Run the complete Python suite**

Run: `pytest -q`

Expected: exit 0; record exact passed/skipped totals in the report.

- [ ] **Step 3: Run the Web tests and production build**

Run: `npm --prefix ui/agent_web test -- --run` and `npm --prefix ui/agent_web run build`

Expected: both exit 0; record test total and generated build status.

- [ ] **Step 4: Generate deterministic coverage and digest sections**

Run: `python scripts/validate_linear_algebra_drawing_catalog.py` and the validation report command added in Task 5. Copy command output summaries into the report, including exact 24/15/15/16/8/3/6/6 counts and zero missing capability-operation edges.

- [ ] **Step 5: Commit the verification report**

```bash
git add docs/verification/linear-algebra-chapters-4-8-report.md
git commit -m "docs: verify linear algebra chapters 4-8"
```

<!-- openspec-task: 6.5 -->
### Task 9: 完成逐章手动走查和截图证据

**Files:**
- Create: `docs/verification/linear-algebra-chapters-4-8-walkthrough.md`
- Create: `docs/verification/screenshots/linear-algebra-ch04.png`
- Create: `docs/verification/screenshots/linear-algebra-ch05.png`
- Create: `docs/verification/screenshots/linear-algebra-ch06.png`
- Create: `docs/verification/screenshots/linear-algebra-ch07.png`
- Create: `docs/verification/screenshots/linear-algebra-ch08.png`

**Interfaces:**
- Walkthrough records topic ID, source hash, artifact revision, compiler version, plan digest, selected stage, expected geometry and observed result for one representative topic per chapter.
- Screenshots are evidence only; mathematical correctness remains established by automated evidence/tolerance tests.

- [ ] **Step 1: Launch the application and verify tree controls**

Run: `python main.py`

Expected: one top-left toolbar; clicking “线性代数” shows eight chapters, search, expand-all and collapse controls; branch clicks do not alter the current scene.

- [ ] **Step 2: Walk chapter 4 and 5 representatives**

Select `ch04.subspace.col-null` and `ch05.consistency.geometry`; verify domain/kernel/image evidence and unique/none/infinite stages. Save the first two screenshots and record the bundle versions/digests.

- [ ] **Step 3: Walk chapter 6 and 7 representatives**

Select `ch06.similarity-transform` and `ch07.diagonalization`; verify change-basis stages, stable endpoint and eigen-direction distinctions. Save screenshots and record versions/digests.

- [ ] **Step 4: Walk chapter 8 and failure rollback**

Select `ch08.principal-axis`; verify original/axes/standard stages. Inject or select the documented stale fixture and confirm the previous scene/explanation remain unchanged. Save the chapter 8 screenshot and record the diagnostic code.

- [ ] **Step 5: Commit walkthrough evidence**

```bash
git add docs/verification/linear-algebra-chapters-4-8-walkthrough.md docs/verification/screenshots/linear-algebra-ch04.png docs/verification/screenshots/linear-algebra-ch05.png docs/verification/screenshots/linear-algebra-ch06.png docs/verification/screenshots/linear-algebra-ch07.png docs/verification/screenshots/linear-algebra-ch08.png
git commit -m "docs: add chapter 4-8 walkthrough evidence"
```
