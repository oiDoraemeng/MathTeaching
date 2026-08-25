# MathAgent Web Sidebar UI Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect the local Web UI to the existing MathAgent runtime, replace the Qt conversation surface on the main branch, and verify the packaged desktop experience.

**Architecture:** Python Runtime and SessionStore remain the only state and mutation authorities. Runtime events are projected into the QWebChannel JSON bridge and consumed by the React reducer. The pre-migration Qt panel is available only on the `math-qt` Git branch; the main branch contains no runtime fallback or compatibility panel.

**Tech Stack:** PySide6, QtWebEngine, QtWebChannel, existing Python Agent Runtime/SessionStore/SceneCommandService, React/TypeScript/Vite, pnpm, Vitest, pytest, PyVista, SymPy.

---

<!-- openspec-task: 3.2 -->
### Task 1: Stream runtime events into the Web UI

**Files:**
- Modify: `agent/runtime.py`
- Modify: `services/agent_worker.py`
- Modify: `ui/agent_bridge.py`
- Modify: `ui/agent_web/src/state/reducer.ts`
- Create: `ui/agent_web/src/bridge/qtBridge.ts`
- Create: `ui/agent_web/src/bridge/qtBridge.test.ts`

- [ ] **Step 1: Write failing end-to-end event tests**

  Use a fake provider and fake command host to assert a streamed turn emits ordered `message_delta`, `plan_ready`, `validation`, `preview`, `execution`, and `turn_finished` envelopes. Assert confirmation waits, Ask does not mutate, Plan does not apply, continuous applies after validation, stop prevents later tool calls, restore/undo do not call the provider, and branch creates a new session.

- [ ] **Step 2: Run focused tests to verify failure**

  Run: `uv run pytest tests/test_agent_runtime_loop.py tests/test_agent_web_dispatch.py -q` and `pnpm test -- qtBridge.test.ts`.

  Expected: FAIL because the current Runtime event names and Web UI bridge are not connected as one ordered stream.

- [ ] **Step 3: Add sequence-aware runtime forwarding**

  Give each session/turn event a monotonically increasing sequence in the Python projection adapter. Convert legacy `AgentEvent` names to the Web UI event names, preserve the original payload, and emit `turn_finished` after persistence. `AgentWorker` forwards events through a Qt signal without passing Qt/PyVista objects.

- [ ] **Step 4: Implement the browser bridge client**

  `qtBridge.ts` must wait for `QWebChannel` readiness, send JSON envelopes through exactly `qtBridge.send_json`, parse `event_json`, and dispatch them to the reducer. On a sequence gap it sends `request_snapshot`; on duplicate it does nothing. It must expose no generic method invocation.

- [ ] **Step 5: Run focused tests and commit**

  Run: `uv run pytest tests/test_agent_runtime_loop.py tests/test_agent_web_dispatch.py -q` and `pnpm test -- qtBridge.test.ts && pnpm build`.

  Expected: PASS. Commit with `git add agent/runtime.py services/agent_worker.py ui/agent_bridge.py ui/agent_web && git commit -m "feat: stream MathAgent runtime events to web UI"`.

<!-- openspec-task: 3.3 -->
### Task 2: Persist per-session UI state and projection recovery

**Files:**
- Modify: `agent/session_store.py`
- Modify: `ui/agent_bridge.py`
- Modify: `ui/agent_sidebar_web.py`
- Modify: `ui/agent_web/src/state/reducer.ts`
- Create: `tests/test_agent_web_persistence.py`

- [ ] **Step 1: Write failing persistence tests**

  Create a temporary `.math` store, change mode, execution strategy, model, and attachment metadata in two sessions, close/reopen one tab, and request a snapshot. Assert each session restores its own values, closed history remains reopenable, attachments remain metadata-only, and opening the sidebar does not restore a scene implicitly.

- [ ] **Step 2: Run the focused test to verify failure**

  Run: `uv run pytest tests/test_agent_web_persistence.py -q`.

  Expected: FAIL because the Web UI dispatcher does not persist or project all per-session selections.

- [ ] **Step 3: Implement preference and attachment intents**

  Route `set_mode`, `set_execution_mode`, and `set_model` to `SessionStore.set_session_preferences`. Route `attach_files` to the existing Python validation/copy pipeline; return relative path metadata only. Emit `settings_state` and updated `session_snapshot` after writes.

