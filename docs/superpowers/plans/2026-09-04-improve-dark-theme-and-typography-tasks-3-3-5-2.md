# Dark Theme and Typography Improvements — WebView, Timeline, and Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete MathInput theming and long-formula access, tighten Agent timeline density with pinned scrolling, and make both panel dividers visible while expanding the Agent width range to 720px.

**Architecture:** A reusable `ThemeBridge` owns DocumentCreation injection, pending theme state, and runtime dataset changes for all MathInput WebViews. The Agent timeline keeps scroll pinning as local DOM state rather than protocol state. Divider appearance remains QSS-driven while `PanelResizeSpec` remains the single persistence/clamping mechanism and `AgentSidebar` enforces the public width contract.

**Tech Stack:** Python 3.11, PySide6 6.8, Qt WebEngine/QWebEngineScript, HTML/CSS, React 18, TypeScript, Vitest/Testing Library, pnpm/Vite, pytest.

**Spec:** `openspec/changes/improve-dark-theme-and-typography/design.md`, `openspec/changes/improve-dark-theme-and-typography/tasks.md`, `openspec/changes/improve-dark-theme-and-typography/specs/ui-design-system/spec.md`, `openspec/changes/improve-dark-theme-and-typography/specs/mathagent-sidebar/spec.md`, and `openspec/changes/improve-dark-theme-and-typography/specs/app-shell/spec.md`

## Global Constraints

- Do not reload a MathInput document to change theme; loaded pages receive only a dataset update.
- Inject the complete variable stylesheet at `QWebEngineScript.InjectionPoint.DocumentCreation` so a newly opened WebView has the correct first paint.
- Preserve direct-open light fallbacks in every MathInput HTML file and do not change MathLive/QWebChannel public bridge names.
- Agent reading width remains centered at a maximum of 620px; the 720px panel limit must not stretch cards to full width.
- The auto-scroll threshold is strictly less than 40px from the bottom and must not pull a reader down after they scroll upward.
- Algebra width remains 260–420px with a 320px default; Agent width becomes exactly 360–720px with a 440px default.
- Keep commits task-scoped and stage only the files listed by the current task.

---

<!-- openspec-task: 3.3 -->
### Task 1: Theme the remaining MathInput documents and fallback label

**Files:**
- Modify: `MathInputWidget/mathlive.html`
- Modify: `MathInputWidget/inline_formula_overlay.html`
- Modify: `MathInputWidget/formula_preview.html`
- Modify: `MathInputWidget/formula_preview.py`
- Modify: `ui/styles/base.qss.in`
- Modify: `tests/test_math_input_theme.py`
- Modify: `tests/test_ui_tokens.py`
- Modify: `tests/snapshots/base-light.qss`
- Modify: `tests/snapshots/base-dark.qss`

**Interfaces:**
- Consumes: the complete `--mi-*` variable set from `MathInputWidget.theme_tokens`.
- Preserves: `window.mathInput`, `window.inlineFormulaEditor`, `window.formulaPreview`, and all current QWebChannel callbacks.
- Produces: a QSS-controlled `#formulaPreviewFallback` label with no inline text color.

- [ ] **Step 1: Add failing coverage for all three HTML documents and the fallback**

  Extend `tests/test_math_input_theme.py`:

  ```python
  @pytest.mark.parametrize(
      "filename",
      ["mathlive.html", "inline_formula_overlay.html", "formula_preview.html"],
  )
  def test_math_input_document_uses_theme_variables(filename: str) -> None:
      html = (ROOT / "MathInputWidget" / filename).read_text(encoding="utf-8")
      assert "var(--mi-bg-panel," in html or "var(--mi-editing-bg," in html
      assert "var(--mi-text-primary," in html
      assert "var(--mi-focus," in html
      assert "--selection-background-color: var(--mi-selected-bg" in html


  def test_formula_preview_fallback_has_no_inline_theme_color() -> None:
      source = (ROOT / "MathInputWidget" / "formula_preview.py").read_text(encoding="utf-8")
      assert "#1f2937" not in source
      assert 'setObjectName("formulaPreviewFallback")' in source
  ```

  Add a helper that finds `background`, `color`, and `border` declarations containing the retired light literals outside `var(...)` fallbacks.

