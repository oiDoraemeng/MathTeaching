# Task 4 report

Status: DONE — strict semantic implementation and Chapter 4 release bundle complete.

Commits:

- Earlier family/resource groundwork: `90f6c09e7380af17b4474f0359f6808b3a6250ef`, `c6075f9`, `be866aa`, `0ea69b2`, `1609766`, `2cdd5f6`, `3cb69dc`, `59d842d`, `f2761d8`.
- Strict typed semantic family and negative tests: `1046b43`, `aa370c5`.
- Chapter-scoped publication/upsert, refreshed 16 reviewed/compiled resources, index, and release tests: `a357bfa`.
- Final mathematical witnesses, disk-backed reviewed loading/release script, desktop host dispatch and rollback, baseline preservation, and regression tests: `430edbd`.

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

Final review follow-up (2026-09-12):

- `compile_chapter_04` now derives the Chapter 1–3 retained rows from `git show 90f6c09^:linear_algebra/teaching/data/index.json`, so dirty working-tree index edits cannot leak into the Chapter 4 release. The 54 baseline rows are checked for uniqueness before any write.
- Basis/span keeps all three `too_many` generators as separate executable vector witnesses. Nullspace computes `A`'s columns, scales each by the nonzero coefficient vector, and records the final zero residual. Classification, column/image, and nonlinear diagnostics are recomputed from relation parameters and entity values.
- The desktop host now dispatches `geometry.intersection` before the generic teaching branch, handles plane-plane intersections as a 3D line, and renders mapping-bundle domain/kernel/image lanes through the 2D teaching controller.
- Added real-host dispatch/rollback coverage for all 16 topics in `tests/test_scene_command_dispatch.py` and strict corruption coverage in `tests/test_linear_algebra_ch04_strict_semantics.py`. These tests execute the actual `MainWindow`, bridge/proxy, and geometry controllers with renderer doubles; they are not a recording-host test.
- Removed the temporary in-memory override from `load_reviewed_artifacts`. It now reads the checked-in reviewed JSON. `python -m scripts.release_chapter04` validates all generated artifacts before materializing the reviewed files and recompiling the canonical resources/index.
- Audit found all 54 legacy index rows in `a357bfa` differed from `90f6c09^`. Only those index rows were restored as explicitly required; unrelated dirty Chapter 1–3 artifacts and compiled resources were left untouched. Audit: 70 rows / 70 unique, 54 legacy rows exactly equal (canonical UTF-8 bytes) to baseline, 16/16 compiled resources reproduced field-for-field, and 16/16 reviewed JSON files equal the canonical descriptor output.

Final commands:

- `python -m scripts.release_chapter04` — 16 reviewed/compiled resources released.
- `pytest tests/test_linear_algebra_compiled_resources.py tests/test_linear_algebra_chapter_04.py tests/test_linear_algebra_chapters_4_8_artifacts.py -q` — **11 passed in 2.95s**.
- `pytest tests/test_linear_algebra_builders.py tests/test_linear_algebra_visual_compiler.py -q` — **20 passed in 0.26s**.
- `pytest tests/test_linear_algebra_ch04_strict_semantics.py tests/test_linear_algebra_chapter_04.py tests/test_linear_algebra_compiled_resources.py tests/test_linear_algebra_chapters_4_8_artifacts.py tests/test_linear_algebra_builders.py tests/test_linear_algebra_visual_compiler.py tests/test_linear_algebra_teaching_store.py tests/test_scene_command_dispatch.py -q` — **154 passed in 8.25s**, 2 paramiko deprecation warnings.
- `pytest tests/test_linear_algebra_ch04_strict_semantics.py tests/test_linear_algebra_subspace_family.py tests/test_linear_algebra_extended_plan_replay.py tests/test_scene_commands.py tests/test_geometry_3d_scene.py -q` — **99 passed in 3.13s**, 2 paramiko deprecation warnings.
- `pytest tests/test_scene_command_dispatch.py -k chapter_four_real -q` — **16 passed in 3.11s**.
- `pytest tests/test_linear_algebra_registry.py -q` — **1 failed in 0.22s**, exactly `KeyError: Unknown visualization recipe: draw.ch05.homogeneous.solution-space`. No registry check was weakened.

Remaining concern: the full registry suite still reports the pre-existing missing Chapter 5 recipe; Chapter 4 resources and host replay are independent of that downstream gap.
