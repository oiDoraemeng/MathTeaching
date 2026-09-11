# Plan 2 / Task 3 review

## Spec Compliance

**Needs fixes.** The commit adds `publish_chapter`/`unpublish_chapter`, uses the store's sibling-temp + `os.replace` writer, preserves unrelated chapter entries, and adds the requested snapshot fields with backward-compatible decoding. The stale-source path already returns a diagnostic (`linear_algebra/teaching/store.py:194-201`) and is not regressed.

However, `publish_chapter` does not implement the brief's required validation of source/contract/snapshot before replacing the index. At `linear_algebra/teaching/store.py:127-152`, it validates chapter/topic/revision and loads a published artifact, but never loads or verifies a compiled snapshot, never checks its source hash, and never validates the visual contract/contract digest. Thus an artifact can be indexed even when its compiled resource is absent or stale. The commit also does not modify `linear_algebra/teaching/data/index.json`, despite the task explicitly listing preservation/update of that payload as a task-scoped file; this is acceptable only if the existing payload is intentionally unchanged, but should be covered by a fixture/assertion.

## Strengths

- Failed validation occurs before the index write, and the stable writer performs a sibling temporary write followed by atomic replacement (`store.py:152`, `store.py:405-418`).
- Chapter replacement is isolated by `chNN.` prefix; unpublish removes only matching dictionary entries (`store.py:157-161`).
- Input validation rejects bool/non-positive chapter and revision values and unsafe topic IDs (`store.py:129-143`).
- Snapshot metadata is serialized and legacy payloads still decode with empty defaults (`visualizations/snapshots.py:35-76`); `snapshot_from` records a contract digest and scene family (`snapshots.py:94-110`).
- The added tests cover failed publish preserving the prior payload and chapter-isolated unpublish (`tests/test_linear_algebra_teaching_store.py:71-89`).

## Issues

1. **P1 — missing compiled snapshot/contract/source validation.** `publish_chapter` accepts any existing published artifact and copies its `source_hash` into the index, without requiring a corresponding compiled snapshot or checking snapshot source/contract identity. This violates the central atomic release gate and can publish an unusable/stale chapter. Add the snapshot/contract checks before mutating the payload and regression tests for missing snapshot, stale source hash, and contract mismatch. File: `linear_algebra/teaching/store.py:127-152`.

2. **P2 — no task-level coverage for chapter 1–3 index preservation/lookup and the release gates.** The two new tests exercise only synthetic index filtering and an unknown topic. Add tests against the real `teaching/data/index.json` and all required validation branches. File: `tests/test_linear_algebra_teaching_store.py:71-89`.

The report's two failed compiled-resource tests are downstream dependency gaps (chapter 4–8 compiled JSON/recipes are produced by later tasks), not by themselves a Task 3 defect. They should remain tracked separately from the missing validation above.

## Assessment

**Needs fixes.** Atomic file replacement, unpublish isolation, stale diagnostic behavior, and snapshot metadata are solid, but the chapter publication API currently lacks the required compiled snapshot/contract validation and therefore does not safely enforce the release contract.
