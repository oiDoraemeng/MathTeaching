# UI Design Refresh: Shell Layout and Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the main-window information architecture with a compact status bar and persisted resizable side panels, remove retired shell code, and prove the finished dual-theme desktop and Web UI behavior through focused and full verification.

**Architecture:** `MainWindow` keeps the live horizontal scene layout intact and nests it in a new vertical central layout alongside a 30px status bar. A reusable `_PanelResizeHandle` owns pointer math, clamping, double-click reset, and `QSettings` persistence; `AgentSidebar` exposes width constants and no longer contains retired collapsed-bar UI. Tests exercise pure resize semantics and Qt integration separately.

**Tech Stack:** Python 3.11, PySide6, QSettings, PyVista/PyVistaQt, React/TypeScript, Vitest, pnpm, pytest, OpenSpec CLI.

**Spec:** `openspec/changes/ui-design-refresh/design.md`, `openspec/changes/ui-design-refresh/specs/app-shell/spec.md`, `openspec/changes/ui-design-refresh/specs/mathagent-sidebar/spec.md`, and `openspec/changes/ui-design-refresh/specs/ui-design-system/spec.md`

## Global Constraints

- The status bar is exactly 30px and contains passive scene/Agent state plus the theme control; it must not become a business-operation toolbar or overflow at 1024px window width.
- Maintain a three-region shell: algebra 260-420px (default 320), viewport flexible, Agent 360-560px (default 440). Handles are 5px; the Agent handle is absent when the panel is hidden.
- Both widths persist in QSettings under `ui/algebra_panel_width` and `ui/agent_panel_width`; invalid values clamp to defaults; double-click restores defaults.
- Do not migrate the viewport into a QSplitter or alter the native VTK widget parent hierarchy.
- `ui/main_window.py` and the Designer-file legacy sidebar are retired; no compatibility UI should remain after removal.
- Retain WebView isolation and test all existing 2D/3D render and bridge paths before declaring completion.

---

<!-- openspec-task: 4.1 -->
### Task 1: Add the compact shell status bar and theme cycle control

**Files:**
- Modify: `ui/designer_window.py`
- Create: `ui/status_bar.py`
- Modify: `ui/styles/base.qss.in`
- Modify: `ui/icons.py`
- Create: `tests/test_app_status_bar.py`
- Modify: `tests/test_main_window_layout.py`

**Interfaces:**
- Produces: `AppStatusBar(QWidget)` with `set_scene_mode(mode: SceneMode)`, `set_active_tool(tool: str | None)`, `set_render_status(text: str)`, `set_agent_status(state: str)`, and `set_theme_mode(mode: ThemeMode)`.
- Produces signals `agent_toggle_requested` and `theme_cycle_requested`; `MainWindow.cycle_theme_mode()` persists then reapplies the selected mode.

- [x] **Step 1: Write failing status-bar layout and interaction tests**

  Add tests that construct the bar in an offscreen app and assert fixed height 30, visible mode/tool/render/Agent/theme controls, Agent segment emits one toggle request on click, and theme control cycles `system -> light -> dark -> system` while updating its accessible tooltip. Include a 1024px host layout assertion that all child geometry remains in bounds.

- [x] **Step 2: Run the focused test and confirm missing shell components**

  Run: `uv run pytest tests/test_app_status_bar.py tests/test_main_window_layout.py -q`

  Expected: FAIL because no status-bar module or vertical shell layout exists.

- [x] **Step 3: Implement `AppStatusBar` with tokenized controls**

  Build a 30px `QFrame` named `appStatusBar`. Use labels for `2D`/`3D`, an optional active-tool pill, a concise render indicator, a clickable Agent segment, a stretch, and a 28px theme `QToolButton`. Use `sun`, `moon`, and `monitor` from `ui.icons`; set tooltip text to the mode that will result from the next click or the current persisted mode, consistently with the spec. Do not put business actions in the bar.

- [x] **Step 4: Nest the existing root layout without changing viewport ownership**

  In `MainWindow._load_designer_form` or an installation helper, take the existing `rootLayout` from the central widget, place it in a new zero-margin vertical root container, and append `AppStatusBar`. Keep the existing `viewportHost`, overlays, and `QtInteractor` parent hierarchy intact. Wire current scene-mode, 2D-tool, render completion, and Agent expand/collapse paths to status updates.

- [x] **Step 5: Run status/layout regressions and commit**

  Run: `uv run pytest tests/test_app_status_bar.py tests/test_main_window_layout.py tests/test_2d_geometry_toolbar.py tests/test_sidebar_visibility.py -q`

  Expected: PASS. Commit with `git add ui/status_bar.py ui/designer_window.py ui/styles/base.qss.in ui/icons.py tests && git commit -m "feat: add main window status bar"`.

