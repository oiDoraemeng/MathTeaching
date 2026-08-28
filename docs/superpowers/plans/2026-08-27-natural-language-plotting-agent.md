# Natural-Language Plotting Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a categorized, schema-validated capability layer that lets the existing math teaching agent use natural language to inspect, create, modify, clear, explain, control, and safely export 2D and 3D scenes.

**Architecture:** Introduce a capability catalog and pure staged-scene tool layer beneath the provider loop. Providers translate their native function-calling formats into one canonical `ToolCall`/`CapabilityResult` protocol; the runtime composes validated scene operations into the existing transactional `SceneCommandService`, protects approval with a scene snapshot fingerprint, and projects sanitized lifecycle events into the existing web UI.

**Tech Stack:** Python 3.11, PySide6, SymPy restricted parsers, `jsonschema` Draft 2020-12, OpenAI-compatible Chat Completions and Responses APIs, TypeScript/React/Vite, Vitest, pytest, pnpm.

---

## Execution Rules

- Work in `D:\github\Math3DTeaching`; preserve unrelated dirty-worktree changes and stage only files named by each task.
- Follow test-driven development: add the failing focused test first, run it, implement the smallest passing change, then run the focused test suite again.
- Keep provider payloads, persisted events, capability results, and UI-facing state JSON-safe. Do not persist prompts, credentials, model reasoning, renderer objects, or full attachment contents.
- The natural-language agent calls the new capability registry directly. The legacy MCP adapter and `ToolRegistry` remain compatibility boundaries and must never receive `execute=True` from this flow.
- Each logical task may be committed after its focused tests pass. Use a narrow `git add -- <listed paths>` and a descriptive commit message; do not commit unrelated files.

## Post-Implementation Note (2026-08-28)

This plan was written against a module layout that the repository has since
refactored. The work is complete and verified, but **do not treat the file paths
in the task bodies above as current** — roughly two thirds of them no longer
exist. The table below maps each planned path to where the implementation
actually landed.

| Planned path | Actual path |
| --- | --- |
| `agent/provider.py`, `agent/openai_provider.py`, `agent/models.py` | `services/agent_provider.py` |
| `agent/scene_commands.py` | `services/scene_commands.py` |
| `agent/persistence.py` | `agent/session_store.py` |
| `agent/agent_bridge.py` | `ui/agent_bridge.py` + `agent/web_protocol.py` |
| `agent/agent_web_protocol.py` | `agent/web_protocol.py` |
| `agent/prompts.py`, `agent/skills.py` | `agent/prompt_manager.py`, `agent/skill_manager.py` (+ `agent/prompts/`, `agent/instructions/` content files) |
| `ui/agent_web/src/bridge.ts` | `ui/agent_web/src/bridge/qtBridge.ts` |
| `ui/agent_web/src/components/Conversation.tsx` | `ui/agent_web/src/components/Timeline.tsx` |
| `tests/test_agent_math_capabilities.py` | `tests/test_agent_capability_tools.py` |

Snapshot projection lives in `agent/ui_projection.py`, which the plan never
named. Task 5.1's prompt work split across two namespaces: canonical capability
names go to native tool requests via `CANONICAL_CAPABILITY_NAMES`
(`agent/agent.py`), while `SYSTEM_PROMPT` in `services/agent_provider.py`
correctly lists `CommandPlan` **operation** names for the JSON fallback path —
these are different identifier sets, not a missed migration.

**Checkbox state:** the 117 checkboxes above were never ticked during execution.
`openspec/changes/natural-language-plotting-agent/tasks.md` is the authoritative
completion record; all 20 of its items are done. This file is kept as the
historical design-time plan rather than being retro-ticked, so it should be read
as "what we intended to do" and not as a live progress tracker.

**Fallback behaviour changed after this plan was written.** Task 11 specified a
one-shot JSON retry when a provider rejects native tools. A later fix made that
retry stream instead, because the non-streaming retry was masking a server-side
tool-schema rejection and silently degrading every turn to non-streaming output.
The JSON/fenced `CommandPlan` parsing, single-retry limit, same-provider
constraint, and fingerprint guard are all unchanged; only the streaming property
and the fallback event's `reason` differ. See the updated
`spec.md` / `design.md` / `tasks.md` 3.2 for the current contract.

## Task Sequence

<!-- openspec-task: 1.1 -->
### Task 1: Define canonical capability contracts and result envelopes

**Files:**
- Create: `agent/capabilities/__init__.py`
- Create: `agent/capabilities/contracts.py`
- Create: `tests/test_agent_capability_contracts.py`

