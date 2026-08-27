# MathAgent Sidebar Bug Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the local React MathAgent sidebar usable as the VS Code-like conversation workspace described by the OpenSpec change while preserving the JSON-only Qt boundary and SceneCommandService execution path.

**Architecture:** Python remains the source of truth for sessions, turns, snapshots, provider settings, Memory, Rules, and runtime events. React owns only transient view, draft, popover, and optimistic-request state. All WebView mutations travel through the single `AgentBridge.send_json` slot, are validated and dispatched by Python, and scene changes continue through the existing validator and `SceneCommandService`.

**Tech Stack:** Python 3.11+, PySide6/QWebEngine/QWebChannel, SQLite in the application-managed `.math` directory, QSettings JSON for credentials and custom models, React 18 + TypeScript, Vite, pnpm, Vitest, Testing Library, pytest.

---

## File Map and Execution Order

Python persistence and protocol work must land before the React projections that consume it. The dependency order is:

1. Session schema and history operations (`1.1`-`1.4`)
2. JSON protocol, bridge dispatch, and idempotency (`2.1`-`2.4`)
3. Model/provider catalog and per-session preferences (`3.1`-`3.6`)
4. Mode semantics, composer controls, and responsive presentation (`4.1`-`4.5`)
5. Cross-layer verification (`5.1`-`5.4`)

Primary existing seams:

- `agent/session_store.py`: SQLite records, migrations, and session/turn queries.
- `agent/ui_projection.py`: credential-free JSON snapshots for the Web UI.
- `agent/web_protocol.py` and `ui/agent_bridge.py`: the versioned JSON boundary and the only Qt slot.
- `ui/designer_window.py`: host-side intent dispatch and runtime/scene integration.
- `ui/agent_web/src/App.tsx`, `state/reducer.ts`, and `components/*`: local React state and presentation.
- `ui/agent_settings.py`, `agent/providers/*`, and `services/agent_provider.py`: QSettings/provider compatibility.

Every task below is intentionally small enough to implement and test independently. Keep the OpenSpec task comment immediately above each task heading so `/opsx:executing-plans` can sync progress.

<!-- openspec-task: 1.1 -->
### Task 1: Add additive session-schema migration

**Files:**
- Modify: `agent/session_store.py:39-190` (`SessionRecord`, `SessionStore._initialize`, `_session`).
- Test: `tests/test_session_store.py`.

- [ ] **Step 1: Write the failing migration test.** Create a SQLite database containing the pre-change `sessions` table, open it with `SessionStore(app_root=tmp_path)`, and assert `PRAGMA table_info(sessions)` contains `hidden_at`; assert an existing row loads with `hidden_at is None`.
- [ ] **Step 2: Run the focused test.** Run `python -m pytest tests/test_session_store.py -k migration -q`; expected result is FAIL because `SessionRecord` and the table have no `hidden_at` field.
- [ ] **Step 3: Implement one reusable additive migration helper.** Add `hidden_at: str | None = None` to `SessionRecord`, create new databases with the column, and in `_initialize` inspect `PRAGMA table_info(sessions)` before executing `ALTER TABLE sessions ADD COLUMN hidden_at TEXT`. Do not rebuild or rewrite any table.
- [ ] **Step 4: Re-read rows using named columns.** Keep `_session()` tolerant of old SQLite row shapes by supplying `hidden_at=None` when the key is absent; update insert/update statements to preserve NULL for new sessions.
- [ ] **Step 5: Run regression tests.** Run `python -m pytest tests/test_session_store.py -q`; expected result is PASS with all existing turn, event, attachment, and snapshot tests unchanged.
- [ ] **Step 6: Commit the isolated change.** Run `git add agent/session_store.py tests/test_session_store.py && git commit -m "fix: migrate sessions with hidden timestamps"`.

<!-- openspec-task: 1.2 -->
### Task 2: Implement title validation, hiding, and visible filtering

**Files:**
- Modify: `agent/session_store.py:200-275` (`create_session`, `list_sessions`, `rename_session`, new `hide_session`).
- Test: `tests/test_session_store.py`.

- [ ] **Step 1: Add failing behavior tests.** Cover duplicate titles, whitespace becoming `New Chat`, an 81-code-point title raising a field error, `list_sessions()` excluding hidden rows by default, and refusing to hide the last visible session.
- [ ] **Step 2: Run the tests to verify the contract is missing.** Run `python -m pytest tests/test_session_store.py -k "title or hidden or visible" -q`; expected result is FAIL.
- [ ] **Step 3: Add a shared title normalizer.** Implement `_normalize_title(title: str) -> str` with `strip()`, the `New Chat` fallback, and `len()` measured in Unicode code points; raise `ValueError("title_too_long")` above 80. Use it in create and rename without adding a uniqueness constraint.
- [ ] **Step 4: Add reversible hide semantics.** Implement `hide_session(session_id)` and `restore_hidden_session(session_id)`. `list_sessions(include_closed=False)` must apply `closed_at IS NULL AND hidden_at IS NULL`; add `list_hidden_sessions()` for explicit recovery. Keep close/reopen independent from hide/restore.
- [ ] **Step 5: Verify persistence and isolation.** Run `python -m pytest tests/test_session_store.py -q`; expected result is PASS and hidden sessions still return all turns, events, attachments, and snapshots when addressed by ID.
- [ ] **Step 6: Commit.** Run `git add agent/session_store.py tests/test_session_store.py && git commit -m "feat: hide and rename MathAgent sessions"`.

