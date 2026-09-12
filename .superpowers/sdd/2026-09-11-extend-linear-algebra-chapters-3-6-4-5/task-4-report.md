# Task 4 report

Status: DONE — strict semantic implementation and Chapter 4 release bundle complete.

Commits:

- Earlier family/resource groundwork: `90f6c09e7380af17b4474f0359f6808b3a6250ef`, `c6075f9`, `be866aa`, `0ea69b2`, `1609766`, `2cdd5f6`, `3cb69dc`, `59d842d`, `f2761d8`.
- Strict typed semantic family and negative tests: `1046b43`, `aa370c5`.
- Chapter-scoped publication/upsert, refreshed 16 reviewed/compiled resources, index, and release tests: `a357bfa`.

Implementation:

- All 16 topics now use immutable declarative typed descriptors: exact entity role/kind/dimension/value, explicit relation endpoints and parameters, multi-stage layouts, mathematical invariants, and expected protocol operations.
- `Chapter4FamilyCompiler` validates the exact graph and independently recomputes closure, classification, intersection/union counterexample, kernel/image, spans/ranks, dependence, nullspace, rank collapse, coordinates, linearity, matrix columns, and rank–nullity evidence. It emits true geometry operations; annotations are supplementary only.
- The main compiler invokes and consumes the Chapter 4 family result, skips generic entity/relation/capability fallbacks for Ch4, gates aliases against real operations, and carries computed family evidence into the final compiled record.
- The artifact builder and claim ledger cover every entity, relation, and stage for each topic. Contracts require typed roles, relation kinds/endpoints/parameters, invariants, minimum stages, and expected operations.
- `compile_chapter_04` now validates all 16 topics before writing, refreshes `data/compiled/ch04.*.json`, and performs a chapter-scoped atomic index upsert. Existing Chapter 1–3 index rows are retained verbatim; repeated upserts replace rather than append. Invalid index baselines fail before resource/index writes.
- `data/revieweds/ch04/*/r1.json`, `data/compiled/ch04.*.json`, and `data/index.json` contain the released 16-topic bundle. Ch05–08 remain unpublished and untouched.

Tests:

- Strict semantics and destructive negative coverage: `67 passed` initially, `71 passed` after the 3D protocol witness fix.
- Focused implementation/resource suite: `pytest tests/test_linear_algebra_ch04_strict_semantics.py tests/test_linear_algebra_chapter_04.py tests/test_linear_algebra_compiled_resources.py tests/test_linear_algebra_chapters_4_8_artifacts.py tests/test_linear_algebra_builders.py tests/test_linear_algebra_visual_compiler.py tests/test_linear_algebra_teaching_store.py -q` — `115 passed`.
- Release index tests cover 70 unique rows, exactly 16 Ch4 rows, preservation of all non-Ch4 rows, idempotent replacement, and atomic failure/no-write behavior.
- `python -m py_compile` passed for semantic specs, artifact/resource compiler, contracts, visual compiler, and Chapter 4 family.
- Every released Ch4 plan validates and executes transactionally through `SceneCommandService` with no rollback.

Known downstream scope:

- Ch05–08 remain unpublished by design. Full production registry validation still depends on the pre-existing missing `draw.ch05.homogeneous.solution-space` recipe; no Ch05–08 resource was changed in this release.
