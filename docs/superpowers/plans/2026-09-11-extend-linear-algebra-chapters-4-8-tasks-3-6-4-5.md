# 线性代数第 4–8 章扩展（高级场景与章节内容）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `openspec-executing-plans` to implement this plan task-by-task and sync completed work back to OpenSpec tasks. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成谱/正交/二次型渲染能力，并用这些场景族实现和发布第 4–8 章全部 39 个主题。

**Architecture:** 高级场景族保持“数值证据 → 受控操作 → renderer replay”的单一路径；各章只提供 topic-local semantic fixture、解释、contract 和 builder 注册。章节发布按 4→8 顺序进行，每章可单独撤回。

**Tech Stack:** Python 3.11、NumPy、PyVista、PySide6、pytest、现有场景命令和教学资源发布工具。

**Spec:** `docs/superpowers/specs/2026-09-11-linear-algebra-chapters-4-8-design.md`、`openspec/changes/extend-linear-algebra-chapters-4-8/`。

## Global Constraints

- 本计划依赖计划 1–2 的 93-topic catalog、39 reviewed artifacts、family routing 和基础场景族。
- 所有新操作必须在 schema、命令服务、离线 replay 和实际 renderer 四层同时存在后才能发布。
- 每章拥有独立 catalog/explanation/recipe/builder/artifact/contract/snapshot；跨章只共享场景族。
- 主题 builder 只组合受控语义数据，不直接访问 Qt/PyVista 或宿主场景。
- 发布前验证 source hash、artifact revision、contract 和 plan digest；失败时不更新章节 index。
- 每个任务使用 TDD 和隔离提交，不加入工作区无关修改。

---

<!-- openspec-task: 3.6 -->
### Task 1: 实现特征值谱、3D 投影和 Gram–Schmidt

**Files:**
- Create: `linear_algebra/visualizations/families/spectral.py`
- Create: `linear_algebra/visualizations/families/orthogonalization.py`
- Modify: `services/scene_commands.py`
- Modify: `rendering/geometry_3d_scene.py`
- Test: `tests/test_linear_algebra_spectral_family.py`
- Test: `tests/test_linear_algebra_orthogonalization.py`

**Interfaces:**
- Produces `spectral_evidence(matrix, tolerance) -> SpectralEvidence` with roots and eigenspace bases.
- Produces `gram_schmidt(vectors, tolerance) -> OrthogonalizationEvidence` with projection components, residuals and normalized basis.
- Produces high-level operations `geometry.spectrum`, `geometry.projection3d` and `geometry.orthogonalization` with stable stage aliases.

- [x] **Step 1: Add eigen binding, projection and orthogonality tests**

```python
def test_each_real_spectral_root_binds_to_an_eigenspace():
    evidence = spectral_evidence([[2, 0], [0, 3]], 1e-9)
    assert {root.value for root in evidence.roots} == {2, 3}
    assert all(root.eigenspace_id in evidence.eigenspaces for root in evidence.roots)

def test_gram_schmidt_outputs_orthonormal_basis():
    evidence = gram_schmidt([[1, 1, 0], [1, 0, 1]], 1e-9)
    assert_allclose(evidence.basis @ evidence.basis.T, np.eye(2), atol=1e-9)
```

- [x] **Step 2: Run focused tests before advanced family support exists**

Run: `pytest tests/test_linear_algebra_spectral_family.py tests/test_linear_algebra_orthogonalization.py -q`

Expected: FAIL with missing spectral/orthogonalization compilers.

- [x] **Step 3: Implement finite spectral and orthogonal evidence**

Sort real roots deterministically, associate each with `Null(A-λI)`, and mark complex-only cases as having no real direction. For Gram–Schmidt, reject dependent vectors below tolerance and emit input/projection/residual/normalized stages. Implement 3D foot/residual/right-angle geometry within bounds.

- [x] **Step 4: Run command, compiler and 3D renderer tests**

Run: `pytest tests/test_linear_algebra_spectral_family.py tests/test_linear_algebra_orthogonalization.py tests/test_geometry_3d_scene.py tests/test_agent_runtime.py -q`

Expected: PASS; complex roots never generate a fake real arrow.

- [x] **Step 5: Commit spectral and orthogonal scene support**

```bash
git add linear_algebra/visualizations/families/spectral.py linear_algebra/visualizations/families/orthogonalization.py services/scene_commands.py rendering/geometry_3d_scene.py tests/test_linear_algebra_spectral_family.py tests/test_linear_algebra_orthogonalization.py
git commit -m "feat: render spectral and orthogonalization evidence"
```