- [ ] **Step 4: Recover projection on open and tab switch**

  `AgentSidebarWeb` requests a fresh snapshot on `loadFinished` and after a tab-change intent. The reducer replaces only the browser projection. No snapshot restore method is called unless the user sends `restore_turn` or `undo_turn`.

- [ ] **Step 5: Run tests and commit**

  Run: `uv run pytest tests/test_agent_web_persistence.py tests/test_session_store.py -q` and `pnpm build`.

  Expected: PASS. Commit with `git add agent/session_store.py ui/agent_bridge.py ui/agent_sidebar_web.py ui/agent_web tests/test_agent_web_persistence.py && git commit -m "feat: persist MathAgent web session state"`.

<!-- openspec-task: 4.1 -->
### Task 3: Install the WebView sidebar on the main branch

**Files:**
- Modify: `ui/agent_sidebar.py`
- Modify: `ui/designer_window.py`
- Create: `tests/test_agent_sidebar_web_integration.py`

- [ ] **Step 1: Verify the backup branch before migration**

  Run: `git show math-qt:ui/agent_panel.py`, `git show math-qt:ui/agent_sidebar.py`, and `git show math-qt:tests/test_agent_panel.py`.

  Expected: the old Qt panel and focused tests exist on `math-qt`; do not modify that branch during this task.

- [ ] **Step 2: Write failing Qt integration tests**

  Test `AgentSidebar` starts hidden, owns exactly one WebView host when opened, uses width 440, opens from the viewport Agent icon, closes without a layout slot, and does not change the fake scene snapshot when a session tab intent is received.

- [ ] **Step 3: Run the focused tests to verify failure**

  Run: `uv run pytest tests/test_agent_sidebar_web_integration.py tests/test_sidebar_visibility.py -q`.

  Expected: FAIL because `AgentSidebar` still constructs and exposes the Qt `AgentPanel`.

- [ ] **Step 4: Replace the panel child with `AgentSidebarWeb`**

  Remove the `AgentPanel` import and child from the main branch. Keep the navigation/settings pages in the sidebar container, but make the Agent page the WebView host. Preserve `expand`, `collapse`, `state`, fixed width, and existing DesignerWindow Agent-button connections. Pass Runtime, SessionStore, snapshot adapter, and model status into the host.

- [ ] **Step 5: Run integration tests and commit**

  Run: `uv run pytest tests/test_agent_sidebar_web_integration.py tests/test_sidebar_visibility.py tests/test_main_window_layout.py -q`.

  Expected: PASS. Commit with `git add ui/agent_sidebar.py ui/designer_window.py tests/test_agent_sidebar_web_integration.py && git commit -m "feat: install WebView MathAgent sidebar"`.

<!-- openspec-task: 4.2 -->
### Task 4: Remove the old Qt panel from the main branch

**Files:**
- Modify: `ui/designer_window.py`
- Modify: `ui/agent_sidebar.py`
- Modify: `tests/test_agent_panel.py`
- Modify: `tests/test_main_window_layout.py`
- Modify: `tests/test_sidebar.py`

- [ ] **Step 1: Write the migration guard test**

  Add a test that scans the main-branch UI modules and asserts they do not import `AgentPanel`, `QTextBrowser`, or the old Qt timeline classes for the sidebar. Assert no `mathagent.web_ui_enabled` setting or fallback path exists.

- [ ] **Step 2: Run the guard test to verify failure**

  Run: `uv run pytest tests/test_agent_panel_migration.py -q`.

  Expected: FAIL because the old panel imports and compatibility methods are still present.

- [ ] **Step 3: Remove old imports and execution wiring**

  Delete main-branch imports and calls to `AgentPanel` methods in `DesignerWindow`. Move any needed signal behavior into the JSON bridge. Remove `AgentPanel`-specific tests from the main-branch suite or replace them with Web UI bridge/integration tests; do not delete the `math-qt` branch.

- [ ] **Step 4: Run repository-wide import checks**

  Run: `rg -n "from ui\.agent_panel|import ui\.agent_panel|AgentPanel|mathagent\.web_ui_enabled" ui agent services tests`.

  Expected: no runtime import or fallback references remain on the main branch; references in historical documentation are reviewed and removed if they describe current behavior.