- [ ] **Step 2: Run the focused tests and identify each light-only declaration**

  Run: `uv run pytest tests/test_math_input_theme.py -q`

  Expected: FAIL for the editor, inline overlay, preview, MathLive selection variables, and the fallback label inline color.

- [ ] **Step 3: Replace editor and inline-overlay colors with semantic variables**

  In both `mathlive.html` and `inline_formula_overlay.html`, use the approved mappings:

  ```css
  body { background: var(--mi-bg-panel, #ffffff); color: var(--mi-text-primary, #1f2937); }
  math-field {
    color: var(--mi-text-primary, #1f2937);
    background: var(--mi-editing-bg, #fffdf4);
    border-color: var(--mi-border, #cfd8e1);
    --caret-color: var(--mi-focus, #2f7ebd);
    --selection-background-color: var(--mi-selected-bg, #eaf2fd);
    --contains-highlight-background-color: var(--mi-selected-bg, #eaf2fd);
  }
  .ML__keyboard, .ML__popover { background: var(--mi-toolbar-bg, #2c2e2f); }
  ```

  Use `--mi-toolbar-hover` and `--mi-toolbar-accent` for toolbar controls. Preserve transparent overlay regions and existing geometry calculations.

- [ ] **Step 4: Theme preview HTML and return fallback text color to QSS**

  Migrate `formula_preview.html` text, transparent background, selection, and highlight colors to variables. In `formula_preview.py`, replace:

  ```python
  self._fallback_label.setStyleSheet("padding-left: 4px; color: #1f2937;")
  ```

  with:

  ```python
  self._fallback_label.setStyleSheet("padding-left: 4px;")
  ```

  Keep `objectName("formulaPreviewFallback")` and add the missing global selector:

  ```css
  #formulaPreviewFallback { color: $text_primary; }
  ```

  Add a `tests/test_ui_tokens.py` assertion for the light/dark token value and regenerate/review both QSS snapshots.

- [ ] **Step 5: Run MathInput and QSS tests, then commit**

  Run: `uv run pytest tests/test_math_input_theme.py tests/test_math_input_widget.py tests/test_ui_tokens.py -q`

  Expected: PASS and no light-only authored declarations outside fallbacks.

  Commit:

  ```bash
  git add MathInputWidget/mathlive.html MathInputWidget/inline_formula_overlay.html MathInputWidget/formula_preview.html MathInputWidget/formula_preview.py ui/styles/base.qss.in tests/test_math_input_theme.py tests/test_ui_tokens.py tests/snapshots/base-light.qss tests/snapshots/base-dark.qss
  git commit -m "style: theme MathInput editor and preview surfaces"
  ```

<!-- openspec-task: 3.4 -->
### Task 2: Add a reusable pending-safe ThemeBridge to every MathInput host

**Files:**
- Create: `MathInputWidget/theme_bridge.py`
- Modify: `MathInputWidget/formula_list.py`
- Modify: `MathInputWidget/widget.py`
- Modify: `MathInputWidget/formula_popup.py`
- Modify: `MathInputWidget/formula_preview.py`
- Modify: `MathInputWidget/inline_formula_overlay.py`
- Modify: `tests/test_math_input_theme.py`

**Interfaces:**
- Produces: `ThemeBridge(view: QWebEngineView, initial_theme: ThemeName = "light")`.
- Produces methods: `install(theme: ThemeName) -> None`, `set_theme(theme: ThemeName) -> None`, and `on_load_finished(success: bool) -> None`.
- Produces optional `initial_theme: ThemeName = "light"` constructor parameters and `set_theme(theme)` APIs on `FormulaListWidget`, `MathInputWidget`, `FormulaEditorPopup`, `FormulaPreviewWidget`, and `InlineFormulaEditorOverlay`.

- [ ] **Step 1: Write failing ThemeBridge state-machine tests with fakes**

  Add fake scripts/page/view objects to `tests/test_math_input_theme.py` and assert:

  ```python
  def test_theme_bridge_caches_until_load_then_switches_without_reload() -> None:
      view = FakeView()
      bridge = ThemeBridge(view, "light")
      bridge.install("dark")
      assert view.page_value.scripts_value.inserted[0].injectionPoint() == QWebEngineScript.InjectionPoint.DocumentCreation
      bridge.set_theme("dark")
      assert view.page_value.javascript == []
      bridge.on_load_finished(True)
      assert view.page_value.javascript[-1] == 'document.documentElement.dataset.theme = "dark";'
      url_calls = view.set_url_calls
      bridge.set_theme("light")
      assert view.page_value.javascript[-1] == 'document.documentElement.dataset.theme = "light";'
      assert view.set_url_calls == url_calls
  ```

  Also assert invalid themes raise `TokenError` and failed loads retain the pending theme for a later successful load.

