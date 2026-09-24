## 1. Registry metadata and deterministic search

- [ ] 1.1 Extend `CapabilitySpec` with family, title, tags, examples, exposure, status, and schema version; preserve catalog-version and old-field compatibility.
- [ ] 1.2 Mark the four core capabilities and the seven discoverable existing capabilities; keep internal renderer operations out of all model-facing catalogs.
- [ ] 1.3 Add lazy immutable search index and Chinese synonym table; implement deterministic ranking, stable ties, scene/status filters, bounded reasons and near misses.
- [ ] 1.4 Implement pure `tool.search` and `tool.describe` handlers with the agreed schemas and stable error codes.
- [ ] 1.5 Add unit fixtures for function/curve, tangent/derivative, projection, 3D view, export PNG, and teaching queries.

## 2. Session activation and safety

- [ ] 2.1 Add per-turn registry snapshot, `active_names`, `search_revision`, `search_count`, and offered-name snapshots to `CapabilitySession`.
- [ ] 2.2 Implement atomic replacement semantics: successful matches replace active set, valid no-match clears it, failed search preserves it.
- [ ] 2.3 Restrict `tool.describe` to active names and reject unactivated, disabled, deprecated, experimental, and scope-incompatible calls with stable errors before handler execution.
- [ ] 2.4 Preserve staged `SceneIndex` behavior and preview-before-stage for existing `scene.edit` and `math.derive`; verify no partial mutation on failure.
- [ ] 2.5 Enforce query/result/activation limits, eight total capability calls (including discovery), three-search and four-mutation sublimits, nine provider rounds, cancellation, timeout, cross-scene and terminal rollback rules.

## 3. Native runtime loop

- [ ] 3.1 Change native turns to send core-only catalog initially and core-plus-active schemas on continuation; freeze offered names before every provider request.
- [ ] 3.2 Feed successful search results into the session only after validation; reject same-batch calls to capabilities whose schema was not offered in that request.
- [ ] 3.3 Generate native definitions from existing provider adapter fields and remove low-level renderer operation enumeration from the system prompt.
- [ ] 3.4 Keep non-native JSON/fenced `CommandPlan` fallback unchanged and verify provider rejection triggers only the existing fallback path.
- [ ] 3.5 Preserve sequential dispatch, one final plan boundary, Agent/Ask/Plan semantics, and existing duplicate/call/result/operation limits.

## 4. Events, projection and compatibility

- [ ] 4.1 Extend lifecycle summaries with optional discovery phase, search revision, activated names, offered count, and bounded result metadata; preserve bridge validator compatibility.
- [ ] 4.2 Add runtime metrics/log summaries for offered tool count, search count, activated count, result size, and terminal reason without persisting sensitive inputs.
- [ ] 4.3 Keep session catalog projection serializable and metadata-rich for future Skills UI, without implementing UI changes in this stage.

## 5. Verification and rollout

- [ ] 5.1 Add registry/search/activation/runtime/provider compatibility tests covering at least 500 synthetic capabilities, all budget boundaries and the confirmed acceptance examples.
- [ ] 5.2 Run focused Agent/scene/bridge tests, the full Python suite, and compile checks; fix regressions without touching unrelated worktree changes.
- [ ] 5.3 Run `openspec validate agent-tool-discovery --strict` and record the rollout flag/rollback method before enabling dynamic catalog by default.
