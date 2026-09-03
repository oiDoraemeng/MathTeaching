# Linear Algebra Visualization System Redesign

**Date:** 2026-09-01  
**Status:** Approved  
**Related Change:** expand-linear-algebra-lecture-tree

> **Execution audit (2026-09-02):** The command path validates all 54 topic
> builders. The toolbar component and six canvas interaction handlers are
> implemented, with planning/math helpers isolated in `ui/linear_algebra_tools.py`.

## Problem Statement

Current visualization system uses capability-tag-based generic templates, causing ~40/54 topics (75%) to display incorrect geometry. The generic template approach cannot express topic-specific mathematical content.

**Current Architecture:**
```
Topic → Capabilities → Generic Template → CommandPlan
             ↑ Information loss here
```

**Root Cause:**
- All topics sharing ~8 hardcoded geometry templates
- No topic-specific vector coordinates or geometric relationships
- Capability tags (e.g., "vector_2d", "polygon_2d") trigger same fixed geometry

**Example Issues:**
- Vector addition: Expected a, b, a+b → Actual: one fixed vector + unrelated polygon
- Vector subtraction: Expected subtraction geometry → Actual: projection (completely wrong)
- Inner product: Expected two vectors with angle → Actual: one vector + angle arc with no second vector

## Solution Overview

**New Architecture:**
```
Topic → Topic-Specific Builder Function → CommandPlan
```

**Core Changes:**
1. Create 54 topic-specific builder functions (one per topic)
2. Implement reusable primitive builders to avoid code duplication
3. Add horizontal linear algebra toolbar (top-left corner) with 6 new tools
4. Update `recipe_for_entry()` to use topic-specific builders

**Scope:**
- ✅ All 54 topics (24 Chapter 1 + 15 Chapter 2 + 15 Chapter 3)
- ✅ 2D and 3D visualizations
- ✅ Horizontal toolbar with 6 linear algebra tools and canvas handlers
- ⏳ Representative unit tests + manual verification (command-level tests pass; visual review pending)

## Architecture Design

### 1. Module Structure

```
linear_algebra/visualizations/
├── __init__.py              # Registry exports
├── common.py                # VisualizationRecipe, updated recipe_for_entry()
├── builders/
│   ├── __init__.py         # Export all builders
│   ├── primitives.py       # Primitive builders (vectors, labels, projections)
│   ├── math_utils.py       # Math calculations (projection, angle, cross product)
│   ├── chapter_01.py       # 24 Chapter 1 builders
│   ├── chapter_02.py       # 15 Chapter 2 builders
│   └── chapter_03.py       # 15 Chapter 3 builders
├── chapter_01.py           # RECIPES tuple (unchanged)
├── chapter_02.py           # RECIPES tuple (unchanged)
└── chapter_03.py           # RECIPES tuple (unchanged)

ui/
├── linear_algebra_toolbar.py    # New horizontal toolbar (top-left)
├── linear_algebra_tools.py      # Independent toolbar math and plan builders
├── two_d_tools.py              # Keep existing (may become unused)
└── designer_window.py          # Update: integrate new toolbar
```

### 2. Layered Builder Architecture

**Three Layers:**

1. **Primitive Builders** - Reusable geometry building blocks
2. **Topic Builders** - Compose primitives into topic-specific visualizations
3. **Builder Registry** - Map visualization_id → builder function

**Example:**