<!-- openspec-task: 1.3 -->
### Task 3: Project history snapshots without SQLite leakage

**Files:**
- Modify: `agent/ui_projection.py:28-145` (`_session_projection`, `build_session_snapshot`).
- Test: `tests/test_agent_ui_projection.py`.

- [ ] **Step 1: Write projection tests.** Assert a history item has only `id`, normalized `title`, `updated_at`, `turn_count`, `hidden`, `closed`, and `last_opened_at`; assert no SQLite row, credential, renderer object, or API header appears.
- [ ] **Step 2: Run the focused test and confirm failure.** Run `python -m pytest tests/test_agent_ui_projection.py -k history -q`; expected result is FAIL because the current projection emits full sessions only.
- [ ] **Step 3: Add explicit projections.** Implement `_history_item(store, session)` and include `history.visible` plus `history.hidden` in `build_session_snapshot`; keep the conversation `sessions` projection backward-compatible for the active timeline.
- [ ] **Step 4: Make ordering deterministic.** Sort visible and hidden lists by `updated_at DESC`, then `id ASC`; calculate `turn_count` from `list_turns()` and expose `hidden` from `hidden_at is not None`.
- [ ] **Step 5: Run projection and security tests.** Run `python -m pytest tests/test_agent_ui_projection.py tests/test_agent_web_security.py -q`; expected result is PASS.
- [ ] **Step 6: Commit.** Run `git add agent/ui_projection.py tests/test_agent_ui_projection.py && git commit -m "feat: project safe MathAgent history snapshots"`.

<!-- openspec-task: 1.4 -->
### Task 4: Add hidden-session recovery and active-session fallback

**Files:**
- Modify: `agent/session_store.py:240-290` (fallback helpers).
- Modify: `ui/designer_window.py:252-380` (`_dispatch_agent_web_intent`, `_emit_agent_snapshot`).
- Test: `tests/test_session_store.py`, `tests/test_agent_web_persistence.py`.

- [ ] **Step 1: Write fallback tests.** Hide the active session and assert fallback order is most recently opened visible, then most recently updated visible, then a newly created `New Chat`; restore a hidden session and assert its scene is unchanged.
- [ ] **Step 2: Run the focused tests.** Run `python -m pytest tests/test_session_store.py tests/test_agent_web_persistence.py -k "fallback or restore_hidden" -q`; expected result is FAIL.
- [ ] **Step 3: Implement deterministic selection.** Add `select_visible_fallback(excluding=session_id)` using `last_opened_at DESC`, `updated_at DESC`, and `id ASC`; create a visible default session only when no candidate exists.
- [ ] **Step 4: Wire intents and snapshots.** Dispatch `hide_session` and `restore_hidden_session`; after hiding the active session, emit a snapshot with the fallback active ID. Restoring clears `hidden_at` only and never calls the scene restore path.
- [ ] **Step 5: Run persistence regressions.** Run `python -m pytest tests/test_session_store.py tests/test_agent_web_persistence.py -q`; expected result is PASS.
- [ ] **Step 6: Commit.** Run `git add agent/session_store.py ui/designer_window.py tests/test_session_store.py tests/test_agent_web_persistence.py && git commit -m "feat: recover hidden sessions safely"`.

<!-- openspec-task: 2.1 -->
### Task 5: Add conversation, history, and settings React views

**Files:**
- Modify: `ui/agent_web/src/types.ts`, `ui/agent_web/src/state/reducer.ts`, `ui/agent_web/src/App.tsx`.
- Create: `ui/agent_web/src/components/HistoryView.tsx`, `ui/agent_web/src/components/SettingsView.tsx`.
- Test: `ui/agent_web/src/App.test.tsx`, new view tests beside components.

- [ ] **Step 1: Write failing navigation tests.** Click the header clock and assert history renders immediately; click settings and assert the four sections (Agent/model, Skills, Memory, Rules); click Back and assert the conversation timeline returns without a snapshot requirement.
- [ ] **Step 2: Run the focused Vitest tests.** Run `pnpm --dir ui/agent_web test -- App.test.tsx`; expected result is FAIL because `App` has no local view state.
- [ ] **Step 3: Add a typed view reducer.** Define `ViewName = "conversation" | "history" | "settings"`, add `view` to `AppState`, and handle `set_view` without replacing sessions or applying a scene snapshot.
- [ ] **Step 4: Render views as siblings.** In `App.tsx`, render `HistoryView` or `SettingsView` based on `state.view`; keep `AgentHeader` mounted so Back and title-bar actions remain stable; preserve timeline events while secondary views are open.
- [ ] **Step 5: Run view tests and build.** Run `pnpm --dir ui/agent_web test -- App.test.tsx HistoryView.test.tsx SettingsView.test.tsx` then `pnpm --dir ui/agent_web build`; expected result is PASS and a successful Vite build.
- [ ] **Step 6: Commit.** Run `git add ui/agent_web/src && git commit -m "feat: add in-panel MathAgent views"`.

