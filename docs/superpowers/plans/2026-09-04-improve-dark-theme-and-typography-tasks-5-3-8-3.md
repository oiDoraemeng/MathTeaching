# Dark Theme and Typography Improvements — Interaction and Accessibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Verify robust panel resizing, eliminate the remaining dark-theme paint leak, restore visible Qt keyboard focus, make the 2D line flyout keyboard-accessible, and fix core Agent Web dismissal and target-size interactions.

**Architecture:** Qt visual state remains token-backed and testable through explicit widget properties; `LightRotationWidget` owns a resolved paint palette supplied by `LightingDialog`. Keyboard access is implemented in the existing toolbar event-filter boundary. React cancellation/dismissal state stays local to each component and CSS enforces the shared 11px text and 28px target floors.

**Tech Stack:** Python 3.11, PySide6 6.8/QTest, Qt Style Sheets, React 18, TypeScript, Vitest/Testing Library, pnpm/Vite, pytest.

**Spec:** `openspec/changes/improve-dark-theme-and-typography/design.md`, `openspec/changes/improve-dark-theme-and-typography/tasks.md`, `openspec/changes/improve-dark-theme-and-typography/specs/ui-design-system/spec.md`, `openspec/changes/improve-dark-theme-and-typography/specs/app-shell/spec.md`, and `openspec/changes/improve-dark-theme-and-typography/specs/mathagent-sidebar/spec.md`

## Global Constraints

- Do not introduce Qt-unsupported pseudo-states; generated QSS must contain no `:focus-visible`.
- A focused Qt control has a visible 2px accent ring in both themes, without changing its overall fixed hit area.
- Preserve hover behavior for the 2D line flyout while adding click, arrows, Enter/Space, and Escape paths.
- All co-located toolbar icons remain SVG-backed through `ui.icons`; no Unicode control icons or emoji may be introduced.
- Agent Web visible text uses at least 11px and the named interactive targets use at least 28×28px.
- Dark-theme verification must be encoded in repeatable tests before the manual smoke pass.
- Keep commits task-scoped and stage only the files listed by the current task.

---

<!-- openspec-task: 5.3 -->
### Task 1: Lock panel drag, reset, persistence, and collapse behavior with an interaction regression

**Files:**
- Modify: `tests/test_panel_resize_handle.py`
- Modify: `tests/test_sidebar_visibility.py`
- Modify: `tests/test_main_window_layout.py`

**Interfaces:**
- Verifies: right-edge algebra drag uses direct delta and clamps to 260–420px.
- Verifies: left-edge Agent drag uses inverse delta and clamps to 360–720px.
- Verifies: double-click resets to 320/440, persisted values survive a new handle, and a collapsed Agent panel hides the divider.

- [x] **Step 1: Add failing end-to-end handle interaction tests**

  Use `QTest` and a real temporary `QSettings` file:

  ```python
  @pytest.mark.parametrize(
      ("spec", "start", "delta", "expected"),
      [
          (PanelResizeSpec(260, 420, 320, "ui/algebra_panel_width", "right"), 320, 180, 420),
          (PanelResizeSpec(360, 720, 440, "ui/agent_panel_width", "left"), 440, -400, 720),
      ],
  )
  def test_drag_follows_pointer_and_clamps(tmp_path, spec, start, delta, expected) -> None:
      settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
      handle = _PanelResizeHandle(spec, settings=settings)
      handle.set_width(start)
      seen = []
      handle.width_changed.connect(seen.append)
      # Send press/move/release events whose global x positions differ by delta.
      send_drag(handle, delta)
      assert seen[-1] == expected
      assert settings.value(spec.settings_key, type=int) == expected
  ```

  Add a double-click test for both specs and reconstruct a second handle from the same settings to verify persistence.

