# Linear Algebra Lecture Tree Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the old linear-algebra examples with a lecture-driven, searchable tree containing the 54 geometry-oriented topics from chapters 1-3, with independently editable explanations, visualization recipes, and reusable 2D/3D drawing capabilities.

**Architecture:** linear_algebra/catalog owns the source-checked lesson manifest, linear_algebra/explanations owns mathematical text, and linear_algebra/visualizations owns deterministic CommandPlan builders. An explicit registry joins those modules and validates source anchors, capability references, and plans before the Qt UI consumes them. The UI tree is a separate adapter over the registry; it never contains lesson content or renderer code.

**Tech Stack:** Python 3.12, PySide6, PyVista, NumPy, SymPy where deterministic calculations are needed, pytest, existing CommandPlan/SceneCommandService, and the current Qt token/QSS system.

**Spec:** docs/superpowers/specs/2026-08-31-linear-algebra-lecture-tree-modular-design.md; OpenSpec change openspec/changes/expand-linear-algebra-lecture-tree/.

## Global Constraints

- The final implementation contains exactly 54 topic leaves: chapter 1 has 24, chapter 2 has 15, and chapter 3 has 15.
- The source of truth for topic selection is .agents/线性代数讲义.md; self-checks, exercises, challenges, and symbol-only derivations are excluded.
- Delete models/linear_algebra_cases.py and remove all legacy case IDs and compatibility adapters after callers migrate.
- Content modules must not import PySide6, PyVista, DesignerWindow, or a scene controller.
- Visualization builders return a validated CommandPlan; they never mutate a scene directly.
- Missing capabilities or broken source anchors fail registry validation with the topic ID and actionable error text.
- Runtime loading uses the checked-in manifest and does not require .agents/线性代数讲义.md to be present in a packaged application.
- Branch nodes only control tree state; only topic leaves trigger scene loading and mathematical explanation display.
- A failed plan build, validation, or execution leaves the current scene unchanged.
- Do not change the JSON shape of the existing math_case browser event unless a test proves the new content cannot be represented by it.

## File Map

Create the following focused modules:

~~~text
linear_algebra/
├─ __init__.py
├─ catalog/
│  ├─ __init__.py
│  ├─ model.py
│  ├─ chapter_01.py
│  ├─ chapter_02.py
│  ├─ chapter_03.py
│  └─ manifest.py
├─ explanations/
│  ├─ __init__.py
│  ├─ chapter_01.py
│  ├─ chapter_02.py
│  └─ chapter_03.py
├─ visualizations/
│  ├─ __init__.py
│  ├─ common.py
│  ├─ chapter_01.py
│  ├─ chapter_02.py
│  └─ chapter_03.py
├─ registry.py
└─ validation.py
~~~

Modify the existing scene and shell files only at their ownership boundaries:

~~~text
models/geometry_2d.py                  # filled regions and angle/projection data
models/geometry_3d.py                  # 3D line, plane, polygon, volume data
services/scene_commands.py             # command schemas, expansion, validation
rendering/geometry_scene.py             # 2D polygon/arc/marker rendering
rendering/geometry_3d_scene.py         # reusable 3D linear-object rendering
ui/designer_window.py                  # host dispatch and transactional loading
ui/algebra_panel.py                    # linear algebra entry wiring
ui/linear_algebra_tree_model.py        # tree construction/filter/expansion state
ui/linear_algebra_dialog.py             # popup controls and signals
ui/linear_algebra_content_view.py      # explanation presentation state
ui/icons.py
ui/styles/base.qss.in
~~~

Create focused tests:

~~~text
tests/test_linear_algebra_catalog.py
tests/test_linear_algebra_explanations.py
tests/test_linear_algebra_capabilities.py
tests/test_linear_algebra_recipes.py
tests/test_linear_algebra_registry.py
tests/test_lecture_source_validation.py
tests/test_linear_algebra_loading.py
tests/test_linear_algebra_tree_model.py
tests/test_linear_algebra_dialog.py
tests/test_geometry_3d_scene.py
~~~

---

<!-- openspec-task: 1.1 -->
### Task 1: Create the Source-Checked Curriculum and Explanation Modules

**Files:**
- Create: linear_algebra/__init__.py
- Create: linear_algebra/catalog/model.py
- Create: linear_algebra/catalog/chapter_01.py
- Create: linear_algebra/catalog/chapter_02.py
- Create: linear_algebra/catalog/chapter_03.py
- Create: linear_algebra/catalog/manifest.py
- Create: linear_algebra/explanations/__init__.py
- Create: linear_algebra/explanations/chapter_01.py
- Create: linear_algebra/explanations/chapter_02.py
- Create: linear_algebra/explanations/chapter_03.py
- Create: tests/test_linear_algebra_catalog.py
- Create: tests/test_linear_algebra_explanations.py
- Modify: models/linear_algebra_cases.py only during migration; it is deleted in Task 5 after all callers move.

