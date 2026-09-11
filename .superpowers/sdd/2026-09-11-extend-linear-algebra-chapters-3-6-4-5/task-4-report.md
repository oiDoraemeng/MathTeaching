# Task 4 report

Status: DONE

Commits: `90f6c09e7380af17b4474f0359f6808b3a6250ef` (initial recipes), `c6075f9` (publication gate), `be866aa`/`0ea69b2` (reports), `1609766` (per-topic semantic mapping fix).

Implementation:

- Added chapter 4's 16 explicit recipe/builders and registered them in the visualization registry.
- Builders now resolve the reviewed semantic graph, explicit visual contract, source context, and shared compiler before returning a plan; no fixed identity/fallback plan remains.
- Added an immutable explicit mapping for all 16 chapter-4 topics. Reviewed artifacts now carry the mapped scene family and relation graph, while contracts require the mapped family/relation. The resulting plans cover polygon, projection, angle, transformed-grid, staged-transform, subspace, and affine evidence instead of one generic sequence.
- Added chapter-scoped reviewed compilation and materialized all 16 `data/compiled/ch04.*.json` resources with artifact/source/contract/scene/plan linkage.
- Atomically added the 16 chapter 4 rows to `data/index.json`; the pre-existing chapter 1–3 rows remain byte-for-byte unchanged.

Tests:

- `pytest tests/test_linear_algebra_chapter_04.py tests/test_linear_algebra_quadratic_family.py tests/test_linear_algebra_extended_plan_replay.py -q` — `13 passed` (existing focused suite).
- `pytest tests/test_linear_algebra_compiled_resources.py tests/test_linear_algebra_chapter_04.py tests/test_linear_algebra_chapters_4_8_artifacts.py -q` — `8 passed`.
- `pytest tests/test_linear_algebra_compiled_resources.py tests/test_linear_algebra_chapter_04.py tests/test_linear_algebra_chapters_4_8_artifacts.py -q` — `9 passed` after per-topic mapping.
- `pytest tests/test_linear_algebra_builders.py tests/test_linear_algebra_visual_compiler.py -q` — `20 passed`.

Concerns:

- Ch05–08 remain unpublished and are intentionally excluded from the published-registry verifier; ch04 uses the explicit reviewed chapter-scoped resolver required by this release gate.
