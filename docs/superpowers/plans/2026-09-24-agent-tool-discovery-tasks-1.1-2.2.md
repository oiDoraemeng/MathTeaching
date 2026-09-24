# Agent Tool Discovery Implementation Plan: Registry and Session Discovery

> **For agentic workers:** REQUIRED SUB-SKILL: Use `openspec-executing-plans` to implement this plan task-by-task and sync completed work back to OpenSpec tasks.

**Goal:** Add bounded metadata-based capability discovery and turn-scoped atomic activation without exposing the full catalog to the model.

**Architecture:** Extend the existing `CapabilitySpec` registry with exposure/lifecycle metadata, build an immutable local lexical search index from registry snapshots, and implement `tool.search`/`tool.describe` as typed capabilities. `CapabilitySession` owns active names and commits search results atomically; handlers continue to return JSON data or `CommandPlan` values and never touch a renderer.

**Tech Stack:** Python 3, dataclasses, `jsonschema` Draft 2020-12, pytest, existing `SceneIndex` and `CapabilityRegistry`.

**Spec:** `openspec/changes/agent-tool-discovery/proposal.md`, `design.md`, `specs/mathagent-capabilities/spec.md`, `specs/mathagent-runtime/spec.md`, `tasks.md`; detailed rationale in `docs/superpowers/specs/2026-09-23-agent-tool-discovery-design.md`.

## Global Constraints

- The initial provider catalog contains exactly `tool.search`, `tool.describe`, `scene.inspect`, and `scene.find`.
- Existing discoverable names are `scene.edit`, `scene.clear`, `math.calculate`, `math.derive`, `view.control`, `result.export`, and `teaching.explain`.
- Registry catalog version remains `1`; new metadata defaults are `family=general`, `exposure=discoverable`, `status=stable`, and `schema_version=1`.
- Search query length is 1-512 characters; default result limit is 6, hard maximum is 8; near misses are at most 3; active names are at most 8.
- Search is deterministic and local; no embedding API, remote index, MCP service, or new runtime dependency.
- Search replaces the active set; valid no-match clears it; invalid search preserves it.
- Internal renderer operations are never model-facing capabilities; no `draw.*`, toolbar, or Skills UI work belongs to this change.
- Every mutating capability still passes `SceneCommandService.preview` before staged state changes.
- New Agent modules must not import PySide6 or PyVista.

---

<!-- openspec-task: 1.1 -->
### Task 1: Extend the capability metadata contract

**Files:**
- Modify: `agent/capabilities/contracts.py`
- Modify: `agent/capabilities/__init__.py`
- Test: `tests/test_agent_capability_contracts.py`

**Interfaces:**
- Produces `CapabilitySpec(..., family="general", title=None, tags=(), examples=(), exposure="discoverable", status="stable", schema_version=1)`; append fields after existing fields so current positional construction remains valid.
- `CapabilitySpec.to_dict()` emits `title` using `title or name`, plus JSON-safe arrays for tags/examples and the lifecycle/exposure/schema fields.
- Add separate `CapabilityExposure` and `CapabilityLifecycle` string enums; do not reuse result `CapabilityStatus` (`ok`, `no_op`, `error`).

- [ ] **Step 1: Add a failing metadata round-trip test**

```python
def test_capability_metadata_defaults_and_round_trip() -> None:
    spec = CapabilitySpec("x.test", "math", "test", {"type": "object", "additionalProperties": False}, "data")
    payload = spec.to_dict()
    assert (payload["family"], payload["title"], payload["exposure"], payload["status"], payload["schema_version"]) == (
        "general", "x.test", "discoverable", "stable", 1
    )
    assert payload["tags"] == [] and payload["examples"] == []
```

- [ ] **Step 2: Run `pytest tests/test_agent_capability_contracts.py::test_capability_metadata_defaults_and_round_trip -q` and confirm it fails because metadata is absent.**
- [ ] **Step 3: Add the appended dataclass fields, enum values, bounded metadata validation, and `to_dict()` projection. Reject unknown exposure/status values, non-positive schema versions, more than 8 tags/examples, and overlong metadata strings. Export the public enums from `agent/capabilities/__init__.py`.**
- [ ] **Step 4: Run `pytest tests/test_agent_capability_contracts.py -q`; confirm the new test and existing positional/JSON-safe contract tests pass.**
- [ ] **Step 5: Commit only `agent/capabilities/contracts.py`, `agent/capabilities/__init__.py`, and `tests/test_agent_capability_contracts.py`.**

