# Fix Plan: Visualization System Redesign

**Related to:** expand-linear-algebra-lecture-tree  
**Date:** 2026-09-01  
**Priority:** High

## Problem Summary

当前可视化系统使用 capability-tag-based 通用模板，导致约 40/54 主题显示不正确的几何图形。需要重新设计为 topic-specific builders。

## Proposed Solution

### Architecture Change

**From:**
```
Topic → Capabilities → Generic Template → CommandPlan
```

**To:**
```
Topic → Topic-Specific Builder Function → CommandPlan
```

### Implementation Approach

为每个主题编写专门的几何构建函数。

**Example: Vector Addition**
```python
# linear_algebra/visualizations/builders/chapter_01.py

def build_vector_addition(context: RenderContext) -> CommandPlan:
    """向量加法：显示 a + b = c 的平行四边形法则"""
    a = [2.0, 1.0]
    b = [1.0, 2.0]
    c = [a[0] + b[0], a[1] + b[1]]  # [3.0, 3.0]
    
    operations = [
        # Origin
        {"op": "point.upsert", "alias": "O", "coordinates": [0, 0], "name": "O"},
        
        # Vector a (primary color)
        {"op": "point.upsert", "alias": "A", "coordinates": a, "name": "A"},
        {"op": "linear.upsert", "alias": "a", "start": "O", "end": "A", 
         "kind": "vector", "role": "primary"},
        
        # Vector b (secondary color)
        {"op": "point.upsert", "alias": "B", "coordinates": b, "name": "B"},
        {"op": "linear.upsert", "alias": "b", "start": "O", "end": "B",
         "kind": "vector", "role": "secondary"},
        
        # Translated b' from A
        {"op": "point.upsert", "alias": "C", "coordinates": c, "name": "C"},
        {"op": "linear.upsert", "alias": "b_translated", "start": "A", "end": "C",
         "kind": "vector", "role": "auxiliary", "style": "dashed"},
        
        # Result vector a+b (result color)
        {"op": "linear.upsert", "alias": "result", "start": "O", "end": "C",
         "kind": "vector", "role": "result"},
        
        # Parallelogram O-a-c-b
        {"op": "geometry.polygon", "alias": "parallelogram",
         "vertices": [[0, 0], a, c, b], 
         "color": "#5b8def", "opacity": 0.15, "outline": True},
        
        # Labels
        {"op": "annotation.label", "alias": "label_a", "text": "a", 
         "position": [a[0]/2, a[1]/2], "offset": [-0.2, -0.2]},
        {"op": "annotation.label", "alias": "label_b", "text": "b",
         "position": [b[0]/2, b[1]/2], "offset": [0.2, 0.2]},
        {"op": "annotation.label", "alias": "label_result", "text": "a+b",
         "position": [c[0]/2, c[1]/2], "offset": [0.2, 0]},
        
        {"op": "view.fit", "padding": 1.15}
    ]
    
    return CommandPlan(
        scene="2d", 
        operations=tuple(operations), 
        summary="向量加法的平行四边形法则"
    )

# Builder registry
BUILDERS = {
    "draw.ch01.ops.addition": build_vector_addition,
    "draw.ch01.ops.subtraction": build_vector_subtraction,
    "draw.ch01.inner.definitions": build_inner_product_definitions,
    # ... all 24 chapter 1 topics
}
```

**Updated common.py:**
```python
def recipe_for_entry(entry: LessonEntry) -> VisualizationRecipe:
    from .builders import chapter_01, chapter_02, chapter_03
    
    # Look up topic-specific builder
    builder_func = None
    for module in [chapter_01, chapter_02, chapter_03]:
        if hasattr(module, 'BUILDERS') and entry.visualization_id in module.BUILDERS:
            builder_func = module.BUILDERS[entry.visualization_id]
            break
    
    if builder_func is None:
        # Fallback to generic builder (temporary during migration)
        builder_func = lambda ctx: _build_plan(ctx, entry, _determine_scene(entry))
    
    scene = "3d" if _uses_3d(entry.required_capabilities) else "2d"
    
    return VisualizationRecipe(
        id=entry.visualization_id,
        scene=scene,
        required_capabilities=entry.required_capabilities,
        builder=builder_func,
    )
```

## Implementation Plan

### Phase 1: Infrastructure (1 day)

- [ ] Create `linear_algebra/visualizations/builders/` directory
- [ ] Create `builders/common.py` with shared utilities
- [ ] Create `builders/types.py` with type definitions
- [ ] Update `recipe_for_entry()` to support topic-specific builders
- [ ] Add fallback to generic builder for unmigrated topics

### Phase 2: Chapter 1 - Vectors (2 days)

