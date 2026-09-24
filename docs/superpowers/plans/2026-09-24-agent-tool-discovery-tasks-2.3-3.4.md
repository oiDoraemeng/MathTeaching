# Agent Tool Discovery Implementation Plan: Dispatch and Native Runtime

> **For agentic workers:** REQUIRED SUB-SKILL: Use `openspec-executing-plans` to implement this plan task-by-task and sync completed work back to OpenSpec tasks.

**Goal:** Enforce active capability permissions and use request-by-request native catalogs while preserving transactional scene execution and legacy provider fallback.

**Architecture:** `CapabilitySession` checks lifecycle, scope, active set, offered-name snapshot, budgets, and plan validity before staging. `AgentRuntime._native_turn` sends a frozen core-plus-active catalog each round; search affects only the next request. Native tool prompting is separated from the existing JSON/fenced plan prompt so fallback behavior remains intact.

**Tech Stack:** Python 3, pytest, existing provider-neutral `ProviderToolCall`, `SceneIndex`, `SceneCommandService`, Chat Completions and Responses adapters.

**Spec:** `openspec/changes/agent-tool-discovery/proposal.md`, `design.md`, `specs/mathagent-capabilities/spec.md`, `specs/mathagent-runtime/spec.md`, `tasks.md`; detailed rationale in `docs/superpowers/specs/2026-09-23-agent-tool-discovery-design.md`. This plan depends on the registry/session interfaces in `2026-09-24-agent-tool-discovery-tasks-1.1-2.2.md`.

## Global Constraints

- Model calls are accepted only if their name was in the exact `offered_names` snapshot sent on that provider request.
- Search only affects the next provider request; same-response search plus call to a newly discovered tool is rejected as `tool_not_activated`.
- Each request has at most 4 core plus 8 active schemas; each turn has 8 total capability calls including discovery, 3 searches, 4 mutation calls, and 9 provider requests.
- Every mutating result passes `SceneCommandService.preview` before it changes staged `SceneIndex`; only normal finish produces one `CommandPlan`.
- Cancellation, timeout, terminal limits, protocol errors, and scene conflict discard staged operations and cannot call renderer execution.
- Only native function-tools providers use discovery. Non-native and JSON/fenced plan fallback receive no fake search tool.
- No low-level renderer operation, Python, filesystem handle, Qt object, or PyVista object becomes a model tool.
- Stage 1 excludes semantic `draw.*`, toolbar changes, `ToolIntent`, and Skills UI.

---

<!-- openspec-task: 2.3 -->
### Task 1: Gate dispatch by active set, lifecycle, and scene scope

**Files:**
- Modify: `agent/capabilities/orchestrator.py`
- Modify: `agent/capabilities/registry.py`
- Test: `tests/test_agent_capability_orchestrator.py`

**Interfaces:**
- Add `CapabilityRegistry.set_runtime_disabled(name: str, disabled: bool = True) -> None` and `is_runtime_disabled(name: str) -> bool`; this is the live emergency gate, while metadata/schema remains turn-snapshotted.
- `CapabilitySession.dispatch()` returns a `CapabilityResult.error` using stable codes: `tool_not_activated`, `capability_disabled`, `capability_deprecated`, `experimental_capability_unavailable`, or `scene_scope_mismatch` before calling a protected handler.
- `tool.describe` requires its requested name to be in the current `active_names`; `tool.search`, `tool.describe`, `scene.inspect`, and `scene.find` remain core-callable.

- [ ] **Step 1: Add failing tests using a handler spy: inactive `scene.edit`, active-disabled capability, deprecated capability, experimental without opt-in, wrong-scene capability, and inactive `tool.describe` all return the expected code with zero spy calls.**
- [ ] **Step 2: Run `pytest tests/test_agent_capability_orchestrator.py -q` and confirm guards are missing.**
- [ ] **Step 3: Add permission checks before `registry_snapshot.dispatch()`. Validate a describe name after schema validation but before metadata projection. Check emergency disabled state on the live source registry, not only the frozen snapshot.**
- [ ] **Step 4: Run `pytest tests/test_agent_capability_orchestrator.py tests/test_agent_capability_registry.py -q`; verify direct `registry.dispatch()` unit tests remain an internal API and session dispatch is the protected runtime API.**
- [ ] **Step 5: Commit lifecycle/scope guards and tests.**

<!-- openspec-task: 2.3 -->
### Task 2: Preserve discovery authorization across errors and scene changes

**Files:**
- Modify: `agent/capabilities/orchestrator.py`
- Test: `tests/test_agent_capability_orchestrator.py`