```python
# builders/primitives.py - Primitive Layer
def make_vector_2d(start, end, alias, role="primary", style="solid"):
    """Create 2D vector (points + line segment)"""
    return [
        {"op": "point.upsert", "alias": f"{alias}_start", "coordinates": start},
        {"op": "point.upsert", "alias": f"{alias}_end", "coordinates": end},
        {"op": "linear.upsert", "alias": alias, "start": f"{alias}_start", 
         "end": f"{alias}_end", "kind": "vector", "role": role, "style": style},
    ]

def make_label(text, position, offset=[0, 0]):
    """Create text label"""
    return {
        "op": "annotation.formula",
        "alias": f"label_{text.replace(' ', '_')}",
        "text": text,
        "position": position,
    }

def make_polygon(vertices, color="#5b8def", opacity=0.15, outline=True):
    """Create polygon"""
    return {
        "op": "geometry.polygon",
        "alias": "polygon",
        "vertices": vertices,
        "color": color,
        "opacity": opacity,
        "outline": outline,
    }

# builders/chapter_01.py - Topic Layer
def build_vector_addition(context: RenderContext) -> CommandPlan:
    """向量加法：显示 a + b = c 的平行四边形法则"""
    a, b = [2.0, 1.0], [1.0, 2.0]
    c = [a[0] + b[0], a[1] + b[1]]  # [3.0, 3.0]
    
    ops = []
    ops.extend(make_vector_2d([0, 0], a, "a", role="primary"))
    ops.extend(make_vector_2d([0, 0], b, "b", role="construction"))
    ops.extend(make_vector_2d(a, c, "b_translated", role="construction", style="dashed"))
    ops.extend(make_vector_2d([0, 0], c, "result", role="result"))
    ops.append(make_polygon([[0, 0], a, c, b]))
    ops.append(make_label("a", [a[0]/2, a[1]/2], [-0.2, -0.2]))
    ops.append(make_label("b", [b[0]/2, b[1]/2], [0.2, 0.2]))
    ops.append(make_label("a+b", [c[0]/2, c[1]/2], [0.2, 0]))
    ops.append({"op": "view.fit", "padding": 1.15})
    
    return CommandPlan(
        scene="2d", 
        operations=tuple(ops),
        summary="向量加法的平行四边形法则"
    )

BUILDERS = {
    "draw.ch01.ops.addition": build_vector_addition,
    "draw.ch01.ops.subtraction": build_vector_subtraction,
    # ... all 24 chapter 1 topics
}
```

### 3. Core Interface Changes

**Update `common.py`:**

```python
def recipe_for_entry(entry: LessonEntry) -> VisualizationRecipe:
    """Create visualization recipe from lesson entry"""
    from .builders import get_builder_for
    
    # Get topic-specific builder
    builder_func = get_builder_for(entry.visualization_id)
    
    if builder_func is None:
        # All 54 topics must have builders
        raise ValueError(
            f"No builder found for {entry.visualization_id}. "
            f"All topics must have a specific builder."
        )
    
    scene = "3d" if _uses_3d(entry.required_capabilities) else "2d"
    
    return VisualizationRecipe(
        id=entry.visualization_id,
        scene=scene,
        required_capabilities=entry.required_capabilities,
        builder=builder_func,
    )
```

**Builder Registry (`builders/__init__.py`):**

```python
from .chapter_01 import BUILDERS as CHAPTER_01_BUILDERS
from .chapter_02 import BUILDERS as CHAPTER_02_BUILDERS
from .chapter_03 import BUILDERS as CHAPTER_03_BUILDERS

_ALL_BUILDERS = {
    **CHAPTER_01_BUILDERS,
    **CHAPTER_02_BUILDERS,
    **CHAPTER_03_BUILDERS,
}

def get_builder_for(visualization_id: str):
    """Get builder function for specified topic"""
    return _ALL_BUILDERS.get(visualization_id)
```

### 4. Primitive Builders API

**2D Primitives:**

```python
# Vector creation
make_vector_2d(start: Point2D, end: Point2D, alias: str, 
               role: str = "primary", style: str = "solid") -> List[dict]

# Text labels
make_label(text: str, position: Point2D, offset: Point2D = [0, 0]) -> dict

# Angle arc
make_angle_arc(vertex: Point2D, first: Point2D, second: Point2D, 
               radius: float = 0.5) -> dict

# Projection
make_projection(vector: Point2D, direction: Point2D) -> dict

# Polygon
make_polygon(vertices: List[Point2D], color: str = "#5b8def", 
             opacity: float = 0.15, outline: bool = True) -> dict

# Right angle marker
make_right_angle_marker(vertex: Point2D, first: Point2D, 
                        second: Point2D, size: float = 0.3) -> dict

# View fitting
make_view_fit(padding: float = 1.15) -> dict
```

