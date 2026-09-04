# Dark Theme and Typography Improvements — Foundations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the font-stack foundation, make native window chrome follow the effective theme, and introduce token-generated MathInput CSS variables with the formula list as the first migrated WebView.

**Architecture:** `design/tokens.json` remains the authored source for typography and colors. Python exposes validated font and theme helpers to Qt, `ui.native_chrome` isolates optional Windows DWM behavior behind a no-throw API, and `MathInputWidget.theme_tokens` converts the same theme leaves into `--mi-*` variables with light literal fallbacks for direct HTML debugging.

**Tech Stack:** Python 3.11, PySide6 6.8, Qt Style Sheets, Qt WebEngine, Windows DWM through `ctypes`, HTML/CSS, Node.js, pnpm/Vite, pytest, Vitest.

**Spec:** `openspec/changes/improve-dark-theme-and-typography/design.md`, `openspec/changes/improve-dark-theme-and-typography/tasks.md`, `openspec/changes/improve-dark-theme-and-typography/specs/ui-design-system/spec.md`, and `openspec/changes/improve-dark-theme-and-typography/specs/app-shell/spec.md`

## Global Constraints

- Do not add a framework, runtime dependency, remote asset, or new Agent protocol event.
- Keep the authored font sizes at exactly 11/12/13/15px; the application body font is 12 pixels, never 12 points.
- The native title-bar feature is optional platform integration: unsupported platforms, missing DWM APIs, and non-zero HRESULT values must leave in-application theming operational and must not raise.
- Theme switches must update loaded WebViews without navigation or reload; WebViews created later must receive the effective theme at document creation.
- MathInput HTML must remain readable when opened directly, so every `var(--mi-*, ...)` use keeps the approved light literal fallback.
- Preserve the explicit non-goal: do not add screen-edge clamping to the frameless formula editor popup.
- Keep commits task-scoped. The working tree may contain unrelated user changes; stage only the files listed by the current task.

---

<!-- openspec-task: 1.1 -->
### Task 1: Validate and expose the application font-family stack

**Files:**
- Modify: `design/tokens.json`
- Modify: `ui/tokens.py`
- Modify: `tests/test_ui_tokens.py`

**Interfaces:**
- Produces: `font_family_stack(tokens: Mapping[str, object] | None = None) -> list[str]`.
- Preserves: `load_tokens()`, `flatten_theme()`, and `build_qss()` behavior for all existing scalar tokens.
- Produces token value: `font.family_stack = ["Segoe UI", "Microsoft YaHei UI", "PingFang SC", "Noto Sans CJK SC"]`.

- [x] **Step 1: Add failing validation and accessor tests**

  Extend `tests/test_ui_tokens.py` with positive and malformed cases:

  ```python
  from ui.tokens import font_family_stack


  def test_font_family_stack_preserves_declared_fallback_order() -> None:
      assert font_family_stack() == [
          "Segoe UI",
          "Microsoft YaHei UI",
          "PingFang SC",
          "Noto Sans CJK SC",
      ]


  @pytest.mark.parametrize(
      "value",
      [[], ["Segoe UI", ""], ["Segoe UI", 7], "Segoe UI"],
  )
  def test_font_family_stack_must_be_a_non_empty_string_list(tmp_path, value) -> None:
      data = deepcopy(load_tokens())
      data["font"]["family_stack"] = value
      path = tmp_path / "tokens.json"
      path.write_text(json.dumps(data), encoding="utf-8")
      with pytest.raises(TokenError, match=r"font\.family_stack"):
          load_tokens(path)
  ```

- [x] **Step 2: Run the focused test and verify the missing contract**

  Run: `uv run pytest tests/test_ui_tokens.py -q`

  Expected: FAIL because `font_family_stack` is not exported and `font.family_stack` is absent.

- [x] **Step 3: Add the token and exact validation rule**

  Change the `font` object in `design/tokens.json` to:

  ```json
  "font": {
    "family_default": "Segoe UI",
    "family_stack": ["Segoe UI", "Microsoft YaHei UI", "PingFang SC", "Noto Sans CJK SC"],
    "size": {"caption": 11, "body": 12, "subtitle": 13, "title": 15}
  }
  ```

  In `_validate`, reject non-lists, empty lists, non-string entries, and blank entries with the path `font.family_stack` in the error. Keep `family_default` for compatibility with existing callers.

