# UI Design Refresh: Tokens and Qt Foundations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish one validated light/dark token source, generate Qt and Web theme assets from it, resolve the effective application theme, and migrate the first Qt visual surfaces to the shared system.

**Architecture:** `design/tokens.json` is the only authored visual source. `ui/tokens.py` validates and flattens it for `string.Template`-based QSS, while a Node prebuild script emits equivalent CSS custom properties. `main.py` owns persisted light/dark/system preference resolution; `MainWindow` consumes only the effective light/dark mode.

**Tech Stack:** Python 3.11, PySide6 6.8, JSON, `string.Template`, Node.js ESM, Vite 6, pnpm, pytest, Vitest.

**Spec:** `openspec/changes/ui-design-refresh/design.md`, `openspec/changes/ui-design-refresh/specs/ui-design-system/spec.md`, and `openspec/changes/ui-design-refresh/specs/app-shell/spec.md`

## Global Constraints

- Preserve the Agent boundary: WebView receives JSON events only and never gains access to Qt, PyVista, credentials, or scene mutation services.
- Do not add a UI framework, remote asset, CDN dependency, or third-party icon dependency; Qt icons use bundled lucide SVG path data and existing `QtSvg`.
- Keep `design/tokens.json` as the sole authored source for colors, typography, spacing, radii, shadows, and motion.
- Support complete `light` and `dark` token trees; persisted preference values are exactly `light`, `dark`, or `system`, with `system` as the default.
- Typography sizes are exactly 11/12/13/15px; control heights are 36/32/28px; radii are 4/8/10px; motion durations are 120/150/200ms.
- Text contrast must meet WCAG AA 4.5:1, and no five retired border grays or legacy Web accents may remain in live style code.
- Existing 2D/3D rendering, `.math` storage, provider behavior, and CommandPlan validation remain unchanged.

---

<!-- openspec-task: 1.1 -->
### Task 1: Add the validated design-token source

**Files:**
- Create: `design/tokens.json`
- Create: `ui/tokens.py`
- Test: `tests/test_ui_tokens.py`

**Interfaces:**
- Produces: `TokenError`, `load_tokens(path: Path | None = None) -> dict[str, object]`, and `flatten_theme(theme: Literal["light", "dark"], tokens: Mapping[str, object] | None = None) -> dict[str, str | int]`.
- Produces: flat names such as `bg_panel`, `text_primary`, `size_title`, `radius_md`, `duration_normal`, and `shadow_overlay` for Qt and parity tests.

- [x] **Step 1: Write failing loader and schema tests**

  Add `tests/test_ui_tokens.py` with a real-source test and temporary malformed documents:

  ```python
  from copy import deepcopy
  import json

  import pytest

  from ui.tokens import TokenError, flatten_theme, load_tokens


  def test_light_and_dark_themes_have_identical_leaf_keys() -> None:
      tokens = load_tokens()
      light = flatten_theme("light", tokens)
      dark = flatten_theme("dark", tokens)
      themed = {key for key in light if key.startswith(("bg_", "text_", "border_", "accent_", "status_", "shadow_"))}
      assert themed == {key for key in dark if key.startswith(("bg_", "text_", "border_", "accent_", "status_", "shadow_"))}
      assert light["bg_scene"] == "#f4f6f9"
      assert dark["bg_scene"] == "#1e1f23"


  def test_invalid_color_fails_fast(tmp_path) -> None:
      data = deepcopy(load_tokens())
      data["themes"]["dark"]["accent"]["default"] = "not-a-color"
      path = tmp_path / "tokens.json"
      path.write_text(json.dumps(data), encoding="utf-8")
      with pytest.raises(TokenError, match="themes.dark.accent.default"):
          load_tokens(path)
  ```

- [x] **Step 2: Run the focused test and confirm the missing module failure**

  Run: `uv run pytest tests/test_ui_tokens.py -q`

  Expected: FAIL during collection with `ModuleNotFoundError: No module named 'ui.tokens'`.

