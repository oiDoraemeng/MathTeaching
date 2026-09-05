# Linear Algebra Visual Semantics Compiler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compile claim-linked mathematical visual semantics into deterministic, validated teaching scenes with no irrelevant fallback drawings.

**Architecture:** `VisualContract` validates what a topic must communicate before compilation. A renderer-independent compiler translates entities, relations, stages, and layouts into existing `CommandPlan` operations, with small helper modules for evidence, layout, and palette. `SceneCommandService` remains the final execution validator.

**Tech Stack:** Python 3.11+, frozen dataclasses, existing `CommandPlan`/`SceneCommandService`, NumPy for bounded matrix arithmetic, pytest golden-plan tests.

**Spec:** `openspec/changes/enrich-linear-algebra-teaching-depth/design.md`, `linear-algebra-visual-primitives`, and `linear-algebra-color-contract` specs.

## Global Constraints

- `VisualSemanticsCompiler` is the only component that turns teaching semantics into a `CommandPlan`.
- Unsupported relations fail with a topic/relation diagnostic; never fall back to unrelated vectors.
- Layouts are static `sequence`, `side_by_side`, or `overlay`; no animation timeline is introduced.
- Entity aliases, coordinates, roles, stages, and plan digests are deterministic for a fixed artifact/compiler/render profile.
- Teaching colors come only from the shared role palette.
- Every compiled plan must pass `SceneCommandService.validate` before it can be published or executed.

## File Structure

- Create `linear_algebra/visualizations/contracts.py`: topic contracts and contract validation.
- Create `linear_algebra/visualizations/compiler.py`: semantic compiler entry point and operation dispatch.
- Create `linear_algebra/visualizations/evidence.py`: claim-to-plan evidence ledger.
- Create `linear_algebra/visualizations/layout.py`: deterministic slots, transforms, and bounds.
- Create `linear_algebra/visualizations/palette.py`: role-to-color mapping.
- Modify `linear_algebra/visualizations/builders/primitives.py`: reusable semantic helpers.
- Modify `linear_algebra/visualizations/common.py`: recipe calls compiler; remove dead generic plan builder.
- Create focused compiler tests and golden fixtures.

---

<!-- openspec-task: 4.1 -->
### Task 1: Define Topic Visual Contracts

**Files:**
- Create: `linear_algebra/visualizations/contracts.py`
- Create: `tests/visual_semantics_fixtures.py`
- Test: `tests/test_linear_algebra_visual_contracts.py`

**Interfaces:**
- Consumes: `TeachingArtifact`, catalog topic IDs, and semantic graph IDs.
- Produces: `VisualContract`, `ContractIssue`, `contract_for(topic_id)`, and `validate_contract(artifact, contract)`.

- [x] **Step 1: Write failing contract fixture tests**

```python
def test_composition_contract_requires_two_paths_and_endpoint_difference() -> None:
    contract = contract_for("ch02.matrix.composition")
    assert contract.minimum_stage_count == 5
    assert {"composition_order", "endpoint_diff", "compare"} <= set(contract.required_relations)


def test_projection_contract_rejects_missing_residual() -> None:
    artifact = projection_artifact(with_residual=False)
    issues = validate_contract(artifact, contract_for("ch01.projection.definition"))
    assert "missing_entity_role" in {issue.code for issue in issues}
```

- [x] **Step 2: Run contract tests and verify missing module failure**

Run: `pytest tests/test_linear_algebra_visual_contracts.py -q`

Expected: FAIL because `contracts.py` is missing.

- [x] **Step 3: Implement explicit contracts and validation**