- [x] **Step 4: Implement the accessor without leaking a list into QSS substitution**

  Add the public helper and remove the list-valued token before flattening common scalar values:

  ```python
  def font_family_stack(
      tokens: Mapping[str, object] | None = None,
  ) -> list[str]:
      source = dict(tokens or load_tokens())
      _validate(source)
      font = source["font"]
      assert isinstance(font, Mapping)
      return [str(name) for name in font["family_stack"]]


  def _common_scalar_tokens(source: Mapping[str, object]) -> dict[str, object]:
      common = {
          key: value
          for key, value in source.items()
          if key not in {"$schema", "$comment", "themes"}
      }
      font = dict(common["font"])
      font.pop("family_stack", None)
      common["font"] = font
      return common
  ```

  Make `flatten_theme()` call `_flatten(_common_scalar_tokens(source))`, preserving its `dict[str, str | int]` return contract.

- [x] **Step 5: Run token regression tests and commit**

  Run: `uv run pytest tests/test_ui_tokens.py -q`

  Expected: PASS, including the existing light/dark leaf and QSS snapshot tests.

  Commit:

  ```bash
  git add design/tokens.json ui/tokens.py tests/test_ui_tokens.py
  git commit -m "feat: add application font family stack token"
  ```

<!-- openspec-task: 1.2 -->
### Task 2: Apply a 12-pixel antialiased fallback font to QApplication

**Files:**
- Modify: `main.py`
- Modify: `tests/test_ui_typography.py`

**Interfaces:**
- Consumes: `font_family_stack()` and `load_tokens()` from Task 1.
- Produces: `build_application_font() -> QFont` for construction and focused testing.
- `main()` applies the returned font before constructing `MainWindow`.

- [x] **Step 1: Add a failing application-font test**

  Extend `tests/test_ui_typography.py`:

  ```python
  from main import build_application_font


  def test_application_font_uses_pixel_size_and_chinese_fallbacks() -> None:
      font = build_application_font()
      assert font.pixelSize() == 12
      assert font.pointSize() == -1
      assert font.families()[:3] == [
          "Segoe UI",
          "Microsoft YaHei UI",
          "PingFang SC",
      ]
      assert font.styleStrategy() & QFont.StyleStrategy.PreferAntialias
  ```

- [x] **Step 2: Run the test and confirm the old point-size behavior**

  Run: `uv run pytest tests/test_ui_typography.py -q`

  Expected: FAIL because `build_application_font` does not exist and `main()` still constructs `QFont(family, 12)` as a point size.

- [x] **Step 3: Build the font from tokens**

  Replace the direct `QFont` constructor with a pure helper:

  ```python
  from ui.tokens import font_family_stack, load_tokens


  def build_application_font() -> QFont:
      tokens = load_tokens()
      font_tokens = tokens["font"]
      font = QFont()
      font.setFamilies(font_family_stack(tokens))
      font.setPixelSize(int(font_tokens["size"]["body"]))
      font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
      return font
  ```

  In `main()`, call `app.setFont(build_application_font())` before `MainWindow(...)`.

- [x] **Step 4: Assert QApplication receives the same font object semantics**

  Add a Qt-level assertion to the same test file:

  ```python
  def test_qapplication_accepts_the_token_font() -> None:
      app = QApplication.instance() or QApplication([])
      original = app.font()
      try:
          app.setFont(build_application_font())
          assert app.font().pixelSize() == 12
          assert "Microsoft YaHei UI" in app.font().families()
      finally:
          app.setFont(original)
  ```

- [x] **Step 5: Run typography and startup helpers, then commit**

  Run: `uv run pytest tests/test_ui_typography.py tests/test_theme_mode.py -q`

  Expected: PASS without creating a real main-window event loop.

  Commit:

  ```bash
  git add main.py tests/test_ui_typography.py
  git commit -m "fix: apply token font in pixels"
  ```

<!-- openspec-task: 1.3 -->
### Task 3: Cover every Qt chrome category with token font sizes

