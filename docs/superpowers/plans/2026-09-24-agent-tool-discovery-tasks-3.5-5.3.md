# Agent Tool Discovery Implementation Plan: Events, Verification, and Rollout

> **For agentic workers:** REQUIRED SUB-SKILL: Use `openspec-executing-plans` to implement this plan task-by-task and sync completed work back to OpenSpec tasks.

**Goal:** Complete the dynamic-discovery turn contract with safe events, bounded observability, compatibility tests, and a reversible rollout.

**Architecture:** Keep the existing `AgentEvent` and web envelope, adding only optional discovery metadata. Add metadata-rich local catalog projection for future UI consumers without building UI. Verify retrieval, snapshots, same-batch rejection, budgets, cancellation, and provider compatibility with deterministic fakes before enabling the dynamic path by default.

**Tech Stack:** Python 3, pytest, existing Agent event envelope, SessionStore, provider fakes, OpenSpec CLI.

**Spec:** `openspec/changes/agent-tool-discovery/proposal.md`, `design.md`, `specs/mathagent-capabilities/spec.md`, `specs/mathagent-runtime/spec.md`, `tasks.md`; detailed rationale in `docs/superpowers/specs/2026-09-23-agent-tool-discovery-design.md`. This plan depends on `2026-09-24-agent-tool-discovery-tasks-1.1-2.2.md` and `2026-09-24-agent-tool-discovery-tasks-2.3-3.4.md`.

## Global Constraints

- Existing event envelope and required `tool_started`/`tool_finished` fields remain valid; discovery fields are optional and bounded.
- Events never carry full schemas, internal paths, credentials, renderer objects, raw long arguments, hidden reasoning, or stack traces.
- Session snapshot catalog is local presentation data and must never be reused as a provider catalog.
- Stage 1 includes no Skills explorer, toolbar changes, `ToolIntent`, or semantic `draw.*` capabilities.
- Search uses local deterministic metadata only and has no new dependency.
- Runtime limits are 8 total capability calls, 3 searches, 4 mutation calls, 9 provider requests, 8 active names, and 4+8 offered schemas.
- Non-native JSON/fenced `CommandPlan` behavior and Agent/Ask/Plan transaction boundaries remain compatible.

---

<!-- openspec-task: 3.5 -->
### Task 1: Preserve sequential dispatch and one final plan boundary

**Files:**
- Modify: `agent/runtime.py`
- Modify: `agent/capabilities/orchestrator.py` only if call sequencing requires adjustment
- Test: `tests/test_agent_runtime_loop.py`
- Test: `tests/test_agent_capability_e2e.py`

**Interfaces:**
- `_native_turn()` continues appending one assistant tool-call message and one correlated `ToolResultMessage` per provider call, in response order.
- `CapabilitySession.finish()` produces zero or one validated `CommandPlan`; reads after a valid staged mutation observe the staged `SceneIndex`.
- Agent executes automatically, Ask produces one approval ticket, and Plan remains pending without renderer mutation.

- [ ] **Step 1: Add a fake provider sequence `tool.search(scene.edit) -> scene.edit(point P) -> scene.find(P) -> final text`; assert the staged read sees P, the provider saw one plan boundary, and the renderer is unchanged until runtime execution.**
- [ ] **Step 2: Run `pytest tests/test_agent_runtime_loop.py::test_native_search_edit_find_composes_single_plan -q` and confirm the discovered-tool loop is not yet exercised.**
- [ ] **Step 3: Keep calls sequential and use the existing `AgentMessage.assistant_tool_calls`/`tool_result` transcript shape. Do not execute individual plans from handlers.**
- [ ] **Step 4: Add Ask and Plan variants using the same fake provider; assert Ask creates one approval requirement and Plan creates `plan_pending`, with no host operations. Run `pytest tests/test_agent_runtime_loop.py tests/test_agent_capability_e2e.py -q`.**
- [ ] **Step 5: Commit loop/mode regression tests and required correction.**

<!-- openspec-task: 4.1 -->
### Task 2: Extend web protocol validation for optional discovery fields

**Files:**
- Modify: `agent/web_protocol.py`
- Modify: `tests/test_agent_web_protocol.py`

**Interfaces:**
- `tool_started` may additionally contain `phase`, `search_revision`, `offered_tool_count`, and bounded `activated_names`.
- `tool_finished` may additionally contain the same discovery metadata; `result_kind` accepts existing kinds plus `search` and `description`.
- Older payloads with only required fields remain accepted; optional values are type-, length-, and item-count validated.

- [ ] **Step 1: Add a failing protocol test accepting a search lifecycle payload and another accepting an old `tool_finished` payload with no optional fields.**
- [ ] **Step 2: Add rejection tests for invalid phase, negative revision, non-integer offered count, more than 8 activated names, and overlong names; run `pytest tests/test_agent_web_protocol.py::test_capability_events_require_their_bounded_structured_fields -q`.**
- [ ] **Step 3: Validate only known optional fields with bounds; keep existing required field checks and event envelope version unchanged.**
- [ ] **Step 4: Run `pytest tests/test_agent_web_protocol.py -q`.**
- [ ] **Step 5: Commit protocol schema and tests.**