- [ ] **Step 5: Run focused tests and commit**

  Run: `uv run pytest tests/test_agent_panel_migration.py tests/test_agent_sidebar_web_integration.py tests/test_main_window_layout.py -q`.

  Expected: PASS. Commit with `git add ui tests && git commit -m "refactor: remove legacy Qt Agent panel"`.

<!-- openspec-task: 4.3 -->
### Task 5: Update pnpm packaging and release asset checks

**Files:**
- Modify: `pyproject.toml`
- Modify: `requirements.txt`
- Create: `scripts/build_agent_web.ps1`
- Create: `tests/test_agent_web_packaging.py`
- Modify: `.gitignore`

- [ ] **Step 1: Write failing packaging tests**

  Assert Python test commands do not invoke Node, `ui/agent_web/dist/index.html` and `manifest.json` exist, all manifest files resolve below the dist root, and the build script uses `pnpm install --frozen-lockfile` followed by `pnpm build`.

- [ ] **Step 2: Run the focused test to verify failure**

  Run: `uv run pytest tests/test_agent_web_packaging.py -q`.

  Expected: FAIL until the build helper and manifest checks exist.

- [ ] **Step 3: Add the build helper and package resource rules**

  Make `scripts/build_agent_web.ps1` resolve the repository path explicitly, run pnpm in `ui/agent_web`, and fail if `dist/index.html` or the manifest is missing. Keep frontend dev dependencies out of Python dependency declarations. Include `dist/` in source control; ignore only transient Vite cache files.

- [ ] **Step 4: Run the production build and packaging tests**

  Run: `pwsh -File scripts/build_agent_web.ps1`, then `uv run pytest tests/test_agent_web_packaging.py -q`.

  Expected: build exits 0, local asset manifest validation passes, and Python tests remain independent of Node.

- [ ] **Step 5: Commit**

  Run: `git add scripts ui/agent_web pyproject.toml requirements.txt .gitignore tests/test_agent_web_packaging.py && git commit -m "build: package local MathAgent web assets"`.

<!-- openspec-task: 5.1 -->
### Task 6: Add Python protocol and bridge isolation coverage

**Files:**
- Modify: `tests/test_agent_web_protocol.py`
- Modify: `tests/test_agent_bridge.py`
- Create: `tests/test_agent_web_isolation.py`

- [ ] **Step 1: Add protocol matrix tests**

  Cover every client intent, every runtime event projection, required-ID rules, protocol mismatch, malformed JSON, oversized payload, duplicate request ID handling, and serializable error responses.

- [ ] **Step 2: Add bridge isolation tests**

  Inspect the public `AgentBridge` meta-object and assert only `send_json` is invokable. Use a fake dispatcher to prove approve/restore/undo/branch intents call Runtime/session adapters, never PyVista or `SceneCommandService.execute()` directly, and never return credentials or hidden reasoning.

- [ ] **Step 3: Run focused tests**

  Run: `uv run pytest tests/test_agent_web_protocol.py tests/test_agent_bridge.py tests/test_agent_web_isolation.py -q`.

  Expected: PASS with no Qt/PyVista object crossing the JSON boundary.

- [ ] **Step 4: Commit**

  Run: `git add tests && git commit -m "test: cover MathAgent bridge isolation"`.

<!-- openspec-task: 5.2 -->
### Task 7: Add frontend reducer and component coverage

**Files:**
- Modify: `ui/agent_web/src/state/reducer.test.ts`
- Modify: `ui/agent_web/src/App.test.tsx`
- Modify: `ui/agent_web/src/components/Composer.test.tsx`
- Create: `ui/agent_web/src/components/Timeline.test.tsx`
- Create: `ui/agent_web/src/components/SessionTabs.test.tsx`

- [ ] **Step 1: Cover snapshot and ordered event behavior**

  Test snapshot replacement, incremental text merge, duplicate suppression, sequence-gap recovery, tab switching, and that switching sessions does not emit restore or scene mutation intents.

- [ ] **Step 2: Cover cards and composer behavior**

  Test all event-card types, Markdown/KaTeX sanitization, technical details disclosure, plan validation state, send/stop, Agent/Ask/Plan, context hover percentage, and hover-only restore/undo/branch actions.