**3D Primitives:**

```python
# 3D vector
make_vector_3d(start: Point3D, end: Point3D, alias: str,
               role: str = "primary") -> dict

# 3D plane
make_plane_3d(origin: Point3D, normal: Point3D, size: float = 4,
              color: str = "#5b8def", opacity: float = 0.18) -> dict

# Parallelepiped
make_parallelepiped(origin: Point3D, vectors: List[Point3D],
                   color: str = "#4c9f70", opacity: float = 0.2) -> dict
```

**Math Utilities:**

```python
# Calculate projection of v onto direction u
def project_vector(v: Point2D, u: Point2D) -> Point2D

# Calculate angle between two vectors (radians)
def angle_between(v1: Point2D, v2: Point2D) -> float

# Calculate cross product (3D)
def cross_product(v1: Point3D, v2: Point3D) -> Point3D

# Calculate dot product
def dot_product(v1: List[float], v2: List[float]) -> float
```

## Toolbar Design

### 1. Layout and Position

**Horizontal toolbar at top-left corner:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  [选择] [点] [向量] [角度] [投影] [多边形] [变换] [子空间] [面积]    [撤销] [重做]  │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Layout Details:**
- Position: Top-left, 12px from edges
- Orientation: Horizontal
- Button size: 32×32px
- Button spacing: 4px between tools
- Group spacing: 12px between groups
- Background: Semi-transparent with theme-aware color
- Shadow: Subtle drop shadow for depth

**Groups:**
1. Basic tools: Select, Point, Vector
2. Linear algebra tools: Angle, Projection, Polygon, Transform, Subspace, Area
3. History: Undo, Redo

### 2. Component API

```python
class LinearAlgebraToolbar(QWidget):
    """Horizontal linear algebra toolbar at top-left"""
    
    # Signals
    tool_selected = Signal(str)  # "select", "point", "vector", "angle", ...
    undo_requested = Signal()
    redo_requested = Signal()
    
    def __init__(self, parent: QWidget, theme: str = "light"):
        # Basic tools
        self.select_tool: QToolButton
        self.point_tool: QToolButton
        self.vector_tool: QToolButton
        
        # Linear algebra tools (NEW)
        self.angle_tool: QToolButton       # Angle measurement
        self.projection_tool: QToolButton  # Projection
        self.polygon_tool: QToolButton     # Polygon construction
        self.transform_tool: QToolButton   # Matrix transformation
        self.subspace_tool: QToolButton    # Subspace region
        self.area_tool: QToolButton        # Oriented area
        
        # History
        self.undo_button: QToolButton
        self.redo_button: QToolButton
    
    def set_active_tool(self, tool: str) -> None:
        """Set active tool and update button states"""
    
    def set_theme(self, theme: str) -> None:
        """Update toolbar appearance for theme"""
    
    def position_in_host(self) -> None:
        """Position toolbar at top-left of parent"""
```

### 3. New Tool Interactions

**1. Angle Measurement Tool:**
- Click two vectors
- Display angle arc and angle value
- Support acute, right, and obtuse angles

**2. Projection Tool:**
- Select source vector and target direction
- Automatically draw projection vector, foot point, residual
- Display projection formula

**3. Polygon Tool:**
- Click to create vertices sequentially
- Double-click or click start point to close
- Support fill and outline styling

**4. Matrix Transformation Tool:**
- Pop up 2×2 matrix input dialog
- Apply to selected vectors or grid
- Show before/after comparison

**5. Subspace Region Tool:**
- Select basis vectors
- Fill the spanned subspace region
- Support different colors and opacity

**6. Oriented Area Tool:**
- Select two vectors
- Calculate and display oriented area
- Show sign and numerical value

### 4. Integration