- [ ] **Step 2: Run the focused test and confirm the bridge is missing**

  Run: `uv run pytest tests/test_math_input_theme.py -q`

  Expected: FAIL during import because `MathInputWidget.theme_bridge` does not exist.

- [ ] **Step 3: Implement script installation and pending state**

  Construct a new `QWebEngineScript` for `math_input_theme_script(theme)`:

  ```python
  script = QWebEngineScript()
  script.setName("math3d-math-input-theme")
  script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
  script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
  script.setRunsOnSubFrames(False)
  script.setSourceCode(math_input_theme_script(theme))
  view.page().scripts().insert(script)
  ```

  Store `_loaded` and `_pending_theme`. `set_theme()` must cache before load and run exactly `document.documentElement.dataset.theme = <json>;` after load. `on_load_finished(False)` must not clear pending state.

- [ ] **Step 4: Wire each host exactly once**

  Add an optional `initial_theme` parameter to each host constructor. Create the bridge immediately after each `QWebEngineView` is created and before `setUrl()`; call `install(initial_theme)`. In every existing `_on_load_finished`, call `theme_bridge.on_load_finished(success)` before sending content. Public APIs delegate:

  ```python
  def set_theme(self, theme: ThemeName) -> None:
      self._theme_bridge.set_theme(theme)
  ```

  `FormulaEditorPopup` passes its constructor theme to `MathInputWidget` and `set_theme()` delegates to `self.editor.set_theme(theme)`. Lazy `FormulaPreviewWidget` stores `_theme` before `_ensure_web_view()` and installs that theme on creation. Wire the currently standalone `InlineFormulaEditorOverlay` as well, satisfying the design's fourth WebView without forcing it into AlgebraPanel construction.

- [ ] **Step 5: Run theme state and existing WebEngine lifecycle tests, then commit**

  Run: `uv run pytest tests/test_math_input_theme.py tests/test_math_input_widget.py tests/test_algebra_panel.py -q`

  Expected: PASS; content synchronization still occurs after successful load, and no theme switch calls `setUrl()` or `reload()`.

  Commit:

  ```bash
  git add MathInputWidget/theme_bridge.py MathInputWidget/formula_list.py MathInputWidget/widget.py MathInputWidget/formula_popup.py MathInputWidget/formula_preview.py MathInputWidget/inline_formula_overlay.py tests/test_math_input_theme.py
  git commit -m "feat: bridge themes into MathInput webviews"
  ```

<!-- openspec-task: 3.5 -->
### Task 3: Propagate AlgebraPanel theme to current and future formula surfaces

**Files:**
- Modify: `ui/algebra_panel.py`
- Modify: `tests/test_algebra_panel.py`
- Modify: `tests/test_math_input_theme.py`

**Interfaces:**
- Consumes: MathInput host `set_theme(theme)` APIs from Task 2.
- Produces: `AlgebraPanel._effective_theme: ThemeName` as the source for previews created after a switch.
- Extends: `AlgebraPanel.sync_overlay_theme(theme)` to theme formula list, editor popup, and every `FormulaPreviewWidget` descendant.

- [ ] **Step 1: Add a failing propagation test using spies**

  In `tests/test_algebra_panel.py`, add:

  ```python
  def test_sync_overlay_theme_forwards_to_math_input_surfaces(monkeypatch) -> None:
      panel = AlgebraPanel()
      list_themes, popup_themes = [], []
      monkeypatch.setattr(panel.formula_list, "set_theme", list_themes.append)
      monkeypatch.setattr(panel.formula_popup, "set_theme", popup_themes.append)
      preview = FormulaPreviewWidget("x^2", panel)
      preview_themes = []
      monkeypatch.setattr(preview, "set_theme", preview_themes.append)

      panel.sync_overlay_theme("dark")

      assert panel._effective_theme == "dark"
      assert list_themes == ["dark"]
      assert popup_themes == ["dark"]
      assert preview_themes == ["dark"]
  ```

