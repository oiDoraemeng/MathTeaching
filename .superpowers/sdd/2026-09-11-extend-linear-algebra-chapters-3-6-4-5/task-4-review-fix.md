# Plan 3 Task 4 review-fix — Needs fixes

## Verdict

**Needs fixes.** The publication and linkage gate is now present and the requested focused command passes, but the implementation does not satisfy the required per-topic operation semantics. The reviewed artifacts/contracts currently collapse all sixteen chapter-4 topics into one generic semantic family/plan, so labels are not bound to topic-specific closure, span, dependence, nullspace, rank, map, kernel/image, or rank-nullity operations.

## Evidence

- The requested command passes: `pytest tests/test_linear_algebra_compiled_resources.py tests/test_linear_algebra_chapter_04.py tests/test_linear_algebra_chapters_4_8_artifacts.py -q` → **8 passed**.
- Registry/builders contain the expected sixteen IDs: `linear_algebra/visualizations/builders/chapter_04.py:6,35`; the builder loads reviewed artifacts and calls `VisualSemanticsCompiler` (`:9-18`), checks topic/source identity (`:26-31`), and returns the compiled plan (`:32`).
- All sixteen compiled snapshots exist and index/digest linkage is covered by `tests/test_linear_algebra_chapter_04.py:38-58`; the focused tests passed. Chapter 1–3 index rows are byte-for-byte preserved relative to the parent of `90f6c09` (54 rows compared).
- **Blocking semantic issue:** `linear_algebra/visualizations/contracts.py:65-68` assigns every ch04 topic `subspace_region` and the same generic contract shape. `linear_algebra/teaching/chapter_artifacts.py:65-68` generates the same `scene_family` and `maps_to` semantic graph for every topic. Consequently, the sixteen compiled JSON plans all report `scene_family: subspace_region` and the same operation sequence, including `geometry.subspace_region`; only the required IDs differ. This is a generic fallback in substance even though it is routed through the shared compiler.
- The test `tests/test_linear_algebra_chapter_04.py:22-35` only checks that compiled output equals the generic compiler output and that required primitives are present; it does not assert distinct topic operation mappings. Thus the passing test does not establish the brief's “逐主题 operation 语义” requirement.
- Chapter-scoped compilation in `linear_algebra/teaching/compile_resources.py:163-168,229-244` is acceptable for ch04 release gating as stated in the fix package, provided production registry validation remains strict; no separate failure was found in the requested focused command.

## Required follow-up

Give each ch04 topic an artifact/contract semantic graph and operation mapping that expresses its actual claim (closure, subspace, span, dependence, nullspace, rank, basis, dimension, coordinates, maps, kernel/image, rank-nullity), regenerate the sixteen snapshots/index digests, and add assertions that reject identical generic plans for unrelated topics. Rerun the focused command and the production registry validation.