**Files:**
- Modify: `ui/styles/base.qss.in`
- Modify: `tests/test_ui_typography.py`
- Modify: `tests/test_ui_tokens.py`
- Modify: `tests/snapshots/base-light.qss`
- Modify: `tests/snapshots/base-dark.qss`

**Interfaces:**
- Consumes: `${size_caption}` and `${size_body}` QSS substitutions.
- Produces caption-size rules for tool buttons/tooltips/status controls and body-size rules for menus, combo popups, and item views.

- [ ] **Step 1: Add exact selector and size assertions**

  Extend `tests/test_ui_typography.py`:

  ```python
  @pytest.mark.parametrize("theme", ["light", "dark"])
  def test_unstyled_qt_chrome_uses_token_pixel_sizes(theme: str) -> None:
      qss = build_qss(theme)
      assert "QToolButton {" in qss and "font-size: 11px" in qss
      assert "QMenu {" in qss and "font-size: 12px" in qss
      assert "QToolTip {" in qss and "font-size: 11px" in qss
      assert "QComboBox QAbstractItemView" in qss
      assert "QTreeView, QListView, QListWidget" in qss
      assert "#appStatusBar QToolButton" in qss
  ```

  Add a status-specific block assertion using the existing `_block_for_selector` helper in `tests/test_ui_tokens.py`:

  ```python
  def test_status_bar_labels_and_buttons_share_caption_size() -> None:
      qss = build_qss("light")
      assert "font-size: 11px" in _block_for_selector(qss, "#appStatusBar QLabel")
      assert "font-size: 11px" in _block_for_selector(qss, "#appStatusBar QToolButton")
  ```

- [ ] **Step 2: Run the focused tests and capture missing selectors**

  Run: `uv run pytest tests/test_ui_typography.py tests/test_ui_tokens.py -q`

  Expected: FAIL for the missing global font declarations and stale QSS snapshots.

- [ ] **Step 3: Add the token-size QSS rules**

  Add or extend stable selector blocks in `ui/styles/base.qss.in`:

  ```css
  QToolButton { font-size: ${size_caption}px; }
  QMenu { font-size: ${size_body}px; }
  QToolTip { font-size: ${size_caption}px; }
  QComboBox QAbstractItemView { font-size: ${size_body}px; }
  QTreeView, QListView, QListWidget { font-size: ${size_body}px; }
  #appStatusBar QToolButton { font-size: ${size_caption}px; }
  ```

  Merge declarations into existing selector blocks where present; do not create duplicate blocks whose cascade order changes hover, border, or minimum-size behavior.

- [ ] **Step 4: Review and update both generated QSS snapshots**

  Generate the two reviewed outputs:

  ```powershell
  uv run python -c "from pathlib import Path; from ui.tokens import build_qss; p=Path('tests/snapshots'); (p/'base-light.qss').write_text(build_qss('light'), encoding='utf-8'); (p/'base-dark.qss').write_text(build_qss('dark'), encoding='utf-8')"
  ```

  Inspect the diff and confirm only the intended token font declarations changed.

- [ ] **Step 5: Run QSS regressions and commit**

  Run: `uv run pytest tests/test_ui_typography.py tests/test_ui_tokens.py tests/test_app_status_bar.py -q`

  Expected: PASS in both themes with all snapshot substitutions resolved.

  Commit:

  ```bash
  git add ui/styles/base.qss.in tests/test_ui_typography.py tests/test_ui_tokens.py tests/snapshots/base-light.qss tests/snapshots/base-dark.qss
  git commit -m "style: normalize Qt chrome font sizes"
  ```

<!-- openspec-task: 1.4 -->
### Task 4: Move Agent tool-page headings onto the shared section style

**Files:**
- Modify: `ui/agent_sidebar.py`
- Modify: `tests/test_ui_typography.py`

**Interfaces:**
- Consumes: the existing `#sectionHeader` rule in `ui/styles/base.qss.in`.
- Produces: four Agent tool-page title labels with `objectName == "sectionHeader"` and no inline font declaration.

