# 线性代数第 4–8 章扩展（来源与基础门禁）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `openspec-executing-plans` to implement this plan task-by-task and sync completed work back to OpenSpec tasks. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立第 4–8 章扩展所需的语义能力映射、加载状态、渲染预算、来源解析和 39 个绘图主题的稳定目录。

**Architecture:** 先在纯 Python 层建立语义 primitive、场景族 fixture、加载状态机和 render profile；再扩展讲义来源解析器、绘图目录索引、catalog manifest 与树搜索。内容模块不依赖 Qt/PyVista，所有目录资源通过稳定 `topic_id` 进入 registry。

**Tech Stack:** Python 3.11、dataclasses、pytest、现有 `linear_algebra.catalog`、`linear_algebra.teaching`、`linear_algebra.visualizations` 和 Qt tree model。

**Spec:** `docs/superpowers/specs/2026-09-11-linear-algebra-chapters-4-8-design.md`、`openspec/changes/extend-linear-algebra-chapters-4-8/{proposal.md,design.md,tasks.md}`。

## Global Constraints

- 第 4–8 章绘图主题固定为 39 个，计数为 16/8/3/6/6；前三章固定为 54 个。
- 章节、解释、绘图和 fixture 使用稳定 `topic_id`；不得用显示标题或自然语言相似度路由主题。
- 内容和编译层不得导入 Qt、PyVista、主窗口或场景宿主。
- 2D/3D 只允许受控数值字段；非有限数值、维度不匹配和未知字段必须失败。
- 所有任务先写失败测试，再实现，再运行最小测试集；不修改 `.agents/线性代数讲义.md`。
- 不撤销或覆盖工作区已有修改；提交时只加入当前任务涉及的计划/代码/测试文件。

---

<!-- openspec-task: 0.1 -->
### Task 1: 固化 semantic primitive 与 CommandPlan 映射

**Files:**
- Create: `linear_algebra/visualizations/capability_map.py`
- Test: `tests/test_linear_algebra_capability_map.py`
- Modify: `linear_algebra/visualizations/__init__.py`

**Interfaces:**
- Produces `SemanticPrimitiveSpec(name: str, command_ops: tuple[str, ...], dimensions: tuple[int, ...], required_fields: tuple[str, ...])`。
- Produces `primitive_spec(name: str) -> SemanticPrimitiveSpec`、`all_primitive_specs() -> tuple[SemanticPrimitiveSpec, ...]` 和 `validate_payload_header(payload: Mapping[str, object]) -> tuple[str, ...]`。
- Later compiler tasks consume this map; a missing primitive or operation must be reported before compilation.

- [x] **Step 1: Write the failing tests**

```python
def test_all_extended_primitives_have_command_mapping():
    names = {item.name for item in all_primitive_specs()}
    assert {"subspace_family", "domain_image_map", "quadratic_level_set"} <= names
    assert primitive_spec("quadratic_level_set").command_ops == ("geometry.quadratic_level_set",)

def test_payload_header_rejects_unknown_role_and_nonfinite_dimension():
    errors = validate_payload_header({"op": "geometry.spectrum", "dimension": 4, "role": "unknown"})
    assert "dimension" in " ".join(errors)
    assert "role" in " ".join(errors)
```

- [x] **Step 2: Run the focused test to verify it fails**

Run: `pytest tests/test_linear_algebra_capability_map.py -q`

Expected: FAIL because the capability map module and public functions do not exist.

- [x] **Step 3: Implement the typed map and validator**

Use a frozen dataclass and one immutable registry. Register the ten primitives from the design document, including required fields and valid dimensions. Validate `op`, integer dimension `2|3`, finite numeric header values, non-empty claim references and the role vocabulary before any renderer is called.

- [x] **Step 4: Run the focused test and existing visualization import tests**

Run: `pytest tests/test_linear_algebra_capability_map.py tests/test_linear_algebra_visual_compiler.py -q`

Expected: PASS, with no change to existing chapter 1–3 compiler behavior.

- [x] **Step 5: Commit the isolated capability boundary**

```bash
git add linear_algebra/visualizations/capability_map.py linear_algebra/visualizations/__init__.py tests/test_linear_algebra_capability_map.py
git commit -m "feat: define chapter 4-8 visual capability map"
```

<!-- openspec-task: 0.2 -->
### Task 2: 建立五类场景族 fixture 矩阵

**Files:**
- Create: `tests/fixtures/linear_algebra_chapters_4_8.py`
- Create: `tests/test_linear_algebra_scene_family_fixtures.py`