- [x] **Step 2: Add a failing divider visibility assertion**

  Extend `tests/test_sidebar_visibility.py` around the existing show/hide seam: after expanding, `agent_resize_handle.isVisible()` is true; after collapsing, both sidebar and handle are hidden and the viewport layout contains no visible placeholder strip.

- [x] **Step 3: Run the panel-focused tests and fix only uncovered regressions**

  Run: `uv run pytest tests/test_panel_resize_handle.py tests/test_sidebar_visibility.py tests/test_main_window_layout.py -q`

  Expected: PASS if Tasks 5.1–5.2 fully preserved existing behavior; otherwise FAIL at the exact drag/reset/collapse contract. Fix product code only when a test demonstrates a real regression, keeping the already-approved bounds/defaults.

- [ ] **Step 4: Perform the pointer smoke pass in the running application**

  Verify both dividers in light and dark themes: the width follows the pointer; both bounds clamp; double-click returns 320/440; closing Agent hides its divider; reopening restores the last persisted width; restarting the app retains both values. Record any discrepancy as a focused test before fixing it.

- [x] **Step 5: Commit the repeatable regression coverage**

  Run: `uv run pytest tests/test_panel_resize_handle.py tests/test_sidebar_visibility.py tests/test_main_window_layout.py -q`

  Expected: PASS.

  Commit:

  ```bash
  git add tests/test_panel_resize_handle.py tests/test_sidebar_visibility.py tests/test_main_window_layout.py
  git commit -m "test: cover panel resize interaction lifecycle"
  ```

<!-- openspec-task: 6.1 -->
### Task 2: Paint the lighting rotation widget from effective-theme tokens

**Files:**
- Modify: `widgets/LightRotationWidget.py`
- Modify: `ui/lighting_dialog.py`
- Modify: `tests/test_lighting_dialog.py`
- Modify: `tests/test_ui_typography.py`

**Interfaces:**
- Produces: `LightRotationWidget.set_theme(tokens: Mapping[str, str | int]) -> None`.
- Produces internal paint palette keys: `card`, `label`, `value`, `ring_default`, `ring_hover`, `ring_pressed`, `sphere_light`, `sphere_mid`, `sphere_dark`, `sphere_border`, and `marker_border`.
- `LightingDialog.set_effective_theme(theme)` supplies `flatten_theme(theme)` and requests repaint.

- [x] **Step 1: Add failing light/dark token palette tests**

  Extend `tests/test_lighting_dialog.py`:

  ```python
  def test_rotation_widget_uses_effective_theme_tokens() -> None:
      dialog = LightingDialog(LightSettings(), effective_theme="light")
      light = dict(dialog.rotation_widget._paint_colors)
      dialog.set_effective_theme("dark")
      dark = dialog.rotation_widget._paint_colors
      assert light["card"] == flatten_theme("light")["bg_elevated"]
      assert dark["card"] == flatten_theme("dark")["bg_elevated"]
      assert dark["label"] == flatten_theme("dark")["text_secondary"]
      assert dark["value"] == flatten_theme("dark")["accent_default"]
      assert light != dark
  ```

  Spy on `rotation_widget.update` and assert `set_effective_theme("dark")` requests a repaint.

- [x] **Step 2: Run the test and reproduce hardcoded light colors**

  Run: `uv run pytest tests/test_lighting_dialog.py tests/test_ui_typography.py -q`

  Expected: FAIL because `LightRotationWidget.paintEvent()` embeds light literals and has no theme API.

- [x] **Step 3: Resolve a complete paint palette in `set_theme`**

  Add a mapping-based API and initialize it from `flatten_theme("light")` in the widget constructor:

  ```python
  def set_theme(self, tokens: Mapping[str, str | int]) -> None:
      self._paint_colors = {
          "card": str(tokens["bg_elevated"]),
          "label": str(tokens["text_secondary"]),
          "value": str(tokens["accent_default"]),
          "ring_default": str(tokens["accent_default"]),
          "ring_hover": str(tokens["accent_hover"]),
          "ring_pressed": str(tokens["accent_pressed"]),
          "sphere_light": str(tokens["border_strong"]),
          "sphere_mid": str(tokens["border_default"]),
          "sphere_dark": str(tokens["text_muted"]),
          "sphere_border": str(tokens["border_strong"]),
          "marker_border": str(tokens["text_primary"]),
      }
      self.update()
  ```

  Keep sun fill/ray constants `#fbbf24` and `#f59e0b`, which the design explicitly approves in both themes.