```python
@dataclass(frozen=True)
class VisualContract:
    topic_id: str
    required_claims: tuple[str, ...]
    required_entity_roles: tuple[str, ...]
    required_relations: tuple[str, ...]
    required_primitives: tuple[str, ...]
    minimum_stage_count: int
    required_invariants: tuple[str, ...] = ()
    distinguishable_role_groups: tuple[tuple[str, ...], ...] = ()


def validate_contract(artifact: TeachingArtifact, contract: VisualContract) -> tuple[ContractIssue, ...]:
    actual_claims = {claim.id for claim in artifact.claims}
    roles = {entity.role for entity in artifact.visual_semantics.entities}
    relations = {relation.kind for relation in artifact.visual_semantics.relations}
    primitives = set(artifact.visual_semantics.primitives)
    issues = _missing_contract_values(contract, actual_claims, roles, relations, primitives)
    if len(artifact.visual_semantics.stages) < contract.minimum_stage_count:
        issues.append(ContractIssue("insufficient_stages", contract.topic_id, "stages"))
    return tuple(issues)
```

Start with full contracts for projection, transformed grid, matrix composition, null space, determinant multiplicativity, cross product, and inverse undo. Define a conservative base contract for the remaining topic IDs so all 54 resolve explicitly.

- [x] **Step 4: Verify all 54 topics resolve a contract**

Run: `pytest tests/test_linear_algebra_visual_contracts.py tests/test_linear_algebra_catalog.py -q`

Expected: PASS with no title-based contract inference.

- [x] **Step 5: Commit visual contracts**

```bash
git add linear_algebra/visualizations/contracts.py tests/visual_semantics_fixtures.py tests/test_linear_algebra_visual_contracts.py
git commit -m "feat: define topic visual contracts"
```

<!-- openspec-task: 4.2 -->
### Task 2: Add the Visual Semantics Compiler Boundary

**Files:**
- Create: `linear_algebra/visualizations/compiler.py`
- Modify: `linear_algebra/visualizations/common.py`
- Test: `tests/test_linear_algebra_visual_compiler.py`

**Interfaces:**
- Consumes: `TeachingArtifact.visual_semantics`, `VisualContract`, and `RenderContext`.
- Produces: `CompiledVisualization`, `VisualCompileError`, and `VisualSemanticsCompiler.compile(...)`.

- [ ] **Step 1: Write compiler boundary and no-render tests**

```python
class RejectingHost:
    def apply_scene_command(self, operation):
        raise AssertionError("compiler must not render")


def test_compiler_returns_validated_plan_without_rendering() -> None:
    artifact = composition_artifact()
    compiled = VisualSemanticsCompiler().compile(
        artifact.visual_semantics,
        contract_for(artifact.topic_id),
        RenderContext.default(artifact.topic_id),
    )
    assert compiled.plan.scene == "2d"
    assert SceneCommandService().validate(compiled.plan).valid is True
```

- [ ] **Step 2: Run the compiler test and verify missing compiler failure**

Run: `pytest tests/test_linear_algebra_visual_compiler.py -q`

Expected: FAIL because `VisualSemanticsCompiler` is missing.

- [ ] **Step 3: Implement validation-first compilation**

```python
@dataclass(frozen=True)
class CompiledVisualization:
    topic_id: str
    compiler_version: str
    render_profile: str
    plan: CommandPlan
    plan_digest: str
    evidence: tuple[CompiledEvidence, ...]


class VisualSemanticsCompiler:
    VERSION = "visual-semantics-v1"

    def compile(self, semantics, contract, context) -> CompiledVisualization:
        issues = validate_contract_semantics(semantics, contract)
        if issues:
            raise VisualCompileError(contract.topic_id, issues)
        operations, evidence = self._compile_graph(semantics, context)
        plan = CommandPlan(scene=semantics.scene, operations=tuple((*operations, {"op": "view.fit", "padding": 1.15})), summary=semantics.title)
        result = SceneCommandService().validate(plan)
        if not result.valid:
            raise VisualCompileError(contract.topic_id, result.messages)
        digest = digest_plan(plan, self.VERSION, context.render_profile)
        return CompiledVisualization(contract.topic_id, self.VERSION, context.render_profile, plan, digest, evidence)
```