**Interfaces:**
- Produces `SceneFamilyFixture(family: str, case: str, payload: dict[str, object], expected: dict[str, object])`。
- Produces `scene_family_fixtures() -> tuple[SceneFamilyFixture, ...]` with normal, boundary and failure cases for all five families.
- Later family compilers and chapter builders use fixture IDs to select deterministic numeric examples; fixture data must not contain Qt or renderer objects.

- [x] **Step 1: Add failing coverage assertions**

```python
def test_each_scene_family_has_normal_boundary_and_failure_fixture():
    grouped = {(item.family, item.case) for item in scene_family_fixtures()}
    expected_families = {"subspace_structure", "constraint_solution", "basis_coordinate", "spectral_orthogonal", "quadratic_shape"}
    for family in expected_families:
        assert {(family, kind) for kind in ("normal", "boundary", "failure")} <= grouped
```

- [x] **Step 2: Run the test to verify the fixture module is absent**

Run: `pytest tests/test_linear_algebra_scene_family_fixtures.py -q`

Expected: FAIL with an import error.

- [x] **Step 3: Add finite, source-independent fixture data**

Include rank-deficient and full-rank subspaces, unique/no/infinite constraint solutions, invertible and singular basis changes, repeated/complex spectral roots, and positive-definite/indefinite/degenerate quadratic matrices. Mark each expected classification explicitly so tests do not infer it from pixels.

- [x] **Step 4: Test dimensions, finite values and expected classifications**

Run: `pytest tests/test_linear_algebra_scene_family_fixtures.py -q`

Expected: PASS and every payload has a valid dimension, bounded array sizes and finite numeric leaves.

- [x] **Step 5: Commit the reusable fixture matrix**

```bash
git add tests/fixtures/linear_algebra_chapters_4_8.py tests/test_linear_algebra_scene_family_fixtures.py
git commit -m "test: add chapter 4-8 scene family fixtures"
```

<!-- openspec-task: 0.3 -->
### Task 3: 实现主题加载状态机和错误码

**Files:**
- Create: `linear_algebra/teaching/load_states.py`
- Test: `tests/test_linear_algebra_teaching_load_states.py`

**Interfaces:**
- Produces `LoadPhase` values `idle`, `resolving`, `source_checked`, `artifact_checked`, `contract_checked`, `compiled`, `plan_validated`, `staged`, `committed`, `rejected`。
- Produces `LoadDiagnostic(code: str, topic_id: str, phase: LoadPhase, field: str, message: str)` and `LoadTransaction.advance(phase, ...)`/`reject(...)`.
- The runtime registry task consumes an immutable transaction snapshot and cannot commit from `selected` or an incomplete phase.

- [x] **Step 1: Write state transition and rejection tests**

```python
def test_commit_requires_staged_payload():
    transaction = LoadTransaction("ch04.space.closure")
    transaction.advance(LoadPhase.RESOLVING)
    with pytest.raises(ValueError, match="staged"):
        transaction.advance(LoadPhase.COMMITTED)

def test_rejection_retains_previous_revision_metadata():
    transaction = LoadTransaction("ch08.principal-axis", previous_revision=3)
    diagnostic = transaction.reject("source_stale", LoadPhase.SOURCE_CHECKED, "source_hash")
    assert diagnostic.code == "source_stale"
    assert transaction.previous_revision == 3
```

- [x] **Step 2: Run the focused tests and confirm the state API is missing**

Run: `pytest tests/test_linear_algebra_teaching_load_states.py -q`

Expected: FAIL with an import error.

- [x] **Step 3: Implement explicit allowed transitions**

Represent allowed transitions in an immutable adjacency map. `reject()` may be called from any non-committed phase and freezes the diagnostic; `commit()` is allowed only after `STAGED`. Include error codes `source_stale`, `contract_missing_evidence`, `unsupported_scene_family`, `numeric_invalid`, `layout_overflow`, `plan_invalid` and `renderer_unavailable`.

- [x] **Step 4: Run tests including existing registry transaction tests**

Run: `pytest tests/test_linear_algebra_teaching_load_states.py tests/test_linear_algebra_registry.py -q`

Expected: PASS; no existing topic can skip the current atomic-loading checks.

- [x] **Step 5: Commit the state machine**

```bash
git add linear_algebra/teaching/load_states.py tests/test_linear_algebra_teaching_load_states.py
git commit -m "feat: add atomic lecture topic load states"
```

<!-- openspec-task: 0.4 -->
### Task 4: 固化 RenderProfile 资源预算

**Files:**
- Modify: `linear_algebra/visualizations/common.py`
- Create: `linear_algebra/visualizations/limits.py`
- Test: `tests/test_linear_algebra_render_limits.py`