- [ ] **Step 3: Run frontend tests and build**

  Run: `pnpm test` and `pnpm build` from `ui/agent_web`.

  Expected: all frontend tests pass and the committed dist output is regenerated.

- [ ] **Step 4: Commit**

  Run: `git add ui/agent_web && git commit -m "test: cover MathAgent web interactions"`.

<!-- openspec-task: 5.3 -->
### Task 8: Add Qt WebView integration coverage

**Files:**
- Modify: `tests/test_agent_sidebar_web_integration.py`
- Create: `tests/test_agent_web_offline.py`
- Modify: `tests/test_main_window_layout.py`

- [ ] **Step 1: Test custom-scheme loading**

  Instantiate the host in an offscreen QApplication, wait for `loadFinished`, and assert the loaded URL is `mathagent://app/index.html`, the document title is MathAgent, and no network request is required.

- [ ] **Step 2: Test sidebar lifecycle**

  Assert hidden startup, Agent-button open, fixed width, close releasing layout space, one WebView instance, and tab switching without a scene snapshot mutation.

- [ ] **Step 3: Run focused Qt tests**

  Run: `uv run pytest tests/test_agent_sidebar_web_integration.py tests/test_agent_web_offline.py tests/test_main_window_layout.py -q`.

  Expected: PASS in the configured Qt offscreen environment; skip only when QtWebEngine is unavailable and report the dependency explicitly.

- [ ] **Step 4: Commit**

  Run: `git add tests && git commit -m "test: verify WebView sidebar integration"`.

<!-- openspec-task: 5.4 -->
### Task 9: Run release verification

**Files:**
- Modify: `openspec/changes/mathagent-web-sidebar-ui/tasks.md`

- [ ] **Step 1: Build frontend assets**

  Run: `pnpm install --frozen-lockfile` and `pnpm build` from `ui/agent_web`.

  Expected: exit 0 and `dist/manifest.json` contains only local asset paths.

- [ ] **Step 2: Run focused test groups**

  Run: `uv run pytest tests/test_agent_web_protocol.py tests/test_agent_bridge.py tests/test_agent_web_dispatch.py tests/test_agent_sidebar_web_integration.py tests/test_agent_web_assets.py tests/test_agent_web_packaging.py -q`.

  Expected: all focused protocol, bridge, asset, packaging, and integration tests pass.

- [ ] **Step 3: Run full Python and static verification**

  Run: `uv run pytest -q`, `uv run python -m compileall agent services ui tests`, and `git diff --check`.

  Expected: all Python tests pass, compileall reports no errors, and diff check is clean.

- [ ] **Step 4: Validate OpenSpec**

  Run: `openspec validate mathagent-web-sidebar-ui --type change --strict`.

  Expected: `Change 'mathagent-web-sidebar-ui' is valid`.

- [ ] **Step 5: Mark completed OpenSpec task and commit**

  Change only the `5.4` checkbox to `[x]` after all commands pass. Commit with `git add openspec/changes/mathagent-web-sidebar-ui/tasks.md && git commit -m "test: verify MathAgent web sidebar release"`.

<!-- openspec-task: 5.5 -->
### Task 10: Document the pnpm WebView workflow and Git rollback path

**Files:**
- Modify: `README.md`
- Create: `docs/mathagent-web-sidebar.md`
- Modify: `docs/superpowers/specs/2026-08-26-mathagent-web-sidebar-ui-design.md`

- [ ] **Step 1: Write documentation checks**

  Add a documentation test or scripted check that required strings exist: `pnpm install --frozen-lockfile`, `pnpm build`, `mathagent://app/`, `QWebChannel`, JSON-only bridge, `.math`, and `math-qt`. Assert no documentation advertises arbitrary Python, terminal, or code-agent execution.

- [ ] **Step 2: Update user/developer documentation**

  Explain the hidden Agent toggle, local WebView UI, pnpm build, committed dist assets, bridge boundary, offline policy, session persistence, and that rollback is through the `math-qt` Git branch rather than an application setting. Keep user-facing text focused on mathematical teaching behavior.

- [ ] **Step 3: Run documentation checks and commit**

  Run: `uv run pytest tests/test_documentation.py -q` and `git diff --check`.

  Expected: PASS. Commit with `git add README.md docs && git commit -m "docs: document MathAgent web sidebar workflow"`.
