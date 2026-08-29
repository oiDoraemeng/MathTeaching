# UI Design Refresh: Scene Semantics and Web Theme Synchronization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the Qt visual migration, make scene backgrounds follow the effective theme when requested, and synchronize the local React Agent sidebar through a no-flash initial URL and a minimal runtime theme event.

**Architecture:** Qt owns the effective theme and scene appearance state. The WebView gets the initial mode in `mathagent://app/index.html?theme=...` and applies it in a `DocumentCreation` script; later changes cross the existing validated JSON bridge as `{ type: "theme_state", payload: { mode } }`. React changes only its document root and semantic CSS variables.

**Tech Stack:** Python 3.11, PySide6 QtWebEngine/QtSvg, PyVista, React 18, TypeScript, Vite, Vitest, pytest.

**Spec:** `openspec/changes/ui-design-refresh/design.md`, `openspec/changes/ui-design-refresh/specs/ui-design-system/spec.md`, and `openspec/changes/ui-design-refresh/specs/mathagent-sidebar/spec.md`

## Global Constraints

- `light`, `dark`, and `system` are the only UI preference values; bridge `theme_state` payloads contain only an effective `mode` of `light` or `dark`.
- Web CSS must not use `prefers-color-scheme` or a default dark `color-scheme`; missing token data falls back to light.
- `SceneAppearance.background="auto"` is the new default; stored `light`/`dark` values remain explicit overrides for backward compatibility.
- All Web surfaces use generated semantic variables; no literal hex/rgb/rgba colors remain in sidebar stylesheets or components.
- Preserve conversation state and scroll position during runtime theme changes; never reload the WebView for a theme change.
- Keep scene rendering and bridge validation behavior deterministic and testable without network access or credentials.

---

<!-- openspec-task: 2.5 -->
### Task 1: Add theme-following scene appearance semantics

**Files:**
- Modify: `models/scene_mode.py`
- Modify: `ui/scene_settings.py`
- Modify: `rendering/scene.py`
- Modify: `rendering/two_d_scene.py`
- Modify: `ui/designer_window.py`
- Modify: `tests/test_scene_mode.py`
- Modify: `tests/test_scene_settings.py`
- Create: `tests/test_scene_theme_background.py`

**Interfaces:**
- Produces: `SceneAppearance.background` values `"auto" | "light" | "dark"`, `background_color(effective_theme: str = "light") -> str`, and `contrast_axis_color(effective_theme: str = "light") -> str`.
- `MainWindow._render_scene()` and `_refresh_2d_viewport()` pass the effective theme when resolving auto colors.

- [x] **Step 1: Write failing auto-background tests**

  Add tests asserting a new `SceneAppearance()` has `background == "auto"`, explicit `light`/`dark` colors stay unchanged, and auto resolves to token scene colors:

  ```python
  def test_auto_background_uses_effective_theme() -> None:
      appearance = SceneAppearance()
      assert appearance.background == "auto"
      assert appearance.background_color("light") == "#f4f6f9"
      assert appearance.background_color("dark") == "#1e1f23"


  def test_legacy_background_values_remain_explicit() -> None:
      assert SceneAppearance(background="light").background_color("dark") == "#f7f8fb"
      assert SceneAppearance(background="dark").background_color("light") == "#101317"
  ```

  Update scene-settings tests to assert the first combo item is `跟随主题` with data `auto` and that `set_values(background="auto", ...)` selects it without emitting a change signal.

- [x] **Step 2: Run focused tests and verify current binary semantics fail**

  Run: `uv run pytest tests/test_scene_mode.py tests/test_scene_settings.py tests/test_scene_theme_background.py -q`

  Expected: FAIL because the model only accepts light/dark and the combo has no auto item.

- [x] **Step 3: Implement model and settings compatibility**

  Add `auto` as the default dataclass value. Keep explicit colors exactly as current values, and use `load_tokens()` for auto scene/axis colors. Normalize unknown persisted values to `auto` at the model boundary. Add the combo item before the existing light/dark entries and keep current signal-blocking behavior in `set_values`.