Add `render_profile: str = "lecture-v1"` to `RenderContext`. The compiler may instantiate a validator without a host; it must not call execute/apply.

- [ ] **Step 4: Verify compiler and scene-command tests**

Run: `pytest tests/test_linear_algebra_visual_compiler.py tests/test_scene_commands.py -q`

Expected: PASS; invalid semantics fails before any host call.

- [ ] **Step 5: Commit compiler boundary**

```bash
git add linear_algebra/visualizations/compiler.py linear_algebra/visualizations/common.py tests/test_linear_algebra_visual_compiler.py
git commit -m "feat: add visual semantics compiler"
```

<!-- openspec-task: 4.3 -->
### Task 3: Track Claim Evidence Through Compilation

**Files:**
- Create: `linear_algebra/visualizations/evidence.py`
- Modify: `linear_algebra/visualizations/compiler.py`
- Test: `tests/test_linear_algebra_visual_evidence.py`

**Interfaces:**
- Consumes: claim/entity/relation/stage references and emitted operation aliases.
- Produces: `EvidenceLedger`, `CompiledEvidence`, and `validate_compiled_evidence(contract, ledger)`.

- [ ] **Step 1: Write missing endpoint/residual evidence tests**

```python
def test_composition_with_one_compiled_path_fails_evidence_check() -> None:
    ledger = composition_ledger(include_ba_path=False)
    issues = validate_compiled_evidence(contract_for("ch02.matrix.composition"), ledger)
    assert any(issue.code == "claim_evidence_not_visible" for issue in issues)


def test_projection_evidence_locates_foot_and_residual_aliases() -> None:
    compiled = compile_projection_fixture()
    evidence = next(item for item in compiled.evidence if item.claim_id == "claim.residual-orthogonal")
    assert {"projection_foot", "projection_residual"} <= set(evidence.operation_aliases)
```

- [ ] **Step 2: Run evidence tests and verify failure**

Run: `pytest tests/test_linear_algebra_visual_evidence.py -q`

Expected: FAIL because the evidence ledger does not exist.

- [ ] **Step 3: Implement alias-level evidence tracking**

```python
@dataclass(frozen=True)
class CompiledEvidence:
    claim_id: str
    entity_ids: tuple[str, ...]
    relation_ids: tuple[str, ...]
    stage_ids: tuple[str, ...]
    operation_aliases: tuple[str, ...]


class EvidenceLedger:
    def __init__(self) -> None:
        self._aliases: dict[str, set[str]] = defaultdict(set)

    def record(self, semantic_id: str, *operation_aliases: str) -> None:
        self._aliases[semantic_id].update(operation_aliases)

    def evidence_for(self, claim: Claim) -> CompiledEvidence:
        ids = (*claim.entity_refs, *claim.relation_refs, *claim.stage_refs)
        aliases = sorted({alias for semantic_id in ids for alias in self._aliases.get(semantic_id, ())})
        return CompiledEvidence(claim.id, claim.entity_refs, claim.relation_refs, claim.stage_refs, tuple(aliases))
```

Compilation helpers must record the exact aliases they emit. Contract validation fails when a required claim has no visible aliases or a distinguishable group collapses to one alias.

- [ ] **Step 4: Run evidence and compiler tests**

Run: `pytest tests/test_linear_algebra_visual_evidence.py tests/test_linear_algebra_visual_compiler.py -q`

Expected: PASS.

- [ ] **Step 5: Commit claim evidence tracking**

```bash
git add linear_algebra/visualizations/evidence.py linear_algebra/visualizations/compiler.py tests/test_linear_algebra_visual_evidence.py
git commit -m "feat: track compiled claim evidence"
```

<!-- openspec-task: 4.4 -->
### Task 4: Map Semantic Primitives to Existing Scene Operations

