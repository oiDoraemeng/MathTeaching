# MathAgent Web Sidebar UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the local React WebView workspace, strict JSON bridge, and Python projection layer for the MathAgent sidebar.

**Architecture:** Keep PySide6 as the desktop shell and expose one `send_json(str)` slot plus one `event_json(str)` signal through QWebChannel. React/TypeScript/Vite renders a local static document and projects Python snapshots/events; it never owns SQLite, credentials, scene objects, or execution methods.

**Tech Stack:** Python 3.11, PySide6 QtWebEngine/QtWebChannel, React, TypeScript, Vite, pnpm, Vitest, React Testing Library, markdown-it, DOMPurify, KaTeX, lucide-react, existing Agent Runtime and SessionStore.

---

<!-- openspec-task: 1.1 -->
### Task 1: Create the local frontend workspace

**Files:**
- Create: `ui/agent_web/package.json`
- Create: `ui/agent_web/pnpm-lock.yaml`
- Create: `ui/agent_web/index.html`
- Create: `ui/agent_web/vite.config.ts`
- Create: `ui/agent_web/tsconfig.json`
- Create: `ui/agent_web/src/main.tsx`
- Create: `ui/agent_web/src/types.ts`
- Create: `tests/test_agent_web_assets.py`

- [ ] **Step 1: Write the failing asset contract test**

  Add a Python test that resolves `ui/agent_web/dist/index.html`, parses the Vite manifest or HTML references, and asserts every script/style reference is relative and local. Assert the source manifest declares React, `markdown-it`, DOMPurify, KaTeX, and `lucide-react`.

- [ ] **Step 2: Run the focused test to verify it fails**

  Run: `uv run pytest tests/test_agent_web_assets.py -q`

  Expected: FAIL because the frontend workspace and `dist/` do not exist.

- [ ] **Step 3: Add the pnpm/Vite workspace**

  Define scripts in `package.json`:

  ```json
  {
    "scripts": {
      "dev": "vite",
      "build": "vite build",
      "test": "vitest run",
      "test:watch": "vitest"
    }
  }
  ```

  Pin React, ReactDOM, TypeScript, Vite, `@vitejs/plugin-react`, `markdown-it`, `dompurify`, `katex`, `lucide-react`, Vitest, jsdom, and React Testing Library. Configure Vite to emit `dist/manifest.json`, use relative asset paths, and copy local KaTeX fonts/styles into the output. `main.tsx` must mount `<App />` into `#root`; `types.ts` must export the protocol/event types used by later tasks.

- [ ] **Step 4: Install and build with pnpm**

  Run: `pnpm install --lockfile-only`, then `pnpm install --frozen-lockfile`, then `pnpm build` from `ui/agent_web`.

  Expected: `pnpm-lock.yaml` is created, `dist/index.html` and `dist/manifest.json` are emitted, and no Node process is required after the build.

- [ ] **Step 5: Run the focused test and commit**

  Run: `uv run pytest tests/test_agent_web_assets.py -q`.

  Expected: PASS. Commit with `git add ui/agent_web tests/test_agent_web_assets.py && git commit -m "feat: add MathAgent web workspace"`.

<!-- openspec-task: 1.2 -->
### Task 2: Implement the MathAgent shell and theme

**Files:**
- Create: `ui/agent_web/src/App.tsx`
- Create: `ui/agent_web/src/components/AgentHeader.tsx`
- Create: `ui/agent_web/src/components/SessionTabs.tsx`
- Create: `ui/agent_web/src/components/EmptyState.tsx`
- Create: `ui/agent_web/src/components/Timeline.tsx`
- Create: `ui/agent_web/src/components/Composer.tsx`
- Create: `ui/agent_web/src/styles/theme.css`
- Create: `ui/agent_web/src/styles/layout.css`
- Create: `ui/agent_web/src/App.test.tsx`