- [ ] **Step 1: Add a failing source and construction contract**

  Extend `tests/test_ui_typography.py`:

  ```python
  def test_agent_sidebar_tool_titles_use_section_header_tokens() -> None:
      source = (_source_path() / "ui" / "agent_sidebar.py").read_text(encoding="utf-8")
      assert "font-size: 14px" not in source
      assert source.count('setObjectName("sectionHeader")') >= 4
  ```

- [ ] **Step 2: Run the test and verify all four inline declarations are found**

  Run: `uv run pytest tests/test_ui_typography.py::test_agent_sidebar_tool_titles_use_section_header_tokens -q`

  Expected: FAIL because history, skills, memory, and rules each set `font-size: 14px` inline.

- [ ] **Step 3: Assign the shared object name at each construction site**

  For each title label in `_build_history_page`, `_build_skills_page`, `_build_memory_page`, and `_build_rules_page`, use:

  ```python
  title = QLabel("历史记录", page)
  title.setObjectName("sectionHeader")
  column.addWidget(title)
  ```

  Preserve each page's current Chinese text; remove only the four `setStyleSheet("font-weight: 700; font-size: 14px;")` calls.

- [ ] **Step 4: Run nearby sidebar and typography coverage**

  Run: `uv run pytest tests/test_ui_typography.py tests/test_sidebar_visibility.py tests/test_agent_panel_migration.py -q`

  Expected: PASS with no navigation or visibility behavior changes.

- [ ] **Step 5: Commit the heading cleanup**

  ```bash
  git add ui/agent_sidebar.py tests/test_ui_typography.py
  git commit -m "style: reuse token heading style in agent sidebar"
  ```

<!-- openspec-task: 1.5 -->
### Task 5: Generate the quoted bilingual Agent Web font stack

**Files:**
- Modify: `ui/agent_web/scripts/gen-theme.mjs`
- Modify: `ui/agent_web/scripts/gen-theme.test.mjs`
- Modify: `ui/agent_web/src/styles/theme.test.ts`
- Generate: `ui/agent_web/src/styles/theme.css`
- Generate: `ui/agent_web/dist/`

**Interfaces:**
- Consumes: `font.family_stack` added in Task 1.
- Produces in both theme branches: `--agent-font-family: "Segoe UI", "Microsoft YaHei UI", "PingFang SC", sans-serif;`.
- Preserves: the existing `pnpm prebuild -> theme:generate -> vite build` chain.

- [ ] **Step 1: Add failing generator and CSS parity assertions**

  In `scripts/gen-theme.test.mjs`, assert generated CSS contains the exact stack twice:

  ```javascript
  const stack = '--agent-font-family: "Segoe UI", "Microsoft YaHei UI", "PingFang SC", sans-serif;';
  assert.equal(generateThemeCss(tokens).split(stack).length - 1, 2);
  ```

  In `src/styles/theme.test.ts`, add:

  ```typescript
  it("uses the quoted Latin and Simplified Chinese font stack in both themes", () => {
    const css = themeCss();
    const stack = '--agent-font-family: "Segoe UI", "Microsoft YaHei UI", "PingFang SC", sans-serif;';
    expect(css.split(stack)).toHaveLength(3);
  });
  ```

- [ ] **Step 2: Run the theme tests and confirm the single-family output**

  Run from `ui/agent_web`: `node --test scripts/gen-theme.test.mjs && pnpm test -- src/styles/theme.test.ts`

  Expected: FAIL because the generator currently emits only `Segoe UI` and appends another `sans-serif` in `body`.

- [ ] **Step 3: Serialize the Web subset of the token stack safely**

  Add a helper that quotes the first three approved UI families and appends the generic family exactly once:

  ```javascript
  function webFontStack(tokens) {
    const declared = Array.isArray(tokens.font?.family_stack)
      ? tokens.font.family_stack.slice(0, 3)
      : ["Segoe UI", "Microsoft YaHei UI", "PingFang SC"];
    return `${declared.map((name) => JSON.stringify(name)).join(", ")}, sans-serif`;
  }
  ```

  Make `declarations()` emit `--agent-font-family: ${webFontStack(tokens)};`, update `FALLBACK.font.family_stack`, and change the body rule to `font-family: var(--agent-font-family);` so `sans-serif` is not duplicated.