**Files:**
- Modify: `linear_algebra/visualizations/compiler.py`
- Modify: `linear_algebra/visualizations/builders/primitives.py`
- Test: `tests/test_linear_algebra_semantic_primitives.py`

**Interfaces:**
- Consumes: validated primitives `grid_transform`, `subspace_span`, `projection_bundle`, `batch_mapping`, `staged_transform`, `signed_area`, `volume_orientation`, and `orientation_marker`.
- Produces: deterministic operation tuples accepted by `SceneCommandService`.

- [ ] **Step 1: Write golden operation tests for every primitive**

```python
@pytest.mark.parametrize(("fixture_name", "required_ops"), [
    ("grid_transform", {"geometry.transformed_grid", "linear.upsert"}),
    ("subspace_span", {"geometry.subspace_region"}),
    ("projection_bundle", {"geometry.projection", "geometry.right_angle_marker"}),
    ("staged_transform", {"geometry.staged_transform"}),
    ("signed_area", {"geometry.oriented_area", "annotation.formula"}),
    ("volume_orientation", {"geometry.parallelepiped", "geometry.oriented_volume"}),
])
def test_semantic_primitive_emits_required_ops(fixture_name, required_ops) -> None:
    plan = compile_semantic_fixture(fixture_name).plan
    assert required_ops <= {operation["op"] for operation in plan.operations}
```

- [ ] **Step 2: Run primitive tests and verify unsupported mappings fail**

Run: `pytest tests/test_linear_algebra_semantic_primitives.py -q`

Expected: FAIL because primitive dispatch is incomplete.

- [ ] **Step 3: Implement one explicit compiler per primitive**

```python
PrimitiveCompiler = Callable[[VisualSemantics, SemanticPrimitive, LayoutFrame, EvidenceLedger], list[dict[str, object]]]


_PRIMITIVE_COMPILERS: dict[str, PrimitiveCompiler] = {
    "grid_transform": _compile_grid_transform,
    "subspace_span": _compile_subspace_span,
    "projection_bundle": _compile_projection_bundle,
    "batch_mapping": _compile_batch_mapping,
    "staged_transform": _compile_staged_transform,
    "signed_area": _compile_signed_area,
    "volume_orientation": _compile_volume_orientation,
    "orientation_marker": _compile_orientation_marker,
}


def _compile_projection_bundle(semantics, primitive, frame, ledger):
    operations: list[dict[str, object]] = []
    for index, input_id in enumerate(primitive.input_ids):
        vector = semantics.entity(input_id).vector2()
        alias = frame.alias(f"projection-{index}")
        operations.append(make_projection(vector, semantics.entity(primitive.direction_id).vector2(), alias=alias))
        ledger.record(input_id, alias, f"{alias}_result", f"{alias}_foot", f"{alias}_residual")
    return operations
```

Use current commands where they preserve the required evidence. Add a builder helper before considering a new scene operation. Each helper receives resolved numeric values, never formula strings.

- [ ] **Step 4: Validate all golden plans through the scene service**

Run: `pytest tests/test_linear_algebra_semantic_primitives.py tests/test_linear_algebra_capabilities.py tests/test_scene_commands.py -q`

Expected: PASS; every golden plan is valid and contains the asserted relationship operations.

- [ ] **Step 5: Commit semantic primitive mappings**

```bash
git add linear_algebra/visualizations/compiler.py linear_algebra/visualizations/builders/primitives.py tests/test_linear_algebra_semantic_primitives.py
git commit -m "feat: compile teaching semantic primitives"
```

<!-- openspec-task: 4.5 -->
### Task 5: Compile Static Storyboard Layouts

**Files:**
- Create: `linear_algebra/visualizations/layout.py`
- Modify: `linear_algebra/visualizations/compiler.py`
- Test: `tests/test_linear_algebra_storyboard_layout.py`

**Interfaces:**
- Consumes: stage list, semantic layout, scene bounds, and seed.
- Produces: `LayoutFrame`, `StoryboardLayout`, and `layout_storyboard(...)`.