**Interfaces:**
- `CapabilitySession.dispatch()` treats recoverable capability errors as tool results but never adds their plans to staged state.
- A successful `view.control` scene mode change updates the session `SceneIndex`; subsequent searches use the new scene and old active names remain unusable if their scope no longer matches.

- [ ] **Step 1: Add failing tests for an error result not staging a plan and for an activated 2D capability being rejected after a valid switch to 3D.**
- [ ] **Step 2: Run the targeted orchestrator tests and confirm the scene-scope assertion fails.**
- [ ] **Step 3: Re-evaluate live scene scope on every dispatch and search, while leaving the frozen tool schema unchanged. Require a fresh search for a capability in the new scope.**
- [ ] **Step 4: Run `pytest tests/test_agent_capability_orchestrator.py tests/test_agent_capability_tools.py -q`.**
- [ ] **Step 5: Commit the scope-transition tests and implementation.**

<!-- openspec-task: 2.4 -->
### Task 3: Make plan staging and terminal abort atomic

**Files:**
- Modify: `agent/capabilities/orchestrator.py`
- Test: `tests/test_agent_capability_orchestrator.py`

**Interfaces:**
- Add `CapabilitySession.abort() -> CapabilityTurn`, which clears candidate operations/summaries/target scene, restores a detached `SceneIndex` from the turn's initial `SceneSnapshot`, and returns a terminal error without a plan.
- Keep `SceneCommandService.preview(plan)` before `SceneIndex.apply_operations(expanded_operations)`; failed preview must leave index, operations, and summaries unchanged.

- [ ] **Step 1: Add a failing regression test: stage a valid point edit, then dispatch a mutating handler whose plan fails preview; assert the turn has no plan and the staged index/operations are reset after abort.**
- [ ] **Step 2: Run `pytest tests/test_agent_capability_orchestrator.py -q` and confirm staged state currently remains after terminal failure.**
- [ ] **Step 3: Store the initial snapshot in the session, keep the existing preview-before-apply order, and call `abort()` for terminal validation/scene-conflict paths. Do not mutate the live renderer during abort.**
- [ ] **Step 4: Run `pytest tests/test_agent_capability_orchestrator.py tests/test_scene_commands.py -q`; assert a normal `finish()` still composes exactly one plan.**
- [ ] **Step 5: Commit atomic stage/abort behavior and tests.**

<!-- openspec-task: 2.5 -->
### Task 4: Enforce discovery and turn budgets at session boundaries

**Files:**
- Modify: `agent/capabilities/contracts.py`
- Modify: `agent/capabilities/orchestrator.py`
- Test: `tests/test_agent_capability_orchestrator.py`

**Interfaces:**
- Add constants `MAX_CAPABILITY_SEARCHES = 3`, `MAX_ACTIVE_CAPABILITIES = 8`, and `MAX_PROVIDER_ROUNDS = 9`; keep existing `MAX_TOOL_CALLS = 8` and `MAX_MUTATING_CALLS = 4` authoritative.
- `search_count` increments for every `tool.search` attempt; the fourth attempt terminates with `search_limit_exceeded`. Total capability calls include search and describe.
- Session terminal error prevents additional dispatch and invokes `abort()`; no terminal path may yield a composed plan.

- [ ] **Step 1: Add boundary tests for calls 8/9, searches 3/4, active candidates 8/9, and mutations 4/5. Assert the first over-limit call returns the agreed code and does not invoke its handler.**
- [ ] **Step 2: Run `pytest tests/test_agent_capability_orchestrator.py -q` and confirm new discovery-limit assertions fail.**
- [ ] **Step 3: Enforce limits before handler dispatch and before active-set commit. Use a terminal code for total/search/mutation budget exhaustion and clear staged candidate state via `abort()`.**
- [ ] **Step 4: Run `pytest tests/test_agent_capability_orchestrator.py -q`; verify boundary calls do not exceed raw result or plan limits.**
- [ ] **Step 5: Commit bounded session limits and tests.**

<!-- openspec-task: 2.5 -->
### Task 5: Make cancellation, timeout, and terminal exit discard staged work

**Files:**
- Modify: `agent/runtime.py`
- Modify: `agent/capabilities/orchestrator.py`
- Test: `tests/test_agent_runtime_loop.py`

**Interfaces:**
- `_native_turn(...) -> tuple[AgentResponse, CapabilityTurn]` checks stop state before provider calls, before each dispatch, before `finish()`, and before returning a normal plan.
- A terminal `CapabilityTurn.error` is returned through `abort()`; it never calls normal `finish()` and never produces `plan_composed`.