<!-- openspec-task: 4.2 -->
### Task 2: Add reusable persisted panel resize handles

**Files:**
- Create: `ui/panel_resize_handle.py`
- Modify: `ui/designer_window.py`
- Modify: `ui/algebra_panel.py`
- Modify: `ui/agent_sidebar.py`
- Modify: `ui/styles/base.qss.in`
- Create: `tests/test_panel_resize_handle.py`
- Modify: `tests/test_main_window_layout.py`

**Interfaces:**
- Produces: `PanelResizeSpec(minimum: int, maximum: int, default: int, settings_key: str, edge: Literal["right", "left"])` and `_PanelResizeHandle(QWidget)`.
- `_PanelResizeHandle` provides `restore_width() -> int`, `set_width(value: int, *, persist: bool = True) -> int`, and `width_changed = Signal(int)`.
- `AgentSidebar` exports `MIN_WIDTH = 360`, `DEFAULT_WIDTH = 440`, `MAX_WIDTH = 560`; Algebra panel limits are 260/320/420.

- [x] **Step 1: Write failing pure behavior and Qt-drag tests**

  Add tests for settings fallback, clamping, persistence round-trip, double-click reset, and direction-specific drag deltas:

  ```python
  def test_left_panel_handle_clamps_and_persists(qsettings) -> None:
      handle = _PanelResizeHandle(PanelResizeSpec(260, 420, 320, "ui/algebra_panel_width", "right"), settings=qsettings)
      assert handle.set_width(99) == 260
      assert handle.set_width(999) == 420
      assert qsettings.value("ui/algebra_panel_width", type=int) == 420
      assert handle.restore_width() == 320


  def test_right_panel_drag_uses_inverse_delta(qsettings, qtbot) -> None:
      handle = _PanelResizeHandle(PanelResizeSpec(360, 560, 440, "ui/agent_panel_width", "left"), settings=qsettings)
      assert handle.width_for_delta(start_width=440, delta_x=-50) == 490
  ```

- [x] **Step 2: Run focused tests and confirm missing handle failures**

  Run: `uv run pytest tests/test_panel_resize_handle.py tests/test_main_window_layout.py -q`

  Expected: FAIL because no parameterized resize handle exists.

- [x] **Step 3: Implement reusable handle behavior**

  Render a fixed 5px `QWidget` with horizontal-resize cursor. On press, capture global x and current width; on move, derive delta from `edge` (`right` adds x delta; `left` subtracts it), clamp, apply, and persist on release. On double click, call `restore_width`. Read setting via robust `int` conversion and use default if missing/invalid. Keep the widget passive beyond drag/double-click.

- [x] **Step 4: Install left/right handles without a splitter**

  Insert the left handle after `AlgebraPanel` and before `viewportHost`; insert the right handle before `AgentSidebar`. Bind each `width_changed` to the relevant `setFixedWidth`. Set AlgebraPanel min/max to 260/420 and initial width from settings/default. Set AgentSidebar width through named constants and hide/show its handle in lockstep with the panel; never leave a placeholder strip when hidden.

- [x] **Step 5: Run resize/layout regressions and commit**

  Run: `uv run pytest tests/test_panel_resize_handle.py tests/test_main_window_layout.py tests/test_agent_sidebar_web_integration.py tests/test_sidebar_visibility.py tests/test_algebra_panel.py -q`

  Expected: PASS. Commit with `git add ui/panel_resize_handle.py ui/designer_window.py ui/algebra_panel.py ui/agent_sidebar.py ui/styles/base.qss.in tests && git commit -m "feat: add persisted resizable side panels"`.

<!-- openspec-task: 4.3 -->
### Task 3: Remove the retired Agent sidebar chrome and normalize width constants

**Files:**
- Modify: `ui/agent_sidebar.py`
- Modify: `ui/designer_window.py`
- Modify: `tests/test_agent_sidebar_web_integration.py`
- Modify: `tests/test_sidebar_visibility.py`
- Modify: `tests/test_agent_panel_migration.py`

**Interfaces:**
- Produces: `AgentSidebar` with one WebView child, `expand()`, `collapse()`, `toggle()`, `set_panel_width(width: int)`, and width constants only.
- Removes: `AgentCollapsedBar`, its comments/instances/status paths, and all 440 literals outside the one default constant.