<!-- openspec-task: 3.7 -->
### Task 2: 实现二次型等值线、曲面和主轴

**Files:**
- Create: `linear_algebra/visualizations/families/quadratic.py`
- Modify: `services/scene_commands.py`
- Modify: `rendering/geometry_scene.py`
- Modify: `rendering/geometry_3d_scene.py`
- Test: `tests/test_linear_algebra_quadratic_family.py`

**Interfaces:**
- Produces `classify_quadratic(matrix, tolerance) -> QuadraticEvidence` with eigenvalues, principal axes, signature and classification.
- Produces `QuadraticFamilyCompiler` for `geometry.quadratic_level_set` in 2D/3D.
- Renderer consumes bounded vertices/contours generated after classification; it never evaluates raw user expressions.

- [x] **Step 1: Add classification and deterministic-axis tests**

```python
@pytest.mark.parametrize((matrix, expected), [
    ([[2, 0], [0, 1]], "positive_definite"),
    ([[1, 0], [0, -1]], "indefinite"),
    ([[1, 0], [0, 0]], "semidefinite"),
])
def test_quadratic_classification(matrix, expected):
    assert classify_quadratic(matrix, 1e-9).classification == expected

def test_principal_axes_are_stable_across_compilations():
    assert compile_quadratic([[3, 1], [1, 2]]).principal_axes == compile_quadratic([[3, 1], [1, 2]]).principal_axes
```

- [x] **Step 2: Run quadratic tests before the operation exists**

Run: `pytest tests/test_linear_algebra_quadratic_family.py -q`

Expected: FAIL with missing classifier/compiler.

- [x] **Step 3: Implement symmetric validation, eigendecomposition and bounded sampling**

Reject nonsymmetric/nonfinite matrices unless explicitly normalized by a validated symmetric-part rule. Stabilize eigenvector signs, classify from eigenvalues and tolerance, generate 2D contours up to 128×128 and 3D meshes up to 64³, and attach original/principal/standard-stage aliases.

- [x] **Step 4: Run quadratic, command and renderer tests**

Run: `pytest tests/test_linear_algebra_quadratic_family.py tests/test_geometry_2d.py tests/test_geometry_3d_scene.py tests/test_agent_runtime.py -q`

Expected: PASS with deterministic classification/layout and explicit sample-limit failures.

- [x] **Step 5: Commit quadratic geometry support**

```bash
git add linear_algebra/visualizations/families/quadratic.py services/scene_commands.py rendering/geometry_scene.py rendering/geometry_3d_scene.py tests/test_linear_algebra_quadratic_family.py
git commit -m "feat: render quadratic level sets and principal axes"
```

<!-- openspec-task: 3.8 -->
### Task 3: 完成所有新操作的命令、宿主和 replay 接入

**Files:**
- Modify: `services/scene_commands.py`
- Modify: `rendering/geometry_scene.py`
- Modify: `rendering/geometry_3d_scene.py`
- Modify: `ui/designer_window.py`
- Create: `tests/test_linear_algebra_extended_plan_replay.py`

**Interfaces:**
- `SceneCommandService.allowed_operations` includes every operation in `capability_map.py` and validates exact fields.
- The 2D/3D teaching hosts implement all expanded atomic operations transactionally.
- Produces `replay_extended_plan(plan: CommandPlan, host) -> CommandValidation` for deterministic offline/host parity tests.

- [x] **Step 1: Add operation coverage and atomic rollback tests**

```python
def test_every_extended_command_op_has_validator_and_replay_adapter():
    for spec in all_primitive_specs():
        for op in spec.command_ops:
            assert op in SceneCommandService().allowed_operations
            assert replay_registry.has(op)

def test_invalid_operation_rolls_back_entire_extended_plan(recording_host):
    plan = plan_with_valid_subspace_then_nan_quadratic()
    with pytest.raises(CommandError):
        SceneCommandService(recording_host).execute(plan)
    assert recording_host.committed_operations == []
```

- [x] **Step 2: Run replay tests and enumerate missing adapters**

Run: `pytest tests/test_linear_algebra_extended_plan_replay.py -q`

Expected: FAIL listing any operation missing from validator or replay.

- [x] **Step 3: Register exact schemas and host dispatch**

