# Plan 4 / Task 1 — atomic extended-topic loading

## Scope

Implemented the registry and runtime loading boundary for OpenSpec 5.1. A
chapter 4–8 topic now resolves a topic/artifact/contract/recipe/compiled/
snapshot one-to-one, and `CurriculumRegistry.commit_curriculum_bundle()` stages
the explanation and validated command plan together before an optional host
transaction. Source, artifact, contract, compiled, snapshot and plan failures
produce a structured `LoadDiagnostic` with topic, phase and field; the previous
scene/explanation fingerprints are carried on the rejected transaction.

The designer window now publishes the new topic identity only after the case
panes and explanation have both been prepared. A display failure restores the
complete `SceneSnapshot` (pane states, layout/lecture metadata, scene objects,
cameras and teaching identity) plus the previous explanation case. A pane
interactor callback is a hand-off point for the same transaction: it executes
the host at most once, finalizes the explanation/identity in that callback, and
removes every leftover `pending_plan` so a later renderer recreation cannot
replay it. Extended reviewed resources are exposed as an immutable published
runtime view when the checked-in release layout has no filesystem `published/`
row.

## Red/green evidence

Focused command:

```text
pytest tests/test_linear_algebra_registry_chapters_4_8.py \
  tests/test_linear_algebra_loading.py \
  tests/test_teaching_case_panes.py -q
13 passed
```

Registry and bundle regression:

```text
pytest tests/test_linear_algebra_registry.py \
  tests/test_agent_workspace_restore.py \
  tests/test_linear_algebra_registry_chapters_4_8.py \
  tests/test_teaching_case_panes.py -q
21 passed
```

The new tests cover one-to-one Chapter 8 resolution, stale-source rejection
before host commit, missing/mismatched snapshot diagnostics, complete
diagnostics, host-failure transaction handling, and exact-once host execution.
The workspace restore regression verifies that pane/scene metadata and the
old explanation fingerprint are preserved after a publication failure.
`validate_registry(catalog_registry())` is green for the exact
24/15/15/16/8/3/6/6 distribution and the `quadratic_level_set` capability.

## Minimal direct dependency repair

The pre-existing cold-start import path had a real cycle: importing
`services.scene_commands` eagerly imported `linear_algebra.visualizations`,
whose recipe builders imported `CommandPlan` while it was still being defined.
The smallest safe repair was to make the visual `CommandPlan` annotation
type-only and defer budget validation until operation validation. No command
semantics changed; this is covered by the focused import/test run.

## Rollback evidence

The registry does not mutate a host before `STAGED`. `SceneCommandService`
continues to own `begin → execute → commit/rollback`; the UI records and
restores the old `SceneSnapshot` if explanation/case publication fails. The
interactor callback and the synchronous fallback share one transaction and
clear pending plans before any later callback. Stale-source rejection leaves
the transaction rejected at `source_checked`, with the supplied previous scene
and explanation fingerprints unchanged. Snapshot/compiler/source exceptions
are converted into `LoadDiagnostic` rather than escaping as unstructured
`ValueError`/`OSError` failures.