- [ ] **Step 1: Write failing component tests**

  Test that `App` renders `MathAgent`, a tab titled `New Chat`, the empty-state title/subtitle, four math starter cards, the exact placeholder `提问或输入 "/"快捷命令`, and an `Agent` selector. Test that the main panel has stable header, tab, timeline, and composer regions.

- [ ] **Step 2: Run the frontend test to verify it fails**

  Run: `pnpm test -- App.test.tsx`.

  Expected: FAIL because the React components do not exist.

- [ ] **Step 3: Implement the shell**

  Build `App` around a `useReducer` placeholder state with one session. `AgentHeader` must use lucide icons for new chat, history, settings, and close. `SessionTabs` must render closable tabs without allowing the last tab to be removed. `EmptyState` must show math-specific copy and starter cards. `Timeline` must own the scroll region. `Composer` must reserve a multiline input and two toolbar rows.

- [ ] **Step 4: Add stable visual tokens and layout**

  Define light/dark CSS variables for neutral IDE surfaces, borders, text, muted text, accent, success, warning, and error. Use a 420-480px host width, 36px header, 30px tabs, `minmax(0, 1fr)` timeline, and a fixed composer region. Avoid gradients, nested cards, emoji icons, and layout shifts.

- [ ] **Step 5: Run tests and commit**

  Run: `pnpm test -- App.test.tsx` and `pnpm build`.

  Expected: PASS and a valid `dist/`. Commit with `git add ui/agent_web && git commit -m "feat: add MathAgent web shell"`.

<!-- openspec-task: 1.3 -->
### Task 3: Implement event state and timeline cards

**Files:**
- Create: `ui/agent_web/src/state/reducer.ts`
- Create: `ui/agent_web/src/state/reducer.test.ts`
- Create: `ui/agent_web/src/components/EventCard.tsx`
- Create: `ui/agent_web/src/components/PlanCard.tsx`
- Create: `ui/agent_web/src/components/TurnActions.tsx`
- Create: `ui/agent_web/src/components/MarkdownContent.tsx`
- Modify: `ui/agent_web/src/components/Timeline.tsx`
- Modify: `ui/agent_web/src/types.ts`

- [ ] **Step 1: Write failing reducer and card tests**

  Cover a `session_snapshot`, two `message_delta` events merging into one explanation card, a `plan_ready` event appending a plan card, duplicate sequence suppression, and a successful turn showing restore/undo/branch controls only when `hovered=true`. Assert failed turns do not expose those controls and raw payloads are hidden until technical details are opened.

- [ ] **Step 2: Run the frontend tests to verify failure**

  Run: `pnpm test -- reducer.test.ts`.

  Expected: FAIL because the reducer and card components are not implemented.

- [ ] **Step 3: Define the projection types and reducer**

  Add discriminated TypeScript types for `SessionSnapshot`, `TimelineEvent`, `TurnProjection`, `ContextUsage`, and `ModelStatus`. Implement reducer actions `snapshot_loaded`, `event_received`, `hover_turn`, `toggle_details`, and `clear_session`. Merge `message_delta` text by `(session_id, turn_id)` and append non-delta event cards in arrival order.

- [ ] **Step 4: Render role-specific cards**

  Map runtime event names to user, explanation, scene context, calculation, plan, preview, execution, stopped, and error cards. `MarkdownContent` must sanitize Markdown with DOMPurify and render KaTeX from local assets. `PlanCard` must show summary, operation count, validation state, preview state, and an explicit technical-details disclosure. `TurnActions` must use absolute positioning and emit intent callbacks rather than calling Python methods.

- [ ] **Step 5: Run tests/build and commit**

  Run: `pnpm test -- reducer.test.ts` and `pnpm build`.

  Expected: PASS. Commit with `git add ui/agent_web && git commit -m "feat: render MathAgent event timeline"`.

<!-- openspec-task: 1.4 -->
### Task 4: Implement the composer interactions