- [x] **Step 4: Replace every retired paint literal and connect the dialog**

  Make `paintEvent()` read only `_paint_colors` for the card, labels, ring, sphere, marker border, and value. In `LightingDialog.set_effective_theme`:

  ```python
  self.effective_theme = effective_theme
  apply_drop_shadow(self, "modal", effective_theme)
  if hasattr(self, "rotation_widget"):
      self.rotation_widget.set_theme(flatten_theme(effective_theme))
  ```

  Because the constructor currently calls `set_effective_theme` before `_build_ui`, call it once more after `_build_ui`, or move the initial call after widget creation while preserving modal shadow setup.

- [x] **Step 5: Run light/dark paint and typography tests, then commit**

  Run: `uv run pytest tests/test_lighting_dialog.py tests/test_ui_typography.py tests/test_dialog_theming.py -q`

  Expected: PASS with inherited fonts unchanged and no light-only card literal in the painter.

  Commit:

  ```bash
  git add widgets/LightRotationWidget.py ui/lighting_dialog.py tests/test_lighting_dialog.py tests/test_ui_typography.py
  git commit -m "style: theme the lighting rotation widget"
  ```

<!-- openspec-task: 6.2 -->
### Task 3: Add an integrated dark-surface regression for lighting and formula fallback

**Files:**
- Create: `tests/test_dark_theme_surfaces.py`

**Interfaces:**
- Verifies: dark lighting card/labels/accent equal dark tokens.
- Verifies: FormulaPreview fallback is visible before load and inherits `#formulaPreviewFallback` QSS color instead of an inline light-theme color.

- [x] **Step 1: Create an integrated dark-theme test**

  Add:

  ```python
  def test_dark_lighting_and_formula_fallback_are_token_driven() -> None:
      app = QApplication.instance() or QApplication([])
      app.setStyleSheet(build_qss("dark"))
      lighting = LightingDialog(LightSettings(), effective_theme="dark")
      preview = FormulaPreviewWidget("x^2")

      colors = lighting.rotation_widget._paint_colors
      dark = flatten_theme("dark")
      assert colors["card"] == dark["bg_elevated"]
      assert colors["label"] == dark["text_secondary"]
      assert colors["value"] == dark["accent_default"]
      assert preview._fallback_label.isVisibleTo(preview)
      assert "color:" not in preview._fallback_label.styleSheet()
      assert f"#formulaPreviewFallback {{ color: {dark['text_primary']}" in build_qss("dark")
  ```

  Restore the prior application stylesheet in `finally` to avoid cross-test leakage.

- [x] **Step 2: Run the integrated test before changing production code**

  Run: `uv run pytest tests/test_dark_theme_surfaces.py -q`

  Expected: PASS after Tasks 3.3 and 6.1. If it fails, fix the owning earlier implementation rather than weakening the assertions.

- [x] **Step 3: Render one offscreen image for visual sanity**

  Show both widgets under `QT_QPA_PLATFORM=offscreen`, process events, render them to `QImage`, and assert a representative center pixel is not the retired light card color `#f4f6f9` and that the fallback text region contains non-background pixels. Keep assertions broad enough for platform antialiasing.

- [x] **Step 4: Run the neighboring theme suite**

  Run: `uv run pytest tests/test_dark_theme_surfaces.py tests/test_lighting_dialog.py tests/test_math_input_theme.py tests/test_dialog_theming.py -q`

  Expected: PASS in a single process without stylesheet leakage.