For each high-level op reject unknown keys, invalid role, nonfinite values, excessive counts and scene mismatch. Expand macros, validate each atomic operation, bind the target pane once, and execute through one transaction. Add no title/capability-based alternate dispatch.

- [x] **Step 4: Run full scene command and renderer tests**

Run: `pytest tests/test_linear_algebra_extended_plan_replay.py tests/test_agent_runtime.py tests/test_agent_capability_e2e.py tests/test_geometry_2d.py tests/test_geometry_3d_scene.py -q`

Expected: PASS with validator/replay/renderer operation parity.

- [x] **Step 5: Commit the complete extended rendering path**

```bash
git add services/scene_commands.py rendering/geometry_scene.py rendering/geometry_3d_scene.py ui/designer_window.py tests/test_linear_algebra_extended_plan_replay.py
git commit -m "feat: connect extended linear algebra plan replay"
```

<!-- openspec-task: 4.1 -->
### Task 4: 实现并发布第 4 章 16 个主题

**Files:**
- Create: `linear_algebra/visualizations/chapter_04.py`
- Create: `linear_algebra/visualizations/builders/chapter_04.py`
- Modify: `linear_algebra/visualizations/builders/__init__.py`
- Create: `linear_algebra/teaching/data/compiled/ch04.*.json`
- Modify: `linear_algebra/teaching/data/index.json`
- Test: `tests/test_linear_algebra_chapter_04.py`

**Interfaces:**
- Chapter module exports recipes/builders for exactly 16 chapter 4 topic IDs.
- Each builder consumes `RenderContext` and the reviewed artifact semantic graph, then returns a validated `CommandPlan` through the shared compiler.
- Chapter 4 index update occurs only after all source/artifact/contract/plan checks pass.

- [x] **Step 1: Add exact topic, capability and contract coverage tests**

```python
def test_chapter_four_has_16_complete_topic_bundles():
    bundles = chapter_bundles(4)
    assert len(bundles) == 16
    assert all(bundle.artifact and bundle.compiled and bundle.snapshot for bundle in bundles)
    assert declared_ops(bundles) == actual_required_ops(bundles)
```

- [x] **Step 2: Run chapter 4 tests before builders/snapshots exist**

Run: `pytest tests/test_linear_algebra_chapter_04.py -q`

Expected: FAIL for missing recipes/builders/published snapshots.

- [x] **Step 3: Implement subspace/rank/kernel-image topic fixtures and builders**

Use the 16 IDs in `drawing-catalog.md`, explicit contracts and reviewed artifacts. Ensure closure/classification/intersection/span/dependence/nullspace/rank/basis/dimension/coordinates/maps/kernel-image/rank-nullity claims emit actual family operations, not labels alone.

- [x] **Step 4: Publish chapter 4 and run focused validations**

Run: `pytest tests/test_linear_algebra_chapter_04.py tests/test_linear_algebra_chapters_4_8_artifacts.py tests/test_linear_algebra_compiled_resources.py -q`

Expected: PASS for all 16 bundles; chapter 1–3 digests unchanged.

- [x] **Step 5: Commit chapter 4 resources**

```bash
git add linear_algebra/visualizations/chapter_04.py linear_algebra/visualizations/builders/chapter_04.py linear_algebra/visualizations/builders/__init__.py linear_algebra/teaching/data/compiled linear_algebra/teaching/data/index.json tests/test_linear_algebra_chapter_04.py
git commit -m "feat: publish linear algebra chapter 4 visuals"
```

<!-- openspec-task: 4.2 -->
### Task 5: 实现并发布第 5 章 8 个主题

**Files:**
- Create: `linear_algebra/visualizations/chapter_05.py`
- Create: `linear_algebra/visualizations/builders/chapter_05.py`
- Modify: `linear_algebra/visualizations/builders/__init__.py`
- Create: `linear_algebra/teaching/data/compiled/ch05.*.json`
- Modify: `linear_algebra/teaching/data/index.json`
- Test: `tests/test_linear_algebra_chapter_05.py`

**Interfaces:**
- Chapter module exports exactly 8 equation/solution/elimination/least-squares recipes.
- The consistency topic carries all three solution-state stages; Gaussian elimination carries exact tableau operations; least squares carries residual orthogonality evidence.

- [x] **Step 1: Add chapter 5 bundle and invariant tests**