- [ ] Write failing contract tests for a JSON-safe `CapabilitySpec`, `ToolCall`, `CapabilityError`, and `CapabilityResult`. Cover the nine required canonical names, the six categories, all `SceneScope` values, and `CapabilityResult.ok()` rejecting an envelope with both `data` and `plan`.
- [ ] In `agent/capabilities/contracts.py`, add immutable dataclasses/enums for `CapabilitySpec`, `ToolCall`, `CapabilityError`, `CapabilityResult`, `SceneScope`, and `CapabilityStatus`. Make successful result envelopes contain exactly one of `data`, `plan`, or `explanation`; make errors contain only `code`, `message`, and optional `field`.
- [ ] Add `to_dict()` methods that normalize enums/dataclasses recursively into standard JSON values, plus a `json_safe()` validation helper that rejects non-finite floats and non-serializable values. Keep payload serialization independent of PySide6, plotters, or scene objects.
- [ ] Define catalog version `1`, canonical tool-name/category constants, and an ASCII alias validator using `[A-Za-z][A-Za-z0-9_-]{0,63}`. Allow localized labels only as display metadata, never as canonical identifiers.
- [ ] Run `./.venv/Scripts/python.exe -m pytest tests/test_agent_capability_contracts.py -q`; commit only the new capability package and test with `git add -- agent/capabilities/__init__.py agent/capabilities/contracts.py tests/test_agent_capability_contracts.py`.

<!-- openspec-task: 1.2 -->
### Task 2: Add bounded Draft 2020-12 input validation and dependency metadata

**Files:**
- Modify: `pyproject.toml`
- Modify: `requirements.txt`
- Modify: `agent/capabilities/contracts.py`
- Create: `agent/capabilities/validation.py`
- Modify: `tests/test_agent_capability_contracts.py`

- [ ] Add failing tests that reject unknown input fields, unsupported schema keywords, non-finite numeric values, payloads exceeding `16 * 1024` UTF-8 bytes, strings/arrays over their declared bounds, and a malformed capability schema before dispatch.
- [ ] Add `jsonschema>=4.23,<5` to the project dependency sources, then install/sync it through the repository's normal environment setup before rerunning the tests.
- [ ] Implement `validate_tool_call(spec, call)` with `Draft202012Validator`. Require every input schema to be an object with `additionalProperties: false`, bounded strings/arrays/numbers where applicable, and a schema describing only JSON-compatible values.
- [ ] Make validation return bounded `CapabilityResult.error(code="invalid_tool_arguments", ...)` values rather than leaking `jsonschema` exception details. Use deterministic `field` paths and cap messages at 512 characters.
- [ ] Add `MAX_TOOL_ARGUMENT_BYTES = 16 * 1024` in one limits module or contract constant, and route all registry/orchestrator dispatch through this validator before a handler receives arguments.
- [ ] Run `./.venv/Scripts/python.exe -m pytest tests/test_agent_capability_contracts.py -q`; commit the dependency and validation files with `git add -- pyproject.toml requirements.txt agent/capabilities/contracts.py agent/capabilities/validation.py tests/test_agent_capability_contracts.py`.

<!-- openspec-task: 1.3 -->
### Task 3: Implement the versioned capability registry and default v1 catalog

**Files:**
- Create: `agent/capabilities/registry.py`
- Modify: `agent/capabilities/__init__.py`
- Create: `tests/test_agent_capability_registry.py`

- [ ] Start with failing tests asserting that `build_default_registry().catalog()` advertises exactly these canonical names: `scene.inspect`, `scene.find`, `scene.edit`, `scene.clear`, `math.calculate`, `math.derive`, `view.control`, `result.export`, and `teaching.explain`.
- [ ] Test that the catalog has version `1`, groups every entry into the defined category set, exposes dependency metadata/result kind/scope/mutating flag, is deterministically ordered by canonical name, and omits aliases.
- [ ] Implement `CapabilityRegistry.register()`, `get()`, `catalog()`, and `dispatch()`. Reject duplicate canonical names and undeclared handler dependencies during registration; validate calls before invoking a handler.
- [ ] Define explicit bounded Draft 2020-12 schemas for every v1 tool. Ensure `scene.inspect.limit` is at most 50, `scene.find.limit` is at most 20, export accepts only a basename, and `view.control` supports only `set_mode` and `fit`.
- [ ] Wire default handlers lazily enough that registry import remains free of renderer/UI imports. The handler implementations may be added in later tasks, but catalog construction must fail clearly if a registered handler is unavailable.
- [ ] Run `./.venv/Scripts/python.exe -m pytest tests/test_agent_capability_registry.py -q`; commit the registry and its tests with `git add -- agent/capabilities/__init__.py agent/capabilities/registry.py tests/test_agent_capability_registry.py`.

<!-- openspec-task: 1.4 -->
### Task 4: Preserve legacy tool aliases through a compatibility facade

**Files:**
- Modify: `agent/tool_registry.py`
- Modify: `agent/capabilities/registry.py`
- Modify: `tests/test_agent_tools.py`
- Modify: `tests/test_agent_capability_registry.py`

