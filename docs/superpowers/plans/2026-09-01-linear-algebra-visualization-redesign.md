# Linear Algebra Visualization System Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace generic template-based visualization system with 54 topic-specific builders and add horizontal linear algebra toolbar with 6 new tools.

**Architecture:** Three-layer builder system: (1) Primitive builders (reusable geometry), (2) Topic builders (compose primitives), (3) Builder registry (map topic ID → builder function). Horizontal toolbar at top-left.

**Tech Stack:** Python 3.11, PySide6, pytest

**Spec:** `docs/superpowers/specs/2026-09-01-linear-algebra-visualization-redesign.md`

## Global Constraints

- Python 3.11+
- TDD: write test first, then implementation
- Commit after each task
- All 54 topics must have builders
- Coordinates chosen for teaching clarity
- Toolbar: top-left, 32×32px buttons, 4px spacing, 12px group spacing

---

## Implementation Notes

**Builder Pattern:**
All 54 builders follow the same structure:
1. Define coordinates for clear visualization
2. Use primitive helpers (make_vector_2d, make_label, etc.)
3. Return CommandPlan with operations tuple

**Topic IDs from catalog:**
- Chapter 1: 24 topics (ch01.vector.*, ch01.ops.*, ch01.inner.*, ch01.projection.*, ch01.proof.*)
- Chapter 2: 16 topics (ch02.batch.*, ch02.matrix.*, ch02.subspace.*)
- Chapter 3: 14 topics (ch03.det.*, ch03.cramer.*, ch03.inverse.*)

See `linear_algebra/catalog/chapter_*.py` for complete topic lists and IDs.

---

## Tasks

### Task 1: Infrastructure - Primitives and Math Utils

Create builder infrastructure with primitives, math utilities, and registry.

**Files:**
- Create: `linear_algebra/visualizations/builders/__init__.py`
- Create: `linear_algebra/visualizations/builders/primitives.py`
- Create: `linear_algebra/visualizations/builders/math_utils.py`
- Create: `tests/test_linear_algebra_builders.py`

**Implementation:** See spec sections "Primitive Builders API" and "Math Utilities" for complete function signatures. Implement:
- Registry: `get_builder_for()`, `register_builders()`
- Math: `dot_product()`, `project_vector()`, `angle_between()`, `cross_product()`
- 2D primitives: `make_vector_2d()`, `make_label()`, `make_polygon()`, `make_angle_arc()`, `make_projection()`, `make_right_angle_marker()`
- 3D primitives: `make_vector_3d()`, `make_plane_3d()`, `make_parallelepiped()`
- Common: `make_view_fit()`

**Testing:** Write unit tests for math utilities and primitive builders.

**Commit:** `feat: add visualization builder infrastructure`

---

### Task 2: Update Common.py

Update `recipe_for_entry()` to use builder registry instead of generic templates.

**Files:**
- Modify: `linear_algebra/visualizations/common.py`

**Changes:**
Replace `_build_plan()` logic with:
```python
from .builders import get_builder_for

builder_func = get_builder_for(entry.visualization_id)
if builder_func is None:
    raise ValueError(f"No builder found for {entry.visualization_id}")
```

**Testing:** Verify raises ValueError for missing builders.

**Commit:** `feat: update recipe_for_entry to use builder registry`

---

### Task 3: Chapter 1 Builders (Vectors and Operations)

Implement all 24 Chapter 1 builders.

**Files:**
- Create: `linear_algebra/visualizations/builders/chapter_01.py`

**Builder Template:**
```python
def build_<topic>(context: RenderContext) -> CommandPlan:
    """<Chinese title>"""
    # Define coordinates
    # Use primitives to build operations
    # Return CommandPlan
```

**Topics to implement:**
1. `build_vector_magnitude` - ch01.vector.magnitude
2. `build_vector_point_distinction` - ch01.vector.point-distinction
3. `build_vector_coordinate_system` - ch01.vector.coordinate-system  
4. `build_vector_direction_examples` - ch01.vector.direction-examples
5. `build_vector_addition` - ch01.ops.addition
6. `build_vector_subtraction` - ch01.ops.subtraction
7. `build_vector_scalar` - ch01.ops.scalar
8. `build_linear_combination` - ch01.ops.linear-combination
9. `build_velocity_composition` - ch01.ops.velocity
10. `build_cross_product` - ch01.ops.cross-product (3D)
11. `build_scalar_triple_product` - ch01.ops.scalar-triple (3D)
12. `build_inner_product_equivalence` - ch01.inner.equivalence
13. `build_inner_product_definitions` - ch01.inner.definitions
14. `build_inner_product_applications` - ch01.inner.applications
15. `build_cauchy_schwarz` - ch01.inner.cauchy-schwarz
16. `build_inner_product_examples` - ch01.inner.examples
17. `build_projection_definition` - ch01.projection.definition
18. `build_projection_properties` - ch01.projection.properties
19. `build_projection_force` - ch01.projection.force
20. `build_proof_method` - ch01.proof.method
21. `build_midline_theorem` - ch01.proof.midline
22. `build_centroid_theorem` - ch01.proof.centroid
23. `build_parallelogram_diagonals` - ch01.proof.parallelogram-diagonals
24. `build_high_dimensional_analogy` - ch01.high-dimensional.analogy