**Interfaces:**
- Produces `RenderLimits(profile: str, max_entities_2d: int, max_entities_3d: int, max_stages: int, max_samples_2d: int, max_samples_3d: int, absolute_tolerance: float, relative_tolerance: float)`。
- Produces `limits_for(profile: str) -> RenderLimits` and `validate_budget(profile, *, scene, entity_count, stage_count, sample_count, bounds) -> tuple[str, ...]`.
- `RenderContext` gains an immutable `limits` property resolved from `render_profile`; family compilers use it before allocating operations.

- [x] **Step 1: Add budget and bounds failure tests**

```python
def test_lecture_profile_rejects_excessive_3d_samples():
    errors = validate_budget("lecture-v1", scene="3d", entity_count=2, stage_count=1, sample_count=64 * 64 * 64 + 1, bounds=(-3, 3, -3, 3))
    assert any("samples" in error for error in errors)
```

- [x] **Step 2: Run the new test to verify the profile API is absent**

Run: `pytest tests/test_linear_algebra_render_limits.py -q`

Expected: FAIL with an import error or missing `RenderContext.limits`.

- [x] **Step 3: Implement deterministic limits and integrate RenderContext**

Define the lecture profile with 48/32 entities, 6 stages, 128×128 2D samples, 64×64×64 3D samples and finite tolerances. Reject reversed/NaN bounds and over-budget counts before compiler output.

- [x] **Step 4: Run focused and compiler regression tests**

Run: `pytest tests/test_linear_algebra_render_limits.py tests/test_linear_algebra_visual_compiler.py -q`

Expected: PASS and identical plan digests for existing artifacts under the default profile.

- [x] **Step 5: Commit the render budget boundary**

```bash
git add linear_algebra/visualizations/common.py linear_algebra/visualizations/limits.py tests/test_linear_algebra_render_limits.py
git commit -m "feat: enforce deterministic teaching render limits"
```

<!-- openspec-task: 0.5 -->
### Task 5: 准备章节端到端发布与回滚 fixture

**Files:**
- Create: `tests/fixtures/linear_algebra_chapter_release.py`
- Create: `tests/test_linear_algebra_chapter_release_fixtures.py`
- Modify: `linear_algebra/teaching/data/index.json`

**Interfaces:**
- Produces `ChapterReleaseFixture(chapter: int, topic_id: str, published_revision: int, stale_revision: int, previous_topic_id: str)` for chapters 4–8。
- Produces `chapter_release_fixtures() -> tuple[ChapterReleaseFixture, ...]` and `assert_previous_chapters_unchanged(before, after)`。
- Later store/registry tasks consume these fixtures to test per-chapter index insertion and removal.

- [x] **Step 1: Write release isolation tests**

```python
def test_each_new_chapter_has_one_publish_and_one_rollback_fixture():
    fixtures = chapter_release_fixtures()
    assert {fixture.chapter for fixture in fixtures} == {4, 5, 6, 7, 8}
    assert all(fixture.topic_id.startswith(f"ch{fixture.chapter:02d}.") for fixture in fixtures)
```

- [x] **Step 2: Run tests before fixture implementation**

Run: `pytest tests/test_linear_algebra_chapter_release_fixtures.py -q`

Expected: FAIL because the fixture module and chapter index entries do not exist.

- [x] **Step 3: Add one deterministic published/stale pair per chapter**

Use the first representative topic in each chapter, revision 1 as the published candidate and revision 0/source-mismatch metadata as the rollback case. Keep chapter 1–3 index entries byte-for-byte unchanged in the test snapshot.

- [x] **Step 4: Verify fixtures and index isolation**

Run: `pytest tests/test_linear_algebra_chapter_release_fixtures.py tests/test_linear_algebra_compiled_resources.py -q`

Expected: PASS; a failed chapter removes only its own index entry.

- [x] **Step 5: Commit the release fixtures**

```bash
git add tests/fixtures/linear_algebra_chapter_release.py tests/test_linear_algebra_chapter_release_fixtures.py linear_algebra/teaching/data/index.json
git commit -m "test: add chapter release isolation fixtures"
```

<!-- openspec-task: 1.1 -->
### Task 6: 扩展讲义来源解析和排除规则

**Files:**
- Modify: `linear_algebra/teaching/source.py`
- Test: `tests/test_lecture_source_validation.py`
- Create: `tests/fixtures/lecture_chapters_4_8_source.py`

**Interfaces:**
- Produces `LectureSourceRepository.context_for(entry)` support for repeated headings and adjacent context in chapters 4–8.
- Produces `extract_heading_occurrences(source, chapter_range=(4, 8)) -> tuple[SourceOccurrence, ...]` and `is_excluded_heading(title: str) -> bool`.
- Existing chapter 1–3 source validation remains unchanged and uses the same `SourceAnchor` occurrence semantics.