Implement 24 builders:

**1.1 向量的几何表示 (4 topics)**
- [ ] ch01.vector.magnitude - 向量的几何量
- [ ] ch01.vector.point-distinction - 点与向量的本质区别
- [ ] ch01.vector.coordinate-system - 坐标系与右手约定
- [ ] ch01.vector.direction-examples - 方向、象限与分层例题

**1.2 向量的线性运算 (7 topics)**
- [ ] ch01.ops.addition - 向量加法
- [ ] ch01.ops.subtraction - 向量减法
- [ ] ch01.ops.scalar - 向量数乘与共线
- [ ] ch01.ops.linear-combination - 线性组合
- [ ] ch01.ops.velocity - 速度合成的几何表示
- [ ] ch01.ops.cross-product - 叉积的三维旋转方向
- [ ] ch01.ops.scalar-triple - 混合积与平行六面体体积

**1.3 内积 (5 topics)**
- [ ] ch01.inner.equivalence - 内积两种定义的几何等价
- [ ] ch01.inner.definitions - 内积、夹角与投影
- [ ] ch01.inner.applications - 内积的长度、正交与夹角应用
- [ ] ch01.inner.cauchy-schwarz - 柯西-施瓦茨不等式的投影界
- [ ] ch01.inner.examples - 内积几何分层例题

**1.4 投影 (3 topics)**
- [ ] ch01.projection.definition - 投影、垂足与残差
- [ ] ch01.projection.properties - 投影的可加性与齐次性
- [ ] ch01.projection.force - 坐标轴与斜面上的力分解

**1.5 几何证明 (4 topics)**
- [ ] ch01.proof.method - 几何问题转向量的四步方法
- [ ] ch01.proof.midline - 三角形中位线定理
- [ ] ch01.proof.centroid - 三角形重心定理
- [ ] ch01.proof.parallelogram-diagonals - 平行四边形对角线互相平分

**1.7 高维拓展 (1 topic)**
- [ ] ch01.high-dimensional.analogy - 从二维、三维到 n 维的向量类比

### Phase 3: Chapter 2 - Matrices (2 days)

Implement 16 builders:

**2.2-2.4 批量操作与矩阵运算 (3 topics)**
- [ ] ch02.batch.inner-products - 批量内积与多角度比较
- [ ] ch02.batch.projection - 投影矩阵把一批向量压到方向上
- [ ] ch02.matrix.additive-distributivity - 矩阵加法与变换分配律

**2.5-2.6 矩阵乘法 (5 topics)**
- [ ] ch02.matrix.row-column - 矩阵乘向量的行视角与列视角
- [ ] ch02.matrix.transformed-grid - 基向量变换与网格变形
- [ ] ch02.matrix.stretch-rotate-scale - 拉伸、旋转与缩放的矩阵图像
- [ ] ch02.matrix.composition - 复合变换与 AB ≠ BA
- [ ] ch02.matrix.basis - 矩阵的列与新基坐标

**2.7-2.8 矩阵性质 (2 topics)**
- [ ] ch02.matrix.powers - 矩阵幂表示重复变换

**2.9 子空间 (5 topics)**
- [ ] ch02.subspace.independence - 线性无关与线性相关的方向图
- [ ] ch02.subspace.rank - 秩与输出空间的真实维度
- [ ] ch02.subspace.null - 零空间是被压到原点的方向
- [ ] ch02.subspace.column - 列空间是变换可到达的位置
- [ ] ch02.subspace.rank-nullity - 秩-零化度的维数守恒

**2.10 高维拓展 (1 topic)**
- [ ] ch02.high-dimensional.analogy - n 维矩阵运算的低维类比

### Phase 4: Chapter 3 - Determinants (1 day)

Implement 14 builders:

**3.1 行列式定义 (4 topics)**
- [ ] ch03.det.oriented-area - 行列式的有向面积定义
- [ ] ch03.det.ad-bc - ad-bc 的面积分解
- [ ] ch03.det.sign-zero-one - 行列式符号、零和一的几何意义
- [ ] ch03.det.examples - 行列式面积缩放分层例题

**3.2 行列式性质 (4 topics)**
- [ ] ch03.det.row-swap - 交换两行翻转方向
- [ ] ch03.det.scaling - 一行数乘改变面积比例
- [ ] ch03.det.shear - 切变保持面积不变
- [ ] ch03.det.multiplicativity - det(AB) 的两阶段面积缩放

**3.3-3.4 克拉默法则与逆矩阵 (4 topics)**
- [ ] ch03.cramer.area-ratio - 克拉默法则的面积比解方程组
- [ ] ch03.inverse.undo - 逆矩阵的几何撤销
- [ ] ch03.inverse.formula - 2×2 求逆公式的几何参数
- [ ] ch03.inverse.examples - 可逆与退化变换的分层例题