- [x] **Step 3: Define the complete token document**

  Create `design/tokens.json` with the frozen values from `design.md` section 2. Include `$schema`, `font.family_default`, the 11/12/13/15 size scale, `space.s1` through `space.s6`, 4/8/10 radii, 120/150/200 durations, the shared easing curve, and matching light/dark leaf structures. Each theme must contain:

  ```json
  {
    "bg": {"canvas": "#eef1f4", "panel": "#ffffff", "elevated": "#f5f7f9", "overlay": "#ffffff", "scene": "#f4f6f9"},
    "text": {"primary": "#17212e", "secondary": "#3f4c5c", "muted": "#66788c", "on_accent": "#ffffff"},
    "border": {"subtle": "#eceff3", "default": "#d5dbe3", "strong": "#b8c2cd"},
    "accent": {"default": "#2f7ebd", "hover": "#3a8cd0", "pressed": "#2970ab", "soft_bg": "#e4f0f9"},
    "status": {"success": "#16825d", "warning": "#8a5a00", "error": "#b42318"},
    "shadow": {"overlay": "0 1px 3px rgba(23,33,46,.10), 0 4px 12px rgba(23,33,46,.08)", "modal": "0 4px 8px rgba(23,33,46,.10), 0 12px 32px rgba(23,33,46,.14)"}
  }
  ```

  Use the exact dark values from the approved design, including `bg.scene = #1e1f23`, `accent.default = #4c9ee8`, and both dark shadow strings.

- [x] **Step 4: Implement typed validation and recursive flattening**

  Implement `ui/tokens.py` using `json.loads`, `Path`, `Mapping`, and `QColor.isValid()`. Validate required global sections, positive integer font sizes/durations, exact theme names, recursively identical light/dark leaf paths, and every value under color-bearing groups. Prefix global nested keys (`font.size.title` becomes `size_title`) and strip the `themes.<mode>` prefix from themed keys:

  ```python
  class TokenError(ValueError):
      pass


  def flatten_theme(theme: ThemeName, tokens: Mapping[str, object] | None = None) -> dict[str, str | int]:
      source = dict(tokens or load_tokens())
      common = _flatten({key: value for key, value in source.items() if key not in {"$schema", "$comment", "themes"}})
      themed = _flatten(source["themes"][theme])
      return {_flat_name(key): value for key, value in {**common, **themed}.items()}
  ```

  `_flat_name` must convert `font.size.title` to `size_title`, `motion.duration.normal` to `duration_normal`, `motion.easing_out` to `easing_out`, and all other dotted paths by replacing dots with underscores.

- [x] **Step 5: Run tests and commit the token foundation**

  Run: `uv run pytest tests/test_ui_tokens.py -q`

  Expected: PASS. Commit with `git add design/tokens.json ui/tokens.py tests/test_ui_tokens.py && git commit -m "feat: add validated UI design tokens"`.

<!-- openspec-task: 1.2 -->
### Task 2: Render the global Qt stylesheet from tokens

**Files:**
- Create: `ui/styles/base.qss.in`
- Modify: `ui/tokens.py`
- Modify: `ui/designer_window.py`
- Modify: `tests/test_ui_tokens.py`

**Interfaces:**
- Consumes: `flatten_theme(theme)` from Task 1.
- Produces: `build_qss(theme: Literal["light", "dark"]) -> str` with no unresolved `$` placeholders.
- `MainWindow._apply_style()` consumes `self.effective_theme` when present and otherwise uses `light` for construction-focused tests.

- [x] **Step 1: Add a failing QSS contract test**

  Extend `tests/test_ui_tokens.py`:

  ```python
  from ui.tokens import build_qss


  @pytest.mark.parametrize("theme", ["light", "dark"])
  def test_qss_template_is_fully_substituted(theme: str) -> None:
      qss = build_qss(theme)
      assert "$" not in qss
      assert "#viewportToolbar" in qss
      assert "QLineEdit:focus" in qss
      assert "min-height: 32px" in qss
  ```

- [x] **Step 2: Run the test and confirm the missing builder failure**

  Run: `uv run pytest tests/test_ui_tokens.py -q`

  Expected: FAIL because `build_qss` is not exported.