- [ ] Add failing compatibility tests for every supported legacy name in `agent/tool_registry.py`: it must resolve to one canonical capability and produce a canonical result name.
- [ ] Add alias maps to `CapabilitySpec`/`CapabilityRegistry` with collision checks across canonical names and aliases. Treat aliases as case-sensitive and reject aliases that are not ASCII identifiers.
- [ ] Refactor `ToolRegistry` into a small facade over `CapabilityRegistry`: translate legacy requests into `ToolCall`, preserve its public compatibility methods, and return canonical `CapabilityResult` dictionaries without changing existing callers' expected shape unnecessarily.
- [ ] Verify that `catalog()` and provider tool declarations include only canonical names, even when an alias can be dispatched internally.
- [ ] Ensure the compatibility facade cannot select execution mode or invoke the legacy MCP adapter; it can only construct/dispatch the canonical capability call.
- [ ] Run `./.venv/Scripts/python.exe -m pytest tests/test_agent_tools.py tests/test_agent_capability_registry.py -q`; commit only the facade/registry/test changes with `git add -- agent/tool_registry.py agent/capabilities/registry.py tests/test_agent_tools.py tests/test_agent_capability_registry.py`.

<!-- openspec-task: 2.1 -->
### Task 5: Build a renderer-free staged SceneIndex for inspect and find

**Files:**
- Create: `agent/capabilities/scene_index.py`
- Create: `tests/test_agent_scene_index.py`

- [ ] Write failing tests that construct a `SceneIndex` from the existing `SceneSnapshot`, inspect aliases/types with deterministic ordering, enforce the 50/20 result limits, and return `not_found` without falling back to current UI selection.
- [ ] Add tests proving `SceneIndex` does not import `pyvista`, `PySide6`, `ui.designer_window`, or live renderer state, and that an index can be cloned/applied without mutating its input snapshot.
- [ ] Implement normalized entries for scene mode, curves, geometries, aliases, stable IDs, and minimal safe metadata. Define `SceneIndex.from_snapshot(snapshot)`, `inspect()`, `find()`, `clone()`, and `apply_operations()`.
- [ ] Make `inspect` and `find` accept only documented filters and return bounded, JSON-safe summaries. Do not include plotter objects, mesh instances, attachments, or raw command histories.
- [ ] Preserve staging semantics: `apply_operations()` updates only the in-memory index so subsequent calls in the same turn observe earlier planned edits, while the renderer remains untouched.
- [ ] Run `./.venv/Scripts/python.exe -m pytest tests/test_agent_scene_index.py -q`; commit with `git add -- agent/capabilities/scene_index.py tests/test_agent_scene_index.py`.

<!-- openspec-task: 2.2 -->
### Task 6: Implement scene, view, clear, and export capability handlers

**Files:**
- Create: `agent/capabilities/scene_tools.py`
- Modify: `agent/capabilities/registry.py`
- Modify: `ui/designer_window.py`
- Create: `tests/test_agent_capability_tools.py`
- Modify: `tests/test_agent_tools.py`

- [ ] Add failing handler tests for `scene.edit`, `scene.clear`, `view.control`, and `result.export`: aliases resolve against `SceneIndex`, scoped clears handle empty scope as a no-op, and every mutating handler returns an unexecuted command-plan fragment.
- [ ] Test explicit error results for an invalid alias, a 2D operation targeting a 3D-only entity (and inverse), unsupported `view.control` operations such as rotation/zoom/visibility, and unsafe export names including path separators or non-`.png` extensions.
- [ ] Implement handlers using typed plan fragments only. Resolve aliases/types from `SceneIndex`; return `not_found`, `scene_scope_mismatch`, or `unsupported_operation` errors rather than guessing a selected object.
- [ ] Restrict `view.control` v1 to `set_mode` and `fit`. For `result.export`, validate a safe basename and defer path resolution to the GUI host; resolve output only under `.math/exports/` and use `SceneCommandService`/the existing screenshot path rather than an arbitrary filename.
- [ ] Update `DesignerWindow`'s command application/export pathway so it receives a validated basename and writes only inside the resolved export directory. Preserve existing manual export behavior and add a regression test for it.
- [ ] Run `./.venv/Scripts/python.exe -m pytest tests/test_agent_capability_tools.py tests/test_agent_tools.py -q`; commit with `git add -- agent/capabilities/scene_tools.py agent/capabilities/registry.py ui/designer_window.py tests/test_agent_capability_tools.py tests/test_agent_tools.py`.

<!-- openspec-task: 2.3 -->
### Task 7: Implement controlled math calculation and derivation handlers

**Files:**
- Create: `agent/capabilities/math_tools.py`
- Modify: `agent/capabilities/registry.py`
- Modify: `geometry/cas_curve.py`
- Create: `tests/test_agent_math_capabilities.py`