- [ ] **Step 4: Rebuild committed source and production assets**

  Run from `ui/agent_web`: `pnpm build`

  Expected: `src/styles/theme.css` and the current hashed CSS asset under `dist/assets/` contain the quoted stack; `dist/manifest.json` points to the rebuilt asset.

- [ ] **Step 5: Run frontend and packaging checks, then commit**

  Run from the repository root:

  ```powershell
  Push-Location ui/agent_web
  pnpm test -- src/styles/theme.test.ts
  pnpm build
  Pop-Location
  uv run pytest tests/test_agent_web_assets.py tests/test_agent_web_packaging.py -q
  ```

  Expected: PASS with no network assets and no stale manifest entries.

  Commit:

  ```bash
  git add ui/agent_web/scripts/gen-theme.mjs ui/agent_web/scripts/gen-theme.test.mjs ui/agent_web/src/styles/theme.test.ts ui/agent_web/src/styles/theme.css ui/agent_web/dist
  git commit -m "style: add bilingual agent web font stack"
  ```

<!-- openspec-task: 2.1 -->
### Task 6: Isolate Windows native title-bar theming behind a safe tracker

**Files:**
- Create: `ui/native_chrome.py`
- Create: `tests/test_native_chrome.py`
- Modify: `main.py`

**Interfaces:**
- Produces: `apply_native_titlebar_theme(window: QWidget, effective_theme: str) -> bool`.
- Produces: `install_titlebar_tracker(app: QApplication) -> None`.
- Consumes application property: `math3d_effective_theme`, whose value is `light` or `dark`.

- [ ] **Step 1: Write failing DWM, fallback, and lifecycle tests**

  Create `tests/test_native_chrome.py` with a fake DWM callable:

  ```python
  def test_dwm_receives_dark_and_light_integer_values(monkeypatch) -> None:
      calls = []

      class DwmApi:
          def DwmSetWindowAttribute(self, hwnd, attribute, value, size):
              calls.append((int(hwnd), attribute, value._obj.value, size))
              return 0

      monkeypatch.setattr(native_chrome.sys, "platform", "win32")
      monkeypatch.setattr(native_chrome.ctypes, "windll", SimpleNamespace(dwmapi=DwmApi()), raising=False)
      window = QWidget()
      assert apply_native_titlebar_theme(window, "dark") is True
      assert apply_native_titlebar_theme(window, "light") is True
      assert [call[2] for call in calls] == [1, 0]
      assert all(call[1] == 20 for call in calls)
  ```

  Also cover `sys.platform = "linux"`, a missing `windll`, a raised `OSError`, and a non-zero HRESULT; all return `False` without raising. Add an event-filter test that sends `QEvent.Show` and `QEvent.WinIdChange` to a top-level widget after setting the app property.

- [ ] **Step 2: Run the focused test and confirm the module is missing**

  Run: `uv run pytest tests/test_native_chrome.py -q`

  Expected: FAIL during import because `ui.native_chrome` does not exist.

- [ ] **Step 3: Implement the no-throw DWM adapter**

  Create `ui/native_chrome.py` with the exact attribute and value size:

  ```python
  DWMWA_USE_IMMERSIVE_DARK_MODE = 20


  def apply_native_titlebar_theme(window: QWidget, effective_theme: str) -> bool:
      if sys.platform != "win32" or effective_theme not in ("light", "dark"):
          return False
      try:
          enabled = ctypes.c_int(1 if effective_theme == "dark" else 0)
          result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
              int(window.winId()),
              DWMWA_USE_IMMERSIVE_DARK_MODE,
              ctypes.byref(enabled),
              ctypes.sizeof(enabled),
          )
      except (AttributeError, OSError, TypeError, ValueError):
          return False
      return result == 0
  ```

- [ ] **Step 4: Install one application-level lifecycle tracker**

  Implement a private `QObject` event filter owned by the application. On `Show` or `WinIdChange`, apply only to `QWidget` top-level windows using the app property:

  ```python
  class _TitlebarTracker(QObject):
      def eventFilter(self, watched: QObject, event: QEvent) -> bool:
          if (
              event.type() in (QEvent.Type.Show, QEvent.Type.WinIdChange)
              and isinstance(watched, QWidget)
              and watched.isWindow()
          ):
              app = QApplication.instance()
              theme = app.property("math3d_effective_theme") if app else None
              if theme in ("light", "dark"):
                  apply_native_titlebar_theme(watched, theme)
          return False
  ```

  `install_titlebar_tracker(app)` must be idempotent by storing the tracker on an app property or Python attribute. Call it in `main()` immediately after creating `QApplication`.