**Files:**
- Modify: `ui/agent_web/src/components/Composer.tsx`
- Create: `ui/agent_web/src/components/AttachmentActions.tsx`
- Create: `ui/agent_web/src/components/ModeSelector.tsx`
- Create: `ui/agent_web/src/components/ModelSelector.tsx`
- Create: `ui/agent_web/src/components/ContextRing.tsx`
- Create: `ui/agent_web/src/components/Composer.test.tsx`
- Modify: `ui/agent_web/src/App.tsx`

- [ ] **Step 1: Write failing interaction tests**

  Test Enter sends a non-empty prompt, Shift+Enter inserts a newline, the send button becomes stop while `busy`, mode/model changes emit JSON intents, the context ring is read-only and exposes the percentage on hover, attachment actions emit an attachment intent, and turn actions emit restore/undo/branch intents.

- [ ] **Step 2: Run the frontend test to verify failure**

  Run: `pnpm test -- Composer.test.tsx`.

  Expected: FAIL because the interaction components are not implemented.

- [ ] **Step 3: Implement composer controls**

  Keep the input controlled in React state. On Enter without Shift call an `onIntent` callback with `send_message`; on busy call `stop_turn`. Render lucide attachment/image/document/menu/tool buttons, Agent/Ask/Plan options, a per-session model selector, and a CSS circular context ring with `aria-label` and a hover tooltip. The ring must have no click handler.

- [ ] **Step 4: Connect action callbacks to the protocol client seam**

  Define an `IntentSender` type that accepts a JSON envelope. Composer and turn-action components call only this interface. Do not import Qt, filesystem APIs, Runtime, or SceneCommandService into the frontend.

- [ ] **Step 5: Run tests/build and commit**

  Run: `pnpm test -- Composer.test.tsx` and `pnpm build`.

  Expected: PASS. Commit with `git add ui/agent_web && git commit -m "feat: add MathAgent composer controls"`.

<!-- openspec-task: 2.1 -->
### Task 5: Define and validate the versioned JSON protocol

**Files:**
- Modify: `agent/web_protocol.py`
- Create: `tests/test_agent_web_protocol.py`
- Modify: `agent/events.py`

- [ ] **Step 1: Write failing protocol tests**

  Add tests for a valid envelope, unknown type rejection, protocol version rejection, required `session_id` and `turn_id`, non-object payload rejection, maximum payload rejection, and JSON serialization of an error event. Test both Python dict input and raw JSON input.

- [ ] **Step 2: Run the focused tests to verify failure**

  Run: `uv run pytest tests/test_agent_web_protocol.py -q`.

  Expected: FAIL because the current bridge parser lacks protocol version, request IDs, sequence values, payload limits, snapshot intents, and the full event envelope.

- [ ] **Step 3: Implement immutable protocol models**

  Add frozen dataclasses `BridgeEnvelope`, `ClientIntent`, and `BridgeEvent` with `PROTOCOL_VERSION = 1`, explicit client/event type sets, required-ID rules, and `MAX_PAYLOAD_BYTES`. Parse JSON with `json.loads`, reject non-objects and trailing content, validate UTF-8 encoded size, and return plain dicts only from `to_dict()`.

- [ ] **Step 4: Keep legacy runtime event conversion explicit**

  Add an adapter that maps existing `AgentEvent` names such as `validation_result`, `preview_ready`, and `execution_finished` to the Web UI names without changing the existing runtime event class. Preserve the existing `parse_client_message` compatibility wrapper by delegating to the new validator.

- [ ] **Step 5: Run focused tests and commit**

  Run: `uv run pytest tests/test_agent_web_protocol.py tests/test_agent_events.py -q`.

  Expected: PASS. Commit with `git add agent/web_protocol.py agent/events.py tests/test_agent_web_protocol.py && git commit -m "feat: add versioned MathAgent web protocol"`.