- [x] **Step 1: Add failing source cases**

```python
def test_chapter_4_to_8_source_resolves_repeated_heading_by_occurrence():
    occurrences = extract_heading_occurrences(sample_source(), chapter_range=(4, 8))
    matches = [item for item in occurrences if item.title == "定义"]
    assert len(matches) > 1
    assert matches[0].occurrence != matches[1].occurrence

def test_exercise_self_check_and_challenge_are_excluded():
    assert is_excluded_heading("练习")
    assert is_excluded_heading("自检")
    assert is_excluded_heading("挑战题")
```

- [x] **Step 2: Run source tests and verify current parser misses the cases**

Run: `pytest tests/test_lecture_source_validation.py tests/test_linear_algebra_teaching_source.py -q`

Expected: FAIL for repeated occurrence or chapter 4–8 context assertions.

- [x] **Step 3: Implement heading stack, occurrence counting and neighbor context**

Parse Markdown heading levels without assuming chapter 4–8 uses the same depth as chapter 1–3. Store full heading path, line numbers, occurrence within the same path and the adjacent non-heading text needed by `SourceContext`. Apply exclusions before catalog matching.

- [x] **Step 4: Run source and legacy anchor tests**

Run: `pytest tests/test_lecture_source_validation.py tests/test_linear_algebra_teaching_source.py tests/test_linear_algebra_source_evidence.py -q`

Expected: PASS for old and new source behavior.

- [x] **Step 5: Commit source parsing support**

```bash
git add linear_algebra/teaching/source.py tests/test_lecture_source_validation.py tests/fixtures/lecture_chapters_4_8_source.py
git commit -m "feat: parse chapter 4-8 lecture source anchors"
```

<!-- openspec-task: 1.2 -->
### Task 7: 将绘图目录转换为可校验索引

**Files:**
- Create: `linear_algebra/catalog/drawing_index.py`
- Create: `scripts/validate_linear_algebra_drawing_catalog.py`
- Test: `tests/test_linear_algebra_drawing_catalog.py`

**Interfaces:**
- Produces `DrawingCatalogEntry(topic_id, chapter_number, source_path, visual_claims, existing_capabilities, missing_capabilities)`。
- Produces `load_drawing_catalog(path: Path) -> tuple[DrawingCatalogEntry, ...]` and `validate_drawing_catalog(entries) -> tuple[str, ...]`.
- The validator must enforce 39 unique topics and chapter counts 16/8/3/6/6, and expose exclusions for non-geometric entries.

- [x] **Step 1: Write catalog count and duplicate tests**

```python
def test_drawing_catalog_has_expected_distribution():
    entries = load_drawing_catalog(Path("openspec/changes/extend-linear-algebra-chapters-4-8/drawing-catalog.md"))
    assert Counter(item.chapter_number for item in entries) == Counter({4: 16, 5: 8, 6: 3, 7: 6, 8: 6})
    assert len({item.topic_id for item in entries}) == 39
```

- [x] **Step 2: Run the test against the unparsed Markdown**

Run: `pytest tests/test_linear_algebra_drawing_catalog.py -q`

Expected: FAIL because no typed catalog loader exists.

- [x] **Step 3: Implement strict Markdown table parsing and validation**

Parse only rows beginning with a chapter 4–8 `topic_id`; reject malformed rows, empty source paths, missing visual claims or missing expected operations. Keep excluded 7.7 and 8.6 entries in explicit prose metadata, not in the topic index.

- [x] **Step 4: Run catalog validation and CLI smoke test**

Run: `pytest tests/test_linear_algebra_drawing_catalog.py -q` and `python scripts/validate_linear_algebra_drawing_catalog.py`

Expected: PASS with `39 topics; 16/8/3/6/6; 0 duplicates`.

- [x] **Step 5: Commit the source-grounded drawing index**

```bash
git add linear_algebra/catalog/drawing_index.py scripts/validate_linear_algebra_drawing_catalog.py tests/test_linear_algebra_drawing_catalog.py
git commit -m "feat: validate chapter 4-8 drawing catalog"
```

<!-- openspec-task: 1.3 -->
### Task 8: 注册第 4–8 章 catalog 和 manifest

**Files:**
- Create: `linear_algebra/catalog/chapter_04.py`
- Create: `linear_algebra/catalog/chapter_05.py`
- Create: `linear_algebra/catalog/chapter_06.py`
- Create: `linear_algebra/catalog/chapter_07.py`
- Create: `linear_algebra/catalog/chapter_08.py`
- Modify: `linear_algebra/catalog/manifest.py`
- Test: `tests/test_linear_algebra_catalog.py`

