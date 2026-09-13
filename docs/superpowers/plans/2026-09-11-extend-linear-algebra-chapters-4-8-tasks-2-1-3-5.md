# 线性代数第 4–8 章扩展（教学产物与基础场景族）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `openspec-executing-plans` to implement this plan task-by-task and sync completed work back to OpenSpec tasks. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 扩展教学产物和发布模型，并实现第 4–8 章所需的语义词汇、3D 子空间、约束交集、矩阵消元、最小二乘和双坐标基础能力。

**Architecture:** 教学解释和视觉语义先成为受 schema/contract 校验的独立 artifact，再由场景族 compiler 生成受控 CommandPlan。新增能力先在纯 Python validator/compiler 中通过黄金 fixture，再接 SceneCommandService 和 renderer。

**Tech Stack:** Python 3.11、JSON Schema、NumPy、pytest、现有 TeachingArtifact/VisualContract/VisualSemanticsCompiler/CommandPlan。

**Spec:** `docs/superpowers/specs/2026-09-11-linear-algebra-chapters-4-8-design.md`、`openspec/changes/extend-linear-algebra-chapters-4-8/`。

## Global Constraints

- 本计划依赖计划 1 已完成的 capability map、scene-family fixtures、render limits、来源解析和 93-topic manifest。
- 章节资源按 `chapter_04`–`chapter_08` 分片；公共模型只承载共享字段和校验。
- artifact/contract/compiled snapshot 必须使用相同 `topic_id`、source hash 和 revision。
- family compiler 不导入 Qt/PyVista，不执行任意表达式，不用默认向量替代缺失关系。
- 所有数值结果必须可由 fixture 复算；颜色和截图不能作为唯一数学证据。
- 每个任务使用 TDD 和隔离提交，不加入工作区无关修改。

---

<!-- openspec-task: 2.1 -->
### Task 1: 扩展教学 profile、source context 和 artifact schema

**Files:**
- Modify: `linear_algebra/teaching/profiles.py`
- Modify: `linear_algebra/teaching/source.py`
- Modify: `linear_algebra/teaching/artifact.schema.json`
- Modify: `linear_algebra/teaching/model.py`
- Modify: `linear_algebra/teaching/vocabulary.py`
- Test: `tests/test_linear_algebra_teaching_profiles.py`
- Test: `tests/test_linear_algebra_teaching_model.py`

**Interfaces:**
- `TeachingProfileRecord` continues to expose `requires_analogy_boundary` and accepts chapter 4–8 required sections.
- `VisualEntity.kind`/`VisualRelation.kind` accept only the new controlled vocabulary from the design.
- Artifact JSON round-trips `analogy_boundary`, claim refs, scene family, stages and source occurrence without losing fields.

- [x] **Step 1: Add failing schema and vocabulary cases**

```python
def test_chapter_eight_artifact_round_trips_quadratic_semantics():
    artifact = TeachingArtifact.from_dict(chapter_eight_payload())
    assert artifact.explanation.analogy_boundary
    assert {relation.kind for relation in artifact.visual_semantics.relations} >= {"has_principal_axis", "classifies_as"}
    assert TeachingArtifact.from_dict(artifact.to_dict()) == artifact
```

- [x] **Step 2: Run schema/model tests before extending the vocabulary**

Run: `pytest tests/test_linear_algebra_teaching_profiles.py tests/test_linear_algebra_teaching_model.py -q`

Expected: FAIL on unknown relation/entity kinds or missing profile rules.

- [x] **Step 3: Add exact fields and controlled vocabulary**

Register scene-family metadata and relations for span/containment/maps-to/collapse/affine translation/constraint state/row operation/coordinate equivalence/eigen binding/orthogonality/principal axis/classification. Preserve strict unknown-field rejection and chapter 1–3 payload compatibility.

- [x] **Step 4: Run schema, parser and legacy tests**

Run: `pytest tests/test_linear_algebra_teaching_profiles.py tests/test_linear_algebra_teaching_model.py tests/test_linear_algebra_explanation_parser.py tests/test_linear_algebra_teaching_legacy.py -q`

Expected: PASS with existing artifacts unchanged.

- [x] **Step 5: Commit the teaching schema extension**