- [x] **Step 3: Create the QSS template with stable selector families**

  Move the live rules from `MainWindow._apply_style()` into `ui/styles/base.qss.in`. Use semantic substitutions and shared selector groups, including:

  ```css
  QMainWindow, #viewportHost { background: $bg_canvas; color: $text_primary; }
  #algebraPanel, #agentSidebar { background: $bg_panel; }
  QLineEdit, QComboBox, QPushButton {
    min-height: 32px; color: $text_primary; background: $bg_panel;
    border: 1px solid $border_default; border-radius: ${radius_sm}px;
  }
  QLineEdit:focus, QComboBox:focus, QPushButton:focus {
    border: 2px solid $accent_default;
  }
  #viewportToolbar, #twoDGeometryToolbar, #twoDLineFlyout, #sceneSettingsPanel {
    background: $bg_overlay; border: 1px solid $border_subtle;
    border-radius: ${radius_md}px;
  }
  ```

  Preserve selectors used by current widgets, but express all fixed visual values through the flattened mapping.

- [x] **Step 4: Implement `build_qss` and migrate `_apply_style`**

  Use strict substitution so missing tokens fail immediately:

  ```python
  from string import Template


  def build_qss(theme: ThemeName) -> str:
      template_path = Path(__file__).with_name("styles") / "base.qss.in"
      return Template(template_path.read_text(encoding="utf-8")).substitute(flatten_theme(theme))
  ```

  Replace the inline multiline stylesheet in `MainWindow._apply_style()` with `self.window.setStyleSheet(build_qss(getattr(self, "effective_theme", "light")))`. Do not change the call order in `MainWindow.__init__`.

- [x] **Step 5: Run focused layout/style tests and commit**

  Run: `uv run pytest tests/test_ui_tokens.py tests/test_main_window_layout.py tests/test_2d_geometry_toolbar.py -q`

  Expected: PASS. Commit with `git add ui/styles/base.qss.in ui/tokens.py ui/designer_window.py tests/test_ui_tokens.py && git commit -m "refactor: render Qt styles from design tokens"`.

<!-- openspec-task: 1.3 -->
### Task 3: Generate Web theme CSS from the shared tokens

**Files:**
- Create: `ui/agent_web/scripts/gen-theme.mjs`
- Create: `ui/agent_web/scripts/gen-theme.test.mjs`
- Modify: `ui/agent_web/package.json`
- Generate: `ui/agent_web/src/styles/theme.css`

**Interfaces:**
- Consumes: repository-root `design/tokens.json`.
- Produces: `generateThemeCss(tokens) -> string` and `loadTokens(path) -> object` for Node tests.
- Produces CSS branches `:root, [data-theme="light"]` and `[data-theme="dark"]`, each with matching `--agent-*` variables and a matching `color-scheme`.

- [x] **Step 1: Add a failing dependency-free Node test**

  Create `gen-theme.test.mjs` using `node:test` and `node:assert/strict`:

  ```javascript
  import test from "node:test";
  import assert from "node:assert/strict";
  import { generateThemeCss, loadTokens } from "./gen-theme.mjs";

  test("emits complete light and dark branches", async () => {
    const tokens = await loadTokens();
    const css = generateThemeCss(tokens);
    assert.match(css, /:root, \[data-theme="light"\]/);
    assert.match(css, /\[data-theme="dark"\]/);
    assert.match(css, /--agent-accent: #2f7ebd/);
    assert.match(css, /color-scheme: dark/);
  });
  ```

- [x] **Step 2: Run the Node test and confirm the missing generator failure**

  Run from `ui/agent_web`: `node --test scripts/gen-theme.test.mjs`

  Expected: FAIL with module-not-found for `scripts/gen-theme.mjs`.

- [x] **Step 3: Implement generation and the missing-file light fallback**

  Export `generateThemeCss` and `loadTokens`. Resolve the token file from `import.meta.url`, map semantic leaves to the existing Web names (`bg.panel -> --agent-bg`, `bg.elevated -> --agent-elevated`, `border.default -> --agent-border`, etc.), and add variables for overlay/modal shadows, muted text, on-accent text, scene background, and motion. When reading or parsing fails, return a built-in object containing the complete light theme and duplicate it into the dark slot so the build remains usable and visibly light:

  ```javascript
  export async function loadTokens(path = TOKEN_PATH) {
    try { return JSON.parse(await readFile(path, "utf8")); }
    catch { return { font: FALLBACK.font, motion: FALLBACK.motion, themes: { light: FALLBACK.theme, dark: FALLBACK.theme } }; }
  }
  ```

  The CLI path writes `src/styles/theme.css`; imported test execution must not write a file.