<!-- openspec-task: 2.2 -->
### Task 6: Wire history, settings, Skills, and title actions to JSON intents

**Files:**
- Modify: `ui/agent_web/src/types.ts`, `ui/agent_web/src/App.tsx`, `ui/agent_web/src/bridge/qtBridge.ts`.
- Modify: `agent/web_protocol.py`, `ui/designer_window.py`.
- Test: `tests/test_agent_web_dispatch.py`, `ui/agent_web/src/bridge/qtBridge.test.ts`.

- [ ] **Step 1: Add intent-shape tests.** Assert header actions send `open_history`/`open_settings`, Skills sends `open_skills`, title save sends `rename_session`, hide sends `hide_session`, and recovery sends `restore_hidden_session`, each with a UUID `request_id`.
- [ ] **Step 2: Run tests before implementation.** Run `python -m pytest tests/test_agent_web_dispatch.py -q` and `pnpm --dir ui/agent_web test -- qtBridge.test.ts`; expected result is FAIL for the new message types.
- [ ] **Step 3: Extend the protocol allow-list.** Add the design's intent names to `CLIENT_MESSAGE_TYPES`; keep `AgentBridge.send_json` as the only Qt slot and map all responses to JSON envelopes.
- [ ] **Step 4: Dispatch host actions.** Add branches in `_dispatch_agent_web_intent` that call the store/projection functions and emit `history_snapshot`, `settings_snapshot`, or `model_catalog` payloads; `open_skills` returns registered skill metadata only.
- [ ] **Step 5: Run protocol and dispatch tests.** Run `python -m pytest tests/test_agent_web_dispatch.py tests/test_agent_bridge.py -q` and `pnpm --dir ui/agent_web test -- qtBridge.test.ts`; expected result is PASS.
- [ ] **Step 6: Commit.** Run `git add agent/web_protocol.py ui/designer_window.py ui/agent_web/src tests/test_agent_web_dispatch.py && git commit -m "feat: connect sidebar navigation intents"`.

<!-- openspec-task: 2.3 -->
### Task 7: Make unknown intents and failures safe JSON responses

**Files:**
- Modify: `agent/web_protocol.py:100-170`, `ui/agent_bridge.py:25-55`.
- Test: `tests/test_agent_bridge.py`, `tests/test_agent_web_protocol.py`, `tests/test_agent_web_security.py`.

- [ ] **Step 1: Add failure tests.** Send an unknown history/settings intent, malformed payload, and invalid ID; assert the response is `{type:"error", request_id, session_id, payload:{code,message}}` and contains no exception object or traceback.
- [ ] **Step 2: Run focused tests to verify current behavior.** Run `python -m pytest tests/test_agent_bridge.py tests/test_agent_web_protocol.py -q`; expected result is FAIL for stable error codes and field validation.
- [ ] **Step 3: Implement field-safe errors.** Add `ProtocolError(code, message, field=None)` and catch it in `AgentBridge.send_json`; serialize only strings and bounded field names. Preserve the incoming request ID when JSON decoding succeeds.
- [ ] **Step 4: Add validation limits.** Enforce non-empty IDs <=128, title <=80 code points, URL <=512 with HTTPS or localhost HTTP and no userinfo, and the existing 128 KiB envelope cap. Never include API-key fields in errors.
- [ ] **Step 5: Run security tests.** Run `python -m pytest tests/test_agent_bridge.py tests/test_agent_web_protocol.py tests/test_agent_web_security.py -q`; expected result is PASS.
- [ ] **Step 6: Commit.** Run `git add agent/web_protocol.py ui/agent_bridge.py tests/test_agent_bridge.py tests/test_agent_web_protocol.py tests/test_agent_web_security.py && git commit -m "fix: serialize safe WebView protocol errors"`.

<!-- openspec-task: 2.4 -->
### Task 8: Add request correlation, optimistic rollback, and sequence recovery

**Files:**
- Modify: `ui/agent_web/src/state/reducer.ts`, `ui/agent_web/src/bridge/qtBridge.ts`, `ui/agent_web/src/App.tsx`.
- Modify: `agent/runtime.py`, `ui/designer_window.py`.
- Test: `ui/agent_web/src/state/reducer.test.ts`, `tests/test_agent_runtime_web_events.py`.

- [ ] **Step 1: Write reducer tests.** Assert a rename/model/mode action applies immediately, a matching `mutation_failed` restores the prior projection, a different request ID does not roll it back, and a sequence gap sets `gapDetected` and requests a fresh snapshot.
- [ ] **Step 2: Run reducer tests to establish failure.** Run `pnpm --dir ui/agent_web test -- reducer.test.ts`; expected result is FAIL because pending mutations and sequence tracking are incomplete.
- [ ] **Step 3: Add pending mutation records.** Store `{requestId, sessionId, previousValue}` per mutation key; handle `mutation_succeeded` by replacing the optimistic item with the projection and `mutation_failed` by restoring only the matching record.
- [ ] **Step 4: Add a Python idempotency ledger.** Keep a bounded per-session request result map in Runtime/dispatcher keyed by `(session_id, request_id)`; return the original result for retries and reject conflicting reuse. Emit a snapshot request on sequence gaps.
- [ ] **Step 5: Run cross-layer tests.** Run `pnpm --dir ui/agent_web test -- reducer.test.ts qtBridge.test.ts` and `python -m pytest tests/test_agent_runtime_web_events.py tests/test_agent_web_dispatch.py -q`; expected result is PASS.
- [ ] **Step 6: Commit.** Run `git add ui/agent_web/src agent/runtime.py ui/designer_window.py tests/test_agent_runtime_web_events.py && git commit -m "feat: correlate and recover sidebar mutations"`.