**3.6-3.8 深度解释 (2 topics)**
- [ ] ch03.det.zero.equivalence - det=0 的等价几何条件
- [ ] ch03.det.high-dimensional-volume - n 阶行列式与面积、体积类比
- [ ] ch03.inverse.reverse-order - 逆矩阵乘积的逆序撤销

### Phase 5: 2D Toolbar Extensions (2-3 days)

Add missing linear algebra tools:

- [ ] **Angle Tool** - Click two vectors to measure angle, display arc and value
- [ ] **Projection Tool** - Click vector and direction, show projection and residual
- [ ] **Polygon Tool** - Click points to create polygon, close with double-click
- [ ] **Transform Tool** - Input 2×2 matrix, apply to selected vectors/grid
- [ ] **Subspace Tool** - Select basis vectors, fill subspace region
- [ ] **Oriented Area Tool** - Select two vectors, show oriented area

### Phase 6: Testing & Verification (2 days)

- [ ] Unit tests for each builder function
- [ ] Manual verification of all 54 topics
- [ ] Screenshot comparisons with expected visualizations
- [ ] Mathematical correctness verification
- [ ] Update existing tests to reflect new implementation
- [ ] User acceptance testing

## Migration Strategy

**Incremental approach:**
1. Start with 3 example topics (vector addition, subtraction, inner product)
2. Verify they work correctly
3. Complete Chapter 1 (week 1)
4. Complete Chapter 2 (week 2)
5. Complete Chapter 3 (week 3)
6. Toolbar extensions (parallel to chapters)

**Testing during migration:**
```python
def test_vector_addition_visualization():
    recipe = recipe_for("draw.ch01.ops.addition")
    context = RenderContext.default("ch01.ops.addition")
    plan = recipe.builder(context)
    
    # Verify minimum operations
    assert len(plan.operations) >= 10
    
    # Verify vectors
    vector_ops = [op for op in plan.operations if op["op"] == "linear.upsert"]
    assert len(vector_ops) >= 3  # a, b, a+b minimum
    
    # Verify labels
    label_ops = [op for op in plan.operations if "label" in op.get("op", "")]
    assert len(label_ops) >= 3  # a, b, a+b labels
```

## File Structure

```
linear_algebra/visualizations/
├── __init__.py              # Registry
├── common.py                # VisualizationRecipe, updated recipe_for_entry
├── builders/
│   ├── __init__.py
│   ├── common.py            # Shared utilities (projection calc, angle calc, etc.)
│   ├── types.py             # Type definitions
│   ├── chapter_01.py        # 24 builder functions + BUILDERS dict
│   ├── chapter_02.py        # 16 builder functions + BUILDERS dict
│   └── chapter_03.py        # 14 builder functions + BUILDERS dict
├── chapter_01.py            # RECIPES tuple (unchanged)
├── chapter_02.py            # RECIPES tuple (unchanged)
└── chapter_03.py            # RECIPES tuple (unchanged)
```

## Success Criteria

- ✅ All 54 topics display mathematically correct visualizations
- ✅ Each visualization matches its explanation text
- ✅ 2D toolbar supports all required linear algebra operations
- ✅ No regression in existing tree UI and explanation system
- ✅ Code is maintainable and well-documented
- ✅ All tests pass

## Effort Estimate

| Phase | Days | Dependencies |
|-------|------|-------------|
| Phase 1: Infrastructure | 1 | None |
| Phase 2: Chapter 1 | 2 | Phase 1 |
| Phase 3: Chapter 2 | 2 | Phase 1 |
| Phase 4: Chapter 3 | 1 | Phase 1 |
| Phase 5: Toolbar | 2-3 | None (parallel) |
| Phase 6: Testing | 2 | Phase 2-4 |
| **Total** | **10-11 days** | |

## Risk Mitigation

**Risk 1:** Geometric calculations incorrect
- Mitigation: Unit tests for each builder
- Mitigation: Visual comparison with reference materials

**Risk 2:** Breaking existing functionality
- Mitigation: Fallback to generic builder for unmigrated topics
- Mitigation: Comprehensive regression testing

**Risk 3:** Scope creep (animations, interactivity)
- Mitigation: Strict focus on static correct visualizations first
- Mitigation: Defer enhancements to future changes

## Related Documents

- [verification.md](./verification.md) - Detailed problem analysis
- [design.md](./design.md) - Original design (tree structure still valid)
- [tasks.md](./tasks.md) - Completed tasks (tree and explanations)