- [x] **Step 4: Wire generation before development and production builds**

  Add scripts without changing the existing Vite command semantics:

  ```json
  {
    "scripts": {
      "theme:generate": "node scripts/gen-theme.mjs",
      "predev": "pnpm theme:generate",
      "prebuild": "pnpm theme:generate",
      "dev": "vite",
      "build": "vite build"
    }
  }
  ```

  Run `pnpm theme:generate` and commit the generated `theme.css` so Python packaging remains Node-free.

- [x] **Step 5: Run generator tests and the frontend build, then commit**

  Run from `ui/agent_web`: `node --test scripts/gen-theme.test.mjs && pnpm build`

  Expected: PASS and `dist/manifest.json` references fresh local assets. Commit with `git add design/tokens.json ui/agent_web/package.json ui/agent_web/scripts ui/agent_web/src/styles/theme.css ui/agent_web/dist && git commit -m "build: generate Web theme from shared tokens"`.

<!-- openspec-task: 1.4 -->
### Task 4: Resolve and persist the application theme mode

**Files:**
- Modify: `main.py`
- Modify: `ui/designer_window.py`
- Create: `tests/test_theme_mode.py`

**Interfaces:**
- Produces: `normalize_theme_mode(value: object) -> Literal["light", "dark", "system"]` and `effective_theme(mode, color_scheme) -> Literal["light", "dark"]` in `main.py`.
- `MainWindow.set_theme(mode: ThemeMode, effective: EffectiveTheme) -> None` reapplies QSS and forwards the effective value to dependent surfaces.

- [x] **Step 1: Write failing pure theme-resolution tests**

  Create `tests/test_theme_mode.py` without constructing the full PyVista window:

  ```python
  from PySide6.QtCore import Qt

  from main import effective_theme, normalize_theme_mode


  def test_theme_mode_defaults_invalid_values_to_system() -> None:
      assert normalize_theme_mode(None) == "system"
      assert normalize_theme_mode("sepia") == "system"
      assert normalize_theme_mode("dark") == "dark"


  def test_system_mode_tracks_qt_color_scheme() -> None:
      assert effective_theme("system", Qt.ColorScheme.Dark) == "dark"
      assert effective_theme("system", Qt.ColorScheme.Light) == "light"
      assert effective_theme("light", Qt.ColorScheme.Dark) == "light"
  ```

- [x] **Step 2: Run the focused test and verify import failure**

  Run: `uv run pytest tests/test_theme_mode.py -q`

  Expected: FAIL because the helpers do not exist.

- [x] **Step 3: Implement mode resolution and application font setup**

  In `main.py`, read `QSettings().value("ui/theme", "system")`, normalize it, resolve `app.styleHints().colorScheme()`, and set one global `QFont` using `load_tokens()["font"]` before creating `MainWindow`. Keep helper functions pure. Construct the window with theme state explicitly:

  ```python
  mode = normalize_theme_mode(settings.value("ui/theme", "system"))
  effective = effective_theme(mode, app.styleHints().colorScheme())
  app.setFont(QFont(str(tokens["font"]["family_default"]), int(tokens["font"]["size"]["body"])))
  window = MainWindow(theme_mode=mode, effective_theme=effective)
  ```

- [x] **Step 4: React to OS changes only in system mode**

  Add `MainWindow.set_theme` to save `theme_mode`/`effective_theme`, call `_apply_style()`, refresh theme-aware icons if available, forward the effective theme to the Agent host if available, and rerender auto-background scenes when Task 10 later adds that behavior. Connect `colorSchemeChanged` to a closure that returns immediately unless the stored mode is `system`.

- [x] **Step 5: Run tests and commit theme resolution**

  Run: `uv run pytest tests/test_theme_mode.py tests/test_main_window_layout.py -q`

  Expected: PASS. Commit with `git add main.py ui/designer_window.py tests/test_theme_mode.py && git commit -m "feat: resolve and persist application theme"`.

<!-- openspec-task: 1.5 -->
### Task 5: Complete token and QSS regression coverage

**Files:**
- Modify: `tests/test_ui_tokens.py`
- Create: `tests/snapshots/base-light.qss`
- Create: `tests/snapshots/base-dark.qss`