- [ ] Create failing tests for bounded `math.calculate` arithmetic and symbolic differentiation, plus `math.derive` generating curve derivatives/tangent information and supported 3D surface/intersection derivations.
- [ ] Add negative tests for unsafe expression constructs, arbitrary attribute access, unbounded functions, parser failures, and unsupported 2D intersections. Each must fail before plan creation with `unsafe_expression` or `unsupported_operation` and no SymPy traceback.
- [ ] Extract or reuse the existing allowlisted parsing machinery in `geometry/cas_curve.py`; do not call unrestricted `sympy.sympify` on capability input. Make the allowlist, symbol set, expression length, and output size explicit and testable.
- [ ] Implement `math.calculate` as an explanatory data result and `math.derive` as either explanatory data or a typed scene plan fragment when the requested result is drawable. Keep all returned expressions/coordinates JSON-safe and size bounded.
- [ ] Register the handlers only after their schemas/limits are present in the default registry. Do not add direct renderer access or legacy `ToolRegistry` calls.
- [ ] Run `./.venv/Scripts/python.exe -m pytest tests/test_agent_math_capabilities.py tests/test_agent_capability_registry.py -q`; commit with `git add -- agent/capabilities/math_tools.py agent/capabilities/registry.py geometry/cas_curve.py tests/test_agent_math_capabilities.py`.

<!-- openspec-task: 2.4 -->
### Task 8: Compose validated mutating fragments into one staged target-scene plan

**Files:**
- Create: `agent/capabilities/orchestrator.py`
- Modify: `agent/capabilities/scene_index.py`
- Modify: `agent/scene_commands.py`
- Create: `tests/test_agent_capability_orchestrator.py`

- [ ] Write failing tests for a multi-call turn where an edit is followed by inspect/find and sees staged state, while the source snapshot and renderer host receive no calls until final execution.
- [ ] Add tests that several mutating fragments compose in call order into one target scene, reject mixed 2D/3D fragments with `scene_conflict`, and inject exactly one leading `scene.set_mode` command when needed.
- [ ] Implement an orchestrator that accumulates normalized `CapabilityResult` objects, expands raw fragments through the existing `SceneCommandService.preview()` path, and applies expanded operations to a cloned `SceneIndex`.
- [ ] Extend scene command validation/composition so the correct target mode is inserted once only when absent; reject contradictory mode changes instead of appending duplicate mode operations.
- [ ] Emit a single composed `CommandPlan` only after all tool calls succeed/no-op. Non-mutating results remain ordered by call ID and retain no renderer references.
- [ ] Run `./.venv/Scripts/python.exe -m pytest tests/test_agent_capability_orchestrator.py tests/test_agent_scene_index.py -q`; commit with `git add -- agent/capabilities/orchestrator.py agent/capabilities/scene_index.py agent/scene_commands.py tests/test_agent_capability_orchestrator.py`.

<!-- openspec-task: 2.5 -->
### Task 9: Enforce per-turn tool, mutation, payload, plan, and loop limits

**Files:**
- Modify: `agent/capabilities/contracts.py`
- Modify: `agent/capabilities/orchestrator.py`
- Modify: `agent/capabilities/validation.py`
- Modify: `tests/test_agent_capability_orchestrator.py`
- Modify: `tests/test_agent_capability_contracts.py`

- [ ] Add failing tests for the fixed limits: 8 tool calls, 4 mutating calls, 16 KiB arguments, 32 KiB result payloads, 32 raw plan operations, 128 expanded plan operations, and a third identical normalized call.
- [ ] Define the limit constants in one importable location and make validation/orchestration count canonical name plus normalized arguments, not provider-native JSON formatting, for loop detection.
- [ ] Before every handler call, reject exhausted call/mutation/argument limits with a bounded terminal error. After a handler returns, check serialized result size and plan operation caps before staging it.
- [ ] Use `tool_loop_detected` for the third matching normalized invocation. Ensure all terminal limit failures preserve the last valid staged index and never invoke the renderer or partial transaction.
- [ ] Test an exact-boundary success and one-over-boundary failure for each counter, including a composed plan that would expand past the cap.
- [ ] Run `./.venv/Scripts/python.exe -m pytest tests/test_agent_capability_contracts.py tests/test_agent_capability_orchestrator.py -q`; commit with `git add -- agent/capabilities/contracts.py agent/capabilities/validation.py agent/capabilities/orchestrator.py tests/test_agent_capability_contracts.py tests/test_agent_capability_orchestrator.py`.

<!-- openspec-task: 3.1 -->
### Task 10: Add provider-native function-call and function-result transcript support

**Files:**
- Modify: `agent/provider.py`
- Modify: `agent/openai_provider.py`
- Modify: `agent/models.py`
- Modify: `tests/test_agent_provider.py`