- [x] **Step 5: Commit the integrated regression**

  ```bash
  git add tests/test_dark_theme_surfaces.py
  git commit -m "test: guard dark lighting and formula fallback surfaces"
  ```

<!-- openspec-task: 7.1 -->
### Task 4: Replace unsupported focus selectors with a real 2px Qt focus ring

**Files:**
- Modify: `ui/styles/base.qss.in`
- Modify: `tests/test_ui_tokens.py`
- Modify: `tests/test_ui_typography.py`
- Modify: `tests/snapshots/base-light.qss`
- Modify: `tests/snapshots/base-dark.qss`

**Interfaces:**
- Produces: Qt-supported `:focus` selectors only.
- Produces: transparent 2px default borders for `QPushButton` and `QToolButton`, replaced by a 2px accent border on focus.
- Produces: accent focus borders for text/combo/spin/edit controls that already have bordered chrome.

- [x] **Step 1: Add failing QSS focus contracts**

  In `tests/test_ui_tokens.py` add:

  ```python
  @pytest.mark.parametrize("theme", ["light", "dark"])
  def test_qss_uses_only_supported_visible_focus_rules(theme: str) -> None:
      qss = build_qss(theme)
      accent = flatten_theme(theme)["accent_default"]
      assert ":focus-visible" not in qss
      assert f"QPushButton:focus" in qss
      assert f"QToolButton:focus" in qss
      assert f"border: 2px solid {accent}" in qss
      assert "QLineEdit:focus" in qss
      assert "QComboBox:focus" in qss
  ```

  Add a typography assertion that button fixed sizes remain unchanged when focus is applied, using a 36px `QToolButton` rendered under both QSS themes.

- [x] **Step 2: Run tests and reproduce the unsupported/dropped rule**

  Run: `uv run pytest tests/test_ui_tokens.py tests/test_ui_typography.py -q`

  Expected: FAIL because QSS contains `:focus-visible` and its supported `:focus` rule resets the border to the default color.

- [x] **Step 3: Reserve button border space and add supported focus rules**

  Change the base controls to:

  ```css
  QPushButton { border: 2px solid transparent; }
  QToolButton { border: 2px solid transparent; }
  QPushButton:focus, QToolButton:focus { border: 2px solid $accent_default; }
  QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
  QPlainTextEdit:focus, QTextEdit:focus { border: 2px solid $accent_default; }
  ```

  Merge these declarations with existing blocks so hover/checked rules keep their background behavior. Remove the entire `:focus-visible` selector group and the rule that restores `border_default` on focus.

- [ ] **Step 4: Update snapshots and keyboard-smoke the main shell**

  Regenerate/review both QSS snapshots. Run the app in light and dark mode, press Tab across viewport toolbar, algebra controls, status controls, and dialog fields, and verify the ring is visible without changing fixed button dimensions.

- [x] **Step 5: Run QSS/UI tests and commit**

  Run: `uv run pytest tests/test_ui_tokens.py tests/test_ui_typography.py tests/test_ui_design_integration.py -q`

  Expected: PASS and no `focus-visible` text in generated QSS.

  Commit:

  ```bash
  git add ui/styles/base.qss.in tests/test_ui_tokens.py tests/test_ui_typography.py tests/snapshots/base-light.qss tests/snapshots/base-dark.qss
  git commit -m "fix: render supported Qt focus rings"
  ```

<!-- openspec-task: 7.2 -->
### Task 5: Make the 2D line flyout reachable by click and keyboard

**Files:**
- Modify: `ui/two_d_tools.py`
- Modify: `tests/test_2d_geometry_toolbar.py`

**Interfaces:**
- Produces: `_toggle_line_flyout()`, `_focus_line_button(index: int)`, and `_close_line_flyout(return_focus: bool = True)`.
- Flyout order is exactly line, segment, ray.
- Key contract: Up/Left previous; Down/Right next; Enter/Space activates; Escape closes and focuses `line_button`.