<!-- openspec-task: 2.2 -->
### Task 6: Add the narrow AgentBridge and WebView host

**Files:**
- Create: `ui/agent_bridge.py`
- Create: `ui/agent_sidebar_web.py`
- Create: `tests/test_agent_bridge.py`
- Modify: `ui/agent_sidebar.py`

- [ ] **Step 1: Write failing bridge/host tests**

  Use a fake runtime callback and assert `AgentBridge.send_json()` forwards only validated intents, emits a JSON error for malformed input, and never exposes methods other than `send_json`. Instantiate the host in an offscreen QApplication and assert it contains exactly one `QWebEngineView`.

- [ ] **Step 2: Run the focused tests to verify failure**

  Run: `uv run pytest tests/test_agent_bridge.py -q`.

  Expected: FAIL because the bridge and WebView host do not exist.

- [ ] **Step 3: Implement the bridge contract**

  `AgentBridge(QObject)` must define only `event_json = Signal(str)` and `@Slot(str) send_json`. Its constructor receives an intent dispatcher callable and an event serializer. `send_json` parses the envelope, dispatches it, and catches exceptions into serializable `error` events. It must not retain a Qt widget, PyVista object, or direct command service reference.

- [ ] **Step 4: Implement the WebView host**

  `AgentSidebarWeb(QWidget)` creates one `QWebEngineView`, one `QWebChannel`, registers the bridge under `qtBridge`, and loads `mathagent://app/index.html`. It emits a snapshot request after `loadFinished` and forwards `event_json` to JavaScript through the channel. Keep the host independent of `DesignerWindow` so it can be tested with a fake dispatcher.

- [ ] **Step 5: Run focused Qt tests and commit**

  Run: `uv run pytest tests/test_agent_bridge.py -q`.

  Expected: PASS in the repository's offscreen Qt environment. Commit with `git add ui/agent_bridge.py ui/agent_sidebar_web.py ui/agent_sidebar.py tests/test_agent_bridge.py && git commit -m "feat: host MathAgent in Qt WebEngine"`.

<!-- openspec-task: 2.3 -->
### Task 7: Connect bridge intents to Runtime and SessionStore

**Files:**
- Modify: `ui/agent_bridge.py`
- Modify: `ui/agent_sidebar_web.py`
- Modify: `ui/designer_window.py`
- Create: `tests/test_agent_web_dispatch.py`

- [ ] **Step 1: Write failing dispatch tests**

  Use fake `AgentRuntime`, `SessionStore`, and scene adapter objects. Assert `send_message` calls `run_turn` with the selected session mode/model, `approve_plan` calls the runtime approval path, `restore_turn` and `undo_turn` call snapshot services without a provider call, and `branch_turn` persists a new session. Assert no test double receives a direct renderer call from the bridge.

- [ ] **Step 2: Run the focused test to verify failure**

  Run: `uv run pytest tests/test_agent_web_dispatch.py -q`.

  Expected: FAIL because the bridge has no dispatcher for these intent types.

- [ ] **Step 3: Implement a dispatcher-owned command map**

  Add a small Python dispatcher method that switches over the validated intent type and delegates to existing runtime/session APIs. Keep scene-changing approval in `AgentRuntime`; the bridge may request it but must not call `SceneCommandService.execute()`. Return a request acknowledgment and let runtime events carry the result.

- [ ] **Step 4: Wire DesignerWindow signals**

  Pass the existing runtime, session store, scene snapshot adapter, and model status callbacks into the WebView host. Forward runtime events through the bridge, send a fresh `session_snapshot` on panel open/tab change, and keep the viewport Agent button and close signal unchanged.

- [ ] **Step 5: Run focused regression tests and commit**

  Run: `uv run pytest tests/test_agent_web_dispatch.py tests/test_agent_runtime.py tests/test_sidebar_visibility.py -q`.

  Expected: PASS. Commit with `git add ui/agent_bridge.py ui/agent_sidebar_web.py ui/designer_window.py tests/test_agent_web_dispatch.py && git commit -m "feat: connect MathAgent web intents to runtime"`.