- [ ] **Step 2: Run the test and observe missing WebView forwarding**

  Run: `uv run pytest tests/test_algebra_panel.py::test_sync_overlay_theme_forwards_to_math_input_surfaces -q`

  Expected: FAIL because `sync_overlay_theme()` currently updates only shadows and icons.

- [ ] **Step 3: Store and forward the effective theme**

  Derive the initial theme at the start of `AlgebraPanel.__init__` from `getattr(parent, "effective_theme", "light")`, store it in `_effective_theme`, and pass it to `FormulaListWidget` and `FormulaEditorPopup` constructors. This prevents a dark startup from installing a light DocumentCreation script. At the top of `sync_overlay_theme`:

  ```python
  self._effective_theme = theme
  self.formula_list.set_theme(theme)
  self.formula_popup.set_theme(theme)
  for preview in self.findChildren(FormulaPreviewWidget):
      preview.set_theme(theme)
  ```

  Retain the existing popup shadow and icon retint loop. Replace the constructor's unconditional `sync_overlay_theme("light")` with `sync_overlay_theme(self._effective_theme)`.

- [ ] **Step 4: Ensure newly created previews inherit the stored theme**

  At both `FormulaPreviewWidget(...)` construction sites used by algebra rows/settings rows, immediately call `preview.set_theme(self.window().effective_theme)` only if the owner has a valid theme, or pass the panel's stored theme through the owning row constructor. Prefer the smallest change that results in this invariant:

  ```python
  preview.set_theme(getattr(self.window(), "effective_theme", "light"))
  ```

  Add a test that switches the panel to dark, creates a row/preview afterward, and asserts the new preview caches `dark` before its WebView is loaded.

- [ ] **Step 5: Run AlgebraPanel and theme integration tests, then commit**

  Run: `uv run pytest tests/test_algebra_panel.py tests/test_math_input_theme.py tests/test_ui_tokens.py -q`

  Expected: PASS for initial dark startup, runtime switching, and a popup opened after the switch.

  Commit:

  ```bash
  git add ui/algebra_panel.py tests/test_algebra_panel.py tests/test_math_input_theme.py
  git commit -m "feat: propagate algebra panel theme to formulas"
  ```

<!-- openspec-task: 3.6 -->
### Task 4: Make long formulas horizontally scrollable without a visible scrollbar

**Files:**
- Modify: `MathInputWidget/formula_list.html`
- Modify: `tests/test_math_input_theme.py`

**Interfaces:**
- Produces: row-local horizontal scrolling on `.formula-cell`.
- Preserves: `body { overflow-x: hidden; }`, `math-field` no-wrap rendering, and the absolutely positioned visibility/settings controls.

- [ ] **Step 1: Add a failing CSS contract for hidden row scrolling**

  Add to `tests/test_math_input_theme.py`:

  ```python
  def test_formula_cell_scrolls_long_content_without_visible_scrollbar() -> None:
      html = (ROOT / "MathInputWidget" / "formula_list.html").read_text(encoding="utf-8")
      assert re.search(r"\.formula-cell\s*\{[^}]*overflow-x:\s*auto", html, re.S)
      assert re.search(r"\.formula-cell\s*\{[^}]*scrollbar-width:\s*none", html, re.S)
      assert re.search(r"\.formula-cell::?-webkit-scrollbar\s*\{[^}]*display:\s*none", html, re.S)
      assert re.search(r"body\s*\{[^}]*overflow-x:\s*hidden", html, re.S)
  ```

  Add an assertion that `white-space: nowrap` is not applied to the whole formula row; it may remain on the MathLive field/content element.

- [ ] **Step 2: Run the test and confirm long content is currently clipped**

  Run: `uv run pytest tests/test_math_input_theme.py::test_formula_cell_scrolls_long_content_without_visible_scrollbar -q`

  Expected: FAIL because the row/cell has no horizontal scroll container.

- [ ] **Step 3: Move overflow ownership to the formula cell**

  Implement:

  ```css
  .formula-cell {
    min-width: 0;
    overflow-x: auto;
    overflow-y: hidden;
    scrollbar-width: none;
  }
  .formula-cell::-webkit-scrollbar { display: none; }
  .formula-cell math-field { min-width: max-content; white-space: nowrap; }
  ```

  Remove row-level `white-space: nowrap` that prevents scrolling. Keep action buttons outside `.formula-cell` so they do not move with its scroll position.