- [x] **Step 4: Route effective theme colors into both renderers**

  In `rendering/scene.py`, replace the default background literal with `SceneAppearance.background_color(effective_theme)` when an appearance is supplied. In `rendering/two_d_scene.py`, choose grid color from the appearance’s effective theme: auto uses the matching light/dark grid token, explicit dark/light retains the current grid colors. In `MainWindow`, pass `self.effective_theme` to render/refresh calls and trigger a rerender for auto appearances inside `set_theme`.

- [x] **Step 5: Run rendering regressions and commit**

  Run: `uv run pytest tests/test_scene_mode.py tests/test_scene_settings.py tests/test_scene_theme_background.py tests/test_viewport_guides.py tests/test_curve_scene.py tests/test_layer_scene.py -q`

  Expected: PASS. Commit with `git add models/scene_mode.py ui/scene_settings.py rendering/scene.py rendering/two_d_scene.py ui/designer_window.py tests && git commit -m "feat: allow scene backgrounds to follow theme"`.

<!-- openspec-task: 2.6 -->
### Task 2: Bring lighting and dialog surfaces into the token system

**Files:**
- Modify: `ui/lighting_dialog.py`
- Modify: `ui/agent_settings.py`
- Modify: `ui/styles/base.qss.in`
- Create: `tests/test_dialog_theming.py`

**Interfaces:**
- Consumes: `build_qss`, radius/shadow tokens, and the shared color-button contract from Plan 1.
- Produces: dialogs whose `QGroupBox`, form controls, buttons, and modal surfaces are styled by object/Qt selectors rather than per-widget static QSS.

- [x] **Step 1: Write failing dialog-style tests**

  Instantiate `LightingDialog` and the existing settings dialogs in an offscreen `QApplication`, assert `QDialog`/`QGroupBox` rules contain token substitutions, and assert color swatches retain only their dynamic background while their foreground is a semantic dark/light value. A source assertion must reject hardcoded `font-size: 22pt` and `Segoe UI` in dialog/widget modules.

- [x] **Step 2: Run focused tests and capture current local styles**

  Run: `uv run pytest tests/test_dialog_theming.py tests/test_ui_typography.py -q`

  Expected: FAIL on missing dialog selectors and the current per-color-button stylesheet.

- [x] **Step 3: Add QDialog/QGroupBox token rules**

  Add `QDialog` modal radius/shadow-compatible surface rules, `QGroupBox` border/text rules, and dialog button/form metrics to `base.qss.in`. Keep the modal drop-shadow effect installed by the overlay helper; QSS remains responsible for colors, spacing, and focus states.

- [x] **Step 4: Remove static local presentation overrides**

  Update `LightingDialog._set_color_button` to set a dynamic palette/stylesheet only for the swatch fill and a semantic foreground selected from the current theme. Remove hardcoded font family/point sizes in `agent_settings.py` and any dialog-local border/color declarations duplicated by the global template.

- [x] **Step 5: Run dialog and UI tests, then commit**

  Run: `uv run pytest tests/test_dialog_theming.py tests/test_ui_typography.py tests/test_scene_settings.py -q`

  Expected: PASS. Commit with `git add ui/lighting_dialog.py ui/agent_settings.py ui/styles/base.qss.in tests && git commit -m "style: theme Qt dialogs from shared tokens"`.

<!-- openspec-task: 2.7 -->
### Task 3: Finish Qt visual hierarchy, metrics, focus, and motion

**Files:**
- Modify: `ui/styles/base.qss.in`
- Modify: `ui/designer_window.py`
- Modify: `ui/algebra_panel.py`
- Modify: `ui/two_d_tools.py`
- Modify: `ui/scene_settings.py`
- Modify: `ui/agent_sidebar.py`
- Modify: `widgets/LightRotationWidget.py`
- Modify: `tests/test_ui_visual_contract.py`

**Interfaces:**
- Consumes: tokenized overlays, icons, typography, scene semantics, and dialog styling from Plan 1 and Tasks 2.5-2.6.
- Produces: no region divider borders, card-style LayerRow states, 36/32/28 control sizes, keyboard focus rings, 120/150/200ms motion values, and reduced-motion Web CSS.

- [x] **Step 1: Add failing visual contract checks**

  Create source/style checks for `border-right` removal, absence of 38/40/30 control dimensions, presence of the 4px LayerRow leading strip and selected/hover states, `:focus-visible` 2px accent rings, 150ms overlay and 200ms panel animations, and a `@media (prefers-reduced-motion: reduce)` block in Web styles.