**Interfaces:**
- Consumes: `load_tokens`, `flatten_theme`, and `build_qss` from Tasks 1-2.
- Produces: stable normalized QSS snapshots and explicit assertions for prohibited legacy selectors/colors.

- [x] **Step 1: Add the full validation matrix**

  Add parametrized malformed fixtures for a missing theme leaf, mismatched theme key sets, zero font size, negative duration, and invalid color. Add contract assertions:

  ```python
  RETIRED_SELECTORS = ("#agentPanel", "#agentCollapsedBar", "#agentUserBubble", "#agentAssistantBubble", "#agentPlanCard")
  RETIRED_COLORS = ("#d9dde3", "#d0d7df", "#cbd3dd", "#dfe3e8", "#e0e5ea", "#3794ff", "#006ab1")


  @pytest.mark.parametrize("theme", ["light", "dark"])
  def test_qss_has_required_and_no_retired_content(theme: str) -> None:
      qss = build_qss(theme).lower()
      assert "#scenesettingspanel" in qss
      assert not any(selector.lower() in qss for selector in RETIRED_SELECTORS)
      assert not any(color in qss for color in RETIRED_COLORS)
  ```

- [x] **Step 2: Run the expanded tests and observe contract failures**

  Run: `uv run pytest tests/test_ui_tokens.py -q`

  Expected: FAIL on any validation or selector behavior not completed in Tasks 1-2.

- [x] **Step 3: Tighten error paths and snapshot normalization**

  Make every `TokenError` name the invalid JSON path. Normalize snapshots by stripping trailing whitespace and ending with one newline, then compare `build_qss("light")` and `build_qss("dark")` to the committed files. Generate the two initial expected snapshots from reviewed output, not by updating snapshots inside the test.

- [x] **Step 4: Run focused and neighboring UI tests**

  Run: `uv run pytest tests/test_ui_tokens.py tests/test_theme_mode.py tests/test_main_window_layout.py tests/test_scene_settings.py tests/test_2d_geometry_toolbar.py -q`

  Expected: PASS with no QSS placeholder or retired style values.

- [x] **Step 5: Commit the regression suite**

  Run: `git add tests/test_ui_tokens.py tests/snapshots && git commit -m "test: lock UI token and QSS contracts"`.

<!-- openspec-task: 2.1 -->
### Task 6: Remove retired Qt Agent selectors from the live stylesheet

**Files:**
- Modify: `ui/styles/base.qss.in`
- Modify: `ui/designer_window.py`
- Modify: `tests/test_ui_tokens.py`

**Interfaces:**
- Consumes: the retired-selector guard introduced in Task 5.
- Produces: a global QSS surface that styles `#agentSidebar` only as a live shell region and contains no `#agentCollapsedBar` family.

- [x] **Step 1: Extend the selector guard to every retired prefix**

  Parse selector preambles from generated QSS and assert no selector begins with `#agent` except the live allowlist `{#agentSidebar, #agentSidebarWeb, #agentButton}`. Also assert the inline QSS block no longer exists in `MainWindow._apply_style()`.

- [x] **Step 2: Run the selector test and capture all remaining names**

  Run: `uv run pytest tests/test_ui_tokens.py -q`

  Expected: FAIL and identify every leftover retired selector before deletion.

- [x] **Step 3: Remove dead selector groups**

  Delete rules for `#agentPanel`, `#agentCollapsedBar`, `#agentCollapsedLabel`, `#agentNav*`, `#agentTitle`, `#agentStatus`, `#agentModeHint`, `#agentMessageScroll`, `#agentUserBubble`, `#agentAssistantBubble`, `#agentPlanCard`, `#agentPlanProblems`, `#agentPromptEdit`, and `#agentSendButton`. Preserve only current shell/WebView styling and do not add replacement Qt chat rules.

- [x] **Step 4: Search live style sources and run migration tests**

  Run: `rg -n "#agent(Panel|Collapsed|Nav|Title|Status|ModeHint|MessageScroll|UserBubble|AssistantBubble|PlanCard|PlanProblems|PromptEdit|SendButton)" ui --glob "*.py" --glob "*.qss.in"`

  Expected: no matches. Then run `uv run pytest tests/test_ui_tokens.py tests/test_agent_panel_migration.py tests/test_sidebar_visibility.py -q` and expect PASS.