**Interfaces:**
- Produces LessonEntry, LessonNode, and SourceAnchor dataclasses.
- Produces topic_entries() -> tuple[LessonEntry, ...] in lecture order.
- Produces lecture_manifest() -> tuple[LessonNode, ...] containing generated chapter, section, and topic nodes.
- Produces explanation_for(topic_id: str) -> ExplanationContent.
- Consumes only the approved 54-topic directory and plain Python/LaTeX strings.

- [x] **Step 1: Write failing catalog and explanation contract tests**

~~~python
from collections import Counter

from linear_algebra.catalog.manifest import lecture_manifest, topic_entries
from linear_algebra.explanations import explanation_for


def test_manifest_has_exact_chapter_counts_and_three_levels() -> None:
    topics = topic_entries()
    assert len(topics) == 54
    assert Counter(item.chapter_number for item in topics) == Counter({1: 24, 2: 15, 3: 15})
    assert len({item.id for item in topics}) == 54
    assert all(len(item.source_path) == 3 for item in topics)
    nodes = lecture_manifest()
    assert all(item.kind == "topic" for item in nodes if item.explanation_id)


def test_manifest_excludes_non_geometry_content_and_legacy_ids() -> None:
    topics = topic_entries()
    searchable = " ".join(" ".join(item.source_path) for item in topics)
    assert not any(word in searchable for word in ("自检", "练习", "挑战"))
    assert not any(item.id.startswith("vector-") for item in topics)


def test_every_topic_has_independent_explanation_content() -> None:
    for item in topic_entries():
        content = explanation_for(item.id)
        assert content.id == item.explanation_id
        assert content.title and content.summary and content.formula
        assert 2 <= len(content.steps) <= 12
        assert content.geometric_meaning and content.conclusion
~~~

- [x] **Step 2: Run the new tests and verify RED**

Run: pytest tests/test_linear_algebra_catalog.py tests/test_linear_algebra_explanations.py -q

Expected: FAIL because the linear_algebra package and its manifest do not exist.

- [x] **Step 3: Implement the immutable catalog model and the exact 54 entries**

Use explicit dataclasses and stable IDs whose prefix identifies the chapter and section:

~~~python
@dataclass(frozen=True)
class SourceAnchor:
    heading_path: tuple[str, ...]
    heading_level: int
    occurrence: int = 1


@dataclass(frozen=True)
class LessonEntry:
    id: str
    chapter_number: int
    section_id: str
    title: str
    source_path: tuple[str, str, str]
    source_anchor: SourceAnchor
    explanation_id: str
    visualization_id: str
    required_capabilities: tuple[str, ...]


@dataclass(frozen=True)
class LessonNode:
    id: str
    kind: Literal["chapter", "section", "topic"]
    title: str
    order: tuple[int, ...]
    parent_id: str | None
    children: tuple[str, ...]
    source_path: tuple[str, ...]
    explanation_id: str | None
    visualization_id: str | None
    required_capabilities: tuple[str, ...]
~~~

Populate chapter files in reviewed source order. Chapter 1 covers vector representation, vector operations, inner-product geometry, projection, vector proofs, and the n-dimensional analogy. Chapter 2 covers batch products, matrix-vector geometry, composition, basis, powers, subspaces, and the high-dimensional analogy. Chapter 3 covers oriented area, determinant properties, Cramer area ratios, inverse geometry, det=0, n-dimensional volume analogy, and reverse-order inverse composition. Do not add headings that the approved directory excluded.

- [x] **Step 4: Add one explanation module per chapter**

Keep explanations independent from catalog and renderer imports:

~~~python
@dataclass(frozen=True)
class ExplanationContent:
    id: str
    title: str
    summary: str
    formula: str
    steps: tuple[str, ...]
    geometric_meaning: str
    conclusion: str
    searchable_text: tuple[str, ...]
~~~

Use the lecture formulas and geometric meanings for all 54 entries. Keep proof text concise enough for the popup, but include the key geometric interpretation that the drawing establishes. Register each chapter mapping in linear_algebra/explanations/__init__.py and make missing IDs raise KeyError with the topic ID.

- [x] **Step 5: Run the catalog and explanation tests**

Run: pytest tests/test_linear_algebra_catalog.py tests/test_linear_algebra_explanations.py -q

Expected: PASS with exactly 54 topics and no legacy IDs.

- [x] **Step 6: Commit the content foundation**

~~~powershell
git add linear_algebra tests/test_linear_algebra_catalog.py tests/test_linear_algebra_explanations.py
git commit -m "feat: add source-checked linear algebra curriculum"
~~~

---

<!-- openspec-task: 1.1 -->
### Task 2: Add Reusable 2D and 3D Geometry Capabilities

**Files:**
- Create: models/geometry_3d.py
- Create: rendering/geometry_3d_scene.py
- Create: tests/test_geometry_3d_scene.py
- Create: tests/test_linear_algebra_capabilities.py
- Modify: models/geometry_2d.py
- Modify: services/scene_commands.py
- Modify: rendering/geometry_scene.py
- Modify: ui/designer_window.py