- [x] **Step 1: Write failing migration and constant tests**

  Update sidebar tests to assert no `collapsed_bar` attribute/class, no `AgentCollapsedBar` source token, hidden sidebar has no layout slot, and `AgentSidebar.DEFAULT_WIDTH == 440` with min/max 360/560. Assert `set_panel_width(999)` clamps to 560 and collapse does not reset the saved width.

- [x] **Step 2: Run the focused tests and capture legacy compatibility failures**

  Run: `uv run pytest tests/test_agent_sidebar_web_integration.py tests/test_sidebar_visibility.py tests/test_agent_panel_migration.py -q`

  Expected: FAIL because current sidebar retains hidden collapsed-bar compatibility code and duplicated fixed-width calls.

- [x] **Step 3: Delete dead collapsed-bar state and comments**

  Remove `AgentCollapsedBar`, related imports, state indicator methods, constructor allocation, connections, and stale comments. Keep `AgentSidebarState` only if tests/current callers require it; update its docstring to describe whole-panel visibility rather than an unused 40px strip.

- [x] **Step 4: Centralize width behavior**

  Define `MIN_WIDTH`, `DEFAULT_WIDTH`, and `MAX_WIDTH` on `AgentSidebar`; implement `set_panel_width` with clamp plus `setFixedWidth`. Replace every literal `setFixedWidth(440)` and DesignerWindow direct width call with that API. Ensure width set by a handle survives hide/show and starts from the persisted setting supplied by MainWindow.

- [x] **Step 5: Run sidebar suite and commit**

  Run: `uv run pytest tests/test_agent_sidebar_web_integration.py tests/test_sidebar_visibility.py tests/test_agent_panel_migration.py tests/test_main_window_layout.py -q`

  Expected: PASS. Commit with `git add ui/agent_sidebar.py ui/designer_window.py tests && git commit -m "refactor: remove retired Agent sidebar chrome"`.

<!-- openspec-task: 4.4 -->
### Task 4: Remove the legacy Designer sidebar and unused window module

**Files:**
- Modify: `ui/main_window.ui`
- Delete: `ui/main_window.py`
- Modify: `tests/test_main_window_layout.py`
- Modify: `tests/test_documentation.py`
- Modify: any direct imports identified by search

**Interfaces:**
- Produces: `main_window.ui` with only central widget, `rootLayout`, and `viewportHost`; runtime code inserts AlgebraPanel, handles, AgentSidebar, and status bar.
- Produces window title exactly `Math3D Teaching`.

- [x] **Step 1: Write failing UI-file and title contract tests**

  Update `tests/test_main_window_layout.py` to load the `.ui` document and assert `rootLayout` has only `viewportHost` before runtime installation, `sidebar` and its nested legacy widget names do not exist, and `windowTitle()` equals `Math3D Teaching`. Add a source test that `ui/main_window.py` is absent and no import references it.

- [x] **Step 2: Run focused tests and verify current legacy content fails**

  Run: `uv run pytest tests/test_main_window_layout.py tests/test_documentation.py -q`

  Expected: FAIL because the UI has the stale 294px sidebar, title whitespace, and old Python module still exists.

- [x] **Step 3: Reduce the Designer file to its live scaffold**

  Edit `main_window.ui` to change the title and remove the entire `sidebar` `<item>` plus all nested obsolete controls. Preserve `centralwidget`, its zero-margin/zero-spacing horizontal `rootLayout`, and the native `viewportHost` object name required by `MainWindow._configure_viewport`.

- [x] **Step 4: Delete unused module only after reference audit**

  Run: `rg -n "ui\.main_window|from ui import main_window|main_window import" . --glob "!*.pyc"`.

  Expected: only the intended file/known documentation matches. Update those references, then delete the explicit file `ui/main_window.py` using a repository patch. Do not delete any other file.

- [x] **Step 5: Run layout/documentation tests and commit**

  Run: `uv run pytest tests/test_main_window_layout.py tests/test_documentation.py tests/test_agent_panel_migration.py -q`

  Expected: PASS. Commit with `git add ui/main_window.ui tests && git rm ui/main_window.py && git commit -m "refactor: remove legacy main window scaffold"`.

<!-- openspec-task: 5.1 -->
### Task 5: Add focused Python coverage for the complete design contract

**Files:**
- Create: `tests/test_theme_mode.py` (extend from Plan 1)
- Create: `tests/test_ui_tokens.py` (extend from Plan 1)
- Create: `tests/test_panel_resize_handle.py` (extend from Task 2)
- Create: `tests/test_agent_web_theme_protocol.py` (extend from Plan 2)
- Create: `tests/test_agent_sidebar_theme_bootstrap.py` (extend from Plan 2)
- Modify: `tests/test_scene_mode.py`
- Modify: `tests/test_scene_settings.py`
- Modify: `tests/test_main_window_layout.py`