<!-- openspec-task: 1.1 -->
### Task 2: Preserve catalog compatibility while adding exposure projections

**Files:**
- Modify: `agent/capabilities/registry.py`
- Modify: `tests/test_agent_capability_registry.py`

**Interfaces:**
- `CapabilityRegistry.catalog() -> dict[str, Any]` remains the serializable local catalog for compatibility and includes the new metadata while continuing to omit aliases.
- Add `CapabilityRegistry.catalog_for_names(names: Iterable[str]) -> list[dict[str, Any]]`; preserve caller name order, reject unknown/internal/non-callable names, and return full schemas only for requested names.
- Add `CapabilityRegistry.core_names() -> tuple[str, ...]` in deterministic order; discovery tools are registered in Task 6, so this method returns currently registered core entries rather than hard-coded absent names.

- [ ] **Step 1: Add failing tests for exposure filtering and schema projection.** Assert requested names are ordered as requested, an internal capability is omitted/rejected, and the ordinary local catalog still contains metadata without aliases.
- [ ] **Step 2: Run `pytest tests/test_agent_capability_registry.py -q` and confirm the new projection assertions fail.**
- [ ] **Step 3: Implement catalog projection from `CapabilitySpec.to_dict()`; ensure only `core` or eligible `discoverable` entries can be returned by the model-facing method. Keep `catalog()` behavior sorted and all non-internal local entries visible.**
- [ ] **Step 4: Run `pytest tests/test_agent_capability_registry.py -q`; confirm current nine-capability compatibility tests pass with updated metadata assertions.**
- [ ] **Step 5: Commit only the registry and its tests.**

<!-- openspec-task: 1.2 -->
### Task 3: Classify existing capabilities and reserve the core set

**Files:**
- Modify: `agent/capabilities/registry.py`
- Modify: `agent/capabilities/contracts.py`
- Test: `tests/test_agent_capability_registry.py`

**Interfaces:**
- Existing `scene.inspect` and `scene.find` specs receive `exposure="core"`; the other seven existing specs receive explicit family/title/tags/examples and remain `exposure="discoverable", status="stable"`.
- `catalog_for_names()` is the only provider projection API; no low-level command operation is added to `_specifications()` or aliases.

- [ ] **Step 1: Add a failing test asserting the two context tools are core and all other existing canonical tools are discoverable.**
- [ ] **Step 2: Run `pytest tests/test_agent_capability_registry.py -q` and verify the exposure assertion fails.**
- [ ] **Step 3: Add concise Chinese/English metadata to the nine existing specs. Use tags/examples that describe existing behavior only; do not claim semantic surface or drawing capabilities that are not implemented.**
- [ ] **Step 4: Run `pytest tests/test_agent_capability_registry.py tests/test_agent_capability_tools.py -q`; verify aliases remain resolvable but absent from every catalog.**
- [ ] **Step 5: Commit the metadata classification and regression tests.**

<!-- openspec-task: 1.3 -->
### Task 4: Build the lazy immutable search index and synonym vocabulary

**Files:**
- Create: `agent/capabilities/search_terms.py`
- Create: `agent/capabilities/search_index.py`
- Modify: `agent/capabilities/registry.py`
- Test: `tests/test_agent_capability_search.py`

**Interfaces:**
- `CapabilitySearchHit(spec: CapabilitySpec, raw_score: int, reasons: tuple[str, ...])` and `CapabilitySearchPage(matches: tuple[CapabilitySearchHit, ...], near_misses: tuple[CapabilitySearchHit, ...])` are frozen dataclasses in `search_index.py`.
- `CapabilitySearchIndex(specs: Iterable[CapabilitySpec]).search(query: str, *, scene: str, family: str | None, tags: tuple[str, ...], limit: int, include_experimental: bool) -> CapabilitySearchPage` is pure and performs no registry mutation.
- `search_terms.py` exports an immutable `SYNONYM_GROUPS` mapping and `expand_query_terms(query: str) -> tuple[str, ...]`.