**Update `designer_window.py`:**
- Remove or hide existing vertical toolbar (`two_d_tools.py`)
- Add `LinearAlgebraToolbar` at top-left
- Connect toolbar signals to scene interaction handlers
- Update tool state when scene changes

## Coordinate Selection Strategy

For each topic, choose coordinates that:
- **Clear visibility**: Moderate vector lengths (not too long or short)
- **Clear angles**: Avoid near-0° or near-180° angles
- **Simple values**: Integers or simple decimals when possible
- **Obvious relationships**: Geometric relationships should be visually clear

**Examples:**
- Vector addition: a=[2, 1], b=[1, 2] → clear parallelogram
- Projection: vector=[3, 1], direction=[2, 0.5] → clear perpendicular
- Inner product: a=[3, 1], b=[1, 2] → clear acute angle

Coordinates will be chosen based on teaching clarity, not mathematical generality.

## Testing Strategy

### 1. Unit Tests (Representative Topics)

**Chapter 1 (5 tests):**
- `test_vector_addition_builder` - Vector addition
- `test_vector_subtraction_builder` - Vector subtraction
- `test_inner_product_builder` - Inner product, angle, projection
- `test_projection_definition_builder` - Projection definition
- `test_cross_product_builder` - Cross product (3D)

**Chapter 2 (4 tests):**
- `test_transformed_grid_builder` - Basis transformation
- `test_matrix_composition_builder` - Composite transformation
- `test_subspace_rank_builder` - Rank and output space
- `test_null_space_builder` - Null space

**Chapter 3 (4 tests):**
- `test_oriented_area_builder` - Oriented area
- `test_determinant_properties_builder` - Determinant properties
- `test_inverse_undo_builder` - Inverse matrix undo
- `test_det_zero_builder` - det=0 condition

**Test Template:**
```python
def test_vector_addition_builder():
    """Test vector addition builder generates correct geometry"""
    from linear_algebra.visualizations.builders.chapter_01 import build_vector_addition
    from linear_algebra.visualizations.common import RenderContext
    
    context = RenderContext.default("ch01.ops.addition")
    plan = build_vector_addition(context)
    
    # Verify scene type
    assert plan.scene == "2d"
    
    # Verify vector count (at least 3: a, b, a+b)
    vector_ops = [op for op in plan.operations if op.get("kind") == "vector"]
    assert len(vector_ops) >= 3, f"Expected at least 3 vectors, got {len(vector_ops)}"
    
    # Verify label count (at least 3: a, b, a+b)
    label_ops = [op for op in plan.operations if "label" in op.get("op", "")]
    assert len(label_ops) >= 3, f"Expected at least 3 labels, got {len(label_ops)}"
    
    # Verify parallelogram
    polygon_ops = [op for op in plan.operations if op.get("op") == "geometry.polygon"]
    assert len(polygon_ops) >= 1, "Expected parallelogram polygon"
    
    # Verify view fit
    view_ops = [op for op in plan.operations if op.get("op") == "view.fit"]
    assert len(view_ops) == 1, "Expected exactly one view.fit operation"
```

### 2. Toolbar Tests

```python
def test_linear_algebra_toolbar_creation():
    """Test toolbar creation and layout"""
    toolbar = LinearAlgebraToolbar(None, theme="light")
    
    # Verify tool buttons exist
    assert toolbar.select_tool is not None
    assert toolbar.angle_tool is not None
    assert toolbar.projection_tool is not None
    # ... other tools

def test_toolbar_tool_selection():
    """Test tool selection signal"""
    toolbar = LinearAlgebraToolbar(None)
    
    signal_received = []
    toolbar.tool_selected.connect(lambda tool: signal_received.append(tool))
    
    toolbar.angle_tool.click()
    assert "angle" in signal_received
```

### 3. Manual Verification Checklist

**Per-topic verification:**
- [ ] Geometry mathematically correct (vectors, angles, projections, etc.)
- [ ] Labels clear and well-positioned
- [ ] Color distinction clear (primary/construction/result)
- [ ] View fitting correct, no clipping
- [ ] Consistent with explanation text