- [ ] **Step 5: Run native and startup tests, then commit**

  Run: `uv run pytest tests/test_native_chrome.py tests/test_theme_mode.py -q`

  Expected: PASS on Windows and offscreen CI without requiring a successful real DWM call.

  Commit:

  ```bash
  git add ui/native_chrome.py tests/test_native_chrome.py main.py
  git commit -m "feat: track native title bar theme"
  ```

<!-- openspec-task: 2.2 -->
### Task 7: Apply native chrome during every main-window theme update

**Files:**
- Modify: `ui/designer_window.py`
- Modify: `tests/test_native_chrome.py`

**Interfaces:**
- Consumes: `apply_native_titlebar_theme()` from Task 6.
- Produces application property: `math3d_effective_theme` updated in the same `_apply_style()` pass as QSS.
- Applies immediately to every existing `QApplication.topLevelWidgets()` entry; the tracker handles windows shown later.

- [ ] **Step 1: Add a failing existing-window propagation test**

  Extend `tests/test_native_chrome.py`:

  ```python
  def test_apply_style_updates_app_property_and_all_top_level_windows(monkeypatch) -> None:
      app = QApplication.instance() or QApplication([])
      shell = QWidget()
      dialog = QDialog()
      seen = []
      monkeypatch.setattr(QApplication, "topLevelWidgets", staticmethod(lambda: [shell, dialog]))
      monkeypatch.setattr("ui.designer_window.apply_native_titlebar_theme", lambda widget, theme: seen.append((widget, theme)) or True)

      window = object.__new__(MainWindow)
      window.window = shell
      window.effective_theme = "dark"
      MainWindow._apply_style(window)

      assert app.property("math3d_effective_theme") == "dark"
      assert seen == [(shell, "dark"), (dialog, "dark")]
  ```

  Give the lightweight object only the optional attributes `_apply_style()` reads, or rely on its existing `getattr` guards.

- [ ] **Step 2: Run the test and observe missing propagation**

  Run: `uv run pytest tests/test_native_chrome.py::test_apply_style_updates_app_property_and_all_top_level_windows -q`

  Expected: FAIL because `_apply_style()` currently updates only QSS and in-application surfaces.

- [ ] **Step 3: Import and apply native chrome at the end of `_apply_style()`**

  Add a module import next to the other UI helpers, then append this after the effective theme is known:

  ```python
  application = QApplication.instance()
  if application is not None:
      application.setProperty("math3d_effective_theme", effective_theme)
      for top_level in application.topLevelWidgets():
          apply_native_titlebar_theme(top_level, effective_theme)
  ```

  Keep this in the same method invocation as `self.window.setStyleSheet(...)`; do not add calls at individual Agent settings, lighting, or memory dialog construction sites.

- [ ] **Step 4: Cover repeated light/dark cycles without duplicate state**

  Add a second assertion that calls `_apply_style()` with `dark`, then `light`, and verifies each top-level window receives `["dark", "light"]` in order. The app property must finish as `light`.

- [ ] **Step 5: Run theme propagation regressions and commit**

  Run: `uv run pytest tests/test_native_chrome.py tests/test_theme_mode.py tests/test_dialog_theming.py -q`

  Expected: PASS; unsupported native chrome remains a silent no-op.

  Commit:

  ```bash
  git add ui/designer_window.py tests/test_native_chrome.py
  git commit -m "feat: sync top level chrome with theme"
  ```

<!-- openspec-task: 3.1 -->
### Task 8: Generate MathInput light and dark CSS variables from tokens

**Files:**
- Create: `MathInputWidget/theme_tokens.py`
- Create: `tests/test_math_input_theme.py`

**Interfaces:**
- Produces: `math_input_theme_css(tokens: Mapping[str, object] | None = None) -> str`.
- Produces: `math_input_theme_script(theme: str, tokens: Mapping[str, object] | None = None) -> str`.
- Variable branches: `:root` for light and `[data-theme="dark"]` for dark, with identical `--mi-*` names.