- [x] **Step 1: Add failing click and keyboard interaction tests**

  Extend `tests/test_2d_geometry_toolbar.py` with `QTest`:

  ```python
  def test_line_button_click_toggles_flyout(self) -> None:
      host, toolbar = shown_toolbar()
      QTest.mouseClick(toolbar.line_button, Qt.MouseButton.LeftButton)
      self.assertTrue(toolbar.line_flyout.isVisible())
      QTest.mouseClick(toolbar.line_button, Qt.MouseButton.LeftButton)
      self.assertFalse(toolbar.line_flyout.isVisible())


  def test_line_flyout_keyboard_cycle_select_and_escape(self) -> None:
      host, toolbar = shown_toolbar()
      events = []
      toolbar.tool_selected.connect(events.append)
      QTest.mouseClick(toolbar.line_button, Qt.MouseButton.LeftButton)
      self.assertTrue(toolbar.line_buttons["line"].hasFocus())
      QTest.keyClick(toolbar.line_buttons["line"], Qt.Key.Key_Down)
      self.assertTrue(toolbar.line_buttons["segment"].hasFocus())
      QTest.keyClick(toolbar.line_buttons["segment"], Qt.Key.Key_Return)
      self.assertEqual(events[-1], "segment")
      self.assertFalse(toolbar.line_flyout.isVisible())
      QTest.mouseClick(toolbar.line_button, Qt.MouseButton.LeftButton)
      QTest.keyClick(toolbar.line_buttons["line"], Qt.Key.Key_Escape)
      self.assertTrue(toolbar.line_button.hasFocus())
  ```

- [x] **Step 2: Run the toolbar test and reproduce mouse-hover-only access**

  Run: `uv run pytest tests/test_2d_geometry_toolbar.py -q`

  Expected: FAIL because clicking currently selects the abstract `line` tool and arrow/Escape keys are unhandled.

- [x] **Step 3: Separate flyout toggling from concrete tool activation**

  Replace `line_button.clicked.connect(lambda: self._toggle_tool("line"))` with `_toggle_line_flyout`. Showing positions/raises the flyout and focuses the first concrete button; closing hides it and optionally returns focus. Keep hover `Enter/Leave` calls to `_show_line_flyout()` and the delayed unhover close.

- [x] **Step 4: Handle keys in the existing event filter**

  For watched concrete buttons and `QEvent.KeyPress`, calculate the current index from `list(self.line_buttons.values())`:

  ```python
  if key in (Qt.Key.Key_Left, Qt.Key.Key_Up):
      buttons[(index - 1) % len(buttons)].setFocus()
      return True
  if key in (Qt.Key.Key_Right, Qt.Key.Key_Down):
      buttons[(index + 1) % len(buttons)].setFocus()
      return True
  if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
      buttons[index].click()
      return True
  if key == Qt.Key.Key_Escape:
      self._close_line_flyout()
      return True
  ```

  Set concrete buttons to `Qt.FocusPolicy.StrongFocus`. Preserve `_select_tool` toggle semantics and hover opening.

- [x] **Step 5: Run toolbar regressions and commit**

  Run: `uv run pytest tests/test_2d_geometry_toolbar.py tests/test_2d_geometry_interaction.py -q`

  Expected: PASS for hover, click, direction keys, selection, Escape, and existing tool signals.

  Commit:

  ```bash
  git add ui/two_d_tools.py tests/test_2d_geometry_toolbar.py
  git commit -m "feat: make line tool flyout keyboard accessible"
  ```

<!-- openspec-task: 8.1 -->
### Task 6: Make Escape cancel HistoryView rename without blur-save

**Files:**
- Modify: `ui/agent_web/src/components/HistoryView.tsx`
- Create: `ui/agent_web/src/components/HistoryView.test.tsx`