**Interfaces:**
- Adds validated command names geometry.polygon, geometry.angle_arc, geometry.right_angle_marker, geometry.projection, geometry.transformed_grid, geometry.subspace_region, geometry.staged_transform, linear3d.upsert, plane3d.upsert, geometry.parallelogram3d, geometry.parallelepiped, geometry.oriented_volume, and annotation.formula.
- Geometry3DSceneController.add_linear(...), add_plane(...), add_parallelogram(...), add_parallelepiped(...), and clear() own 3D teaching actors.
- Existing GeometrySceneController gains filled polygon, angle arc, right-angle marker, and projection-region rendering without changing point/line hit testing.
- Every new operation is expanded or dispatched through SceneCommandService; no recipe can bypass validation.

- [x] **Step 1: Write failing command-validation tests for every new operation family**

~~~python
from services.scene_commands import CommandPlan, SceneCommandService


def test_3d_linear_object_and_oriented_volume_are_validated() -> None:
    plan = CommandPlan(
        scene="3d",
        operations=(
            {"op": "linear3d.upsert", "alias": "v", "start": [0, 0, 0], "end": [2, 1, 3], "kind": "vector"},
            {"op": "geometry.oriented_volume", "alias": "V", "origin": [0, 0, 0], "vectors": [[1, 0, 0], [0, 2, 0], [0, 0, 3]]},
        ),
    )
    validation = SceneCommandService().validate(plan)
    assert validation.valid, validation.messages


def test_polygon_rejects_less_than_three_vertices() -> None:
    plan = CommandPlan(scene="2d", operations=({"op": "geometry.polygon", "alias": "bad", "vertices": [[0, 0], [1, 0]]},))
    validation = SceneCommandService().validate(plan)
    assert not validation.valid
    assert "vertices" in " ".join(validation.messages)
~~~

- [x] **Step 2: Run capability tests and verify RED**

Run: pytest tests/test_linear_algebra_capabilities.py tests/test_geometry_3d_scene.py -q

Expected: FAIL because the new command names and controller do not exist.

- [x] **Step 3: Implement strict command schemas and macro expansion**

Add the operation names to the correct 2D/3D scene scopes. Validate finite coordinates, dimensions, non-degenerate polygons, positive arc radius, matrix shape, opacity range, and vector counts. Expand macros into renderer-safe primitives where practical; reject a 2D operation in a 3D plan and vice versa.

Use these payload contracts:

~~~text
geometry.polygon: {alias, vertices: [[x, y], ...], color, opacity, outline}
geometry.angle_arc: {alias, vertex: [x, y], first: [x, y], second: [x, y], radius}
geometry.right_angle_marker: {alias, vertex: [x, y], first: [x, y], second: [x, y], size}
geometry.projection: {vector: [x, y], direction: [x, y], result_alias, foot_alias, residual_alias}
geometry.transformed_grid: {matrix: [[a, b], [c, d]], bounds: [xmin, xmax, ymin, ymax], step}
geometry.subspace_region: {basis: [[x, y], ...], bounds: [xmin, xmax, ymin, ymax], color, opacity}
geometry.staged_transform: {matrices: [[[a, b], [c, d]], ...], points: [[x, y], ...], aliases: [...]}
linear3d.upsert: {alias, start: [x, y, z], end: [x, y, z], kind, color, style, role, label}
plane3d.upsert: {alias, origin: [x, y, z], normal: [x, y, z], size, color, opacity}
geometry.parallelogram3d: {alias, origin: [x, y, z], vectors: [[x, y, z], [x, y, z]], color, opacity}
geometry.parallelepiped: {alias, origin: [x, y, z], vectors: [[...], [...], [...]], color, opacity}
geometry.oriented_volume: {alias, origin: [x, y, z], vectors: [[...], [...], [...]]}
annotation.formula: {alias, text, position: [x, y] or [x, y, z], color}
~~~

- [x] **Step 4: Implement renderer-owned data and actors**

Extend models/geometry_2d.py with immutable polygon/marker records and add typed 3D records in models/geometry_3d.py. Render 2D filled faces and arcs with stable actor names in GeometrySceneController; render 3D arrows, planes, parallelograms and parallelepipeds in Geometry3DSceneController with render=False batching and one final render. Preserve existing point/linear/annotation actor naming and clear behavior.

- [x] **Step 5: Wire host dispatch and test rendering with fake plotters**

Dispatch each expanded command from DesignerWindow.apply_scene_command. A 3D command must switch and validate the 3D scene before creating actors; a failed operation must raise CommandError so the existing transaction rolls back. Add fake-plotter tests asserting actor names, coordinates, visibility and clear behavior without requiring an interactive window.

- [x] **Step 6: Run capability and renderer tests**

Run: pytest tests/test_linear_algebra_capabilities.py tests/test_geometry_3d_scene.py tests/test_scene_commands.py -q

Expected: PASS, including existing scene-command regression tests.

- [x] **Step 7: Commit the reusable capability layer**

~~~powershell
git add models/geometry_2d.py models/geometry_3d.py rendering/geometry_scene.py rendering/geometry_3d_scene.py services/scene_commands.py ui/designer_window.py tests/test_linear_algebra_capabilities.py tests/test_geometry_3d_scene.py
git commit -m "feat: add linear algebra geometry capabilities"
~~~

---