**Toolbar verification:**
- [ ] Toolbar position correct (top-left)
- [ ] All tool icons display
- [ ] Tool selection state toggles correctly
- [ ] Each new tool interaction logic works
- [ ] Toolbar styling updates on theme change

## Implementation Plan

### Phase 1: Infrastructure (1 day)
1. Create `builders/` directory structure
2. Implement `primitives.py` and `math_utils.py`
3. Update `common.py` `recipe_for_entry()`
4. Test basic framework

### Phase 2: Chapter 1 Builders (2 days)
5. Implement 24 Chapter 1 builders
6. Write representative tests (5 tests)
7. Manual verification of all 24 topics

### Phase 3: Chapter 2 Builders (2 days)
8. Implement 15 Chapter 2 builders
9. Write representative tests (4 tests)
10. Manual verification of all 15 topics

### Phase 4: Chapter 3 Builders (1 day)
11. Implement 15 Chapter 3 builders
12. Write representative tests (4 tests)
13. Manual verification of all 15 topics

### Phase 5: Toolbar (2-3 days)
14. Implement `LinearAlgebraToolbar` component
15. Implement 6 new tool interaction handlers
16. Integrate into `designer_window.py`
17. Test toolbar functionality

### Phase 6: Integration & Verification (2 days)
18. Run all unit tests
19. Complete manual verification (54 topics + toolbar)
20. Fix identified issues
21. Update documentation

**Total: 10-11 days**

## Migration & Rollback

**Migration:**
- All 54 topics transition to new builders in single change
- No gradual rollout (all-or-nothing approach)
- The old generic template functions are no longer selected by the registry; missing builders are errors.

**Rollback:**
- If critical issues are found, stop loading the affected topic and fix its builder; do not reintroduce a compatibility fallback.
- Tree UI and explanation system unaffected
- Only `linear_algebra/visualizations/` needs rollback

**Preserved Components:**
- `linear_algebra/catalog/` - Topic catalog ✅
- `linear_algebra/explanations/` - Explanation content ✅
- `ui/linear_algebra_dialog.py` - Tree UI ✅

## Success Criteria

- ⏳ All 54 topics display mathematically correct visualizations (command-valid; visual review pending)
- ⏳ Each visualization matches its explanation text (visual review pending)
- ✅ Horizontal toolbar with 6 new linear algebra tools functional (canvas handlers and tests)
- ✅ No regression in tree UI and explanation system
- ✅ Representative unit tests pass
- ⏳ Manual verification complete for all topics
- ✅ Code maintainable and well-documented

## Risks & Mitigation

**Risk 1: Geometric calculations incorrect**
- Mitigation: Unit tests for each representative builder
- Mitigation: Visual comparison with reference materials
- Mitigation: Manual verification by math expert

**Risk 2: Breaking existing functionality**
- Mitigation: Comprehensive regression testing
- Mitigation: Keep tree UI and explanations unchanged
- Mitigation: Test all 54 topics individually

**Risk 3: Toolbar integration issues**
- Mitigation: Implement toolbar as independent component
- Mitigation: Test toolbar separately before integration
- Mitigation: Keep the existing geometry toolbar for non-lecture contexts while the linear-algebra toolbar is independently completed

**Risk 4: Coordinate choices not pedagogically optimal**
- Mitigation: Review sample visualizations early
- Mitigation: Adjust coordinates based on feedback
- Mitigation: Document rationale for coordinate choices

## Future Enhancements (Out of Scope)

These enhancements are explicitly deferred to future changes:

- **Parameterized visualizations** - Sliders to adjust vectors
- **Animation** - Show construction process step-by-step
- **Interactive exploration** - Drag vectors to see relationships change
- **Visual regression testing** - Automated screenshot comparisons
- **Coordinate presets** - Multiple coordinate sets per topic
- **Export visualizations** - Save as images or animations

Focus remains on fixing the core visualization correctness issue.

---

**Approved by:** User  
**Date:** 2026-09-01