**Interfaces:**
- Produces: `cancelledRef` local to each `HistoryRow`.
- Enter and blur save a non-empty changed title; Escape restores the original title and emits no `rename_session` intent.

- [x] **Step 1: Add failing rename-path component tests**

  Create `HistoryView.test.tsx` with a single visible history item. Cover:

  ```typescript
  it("cancels rename on Escape without blur saving", async () => {
    renderView(onIntent);
    fireEvent.click(screen.getByRole("button", { name: "Rename Algebra" }));
    const input = screen.getByRole("textbox", { name: "Rename Algebra" });
    fireEvent.change(input, { target: { value: "Changed" } });
    fireEvent.keyDown(input, { key: "Escape" });
    expect(onIntent).not.toHaveBeenCalledWith(expect.objectContaining({ type: "rename_session" }));
    expect(screen.getByText("Algebra")).toBeInTheDocument();
  });
  ```

  Add Enter-save and blur-save tests that assert exactly one intent with the trimmed title.

- [x] **Step 2: Run the test and reproduce Escape triggering blur save**

  Run from `ui/agent_web`: `pnpm test -- src/components/HistoryView.test.tsx`

  Expected: FAIL because Escape only calls `setEditing(false)` and the input's blur invokes `save()`.

- [x] **Step 3: Add the cancellation guard and restore original draft**

  Import `useRef`. At edit start, reset `cancelledRef.current = false` and draft title to `item.title`. At the first line of `save()`:

  ```typescript
  if (cancelledRef.current) {
    cancelledRef.current = false;
    setTitle(item.title);
    return;
  }
  ```

  On Escape, set the flag before leaving edit mode, restore the title, and prevent default. Enter continues through `save()`.

- [x] **Step 4: Run the three rename paths**

  Run from `ui/agent_web`: `pnpm test -- src/components/HistoryView.test.tsx`

  Expected: PASS: Escape zero saves, Enter one save, blur one save.

- [x] **Step 5: Commit the rename fix**

  ```bash
  git add ui/agent_web/src/components/HistoryView.tsx ui/agent_web/src/components/HistoryView.test.tsx
  git commit -m "fix: cancel history rename on escape"
  ```

<!-- openspec-task: 8.2 -->
### Task 7: Close ModelSelector on Escape and outside interaction

**Files:**
- Modify: `ui/agent_web/src/components/ModelSelector.tsx`
- Modify: `ui/agent_web/src/components/ModelSelector.test.tsx`

**Interfaces:**
- Produces: a root `ref`, document `mousedown`/`keydown` cleanup lifecycle, trigger `aria-haspopup="listbox"`, and `aria-expanded={open}`.
- Preserves: selection emits `change_model` and closes the popover.

- [x] **Step 1: Add failing dismissal and aria tests**

  Extend `ModelSelector.test.tsx`:

  ```typescript
  it.each(["Escape", "outside"])("closes through %s", (path) => {
    renderSelector();
    const trigger = screen.getByRole("button", { name: "模型" });
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    if (path === "Escape") fireEvent.keyDown(document, { key: "Escape" });
    else fireEvent.mouseDown(document.body);
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    expect(trigger).toHaveAttribute("aria-expanded", "false");
  });
  ```

  Keep/add a selection-path test as the third close route.

- [x] **Step 2: Run the focused test and reproduce the stuck popover**

  Run from `ui/agent_web`: `pnpm test -- src/components/ModelSelector.test.tsx`

  Expected: FAIL because only selection and trigger clicks currently close it.

- [x] **Step 3: Reuse the AttachmentActions listener pattern**

  Import `useEffect`/`useRef`, attach a root ref, and install document listeners once:

  ```typescript
  useEffect(() => {
    const closeOnOutside = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", closeOnOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("mousedown", closeOnOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, []);
  ```