```bash
git add linear_algebra/teaching/profiles.py linear_algebra/teaching/source.py linear_algebra/teaching/artifact.schema.json linear_algebra/teaching/model.py linear_algebra/teaching/vocabulary.py tests/test_linear_algebra_teaching_profiles.py tests/test_linear_algebra_teaching_model.py
git commit -m "feat: extend teaching artifact schema for chapters 4-8"
```

<!-- openspec-task: 2.2 -->
### Task 2: 增加第 4–8 章 explanation 模块

**Files:**
- Create: `linear_algebra/explanations/chapter_04.py`
- Create: `linear_algebra/explanations/chapter_05.py`
- Create: `linear_algebra/explanations/chapter_06.py`
- Create: `linear_algebra/explanations/chapter_07.py`
- Create: `linear_algebra/explanations/chapter_08.py`
- Modify: `linear_algebra/explanations/__init__.py`
- Test: `tests/test_linear_algebra_explanations_chapters_4_8.py`

**Interfaces:**
- Each module exports `EXPLANATIONS: Mapping[str, ExplanationContent]` for its chapter.
- `explanation_for(topic_id)` resolves all 93 topics and rejects unknown IDs.
- Every new explanation contains title, summary, formula, derivation steps, numeric example where applicable, geometric meaning, misconception, conclusion, read guide and searchable text.

- [x] **Step 1: Add completeness and LaTeX tests**

```python
def test_new_chapter_explanations_cover_catalog_exactly():
    topic_ids = {item.id for item in topic_entries() if item.chapter_number >= 4}
    assert {explanation_for(topic_id).id.removeprefix("explain.") for topic_id in topic_ids} == topic_ids

def test_vector_and_matrix_latex_uses_bold_or_matrix_notation():
    for topic_id in new_topic_ids():
        explanation = explanation_for(topic_id)
        assert_latex_roles_are_unambiguous(explanation.formula)
```

- [x] **Step 2: Run explanation tests before modules exist**

Run: `pytest tests/test_linear_algebra_explanations_chapters_4_8.py -q`

Expected: FAIL because chapter 4–8 explanation IDs are unresolved.

- [x] **Step 3: Implement chapter-local explanation dictionaries**

Transcribe and expand only claims grounded in the lecture source. Keep equations and matrices in LaTeX, include a concrete finite example for geometry-heavy topics, and state `analogy_boundary` for general-dimensional claims. Do not embed command operations or renderer instructions.

- [x] **Step 4: Run explanation, depth and source evidence tests**

Run: `pytest tests/test_linear_algebra_explanations_chapters_4_8.py tests/test_linear_algebra_teaching_depth.py tests/test_linear_algebra_source_evidence.py -q`

Expected: PASS with one explanation per new topic and no orphan explanation.

- [x] **Step 5: Commit the explanation modules**

```bash
git add linear_algebra/explanations/chapter_04.py linear_algebra/explanations/chapter_05.py linear_algebra/explanations/chapter_06.py linear_algebra/explanations/chapter_07.py linear_algebra/explanations/chapter_08.py linear_algebra/explanations/__init__.py tests/test_linear_algebra_explanations_chapters_4_8.py
git commit -m "feat: add chapter 4-8 linear algebra explanations"
```

<!-- openspec-task: 2.3 -->
### Task 3: 扩展 artifact store 和章节发布索引

**Files:**
- Modify: `linear_algebra/teaching/store.py`
- Modify: `linear_algebra/visualizations/snapshots.py`
- Modify: `linear_algebra/teaching/data/index.json`
- Test: `tests/test_linear_algebra_teaching_store.py`
- Test: `tests/test_linear_algebra_teaching_stale.py`
- Test: `tests/test_linear_algebra_compiled_resources.py`

**Interfaces:**
- Produces chapter-index operations `publish_chapter(chapter: int, revisions: Mapping[str, int])` and `unpublish_chapter(chapter: int)` with atomic file replacement.
- `CompiledSnapshot` gains/retains contract digest and scene family metadata needed to detect stale compiled plans.
- `load_published(topic_id, current_context)` returns a diagnostic instead of a stale artifact when source hash differs.

- [x] **Step 1: Write atomic chapter publication tests**

```python
def test_failed_chapter_publish_leaves_previous_index_unchanged(tmp_path):
    store = TeachingArtifactStore(tmp_path)
    before = store.index_payload()
    with pytest.raises(ValueError):
        store.publish_chapter(4, {"ch04.unknown": 1})
    assert store.index_payload() == before
```