- [ ] **Step 4: Add a manual WebEngine smoke case**

  Inject a formula substantially wider than 360px, then verify with wheel+Shift or touchpad horizontal input that the right end becomes visible, the row stays within the algebra panel, and no horizontal scrollbar is painted. Repeat in light and dark themes.

- [ ] **Step 5: Run formula regressions and commit**

  Run: `uv run pytest tests/test_math_input_theme.py tests/test_algebra_panel.py -q`

  Expected: PASS with no row action or selection regression.

  Commit:

  ```bash
  git add MathInputWidget/formula_list.html tests/test_math_input_theme.py
  git commit -m "fix: allow hidden horizontal formula scrolling"
  ```

<!-- openspec-task: 4.1 -->
### Task 5: Apply the approved compact Agent timeline density

**Files:**
- Modify: `ui/agent_web/src/styles/layout.css`
- Create: `ui/agent_web/src/styles/layout.test.ts`
- Generate: `ui/agent_web/dist/`

**Interfaces:**
- Produces exact CSS values: `.assistant-content` 12px/1.5; `.event-card` padding `8px 10px`, margin `6px 0`, font 12px; `.turn-block` bottom margin 18px; `.timeline` padding `16px 14px 20px`; paragraph margin 6px; reasoning/thinking values from Design D4.

- [ ] **Step 1: Write a failing stylesheet contract test**

  Create `src/styles/layout.test.ts` using `readFileSync` and a small `block(selector)` helper. Assert exact declarations:

  ```typescript
  expect(block(".assistant-content")).toContain("font-size: 12px");
  expect(block(".assistant-content")).toContain("line-height: 1.5");
  expect(block(".event-card")).toContain("margin: 6px 0");
  expect(block(".event-card")).toContain("padding: 8px 10px");
  expect(block(".turn-block")).toContain("margin: 0 auto 18px");
  expect(block(".timeline")).toContain("padding: 16px 14px 20px");
  expect(block(".markdown-content p")).toContain("margin: 6px 0");
  ```

  Assert `.reasoning-block` has `padding: 7px 9px` and 11px font, and `.thinking-section` has `margin: 8px 0 10px`.

- [ ] **Step 2: Run the test and record the relaxed values**

  Run from `ui/agent_web`: `pnpm test -- src/styles/layout.test.ts`

  Expected: FAIL on 13px/1.55 text, larger card padding, 28px turn spacing, and 22px timeline padding.

- [ ] **Step 3: Replace only the approved density declarations**

  Change the exact D4 values and leave user bubble geometry, composer height, model popover dimensions, and all colors untouched. Where `.turn-actions` has two rule blocks, do not consolidate it in this task; Task 6 locks its layout behavior.

- [ ] **Step 4: Rebuild production assets and inspect the generated CSS**

  Run from `ui/agent_web`: `pnpm build`

  Expected: the current hashed CSS asset in `dist/assets/` contains `font-size:12px;line-height:1.5`, `padding:8px 10px`, and `margin:0 auto 18px` after minification.

- [ ] **Step 5: Run frontend/package checks and commit**

  Run:

  ```powershell
  Push-Location ui/agent_web
  pnpm test -- src/styles/layout.test.ts
  pnpm build
  Pop-Location
  uv run pytest tests/test_agent_web_packaging.py -q
  ```

  Expected: PASS.

  Commit:

  ```bash
  git add ui/agent_web/src/styles/layout.css ui/agent_web/src/styles/layout.test.ts ui/agent_web/dist
  git commit -m "style: tighten agent timeline density"
  ```

<!-- openspec-task: 4.2 -->
### Task 6: Lock hover-action geometry and the 620px reading measure

**Files:**
- Modify: `ui/agent_web/src/styles/layout.test.ts`
- Modify: `ui/agent_web/src/components/Timeline.test.tsx`

**Interfaces:**
- Verifies: `.turn-block { position: relative; max-width: 620px; }` and centered reading surfaces.
- Verifies: `.turn-actions` remains absolutely positioned and visibility/opacity changes do not participate in document layout.