- [x] **Step 4: Expose trigger state without changing selection semantics**

  Add `ref={rootRef}` to the wrapper and `aria-haspopup="listbox" aria-expanded={open}` to the trigger. Keep popover role `menu` unless a separate accessibility refactor changes row roles together; the requested state must be accurate.

- [x] **Step 5: Run component tests and commit**

  Run from `ui/agent_web`: `pnpm test -- src/components/ModelSelector.test.tsx src/components/Composer.test.tsx`

  Expected: PASS for Escape, outside pointer, selection, and aria state.

  Commit:

  ```bash
  git add ui/agent_web/src/components/ModelSelector.tsx ui/agent_web/src/components/ModelSelector.test.tsx
  git commit -m "fix: add model picker dismissal paths"
  ```

<!-- openspec-task: 8.3 -->
### Task 8: Enforce the Agent Web 11px text and 28px target floors

**Files:**
- Modify: `ui/agent_web/src/styles/layout.css`
- Modify: `ui/agent_web/src/styles/layout.test.ts`
- Modify: `ui/agent_web/src/components/ContextRing.tsx`
- Generate: `ui/agent_web/dist/`

**Interfaces:**
- Produces: at least 11px for context ring, turn actions, model details, capability headings/descriptions, thinking/progress metadata, and settings context labels.
- Produces: at least 28×28px for attachment buttons, session-tab close buttons, turn-action buttons, history row actions, and context ring.

- [x] **Step 1: Add failing floor assertions to the stylesheet test**

  Extend `layout.test.ts` with a table-driven contract:

  ```typescript
  const textFloor = [
    ".turn-actions button",
    ".model-details",
    ".capability-group > span",
    ".capability-group button small",
    ".thinking-toggle small, .plan-status-toggle small",
    ".progress-log small",
    ".settings-context-grid label",
    ".context-ring",
  ];
  for (const selector of textFloor) expect(block(selector)).toContain("font-size: 11px");

  const targetFloor = [
    ".session-tab-close",
    ".turn-actions button",
    ".attachment-actions button",
    ".history-row-actions button",
    ".context-ring",
  ];
  for (const selector of targetFloor) {
    expect(block(selector)).toContain("width: 28px");
    expect(block(selector)).toContain("height: 28px");
  }
  ```

- [x] **Step 2: Run the test and enumerate every below-floor declaration**

  Run from `ui/agent_web`: `pnpm test -- src/styles/layout.test.ts`

  Expected: FAIL on current 8–10px labels and 22–26px targets.

- [x] **Step 3: Raise text values and target metrics exactly to the floor**

  Update the named selectors to 11px. Set `.session-tab-close`, `.turn-actions button`, `.attachment-actions button`, `.history-row-actions button`, and `.context-ring` to `width: 28px; height: 28px`; adjust margins/flex-basis so the composer and tabs do not overflow at 360px. Keep icons at 13–15px.

  For `ContextRing`, retain the existing semantic text span and percentage clamp; no SVG recalculation is needed in this implementation because the percentage is HTML text, not SVG text. Add `aria-hidden="true"` to the inner visual span while keeping the outer computed `aria-label`.

- [ ] **Step 4: Rebuild and smoke at 360px/720px widths**

  Run from `ui/agent_web`: `pnpm build`. In browser tests or the embedded sidebar, verify the composer controls do not wrap out of bounds at 360px and the 620px reading column remains centered at 720px.

- [x] **Step 5: Run frontend and packaging regressions, then commit**

  Run:

  ```powershell
  Push-Location ui/agent_web
  pnpm test
  pnpm build
  Pop-Location
  uv run pytest tests/test_agent_web_packaging.py -q
  ```

  Expected: PASS with no named text below 11px or target below 28px.

  Commit:

  ```bash
  git add ui/agent_web/src/styles/layout.css ui/agent_web/src/styles/layout.test.ts ui/agent_web/src/components/ContextRing.tsx ui/agent_web/dist
  git commit -m "fix: enforce agent web interaction floors"
  ```