- [x] **Step 2: Run the contract checks and enumerate current violations**

  Run: `uv run pytest tests/test_ui_visual_contract.py -q`

  Expected: FAIL with current ad-hoc sizes, region borders, and missing focus/motion rules.

- [x] **Step 3: Implement tonal separation and LayerRow cards**

  Style the algebra panel, viewport, and Agent sidebar using background tokens without inter-region divider borders. Give each live layer row an elevated background, 8px radius, 4px left strip from the layer color, no default border, token border on hover, and accent border/soft background when selected. Replace its settings control with a 28px `ellipsis` icon and its visibility text with `eye`/`eye-off` icons.

- [x] **Step 4: Normalize dimensions and interaction states**

  Replace every toolbar 38px value with 36px, form 38/40px values with 32px, and row 30px values with 28px. Add `:focus-visible` rules that draw a 2px accent ring and keep pointer focus quiet. Set QPropertyAnimation durations to 150ms for overlays and 200ms OutCubic for panel transitions. Add equivalent CSS transitions and reduced-motion disabling in `src/styles/layout.css`.

- [x] **Step 5: Run visual and neighboring tests, then commit**

  Run: `uv run pytest tests/test_ui_visual_contract.py tests/test_ui_tokens.py tests/test_2d_geometry_toolbar.py tests/test_algebra_panel.py tests/test_scene_settings.py -q`

  Expected: PASS. Commit with `git add ui widgets tests && git commit -m "style: finish Qt visual hierarchy and motion"`.

<!-- openspec-task: 3.1 -->
### Task 4: Make generated Web themes explicit and host-controlled

**Files:**
- Modify: `ui/agent_web/src/styles/theme.css`
- Modify: `ui/agent_web/src/styles/layout.css`
- Modify: `ui/agent_web/src/styles.css`
- Modify: `ui/agent_web/src/components/*.tsx`
- Modify: `ui/agent_web/src/state/reducer.ts`
- Modify: `ui/agent_web/src/types.ts`
- Modify: `ui/agent_web/src/styles/theme.css` (generated output via `pnpm theme:generate`)
- Create: `ui/agent_web/src/styles/theme.test.ts`

**Interfaces:**
- Consumes: generated CSS from Plan 1 Task 3.
- Produces: explicit `:root, [data-theme="light"]` and `[data-theme="dark"]` branches, light fallback, and no `prefers-color-scheme` dependency.

- [x] **Step 1: Write failing CSS contract tests**

  Add a Vitest test that reads `theme.css`, asserts both data-theme selectors and both color-scheme values, rejects `prefers-color-scheme` and `color-scheme: dark` outside the dark branch, and checks that all existing `--agent-*` variables are present in both branches.

- [x] **Step 2: Run the frontend CSS test and confirm current failures**

  Run from `ui/agent_web`: `pnpm test -- src/styles/theme.test.ts`

  Expected: FAIL because the current stylesheet uses a dark root and a media-query light branch.

- [x] **Step 3: Regenerate and import semantic branches**

  Run `pnpm theme:generate` so `theme.css` is generated from `design/tokens.json`. Update imports to use the generated file once, and replace component/layout literals with semantic variables such as `--agent-on-accent`, `--agent-overlay`, `--agent-shadow-overlay`, and `--agent-shadow-modal`.

- [x] **Step 4: Add root transition and reduced motion**

  Add a `.agent-app`/root color transition of `.15s`, and disable all transitions/animations under `@media (prefers-reduced-motion: reduce)`. Keep this media query only for motion, never for color selection.

- [x] **Step 5: Run CSS/component tests and commit**

  Run: `pnpm test -- src/styles/theme.test.ts src/state/reducer.test.ts && pnpm build`

  Expected: PASS. Commit with `git add ui/agent_web/src && git commit -m "style: make Web themes explicit and semantic"`.

<!-- openspec-task: 3.2 -->
### Task 5: Inject the initial Web theme before first paint

**Files:**
- Modify: `ui/agent_sidebar_web.py`
- Create: `tests/test_agent_sidebar_theme_bootstrap.py`