<!-- openspec-task: 4.1 -->
### Task 3: Emit ordered, sanitized discovery lifecycle summaries

**Files:**
- Modify: `agent/runtime.py`
- Modify: `agent/events.py` only if sanitizer bounds need a targeted extension
- Modify: `tests/test_agent_runtime_loop.py`
- Modify: `tests/test_agent_runtime_web_events.py`

**Interfaces:**
- `tool_started` includes `phase` (`discover|describe|invoke`), canonical name, category, mutation flag, and bounded argument summary.
- `tool_finished` uses `result_kind="search"` for `tool.search`, `"description"` for `tool.describe`, and existing kinds for other tools; includes stable error code, search revision, active names, and offered count where relevant.
- Event payloads remain JSON-safe through `AgentEvent.sanitize_event_payload()` and existing bridge projection.

- [ ] **Step 1: Add a runtime test asserting the event order for search, next-request activation, capability invocation, and plan composition.**
- [ ] **Step 2: Add a secret/long-query test asserting the persisted events include only a bounded sanitized summary and never the full query or credential value. Run the targeted runtime-event tests and confirm they fail before implementation.**
- [ ] **Step 3: Emit start/finish around dispatch in chronological order, derive result kind from canonical capability name, and add only approved optional fields. Avoid full input schema or raw tool result in events.**
- [ ] **Step 4: Run `pytest tests/test_agent_runtime_loop.py tests/test_agent_runtime_web_events.py tests/test_agent_web_protocol.py -q`; assert old event consumers still parse events lacking discovery metadata.**
- [ ] **Step 5: Commit event emission, sanitization, and regression tests.**

<!-- openspec-task: 4.2 -->
### Task 4: Record bounded per-turn discovery metrics

**Files:**
- Modify: `agent/capabilities/orchestrator.py`
- Modify: `agent/runtime.py`
- Test: `tests/test_agent_runtime_loop.py`

**Interfaces:**
- `CapabilitySession` exposes a JSON-safe metrics snapshot with `offered_tool_count_max`, `search_count`, `active_count_max`, `result_bytes_max`, and `terminal_reason`.
- Runtime emits one structured `logging` record named `agent_capability_metrics` per native turn; metrics contain no original query, arguments, schemas, or credentials.

- [ ] **Step 1: Add a failing `caplog` test that a native discovery turn logs counts and terminal reason but not the query text `private phrase`.**
- [ ] **Step 2: Run `pytest tests/test_agent_runtime_loop.py::test_native_discovery_metrics_are_bounded_and_redacted -q` and confirm no metrics record exists.**
- [ ] **Step 3: Track counts and max sizes at the session/runtime boundary. Emit the record from a `finally` path so normal, fallback, cancellation, and terminal exits all report one bounded summary.**
- [ ] **Step 4: Run the focused test for completed and cancelled turns; assert exactly one metrics record per native turn and no raw query/arguments.**
- [ ] **Step 5: Commit metrics tracking and tests.**

<!-- openspec-task: 4.3 -->
### Task 5: Keep the session catalog projection metadata-rich and separate

**Files:**
- Modify: `agent/ui_projection.py` only if projection shaping is needed
- Test: `tests/test_agent_ui_projection.py`
- Test: `tests/test_agent_capability_registry.py`

**Interfaces:**
- `build_session_snapshot(...)["capability_catalog"]` remains a JSON-safe local catalog with metadata and all supported core/discoverable specs, excluding internal operations.
- Provider tool lists are built exclusively via `CapabilityRegistrySnapshot.catalog_for_names(offered_names)`; no runtime path reads the session projection to construct native definitions.

- [ ] **Step 1: Update the snapshot test to assert metadata fields for all 11 Stage 1 names, no aliases/internal names, and JSON serialization with `allow_nan=False`.**
- [ ] **Step 2: Add a separation test proving the full session catalog is larger than the initial provider catalog while the first request still has exactly four tools.**
- [ ] **Step 3: Keep `build_session_snapshot()` as a projection of `build_default_registry().catalog()`; do not implement Skills UI, filtering controls, or manual activation.**
- [ ] **Step 4: Run `pytest tests/test_agent_ui_projection.py tests/test_agent_capability_registry.py tests/test_agent_runtime_loop.py -q`.**
- [ ] **Step 5: Commit projection compatibility tests and any narrowly necessary projection change.**

<!-- openspec-task: 5.1 -->
### Task 6: Verify scale, deterministic retrieval, and exact budget boundaries

**Files:**
- Modify: `tests/test_agent_capability_search.py`
- Modify: `tests/test_agent_capability_orchestrator.py`
- Modify: `tests/test_agent_runtime_loop.py`

**Interfaces:**
- Build a synthetic registry of at least 500 discoverable capabilities through the public registration API; search returns bounded result data and never sends more than 12 schemas to a fake native provider.
- No brittle wall-clock threshold is required; record elapsed time only as diagnostic output if useful.