<!-- openspec-task: 1.1 -->
### Task 3: Implement the 54 Deterministic Visualization Recipes

**Files:**
- Create: linear_algebra/visualizations/__init__.py
- Create: linear_algebra/visualizations/common.py
- Create: linear_algebra/visualizations/chapter_01.py
- Create: linear_algebra/visualizations/chapter_02.py
- Create: linear_algebra/visualizations/chapter_03.py
- Create: tests/test_linear_algebra_recipes.py

**Interfaces:**
- Produces RenderContext and VisualizationRecipe in linear_algebra.visualizations.common.
- Produces recipe_for(visualization_id: str) -> VisualizationRecipe and recipes_for_topics() -> Mapping[str, VisualizationRecipe].
- Every recipe builder has signature build(context: RenderContext) -> CommandPlan and is deterministic for the same context.
- Consumes the operation contracts from Task 2 and topic IDs from Task 1.

- [x] **Step 1: Write failing recipe coverage tests**

~~~python
from linear_algebra.catalog.manifest import topic_entries
from linear_algebra.visualizations import recipe_for
from linear_algebra.visualizations.common import RenderContext
from services.scene_commands import SceneCommandService


def test_every_topic_has_a_recipe_that_validates() -> None:
    validator = SceneCommandService()
    for topic in topic_entries():
        recipe = recipe_for(topic.visualization_id)
        first = recipe.builder(RenderContext.default(topic.id))
        second = recipe.builder(RenderContext.default(topic.id))
        assert first == second
        assert first.operations and first.operations[-1]["op"] == "view.fit"
        result = validator.validate(first)
        assert result.valid, (topic.id, result.messages)


def test_3d_topics_use_3d_scene() -> None:
    for topic in topic_entries():
        plan = recipe_for(topic.visualization_id).builder(RenderContext.default(topic.id))
        operation_names = {str(operation["op"]) for operation in plan.operations}
        if any(name.startswith("linear3d") or name.startswith("plane3d") for name in operation_names):
            assert plan.scene == "3d"
~~~

- [x] **Step 2: Run recipe tests and verify RED**

Run: pytest tests/test_linear_algebra_recipes.py -q

Expected: FAIL because the recipe registry and chapter modules do not exist.

- [x] **Step 3: Add shared recipe helpers**

Implement helpers that create points, vectors, construction lines, formulas, 2D polygons, and 3D vectors with consistent roles and colors. RenderContext.default(topic_id) returns a serializable context with fixed viewport bounds and a deterministic example seed. Every helper returns dictionaries only; it never calls a renderer.

- [x] **Step 4: Implement chapter 1 recipes in source order**

Cover the 24 selected leaves: vector/point distinction and coordinate geometry; addition, subtraction, scalar multiplication, linear combination, velocity composition, 3D cross product, and 3D scalar triple product; inner-product equivalence, dot/angle/projection, orthogonality and magnitude, Cauchy-Schwarz projection bound, projection examples; projection decomposition and properties, force decomposition; vector translation method, triangle midline, centroid, parallelogram diagonals; and the lower-dimensional analogy for n-dimensional intuition. Use angle arcs, right-angle markers, projection, polygons, and 3D operations wherever the topic requires them.

- [x] **Step 5: Implement chapter 2 recipes in source order**

Cover the 15 selected leaves: batch inner products, batch projection, matrix row/column views, transformed basis and grid, stretch/rotation/scale, staged composition and AB != BA, matrix/basis coordinates, matrix powers as repeated transforms, linear independence, rank, null space, column space, rank-nullity geometry, and the n-dimensional analogy. Use transformed grids, staged transforms, and subspace regions rather than duplicating matrix rendering code in each recipe.

- [x] **Step 6: Implement chapter 3 recipes in source order**

Cover the 15 selected leaves: oriented area, ad-bc area decomposition, determinant sign/zero/one, stretch/flip/collapse, row-swap/scaling/shear/equal-row properties, two-stage det(AB) area scale, Cramer area ratios, inverse undo, invertible versus collapsed maps, det=0 equivalences, 2D/3D/n-dimensional area-volume analogy, and reverse-order inverse composition. Use filled polygons for area, 3D parallelepipeds for volume, and staged transforms for composition/inverse explanations.

- [x] **Step 7: Run the complete recipe suite**

Run: pytest tests/test_linear_algebra_recipes.py tests/test_linear_algebra_capabilities.py -q

Expected: PASS for all 54 recipes, with no unregistered operations or invalid scene scopes.

- [x] **Step 8: Commit the recipe modules**

~~~powershell
git add linear_algebra/visualizations tests/test_linear_algebra_recipes.py
git commit -m "feat: add lecture visualization recipes"
~~~

---

<!-- openspec-task: 1.1 -->
### Task 4: Add Explicit Registry and Lecture Source Validation

**Files:**
- Create: linear_algebra/registry.py
- Create: linear_algebra/validation.py
- Create: tests/test_linear_algebra_registry.py
- Create: tests/test_lecture_source_validation.py