- [x] **Step 5: Commit dead-style removal**

  Run: `git add ui/styles/base.qss.in ui/designer_window.py tests/test_ui_tokens.py && git commit -m "refactor: remove retired Qt Agent styles"`.

<!-- openspec-task: 2.2 -->
### Task 7: Add shared high-DPI lucide icons and replace Unicode controls

**Files:**
- Create: `ui/icons.py`
- Modify: `ui/designer_window.py`
- Modify: `ui/two_d_tools.py`
- Modify: `ui/algebra_panel.py`
- Create: `tests/test_ui_icons.py`
- Modify: `tests/test_2d_geometry_toolbar.py`

**Interfaces:**
- Produces: `icon(name: str, color: QColor | str, size: int = 16, dpr: float = 1.0) -> QIcon` and `apply_icon(button: QAbstractButton, name: str, color: str, *, icon_size: int = 16, hit_size: int = 36) -> None`.
- Produces icon names `settings-2`, `sparkles`, `play`, `circle-dot`, `slash`, `type`, `undo-2`, `redo-2`, `plus`, `ellipsis`, and later `eye`/`eye-off`/theme/status icons.

- [x] **Step 1: Write failing icon rendering and control-metric tests**

  In `tests/test_ui_icons.py`, assert every required name renders a non-null 16px `QIcon`, a 2x DPR pixmap has a 32x32 backing image and `devicePixelRatio() == 2.0`, repeated keys reuse the cache, and unknown names raise `KeyError`. Update toolbar tests to assert icon buttons have empty text, 36x36 hit areas, and 16x16 icon sizes.

- [x] **Step 2: Run focused tests and verify the missing module/Unicode failures**

  Run: `uv run pytest tests/test_ui_icons.py tests/test_2d_geometry_toolbar.py -q`

  Expected: FAIL because `ui.icons` does not exist and toolbar buttons still contain Unicode glyphs.

- [x] **Step 3: Implement the SVG renderer and cache**

  Store reviewed 24x24 lucide SVG strings in an immutable mapping. Replace `currentColor` with `QColor(color).name(QColor.NameFormat.HexArgb)` only after validating the color. Render into a transparent `QPixmap(round(size*dpr), round(size*dpr))` via `QSvgRenderer`, call `pixmap.setDevicePixelRatio(dpr)`, and cache `QIcon` by `(name, rgba, size, round(dpr, 2))`.

- [x] **Step 4: Replace the current character buttons**

  Use `apply_icon` for viewport settings and Agent buttons, 2D select/point/line/snap/undo/redo controls, AlgebraPanel add and row-menu controls. Preserve tooltips, checkable state, object names, and signals. Set main toolbar controls to 36/16 and row controls to 28/16. The scene-mode control may show `2D`/`3D` text because it is a mode label, not an icon substitute.

- [x] **Step 5: Search, test, and commit**

  Run: `rg -n "[⚙✦➤●╱↶↷⋮]" ui --glob "*.py"` and expect no control-glyph matches. Run `uv run pytest tests/test_ui_icons.py tests/test_2d_geometry_toolbar.py tests/test_algebra_panel.py tests/test_main_window_layout.py -q` and expect PASS. Commit with `git add ui/icons.py ui/designer_window.py ui/two_d_tools.py ui/algebra_panel.py tests && git commit -m "feat: use shared lucide icons in Qt controls"`.

<!-- openspec-task: 2.3 -->
### Task 8: Unify overlay and dialog chrome

**Files:**
- Modify: `ui/styles/base.qss.in`
- Modify: `ui/designer_window.py`
- Modify: `ui/two_d_tools.py`
- Modify: `ui/scene_settings.py`
- Modify: `ui/lighting_dialog.py`
- Modify: `tests/test_ui_tokens.py`

**Interfaces:**
- Consumes: overlay/modal token values and the 36/16 icon metrics from prior tasks.
- Produces: object-name based overlay family styles and `apply_drop_shadow(widget, level: Literal["overlay", "modal"], theme: EffectiveTheme) -> None` in `ui/tokens.py` if QSS cannot express the approved shadow.