- [ ] **Step 1: Write layout and alias isolation tests**

```python
def test_side_by_side_composition_has_disjoint_frames_and_aliases() -> None:
    layout = layout_storyboard(composition_artifact().visual_semantics, RenderContext.default("ch02.matrix.composition"))
    left, right = layout.frames
    assert left.bounds[1] < right.bounds[0]
    assert left.alias("x") != right.alias("x")


def test_sequence_layout_preserves_stage_order() -> None:
    layout = layout_storyboard(projection_artifact().visual_semantics, RenderContext.default("ch01.projection.definition"))
    assert [frame.stage_id for frame in layout.frames] == ["input", "projection", "residual"]
```

- [ ] **Step 2: Run layout tests and verify missing layout failure**

Run: `pytest tests/test_linear_algebra_storyboard_layout.py -q`

Expected: FAIL because `layout.py` is missing.

- [ ] **Step 3: Implement deterministic frames for three layouts**

```python
@dataclass(frozen=True)
class LayoutFrame:
    stage_id: str
    namespace: str
    bounds: tuple[float, float, float, float]
    offset: tuple[float, float]

    def alias(self, semantic_id: str) -> str:
        return f"{self.namespace}__{semantic_id}"


def layout_storyboard(semantics, context) -> StoryboardLayout:
    if semantics.layout == "side_by_side":
        return _side_by_side(semantics.stages, context.bounds)
    if semantics.layout == "sequence":
        return _sequence(semantics.stages, context.bounds)
    if semantics.layout == "overlay":
        return _overlay(semantics.stages, context.bounds)
    raise LayoutError(semantics.layout)
```

Stage titles compile to `annotation.formula` using namespaced aliases. `overlay` shares bounds but retains stage-specific aliases; `sequence` records order even if the current renderer shows one stage at a time.

- [ ] **Step 4: Run layout, evidence, and compiler tests**

Run: `pytest tests/test_linear_algebra_storyboard_layout.py tests/test_linear_algebra_visual_evidence.py tests/test_linear_algebra_visual_compiler.py -q`

Expected: PASS.

- [ ] **Step 5: Commit storyboard layout**

```bash
git add linear_algebra/visualizations/layout.py linear_algebra/visualizations/compiler.py tests/test_linear_algebra_storyboard_layout.py
git commit -m "feat: compile static teaching storyboards"
```

<!-- openspec-task: 4.6 -->
### Task 6: Make Layout and Plan Digests Deterministic

**Files:**
- Modify: `linear_algebra/visualizations/common.py`
- Modify: `linear_algebra/visualizations/layout.py`
- Modify: `linear_algebra/visualizations/compiler.py`
- Test: `tests/test_linear_algebra_visual_determinism.py`

**Interfaces:**
- Consumes: `RenderContext(topic_id, bounds, seed, render_profile)`.
- Produces: stable operation aliases/coordinates and `digest_plan(...) -> str`.

- [ ] **Step 1: Write determinism and overflow tests**

```python
def test_same_artifact_and_context_have_same_plan_digest() -> None:
    first = compile_composition(seed=17)
    second = compile_composition(seed=17)
    assert first.plan.to_dict() == second.plan.to_dict()
    assert first.plan_digest == second.plan_digest


def test_layout_overflow_fails_instead_of_clipping() -> None:
    with pytest.raises(LayoutError, match="out_of_bounds"):
        compile_oversized_storyboard(bounds=(-1.0, 1.0, -1.0, 1.0))
```

- [ ] **Step 2: Run determinism tests and verify failure**

Run: `pytest tests/test_linear_algebra_visual_determinism.py -q`

Expected: FAIL because plan digest/render profile and overflow checks are absent.

- [ ] **Step 3: Implement canonical plan hashing and bounds checks**

