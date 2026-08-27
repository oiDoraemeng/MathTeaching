# Deep Technical Design: MathAgent Sidebar Bug Fix

## 1. State ownership and view navigation

The React document owns ephemeral UI state only: active view, open popovers, draft titles, draft provider forms, optimistic selection, and pending request IDs. Python remains the source of truth for sessions, turns, scene snapshots, provider credentials, custom model records, Memory, Rules, and runtime events.

The document has three local views: `conversation` (tabs, timeline, composer), `history` (visible sessions, title editing, hide and recovery), and `settings` (Agent/model, Skills, Memory, Rules tabs). History and settings switch locally immediately. Python receives `open_history` or `open_settings` for snapshot refresh, but a delayed response cannot block navigation. `restore_session_view` returns to the conversation without changing the scene. Runtime events continue accumulating while secondary views are open.

Every mutating UI intent has a `request_id`. The reducer applies an optimistic transition, records the request, and rolls it back on a matching error. A successful response replaces the optimistic item with a Python projection. Retry-safe operations are idempotent by `(session_id, request_id)`.

## 2. JSON bridge contract

The bridge remains one `AgentBridge.send_json` Qt Slot. No Qt or Python object is exposed. Additional intent types are `open_history`, `open_settings`, `restore_session_view`, `rename_session`, `hide_session`, `restore_hidden_session`, `save_model_provider`, `test_model_provider`, `save_custom_model`, `update_custom_model`, `delete_custom_model`, `set_selected_model`, `set_thinking_preferences`, and `open_skills`.

Responses are serializable `history_snapshot`, `settings_snapshot`, `model_catalog`, `mutation_succeeded`, `mutation_failed`, `provider_test_result`, and existing runtime events. A mutation error includes only a stable code, readable message, and request ID; it never includes API keys or raw headers.

Payload validation is field-specific: IDs are non-empty and at most 128 characters; titles default to `New Chat` and are capped at 80 Unicode code points; provider URLs must be HTTPS or localhost HTTP, contain no credentials, and be at most 512 characters; API keys are accepted only in save/test requests and never echoed; custom model IDs are at most 128 characters; context limits must use advertised tiers; the existing global payload limit remains active.

## 3. Conversation history persistence

Add nullable `hidden_at` to `sessions` with an additive migration guarded by `PRAGMA table_info`. Existing rows receive `NULL`. `SessionRecord` and projections expose hidden state without exposing SQLite rows directly.

`list_sessions()` defaults to visible sessions. History uses visible sessions plus an explicit hidden-session recovery query. Closing a tab is `closed_at`; hiding is `hidden_at`; these states are independent. Hiding is reversible and never cascades to turns, events, snapshots, attachments, or branches.

Duplicate titles are allowed. Empty or whitespace titles become `New Chat`; titles longer than 80 code points are rejected with a field error. Hiding the active session selects the most recently opened visible session, then most recently updated visible session, and finally creates a new visible `New Chat`. At least one visible session always exists. Restoring a hidden session clears `hidden_at` and does not restore or change the scene.

## 4. Model catalog and provider configuration

Python emits separate `builtin` and `custom` groups. Built-ins have stable display metadata and separate API model IDs: `Deepseek-V4-Flash High`, `Deepseek-V4-Pro High`, and `deepseek-v4-flash-vision-exp` with `High` capability. The first built-in is the default when a session has no valid selection. The bottom model control displays the current selection and opens the catalog popover; settings owns management.

The Pro hover card is actionable. Thinking is enabled by default at `High`; preferences are stored per session as `thinking_enabled` and `thinking_level` (`Low`, `High`, `X-High`). Turning thinking off hides and disables levels; the last level is retained when re-enabled.

The settings provider form is labeled `OpenAI - Responses` by default, but supports `Responses` and `Chat Completions`. Built-in DeepSeek presets use the configured endpoint and selected protocol. Custom models store provider, protocol, Base URL, API key, model ID, timeout, tool/image/reasoning capabilities, and input/output context tiers in QSettings JSON. Custom models can be edited or permanently deleted; deletion never affects sessions or built-ins.

Saving does not test connectivity. A separate bounded `Test connection` action returns success/failure without changing saved configuration. Save failures retain drafts. API keys are stored locally in QSettings, masked in UI, excluded from SQLite, snapshots, event payloads, logs, and error text, and never sent through QWebChannel.

## 5. Execution mode semantics

The Web UI no longer renders `confirm`/`continuous` controls. The runtime normalizes visible modes: `Agent` to `continuous` and execute after validation; `Ask` to `confirm` and wait for one approval for the complete plan; `Plan` to `plan_pending` and never mutate before approval.

Legacy records migrate on read: Agent becomes continuous, Ask becomes confirm, and Plan becomes confirm plus waiting. Existing command validation and SceneCommandService remain the only mutation path. Duplicate or stale approval is rejected idempotently and cannot execute twice. Plan cards use `确认执行` for Ask and `执行计划` for Plan. Stop cancels provider work and invalidates pending approval.

## 6. Toolbar, attachments, and presentation

The composer left toolbar contains only `工具` and `+`. `工具` opens an anchored Skills popover; it lists registered skills and closes on outside click or Escape without changing the scene or forcing a skill choice. `+` opens `添加图片` and `添加文件`; both use ContextBroker.

File selection supports multi-select but enforces at most five attachments and existing per-type limits. Images may be selected for a model without image capability, but submission is blocked with a capability error and no model request. User messages are right-aligned bubbles without visible `你` or `用户`; accessible labels remain screen-reader-only.

## 7. Concurrency and failure boundaries

Only one model turn runs per session; different sessions may run concurrently. Opening history/settings never stops a turn. Runtime events persist and reduce in the background. Switching sessions only changes projection and never applies a snapshot.

Optimistic mutations roll back on matching `mutation_failed`. Sequence gaps request a fresh session/settings snapshot. If a snapshot names a hidden active session, Python chooses a visible fallback before emitting it. Provider errors remain scoped to the turn and never silently fall back to Local.

## 8. Acceptance and test matrix

Python tests cover additive migration, visible/hidden filtering, duplicate/empty/overlong titles, hidden-current fallback, hidden restore, custom model CRUD, QSettings key redaction, protocol selection, context-tier validation, provider test isolation, mode normalization, stale approval rejection, and provider error propagation.

React tests cover immediate history/settings navigation, optimistic rollback, hidden recovery, model groups, Pro hover, per-session thinking controls, custom CRUD, protocol selector, Skills popover, attachment menu and multi-select validation, mode-specific labels, background events, and no visible role labels.

Qt/WebEngine integration tests verify JSON-only intents, no credential in snapshots/events, 440px and 320px layout boundaries, and no scene mutation when opening/closing secondary views.