- [ ] **Step 1: Add failing/readability guard assertions**

  Extend `layout.test.ts`:

  ```typescript
  it("keeps actions out of layout and preserves the readable measure", () => {
    expect(block(".turn-block")).toContain("position: relative");
    expect(block(".turn-block")).toContain("max-width: 620px");
    expect(block(".turn-actions")).toContain("position: absolute");
    expect(block(".turn-actions")).toContain("visibility: hidden");
    expect(block(".turn-actions.visible")).toContain("visibility: visible");
  });
  ```

  In `Timeline.test.tsx`, assert toggling hover adds the `visible` class to the same absolutely positioned element without adding/removing any wrapper around `.assistant-content`.

- [ ] **Step 2: Run the focused tests**

  Run from `ui/agent_web`: `pnpm test -- src/styles/layout.test.ts src/components/Timeline.test.tsx`

  Expected: the new guards may expose duplicate selector parsing or a missing class transition assertion; fix tests/helper precision before changing product CSS.

- [ ] **Step 3: Preserve the locked geometry while resolving duplicate rules**

  If the helper sees two `.turn-actions` blocks, merge their declarations into one block with:

  ```css
  .turn-actions {
    position: absolute;
    right: 0;
    bottom: -24px;
    display: flex;
    gap: 2px;
    visibility: hidden;
    opacity: 0;
    transition: opacity .12s ease;
  }
  ```

  Keep `.turn-actions.visible` limited to visibility/opacity. Do not add margins, fixed flow height, or a grid row for the controls.

- [ ] **Step 4: Run the layout and timeline tests after cleanup**

  Run from `ui/agent_web`: `pnpm test -- src/styles/layout.test.ts src/components/Timeline.test.tsx`

  Expected: PASS, with max-width exactly 620px and action visibility causing no DOM-flow change.

- [ ] **Step 5: Commit the locked layout contract**

  ```bash
  git add ui/agent_web/src/styles/layout.css ui/agent_web/src/styles/layout.test.ts ui/agent_web/src/components/Timeline.test.tsx
  git commit -m "test: lock agent reading width and hover actions"
  ```

<!-- openspec-task: 4.3 -->
### Task 7: Auto-scroll streaming output only while the timeline is pinned

**Files:**
- Modify: `ui/agent_web/src/components/Timeline.tsx`
- Modify: `ui/agent_web/src/components/Timeline.test.tsx`

**Interfaces:**
- Produces: `pinnedRef`, updated from the `.timeline` scroll event using `scrollHeight - scrollTop - clientHeight < 40`.
- Resets pinning when `session.id` changes and when a new user turn appears.
- Preserves: the existing `scrollIntoView({ block: "nearest" })` mechanism when pinned.

- [ ] **Step 1: Add failing pinned and unpinned streaming tests**

  Add a helper that defines writable scroll metrics on the rendered timeline and spies on the terminal div's `scrollIntoView`. Cover:

  ```typescript
  it("does not pull the reader down after they scroll up", () => {
    const { rerender } = renderTimeline(sessionWith("partial"));
    const timeline = screen.getByLabelText("Conversation timeline");
    setScrollMetrics(timeline, { scrollHeight: 1000, scrollTop: 300, clientHeight: 400 });
    fireEvent.scroll(timeline);
    scrollIntoView.mockClear();
    rerender(timelineFor(sessionWith("partial more")));
    expect(scrollIntoView).not.toHaveBeenCalled();
  });

  it("keeps following streaming output while at the bottom", () => {
    setScrollMetrics(timeline, { scrollHeight: 1000, scrollTop: 580, clientHeight: 400 });
    fireEvent.scroll(timeline);
    rerender(timelineFor(sessionWith("next token")));
    expect(scrollIntoView).toHaveBeenCalledWith({ block: "nearest" });
  });
  ```

  Add a third test: appending a new user turn sets pinning true even if the previous turn was unpinned.

- [ ] **Step 2: Run the component test and reproduce forced scrolling**

  Run from `ui/agent_web`: `pnpm test -- src/components/Timeline.test.tsx`

  Expected: FAIL because the current effect scrolls on every streamed text change.