**Registry:** Create `BUILDERS` dict mapping all 24 visualization IDs to functions.

**Testing:** Write representative test for `build_vector_addition` (verify ≥3 vectors, ≥3 labels, polygon, view.fit).

**Register:** Add `from .chapter_01 import BUILDERS as CHAPTER_01_BUILDERS` and `register_builders(CHAPTER_01_BUILDERS)` to `builders/__init__.py`

**Commit:** `feat: implement all 24 Chapter 1 visualization builders`

---

### Task 4: Chapter 2 Builders (Matrices and Transformations)

Implement all 16 Chapter 2 builders.

**Files:**
- Create: `linear_algebra/visualizations/builders/chapter_02.py`

**Topics to implement:**
1. `build_batch_inner_products` - ch02.batch.inner-products
2. `build_batch_projection` - ch02.batch.projection
3. `build_matrix_additive_distributivity` - ch02.matrix.additive-distributivity
4. `build_matrix_row_column` - ch02.matrix.row-column
5. `build_transformed_grid` - ch02.matrix.transformed-grid
6. `build_stretch_rotate_scale` - ch02.matrix.stretch-rotate-scale
7. `build_matrix_composition` - ch02.matrix.composition
8. `build_matrix_basis` - ch02.matrix.basis
9. `build_matrix_powers` - ch02.matrix.powers
10. `build_subspace_independence` - ch02.subspace.independence
11. `build_subspace_rank` - ch02.subspace.rank
12. `build_subspace_null` - ch02.subspace.null
13. `build_subspace_column` - ch02.subspace.column
14. `build_subspace_rank_nullity` - ch02.subspace.rank-nullity
15. `build_high_dimensional_matrix_analogy` - ch02.high-dimensional.analogy

**Key geometries:**
- Use `make_transformed_grid()` for matrix transformations (not a primitive - generate grid transformation ops manually)
- Use `make_polygon()` for subspace regions
- Use `make_vector_2d()` for basis vectors

**Testing:** Write representative test for `build_transformed_grid`.

**Register:** Add to `builders/__init__.py`

**Commit:** `feat: implement all 16 Chapter 2 visualization builders`

---

### Task 5: Chapter 3 Builders (Determinants)

Implement all 14 Chapter 3 builders.

**Files:**
- Create: `linear_algebra/visualizations/builders/chapter_03.py`

**Topics to implement:**
1. `build_oriented_area` - ch03.det.oriented-area
2. `build_ad_bc_decomposition` - ch03.det.ad-bc
3. `build_det_sign_zero_one` - ch03.det.sign-zero-one
4. `build_det_examples` - ch03.det.examples
5. `build_det_row_swap` - ch03.det.row-swap
6. `build_det_scaling` - ch03.det.scaling
7. `build_det_shear` - ch03.det.shear
8. `build_det_multiplicativity` - ch03.det.multiplicativity
9. `build_cramer_area_ratio` - ch03.cramer.area-ratio
10. `build_inverse_undo` - ch03.inverse.undo
11. `build_inverse_formula` - ch03.inverse.formula
12. `build_inverse_examples` - ch03.inverse.examples
13. `build_det_zero_equivalence` - ch03.det.zero.equivalence
14. `build_det_high_dimensional_volume` - ch03.det.high-dimensional-volume
15. `build_inverse_reverse_order` - ch03.inverse.reverse-order

**Key geometries:**
- Generate oriented area ops manually (parallelogram with signed area annotation)
- Use `make_polygon()` for areas
- Show transformation sequences with multiple grid states

**Testing:** Write representative test for `build_oriented_area`.

**Register:** Add to `builders/__init__.py`

**Commit:** `feat: implement all 14 Chapter 3 visualization builders`

---

### Task 6: Horizontal Toolbar Component

Create new horizontal toolbar component with 6 linear algebra tools.