- [x] **Step 1: Add failing chrome assertions**

  Assert generated QSS groups `#viewportToolbar`, `#twoDGeometryToolbar`, `#twoDLineFlyout`, and `#sceneSettingsPanel` with `bg_overlay`, `border_subtle`, and `radius_md`; assert `QDialog` uses `radius_lg`. Add a construction test that each floating widget has the expected object name and `QGraphicsDropShadowEffect` blur/offset/color derived from the selected shadow level.

- [x] **Step 2: Run focused UI tests and verify missing shadow/chrome behavior**

  Run: `uv run pytest tests/test_ui_tokens.py tests/test_2d_geometry_toolbar.py tests/test_scene_settings.py -q`

  Expected: FAIL until all overlay members use the shared style and effects.

- [x] **Step 3: Apply shared overlay metrics and hover styling**

  Group overlay selectors in `base.qss.in`, use 8px radius, subtle border, overlay background, `accent_soft_bg` hover, and `accent_default` checked state. Apply the overlay shadow effect after each floating widget is constructed. Use modal shadow and 10px radius for `LightingDialog` and other current QDialogs.

- [x] **Step 4: Verify geometry and focus behavior remain stable**

  Run: `uv run pytest tests/test_2d_geometry_toolbar.py tests/test_scene_settings.py tests/test_main_window_layout.py -q`

  Expected: PASS; shadows must not alter layout geometry or flyout positioning.

- [x] **Step 5: Commit overlay consistency**

  Run: `git add ui/tokens.py ui/styles/base.qss.in ui/designer_window.py ui/two_d_tools.py ui/scene_settings.py ui/lighting_dialog.py tests && git commit -m "style: unify overlay and dialog chrome"`.

<!-- openspec-task: 2.4 -->
### Task 9: Normalize title hierarchy and remove local font overrides

**Files:**
- Modify: `ui/algebra_panel.py`
- Modify: `widgets/LightRotationWidget.py`
- Modify: `ui/styles/base.qss.in`
- Modify: `tests/test_algebra_panel.py`
- Create: `tests/test_ui_typography.py`

**Interfaces:**
- Consumes: application font and 11/12/13/15 token scale.
- Produces: object names `algebraTitle` and `sectionHeader` styled only by global QSS; `LightRotationWidget` derives painter fonts from `self.font()`.

- [x] **Step 1: Write failing typography-source tests**

  Add source and widget assertions that AlgebraPanel title resolves to 15px, no control sets a 20px/22pt local font, and `LightRotationWidget.py` does not construct `QFont("Segoe UI", ...)`. Assert inline color-button styles set only the dynamic swatch background and never fixed text/font values.

- [x] **Step 2: Run tests and capture current override failures**

  Run: `uv run pytest tests/test_ui_typography.py tests/test_algebra_panel.py -q`

  Expected: FAIL on the current 20px title, 22pt row button, and hardcoded painter fonts.

- [x] **Step 3: Move hierarchy rules into QSS**

  Give the main AlgebraPanel heading `objectName="algebraTitle"` and section labels `objectName="sectionHeader"`. Style the former with `${size_title}px` and weight 600; style the latter with `${size_caption}px`, `text_muted`, and positive `letter-spacing`. Remove local styles that duplicate these concerns.

- [x] **Step 4: Derive custom-painted fonts from the application font**

  In `LightRotationWidget.paintEvent`, copy the inherited font and set pixel size/weight only:

  ```python
  label_font = QFont(self.font())
  label_font.setPixelSize(13)
  label_font.setWeight(QFont.Weight.DemiBold)
  value_font = QFont(self.font())
  value_font.setPixelSize(15)
  value_font.setWeight(QFont.Weight.Bold)
  ```

  Remove the AlgebraPanel 22pt button override and keep swatch foreground selection based on `QColor.lightness()` without a platform font declaration.

- [x] **Step 5: Run tests and commit**

  Run: `uv run pytest tests/test_ui_typography.py tests/test_algebra_panel.py tests/test_ui_tokens.py tests/test_main_window_layout.py -q`

  Expected: PASS. Commit with `git add ui/algebra_panel.py widgets/LightRotationWidget.py ui/styles/base.qss.in tests && git commit -m "style: normalize Qt typography hierarchy"`.