- [ ] **Step 1: Add failing normalization/synonym tests for `切线 -> tangent/derivative`, `函数 -> function/curve`, and case-insensitive English names.**
- [ ] **Step 2: Run `pytest tests/test_agent_capability_search.py -q` and confirm imports or expected terms fail.**
- [ ] **Step 3: Implement NFKC/lowercase normalization, English token extraction, CJK phrase/bigram matching, and the independent synonym table. Include groups for function/curve, tangent/derivative, projection, surface/intersection, fit/view, export, and explain/teaching.**
- [ ] **Step 4: Run the focused synonym tests and confirm deterministic output order.**
- [ ] **Step 5: Commit the new index vocabulary and tests.**

<!-- openspec-task: 1.3 -->
### Task 5: Implement deterministic ranking, scope filters, and bounded results

**Files:**
- Modify: `agent/capabilities/search_index.py`
- Modify: `agent/capabilities/registry.py`
- Test: `tests/test_agent_capability_search.py`

**Interfaces:**
- Registry exposes `search(query, *, scene, family=None, tags=(), limit=6, include_experimental=False) -> CapabilitySearchPage` using a lazily rebuilt immutable index snapshot.
- Weights are canonical name 100, alias 80, tag/synonym 60, title 40, description 20, example 10; exact scene adds 15 and `both` adds 5. Tie-break on canonical name; normalize scores only for display after ranking.

- [ ] **Step 1: Add failing tests for exact-name-over-alias ordering, scene/family/tag filtering, stable ties, experimental opt-in, and disabled/deprecated exclusion.**
- [ ] **Step 2: Run `pytest tests/test_agent_capability_search.py -q` and confirm filter/ranking assertions fail.**
- [ ] **Step 3: Implement lexical scoring over canonical names, aliases, tags, title, description, examples, family, and scope. Return at most `limit` matches and three near misses; cap reasons at three strings of 64 characters. Registration marks the index dirty; a query builds and swaps one immutable snapshot.**
- [ ] **Step 4: Run `pytest tests/test_agent_capability_search.py tests/test_agent_capability_registry.py -q`; include a registration-after-first-search test proving the next search sees the new spec without mutating an in-flight snapshot.**
- [ ] **Step 5: Commit index/ranking changes and tests.**

<!-- openspec-task: 1.4 -->
### Task 6: Register bounded `tool.search`

**Files:**
- Create: `agent/capabilities/discovery_tools.py`
- Modify: `agent/capabilities/registry.py`
- Modify: `agent/capabilities/__init__.py`
- Test: `tests/test_agent_capability_registry.py`

**Interfaces:**
- Register `tool.search` as core with a strict schema: required trimmed `query` (1-512); optional `scene` (`2d|3d`), `family` (max 32), `tags` (max 8 items, each max 32), `limit` (default 6, 1-8), and `include_experimental` (default false).
- Search handler is pure and returns `CapabilityResult.data` with `status`, compact `matches`, compact `near_misses`, and `limitation`; activation metadata is added by `CapabilitySession` in Tasks 9-10.
- Invalid schemas return the registry's normal structured `CapabilityError`; valid empty search returns `status="no_match"`, not an exception.

- [ ] **Step 1: Add a failing registry dispatch test using `ToolCall("s1", "tool.search", {"query": "切线", "scene": "2d"})`; assert the returned data names `math.derive` and contains no `input_schema`.**
- [ ] **Step 2: Run `pytest tests/test_agent_capability_registry.py -q` and confirm `tool.search` is unknown.**
- [ ] **Step 3: Add the search spec and pure handler. Read scene scope from the passed `SceneIndex` when no scene is supplied; map incompatible explicit scope to `scene_scope_mismatch`. Keep no-match as normal data and add a short limitation instead of guessing `scene.edit`.**
- [ ] **Step 4: Add schema-boundary tests for query lengths 0/1/512/513, limits 1/6/8/9, tags 8/9, and experimental opt-in; run `pytest tests/test_agent_capability_registry.py -q`.**
- [ ] **Step 5: Commit the discovery search capability and focused tests.**

<!-- openspec-task: 1.4 -->
### Task 7: Register safe `tool.describe`