- [ ] **Step 1: Add failing variable coverage and token parity tests**

  Create `tests/test_math_input_theme.py`:

  ```python
  EXPECTED_VARIABLES = {
      "--mi-bg-panel",
      "--mi-text-primary",
      "--mi-row-bg",
      "--mi-border",
      "--mi-selected-bg",
      "--mi-selected-border",
      "--mi-btn-hover",
      "--mi-editing-bg",
      "--mi-editing-border",
      "--mi-focus",
      "--mi-toolbar-bg",
      "--mi-toolbar-accent",
      "--mi-toolbar-hover",
      "--mi-layer-fallback",
  }


  def test_math_input_css_has_complete_matching_theme_branches() -> None:
      css = math_input_theme_css()
      light, dark = css.split('[data-theme="dark"]', 1)
      assert set(re.findall(r"--mi-[a-z-]+", light)) == EXPECTED_VARIABLES
      assert set(re.findall(r"--mi-[a-z-]+", dark)) == EXPECTED_VARIABLES


  def test_math_input_css_uses_design_token_values() -> None:
      css = math_input_theme_css()
      assert f"--mi-bg-panel: {flatten_theme('light')['bg_panel']}" in css
      assert f"--mi-bg-panel: {flatten_theme('dark')['bg_panel']}" in css
      assert f"--mi-focus: {flatten_theme('dark')['accent_default']}" in css
  ```

- [ ] **Step 2: Run the focused test and verify the module is missing**

  Run: `uv run pytest tests/test_math_input_theme.py -q`

  Expected: FAIL during import because `MathInputWidget.theme_tokens` does not exist.

- [ ] **Step 3: Define the semantic variable map and approved constants**

  Implement one mapping for token-backed values and one per-theme constant mapping:

  ```python
  TOKEN_VARIABLES = {
      "bg-panel": "bg_panel",
      "text-primary": "text_primary",
      "row-bg": "bg_elevated",
      "border": "border_default",
      "selected-bg": "accent_soft_bg",
      "selected-border": "accent_default",
      "btn-hover": "bg_elevated",
      "editing-bg": "bg_overlay",
      "focus": "accent_default",
      "toolbar-accent": "accent_default",
      "layer-fallback": "accent_default",
  }
  CONSTANTS = {
      "light": {"editing-border": "#e59b00", "toolbar-bg": "#2c2e2f", "toolbar-hover": "#eeeeee"},
      "dark": {"editing-border": "#e59b00", "toolbar-bg": "#2c2e2f", "toolbar-hover": "#3a3d40"},
  }
  ```

- [ ] **Step 4: Emit deterministic CSS and a DocumentCreation-safe script**

  Generate variables in sorted order so snapshots and tests are stable. The script must create or replace a single style element and set the dataset before page code runs:

  ```python
  def math_input_theme_script(theme: str, tokens=None) -> str:
      if theme not in ("light", "dark"):
          raise TokenError(f"unknown theme: {theme}")
      css = json.dumps(math_input_theme_css(tokens))
      selected = json.dumps(theme)
      return (
          "(() => {"
          "const apply = () => {"
          "const root = document.documentElement; if (!root) return false;"
          "let style = document.getElementById('mi-theme-vars');"
          "if (!style) { style = document.createElement('style'); style.id = 'mi-theme-vars'; root.appendChild(style); }"
          f"style.textContent = {css};"
          f"root.dataset.theme = {selected}; return true;"
          "};"
          "if (!apply()) { const observer = new MutationObserver(() => { if (apply()) observer.disconnect(); }); observer.observe(document, { childList: true, subtree: true }); }"
          "})();"
      )
  ```

  Add tests that the script contains `mi-theme-vars`, `dataset.theme`, and JSON-escaped CSS, and that an invalid theme raises `TokenError`.

- [ ] **Step 5: Run the generator tests and commit**

  Run: `uv run pytest tests/test_math_input_theme.py -q`

  Expected: PASS with identical variable names in both branches.

  Commit:

  ```bash
  git add MathInputWidget/theme_tokens.py tests/test_math_input_theme.py
  git commit -m "feat: generate MathInput theme variables"
  ```