- [ ] **Step 1: Add a fake provider that returns a search/edit sequence and requests cancellation after the edit result; assert status is stopped/rejected, host operations are empty, and no plan/approval event occurs.**
- [ ] **Step 2: Run `pytest tests/test_agent_runtime_loop.py::test_native_cancel_discards_staged_capability_plan -q` and confirm it fails.**
- [ ] **Step 3: Route cancellation and session terminal conditions through `staged.abort()` and ensure provider loop exits immediately. Catch timeout only at the existing provider boundary; do not retry a timed-out tool loop.**
- [ ] **Step 4: Run `pytest tests/test_agent_runtime_loop.py tests/test_agent_capability_orchestrator.py -q`.**
- [ ] **Step 5: Commit terminal abort path and runtime tests.**

<!-- openspec-task: 3.1 -->
### Task 6: Send a bounded dynamic catalog to native providers

**Files:**
- Modify: `agent/runtime.py`
- Modify: `agent/capabilities/orchestrator.py`
- Test: `tests/test_agent_runtime_loop.py`

**Interfaces:**
- Before every provider request call `offered_names = staged.freeze_offered_names()` and build `catalog = staged.registry_snapshot.catalog_for_names(offered_names)`.
- Initial `offered_names` is exactly four core tools; continuations are four core plus current active names in stable order.
- Keep existing provider signatures `request_tools(messages, catalog)` and `stream_tools(messages, catalog, on_event=...)` unchanged.

- [ ] **Step 1: Change the fake native provider test to return `tool.search` for `scene.edit`, then return `scene.edit` on the next request; assert request 1 has four tools and request 2 has core plus the active schema.**
- [ ] **Step 2: Run `pytest tests/test_agent_runtime_loop.py::test_native_tool_loop_injects_canonical_catalog_and_composes_once -q` and confirm current full-catalog expectation fails.**
- [ ] **Step 3: Rebuild catalog immediately before each `request_tools`/`stream_tools` call from the frozen turn snapshot; preserve transcript correlation and the existing maximum of nine provider rounds.**
- [ ] **Step 4: Run `pytest tests/test_agent_runtime_loop.py tests/test_agent_provider.py -q`; assert every request contains no more than 12 tool definitions.**
- [ ] **Step 5: Commit dynamic catalog loop and updated fake provider tests.**

<!-- openspec-task: 3.1 -->
### Task 7: Add an explicit rollback switch for dynamic catalog rollout

**Files:**
- Modify: `agent/runtime.py`
- Modify: `agent/capabilities/orchestrator.py`
- Test: `tests/test_agent_runtime_loop.py`

**Interfaces:**
- Add optional `AgentRuntime(..., dynamic_tool_discovery: bool = True)`; default enables the confirmed Stage 1 flow.
- When disabled, native requests use the legacy complete non-internal catalog and the session is placed in compatibility mode where all eligible discoverable names are considered offered/active for that turn; core security checks and command validation remain enabled.
- The flag is constructor configuration only; do not add a persisted setting or change provider credentials.

- [ ] **Step 1: Add a failing test creating `AgentRuntime(..., dynamic_tool_discovery=False)` with the existing one-call fake; assert the full legacy catalog is sent and `scene.edit` still works.**
- [ ] **Step 2: Run the test and confirm the constructor rejects the new keyword.**
- [ ] **Step 3: Add the constructor flag and explicit compatibility-session initialization; keep default behavior dynamic and keep internal capabilities excluded.**
- [ ] **Step 4: Run `pytest tests/test_agent_runtime_loop.py -q`; assert default runtime still starts with four core tools and rollback mode is isolated to its instance.**
- [ ] **Step 5: Commit the rollback switch and tests.**

<!-- openspec-task: 3.2 -->
### Task 8: Reject calls absent from the exact request offer

**Files:**
- Modify: `agent/runtime.py`
- Modify: `agent/capabilities/orchestrator.py`
- Test: `tests/test_agent_runtime_loop.py`

**Interfaces:**
- Before dispatch, `_native_turn` checks each provider call canonical name against the frozen `offered_names` for the request that produced it.
- Search success updates activation only for the next request. An unoffered same-batch call returns `tool_not_activated`, is appended as a normal tool result, and invokes no handler.

- [ ] **Step 1: Add a fake response containing `tool.search("tangent")` and `math.derive` in the same response; use a handler spy and assert `math.derive` is not called until a subsequent provider request.**
- [ ] **Step 2: Run the new runtime test and confirm both calls are currently dispatched.**
- [ ] **Step 3: Freeze and retain `offered_names` per response; canonicalize aliases only through that request snapshot, then return stable rejection for any absent name.**
- [ ] **Step 4: Add a follow-up fake request that calls `math.derive` after receiving its schema; run `pytest tests/test_agent_runtime_loop.py -q`.**
- [ ] **Step 5: Commit offered-snapshot enforcement and tests.**