<!-- openspec-task: 3.1 -->
### Task 9: Define the built-in DeepSeek catalog and Pro details

**Files:**
- Create: `agent/model_catalog.py`.
- Modify: `agent/ui_projection.py`, `ui/designer_window.py`.
- Modify: `ui/agent_web/src/types.ts`, `ui/agent_web/src/components/ModelSelector.tsx`.
- Test: `tests/test_agent_ui_projection.py`, `ui/agent_web/src/components/ModelSelector.test.tsx`.

- [ ] **Step 1: Add catalog tests.** Assert the builtin group contains `Deepseek-V4-Flash High`, `Deepseek-V4-Pro High`, and `deepseek-v4-flash-vision-exp`; assert the first is selected when a session has no valid model and Pro metadata contains 1M context, image input, reasoning, thinking enabled, and Low/High/X-High.
- [ ] **Step 2: Run tests to verify missing catalog.** Run `python -m pytest tests/test_agent_ui_projection.py -k catalog -q` and `pnpm --dir ui/agent_web test -- ModelSelector.test.tsx`; expected result is FAIL.
- [ ] **Step 3: Implement immutable Python metadata.** Add typed `ModelDescriptor` values with stable IDs, display names, protocol, capabilities, and context tiers; return separate `builtin` and `custom` groups from `model_catalog()`.
- [ ] **Step 4: Render the picker and hover card.** Update `ModelSelector` to display groups, highlight the current row, show `+ Configure custom model`, and make the Pro card appear on hover/focus without a scene mutation.
- [ ] **Step 5: Run Python and React tests.** Run `python -m pytest tests/test_agent_ui_projection.py -q` and `pnpm --dir ui/agent_web test -- ModelSelector.test.tsx`; expected result is PASS.
- [ ] **Step 6: Commit.** Run `git add agent/model_catalog.py agent/ui_projection.py ui/designer_window.py ui/agent_web/src tests/test_agent_ui_projection.py && git commit -m "feat: add DeepSeek model catalog"`.

<!-- openspec-task: 3.2 -->
### Task 10: Persist provider credentials through QSettings with redaction

**Files:**
- Modify: `ui/agent_settings.py`, `agent/ui_projection.py`, `ui/designer_window.py`.
- Test: `tests/test_agent_settings.py`, `tests/test_agent_web_security.py`.

- [ ] **Step 1: Add credential-redaction tests.** Save a DeepSeek key and assert QSettings stores it, the settings snapshot reports only `configured: true` and a masked suffix, and the SQLite database, events, logs, and bridge payloads contain no key.
- [ ] **Step 2: Run the focused tests.** Run `python -m pytest tests/test_agent_settings.py tests/test_agent_web_security.py -k key -q`; expected result is FAIL for the new Responses-shaped projection.
- [ ] **Step 3: Add the `OpenAI - Responses` settings record.** Store provider, protocol, base URL, model, timeout, and key under a versioned QSettings JSON key; keep the raw key inside Python only and return a `key_configured` boolean plus mask.
- [ ] **Step 4: Separate save from test.** Make save validate and persist only; no network call is allowed from `_save`. Ensure all exception formatting passes through a key-redacting helper before events or labels.
- [ ] **Step 5: Run settings/security regressions.** Run `python -m pytest tests/test_agent_settings.py tests/test_agent_web_security.py -q`; expected result is PASS.
- [ ] **Step 6: Commit.** Run `git add ui/agent_settings.py agent/ui_projection.py ui/designer_window.py tests/test_agent_settings.py tests/test_agent_web_security.py && git commit -m "fix: keep provider keys local and redacted"`.

<!-- openspec-task: 3.3 -->
### Task 11: Add custom model CRUD and capability/context validation

**Files:**
- Modify: `agent/model_catalog.py`, `ui/designer_window.py`, `agent/ui_projection.py`.
- Modify: `ui/agent_web/src/components/ModelSelector.tsx`, create `ui/agent_web/src/components/ModelSettings.tsx`.
- Test: `tests/test_agent_settings.py`, `tests/test_agent_web_dispatch.py`, React component tests.

