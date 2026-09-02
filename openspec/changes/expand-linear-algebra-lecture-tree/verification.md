# Verification: expand-linear-algebra-lecture-tree

**Date:** 2026-09-01  
**Status:** ❌ FAILED  
**Method:** Systematic Debugging (Superpowers)

## Summary

虽然所有计划任务已标记完成，但通过系统化调试发现**可视化系统存在架构性缺陷**：

- ❌ **约 40/54 主题（75%）显示不正确的几何图形**
- ❌ **二维工具栏缺少线性代数特定工具**

## Critical Issue 1: Generic Templates Cannot Express Topic-Specific Math

### Root Cause

```
Current: 54 topics → ~15 capability tags → ~8 hardcoded geometry templates
Required: 54 topics → 54 topic-specific mathematical visualizations
```

### Evidence

| Topic | Expected | Actual | Status |
|-------|----------|--------|--------|
| 向量加法 | 显示 a, b, a+b 形成平行四边形 | 一个固定向量 + 无关四边形 | ❌ |
| 向量减法 | 显示 a, -b, a-b 的关系 | 一个固定向量 + 投影（错误！） | ❌ |
| 内积、夹角与投影 | 两个向量的夹角和投影 | 一个向量 + 无对象的角弧 | ❌ |
| 线性组合 | αa + βb 的组合过程 | 一个向量 + 固定四边形 | ❌ |

### Technical Details

**Current implementation:**
```python
# linear_algebra/visualizations/common.py
def _two_d_geometry(capabilities: set[str]) -> list[dict]:
    operations = []
    if "vector_2d" in capabilities:
        # All "vector_2d" topics get the same fixed vector
        operations.extend([
            {"op": "point.upsert", "coordinates": [0, 0]},
            {"op": "point.upsert", "coordinates": [2.5, 1.8]},  # HARDCODED!
            {"op": "linear.upsert", "start": "O", "end": "A"},
        ])
    if "polygon_2d" in capabilities:
        # All "polygon_2d" topics get the same fixed polygon
        operations.append({
            "op": "geometry.polygon",
            "vertices": [[0,0],[2,1],[3,3],[1,2]]  # HARDCODED!
        })
    return operations
```

**Problem:** No topic-specific geometry data stored anywhere.

### Test Results

```bash
# Tested: draw.ch01.ops.addition (向量加法)
Expected operations:
  1. Draw vector a from origin
  2. Draw vector b from origin
  3. Draw translated b' from a's endpoint
  4. Draw result vector a+b
  5. Draw parallelogram O-a-(a+b)-b

Actual operations:
  1. point.upsert O at [0, 0]
  2. point.upsert A at [2.5, 1.8]  ← Fixed coords
  3. linear.upsert v from O to A    ← Only one vector!
  4. geometry.polygon [[0,0],[2,1],[3,3],[1,2]]  ← Unrelated polygon
  5. view.fit

Result: ❌ Cannot demonstrate vector addition geometry
```

```bash
# Tested: draw.ch01.ops.subtraction (向量减法)
Expected: Show a, -b, and a-b
Actual: One fixed vector + projection operation

Result: ❌ Completely wrong geometry type
```

### Impact

- **Chapter 1:** ~18/24 topics incorrect
- **Chapter 2:** ~12/16 topics incorrect
- **Chapter 3:** ~10/14 topics incorrect
- **Total:** ~40/54 topics show wrong visualizations

### User Experience

1. User opens "向量加法" topic
2. Sees one random vector and unrelated polygon
3. Reads explanation: "把 b 平移到 a 的终点..."
4. **Confused: Where is b? Where is a+b?**
5. **Cannot understand vector addition concept**
6. **Learning objective blocked** ⚠️

## Critical Issue 2: 2D Toolbar Missing Linear Algebra Tools

### Current Tools

- ✅ Select/Move tool
- ✅ Point tool
- ✅ Line tools (line, segment, ray, vector)
- ✅ Grid snap
- ✅ Undo/Redo

### Missing Tools Required for Chapters 1-3

- ❌ **Angle measurement tool** - needed for 内积、夹角
- ❌ **Projection tool** - needed for 投影、分解
- ❌ **Polygon construction tool** - needed for 平行四边形、线性组合
- ❌ **Matrix transformation tool** - needed for Chapter 2
- ❌ **Subspace region tool** - needed for 秩、零空间、列空间
- ❌ **Oriented area tool** - needed for Chapter 3 行列式

### Impact

- Users can only view preset (incorrect) visualizations
- Cannot interactively construct and verify understanding
- Teaching interactivity limited

## Root Cause Analysis

### Architecture Issue

**Current:**
```
Topic → Capabilities → Generic Template → CommandPlan
             ↑ Information loss here
```

**Required:**
```
Topic → Topic-Specific Builder → CommandPlan
```

### Why This Happened

**Design intent vs. implementation:**

Design doc said:
> "用现有二维原语组合教学图"

Team understood as:
- Use capability tags to trigger generic geometry templates
- All topics share a few hardcoded configurations

**Missing piece:**
- ❌ No topic-specific geometry construction logic written
- ❌ No topic-specific data (vector coords, relationships) stored
- ❌ Used "one-size-fits-all" approach

## Recommendation

### Do Not Proceed with Current Implementation

**Reason:** Visualization system architecturally flawed - cannot fulfill teaching objectives.

### Required Actions

1. **Create new change:** `fix-linear-algebra-visualizations`
2. **Redesign approach:** Topic-specific builders (not generic templates)
3. **Keep working parts:** Tree UI and explanation system are correct
4. **Focus effort:** Only `linear_algebra/visualizations/` needs redesign

### Estimated Effort

| Phase | Days | Description |
|-------|------|-------------|
| Architecture redesign | 1 | Topic-specific builder framework |
| Chapter 1 builders | 2 | 24 topic-specific functions |
| Chapter 2 builders | 2 | 16 topic-specific functions |
| Chapter 3 builders | 1 | 14 topic-specific functions |
| 2D toolbar tools | 2-3 | 6 new linear algebra tools |
| Testing | 2 | All 54 topics verification |
| **Total** | **10-11 days** | |

### Next Step

建议启动新的 OpenSpec change 来修复可视化系统。当前 change 的树形目录和解释系统可以保留，只需重新实现可视化生成逻辑。

## Verified Components

### Working Correctly ✅

- ✅ **Tree UI:** 54 topics organized in 3-level hierarchy
- ✅ **Search & expand/collapse:** All interactions working
- ✅ **Explanation content:** All 54 explanations complete and accurate
- ✅ **Integration:** Tree selection triggers scene loading
- ✅ **Tests:** Tree model, loading, catalog tests all pass

### Not Working ❌

- ❌ **Visualization geometry:** ~40/54 topics show wrong diagrams
- ❌ **2D toolbar:** Missing 6 linear algebra-specific tools

## Conclusion

**Implementation status:** ✅ Completed  
**Quality status:** ❌ Architecturally flawed  
**Ready for use:** ❌ No - requires redesign

The lecture tree structure and explanation system work correctly and should be preserved. The visualization system needs a complete redesign using topic-specific builders instead of generic templates.

**Priority:** 🔴 High - blocks teaching effectiveness

---

**Verified by:** Claude (Systematic Debugging)  
**Verification date:** 2026-09-01