<!-- openspec-task: 3.3 -->
### Task 9: Keep provider schema generation metadata-neutral

**Files:**
- Modify: `services/agent_provider.py` only if tests expose a regression
- Test: `tests/test_agent_provider.py`

**Interfaces:**
- Existing `_tool_definitions(catalog, protocol)` continues mapping only `name`, `description`, and `input_schema` to OpenAI-compatible function definitions.
- New fields (`family`, `tags`, `exposure`, `status`, `schema_version`) remain local metadata and never become function arguments or protocol-specific schema fields.

- [ ] **Step 1: Extend both Chat Completions and Responses tests with a catalog entry containing discovery metadata; assert the serialized native function definition has only protocol fields and the unchanged input schema.**
- [ ] **Step 2: Run `pytest tests/test_agent_provider.py::AgentProviderTests::test_chat_tool_protocol_serializes_calls_results_and_catalog tests/test_agent_provider.py::AgentProviderTests::test_responses_tool_protocol_uses_function_call_output_items -q` and confirm discovery metadata is absent from both native schemas.**
- [ ] **Step 3: Preserve the existing `_tool_definitions` contract; change code only if metadata is currently forwarded.**
- [ ] **Step 4: Run `pytest tests/test_agent_provider.py -q` and verify both native protocols still serialize function calls/results.**
- [ ] **Step 5: Commit only the focused provider regression test and any required adapter correction.**

<!-- openspec-task: 3.3 -->
### Task 10: Separate native instructions from the JSON plan fallback prompt

**Files:**
- Modify: `services/agent_provider.py`
- Modify: `agent/agent.py`
- Test: `tests/test_agent_provider.py`
- Test: `tests/test_agent_runtime_loop.py`

**Interfaces:**
- Add `NATIVE_TOOL_SYSTEM_PROMPT`: tell the model to call only schemas supplied in the current request, search before using undisclosed capabilities, and never invent renderer operations.
- Preserve `SYSTEM_PROMPT` for the existing JSON/fenced `CommandPlan` fallback, since that path still requires its established command contract.
- `MathTeacherAgent.native_tool_messages()` must stop enumerating all canonical capability names; it adds only generic bounded-tool-loop instructions.

- [ ] **Step 1: Replace the test that expects every low-level command in the native prompt with tests that the native prompt names only current supplied tools and contains no renderer operation list.**
- [ ] **Step 2: Run the focused provider/runtime prompt tests and confirm the native prompt assertions fail.**
- [ ] **Step 3: Use the native-only prompt in `request_tools`, `stream_tools`, and Responses streaming; keep `_request` on the existing fallback `SYSTEM_PROMPT`. Remove capability-name enumeration from `native_tool_messages()`.**
- [ ] **Step 4: Run `pytest tests/test_agent_provider.py tests/test_agent_runtime_loop.py -q`; assert the JSON fallback still succeeds using the same provider/model.**
- [ ] **Step 5: Commit prompt isolation and tests.**

<!-- openspec-task: 3.4 -->
### Task 11: Preserve non-native and native-transport fallback behavior

**Files:**
- Modify: `agent/runtime.py` only if fallback is affected
- Test: `tests/test_agent_runtime_loop.py`
- Test: `tests/test_agent_provider.py`

**Interfaces:**
- `_uses_native_tools()` remains the gate for discovery; providers without `supports_native_tools` and callable `request_tools` continue through `respond`/`respond_stream` only.
- Native transport rejection retains the existing one-time same-provider fallback and emits sanitized `capability_fallback`; it never retries with another model or injects `tool.search` into the JSON path.

- [ ] **Step 1: Add a non-native fake provider that records `create_plan` messages and assert it never receives a tool catalog or a `tool.search` message.**
- [ ] **Step 2: Run `pytest tests/test_agent_runtime_loop.py -q` and confirm the compatibility assertions pass or expose a changed path.**
- [ ] **Step 3: Keep native transport failure handling on the existing fallback branch; redact credentials and bound its reason before event persistence.**
- [ ] **Step 4: Run `pytest tests/test_agent_runtime_loop.py::test_native_tool_transport_failure_uses_same_provider_json_fallback tests/test_agent_runtime_loop.py::test_native_tool_rejection_falls_back_to_streaming_text tests/test_agent_provider.py -q`.**
- [ ] **Step 5: Commit fallback regression coverage and any narrowly scoped fix.**
