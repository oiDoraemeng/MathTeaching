# Linear Algebra Visualization Repair Plan

**Related change:** `expand-linear-algebra-lecture-tree`
**Validated:** 2026-09-02
**Scope:** repair the executed topic-builder redesign; keep the lecture tree and explanation contract unchanged.

## Verification Findings

The previous repair plan was not executable as written:

- It specified `annotation.label`, but the command protocol exposes `annotation.formula` and `annotation.upsert` only.
- It used presentation roles `secondary` and `auxiliary`, while `linear.upsert` and `linear3d.upsert` accept only `primary`, `construction`, and `result`.
- It counted Chapter 2 and Chapter 3 as 16 and 14 topics. The catalog contains 24 + 15 + 15 = 54 topics.
- It proposed a generic-builder fallback, which conflicts with the project decision to remove compatibility paths.
- It treated popup visibility as the linear-algebra context. The popup is owned by `AlgebraPanel` and closes after topic selection, so this made the toolbar permanently hidden.
- It did not include a regression check that builds and validates every topic before execution.

The failure was reproduced with `python -m linear_algebra.validation` and the focused pytest suite. Before repair, 53 topic plans were invalid and topic loading raised `CommandError`.

## Corrected Plan

### 1. Command-compatible primitives [x]

- Normalize `secondary` and `auxiliary` to the protocol role `construction` at the primitive boundary.
- Emit labels as `annotation.formula` with a stable alias and position.
- Keep geometry operation names and required fields aligned with `SceneCommandService`.
- Do not add a generic fallback for missing builders.

### 2. Dimension-correct topic builders [x]

- Chapter 1: 24 builders. Topics requiring 3D (`coordinate-system`, `velocity`, `cross-product`, `scalar-triple`, `high-dimensional.analogy`) emit only 3D operations.
- Chapter 2: 15 builders, all matching the catalog IDs.
- Chapter 3: 15 builders. `high-dimensional-volume` emits 3D vectors and an oriented volume plan.
- Every builder returns a deterministic `CommandPlan` ending in `view.fit`.

### 3. Explicit UI context [x]

- Track `_active_linear_algebra_topic_id` only after the clear-and-load transaction succeeds.
- Clear that state on `scene.clear(scope="all")`.
- Show the horizontal toolbar only when the active recipe is 2D; leave the normal geometry toolbar available otherwise.
- Keep topic loading and the `math_case` explanation event unchanged.

### 4. Required verification [x]

Run all of the following from the repository root:

```text
python -m linear_algebra.validation
python -m pytest tests/test_linear_algebra_builders.py tests/test_linear_algebra_recipes.py tests/test_linear_algebra_registry.py tests/test_linear_algebra_loading.py -q
openspec validate expand-linear-algebra-lecture-tree --strict
```

The first command must report `54 topics validated`; the focused suite must pass; the strict OpenSpec validator must exit successfully.

### 5. Toolbar interaction completion [x]

The six linear-algebra-specific buttons (`angle`, `projection`, `polygon`, `transform`, `subspace`, `area`) now have canvas interaction handlers. Basic tools reuse the existing point/vector workflow; the six specialized tools create validated command plans and explanatory annotations. Planning and mathematical text are isolated in `ui/linear_algebra_tools.py`; drawing actors use namespaced aliases and can be cleared without touching lecture-provided overlays. Focused tests cover vector selection, polygon double-click completion, matrix parsing, transform aliases, Escape cancellation, and overlay isolation.

## Acceptance Criteria

- All 54 topic builders are registered, deterministic, dimension-correct, and accepted by `SceneCommandService.validate`.
- Selecting any leaf topic clears and loads one validated plan, then opens its mathematical explanation.
- A 2D topic shows the linear-algebra toolbar after the popup closes; a 3D topic does not show a 2D toolbar.
- No `annotation.label`, `secondary`, `auxiliary`, or generic-builder fallback remains in executable builder output.
- Toolbar interaction work is tracked separately and is not described as complete until its handlers and tests exist.
