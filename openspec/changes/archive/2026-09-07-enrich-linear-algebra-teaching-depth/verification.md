# Verification Record

## Automated checks

- `python -m linear_algebra.validation`: passed, 54 catalog topics with chapter counts 24/15/15.
- `python -m pytest -q`: passed, 669 tests.
- `ui/agent_web`: `pnpm test -- --run` passed, 53 tests across 17 files.
- `ui/agent_web`: `pnpm build` passed.
- `openspec validate --changes enrich-linear-algebra-teaching-depth --strict`: passed.

## Artifact audit status

The opt-in artifact audit is implemented in `linear_algebra.validation` and emits
chapter counts, published count, claim count, stale-source count, per-topic plan
digests, and bounded diagnostics. No `MATH3D_TEACHING_ARTIFACT_ROOT` was present
in this checkout, so the audit correctly reports that the 54 published artifacts
are not yet available. Tasks 5.1-5.3, 7.6, and 7.7 therefore remain open.

The chapter coverage API is available through
`linear_algebra.teaching.content_validation.validate_chapter_artifacts`. The
automated evidence writer is `scripts/write_linear_algebra_verification.py`;
it refuses to create a success report unless all four checks pass and exactly 54
published topic digests are available.