**Files:**
- Create: `ui/linear_algebra_toolbar.py`
- Create: `tests/test_linear_algebra_toolbar.py`

**Component API:**
```python
class LinearAlgebraToolbar(QWidget):
    # Signals
    tool_selected = Signal(str)
    undo_requested = Signal()
    redo_requested = Signal()
    
    def __init__(self, parent, theme="light"):
        # Create tool buttons (select, point, vector, angle, projection, polygon, transform, subspace, area)
        # Create undo/redo buttons
        # Set up horizontal layout
        # Apply styling (32x32px, 4px spacing, 12px group spacing)
    
    def set_active_tool(self, tool: str) -> None: ...
    def set_theme(self, theme: str) -> None: ...
    def position_in_host(self) -> None: ...  # Position at top-left, 12px from edges
```

**Styling:**
- Horizontal `QHBoxLayout`
- 32×32px `QToolButton` size
- 4px spacing between tools
- 12px spacing between groups
- Semi-transparent background with theme-aware color
- Drop shadow for depth

**Testing:**
- Test toolbar creation
- Test tool selection signals
- Test theme switching

**Commit:** `feat: add horizontal linear algebra toolbar component`

---

### Task 7: Toolbar Integration

Integrate toolbar into designer window.

**Files:**
- Modify: `ui/designer_window.py`

**Changes:**
1. Import `LinearAlgebraToolbar`
2. Create toolbar instance: `self.linear_algebra_toolbar = LinearAlgebraToolbar(self.canvas_2d, theme=self._theme)`
3. Position at top-left: Call `toolbar.position_in_host()` on resize
4. Connect signals to existing 2D scene interaction handlers
5. Hide/show based on scene type
6. Optional: Hide old vertical toolbar (`two_d_tools.py`) or keep as fallback

**Testing:**
- Manual: Verify toolbar appears at top-left
- Manual: Verify tool selection works
- Manual: Verify theme switching works

**Commit:** `feat: integrate horizontal toolbar into designer window`

---

### Task 8: Comprehensive Testing

Run all tests and perform manual verification.

**Unit Tests:**
Run: `pytest tests/test_linear_algebra_builders.py -v`
Expected: All tests PASS

**Integration Test:**
Create test script to verify all 54 builders:
```python
from linear_algebra.catalog.manifest import topic_entries
from linear_algebra.visualizations import recipe_for
from linear_algebra.visualizations.common import RenderContext

for entry in topic_entries():
    recipe = recipe_for(entry.visualization_id)
    context = RenderContext.default(entry.id)
    plan = recipe.builder(context)
    assert plan.scene in ("2d", "3d")
    assert len(plan.operations) > 0
    print(f"✓ {entry.id}")
```

**Manual Verification:**
For each of 54 topics:
- [ ] Load topic in application
- [ ] Verify geometry matches explanation
- [ ] Verify colors (primary/secondary/result/auxiliary)
- [ ] Verify labels clear and positioned well
- [ ] No clipping or overflow

**Toolbar Verification:**
- [ ] Toolbar at top-left
- [ ] All 9 tool buttons visible
- [ ] Tool selection toggles correctly
- [ ] Theme switching updates appearance

**Commit:** `test: verify all 54 builders and toolbar functionality`

---

### Task 9: Documentation

Update documentation for new system.

**Files:**
- Update: `openspec/changes/expand-linear-algebra-lecture-tree/README.md`
- Update: `openspec/changes/expand-linear-algebra-lecture-tree/verification.md`

**Changes:**
- Mark visualization system as FIXED
- Document builder architecture
- Update success criteria (all 54 topics correct)
- Remove "needs rework" warnings

**Commit:** `docs: update verification status - visualization system fixed`

---

## Execution Strategy

**Recommended:** Use `superpowers:subagent-driven-development` for iterative execution with review gates between tasks.

**Alternative:** Use `superpowers:executing-plans` for batch execution with periodic checkpoints.

**Estimated Time:** 10-11 days total
- Tasks 1-2: 1 day (infrastructure)
- Task 3: 2 days (Chapter 1 builders)
- Task 4: 2 days (Chapter 2 builders)
- Task 5: 1 day (Chapter 3 builders)
- Tasks 6-7: 2-3 days (toolbar)
- Tasks 8-9: 2 days (testing/docs)

---

## Success Criteria

- ✅ All 54 topics have specific builders
- ✅ All builders use primitive helpers (no code duplication)
- ✅ All visualizations mathematically correct
- ✅ Horizontal toolbar functional with 6 new tools
- ✅ No regression in tree UI or explanations
- ✅ Representative unit tests pass
- ✅ Manual verification complete