- [ ] **Step 1: Write CRUD tests.** Save, update, select, and delete a custom model; assert it appears only in the custom group, builtins remain unchanged, deleting a model does not rewrite session history, and unsupported context tiers are rejected.
- [ ] **Step 2: Run focused tests.** Run `python -m pytest tests/test_agent_settings.py tests/test_agent_web_dispatch.py -k custom -q`; expected result is FAIL.
- [ ] **Step 3: Implement versioned custom-model JSON.** Define `CustomModel` serialization with provider, protocol, URL, key reference, model ID, timeout, tool/image/reasoning flags, and input/output tiers; validate IDs <=128 and tiers against advertised sets before writing QSettings.
- [ ] **Step 4: Implement settings form actions.** Add draft state, Save, Edit, and permanent Delete; keep failed saves editable and never remove builtin descriptors or session records.
- [ ] **Step 5: Run CRUD tests and build.** Run `python -m pytest tests/test_agent_settings.py tests/test_agent_web_dispatch.py -q` and `pnpm --dir ui/agent_web build`; expected result is PASS.
- [ ] **Step 6: Commit.** Run `git add agent/model_catalog.py agent/ui_projection.py ui/designer_window.py ui/agent_web/src tests/test_agent_settings.py tests/test_agent_web_dispatch.py && git commit -m "feat: manage custom MathAgent models"`.

<!-- openspec-task: 3.4 -->
### Task 12: Support Responses/Chat Completions and bounded connection tests

**Files:**
- Modify: `services/agent_provider.py`, `agent/providers/openai_provider.py`, `agent/providers/deepseek_provider.py`, `ui/agent_settings.py`, `ui/designer_window.py`.
- Test: `tests/test_agent_provider.py`, `tests/test_agent_settings.py`.

- [ ] **Step 1: Add protocol tests.** Assert the default form protocol is `responses`, both `responses` and `chat_completions` serialize correctly, and `Test connection` uses draft values without changing saved settings or session history.
- [ ] **Step 2: Run provider tests to verify the gap.** Run `python -m pytest tests/test_agent_provider.py tests/test_agent_settings.py -k protocol -q`; expected result is FAIL.
- [ ] **Step 3: Add a typed protocol adapter.** Introduce `ProviderProtocol = Literal["responses", "chat_completions"]`; route request construction through `build_request(protocol, ...)` and keep model/provider selection outside the WebView.
- [ ] **Step 4: Bound test requests.** Implement `test_model_provider` with a 10-second timeout, no persistence, no scene calls, and a serializable success/error result. Do not fall back to Local on provider failure.
- [ ] **Step 5: Run provider regressions.** Run `python -m pytest tests/test_agent_provider.py tests/test_agent_settings.py -q`; expected result is PASS.
- [ ] **Step 6: Commit.** Run `git add services/agent_provider.py agent/providers ui/agent_settings.py ui/designer_window.py tests/test_agent_provider.py tests/test_agent_settings.py && git commit -m "feat: support provider protocol selection"`.

<!-- openspec-task: 3.5 -->
### Task 13: Persist per-session thinking preferences and custom deletion

**Files:**
- Modify: `agent/session_store.py`, `agent/model_catalog.py`, `ui/designer_window.py`, `agent/ui_projection.py`.
- Modify: `ui/agent_web/src/types.ts`, `ui/agent_web/src/components/ModelSettings.tsx`.
- Test: `tests/test_session_store.py`, `tests/test_agent_web_dispatch.py`, React settings tests.

- [ ] **Step 1: Add preference tests.** Switch sessions and assert each retains `thinking_enabled` and `thinking_level`; disabling thinking hides/disables level controls while re-enabling restores the last level. Assert custom deletion is permanent and isolated.
- [ ] **Step 2: Run focused tests.** Run `python -m pytest tests/test_session_store.py tests/test_agent_web_dispatch.py -k thinking -q`; expected result is FAIL.
- [ ] **Step 3: Extend the additive migration helper.** Add nullable/defaulted `thinking_enabled` and `thinking_level` columns (or a versioned session-preferences JSON field if the existing schema policy requires it); migrate old rows to `True`/`High` without changing model selection.
- [ ] **Step 4: Implement intent and projection updates.** Add `set_thinking_preferences` and `delete_custom_model`, validate `Low|High|X-High`, and emit the active session's preferences in snapshots.
- [ ] **Step 5: Run tests and TypeScript checks.** Run `python -m pytest tests/test_session_store.py tests/test_agent_web_dispatch.py -q` and `pnpm --dir ui/agent_web exec tsc --noEmit`; expected result is PASS.
- [ ] **Step 6: Commit.** Run `git add agent/session_store.py agent/model_catalog.py agent/ui_projection.py ui/designer_window.py ui/agent_web/src tests/test_session_store.py tests/test_agent_web_dispatch.py && git commit -m "feat: save session thinking preferences"`.

<!-- openspec-task: 3.6 -->
### Task 14: Preserve provider errors and render them as assistant cards

**Files:**
- Modify: `agent/runtime.py`, `services/agent_provider.py`, `ui/designer_window.py`.
- Modify: `ui/agent_web/src/components/EventCard.tsx`, `ui/agent_web/src/state/reducer.ts`.
- Test: `tests/test_agent_runtime.py`, `tests/test_agent_runtime_web_events.py`, React event-card tests.