**Files:**
- Modify: `agent/capabilities/discovery_tools.py`
- Modify: `agent/capabilities/registry.py`
- Test: `tests/test_agent_capability_registry.py`

**Interfaces:**
- Register `tool.describe` as core; input is exactly `{ "name": <bounded capability name> }`.
- Registry snapshot method `describe(name: str) -> dict[str, Any]` returns name/title/description/family/scene_scope/status/schema_version/input_schema/examples, never aliases, dependencies, handler references, or renderer operations.
- Session permission that restricts describe to active names is implemented in Plan 2; this task tests only metadata projection and strict schema validation.

- [ ] **Step 1: Add a failing test that describing `math.derive` produces its complete schema and examples but omits `dependencies`, `aliases`, and handler internals.**
- [ ] **Step 2: Run `pytest tests/test_agent_capability_registry.py -q` and confirm `tool.describe` is unknown.**
- [ ] **Step 3: Register the bounded spec and implement metadata-only description against the registry search snapshot. Reject names over 128 characters and unknown names with stable bounded errors.**
- [ ] **Step 4: Run `pytest tests/test_agent_capability_registry.py tests/test_agent_capability_contracts.py -q`; assert the serialized result stays within `MAX_TOOL_RESULT_BYTES`.**
- [ ] **Step 5: Commit describe implementation and tests.**

<!-- openspec-task: 1.5 -->
### Task 8: Lock retrieval quality with intent fixtures

**Files:**
- Modify: `tests/test_agent_capability_search.py`
- Modify: `agent/capabilities/search_terms.py` only when a fixture exposes a real synonym gap

**Interfaces:**
- `search_names(query: str, scene: str) -> tuple[str, ...]` may be a small test helper that calls the public registry search and extracts canonical match names; production ranking remains in the index.

- [ ] **Step 1: Add table-driven fixtures for `函数图像` (existing `scene.edit` only when query describes a supported curve), `切线` (`math.derive`), `切换到 3D 并适配视图` (`view.control`), `导出 PNG` (`result.export`), and `解释投影` (`teaching.explain`).**
- [ ] **Step 2: Add the Stage 1 unsupported fixture: `画一个 3D 曲面` must not return a fabricated `draw.3d.surface` or renderer operation.**
- [ ] **Step 3: Run `pytest tests/test_agent_capability_search.py -q`; adjust only metadata/synonym terms, not ranking weights, unless an asserted weight-order rule fails.**
- [ ] **Step 4: Commit the fixture set and any justified synonym additions.**

<!-- openspec-task: 2.1 -->
### Task 9: Freeze registry metadata for one capability turn

**Files:**
- Modify: `agent/capabilities/registry.py`
- Modify: `agent/capabilities/orchestrator.py`
- Modify: `agent/capabilities/search_index.py`
- Test: `tests/test_agent_capability_orchestrator.py`

**Interfaces:**
- Add immutable `CapabilityRegistrySnapshot(revision: int, specs: Mapping[str, CapabilitySpec], aliases: Mapping[str, str], handlers: Mapping[str, CapabilityHandler], search_index: CapabilitySearchIndex)` with `get()`, `resolve_name()`, `catalog_for_names()`, `search()`, `describe()`, and `dispatch()` methods.
- `CapabilityRegistry.snapshot() -> CapabilityRegistrySnapshot` copies current specs/handlers/aliases and builds or shares the immutable search-index snapshot; each successful `register()` increments the registry revision.
- `CapabilityOrchestrator.start(snapshot: SceneSnapshot) -> CapabilitySession` passes both the frozen capability snapshot and source registry reference to the session.

- [ ] **Step 1: Add a failing test: capture a snapshot, register a new capability, then prove snapshot catalog/search remains unchanged while a new snapshot sees the registration.**
- [ ] **Step 2: Run `pytest tests/test_agent_capability_orchestrator.py::test_registry_snapshot_is_stable_for_turn -q` and confirm the snapshot API is absent.**
- [ ] **Step 3: Implement the immutable registry snapshot and monotonically increasing revision. Keep public registration mutable only on `CapabilityRegistry`; do not expose mutable dicts from the snapshot.**
- [ ] **Step 4: Run `pytest tests/test_agent_capability_orchestrator.py tests/test_agent_capability_registry.py -q`; confirm existing direct registry dispatch remains compatible.**
- [ ] **Step 5: Commit snapshot API and tests.**

