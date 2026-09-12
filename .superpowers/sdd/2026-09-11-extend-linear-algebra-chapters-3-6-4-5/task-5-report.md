# Task 5 report

Chapter 5 has eight descriptor-backed reviewed artifacts, compiled resources, and a chapter-scoped transactional index release. The release preserves the existing 70 Chapter 1–4 rows and produces 78 unique rows with eight Chapter 5 rows and no Chapter 6–8 rows.

The strict release now binds topic-specific roles, relation parameters, stages, invariants, and executable family operations.  Homogeneous/affine/fundamental topics consume matrix, rhs, particular, and nullspace evidence; consistency emits unique/none/infinite tableau operations; Gaussian and elementary topics consume distinct row-operation chains; least-squares topics recompute fit and residual orthogonality and validate normal equations.

Validation:

* `pytest tests/test_linear_algebra_chapter_05.py tests/test_linear_algebra_constraint_family.py tests/test_linear_algebra_matrix_tableau.py tests/test_linear_algebra_least_squares.py -q` — 35 passed.
* `pytest tests/test_linear_algebra_compiled_resources.py tests/test_linear_algebra_chapters_4_8_artifacts.py tests/test_linear_algebra_builders.py tests/test_linear_algebra_visual_compiler.py -q` — 25 passed.
* `compile_chapter_05(reviewed_payloads=reviewed_artifact_payloads())` completed successfully and atomically updated eight reviewed resources, eight compiled snapshots, and the aggregate index.

## Final mutation-audit fixes

The family compiler is now isolated in `linear_algebra/visualizations/families/chapter_05.py`.
It recomputes `A x_p = b`, `A N = 0`, nullspace completeness and pivot/free masks; classifies all three reviewed consistency systems by their ranks; applies each row operation and verifies every elementary matrix and final tableau; and recomputes least-squares coefficients, fit, residual and normal equations. Every entity is cross-checked against those values. Removing one invariant from one stage fails even when other stages still contain it.

Gaussian elimination uses `[[2,1],[4,3]]` and elimination/scaling/back-substitution. Elementary-matrix elimination uses `[[1,2],[2,5]]` with three independently checked elementary matrices. Each role, relation and stage owns disjoint real operation aliases, and stage witnesses are included in storyboard visibility. Required stage names now participate in the contract digest.

Final verification:

* Required Chapter 5/family suite: **35 passed**.
* Required compiled/artifact/builder/compiler suite: **25 passed**.
* `pytest tests/test_linear_algebra_ch05_strict_semantics.py tests/test_linear_algebra_ch04_strict_semantics.py -q`: **377 passed** (302 Chapter 5 checks and 75 Chapter 4 regression checks).
* The strict suite mutates every numeric leaf of every Chapter 5 relation parameter and entity, deletes each required parameter/entity/relation/stage and every per-stage invariant, and checks disjoint real alias coverage and claim-ledger closure.
* All eight plans execute and replay identically through the recording host; injected mid-plan failures preserve the existing host scene for execute and replay.
* Failure at each of all **17** publication replacements restores all prior reviewed, compiled and index bytes. Empty bundles fail before writing. Chapter 1–4's 70 index rows remain equal to the pre-Chapter-5 baseline, including digests.

The previously untracked Chapter 5 recipe/builder modules and their registry imports are included in this fix so a fresh checkout has the same execution path as the validated workspace. No plan or OpenSpec completion checkbox was changed.