**Interfaces:**
- Produces catalog_registry() -> CurriculumRegistry.
- Produces validate_registry(registry: CurriculumRegistry) -> tuple[str, ...].
- Produces validate_lecture_source(path: Path, entries: Iterable[LessonEntry]) -> tuple[str, ...].
- Registry exposes get_topic(topic_id), get_explanation(explanation_id), and get_recipe(visualization_id).
- Consumes the catalog, explanations, recipes, and capability operation set from Tasks 1-3.

- [x] **Step 1: Write failing registry and source-anchor tests**

~~~python
from pathlib import Path

from linear_algebra.registry import catalog_registry
from linear_algebra.validation import validate_lecture_source, validate_registry


def test_complete_registry_has_no_reference_or_capability_errors() -> None:
    errors = validate_registry(catalog_registry())
    assert errors == ()


def test_repository_lecture_source_matches_all_topic_anchors() -> None:
    source = Path(__file__).parents[1] / ".agents" / "线性代数讲义.md"
    errors = validate_lecture_source(source, catalog_registry().topics)
    assert errors == ()
~~~

- [x] **Step 2: Run registry tests and verify RED**

Run: pytest tests/test_linear_algebra_registry.py tests/test_lecture_source_validation.py -q

Expected: FAIL because the registry and Markdown heading indexer do not exist.

- [x] **Step 3: Implement explicit registries**

Create immutable mappings from topic IDs to entries, explanation IDs to ExplanationContent, visualization IDs to recipes, and capability IDs to canonical command names. Detect duplicate IDs, missing references, orphaned explanations/recipes, invalid parent paths, and plans that fail SceneCommandService.validate().

- [x] **Step 4: Implement a deterministic heading-path validator**

Read only ATX heading lines from the source file, preserve heading level and occurrence number, and build the first-three-chapter path index. Match every SourceAnchor by full path, level, and occurrence. Report missing or ambiguous anchors with the topic ID and expected path. Reject entries whose path contains 自检, 练习, 挑战, or an excluded pure-symbol heading. Do not import this validator from the runtime UI path.

- [x] **Step 5: Add a development validation entry point**

Expose python -m linear_algebra.validation to print every error and exit with status 1, or print 54 topics validated and exit 0. Keep the source path configurable only through an explicit CLI argument; the default is the repository .agents path.

- [x] **Step 6: Run registry and source validation**

Run: pytest tests/test_linear_algebra_registry.py tests/test_lecture_source_validation.py -q

Expected: PASS with zero errors and 54 validated topic entries.

- [x] **Step 7: Commit the registry layer**

~~~powershell
git add linear_algebra/registry.py linear_algebra/validation.py tests/test_linear_algebra_registry.py tests/test_lecture_source_validation.py
git commit -m "feat: validate linear algebra curriculum registry"
~~~

---

<!-- openspec-task: 1.2 -->
### Task 5: Replace Legacy Case Loading with Lesson Loading

**Files:**
- Create: tests/test_linear_algebra_loading.py
- Modify: ui/designer_window.py
- Modify: ui/algebra_panel.py
- Modify: ui/agent_sidebar_web.py only if the existing math_case payload cannot consume ExplanationContent directly.
- Delete: models/linear_algebra_cases.py
- Modify/Delete: tests/test_linear_algebra_cases.py, tests/test_linear_algebra_case_loading.py, and any other tests importing the deleted model.