**Interfaces:**
- Consumes all completed public helpers: `normalize_theme_mode`, `effective_theme`, `build_qss`, `_PanelResizeHandle`, `SceneAppearance`, and `AgentSidebarWeb.set_theme`.
- Produces one focused Python matrix covering theme persistence, theme events, both resizers, auto backgrounds, QSS/tokens, first-paint injection, and no sensitive payloads.

- [ ] **Step 1: Add missing contract cases before the broad suite**

  Add tests for QSettings round-tripping `light`/`dark`/`system`; system scheme changes only affecting system mode; `theme_state` exact mode whitelist and no `api_key`/`token` JSON keys; algebra 260/320/420 and Agent 360/440/560 clamps/resets/persistence/direction; old explicit scene backgrounds; generated QSS snapshots and retired-selector absence.

- [ ] **Step 2: Run the focused Python matrix and identify integration gaps**

  Run:

  ```powershell
  uv run pytest tests/test_theme_mode.py tests/test_ui_tokens.py tests/test_panel_resize_handle.py tests/test_scene_mode.py tests/test_scene_settings.py tests/test_agent_web_theme_protocol.py tests/test_agent_sidebar_theme_bootstrap.py tests/test_main_window_layout.py -q
  ```

  Expected: FAIL only for deliberately unimplemented assertions; fix implementation rather than weakening contracts.

- [ ] **Step 3: Make test seams deterministic**

  Inject temporary `QSettings` objects/paths, avoid waiting for real WebEngine paint, use direct `loadFinished` handler invocation or a thin fake only where Qt behavior is otherwise asynchronous, and restore modified application settings in fixture teardown.

- [ ] **Step 4: Re-run the focused Python matrix**

  Run the command from Step 2.

  Expected: PASS with no external network, provider credentials, or real display requirement.

- [ ] **Step 5: Commit focused Python coverage**

  Run: `git add tests && git commit -m "test: cover UI design refresh contracts"`.

<!-- openspec-task: 5.2 -->
### Task 6: Add React coverage for themes and sidebar width layouts

**Files:**
- Modify: `ui/agent_web/src/state/reducer.test.ts`
- Create: `ui/agent_web/src/state/theme.test.ts`
- Create: `ui/agent_web/src/styles/theme.test.ts`
- Create: `ui/agent_web/scripts/no-literal-colors.test.mjs`
- Modify: `ui/agent_web/src/App.test.tsx`
- Modify: `ui/agent_web/src/styles/layout.css`

**Interfaces:**
- Consumes `theme_state` reducer behavior and generated token CSS from Plan 2.
- Produces test coverage for valid/invalid theme events, no system-color dependency, complete two-theme variables, and 360/440/560px layout constraints.

- [ ] **Step 1: Write layout and theme behavior tests**

  Add test cases that dispatch valid/invalid `theme_state` events and assert `documentElement.dataset.theme`; scan CSS for no `prefers-color-scheme`; compare generated variable name sets between branches; render/measure fixtures at 360/440/560px and assert session tabs, header actions, composer controls, and model popovers do not overflow while timeline content uses a bounded centered column.

- [ ] **Step 2: Run frontend tests and confirm any remaining failures**

  Run from `ui/agent_web`: `pnpm test -- src/state/theme.test.ts src/styles/theme.test.ts src/App.test.tsx && node --test scripts/no-literal-colors.test.mjs`

  Expected: FAIL until all Plan 2 Web theme work and responsive CSS are complete.

- [ ] **Step 3: Make width assertions stable in jsdom**

  Use explicit style widths and DOM geometry stubs instead of browser layout heuristics. Assert CSS contracts (`min-width: 0`, overflow behavior, `max-width` timeline rule) alongside component behavior so the 360/440/560 regression is meaningful in jsdom.

- [ ] **Step 4: Run complete Web test/build pipeline**

  Run: `pnpm test && pnpm build`

  Expected: PASS; regenerated output stays local and includes current `theme.css` in the bundle.

- [ ] **Step 5: Commit React verification**

  Run: `git add ui/agent_web && git commit -m "test: verify Agent themes and resize layouts"`.

<!-- openspec-task: 5.3 -->
### Task 7: Add WebView and rendering integration coverage

**Files:**
- Modify: `tests/test_agent_sidebar_web_integration.py`
- Modify: `tests/test_agent_bridge.py`
- Modify: `tests/test_agent_web_protocol.py`
- Modify: `tests/test_2d_geometry_toolbar.py`
- Modify: `tests/test_scene_camera_modes.py`
- Create: `tests/test_ui_design_integration.py`