- [ ] **Step 1: Add a synthetic 500-entry test with deterministic names/tags; assert repeated identical searches return identical ordered names, at most 8 matches, at most 3 near misses, and no schema in the result.**
- [ ] **Step 2: Add exact boundary assertions for 8 versus 9 total calls, 3 versus 4 searches, 4 versus 5 mutations, 8 versus 9 active capabilities, and 9 provider rounds.**
- [ ] **Step 3: Run `pytest tests/test_agent_capability_search.py tests/test_agent_capability_orchestrator.py tests/test_agent_runtime_loop.py -q`; correct boundary off-by-one errors without relaxing specified limits.**
- [ ] **Step 4: Commit scale and budget regression tests.**

<!-- openspec-task: 5.1 -->
### Task 7: Verify Stage 1 acceptance and provider compatibility matrix

**Files:**
- Modify: `tests/test_agent_runtime_loop.py`
- Modify: `tests/test_agent_capability_e2e.py`
- Modify: `tests/test_agent_provider.py`

**Interfaces:**
- Accepted existing-capability journey: `求导并标出切线` searches and activates `math.derive`; a later request receives its schema and returns through normal `CommandPlan` preview/staging.
- Unsupported semantic journey: `画一个 3D 曲面` yields explicit no-match/limitation and no guessed `draw.3d.surface` or raw operation.
- Compatibility journey: non-native provider sees no search tool; native transport failure uses same-provider fallback once; legacy alias resolves locally but is not advertised.

- [ ] **Step 1: Add fake-provider end-to-end fixtures for the accepted derivative/tangent journey and unsupported 3D surface journey. Assert host operations are empty for no-match.**
- [ ] **Step 2: Extend compatibility tests for both Chat Completions and Responses tool definitions and JSON/fenced fallback; run focused tests and verify a regression is exposed by intentionally using the full catalog in a local test expectation.**
- [ ] **Step 3: Keep fixtures deterministic and offline; do not call a live provider, embedding endpoint, filesystem export, or GUI renderer.**
- [ ] **Step 4: Run `pytest tests/test_agent_capability_e2e.py tests/test_agent_runtime_loop.py tests/test_agent_provider.py -q`.**
- [ ] **Step 5: Commit the acceptance and compatibility matrix.**

<!-- openspec-task: 5.2 -->
### Task 8: Run focused tests and Python compile checks

**Files:**
- No source files unless a focused regression is found
- Verification: capability, provider, runtime, protocol, projection, and scene-command tests

- [ ] **Step 1: Run `pytest tests/test_agent_capability_contracts.py tests/test_agent_capability_search.py tests/test_agent_capability_registry.py tests/test_agent_capability_tools.py tests/test_agent_capability_orchestrator.py tests/test_agent_capability_e2e.py tests/test_agent_runtime_loop.py tests/test_agent_runtime_web_events.py tests/test_agent_web_protocol.py tests/test_agent_provider.py tests/test_agent_ui_projection.py tests/test_scene_commands.py tests/test_scene_command_dispatch.py -q`.**
- [ ] **Step 2: Run `python -m compileall -q agent services tests`.**
- [ ] **Step 3: Run the full `pytest -q`; preserve unrelated worktree changes and report any environment-only skips separately.**
- [ ] **Step 4: If a test fails, add a focused regression first, make the smallest fix, rerun its focused test, then rerun the failed suite. Do not alter unrelated linear algebra/rendering changes.**
- [ ] **Step 5: Record exact pass/skip/failure counts in the implementation notes and commit only task-owned code/tests.**

<!-- openspec-task: 5.3 -->
### Task 9: Validate OpenSpec and document rollout/rollback

**Files:**
- Modify: `openspec/changes/agent-tool-discovery/tasks.md` only through `openspec-executing-plans` task synchronization
- Modify: `docs/superpowers/specs/2026-09-23-agent-tool-discovery-design.md` only if implementation changes a confirmed contract
- Verification: OpenSpec CLI and runtime rollback test

**Interfaces:**
- `AgentRuntime(dynamic_tool_discovery=True)` is the default rollout; `False` restores the complete eligible legacy native catalog for rapid rollback without a database/provider migration.
- `openspec validate agent-tool-discovery --strict` must pass; all task labels are synchronized by `openspec-executing-plans` as implementation completes.

- [ ] **Step 1: Add/confirm a runtime test that toggles dynamic discovery off and restores legacy catalog behavior without changing provider/model settings.**
- [ ] **Step 2: Run `openspec validate agent-tool-discovery --strict`; expected output is `Change 'agent-tool-discovery' is valid`.**
- [ ] **Step 3: Review the final diff against each requirement and verify no `mathagent-sidebar`, toolbar, `draw.*`, renderer API, or dependency change entered Stage 1.**
- [ ] **Step 4: Record enable/default and rollback instructions, focused/full test results, and any known limitations; update OpenSpec task checkboxes through the executing-plans workflow only.**
- [ ] **Step 5: Commit only the implementation-plan-owned verification notes or final narrowly scoped fixes; do not stage unrelated workspace modifications.**