<!-- openspec-task: 3.2 -->
### Task 9: Migrate the formula list to token variables with light fallbacks

**Files:**
- Modify: `MathInputWidget/formula_list.html`
- Modify: `tests/test_math_input_theme.py`

**Interfaces:**
- Consumes: the `--mi-*` variable set from Task 8.
- Preserves: all existing FormulaList JavaScript bridge names, row states, selection behavior, and direct-file usability.
- Produces: token-backed row, hover, selection, border, editing, toolbar, and MathLive highlight colors.

- [ ] **Step 1: Add a failing HTML migration contract**

  Extend `tests/test_math_input_theme.py`:

  ```python
  def test_formula_list_uses_variables_with_light_fallbacks() -> None:
      html = (ROOT / "MathInputWidget" / "formula_list.html").read_text(encoding="utf-8")
      required = {
          "var(--mi-bg-panel, #ffffff)",
          "var(--mi-text-primary, #1f2937)",
          "var(--mi-row-bg, #f9fafb)",
          "var(--mi-border, #cfd8e1)",
          "var(--mi-selected-bg, #eaf2fd)",
          "var(--mi-selected-border, #8ab4f8)",
          "var(--mi-btn-hover, #eef2f5)",
          "var(--mi-editing-bg, #fffdf4)",
          "var(--mi-focus, #2f7ebd)",
      }
      assert required <= {match.group(0) for match in re.finditer(r"var\(--mi-[^)]+\)", html)}
      assert "--selection-background-color: var(--mi-selected-bg" in html
      assert "--contains-highlight-background-color:" in html
  ```

  Add a regex guard that rejects declarations such as `background: #ffffff`, `color: #1f2937`, or `border-color: #cfd8e1` outside a `var()` fallback.

- [ ] **Step 2: Run the focused HTML test and enumerate hardcoded declarations**

  Run: `uv run pytest tests/test_math_input_theme.py -q`

  Expected: FAIL and identify the current light-only row, hover, selection, border, alert, and MathLive variable declarations.

- [ ] **Step 3: Replace each authored color declaration with the semantic variable**

  Use the approved fallbacks directly in CSS, for example:

  ```css
  body { background: var(--mi-bg-panel, #ffffff); color: var(--mi-text-primary, #1f2937); }
  .formula-row { background: var(--mi-row-bg, #f9fafb); border-color: var(--mi-border, #cfd8e1); }
  .formula-row:hover { background: var(--mi-btn-hover, #eef2f5); }
  .formula-row.selected { background: var(--mi-selected-bg, #eaf2fd); border-color: var(--mi-selected-border, #8ab4f8); }
  .formula-row.editing { background: var(--mi-editing-bg, #fffdf4); border-color: var(--mi-editing-border, #e59b00); }
  math-field {
    --selection-background-color: var(--mi-selected-bg, #eaf2fd);
    --contains-highlight-background-color: var(--mi-selected-bg, #eaf2fd);
    --caret-color: var(--mi-focus, #2f7ebd);
  }
  ```

  Apply the same treatment to visibility buttons, settings buttons, empty/error hint bars, and all border states. Do not rename JavaScript IDs, callbacks, aria attributes, or QWebChannel bridge functions.

- [ ] **Step 4: Verify the direct-open light fallback and dark variable branch**

  Add assertions that every variable use has a second argument and that `theme_tokens.math_input_theme_css()` supplies every referenced variable. Open `MathInputWidget/formula_list.html` directly in a browser for a smoke check: without injection it must remain light and readable; after setting `document.documentElement.dataset.theme = "dark"` and injecting the generated CSS in DevTools, all listed surfaces must switch.

- [ ] **Step 5: Run MathInput regressions and commit**

  Run: `uv run pytest tests/test_math_input_theme.py tests/test_math_input_widget.py tests/test_algebra_panel.py -q`

  Expected: PASS; formula-list bridge behavior is unchanged.

  Commit:

  ```bash
  git add MathInputWidget/formula_list.html tests/test_math_input_theme.py
  git commit -m "style: theme formula list with token variables"
  ```