- [x] **Step 2: Run store and snapshot tests before API changes**

Run: `pytest tests/test_linear_algebra_teaching_store.py tests/test_linear_algebra_teaching_stale.py tests/test_linear_algebra_compiled_resources.py -q`

Expected: FAIL because chapter-level publish/unpublish and the new snapshot metadata are absent.

- [x] **Step 3: Implement staged index replacement and stale diagnostics**

Validate every chapter topic/revision/source/contract/snapshot before replacing an index. Write to a sibling temporary file and use atomic replace. On unpublish, remove only the requested chapter entries. Preserve existing chapter 1–3 index payload and lookup behavior.

- [x] **Step 4: Run store, publish and release isolation tests**

Run: `pytest tests/test_linear_algebra_teaching_store.py tests/test_linear_algebra_teaching_publish.py tests/test_linear_algebra_teaching_stale.py tests/test_linear_algebra_compiled_resources.py tests/test_linear_algebra_chapter_release_fixtures.py -q`

Expected: PASS and no partial index after any injected failure.

- [x] **Step 5: Commit atomic chapter publishing**

```bash
git add linear_algebra/teaching/store.py linear_algebra/visualizations/snapshots.py linear_algebra/teaching/data/index.json tests/test_linear_algebra_teaching_store.py tests/test_linear_algebra_teaching_stale.py tests/test_linear_algebra_compiled_resources.py
git commit -m "feat: publish teaching resources by chapter atomically"
```

<!-- openspec-task: 2.4 -->
### Task 4: 生成并审核 39 个 teaching artifact fixture

**Files:**
- Create: `linear_algebra/teaching/chapter_artifacts.py`
- Create: `linear_algebra/teaching/data/drafts/ch04/` through `ch08/`
- Create: `linear_algebra/teaching/data/revieweds/ch04/` through `ch08/`
- Test: `tests/test_linear_algebra_chapters_4_8_artifacts.py`

**Interfaces:**
- Produces `artifact_payload_for(topic_id: str) -> dict[str, object]` from chapter-local deterministic source/claim/semantic fixtures.
- Produces 39 reviewed artifacts whose claim refs, formula variables, entity refs, relation refs and stage refs are closed.
- Artifacts remain unpublished until their scene family and renderer operations pass later plan tasks.

- [x] **Step 1: Add exact coverage and reference-closure tests**

```python
def test_reviewed_artifacts_cover_all_new_topics():
    artifacts = load_reviewed_chapter_artifacts(range(4, 9))
    assert len(artifacts) == 39
    assert {artifact.topic_id for artifact in artifacts} == set(new_topic_ids())
    for artifact in artifacts:
        assert validate_claim_bindings(artifact) == ()
```

- [x] **Step 2: Run artifact tests before fixtures exist**

Run: `pytest tests/test_linear_algebra_chapters_4_8_artifacts.py -q`

Expected: FAIL because no chapter 4–8 reviewed resources exist.

- [x] **Step 3: Build deterministic artifacts from source anchors and explanations**

For every topic create claims, concrete entities/relations/stages, generation receipt and source hash. Use the scene-family fixture matrix for numeric examples. Run the existing review transition rather than marking malformed drafts as reviewed.

- [x] **Step 4: Run artifact schema, quality and source validation**

Run: `pytest tests/test_linear_algebra_chapters_4_8_artifacts.py tests/test_linear_algebra_teaching_quality.py tests/test_linear_algebra_content_validation.py -q`

Expected: PASS for all 39 artifacts, with no missing claim/entity/relation/stage reference.

- [x] **Step 5: Commit reviewed chapter artifacts**

```bash
git add linear_algebra/teaching/chapter_artifacts.py linear_algebra/teaching/data/drafts/ch04 linear_algebra/teaching/data/drafts/ch05 linear_algebra/teaching/data/drafts/ch06 linear_algebra/teaching/data/drafts/ch07 linear_algebra/teaching/data/drafts/ch08 linear_algebra/teaching/data/revieweds/ch04 linear_algebra/teaching/data/revieweds/ch05 linear_algebra/teaching/data/revieweds/ch06 linear_algebra/teaching/data/revieweds/ch07 linear_algebra/teaching/data/revieweds/ch08 tests/test_linear_algebra_chapters_4_8_artifacts.py
git commit -m "feat: add reviewed teaching artifacts for chapters 4-8"
```