<!-- openspec-task: 2.1 -->
### Task 10: Add discovery state to `CapabilitySession`

**Files:**
- Modify: `agent/capabilities/orchestrator.py`
- Test: `tests/test_agent_capability_orchestrator.py`

**Interfaces:**
- `CapabilitySession` gains `registry_snapshot`, `source_registry`, `active_names: tuple[str, ...] = ()`, `search_revision: int = 0`, `search_count: int = 0`, `offered_names: tuple[str, ...] = ()`, and `offered_revision: int`.
- Add `freeze_offered_names() -> tuple[str, ...]`, returning deterministic core names followed by active names from the same turn snapshot.
- `CapabilityOrchestrator.start()` initializes the session with an empty active set and the scene scope derived from `SceneIndex.scene_mode`.

- [ ] **Step 1: Add a failing test that a fresh session has no active names, revision/count zero, and a stable four-name core offer after the discovery specs exist.**
- [ ] **Step 2: Run `pytest tests/test_agent_capability_orchestrator.py -q` and confirm the new state/accessor is absent.**
- [ ] **Step 3: Add the fields and deterministic offer snapshot method. Store the initial `SceneSnapshot` (or an immutable copy) so a terminal abort can discard staged state in later tasks.**
- [ ] **Step 4: Run the orchestrator tests; assert returned tuples cannot be mutated and a later active-set replacement changes only the next frozen offer.**
- [ ] **Step 5: Commit session state and tests.**

<!-- openspec-task: 2.2 -->
### Task 11: Commit successful search activation atomically

**Files:**
- Modify: `agent/capabilities/orchestrator.py`
- Modify: `agent/capabilities/discovery_tools.py`
- Test: `tests/test_agent_capability_orchestrator.py`

**Interfaces:**
- `CapabilitySession.dispatch(call: ToolCall) -> CapabilityResult` counts `tool.search` attempts, validates against the frozen registry snapshot, and on a valid search atomically sets `active_names`, increments `search_revision`, and annotates result data with `activated_names` and `search_revision`.
- Active set is the stable-order unique list of matched discoverable names, capped at 8; near misses never activate.

- [ ] **Step 1: Add failing tests for a matched search replacing an earlier set, preserving only names in `matches`, and incrementing revision once.**
- [ ] **Step 2: Run the focused orchestrator test and confirm search currently does not alter `active_names`.**
- [ ] **Step 3: Implement post-handler session validation against the frozen spec snapshot and exposure/status/scene scope; commit the full new set only after every candidate validates. Keep the handler itself pure.**
- [ ] **Step 4: Run `pytest tests/test_agent_capability_orchestrator.py -q` and assert the returned activation metadata and next offered snapshot agree.**
- [ ] **Step 5: Commit atomic match activation and tests.**

<!-- openspec-task: 2.2 -->
### Task 12: Define no-match and failed-search state transitions

**Files:**
- Modify: `agent/capabilities/orchestrator.py`
- Modify: `tests/test_agent_capability_orchestrator.py`

**Interfaces:**
- A valid `status="no_match"` search atomically replaces `active_names` with `()` and increments `search_revision`.
- Schema/argument errors, search-limit errors, index exceptions, and candidate-validation failures preserve `active_names` and `search_revision`; search attempt count still increments for every `tool.search` call so malformed retries cannot evade the search budget.

- [ ] **Step 1: Add separate failing tests for valid no-match clearing and invalid query preserving the previous active set and revision.**
- [ ] **Step 2: Run `pytest tests/test_agent_capability_orchestrator.py -q` and confirm the two transition assertions fail.**
- [ ] **Step 3: Implement commit-after-validation semantics. Map index failures to a bounded `capability_search_failed` result; never partially replace the active set.**
- [ ] **Step 4: Run `pytest tests/test_agent_capability_orchestrator.py tests/test_agent_capability_search.py -q`; verify search count/revision/active names for success, no-match, and failure cases.**
- [ ] **Step 5: Commit transition tests and implementation.**