- [ ] Start with failing provider transcript tests that serialize the same canonical tool turn for both Chat Completions and Responses APIs, including multiple sequential call IDs and matching function-result messages.
- [ ] Extend message models so assistant function calls and function results retain `call_id`, canonical tool name, JSON arguments, and bounded result JSON while remaining independent of a specific provider SDK.
- [ ] In the Chat serializer, produce function definitions, assistant `tool_calls`, and `tool` messages correlated by `tool_call_id`. In the Responses serializer, produce `function_call` and `function_call_output` items correlated by the same `call_id`.
- [ ] Set `parallel_tool_calls=false` in both native request formats and assert it in mocked request tests. Preserve streaming text behavior and existing no-tool providers.
- [ ] Parse native function requests into canonical `ToolCall` objects; reject malformed arguments as capability errors without making a second provider request solely to repair JSON.
- [ ] Run `./.venv/Scripts/python.exe -m pytest tests/test_agent_provider.py -q`; commit with `git add -- agent/provider.py agent/openai_provider.py agent/models.py tests/test_agent_provider.py`.

<!-- openspec-task: 3.2 -->
### Task 11: Implement catalog injection, bounded tool continuation, and same-provider fallback

**Files:**
- Modify: `agent/agent.py`
- Modify: `agent/provider.py`
- Modify: `agent/openai_provider.py`
- Modify: `agent/capabilities/orchestrator.py`
- Modify: `tests/test_agent_runtime_loop.py`
- Modify: `tests/test_agent_provider.py`

- [ ] Add failing tests showing the runtime passes the versioned canonical catalog to a native-tool-capable provider, executes tool calls one at a time, feeds each result back with its call ID, and stops after the configured bounded continuation count.
- [ ] Make the agent/provider feature negotiation explicit: native tool calling is attempted when supported; rule-based/local providers retain the established JSON `CommandPlan` fallback path.
- [ ] Implement the continuation loop around the capability orchestrator, preserving transcript order and only requesting the next provider response after the previous tool result has been recorded.
- [ ] On native tool transport/format incompatibility, retry the same provider exactly once using the existing JSON one-shot `CommandPlan` path. Emit a sanitized `capability_fallback` event; do not switch models or expose internal errors to the user.
- [ ] Ensure an unsupported native capability, invalid schema call, or loop limit becomes an in-band capability result, allowing the provider to answer safely when continuation budget remains.
- [ ] Run `./.venv/Scripts/python.exe -m pytest tests/test_agent_runtime_loop.py tests/test_agent_provider.py -q`; commit with `git add -- agent/agent.py agent/provider.py agent/openai_provider.py agent/capabilities/orchestrator.py tests/test_agent_runtime_loop.py tests/test_agent_provider.py`.

<!-- openspec-task: 3.3 -->
### Task 12: Carry immutable scene fingerprints through validation, approval, and execution

**Files:**
- Modify: `agent/models.py`
- Modify: `agent/runtime.py`
- Modify: `agent/scene_commands.py`
- Modify: `ui/designer_window.py`
- Modify: `tests/test_agent_runtime.py`
- Modify: `tests/test_agent_bridge.py`

- [ ] Write failing tests that compute a SHA-256 fingerprint from `SceneSnapshot.to_json()`, persist it under `turn.validation["base_scene_fingerprint"]`, and pass it through automatic execution and approval paths.
- [ ] Extend the scene host protocol with a GUI-thread `check_scene_fingerprint(expected)` operation. Implement it in the existing host proxy by snapshotting live state immediately before `begin_transaction()` and comparing the hash.
- [ ] Extend `SceneCommandService.execute(plan, expected_scene_fingerprint=...)` to perform that comparison before transaction creation. On mismatch, raise/return `scene_changed_since_plan`, start no transaction, and leave the approval ticket invalid.
- [ ] Update worker/runtime entry points to receive the immutable snapshot used for planning instead of reconstructing mutable context later. Keep the fingerprint out of `CommandPlan` itself.
- [ ] Cover automatic execution, manual approval after an unrelated scene edit, and repeated approval of a stale ticket. Confirm rollback and no renderer mutation on conflict.
- [ ] Run `./.venv/Scripts/python.exe -m pytest tests/test_agent_runtime.py tests/test_agent_bridge.py -q`; commit with `git add -- agent/models.py agent/runtime.py agent/scene_commands.py ui/designer_window.py tests/test_agent_runtime.py tests/test_agent_bridge.py`.

<!-- openspec-task: 3.4 -->
### Task 13: Preserve Agent/Ask/Plan semantics, approvals, cancellation, and rollback

**Files:**
- Modify: `agent/runtime.py`
- Modify: `agent/agent.py`
- Modify: `agent/models.py`
- Modify: `tests/test_agent_runtime.py`
- Modify: `tests/test_agent_runtime_loop.py`