<!-- openspec-task: 3.1 -->
### Task 5: 扩展视觉词汇、VisualContract 和 family 路由

**Files:**
- Modify: `linear_algebra/teaching/vocabulary.py`
- Modify: `linear_algebra/visualizations/contracts.py`
- Modify: `linear_algebra/visualizations/compiler.py`
- Create: `linear_algebra/visualizations/families/__init__.py`
- Test: `tests/test_linear_algebra_chapters_4_8_contracts.py`

**Interfaces:**
- `contract_for(topic_id)` returns explicit contracts for all 39 new topics.
- Produces `family_compiler_for(primitive: str) -> SceneFamilyCompiler`; unknown primitive raises `VisualCompileError(code="unsupported_scene_family")`.
- Contract validation checks scene-family primitive, required operations, roles, relations, stages and invariants before family compilation.

- [x] **Step 1: Add contract and unknown-family tests**

```python
def test_diagonalization_contract_requires_three_stage_relations():
    contract = contract_for("ch07.diagonalization")
    assert contract.minimum_stage_count == 3
    assert {"change_basis", "diagonal_scale", "change_basis_back"} <= set(contract.required_relations)

def test_unknown_family_fails_without_fallback():
    with pytest.raises(VisualCompileError, match="unsupported_scene_family"):
        family_compiler_for("draw_something")
```

- [x] **Step 2: Run contract tests against the current chapter 1–3 overrides**

Run: `pytest tests/test_linear_algebra_chapters_4_8_contracts.py -q`

Expected: FAIL because new contracts and family routing are missing.

- [x] **Step 3: Add explicit chapter contracts and compiler dispatch**

Keep default contracts only for existing topics; every new topic receives an explicit contract. Dispatch by semantic primitive from `capability_map.py`, never by title. Remove any extended-topic fallback that synthesizes a generic vector.

- [x] **Step 4: Run contract and compiler regressions**

Run: `pytest tests/test_linear_algebra_chapters_4_8_contracts.py tests/test_linear_algebra_visual_contracts.py tests/test_linear_algebra_visual_compiler.py -q`

Expected: PASS and unchanged behavior for current explicit contracts.

- [x] **Step 5: Commit visual contracts and family routing**

```bash
git add linear_algebra/teaching/vocabulary.py linear_algebra/visualizations/contracts.py linear_algebra/visualizations/compiler.py linear_algebra/visualizations/families/__init__.py tests/test_linear_algebra_chapters_4_8_contracts.py
git commit -m "feat: route chapter 4-8 visual scene families"
```

<!-- openspec-task: 3.2 -->
### Task 6: 实现 3D 子空间、仿射集和域/核/像布局

**Files:**
- Create: `linear_algebra/visualizations/families/subspace.py`
- Modify: `services/scene_commands.py`
- Modify: `rendering/geometry_3d_scene.py`
- Test: `tests/test_linear_algebra_subspace_family.py`
- Test: `tests/test_geometry_3d_scene.py`

**Interfaces:**
- Produces `SubspaceFamilyCompiler.validate/compile` for `geometry.subspace3d`, `geometry.affine_solution` and `geometry.mapping_bundle`.
- 3D subspace payload declares `origin`, `basis`, `dimension`, `affine_offset`, bounds and labels.
- Mapping bundle returns domain/kernel/image lane aliases and numeric `rank`, `nullity`, `domain_dimension` evidence.

- [x] **Step 1: Add rank-nullity, origin and affine tests**

```python
def test_mapping_bundle_emits_kernel_and_image_with_rank_nullity():
    result = compile_fixture("subspace_structure", "normal")
    assert {op["op"] for op in result.operations} >= {"geometry.mapping_bundle", "geometry.subspace3d"}
    assert result.evidence["rank"] + result.evidence["nullity"] == result.evidence["domain_dimension"]

def test_affine_line_is_rejected_when_marked_as_linear_subspace():
    with pytest.raises(VisualCompileError, match="origin"):
        compile_subspace(affine_offset=[1, 0, 0], is_linear=True)
```