```python
def digest_plan(plan: CommandPlan, compiler_version: str, render_profile: str) -> str:
    payload = {
        "compiler_version": compiler_version,
        "render_profile": render_profile,
        "plan": plan.to_dict(),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def assert_frame_contains(frame: LayoutFrame, points: Iterable[tuple[float, float]]) -> None:
    xmin, xmax, ymin, ymax = frame.bounds
    if any(not (xmin <= x <= xmax and ymin <= y <= ymax) for x, y in points):
        raise LayoutError("out_of_bounds")
```

Use a local `random.Random(context.seed)` only for approved parameterized samples; never use global randomness.

- [ ] **Step 4: Verify deterministic compilation**

Run: `pytest tests/test_linear_algebra_visual_determinism.py tests/test_linear_algebra_storyboard_layout.py -q`

Expected: PASS with byte-identical plan dictionaries for identical inputs.

- [ ] **Step 5: Commit deterministic compilation**

```bash
git add linear_algebra/visualizations/common.py linear_algebra/visualizations/layout.py linear_algebra/visualizations/compiler.py tests/test_linear_algebra_visual_determinism.py
git commit -m "feat: make teaching plans deterministic"
```

<!-- openspec-task: 4.7 -->
### Task 7: Centralize Teaching Role Colors

**Files:**
- Create: `linear_algebra/visualizations/palette.py`
- Modify: `linear_algebra/visualizations/compiler.py`
- Modify: `linear_algebra/visualizations/builders/primitives.py`
- Test: `tests/test_linear_algebra_teaching_palette.py`

**Interfaces:**
- Consumes: semantic teaching roles.
- Produces: `TEACHING_PALETTE`, `role_color(role)`, and `RoleResolution` diagnostics.

- [ ] **Step 1: Write shared role and fallback tests**

```python
def test_known_role_is_stable_across_compiled_stages() -> None:
    compiled = compile_composition(seed=17)
    assert compiled.role_colors["vector_a"] == role_color("vector_a").color
    assert all("semantic_role" not in operation for operation in compiled.plan.operations)


def test_unknown_role_uses_neutral_with_diagnostic() -> None:
    resolution = role_color("unknown-role")
    assert resolution.color == TEACHING_PALETTE["neutral"]
    assert resolution.diagnostic == "unknown-role"
```

- [ ] **Step 2: Run palette tests and verify missing palette failure**

Run: `pytest tests/test_linear_algebra_teaching_palette.py -q`

Expected: FAIL because `palette.py` is missing.

- [ ] **Step 3: Implement the single palette and compiler resolution**

```python
TEACHING_PALETTE = MappingProxyType({
    "vector_a": "#2f80ed",
    "vector_b": "#27ae60",
    "basis_e1": "#2f80ed",
    "basis_e2": "#27ae60",
    "transformed_a": "#9b51e0",
    "transformed_b": "#f2994a",
    "area": "#f2c94c",
    "projection": "#56ccf2",
    "residual": "#eb5757",
    "neutral": "#828282",
})


def role_color(role: str) -> RoleResolution:
    color = TEACHING_PALETTE.get(role)
    return RoleResolution(color or TEACHING_PALETTE["neutral"], None if color else role)
```

Add `role_colors: Mapping[str, str]` to `CompiledVisualization`. Resolve every used role before operation construction, put only the resolved color in scene operations, and retain the role-to-color map in the compiled result for claim highlighting and diagnostics. Move teaching hex literals from `linear_algebra/visualizations/` helpers into this module; do not extend the scene command protocol with teaching metadata.

- [ ] **Step 4: Verify no teaching colors remain outside palette**

Run: `pytest tests/test_linear_algebra_teaching_palette.py tests/test_linear_algebra_semantic_primitives.py -q`

Run: `rg -n '#[0-9A-Fa-f]{6}' linear_algebra/visualizations -g '*.py'`

Expected: tests PASS; matches are limited to `palette.py`.

- [ ] **Step 5: Commit the teaching palette**