- [ ] Add failing tests for Agent auto-execution, Ask no-plan answers, Plan preview-only behavior, duplicate approval rejection, cancellation before dispatch, cancellation during continuation, and cancellation after preview but before commit.
- [ ] Refactor runtime state transitions so provider/tool results, composed plans, and final prose share a single turn record without overwriting an existing explanation with a plan or vice versa.
- [ ] Ensure Ask turns never execute even if a provider emits a mutating capability result; transform this into a preview/no-op result according to existing user-mode behavior and record the decision.
- [ ] Make approval ticket consumption atomic. On duplicate approval, cancellation, invalid fingerprint, handler error, or execution failure, do not commit partial operations and preserve a bounded, user-safe terminal reason.
- [ ] Reuse the existing cancellation signal across the provider loop and scene transaction boundary. Once cancelled, stop requesting tools/provider continuations and roll back any begun transaction exactly once.
- [ ] Run `./.venv/Scripts/python.exe -m pytest tests/test_agent_runtime.py tests/test_agent_runtime_loop.py -q`; commit with `git add -- agent/runtime.py agent/agent.py agent/models.py tests/test_agent_runtime.py tests/test_agent_runtime_loop.py`.

<!-- openspec-task: 3.5 -->
### Task 14: Persist ordered, sanitized capability lifecycle and composition events

**Files:**
- Modify: `agent/models.py`
- Modify: `agent/runtime.py`
- Modify: `agent/persistence.py`
- Modify: `agent/agent_bridge.py`
- Modify: `tests/test_agent_runtime.py`
- Modify: `tests/test_agent_bridge.py`

- [ ] Add failing tests for ordered `tool_started`, `tool_finished`, `capability_fallback`, `plan_composed`, and `scene_conflict` events, plus exactly one terminal event for successful, failed, and cancelled turns.
- [ ] Define the event payload contract with a monotonic sequence, call ID where relevant, canonical name/status, compact summary, and JSON-safe detail object. Cap all user-visible string fields at 512 characters and event/result serialization at configured limits.
- [ ] Sanitize event payloads before persistence and bridge emission. Explicitly redact API keys/credential-like values and reject renderer instances, attachments, full prompts, request headers, and model reasoning fields.
- [ ] Update persistence serialization/deserialization so old saved sessions still load when the new optional event fields are absent. Retain only bounded event history per turn/session as specified by existing retention conventions.
- [ ] Make bridge validation reject malformed event payloads rather than letting them reach the frontend reducer, and test that a rejected event cannot corrupt subsequent valid events.
- [ ] Run `./.venv/Scripts/python.exe -m pytest tests/test_agent_runtime.py tests/test_agent_bridge.py -q`; commit with `git add -- agent/models.py agent/runtime.py agent/persistence.py agent/agent_bridge.py tests/test_agent_runtime.py tests/test_agent_bridge.py`.

<!-- openspec-task: 4.1 -->
### Task 15: Expose the capability catalog through session snapshots and grouped UI tools

**Files:**
- Modify: `agent/runtime.py`
- Modify: `agent/agent_bridge.py`
- Modify: `ui/agent_web/src/types.ts`
- Modify: `ui/agent_web/src/App.tsx`
- Modify: `ui/agent_web/src/components/Composer.tsx`
- Modify: `ui/agent_web/src/components/AttachmentActions.tsx`
- Modify: `tests/test_agent_ui_projection.py`

- [ ] Add failing backend projection tests proving `build_session_snapshot()` includes a deterministic `capability_catalog` with version, canonical names, descriptions, categories, input summary, and availability metadata, but no aliases or internal handler details.
- [ ] Add frontend tests that deserialize the snapshot and render the tool menu from catalog entries rather than a manually maintained capability list. Cover an empty/unavailable category and a catalog with a newly added entry.
- [ ] Extend shared TypeScript types and bridge payload validation for the catalog. Keep its schema compatible with browser/offline fixtures and avoid `any` casts at the state boundary.
- [ ] Replace the legacy manual skill selection surface with a grouped popover based on the six categories. `open_skills` should request/display this catalog; clicking an item inserts a natural-language-friendly starter without selecting a hidden execution tool.
- [ ] Pass catalog state through `App` to `Composer` and `AttachmentActions`, keeping keyboard focus, disabled state, and narrow layout behavior intact.
- [ ] Run `./.venv/Scripts/python.exe -m pytest tests/test_agent_ui_projection.py -q` and `pnpm --dir ui/agent_web test`; commit with `git add -- agent/runtime.py agent/agent_bridge.py ui/agent_web/src/types.ts ui/agent_web/src/App.tsx ui/agent_web/src/components/Composer.tsx ui/agent_web/src/components/AttachmentActions.tsx tests/test_agent_ui_projection.py`.