**Interfaces:**
- Produces: `AgentSidebarWeb._initial_url(theme: str | None = None) -> QUrl` and a `QWebEngineScript` named `theme-bootstrap` injected at `DocumentCreation`.
- The URL must preserve `mathagent://app/index.html` and append only a validated `theme=light|dark` query parameter.

- [x] **Step 1: Write failing URL and script tests**

  Test `_initial_url("dark").query()` equals `theme=dark`, invalid values resolve to `theme=light`, and the page scripts include one `DocumentCreation` script whose source reads `new URLSearchParams(location.search).get("theme")` and sets `document.documentElement.dataset.theme` before application code.

- [x] **Step 2: Run focused tests and confirm current host behavior**

  Run: `uv run pytest tests/test_agent_sidebar_theme_bootstrap.py -q`

  Expected: FAIL because the host currently loads a bare URL and registers no user script.

- [x] **Step 3: Implement validated initial URL construction**

  Add a small mode validator shared with `set_theme`, build the URL with `QUrlQuery`, and call it before `view.setUrl`. Do not include preferences, credentials, or full token data in the URL.

- [x] **Step 4: Register the document-creation bootstrap script**

  Create a `QWebEngineScript`, set its name, injection point `DocumentCreation`, world `MainWorld`, and source:

  ```javascript
  (() => {
    const mode = new URLSearchParams(location.search).get("theme");
    if (mode === "light" || mode === "dark") document.documentElement.dataset.theme = mode;
  })();
  ```

  Add it to `page.scripts()` before loading the URL, and reapply the URL when the host’s effective theme changes while the document is not yet loaded.

- [x] **Step 5: Run WebView bootstrap tests and commit**

  Run: `uv run pytest tests/test_agent_sidebar_theme_bootstrap.py tests/test_agent_sidebar_web_integration.py -q`

  Expected: PASS. Commit with `git add ui/agent_sidebar_web.py tests/test_agent_sidebar_theme_bootstrap.py && git commit -m "feat: bootstrap Agent theme before WebView paint"`.

<!-- openspec-task: 3.3 -->
### Task 6: Add validated runtime `theme_state` bridge events

**Files:**
- Modify: `agent/web_protocol.py`
- Modify: `ui/agent_sidebar_web.py`
- Modify: `ui/agent_bridge.py`
- Create: `tests/test_agent_web_theme_protocol.py`

**Interfaces:**
- Produces: `EVENT_MESSAGE_TYPES` containing `theme_state`; `_validate_event_payload("theme_state", payload)` accepting exactly a string mode in `{light, dark}`; `AgentSidebarWeb.set_theme(mode: str, *, loaded: bool | None = None) -> None`.

- [ ] **Step 1: Write failing protocol and delivery tests**

  Assert valid `theme_state` serializes with only `payload.mode`, unknown modes and extra payload keys are rejected, and `set_theme` queues the latest event before load then emits one event after load. Assert API keys or token maps never appear in the JSON string.

- [ ] **Step 2: Run focused protocol tests and verify rejection/missing-event failures**

  Run: `uv run pytest tests/test_agent_web_theme_protocol.py tests/test_agent_web_protocol.py -q`

  Expected: FAIL because the event type is not whitelisted and the WebView host has no theme queue.

- [ ] **Step 3: Extend the protocol allowlist and payload validator**

  Add `theme_state` to `EVENT_MESSAGE_TYPES` and validate exact keys and a two-value mode. Keep all existing event validators unchanged. Ensure `serialize_bridge_event` emits the event with `session_id=""`, no turn id, and no other payload fields.

- [ ] **Step 4: Implement load-aware delivery in `AgentSidebarWeb`**

  Track `_page_loaded` and `_pending_theme`. `set_theme` validates the mode, updates the initial URL if not loaded, and otherwise calls `bridge.emit_event` immediately. On a successful `loadFinished`, emit the latest pending theme before requesting the initial snapshot; on failure retain the pending mode for the next successful load.

- [ ] **Step 5: Run bridge tests and commit**

  Run: `uv run pytest tests/test_agent_web_theme_protocol.py tests/test_agent_web_protocol.py tests/test_agent_bridge.py -q`

  Expected: PASS. Commit with `git add agent/web_protocol.py ui/agent_sidebar_web.py ui/agent_bridge.py tests && git commit -m "feat: add host theme state bridge event"`.