- [ ] **Step 1: Write provider-error tests.** Use a missing-key DeepSeek provider and an HTTP error fixture; assert the current turn receives a serializable `error` event, the turn is marked failed, and no Local provider is instantiated.
- [ ] **Step 2: Run focused tests.** Run `python -m pytest tests/test_agent_runtime.py tests/test_agent_runtime_web_events.py -k error -q`; expected result is FAIL if the runtime currently drops or substitutes errors.
- [ ] **Step 3: Normalize provider failures.** Add stable codes (`provider_unconfigured`, `provider_http_error`, `provider_timeout`) and redact URLs/keys before persisting or emitting. Keep error scope to the turn/session.
- [ ] **Step 4: Render a distinct assistant error card.** In `EventCard`, map `error` to an accessible alert with retry-safe request correlation; do not render raw traceback or role labels.
- [ ] **Step 5: Run regressions.** Run `python -m pytest tests/test_agent_runtime.py tests/test_agent_runtime_web_events.py -q` and `pnpm --dir ui/agent_web test -- EventCard.test.tsx`; expected result is PASS.
- [ ] **Step 6: Commit.** Run `git add agent/runtime.py services/agent_provider.py ui/designer_window.py ui/agent_web/src tests/test_agent_runtime.py tests/test_agent_runtime_web_events.py && git commit -m "fix: surface provider errors without fallback"`.

<!-- openspec-task: 4.1 -->
### Task 15: Normalize Agent, Ask, and Plan execution semantics

**Files:**
- Modify: `agent/runtime.py`, `ui/designer_window.py`, `agent/session_store.py`, `agent/web_protocol.py`.
- Modify: `ui/agent_web/src/types.ts`, `components/ModeSelector.tsx`, `components/Composer.tsx`, `state/reducer.ts`.
- Test: `tests/test_agent_runtime.py`, `tests/test_agent_runtime_loop.py`, React composer tests.

- [ ] **Step 1: Add mode tests.** For one identical plan assert Agent validates then executes, Ask waits for one complete-plan approval, and Plan emits `plan_pending` without scene mutation; duplicate approval must return `stale_approval`.
- [ ] **Step 2: Run focused tests.** Run `python -m pytest tests/test_agent_runtime.py tests/test_agent_runtime_loop.py -k mode -q`; expected result is FAIL for fixed mapping and stale approval.
- [ ] **Step 3: Implement one normalization function.** Add `normalize_visible_mode(mode) -> (agent_mode, execution_mode, approval_required)` with Agent=`continuous`, Ask=`confirm`, Plan=`plan_pending`; migrate legacy records on read.
- [ ] **Step 4: Enforce the mutation gate.** Route every approved plan through validator then `SceneCommandService.execute`; consume approval tokens atomically and invalidate them from `stop_turn`.
- [ ] **Step 5: Remove the deprecated UI selector.** Keep backend compatibility fields in payloads but render only Agent/Ask/Plan; label Ask action `Confirm execution` and Plan action `Execute plan`.
- [ ] **Step 6: Run Python/React tests.** Run `python -m pytest tests/test_agent_runtime.py tests/test_agent_runtime_loop.py -q` and `pnpm --dir ui/agent_web test -- Composer.test.tsx`; expected result is PASS.
- [ ] **Step 7: Commit.** Run `git add agent/runtime.py agent/session_store.py agent/web_protocol.py ui/designer_window.py ui/agent_web/src tests/test_agent_runtime.py tests/test_agent_runtime_loop.py && git commit -m "feat: fix Agent Ask Plan execution modes"`.

<!-- openspec-task: 4.2 -->
### Task 16: Reduce the composer toolbar to Skills and attachments

**Files:**
- Modify: `ui/agent_web/src/components/Composer.tsx`, `AttachmentActions.tsx`, `ModeSelector.tsx`.
- Modify: `ui/agent_web/src/types.ts`, `ui/agent_web/src/App.tsx`.
- Test: `ui/agent_web/src/components/Composer.test.tsx`, new `AttachmentActions.test.tsx`.

- [ ] **Step 1: Add interaction tests.** Assert the left toolbar has only `Tools` and `+`; Tools opens an anchored skills popover and `+` exposes Add image/Add file. Assert outside click and Escape close the popover without sending an intent.
- [ ] **Step 2: Run the focused tests.** Run `pnpm --dir ui/agent_web test -- Composer.test.tsx AttachmentActions.test.tsx`; expected result is FAIL while old controls are rendered.
- [ ] **Step 3: Implement the two-button toolbar.** Use `lucide-react` icons with accessible tooltips; call `open_skills` for metadata and `attach_files` for validated paths. Do not add manual skill selection or scene mutation in React.
- [ ] **Step 4: Keep attachment validation before send.** Enforce maximum five items and existing file-size/type rules in the ContextBroker response; block `send_message` when validation fails.
- [ ] **Step 5: Run tests and build.** Run `pnpm --dir ui/agent_web test -- Composer.test.tsx AttachmentActions.test.tsx` and `pnpm --dir ui/agent_web build`; expected result is PASS.
- [ ] **Step 6: Commit.** Run `git add ui/agent_web/src && git commit -m "fix: simplify MathAgent composer toolbar"`.

<!-- openspec-task: 4.3 -->
### Task 17: Remove visible user-role words while preserving accessibility

**Files:**
- Modify: `ui/agent_web/src/components/Timeline.tsx`, `EventCard.tsx`, `styles/layout.css`.
- Test: `ui/agent_web/src/components/Timeline.test.tsx`, `App.test.tsx`.