<!-- openspec-task: 4.2 -->
### Task 16: Render lifecycle, fallback, composition, and conflict event cards

**Files:**
- Modify: `ui/agent_web/src/types.ts`
- Modify: `ui/agent_web/src/state/reducer.ts`
- Modify: `ui/agent_web/src/components/EventCard.tsx`
- Modify: `ui/agent_web/src/components/Conversation.tsx`
- Create: `ui/agent_web/src/components/EventCard.test.tsx`

- [ ] Write failing React tests for `tool_started`, `tool_finished`, `capability_fallback`, `plan_composed`, and `scene_conflict` cards. Assert chronological ordering, distinct accessible labels/icons, and safe truncated summaries.
- [ ] Extend reducer state to store events by server sequence, ignore duplicate/older sequence numbers, and retain only the frontend event cap. Do not reorder provider text, plans, approvals, or tool lifecycle records.
- [ ] Implement compact event cards with hover/focus details and correct status styling. Surface fallback and scene conflict clearly, but never render raw request payloads, credentials, or internal exception stacks.
- [ ] Integrate cards into the conversation timeline alongside existing assistant text and plan/approval elements. Keep events visible after reconnect/session reload when present in the snapshot.
- [ ] Add visual-state tests for error/no-op/success and ensure long localized text wraps without layout shift in the compact agent panel.
- [ ] Run `pnpm --dir ui/agent_web test`; commit with `git add -- ui/agent_web/src/types.ts ui/agent_web/src/state/reducer.ts ui/agent_web/src/components/EventCard.tsx ui/agent_web/src/components/Conversation.tsx ui/agent_web/src/components/EventCard.test.tsx`.

<!-- openspec-task: 4.3 -->
### Task 17: Extend bridge and web protocol validation for the new state contract

**Files:**
- Modify: `agent/agent_bridge.py`
- Modify: `agent/agent_web_protocol.py`
- Modify: `ui/agent_web/src/bridge.ts`
- Modify: `ui/agent_web/src/types.ts`
- Modify: `tests/test_agent_bridge.py`
- Modify: `tests/test_agent_web_protocol.py`
- Modify: `tests/test_agent_web_dispatch.py`

- [ ] Add failing Python and TypeScript protocol tests for catalog snapshots and every capability event message. Test valid ordering, unknown message type rejection, malformed nested payload rejection, and recovery after one invalid message.
- [ ] Define the canonical event/message names in one backend protocol source and mirror them in TypeScript discriminated unions. Add `capability_fallback`, `plan_composed`, and `scene_conflict` without changing legacy messages' meanings.
- [ ] Validate all browser bridge inbound and outbound data before dispatch. Do not use renderer objects or Python enums directly in JSON; serialize them through the contract helpers.
- [ ] Add offline/session fixture coverage for catalog absence (old persisted session), a full v1 catalog, and sequence gaps. The UI should degrade to an empty tool menu, not fail the entire app.
- [ ] Run `./.venv/Scripts/python.exe -m pytest tests/test_agent_bridge.py tests/test_agent_web_protocol.py tests/test_agent_web_dispatch.py -q` and `pnpm --dir ui/agent_web test`; commit with `git add -- agent/agent_bridge.py agent/agent_web_protocol.py ui/agent_web/src/bridge.ts ui/agent_web/src/types.ts tests/test_agent_bridge.py tests/test_agent_web_protocol.py tests/test_agent_web_dispatch.py`.

<!-- openspec-task: 5.1 -->
### Task 18: Migrate prompts and local skill metadata to canonical capability names

**Files:**
- Modify: `agent/prompts.py`
- Modify: `agent/skills.py`
- Modify: `agent/tool_registry.py`
- Modify: `tests/test_agent_tools.py`
- Modify: `tests/test_agent_provider.py`

- [ ] Add failing tests that system prompts and local Skill metadata reference only canonical v1 capability names, while legacy input aliases still resolve via the compatibility facade.
- [ ] Update prompt construction to inject catalog-derived names/descriptions instead of an independent hard-coded tool list. Include instructions that tools are sequential, results are bounded, and unsupported operations must be explained rather than invented.
- [ ] Update local skill metadata/mappings to use canonical names and categories. Preserve aliases only at request ingress; confirm aliases do not enter user-visible catalog/prompt declarations.
- [ ] Verify the rule-based/local provider fallback still produces valid plans and that existing non-capability teaching responses are unchanged.
- [ ] Run `./.venv/Scripts/python.exe -m pytest tests/test_agent_tools.py tests/test_agent_provider.py -q`; commit with `git add -- agent/prompts.py agent/skills.py agent/tool_registry.py tests/test_agent_tools.py tests/test_agent_provider.py`.

<!-- openspec-task: 5.2 -->
### Task 19: Add end-to-end fixtures for representative plotting-agent workflows