<!-- openspec-task: 2.4 -->
### Task 8: Enforce local asset security

**Files:**
- Create: `ui/agent_web/security.ts`
- Modify: `ui/agent_sidebar_web.py`
- Create: `tests/test_agent_web_security.py`
- Modify: `ui/agent_web/index.html`

- [ ] **Step 1: Write failing security tests**

  Test the asset resolver rejects path traversal, unknown extensions, absolute filesystem paths, and network URLs. Test the WebEngine page rejects navigation to `http`, `https`, and `file` URLs. Test the HTML contains a CSP with no remote source and no API key literal.

- [ ] **Step 2: Run focused tests to verify failure**

  Run: `uv run pytest tests/test_agent_web_security.py -q`.

  Expected: FAIL because the custom scheme, CSP, and URL allowlist do not exist.

- [ ] **Step 3: Implement the read-only asset resolver**

  Resolve requested paths relative to the packaged `dist` root, normalize them, reject `..`, and allow only `index.html`, Vite assets, fonts, KaTeX files, and icons. Register `mathagent://app/` with a read-only `QWebEngineUrlSchemeHandler`; return a 404 response for everything else.

- [ ] **Step 4: Add page policy and navigation blocking**

  Add a CSP meta tag to `index.html` with local script/style/font/image sources and `connect-src 'none'`. Install a `QWebEnginePage` navigation filter that accepts only the `mathagent` scheme and rejects remote or file URLs. Do not publish any extra bridge objects or enable production developer tools.

- [ ] **Step 5: Run tests and commit**

  Run: `uv run pytest tests/test_agent_web_security.py tests/test_agent_bridge.py -q` and `pnpm build`.

  Expected: PASS. Commit with `git add ui/agent_web ui/agent_sidebar_web.py tests/test_agent_web_security.py && git commit -m "feat: secure local MathAgent web assets"`.

<!-- openspec-task: 3.1 -->
### Task 9: Define Python-to-React projection payloads

**Files:**
- Create: `agent/ui_projection.py`
- Create: `tests/test_agent_ui_projection.py`
- Modify: `ui/agent_bridge.py`
- Modify: `agent/session_store.py`

- [ ] **Step 1: Write failing projection tests**

  Build a temporary SessionStore with two sessions, turns, events, per-session mode/model, and context usage. Assert the projection contains session tabs, active session, turn cards, model status, settings state, and only serializable snapshot data. Assert no SQLite row, Qt object, credential, or raw provider response appears.

- [ ] **Step 2: Run the focused test to verify failure**

  Run: `uv run pytest tests/test_agent_ui_projection.py -q`.

  Expected: FAIL because projection builders do not exist.

- [ ] **Step 3: Implement explicit projection dataclasses**

  Add `SessionProjection`, `TurnProjection`, `SettingsProjection`, and `SnapshotProjection` builders that consume `SessionRecord`, `TurnRecord`, `EventRecord`, `ContextUsage`, and model status. Serialize only JSON primitives and map event payloads to the Web UI event envelope.

- [ ] **Step 4: Add snapshot and event projection entry points**

  Provide `build_session_snapshot(store, active_session_id, model_status, settings_state)` and `project_runtime_event(event, sequence)`. Keep the browser projection separate from SQLite schema and make sequence allocation explicit in the bridge/runtime adapter.

- [ ] **Step 5: Run focused tests and commit**

  Run: `uv run pytest tests/test_agent_ui_projection.py tests/test_session_store.py -q`.

  Expected: PASS. Commit with `git add agent/ui_projection.py agent/session_store.py ui/agent_bridge.py tests/test_agent_ui_projection.py && git commit -m "feat: project MathAgent sessions to web UI"`.