- [ ] **Step 1: Add visual/semantic tests.** Render a user message and assert no visible `you`/`user` text exists; assert an `aria-label` or screen-reader-only role remains and the bubble is right-aligned.
- [ ] **Step 2: Run the tests to verify the regression.** Run `pnpm --dir ui/agent_web test -- Timeline.test.tsx App.test.tsx`; expected result is FAIL if the role word is visible.
- [ ] **Step 3: Update markup and CSS.** Keep semantic `role="article"` and an `sr-only` label, remove visible role spans, and set `margin-inline-start: auto` with a max width that wraps long math text.
- [ ] **Step 4: Run visual component tests.** Run `pnpm --dir ui/agent_web test -- Timeline.test.tsx App.test.tsx`; expected result is PASS.
- [ ] **Step 5: Commit.** Run `git add ui/agent_web/src/components ui/agent_web/src/styles && git commit -m "fix: streamline user message bubbles"`.

<!-- openspec-task: 4.4 -->
### Task 18: Make the 440px sidebar layout stable

**Files:**
- Modify: `ui/agent_web/src/styles/layout.css`, `theme.css`, `components/Composer.tsx`, `components/ModelSelector.tsx`.
- Test: `ui/agent_web/src/components/Composer.test.tsx`, new `layout.test.tsx`.

- [ ] **Step 1: Add narrow-layout assertions.** In a 440px container, assert header settings, model, context ring, input, and send controls are present, have stable widths, and do not create horizontal overflow.
- [ ] **Step 2: Run the test to establish the failure.** Run `pnpm --dir ui/agent_web test -- layout.test.tsx`; expected result is FAIL if controls overflow or are clipped.
- [ ] **Step 3: Implement CSS constraints.** Set `box-sizing: border-box`, `min-width: 0` on flex children, `grid-template-columns: 1fr auto`, fixed 32px icon buttons, `overflow-wrap:anywhere`, and `max-inline-size:100%` for popovers; keep the context ring read-only.
- [ ] **Step 4: Run tests and build.** Run `pnpm --dir ui/agent_web test -- layout.test.tsx Composer.test.tsx` and `pnpm --dir ui/agent_web build`; expected result is PASS.
- [ ] **Step 5: Commit.** Run `git add ui/agent_web/src/styles ui/agent_web/src/components && git commit -m "fix: constrain sidebar controls at 440px"`.

<!-- openspec-task: 4.5 -->
### Task 19: Verify 320px and 440px boundary behavior

**Files:**
- Modify: `ui/agent_web/src/styles/layout.css`, `components/HistoryView.tsx`, `components/SettingsView.tsx`, `components/ModelSettings.tsx`, `components/AttachmentActions.tsx`.
- Test: new `ui/agent_web/src/responsive.test.tsx`.

- [ ] **Step 1: Add viewport tests.** Render at 320px and 440px and assert history titles wrap, settings fields remain usable, Pro details stay inside the viewport, attachment menus are anchored within bounds, and no horizontal scrollbar is created.
- [ ] **Step 2: Run the responsive tests.** Run `pnpm --dir ui/agent_web test -- responsive.test.tsx`; expected result is FAIL before the boundary CSS is complete.
- [ ] **Step 3: Implement responsive rules.** Use container queries/media queries only for layout changes, not font scaling; clamp popover positions to the viewport, stack form rows below 360px, and preserve 32px touch targets.
- [ ] **Step 4: Run the responsive suite and build.** Run `pnpm --dir ui/agent_web test -- responsive.test.tsx` and `pnpm --dir ui/agent_web build`; expected result is PASS.
- [ ] **Step 5: Commit.** Run `git add ui/agent_web/src && git commit -m "fix: support narrow MathAgent viewports"`.

<!-- openspec-task: 5.1 -->
### Task 20: Consolidate Python contract tests

**Files:**
- Create: `tests/test_mathagent_sidebar_contracts.py`.
- Modify: `tests/test_session_store.py`, `tests/test_agent_bridge.py`, `tests/test_agent_provider.py`, `tests/test_agent_runtime.py` only when a focused regression belongs there.

- [ ] **Step 1: Add contract fixtures.** Create a temporary `.math` root, isolated `QSettings` organization/application, fake provider, and fake scene host; never use a real API key or renderer in tests.
- [ ] **Step 2: Add persistence/protocol/provider assertions.** Cover migration, visible/hidden filtering, title limits, fallback, custom CRUD, Responses protocol, context tiers, redaction, provider isolation, mode normalization, duplicate approval, and no-fallback errors.
- [ ] **Step 3: Run the new contract file.** Run `python -m pytest tests/test_mathagent_sidebar_contracts.py -q`; expected result is PASS and deterministic test ordering.
- [ ] **Step 4: Run all Python Agent tests.** Run `python -m pytest tests/test_agent_*.py tests/test_session_store.py -q`; expected result is PASS.
- [ ] **Step 5: Commit.** Run `git add tests/test_mathagent_sidebar_contracts.py tests/test_session_store.py tests/test_agent_bridge.py tests/test_agent_provider.py tests/test_agent_runtime.py && git commit -m "test: cover MathAgent sidebar Python contracts"`.

<!-- openspec-task: 5.2 -->
### Task 21: Consolidate React interaction and visual tests

**Files:**
- Create/modify: `ui/agent_web/src/components/*.{test.ts,test.tsx}`.
- Modify: `ui/agent_web/src/state/reducer.test.ts`, `ui/agent_web/src/App.test.tsx`.