```bash
git add linear_algebra/visualizations/palette.py linear_algebra/visualizations/compiler.py linear_algebra/visualizations/builders/primitives.py tests/test_linear_algebra_teaching_palette.py
git commit -m "feat: centralize teaching role colors"
```

<!-- openspec-task: 4.8 -->
### Task 8: Remove the Capability-Only Rendering Path

**Files:**
- Modify: `linear_algebra/visualizations/common.py`
- Modify: `linear_algebra/visualizations/__init__.py`
- Modify: `linear_algebra/visualizations/chapter_01.py`
- Modify: `linear_algebra/visualizations/chapter_02.py`
- Modify: `linear_algebra/visualizations/chapter_03.py`
- Modify: `tests/teaching_fixtures.py`
- Test: `tests/test_linear_algebra_recipes.py`
- Test: `tests/test_linear_algebra_visual_compiler_coverage.py`

**Interfaces:**
- Consumes: `TeachingArtifact`, topic contract, render context, and `VisualSemanticsCompiler`.
- Produces: one recipe path that compiles artifact semantics; removes `_build_plan`, `_two_d_geometry`, `_three_d_geometry`, and `_formula_for`.

- [ ] **Step 1: Write a failing no-fallback coverage test**

```python
def test_every_recipe_uses_visual_semantics_compiler(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(VisualSemanticsCompiler, "compile", recording_compile(calls))
    for topic in topic_entries():
        recipe_for(topic.visualization_id).build(
            RenderContext.default(topic.id),
            artifact_fixture_for(topic.id),
        )
    assert calls == [topic.id for topic in topic_entries()]


def test_common_module_has_no_capability_plan_builder() -> None:
    source = Path("linear_algebra/visualizations/common.py").read_text(encoding="utf-8")
    assert "def _build_plan" not in source
    assert "def _formula_for" not in source
```

- [ ] **Step 2: Run recipe coverage and verify current fallback failure**

Run: `pytest tests/test_linear_algebra_visual_compiler_coverage.py tests/test_linear_algebra_recipes.py -q`

Expected: FAIL until recipes consistently resolve artifact semantics through the compiler.

- [ ] **Step 3: Replace builder callables with artifact-aware compilation**

```python
@dataclass(frozen=True)
class VisualizationRecipe:
    id: str
    topic_id: str
    scene: Literal["2d", "3d"]
    required_capabilities: tuple[str, ...]

    def build(self, context: RenderContext, artifact: TeachingArtifact) -> CompiledVisualization:
        return VisualSemanticsCompiler().compile(
            artifact.visual_semantics,
            contract_for(self.topic_id),
            context,
        )
```

Implement `artifact_fixture_for(topic_id)` as test-only schema-valid semantics derived from the topic's visual contract, so this task does not depend on the published chapter resources created in Tasks 5.1-5.3. Update every recipe caller to pass an artifact explicitly, delete the old builder callables, and remove the four private generic helpers after all imports are updated.

- [ ] **Step 4: Run all plan-3 tests and validation**

Run: `pytest tests/test_linear_algebra_visual_contracts.py tests/test_linear_algebra_visual_compiler.py tests/test_linear_algebra_visual_evidence.py tests/test_linear_algebra_semantic_primitives.py tests/test_linear_algebra_storyboard_layout.py tests/test_linear_algebra_visual_determinism.py tests/test_linear_algebra_teaching_palette.py tests/test_linear_algebra_visual_compiler_coverage.py tests/test_linear_algebra_recipes.py -q`

Run: `python -m linear_algebra.validation`

Expected: tests PASS and validation reports 54 topics validated.

- [ ] **Step 5: Commit the single rendering path**

```bash
git add linear_algebra/visualizations tests/test_linear_algebra_recipes.py tests/test_linear_algebra_visual_compiler_coverage.py
git commit -m "refactor: require semantic teaching compilation"
```