- [x] **Step 2: Run family and 3D renderer tests before implementation**

Run: `pytest tests/test_linear_algebra_subspace_family.py tests/test_geometry_3d_scene.py -q`

Expected: FAIL because new operations are not allowed or rendered.

- [x] **Step 3: Implement numeric validation, lane layout and bounded renderer adapters**

Compute rank/nullity from finite matrices, enforce origin for linear subspaces, clip 3D lines/planes to render bounds, and generate separate stable aliases for domain, kernel and image. Register high-level operations in the command service and validate expanded atomics.

- [x] **Step 4: Run family, command and 3D tests**

Run: `pytest tests/test_linear_algebra_subspace_family.py tests/test_geometry_3d_scene.py tests/test_agent_runtime.py -q`

Expected: PASS; invalid dimensions and over-budget layouts fail before host mutation.

- [x] **Step 5: Commit subspace scene support**

```bash
git add linear_algebra/visualizations/families/subspace.py services/scene_commands.py rendering/geometry_3d_scene.py tests/test_linear_algebra_subspace_family.py tests/test_geometry_3d_scene.py
git commit -m "feat: render subspace and domain-image scene families"
```

<!-- openspec-task: 3.3 -->
### Task 7: 实现约束线/面及解状态

**Files:**
- Create: `linear_algebra/visualizations/families/constraints.py`
- Modify: `services/scene_commands.py`
- Modify: `rendering/geometry_scene.py`
- Modify: `rendering/geometry_3d_scene.py`
- Test: `tests/test_linear_algebra_constraint_family.py`

**Interfaces:**
- Produces `ConstraintFamilyCompiler` for finite normal/offset constraints in 2D and 3D.
- Produces `classify_constraint_system(matrix, rhs, tolerance) -> Literal["unique", "none", "infinite"]` with rank evidence.
- Compiled output contains `geometry.constraint`, intersection entity aliases and declared solution state.

- [x] **Step 1: Add three-state and numerical consistency tests**

```python
@pytest.mark.parametrize((matrix, rhs, expected), [
    ([[1, 0], [0, 1]], [1, 2], "unique"),
    ([[1, 0], [1, 0]], [1, 2], "none"),
    ([[1, 0], [2, 0]], [1, 2], "infinite"),
])
def test_constraint_solution_classification(matrix, rhs, expected):
    assert classify_constraint_system(matrix, rhs, 1e-9).kind == expected
```

- [x] **Step 2: Run constraint tests before the classifier exists**

Run: `pytest tests/test_linear_algebra_constraint_family.py -q`

Expected: FAIL with missing compiler/classifier.

- [x] **Step 3: Implement rank-based classification and clipped geometry**

Compare `rank(A)` and `rank([A|b])`; store ranks and residual in evidence. Render unique points/lines, empty intersections with a diagnostic annotation, and infinite intersection lines/planes using bounded geometry. Do not infer state from near-parallel pixels.

- [x] **Step 4: Run 2D/3D command and family tests**

Run: `pytest tests/test_linear_algebra_constraint_family.py tests/test_geometry_2d.py tests/test_geometry_3d_scene.py tests/test_agent_runtime.py -q`

Expected: PASS for all three solution states and explicit failures for singular numeric inputs.

- [x] **Step 5: Commit constraint geometry support**

```bash
git add linear_algebra/visualizations/families/constraints.py services/scene_commands.py rendering/geometry_scene.py rendering/geometry_3d_scene.py tests/test_linear_algebra_constraint_family.py
git commit -m "feat: render linear constraint solution states"
```

<!-- openspec-task: 3.4 -->
### Task 8: 实现矩阵 tableau 和消元 storyboard

**Files:**
- Create: `linear_algebra/visualizations/families/tableau.py`
- Modify: `services/scene_commands.py`
- Modify: `ui/linear_algebra_content_view.py`
- Test: `tests/test_linear_algebra_matrix_tableau.py`

**Interfaces:**
- Produces `MatrixTableauCompiler` for augmented matrices and row operations `swap`, `scale`, `eliminate`.
- Produces `apply_row_operation(matrix, rhs, operation) -> tuple[matrix, rhs]` and one stable stage alias per tableau.
- UI consumes stage title/caption/highlight rows but never parses matrix operation JSON.