```python
def test_chapter_five_visuals_include_solution_states_and_least_squares_evidence():
    bundles = chapter_bundles(5)
    assert len(bundles) == 8
    assert stage_ids(bundle_for(bundles, "ch05.consistency.geometry")) >= {"unique", "none", "infinite"}
    assert "residual_orthogonal" in invariants(bundle_for(bundles, "ch05.least-squares.projection"))
```

- [x] **Step 2: Run chapter 5 tests before builders exist**

Run: `pytest tests/test_linear_algebra_chapter_05.py -q`

Expected: FAIL for unresolved visualization IDs.

- [x] **Step 3: Implement the 8 chapter-local recipes using shared families**

Bind homogeneous/affine solution sets, consistency, Gaussian elimination, least squares, fundamental solution systems, elementary matrices and least-squares derivation to explicit semantic fixtures. Do not duplicate constraint/tableau/least-squares math in chapter builders.

- [x] **Step 4: Publish and validate chapter 5**

Run: `pytest tests/test_linear_algebra_chapter_05.py tests/test_linear_algebra_constraint_family.py tests/test_linear_algebra_matrix_tableau.py tests/test_linear_algebra_least_squares.py -q`

Expected: PASS with eight atomic bundles and unchanged earlier chapter indices.

- [x] **Step 5: Commit chapter 5 resources**

```bash
git add linear_algebra/visualizations/chapter_05.py linear_algebra/visualizations/builders/chapter_05.py linear_algebra/visualizations/builders/__init__.py linear_algebra/teaching/data/compiled linear_algebra/teaching/data/index.json tests/test_linear_algebra_chapter_05.py
git commit -m "feat: publish linear algebra chapter 5 visuals"
```

<!-- openspec-task: 4.3 -->
### Task 6: 实现并发布第 6 章 3 个主题

**Files:**
- Create: `linear_algebra/visualizations/chapter_06.py`
- Create: `linear_algebra/visualizations/builders/chapter_06.py`
- Modify: `linear_algebra/visualizations/builders/__init__.py`
- Create: `linear_algebra/teaching/data/compiled/ch06.*.json`
- Modify: `linear_algebra/teaching/data/index.json`
- Test: `tests/test_linear_algebra_chapter_06.py`

**Interfaces:**
- Chapter module exports 3 basis-change/similarity recipes.
- Similarity storyboard stages are `change_basis`, `apply_operator`, `change_basis_back` and verify the same geometric endpoint as `P^{-1}AP`.

- [x] **Step 1: Add exact three-topic and coordinate-path tests**

```python
def test_similarity_storyboard_has_three_exact_stages():
    bundle = resolve_published("ch06.similarity-transform")
    assert tuple(stage.id for stage in bundle.compiled.storyboard) == ("change_basis", "apply_operator", "change_basis_back")
    assert bundle.compiled.evidence.endpoint_error < 1e-9
```

- [x] **Step 2: Run chapter 6 tests before builders exist**

Run: `pytest tests/test_linear_algebra_chapter_06.py -q`

Expected: FAIL for missing chapter 6 recipes.

- [x] **Step 3: Implement three coordinate-family topic fixtures**

Show two bases and the same vector with two readings, then implement similarity as a three-stage coordinate path. Reuse `CoordinateFamilyCompiler`; the chapter builder provides matrices/vectors/claims only.

- [x] **Step 4: Publish and validate chapter 6**

Run: `pytest tests/test_linear_algebra_chapter_06.py tests/test_linear_algebra_coordinate_family.py tests/test_linear_algebra_compiled_resources.py -q`

Expected: PASS for all three topics and reversible coordinate conversions.

- [x] **Step 5: Commit chapter 6 resources**

```bash
git add linear_algebra/visualizations/chapter_06.py linear_algebra/visualizations/builders/chapter_06.py linear_algebra/visualizations/builders/__init__.py linear_algebra/teaching/data/compiled linear_algebra/teaching/data/index.json tests/test_linear_algebra_chapter_06.py
git commit -m "feat: publish linear algebra chapter 6 visuals"
```

<!-- openspec-task: 4.4 -->
### Task 7: 实现并发布第 7 章 6 个主题

**Files:**
- Create: `linear_algebra/visualizations/chapter_07.py`
- Create: `linear_algebra/visualizations/builders/chapter_07.py`
- Modify: `linear_algebra/visualizations/builders/__init__.py`
- Create: `linear_algebra/teaching/data/compiled/ch07.*.json`
- Modify: `linear_algebra/teaching/data/index.json`
- Test: `tests/test_linear_algebra_chapter_07.py`