**Interfaces:**
- Produces MainWindow._linear_algebra_lesson_plan(topic_id: str) -> CommandPlan.
- Replaces _load_linear_algebra_case with _load_linear_algebra_topic(topic_id: str) -> None.
- Consumes catalog_registry().get_topic, get_explanation, and get_recipe.
- Keeps scene loading atomic: the generated plan begins with {\"op\": \"scene.clear\", \"scope\": \"all\"} and uses the recipe scene.

- [x] **Step 1: Write failing loading tests for all 54 topics**

~~~python
from linear_algebra.catalog.manifest import topic_entries
from ui.designer_window import MainWindow


def test_every_topic_is_wrapped_in_one_clear_and_load_plan() -> None:
    for topic in topic_entries():
        plan = MainWindow._linear_algebra_lesson_plan(topic.id)
        assert plan.operations[0] == {\"op\": \"scene.clear\", \"scope\": \"all\"}
        assert plan.scene in {\"2d\", \"3d\"}
        assert plan.operations[-1][\"op\"] == \"view.fit\"


def test_unknown_topic_does_not_change_scene_or_emit_math_case(qtbot) -> None:
    window = make_window_with_fake_scene_host(qtbot)
    window._load_linear_algebra_topic(\"missing-topic\")
    assert window.scene_command_service._last_plan is None
    assert \"未知线性代数主题\" in window.algebra_panel.status_text()
~~~

- [x] **Step 2: Run loading tests and verify RED**

Run: pytest tests/test_linear_algebra_loading.py -q

Expected: FAIL because the new registry-based loader and method do not exist.

- [x] **Step 3: Implement registry-based plan construction**

Resolve the topic, explanation, and recipe by ID; build the recipe plan; validate it before adding the leading scene.clear. If lookup, build, or validation fails, set an error status and return without executing. Do not reintroduce a LinearAlgebraCase record or a legacy-ID lookup.

- [x] **Step 4: Implement atomic execution and explanation dispatch**

Execute through SceneCommandService.execute(). On success, show the explanation object in the content/agent panel and include the new topic ID, title, formula, steps, and conclusion in the existing JSON-safe math-case projection. On CommandError, rely on the existing transaction rollback and leave the previous content selection unchanged.

- [x] **Step 5: Remove legacy model imports and tests**

Replace every import of models.linear_algebra_cases with the new registry API, then delete the old module and rewrite tests around topic IDs and registry contracts. Confirm rg \"models\\.linear_algebra_cases|vector-addition|vector-subtraction\" returns no production references.

- [x] **Step 6: Run loading and bridge regressions**

Run: pytest tests/test_linear_algebra_loading.py tests/test_agent_bridge.py tests/test_agent_web_protocol.py -q

Expected: PASS with the existing math_case envelope shape and no legacy case imports.

- [x] **Step 7: Commit the new loading path**

~~~powershell
git add ui/designer_window.py ui/algebra_panel.py ui/agent_sidebar_web.py tests/test_linear_algebra_loading.py tests/test_agent_bridge.py tests/test_agent_web_protocol.py
git rm models/linear_algebra_cases.py
git commit -m "refactor: load linear algebra lessons from curriculum registry"
~~~

---

<!-- openspec-task: 2.1 -->
### Task 6: Build the Three-Level Lecture Tree

**Files:**
- Create: ui/linear_algebra_tree_model.py
- Create: ui/linear_algebra_dialog.py
- Create: ui/linear_algebra_content_view.py
- Create: tests/test_linear_algebra_tree_model.py
- Create: tests/test_linear_algebra_dialog.py
- Modify: ui/algebra_panel.py

**Interfaces:**
- LinearAlgebraTreeModel(registry: CurriculumRegistry) builds branch and topic rows from lecture_manifest().
- LinearAlgebraTreeModel.visible_topic_ids() -> tuple[str, ...] returns filtered leaf IDs in source order.
- LinearAlgebraTreeModel.restore_default_expansion(), expand_all(), and collapse_to_chapters() are deterministic.
- LinearAlgebraDialog.requested = Signal(str) emits only topic IDs.
- Dialog exposes tree, search_edit, expand_button, collapse_button, and content_view for tests and accessibility checks.

- [x] **Step 1: Write failing tree and leaf-selection tests**

~~~python
def test_default_tree_has_three_open_chapters_and_closed_sections(qtbot) -> None:
    dialog = make_linear_algebra_dialog(qtbot)
    assert dialog.tree.topLevelItemCount() == 3
    for index in range(3):
        chapter = dialog.tree.topLevelItem(index)
        assert chapter.isExpanded()
        assert chapter.childCount() > 0
        assert all(not chapter.child(i).isExpanded() for i in range(chapter.childCount()))


def test_branch_click_does_not_emit_but_topic_leaf_does(qtbot) -> None:
    dialog = make_linear_algebra_dialog(qtbot)
    received: list[str] = []
    dialog.requested.connect(received.append)
    chapter = dialog.tree.topLevelItem(0)
    dialog.activate_item(chapter)
    assert received == []
    topic = chapter.child(0).child(0)
    dialog.activate_item(topic)
    assert received == [topic.data(0, Qt.ItemDataRole.UserRole)]
~~~

- [x] **Step 2: Run tree tests and verify RED**

Run: pytest tests/test_linear_algebra_tree_model.py tests/test_linear_algebra_dialog.py -q

Expected: FAIL because the new tree model and dialog do not exist.

- [x] **Step 3: Implement tree construction from manifest nodes**

Create QTreeWidgetItems from registry parent/child relationships. Store only a topic ID in Qt.ItemDataRole.UserRole on leaves; branch items have no load ID. Set topic tooltips from explanation summaries and keep source order from LessonNode.order.

- [x] **Step 4: Implement branch and leaf activation**

For a branch item, toggle its expanded state without emitting requested. For a topic item, hide the dialog and emit its ID exactly once. The content view resolves the explanation through the registry after the main window confirms the plan execution.

- [x] **Step 5: Run tree tests**

Run: pytest tests/test_linear_algebra_tree_model.py tests/test_linear_algebra_dialog.py -q

Expected: PASS with three chapters, correct parent paths, and leaf-only activation.

- [x] **Step 6: Commit the base tree**

~~~powershell
git add ui/linear_algebra_tree_model.py ui/linear_algebra_dialog.py ui/linear_algebra_content_view.py ui/algebra_panel.py tests/test_linear_algebra_tree_model.py tests/test_linear_algebra_dialog.py
git commit -m "feat: add lecture tree for linear algebra"
~~~

---

<!-- openspec-task: 2.2 -->
### Task 7: Add Search and Expansion Controls

**Files:**
- Modify: ui/linear_algebra_tree_model.py
- Modify: ui/linear_algebra_dialog.py
- Modify: tests/test_linear_algebra_tree_model.py
- Modify: tests/test_linear_algebra_dialog.py

**Interfaces:**
- LinearAlgebraTreeModel.filter(query: str) -> None matches title, source path, explanation summary, formula, and searchable aliases.
- LinearAlgebraDialog.expand_all() -> None expands all visible branches.
- LinearAlgebraDialog.collapse_to_chapters() -> None collapses all branches and leaves chapter rows visible.
- Clearing the search calls restore_default_expansion() and restores all rows.

- [x] **Step 1: Write failing search and expansion tests**

~~~python
def test_search_keeps_cramer_ancestors_and_hides_unrelated_topics(qtbot) -> None:
    dialog = make_linear_algebra_dialog(qtbot)
    dialog.search_edit.setText("克拉默")
    assert dialog.tree.topLevelItemCount() == 1
    chapter = dialog.tree.topLevelItem(0)
    assert "第3章" in chapter.text(0)
    section = chapter.child(0)
    assert section.isExpanded()
    visible = dialog.tree_model.visible_topic_ids()
    assert visible == ("ch03.cramer.area-ratio",)


def test_clear_search_restores_default_and_controls_have_deterministic_depths(qtbot) -> None:
    dialog = make_linear_algebra_dialog(qtbot)
    dialog.expand_all()
    assert dialog.tree_model.all_branches_expanded()
    dialog.collapse_to_chapters()
    assert dialog.tree_model.all_chapters_collapsed()
    dialog.search_edit.clear()
    assert dialog.tree.topLevelItemCount() == 3
    assert dialog.tree_model.default_expansion_is_restored()
~~~

- [x] **Step 2: Run tests and verify RED**

Run: pytest tests/test_linear_algebra_tree_model.py tests/test_linear_algebra_dialog.py -q

Expected: FAIL because filtering and control methods are not implemented.

- [x] **Step 3: Implement cached searchable text and ancestor-preserving filtering**

Build one normalized search string per topic from its title, source_path, explanation summary, formula, and searchable_text. Hide a topic when there is no substring match; hide a section/chapter only when all descendants are hidden. For non-empty queries expand every visible ancestor. An empty query unhides every row and restores the default chapter-open/section-closed state.

- [x] **Step 4: Implement expand/collapse controls and signal wiring**

Connect QLineEdit.textChanged, the expand button, and the collapse button to the model methods. Keep expansion state in the tree model so recreating the dialog does not duplicate search logic. Ensure a search result with no match leaves an empty tree and does not call the loading signal.

- [x] **Step 5: Run the complete popup interaction suite**

Run: pytest tests/test_linear_algebra_tree_model.py tests/test_linear_algebra_dialog.py -q

Expected: PASS for search, ancestor context, empty results, expand-all, collapse-to-chapters, and reset behavior.

- [x] **Step 6: Commit search and controls**

~~~powershell
git add ui/linear_algebra_tree_model.py ui/linear_algebra_dialog.py tests/test_linear_algebra_tree_model.py tests/test_linear_algebra_dialog.py
git commit -m "feat: add lecture tree search and expansion controls"
~~~

---

<!-- openspec-task: 2.3 -->
### Task 8: Integrate Popup Styling, Icons, and Accessible Labels

**Files:**
- Modify: ui/algebra_panel.py
- Modify: ui/icons.py
- Modify: ui/styles/base.qss.in
- Modify: tests/test_ui_tokens.py
- Modify: tests/test_linear_algebra_dialog.py

**Interfaces:**
- The popup uses object names linearAlgebraSearch, linearAlgebraTree, linearAlgebraExpandButton, and linearAlgebraCollapseButton.
- Search placeholder is 搜索讲义目录.
- Tooltips are 展开全部目录 and 折叠到章级.
- Both light and dark QSS builds resolve all tokens and style hover/selected/disabled rows.

- [x] **Step 1: Write failing visual/accessibility tests**

~~~python
def test_popup_controls_have_accessible_names_and_object_names(qtbot) -> None:
    dialog = make_linear_algebra_dialog(qtbot)
    assert dialog.search_edit.objectName() == "linearAlgebraSearch"
    assert dialog.search_edit.placeholderText() == "搜索讲义目录"
    assert dialog.tree.objectName() == "linearAlgebraTree"
    assert dialog.expand_button.toolTip() == "展开全部目录"
    assert dialog.collapse_button.toolTip() == "折叠到章级"
~~~

- [x] **Step 2: Run focused UI-token tests and verify RED**

Run: pytest tests/test_linear_algebra_dialog.py tests/test_ui_tokens.py -q

Expected: FAIL on missing object names, controls, icons, or QSS selectors.

- [x] **Step 3: Add local chevron icons and control layout**

Register chevrons-down and chevrons-up through the existing icon loader. Use icon buttons with 32px hit targets, visible tooltips, and existing token-driven spacing. Keep the popup compact and avoid wrapping the tree in nested card borders.

- [x] **Step 4: Add light/dark tree and search QSS**

Style the search field, branch indicators, topic rows, hover state, selected state, and disabled empty state using existing background, border, text, accent, radius, and spacing tokens. Do not introduce literal theme colors or unresolved $ placeholders.

- [x] **Step 5: Run both theme tests**

Run: pytest tests/test_linear_algebra_dialog.py tests/test_ui_tokens.py -q

Expected: PASS for object names, tooltips, icon loading, light QSS, dark QSS, and token resolution.

- [x] **Step 6: Commit the styled popup**

~~~powershell
git add ui/algebra_panel.py ui/icons.py ui/styles/base.qss.in tests/test_ui_tokens.py tests/test_linear_algebra_dialog.py
git commit -m "feat: style linear algebra lecture tree popup"
~~~

---

<!-- openspec-task: 3.1 -->
### Task 9: Run Focused Linear Algebra Integration Verification

**Files:**
- Modify only files implicated by a failing focused regression.
- Add a regression test beside the failing subsystem before changing production code.

**Interfaces:**
- Verifies the catalog, explanations, recipes, command validator, renderer host, loading transaction, Qt tree, search, and browser math-case projection together.

- [x] **Step 1: Run the focused regression command**

Run:

~~~powershell
pytest tests/test_linear_algebra_catalog.py tests/test_linear_algebra_explanations.py tests/test_linear_algebra_capabilities.py tests/test_linear_algebra_recipes.py tests/test_linear_algebra_registry.py tests/test_lecture_source_validation.py tests/test_linear_algebra_loading.py tests/test_linear_algebra_tree_model.py tests/test_linear_algebra_dialog.py tests/test_scene_commands.py tests/test_agent_bridge.py tests/test_agent_web_protocol.py -q
~~~

Expected: all focused tests pass with 54 topics and no imports of the deleted case model.

- [x] **Step 2: Add a failing regression test for each discovered issue**

Reduce each failure to one assertion, for example: a 3D recipe is rejected as 2D, a branch emits a topic ID, a failed load clears the scene, or a search result loses its chapter ancestor. Keep the test in the owning test file before editing production code.

- [x] **Step 3: Fix the smallest owning module and rerun its focused test**

Use the File Map boundaries: command schema errors belong in services/scene_commands.py, actor errors in a renderer/controller, registry errors in linear_algebra/registry.py, and popup state errors in the tree/dialog modules. Do not add compatibility aliases for deleted case IDs.

- [x] **Step 4: Re-run the complete focused command**

Expected: zero failures, no warnings about unresolved QSS tokens, and all 54 plans validated by SceneCommandService.

- [x] **Step 5: Commit focused regression fixes**

~~~powershell
git add linear_algebra models/geometry_2d.py models/geometry_3d.py services/scene_commands.py rendering/geometry_scene.py rendering/geometry_3d_scene.py ui/designer_window.py ui/algebra_panel.py ui/linear_algebra_tree_model.py ui/linear_algebra_dialog.py ui/linear_algebra_content_view.py ui/agent_sidebar_web.py tests
git commit -m "test: verify linear algebra lecture integration"
~~~

---

<!-- openspec-task: 3.2 -->
### Task 10: Complete Full Verification and OpenSpec Synchronization

**Files:**
- Modify: openspec/changes/expand-linear-algebra-lecture-tree/tasks.md only to synchronize completed checkbox states after implementation passes.
- Modify: openspec/changes/expand-linear-algebra-lecture-tree/proposal.md, design.md, and specs/linear-algebra-case-tabs/spec.md only if the user explicitly authorizes reconciling their stale legacy-case wording; the implementation itself must follow the approved Design Doc.

**Interfaces:**
- Verifies Python, frontend, rendering, bridge, OpenSpec, and source-validation boundaries.
- Produces a clean git diff --check and a complete OpenSpec progress report.

- [x] **Step 1: Run the full Python suite**

Run: pytest -q

Expected: zero failures and only the repository's known skipped tests.

- [x] **Step 2: Run frontend tests and production build**

Run:

~~~powershell
pnpm -C ui/agent_web test
pnpm -C ui/agent_web build
~~~

Expected: Vitest exits 0 and Vite exits 0.

- [x] **Step 3: Run source and OpenSpec validation**

Run:

~~~powershell
python -m linear_algebra.validation
openspec validate expand-linear-algebra-lecture-tree --strict
~~~

Expected: the source validator reports 54 topics and OpenSpec reports a valid change.

- [x] **Step 4: Inspect final repository state**

Run:

~~~powershell
git status --short
git diff --check
rg -n "models\\.linear_algebra_cases|vector-addition|vector-subtraction|vector-dot-product|vector-cross-product" --glob '*.py'
~~~

Expected: no production references to the deleted legacy model or IDs, no whitespace errors, and only intentional implementation files in the worktree.

- [x] **Step 5: Synchronize OpenSpec task checkboxes**

Mark an OpenSpec task [x] only after every mapped plan step for that label passes. Re-run:

~~~powershell
openspec instructions apply --change expand-linear-algebra-lecture-tree --json
~~~

Confirm the reported progress matches the completed plan tasks before declaring the implementation ready.

- [x] **Step 6: Commit documentation synchronization**

~~~powershell
git add openspec/changes/expand-linear-algebra-lecture-tree/tasks.md docs/superpowers/plans/2026-08-31-expand-linear-algebra-lecture-tree.md
git commit -m "docs: sync linear algebra implementation plan"
~~~