**Interfaces:**
- Consumes the installed `theme-bootstrap` script, `AgentSidebarWeb.set_theme`, bridge event rules, and scene background propagation.
- Produces integration tests that observe `document.documentElement.dataset.theme` through `runJavaScript` where WebEngine is available and preserve fallback host/unit coverage in offscreen CI.

- [ ] **Step 1: Add end-to-end host assertions**

  Add a test that creates `AgentSidebarWeb`, validates `_initial_url("dark")`, records bridge emissions after `set_theme("dark")`, and, when the Qt event loop reports a loaded page, calls:

  ```python
  host.page.runJavaScript("document.documentElement.dataset.theme", callback)
  ```

  Assert callback receives `"dark"`. Skip only the JavaScript assertion with a reason if WebEngine load cannot complete under the headless renderer; URL/script and event tests must still run.

- [ ] **Step 2: Add 2D/3D non-regression coverage**

  Test that light/dark effective modes choose expected auto backgrounds and grid/axis contrast, explicit legacy backgrounds override the mode, and current 2D toolbar, camera, geometry interaction, layer, and bridge protocol tests remain unchanged in behavior.

- [ ] **Step 3: Run integration subsets and fix actual regressions**

  Run:

  ```powershell
  uv run pytest tests/test_ui_design_integration.py tests/test_agent_sidebar_web_integration.py tests/test_agent_bridge.py tests/test_agent_web_protocol.py tests/test_2d_geometry_toolbar.py tests/test_2d_geometry_interaction.py tests/test_scene_camera_modes.py tests/test_curve_scene.py tests/test_layer_scene.py -q
  ```

  Expected: PASS, allowing the explicit documented WebEngine JS assertion skip only when platform initialization prevents it.

- [ ] **Step 4: Commit integration coverage**

  Run: `git add tests && git commit -m "test: cover UI theme integration and rendering regressions"`.

<!-- openspec-task: 5.4 -->
### Task 8: Run release-level validation and inspect the packaged result

**Files:**
- Modify only if a test/build/strict validation reveals a directly related defect; otherwise no source changes.
- Verify: `ui/agent_web/dist/**`, OpenSpec artifacts, Python/TypeScript test reports.

**Interfaces:**
- Consumes all completed implementation and test suites.
- Produces a verified UI refresh change that is strict-OpenSpec valid and has current local Web assets.

- [ ] **Step 1: Run focused Python and Web suites**

  Run:

  ```powershell
  uv run pytest tests/test_ui_tokens.py tests/test_theme_mode.py tests/test_ui_icons.py tests/test_ui_visual_contract.py tests/test_app_status_bar.py tests/test_panel_resize_handle.py tests/test_scene_mode.py tests/test_scene_settings.py tests/test_agent_web_theme_protocol.py tests/test_agent_sidebar_theme_bootstrap.py tests/test_ui_design_integration.py -q
  Set-Location ui/agent_web; pnpm test; pnpm build
  ```

  Expected: every test passes; only explicitly guarded headless WebEngine JS checks may skip.

- [ ] **Step 2: Run the full Python suite**

  Run from the repository root: `uv run pytest -q`

  Expected: PASS. Investigate any failure using the existing focused test first; do not mask baseline regressions with skips or loosened assertions.

- [ ] **Step 3: Typecheck/build and validate generated assets**

  Run from `ui/agent_web`: `pnpm exec tsc --noEmit && pnpm build`.

  Then run from the root: `uv run pytest tests/test_agent_web_assets.py tests/test_agent_web_packaging.py tests/test_agent_web_offline.py -q`.

  Expected: PASS; every manifest asset resolves below `ui/agent_web/dist` and no network asset is introduced.

- [ ] **Step 4: Run strict OpenSpec validation**

  Run: `openspec validate ui-design-refresh --strict`

  Expected: exit code 0. Do not modify proposal/design/spec/task artifacts merely to suppress a validation error; correct implementation/tests or report a genuine specification conflict.

- [ ] **Step 5: Review final diff and commit verified implementation**

  Run: `git diff --check`, `git status --short`, and `git diff -- docs/superpowers/plans/2026-08-28-ui-design-refresh-tasks-1-1-2-4.md docs/superpowers/plans/2026-08-28-ui-design-refresh-tasks-2-5-3-5.md docs/superpowers/plans/2026-08-28-ui-design-refresh-tasks-4-1-5-4.md`.

  Expected: no whitespace errors; no unrelated user changes staged or reverted. Commit implementation only with `git add <reviewed implementation paths> && git commit -m "feat: refresh Math3D Teaching UI design"`.