**Interfaces:**
- Chapter module exports 6 eigen/spectrum/diagonalization/Gram–Schmidt/orthogonal recipes.
- Diagonalization has change-basis/diagonal-scale/change-back stages; Gram–Schmidt has input/projection/residual/normalized evidence.

- [x] **Step 1: Add six-topic spectral and orthogonal contract tests**

```python
def test_chapter_seven_bundles_bind_roots_directions_and_stages():
    bundles = chapter_bundles(7)
    assert len(bundles) == 6
    assert all_real_roots_have_eigenspace_refs(bundles)
    assert required_relations("ch07.diagonalization") >= {"change_basis", "diagonal_scale", "change_basis_back"}
```

- [x] **Step 2: Run chapter 7 tests before resources exist**

Run: `pytest tests/test_linear_algebra_chapter_07.py -q`

Expected: FAIL for missing builders/snapshots.

- [x] **Step 3: Implement six topic-local semantic fixtures**

Use spectral and orthogonal family compilers; include eigen direction, characteristic roots, eigenspace, diagonalization, Gram–Schmidt and orthogonal transform. Exclude Cayley–Hamilton as an independent drawing topic per the catalog.

- [x] **Step 4: Publish and validate chapter 7**

Run: `pytest tests/test_linear_algebra_chapter_07.py tests/test_linear_algebra_spectral_family.py tests/test_linear_algebra_orthogonalization.py -q`

Expected: PASS with no fake real directions for complex roots.

- [x] **Step 5: Commit chapter 7 resources**

```bash
git add linear_algebra/visualizations/chapter_07.py linear_algebra/visualizations/builders/chapter_07.py linear_algebra/visualizations/builders/__init__.py linear_algebra/teaching/data/compiled linear_algebra/teaching/data/index.json tests/test_linear_algebra_chapter_07.py
git commit -m "feat: publish linear algebra chapter 7 visuals"
```

<!-- openspec-task: 4.5 -->
### Task 8: 实现并发布第 8 章 6 个主题

**Files:**
- Create: `linear_algebra/visualizations/chapter_08.py`
- Create: `linear_algebra/visualizations/builders/chapter_08.py`
- Modify: `linear_algebra/visualizations/builders/__init__.py`
- Create: `linear_algebra/teaching/data/compiled/ch08.*.json`
- Modify: `linear_algebra/teaching/data/index.json`
- Test: `tests/test_linear_algebra_chapter_08.py`

**Interfaces:**
- Chapter module exports 6 quadratic-form/level-set/principal-axis/definiteness/completing-square/congruence recipes.
- `ch08.principal-axis` contains original/axes/standard stages linked to one symmetric matrix and one claim set.

- [x] **Step 1: Add six-topic classification and principal-axis tests**

```python
def test_principal_axis_topic_links_one_matrix_across_three_stages():
    bundle = resolve_published("ch08.principal-axis")
    assert tuple(stage.id for stage in bundle.compiled.storyboard) == ("original", "axes", "standard")
    assert matrix_claim_refs_are_shared(bundle.artifact)
    assert bundle.compiled.evidence.cross_term_after_rotation < 1e-9
```

- [x] **Step 2: Run chapter 8 tests before resources exist**

Run: `pytest tests/test_linear_algebra_chapter_08.py -q`

Expected: FAIL for missing recipes and snapshots.

- [x] **Step 3: Implement six quadratic scene fixtures and builders**

Use one symmetric matrix per topic, explicit classification/signature and stable axes. Include matrix form, level sets, principal axis, definiteness, completing square and congruence/inertia. Do not register the positive-definite test list as a separate drawing topic.

- [x] **Step 4: Publish and validate chapter 8**

Run: `pytest tests/test_linear_algebra_chapter_08.py tests/test_linear_algebra_quadratic_family.py tests/test_linear_algebra_compiled_resources.py -q`

Expected: PASS for all six topics, classifications and sampling budgets.

- [x] **Step 5: Commit chapter 8 resources**

```bash
git add linear_algebra/visualizations/chapter_08.py linear_algebra/visualizations/builders/chapter_08.py linear_algebra/visualizations/builders/__init__.py linear_algebra/teaching/data/compiled linear_algebra/teaching/data/index.json tests/test_linear_algebra_chapter_08.py
git commit -m "feat: publish linear algebra chapter 8 visuals"
```