**Interfaces:**
- Each chapter module exports `entries() -> tuple[LessonEntry, ...]` in lecture order.
- `topic_entries()` returns 93 entries, and `lecture_manifest()` returns chapter/section/topic nodes with stable parent IDs.
- New entries use `ch04.*` through `ch08.*`, source anchors from the parser, `explain.<topic_id>` and `draw.<topic_id>`.

- [x] **Step 1: Extend catalog tests with exact counts and ordering**

```python
def test_manifest_has_93_topics_and_new_chapter_counts():
    topics = topic_entries()
    assert len(topics) == 93
    assert Counter(item.chapter_number for item in topics) == Counter({1: 24, 2: 15, 3: 15, 4: 16, 5: 8, 6: 3, 7: 6, 8: 6})
    assert [item.chapter_number for item in topics] == sorted(item.chapter_number for item in topics)
```

- [x] **Step 2: Run catalog tests and observe the current 54-topic failure**

Run: `pytest tests/test_linear_algebra_catalog.py -q`

Expected: FAIL at the 93-topic assertion before chapter modules are registered.

- [x] **Step 3: Add independent chapter modules and merge them explicitly**

Populate the 39 IDs from `drawing-catalog.md`; preserve chapter 1–3 tuple order and existing IDs. Update only the manifest merge and chapter-count assertions. Do not introduce a title-based fallback or old case IDs.

- [x] **Step 4: Run catalog and source anchor tests**

Run: `pytest tests/test_linear_algebra_catalog.py tests/test_lecture_source_validation.py -q`

Expected: PASS with complete paths and unique anchors for all 93 topics.

- [x] **Step 5: Commit the eight-chapter catalog**

```bash
git add linear_algebra/catalog/chapter_04.py linear_algebra/catalog/chapter_05.py linear_algebra/catalog/chapter_06.py linear_algebra/catalog/chapter_07.py linear_algebra/catalog/chapter_08.py linear_algebra/catalog/manifest.py tests/test_linear_algebra_catalog.py
git commit -m "feat: register linear algebra chapters 4-8"
```

<!-- openspec-task: 1.4 -->
### Task 9: 扩展讲义树搜索和默认展开

**Files:**
- Modify: `ui/linear_algebra_tree_model.py`
- Modify: `ui/linear_algebra_content_view.py`
- Test: `tests/test_linear_algebra_tree_model.py`
- Test: `tests/test_linear_algebra_tree_search.py`

**Interfaces:**
- Tree filtering consumes the 93-entry manifest and searchable explanation/source fields.
- Branch clicks only change expansion; leaf clicks emit the existing topic-selection signal with `topic_id`.
- Default state expands chapter and second-level section nodes for chapters 1–8 and keeps topic leaves collapsed.

- [x] **Step 1: Add search and branch non-loading tests**

```python
def test_search_keeps_chapter_eight_ancestor_for_principal_axis(tree_model):
    result = tree_model.filter("主轴定理")
    assert [node.id for node in result.visible_nodes] == ["ch08", "ch08.section.3", "ch08.principal-axis"]
    assert result.auto_expanded == ("ch08", "ch08.section.3")

def test_branch_click_does_not_emit_topic_selection(tree_model, qtbot):
    with qtbot.assertNotEmitted(tree_model.topic_selected):
        tree_model.click("ch05")
```

- [x] **Step 2: Run tree tests before changing the model**

Run: `pytest tests/test_linear_algebra_tree_model.py tests/test_linear_algebra_tree_search.py -q`

Expected: FAIL for chapter 8 search and default expansion assertions.

- [x] **Step 3: Index topic title, summary, formula and full source path**

Build a deterministic search index keyed by `topic_id`; preserve only matching ancestor nodes, auto-expand ancestor paths, return an empty tree for no matches, and clear the filter back to the eight-chapter default state. Keep branch and leaf events separate.

- [x] **Step 4: Run Qt tree and content view regressions**

Run: `pytest tests/test_linear_algebra_tree_model.py tests/test_linear_algebra_tree_search.py tests/test_linear_algebra_dialog.py -q`

Expected: PASS, with no scene load on chapter/section selection.

- [x] **Step 5: Commit tree expansion and search**

```bash
git add ui/linear_algebra_tree_model.py ui/linear_algebra_content_view.py tests/test_linear_algebra_tree_model.py tests/test_linear_algebra_tree_search.py
git commit -m "feat: extend lecture tree search through chapter eight"
```