**Files:**
- Create: `tests/test_agent_capability_e2e.py`
- Modify: `tests/test_agent_runtime_loop.py`
- Modify: `tests/test_agent_runtime.py`
- Modify: `tests/test_agent_ui_projection.py`

- [ ] Build deterministic fake-provider/fake-scene-host fixtures that exercise native tool continuations without network access or a live renderer. The host must record transaction, fingerprint, and export requests.
- [ ] Add end-to-end cases for: inspect then edit; derivative plus tangent rendering; 3D surface creation; scoped clear; unsafe export rejection; native provider fallback; stale Plan approval; cancellation; and mixed-scene conflict.
- [ ] For each mutation case, assert exact composed command operation order, one transaction at most, expected fingerprint enforcement, and no live renderer change before commit. For failure/cancellation cases, assert no commit and one terminal event.
- [ ] Add snapshot/UI projections for the corresponding catalog/event/plan states, including long result summaries and an unavailable capability entry.
- [ ] Use the documented fixed limits in at least one end-to-end loop/excess-call fixture so limits are covered across the provider and runtime boundary, not only unit tests.
- [ ] Run `./.venv/Scripts/python.exe -m pytest tests/test_agent_capability_e2e.py tests/test_agent_runtime_loop.py tests/test_agent_runtime.py tests/test_agent_ui_projection.py -q`; commit with `git add -- tests/test_agent_capability_e2e.py tests/test_agent_runtime_loop.py tests/test_agent_runtime.py tests/test_agent_ui_projection.py`.

<!-- openspec-task: 5.3 -->
### Task 20: Run full regression, frontend build, and strict OpenSpec verification

**Files:**
- Modify only when failures reveal a verified defect: relevant implementation and test files from Tasks 1-19
- Verify: `openspec/changes/natural-language-plotting-agent/`
- Verify: `docs/superpowers/plans/2026-08-27-natural-language-plotting-agent.md`

- [ ] Run the full Python suite with `./.venv/Scripts/python.exe -m pytest -q`. Investigate failures with `superpowers:systematic-debugging`; do not weaken tests or mask regressions to obtain a green run.
- [ ] Run `pnpm --dir ui/agent_web test` and `pnpm --dir ui/agent_web build`. Resolve TypeScript type errors, protocol fixture drift, and UI rendering regressions introduced by this change.
- [ ] Run `openspec validate natural-language-plotting-agent --strict` and confirm the completed implementation remains consistent with the approved proposal/design/spec/tasks artifacts.
- [ ] Run `git diff --check -- agent ui geometry tests pyproject.toml requirements.txt` and inspect `git status --short`; ensure only intended files are staged and unrelated user changes remain untouched.
- [ ] Re-run targeted acceptance cases from Task 19 after any regression fix. Record exact commands and outcomes in the implementation handoff/PR description, including any environment-dependent test limitations.
- [ ] Commit the verified implementation with an explicit message such as `feat: add natural-language plotting capabilities`; do not include unrelated worktree changes.

## OpenSpec Coverage Matrix

| OpenSpec task | Plan task | Primary outcome |
| --- | --- | --- |
| 1.1 | 1 | Canonical capability contracts |
| 1.2 | 2 | Strict bounded schema validation |
| 1.3 | 3 | v1 capability catalog/registry |
| 1.4 | 4 | Legacy alias compatibility |
| 2.1 | 5 | Staged renderer-free scene index |
| 2.2 | 6 | Scene/view/clear/export handlers |
| 2.3 | 7 | Controlled math handlers |
| 2.4 | 8 | Composed staged command plan |
| 2.5 | 9 | Safety and loop limits |
| 3.1 | 10 | Chat/Responses tool protocol |
| 3.2 | 11 | Tool loop and same-provider fallback |
| 3.3 | 12 | Snapshot fingerprint enforcement |
| 3.4 | 13 | Modes, approvals, cancellation |
| 3.5 | 14 | Sanitized lifecycle persistence |
| 4.1 | 15 | Catalog-driven grouped UI |
| 4.2 | 16 | Lifecycle/conflict UI cards |
| 4.3 | 17 | Validated bridge/web protocol |
| 5.1 | 18 | Canonical prompts and skills |
| 5.2 | 19 | End-to-end acceptance coverage |
| 5.3 | 20 | Full regression and strict validation |

## Completion Criteria

- Every checkbox is completed in order, and `openspec/changes/natural-language-plotting-agent/tasks.md` is synchronized as work completes.
- The capability catalog advertises canonical names only, all tool calls are schema-validated and bounded, and mixed/stale/cancelled mutations cannot change the scene.
- The backend, provider adapters, persisted session data, bridge protocol, and frontend agree on one JSON-safe capability/event contract.
- The full Python suite, frontend tests/build, whitespace check, and strict OpenSpec validation pass with captured command output.