- [ ] **Step 1: Add deterministic bridge fixtures.** Mock `qtBridge` with an in-memory event stream and stable request IDs; expose helpers for snapshots, mutation success/failure, sequence gaps, and background events.
- [ ] **Step 2: Cover the acceptance interactions.** Test immediate history/settings navigation, optimistic rollback, hidden recovery, model groups/Pro hover, thinking controls, custom CRUD, protocol selector, Skills and attachment menus, mode labels, background events, and absent visible role words.
- [ ] **Step 3: Run the React suite.** Run `pnpm --dir ui/agent_web test`; expected result is PASS with no network access and no dependence on WebEngine.
- [ ] **Step 4: Run TypeScript validation.** Run `pnpm --dir ui/agent_web exec tsc --noEmit`; expected result is PASS with strict mode enabled.
- [ ] **Step 5: Commit.** Run `git add ui/agent_web/src && git commit -m "test: cover MathAgent sidebar interactions"`.

<!-- openspec-task: 5.3 -->
### Task 22: Run focused, full, frontend, and OpenSpec verification

**Files:**
- Modify: `README.md` only if the implemented behavior is missing from user documentation.
- Test artifacts: no production files; retain failing logs outside the repository.

- [ ] **Step 1: Run focused Python checks.** Run `python -m pytest tests/test_mathagent_sidebar_contracts.py tests/test_agent_web_dispatch.py tests/test_agent_web_security.py -q`; expected result is PASS.
- [ ] **Step 2: Run focused frontend checks.** Run `pnpm --dir ui/agent_web test && pnpm --dir ui/agent_web exec tsc --noEmit && pnpm --dir ui/agent_web build`; expected result is PASS.
- [ ] **Step 3: Run the complete application suite.** Run `python -m pytest -q`; expected result is PASS for existing 2D, 3D, PyVista, SymPy, layer, and Agent tests.
- [ ] **Step 4: Run static and artifact checks.** Run `python -m compileall agent services ui tests`, `git diff --check`, and `openspec validate mathagent-sidebar-bugfix --type change --strict`; expected result is no compile/whitespace errors and `Change 'mathagent-sidebar-bugfix' is valid`.
- [ ] **Step 5: Update the README only after behavior is verified.** Document hidden sidebar startup, in-panel history, restore/undo/branch, Agent/Ask/Plan semantics, local `.math` storage, and provider configuration; do not document arbitrary Python execution.
- [ ] **Step 6: Commit verification/documentation.** Run `git add README.md && git commit -m "docs: describe MathAgent sidebar workflows"` only when README changed.

<!-- openspec-task: 5.4 -->
### Task 23: Verify concurrency, background events, stale approval, and credential leakage

**Files:**
- Modify: `agent/runtime.py`, `ui/designer_window.py`, `agent/web_protocol.py` only if a test exposes a contract defect.
- Create: `tests/test_mathagent_sidebar_concurrency.py`, `tests/test_mathagent_credential_scan.py`.

- [ ] **Step 1: Add concurrency tests.** Run two sessions in parallel and assert each receives only its own turn events; run one session with history/settings open and assert the turn continues and events are retained for the conversation view.
- [ ] **Step 2: Add stale-approval tests.** Stop an Ask/Plan turn, submit its old approval, and assert `stale_approval` with no scene mutation; submit the same valid approval twice and assert only one execute call.
- [ ] **Step 3: Add a credential scan.** Populate provider settings with a sentinel key and assert the sentinel is absent from SQLite bytes, serialized snapshots/events, bridge errors, Python logs captured by the test, and built `ui/agent_web/dist` assets.
- [ ] **Step 4: Run the boundary suite.** Run `python -m pytest tests/test_mathagent_sidebar_concurrency.py tests/test_mathagent_credential_scan.py -q`; expected result is PASS.
- [ ] **Step 5: Run the final verification command set.** Run `python -m pytest -q`, `pnpm --dir ui/agent_web test`, `pnpm --dir ui/agent_web exec tsc --noEmit`, `pnpm --dir ui/agent_web build`, and `openspec validate mathagent-sidebar-bugfix --type change --strict`; expected result is PASS for every command.
- [ ] **Step 6: Commit the final tests.** Run `git add tests/test_mathagent_sidebar_concurrency.py tests/test_mathagent_credential_scan.py agent/runtime.py ui/designer_window.py agent/web_protocol.py && git commit -m "test: verify MathAgent concurrency and secrecy"`.

## Risks and Guardrails

- Do not expose a Python callable, Qt object, PyVista handle, or SceneCommandService method to JavaScript; only `send_json(str)` and serialized events cross the bridge.
- Do not silently select Local when DeepSeek or a custom provider is unconfigured or fails; render a scoped error card.
- Keep `closed_at` and `hidden_at` independent and never cascade-delete turns, snapshots, branches, or attachments.
- Keep all credentials in QSettings; redact before persistence to events, snapshots, logs, or errors.
- Keep one active turn per session, allow different sessions to run concurrently, and invalidate approval tokens on stop.
- Treat `pnpm --dir ui/agent_web build` output as packaged local assets; no web server or remote asset fetch is allowed.