<!-- openspec-task: 3.4 -->
### Task 7: Apply `theme_state` in the React reducer and document root

**Files:**
- Modify: `ui/agent_web/src/types.ts`
- Modify: `ui/agent_web/src/state/reducer.ts`
- Modify: `ui/agent_web/src/bridge/qtBridge.ts`
- Modify: `ui/agent_web/src/App.tsx`
- Create: `ui/agent_web/src/state/theme.test.ts`

**Interfaces:**
- Produces: `TimelineEventType`/bridge handling for `theme_state`; an event path that ignores malformed modes and calls `document.documentElement.dataset.theme = mode` for valid modes.
- The reducer state may expose `theme: "light" | "dark"` for rendering but must not store arbitrary token payloads.

- [ ] **Step 1: Write failing reducer and DOM tests**

  Test a valid event changes `data-theme` to dark, a second valid event changes it back to light without remounting conversation state, malformed/unknown values leave the current attribute unchanged, and an initial absent attribute is set to light only when the host supplies light.

- [ ] **Step 2: Run focused Vitest tests and verify missing action behavior**

  Run from `ui/agent_web`: `pnpm test -- src/state/theme.test.ts`

  Expected: FAIL because `theme_state` is currently treated as an unrelated event and no document-root update occurs.

- [ ] **Step 3: Add the event type and reducer case**

  Add `theme_state` to `TimelineEventType` and handle it before session timeline projection. Accept only `payload.mode === "light" || payload.mode === "dark"`; update the root attribute and return state with that theme. Ignore all other shapes without changing state or DOM.

- [ ] **Step 4: Keep UserScript and reducer idempotent**

  Ensure the QWebEngine script and reducer both assign the same attribute, and have `qtBridge.ts` dispatch incoming events exactly once. Add a `.15s` root color transition in the theme/layout CSS without resetting scroll or composer state.

- [ ] **Step 5: Run frontend tests/build and commit**

  Run: `pnpm test -- src/state/theme.test.ts src/state/reducer.test.ts src/App.test.tsx && pnpm build`

  Expected: PASS. Commit with `git add ui/agent_web/src && git commit -m "feat: apply runtime theme events in React"`.

<!-- openspec-task: 3.5 -->
### Task 8: Eliminate literal Web colors and add the lint contract

**Files:**
- Modify: `ui/agent_web/src/styles/layout.css`
- Modify: `ui/agent_web/src/styles.css`
- Modify: `ui/agent_web/src/components/*.tsx`
- Modify: `ui/agent_web/src/styles/theme.css`
- Create: `ui/agent_web/scripts/no-literal-colors.test.mjs`

**Interfaces:**
- Consumes: semantic variable names from Tasks 3.1 and 3.4.
- Produces: a lint test that fails on literal `#...`, `rgb(...)`, or `rgba(...)` in sidebar source styles/components, while allowing token-generator source and test fixtures.

- [ ] **Step 1: Write the failing literal-color lint**

  Implement a Node test that recursively reads `src/styles` and `src/components`, strips comments, and rejects `/#[0-9a-f]{3,8}\b|rgba?\s*\(/i`. Assert it skips `theme.css` generated declarations only when checking component/style sources, then separately validates theme branches have complete variables.

- [ ] **Step 2: Run the lint and list current literals**

  Run from `ui/agent_web`: `node --test scripts/no-literal-colors.test.mjs`

  Expected: FAIL with the current `#fff` and `rgb(0 0 0 / 30%)` locations.

- [ ] **Step 3: Replace literals with semantic variables**

  Replace white-on-accent text with `var(--agent-on-accent)`, shadows with `var(--agent-shadow-overlay)`/`var(--agent-shadow-modal)`, and status/surface colors with generated `--agent-*` variables. Do not encode a color in a component prop; expose semantic class names instead.

- [ ] **Step 4: Run lint, tests, and build**

  Run: `node --test scripts/no-literal-colors.test.mjs && pnpm test && pnpm build`

  Expected: PASS, with no system-theme branch and no literal colors outside generated token CSS.

- [ ] **Step 5: Commit the Web theme cleanup**

  Run: `git add ui/agent_web/src ui/agent_web/scripts && git commit -m "refactor: remove literal Agent Web colors"`.