- [ ] **Step 3: Add the local scroll state machine**

  Implement:

  ```typescript
  const pinnedRef = useRef(true);
  const previousTurnCountRef = useRef(session.turns.length);

  useEffect(() => {
    pinnedRef.current = true;
    previousTurnCountRef.current = session.turns.length;
  }, [session.id]);

  const onScroll = (event: React.UIEvent<HTMLElement>) => {
    const element = event.currentTarget;
    pinnedRef.current = element.scrollHeight - element.scrollTop - element.clientHeight < 40;
  };
  ```

  Before the streaming effect checks `pinnedRef`, detect `session.turns.length > previousTurnCountRef.current`, set pinned true, and update the previous count. Attach `onScroll` to the timeline section.

- [ ] **Step 4: Keep the existing streaming dependencies and gate the effect**

  Retain dependencies on turn count, event count, assistant text, reasoning text, and progress log count:

  ```typescript
  useEffect(() => {
    if (pinnedRef.current) endRef.current?.scrollIntoView?.({ block: "nearest" });
  }, [session.turns.length, latest?.events.length, latest?.assistantText, latest?.reasoningText, latest?.progressLogs?.length]);
  ```

  Do not debounce token rendering or store scroll state in the session reducer.

- [ ] **Step 5: Run timeline/frontend tests and commit**

  Run from `ui/agent_web`: `pnpm test -- src/components/Timeline.test.tsx src/App.test.tsx && pnpm build`

  Expected: PASS for unpinned, pinned, new-turn, and existing timeline rendering cases.

  Commit:

  ```bash
  git add ui/agent_web/src/components/Timeline.tsx ui/agent_web/src/components/Timeline.test.tsx ui/agent_web/dist
  git commit -m "fix: pin timeline scrolling only at bottom"
  ```

<!-- openspec-task: 5.1 -->
### Task 8: Give panel resize handles visible hover and drag states

**Files:**
- Modify: `ui/panel_resize_handle.py`
- Modify: `ui/styles/base.qss.in`
- Modify: `tests/test_panel_resize_handle.py`
- Modify: `tests/test_ui_tokens.py`
- Modify: `tests/test_main_window_layout.py`
- Modify: `tests/snapshots/base-light.qss`
- Modify: `tests/snapshots/base-dark.qss`

**Interfaces:**
- Produces: `_PanelResizeHandle.FIXED_WIDTH = 6`, object name `panelResizeHandle`, tooltip `拖动调整宽度，双击复位`, and dynamic property `dragging`.
- Produces QSS selectors: `#panelResizeHandle`, `#panelResizeHandle:hover`, and `#panelResizeHandle[dragging="true"]`.

- [ ] **Step 1: Add failing construction, interaction, and QSS tests**

  In `tests/test_panel_resize_handle.py`, assert width, name, tooltip, and dynamic property changes using `QTest.mousePress`/`mouseRelease`:

  ```python
  assert handle.width() == 6
  assert handle.objectName() == "panelResizeHandle"
  assert handle.toolTip() == "拖动调整宽度，双击复位"
  QTest.mousePress(handle, Qt.MouseButton.LeftButton, pos=QPoint(2, 2))
  assert handle.property("dragging") is True
  QTest.mouseRelease(handle, Qt.MouseButton.LeftButton, pos=QPoint(2, 2))
  assert handle.property("dragging") is False
  ```

  In `tests/test_ui_tokens.py`, assert the idle block uses `border-left: 1px solid <border_default>` and hover/drag blocks use accent soft background and 2px accent border.

- [ ] **Step 2: Run focused tests and confirm invisible-handle behavior**

  Run: `uv run pytest tests/test_panel_resize_handle.py tests/test_ui_tokens.py tests/test_main_window_layout.py -q`

  Expected: FAIL on width 5, empty name/tooltip, absent dragging property, missing QSS, and stale snapshots/layout assertion.

- [ ] **Step 3: Add discoverability state to the widget**

  In `_PanelResizeHandle`:

  ```python
  FIXED_WIDTH = 6

  self.setObjectName("panelResizeHandle")
  self.setFixedWidth(self.FIXED_WIDTH)
  self.setToolTip("拖动调整宽度，双击复位")
  self.setProperty("dragging", False)
  ```

  Add `_set_dragging(value)` that sets the property and calls `self.style().unpolish(self)`, `polish(self)`, and `self.update()`. Call it on accepted left press and on every release/cancel path.