- [x] **Step 1: Add exact row-operation and stage tests**

```python
def test_eliminate_row_operation_has_exact_next_tableau():
    matrix, rhs = apply_row_operation([[1, 2], [3, 4]], [5, 6], Eliminate(target=1, source=0, factor=3))
    assert matrix == [[1, 2], [0, -2]]
    assert rhs == [5, -9]
```

- [x] **Step 2: Run tableau tests before command support exists**

Run: `pytest tests/test_linear_algebra_matrix_tableau.py -q`

Expected: FAIL on missing row-operation types and `geometry.matrix_tableau`.

- [x] **Step 3: Implement typed row operations and static stage payloads**

Validate row indexes, nonzero scale factors and finite values. Emit one tableau per stage with immutable matrix values, operation label and highlight rows. Preserve solution-set/rank invariants in stage metadata.

- [x] **Step 4: Run tableau, storyboard and content-view tests**

Run: `pytest tests/test_linear_algebra_matrix_tableau.py tests/test_linear_algebra_visual_compiler.py tests/test_linear_algebra_dialog.py -q`

Expected: PASS; switching stages only changes visibility metadata.

- [x] **Step 5: Commit matrix tableau support**

```bash
git add linear_algebra/visualizations/families/tableau.py services/scene_commands.py ui/linear_algebra_content_view.py tests/test_linear_algebra_matrix_tableau.py
git commit -m "feat: add elimination matrix tableau storyboards"
```

<!-- openspec-task: 3.5 -->
### Task 9: 实现最小二乘、备用基网格和双向坐标

**Files:**
- Create: `linear_algebra/visualizations/families/coordinates.py`
- Create: `linear_algebra/visualizations/families/least_squares.py`
- Modify: `services/scene_commands.py`
- Modify: `rendering/geometry_scene.py`
- Test: `tests/test_linear_algebra_coordinate_family.py`
- Test: `tests/test_linear_algebra_least_squares.py`

**Interfaces:**
- Produces `CoordinateFamilyCompiler` for `geometry.basis_grid` and `geometry.coordinate_readout`.
- Produces `LeastSquaresFamilyCompiler` and `least_squares_fit(matrix, values, tolerance) -> LeastSquaresEvidence`.
- Coordinate evidence must satisfy `standard_vector == basis_matrix @ alternate_coordinates`; residual evidence must satisfy `A.T @ residual ≈ 0`.

- [x] **Step 1: Add coordinate round-trip and residual orthogonality tests**

```python
def test_alternate_coordinates_round_trip_to_same_vector():
    evidence = coordinate_evidence([[1, 1], [0, 1]], [2, 3])
    assert_allclose(evidence.basis_matrix @ evidence.alternate_coordinates, evidence.standard_vector)

def test_least_squares_residual_is_orthogonal_to_columns():
    evidence = least_squares_fit([[1, 0], [1, 1], [1, 2]], [1, 2, 2], 1e-9)
    assert_allclose(evidence.design_matrix.T @ evidence.residual, [0, 0], atol=1e-9)
```

- [x] **Step 2: Run focused tests before family compilers exist**

Run: `pytest tests/test_linear_algebra_coordinate_family.py tests/test_linear_algebra_least_squares.py -q`

Expected: FAIL with missing compiler/evidence functions.

- [x] **Step 3: Implement finite linear algebra and bounded visual bundles**

Reject singular basis matrices for bidirectional readout. Solve least squares with NumPy, preserve projection/residual arrays in evidence, and emit stable aliases for data, fit, projections and residuals. Register command validation and 2D renderer expansion.

- [x] **Step 4: Run family, command and rendering regressions**

Run: `pytest tests/test_linear_algebra_coordinate_family.py tests/test_linear_algebra_least_squares.py tests/test_geometry_2d.py tests/test_agent_runtime.py -q`

Expected: PASS for invertible bases and residual orthogonality; singular bases fail explicitly.

- [x] **Step 5: Commit coordinate and least-squares families**

```bash
git add linear_algebra/visualizations/families/coordinates.py linear_algebra/visualizations/families/least_squares.py services/scene_commands.py rendering/geometry_scene.py tests/test_linear_algebra_coordinate_family.py tests/test_linear_algebra_least_squares.py
git commit -m "feat: add coordinate and least-squares scene families"
```