- [ ] **Step 4: Add token QSS and update snapshots/layout expectations**

  Add:

  ```css
  #panelResizeHandle { border-left: 1px solid $border_default; }
  #panelResizeHandle:hover,
  #panelResizeHandle[dragging="true"] {
    background: $accent_soft_bg;
    border-left: 2px solid $accent_default;
  }
  ```

  Update `tests/test_main_window_layout.py` from width 5 to 6, regenerate both QSS snapshots, and inspect the diff.

- [ ] **Step 5: Run panel/QSS regressions and commit**

  Run: `uv run pytest tests/test_panel_resize_handle.py tests/test_main_window_layout.py tests/test_ui_tokens.py -q`

  Expected: PASS in light and dark snapshots.

  Commit:

  ```bash
  git add ui/panel_resize_handle.py ui/styles/base.qss.in tests/test_panel_resize_handle.py tests/test_ui_tokens.py tests/test_main_window_layout.py tests/snapshots/base-light.qss tests/snapshots/base-dark.qss
  git commit -m "style: expose panel resize handles"
  ```

<!-- openspec-task: 5.2 -->
### Task 9: Expand the Agent panel persistence range to 360–720px

**Files:**
- Modify: `ui/agent_sidebar.py`
- Modify: `ui/designer_window.py`
- Modify: `tests/test_sidebar.py`
- Modify: `tests/test_panel_resize_handle.py`
- Modify: `tests/test_main_window_layout.py`

**Interfaces:**
- Produces: `AgentSidebar.MIN_WIDTH = 360`, `DEFAULT_WIDTH = 440`, `MAX_WIDTH = 720`.
- Produces: `_install_agent_panel()` `PanelResizeSpec(360, 720, 440, "ui/agent_panel_width", "left")`.
- Preserves: persistence key, inverse drag direction, and collapsed-panel layout behavior.

- [ ] **Step 1: Update tests first for the new bound and old persisted values**

  Change `tests/test_sidebar.py` to expect 720. Extend `tests/test_panel_resize_handle.py`:

  ```python
  def test_agent_panel_restores_values_above_the_old_limit(tmp_path) -> None:
      settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
      settings.setValue("ui/agent_panel_width", 680)
      handle = _PanelResizeHandle(
          PanelResizeSpec(360, 720, 440, "ui/agent_panel_width", "left"),
          settings=settings,
      )
      assert handle.restore_width() == 680
      assert handle.set_width(999) == 720
  ```

  Add a source/construction assertion in `tests/test_main_window_layout.py` that the installed spec maximum equals `AgentSidebar.MAX_WIDTH` rather than duplicating a literal.

- [ ] **Step 2: Run focused layout tests and see the 560 clamp**

  Run: `uv run pytest tests/test_sidebar.py tests/test_panel_resize_handle.py tests/test_main_window_layout.py -q`

  Expected: FAIL because both `AgentSidebar` and the installed resize spec still clamp at 560.

- [ ] **Step 3: Change both public and persistence clamps together**

  Set `AgentSidebar.MAX_WIDTH = 720`. In `_install_agent_panel`, construct the spec from public constants:

  ```python
  PanelResizeSpec(
      self.agent_sidebar.MIN_WIDTH,
      self.agent_sidebar.MAX_WIDTH,
      self.agent_sidebar.DEFAULT_WIDTH,
      "ui/agent_panel_width",
      "left",
  )
  ```

  Keep `AgentSidebar.set_panel_width()` clamping through the class constants.

- [ ] **Step 4: Verify wide layout retains its readable column**

  Run the Agent CSS contract from Task 6 and add/retain an assertion that `.turn-block` max-width is 620px. Construct the sidebar at 720px in a Qt test and assert composer/WebView width is positive and no fixed child requests more than 720px.

- [ ] **Step 5: Run panel and Web layout regressions, then commit**

  Run:

  ```powershell
  uv run pytest tests/test_sidebar.py tests/test_panel_resize_handle.py tests/test_main_window_layout.py tests/test_sidebar_visibility.py -q
  Push-Location ui/agent_web
  pnpm test -- src/styles/layout.test.ts
  Pop-Location
  ```

  Expected: PASS for 360 minimum, 720 maximum, 680 restoration, and 620px reading measure.

  Commit:

  ```bash
  git add ui/agent_sidebar.py ui/designer_window.py tests/test_sidebar.py tests/test_panel_resize_handle.py tests/test_main_window_layout.py
  git commit -m "feat: widen agent sidebar to 720 pixels"
  ```
