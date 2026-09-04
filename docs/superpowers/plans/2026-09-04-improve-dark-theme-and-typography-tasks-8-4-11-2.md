# Dark Theme and Typography Improvements — Consistency and Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish Chinese UI copy, distinct SVG iconography and accessible names, improve lighting and lecture dialog behavior, then prove the complete change through full regression and a documented dark-theme walkthrough.

**Architecture:** User-facing wording remains in the owning React/HTML component while protocol values and model identifiers stay unchanged. Qt icons continue through the shared tintable SVG registry. Lighting control state is centralized in a control-sync helper, lecture content is constrained by a widget-resizable scroll area, and final evidence is stored as new verification artifacts beside the OpenSpec change without editing its planning files.

**Tech Stack:** Python 3.11, PySide6 6.8/QTest, React 18, TypeScript, HTML/CSS, Vite/pnpm, pytest, Vitest, OpenSpec CLI.

**Spec:** `openspec/changes/improve-dark-theme-and-typography/design.md`, `openspec/changes/improve-dark-theme-and-typography/tasks.md`, `openspec/changes/improve-dark-theme-and-typography/specs/ui-design-system/spec.md`, `openspec/changes/improve-dark-theme-and-typography/specs/app-shell/spec.md`, `openspec/changes/improve-dark-theme-and-typography/specs/mathagent-sidebar/spec.md`, and `openspec/changes/improve-dark-theme-and-typography/specs/linear-algebra-case-tabs/spec.md`

## Global Constraints

- Translate user-facing headings, empty states, tooltips, and aria labels; keep wire/protocol values (`Agent`, `Ask`, `Plan`, provider IDs, model IDs, `responses`) unchanged.
- Do not replace product/technology names such as MathAgent, DeepSeek, OpenAI, API, URL, or model names when they are required identifiers.
- Every new Qt control icon is embedded SVG path data rendered through `ui.icons`; no emoji or Unicode glyph controls.
- Co-located 2D toolbar buttons must have distinct stored icon names and remain retintable in both themes.
- Lighting reset updates all visible values in place and emits one final settings/material state without closing the dialog.
- The lecture dialog maximum height is exactly 80% of the active screen's available geometry; short content must not force a scrollbar.
- Do not edit existing OpenSpec proposal/design/spec/tasks files. Final screenshots and their new index may be added under the change's `verification/` directory.
- Keep commits task-scoped and stage only the files listed by the current task.

---

<!-- openspec-task: 8.4 -->
### Task 1: Replace mixed English UI copy with consistent Chinese wording

**Files:**
- Modify: `ui/agent_web/src/components/HistoryView.tsx`
- Modify: `ui/agent_web/src/components/SettingsView.tsx`
- Modify: `ui/agent_web/src/components/AttachmentActions.tsx`
- Modify: `ui/agent_web/src/components/SessionTabs.tsx`
- Modify: `ui/agent_web/src/components/Timeline.tsx`
- Modify: `ui/agent_web/src/components/ModeSelector.tsx`
- Modify: `ui/agent_web/src/App.test.tsx`
- Modify: `ui/agent_web/src/components/HistoryView.test.tsx`
- Modify: `MathInputWidget/formula_list.html`
- Modify: `tests/test_math_input_theme.py`
- Generate: `ui/agent_web/dist/`

**Interfaces:**
- Preserves: React intent types/payload values, model/provider identifiers, and all MathInput JavaScript/QWebChannel function names.
- Produces exact formula-list copy: `隐藏函数`, `显示函数`, `函数显示与采样设置`, `公式`, `几何对象`, and `删除`.
- Produces Chinese history/settings headings, empty states, tooltips, and aria labels.

- [ ] **Step 1: Add failing component and HTML copy assertions**

  Update `App.test.tsx` to expect `历史记录`, `暂无会话`, `设置`, and `返回当前对话`. Extend `HistoryView.test.tsx` to assert `1 轮` and Chinese action labels.

  Add to `tests/test_math_input_theme.py`:

  ```python
  def test_formula_list_user_copy_is_chinese() -> None:
      html = (ROOT / "MathInputWidget" / "formula_list.html").read_text(encoding="utf-8")
      for expected in ("隐藏函数", "显示函数", "函数显示与采样设置", "公式", "几何对象", "删除"):
          assert expected in html
      for retired in ("Hide function", "Show function", "Function display and sampling settings", 'aria-label="Formula"', 'aria-label="Geometry object"', ">Delete<"):
          assert retired not in html
  ```

  Add a source scan for retired phrases `History`, `No conversations`, `Hidden`, `Back to conversation`, `Settings`, `Skills`, `Memory`, `Rules`, `Add image`, and `Add file` in the listed user-interface components.

- [ ] **Step 2: Run focused Web and MathInput tests**

  Run:

  ```powershell
  Push-Location ui/agent_web
  pnpm test -- src/App.test.tsx src/components/HistoryView.test.tsx
  Pop-Location
  uv run pytest tests/test_math_input_theme.py -q
  ```

  Expected: FAIL on the current English headings, actions, empty states, aria labels, and formula-list tooltips.

- [ ] **Step 3: Translate History, Settings, composer tools, tabs, and timeline semantics**

  Apply these exact UI mappings while leaving values unchanged:

  ```text
  History → 历史记录                  No conversations → 暂无会话
  Hidden → 已隐藏                    N turns → N 轮
  Back to conversation → 返回当前对话
  Rename/Restore/Hide → 重命名/恢复/隐藏
  Settings → 设置                    Agent / Model → 助手 / 模型
  Skills/Memory/Rules → 技能/记忆/规则
  Provider → 供应商                  API protocol → API 协议
  Add image/Add file → 添加图片/添加文件
  Tools/Add attachment → 工具/添加附件
  New Chat → 新对话
  User message/Conversation timeline → 用户消息/对话时间线
  ```

  In `ModeSelector`, keep option values `Agent`, `Ask`, `Plan`, but display `代理`, `问答`, `计划`. Translate only prose around Geometry/Calculus/Linear algebra; do not translate provider/model identifiers or URL placeholders.

- [ ] **Step 4: Translate formula-list tooltip and aria strings**

  Replace the six approved formula-list strings in both initial markup and JavaScript-generated attributes. Do not change CSS class names, dataset keys, serialized layer kinds, or bridge method names.

- [ ] **Step 5: Run full frontend/copy tests, rebuild, and commit**

  Run:

  ```powershell
  Push-Location ui/agent_web
  pnpm test
  pnpm build
  Pop-Location
  uv run pytest tests/test_math_input_theme.py tests/test_agent_web_packaging.py -q
  ```

  Expected: PASS and generated assets expose the Chinese headings/labels.

  Commit:

  ```bash
  git add ui/agent_web/src ui/agent_web/dist MathInputWidget/formula_list.html tests/test_math_input_theme.py
  git commit -m "style: unify sidebar and formula copy in Chinese"
  ```

<!-- openspec-task: 9.1 -->
### Task 2: Give every overlapping 2D tool a distinct tintable SVG icon

**Files:**
- Modify: `ui/icons.py`
- Modify: `ui/two_d_tools.py`
- Modify: `tests/test_ui_icons.py`
- Modify: `tests/test_icon_theming.py`
- Modify: `tests/test_2d_geometry_toolbar.py`

**Interfaces:**
- Produces icon names: `pen-line`, `vector`, and `angle` in `LUCIDE_SVG`.
- Produces mappings: line-tool entry → `pen-line`; vector → `vector`; angle → `angle`; ray remains `arrow-up-right`; straight line remains `slash`; projection remains `corner-down-right`.
- Preserves: `_kiro_icon_state` metadata used by `retint_icons()`.

- [ ] **Step 1: Add failing render and toolbar uniqueness tests**

  Extend `tests/test_ui_icons.py` required names with `pen-line`, `vector`, and `angle`. In `tests/test_2d_geometry_toolbar.py`, inspect each button's remembered icon state:

  ```python
  def icon_name(button) -> str:
      return button.property("_kiro_icon_state")[0]


  def test_co_located_geometry_tools_use_distinct_icons(self) -> None:
      toolbar = TwoDGeometryToolbar(QWidget())
      names = [
          icon_name(toolbar.vector_button),
          icon_name(toolbar.line_button),
          icon_name(toolbar.angle_button),
          icon_name(toolbar.projection_button),
          *(icon_name(button) for button in toolbar.line_buttons.values()),
      ]
      self.assertEqual(len(names), len(set(names)))
  ```

  Add a retint test that includes the three new names.

- [ ] **Step 2: Run icon tests and reproduce the duplicate glyphs**

  Run: `uv run pytest tests/test_ui_icons.py tests/test_icon_theming.py tests/test_2d_geometry_toolbar.py -q`

  Expected: FAIL because the names are absent and vector/ray, line-entry/straight-line, and angle/projection currently share icons.

- [ ] **Step 3: Add the exact SVG path data to `LUCIDE_SVG`**

  Add:

  ```python
  "pen-line": _svg('<path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4Z"/>'),
  "vector": _svg('<circle cx="5" cy="19" r="2" fill="currentColor" stroke="none"/><path d="M6.5 17.5 17 7"/><path d="M11 7h6v6"/>'),
  "angle": _svg('<path d="M5 19h13"/><path d="M5 19 16 8"/><path d="M10.5 19a5.5 5.5 0 0 0-3.9-1.6"/>'),
  ```

  Keep the common 24×24 head, `currentColor`, stroke width, cap, and join behavior so rendering and high-DPI caching remain unchanged.

- [ ] **Step 4: Change only the three duplicate toolbar mappings**

  In `TwoDGeometryToolbar.__init__`, construct `line_button` with `pen-line`, `vector_button` with `vector`, and `angle_button` with `angle`. Leave the concrete flyout and projection mappings as specified above.

- [ ] **Step 5: Run icon/toolbar regressions and commit**

  Run: `uv run pytest tests/test_ui_icons.py tests/test_icon_theming.py tests/test_2d_geometry_toolbar.py -q`

  Expected: PASS; every icon paints visible pixels and every named co-located control has a distinct icon state.

  Commit:

  ```bash
  git add ui/icons.py ui/two_d_tools.py tests/test_ui_icons.py tests/test_icon_theming.py tests/test_2d_geometry_toolbar.py
  git commit -m "style: distinguish 2d geometry tool icons"
  ```

<!-- openspec-task: 9.2 -->
### Task 3: Replace the API-key emoji with filled and hollow circle icons

**Files:**
- Modify: `ui/icons.py`
- Modify: `ui/agent_settings.py`
- Modify: `tests/test_ui_icons.py`
- Modify: `tests/test_icon_theming.py`
- Modify: `tests/test_agent_settings.py`

**Interfaces:**
- Produces icons: `circle-filled` and `circle-outline`.
- Visible key (`QLineEdit.Normal`) uses `circle-filled`; hidden key (`QLineEdit.Password`) uses `circle-outline`.
- Produces: `AgentSettingsDialog._sync_reveal_key_icon(revealed: bool) -> None`.

- [ ] **Step 1: Add failing icon-state and no-emoji tests**

  Extend `tests/test_agent_settings.py`:

  ```python
  def test_api_key_visibility_uses_circle_icons(self) -> None:
      dialog = AgentSettingsDialog(effective_theme="light")
      assert dialog.reveal_key_button.text() == ""
      assert dialog.reveal_key_button.property("_kiro_icon_state")[0] == "circle-outline"
      dialog.reveal_key_button.setChecked(True)
      assert dialog.reveal_key_button.property("_kiro_icon_state")[0] == "circle-filled"
      dialog.set_effective_theme("dark")
      assert dialog.reveal_key_button.property("_kiro_icon_state")[0] == "circle-filled"
  ```

  Assert `👁` is absent from `ui/agent_settings.py`; add both icon names to render tests.

- [ ] **Step 2: Run focused tests and confirm emoji/current eye behavior**

  Run: `uv run pytest tests/test_agent_settings.py tests/test_ui_icons.py tests/test_icon_theming.py -q`

  Expected: FAIL because the button text is an emoji and circle icons do not exist.

- [ ] **Step 3: Add exact filled/hollow SVG paths**

  Add to `LUCIDE_SVG`:

  ```python
  "circle-filled": _svg('<circle cx="12" cy="12" r="7" fill="currentColor" stroke="none"/>'),
  "circle-outline": _svg('<circle cx="12" cy="12" r="7"/>'),
  ```

- [ ] **Step 4: Centralize icon updates with echo-mode changes**

  Import `apply_icon`, `icon_color`, and `retint_icons`. Remove `setText("👁")`; after creating the checkable button call `_sync_reveal_key_icon(False)`. Implement:

  ```python
  def _sync_reveal_key_icon(self, revealed: bool) -> None:
      apply_icon(
          self.reveal_key_button,
          "circle-filled" if revealed else "circle-outline",
          icon_color(self.effective_theme),
          icon_size=16,
          hit_size=28,
      )

  def _toggle_key_echo(self, revealed: bool) -> None:
      self.api_key_edit.setEchoMode(
          QLineEdit.EchoMode.Normal if revealed else QLineEdit.EchoMode.Password
      )
      self._sync_reveal_key_icon(revealed)
  ```

  In `set_effective_theme`, call `retint_icons(self, effective_theme)` when controls already exist. Preserve the tooltip text.

- [ ] **Step 5: Run icon/settings tests and commit**

  Run: `uv run pytest tests/test_agent_settings.py tests/test_ui_icons.py tests/test_icon_theming.py -q`

  Expected: PASS for echo mode, icon state, and dark retint.

  Commit:

  ```bash
  git add ui/icons.py ui/agent_settings.py tests/test_ui_icons.py tests/test_icon_theming.py tests/test_agent_settings.py
  git commit -m "style: replace api key emoji with circle icons"
  ```

<!-- openspec-task: 9.3 -->
### Task 4: Restore viewport text to the token scale and name shell controls accessibly

**Files:**
- Modify: `ui/styles/base.qss.in`
- Modify: `ui/designer_window.py`
- Modify: `ui/two_d_tools.py`
- Modify: `ui/status_bar.py`
- Modify: `tests/test_ui_tokens.py`
- Modify: `tests/test_ui_design_integration.py`
- Modify: `tests/test_app_status_bar.py`
- Modify: `tests/test_2d_geometry_toolbar.py`
- Modify: `tests/snapshots/base-light.qss`
- Modify: `tests/snapshots/base-dark.qss`

**Interfaces:**
- Produces: `sceneModeButton` object name and `${size_title}px` text size; generated QSS contains no `font-size: 18px`.
- Produces: every interactive viewport toolbar, 2D toolbar, and status-bar control has a non-empty accessible name matching its tooltip or visible purpose.

- [ ] **Step 1: Add failing typography and accessible-name tests**

  In `tests/test_ui_tokens.py`, assert `18px` is absent and `_block_for_selector(qss, "#sceneModeButton")` contains `font-size: 15px`.

  In construction tests, collect `QAbstractButton` descendants of `viewportToolbar`, `TwoDGeometryToolbar` (including flyout), and `AppStatusBar`:

  ```python
  for button in controls:
      assert button.accessibleName().strip(), button.objectName()
  ```

  Assert `scene_mode_button.objectName() == "sceneModeButton"`.

- [ ] **Step 2: Run focused shell tests and list unnamed controls**

  Run: `uv run pytest tests/test_ui_tokens.py tests/test_ui_design_integration.py tests/test_app_status_bar.py tests/test_2d_geometry_toolbar.py -q`

  Expected: FAIL for the hardcoded 18px group, missing scene-mode object name, and unnamed buttons.

- [ ] **Step 3: Scope the text rule to the scene-mode button**

  Replace the group font declaration with:

  ```css
  #sceneModeButton { font-size: ${size_title}px; font-weight: 700; }
  ```

  Keep hover styles grouped for all overlay buttons. Set `self.scene_mode_button.setObjectName("sceneModeButton")` before its fixed size.

- [ ] **Step 4: Assign accessible names at each control factory/construction point**

  In `_configure_viewport`, set names to `场景设置`, `切换二维和三维场景`, and `AI 教学助手`. In `TwoDGeometryToolbar._button/_action_button`, call `button.setAccessibleName(tooltip)`. In `AppStatusBar`, give the Agent button a stable purpose name and update it with status text:

  ```python
  self.agent_button.setToolTip("AI 教学助手状态")
  self.agent_button.setAccessibleName("AI 教学助手状态")
  ```

  Keep the theme button's existing dynamic accessible name.

- [ ] **Step 5: Update snapshots, run shell tests, and commit**

  Regenerate/review both QSS snapshots, then run:

  `uv run pytest tests/test_ui_tokens.py tests/test_ui_design_integration.py tests/test_app_status_bar.py tests/test_2d_geometry_toolbar.py -q`

  Expected: PASS with no 18px text rule and no unnamed interactive shell controls.

  Commit:

  ```bash
  git add ui/styles/base.qss.in ui/designer_window.py ui/two_d_tools.py ui/status_bar.py tests/test_ui_tokens.py tests/test_ui_design_integration.py tests/test_app_status_bar.py tests/test_2d_geometry_toolbar.py tests/snapshots/base-light.qss tests/snapshots/base-dark.qss
  git commit -m "fix: normalize shell typography and accessible names"
  ```

<!-- openspec-task: 10.1 -->
### Task 5: Reset lighting in place and expose live numeric slider values

**Files:**
- Modify: `ui/lighting_dialog.py`
- Modify: `tests/test_lighting_dialog.py`

**Interfaces:**
- Produces attributes: `ambient_slider`, `ambient_value_label`, `_intensity_sliders: dict[str, QSlider]`, `_intensity_value_labels: dict[str, QLabel]`, and `_position_spins: dict[str, list[QSpinBox]]`.
- Produces: `_sync_controls_from_settings() -> None`.
- Reset defaults: ambient 20, key 105, fill 45, rim 70, rotation 0°, material `光泽塑料`; dialog remains visible.

- [ ] **Step 1: Add failing reset and live-readout tests**

  Extend `tests/test_lighting_dialog.py`:

  ```python
  def test_slider_readouts_update_live() -> None:
      dialog = LightingDialog(LightSettings())
      dialog.ambient_slider.setValue(37)
      dialog._intensity_sliders["key"].setValue(126)
      assert dialog.ambient_value_label.text() == "37%"
      assert dialog._intensity_value_labels["key"].text() == "126%"


  def test_reset_updates_controls_without_closing() -> None:
      dialog = LightingDialog(LightSettings())
      dialog.show()
      dialog.ambient_slider.setValue(80)
      dialog._intensity_sliders["fill"].setValue(150)
      dialog.rotation_widget.set_angle(90)
      dialog.material_combo.setCurrentText("抛光金属")
      dialog._reset_defaults()
      assert dialog.isVisible()
      assert dialog.ambient_slider.value() == 20
      assert dialog._intensity_sliders["key"].value() == 105
      assert dialog._intensity_sliders["fill"].value() == 45
      assert dialog._intensity_sliders["rim"].value() == 70
      assert dialog.rotation_widget.angle == 0
      assert dialog.material_combo.currentText() == "光泽塑料"
  ```

  Spy on `settings_changed` and `material_changed` to assert the reset emits final default state rather than intermediate stale values.

- [ ] **Step 2: Run the focused test and reproduce close/no-readout behavior**

  Run: `uv run pytest tests/test_lighting_dialog.py -q`

  Expected: FAIL because sliders are local variables, labels do not exist, and `_reset_defaults()` closes the dialog.

- [ ] **Step 3: Build reusable slider-with-value rows**

  Store control references. Create a helper returning a host plus label:

  ```python
  def _slider_row(self, slider: QSlider) -> tuple[QWidget, QLabel]:
      host = QWidget(self)
      row = QHBoxLayout(host)
      row.setContentsMargins(0, 0, 0, 0)
      value_label = QLabel(f"{slider.value()}%", host)
      value_label.setMinimumWidth(38)
      value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
      slider.valueChanged.connect(lambda value: value_label.setText(f"{value}%"))
      row.addWidget(slider, 1)
      row.addWidget(value_label)
      return host, value_label
  ```

  Use it for ambient and all three intensity sliders. Store position spinboxes by light name so reset can restore them.

- [ ] **Step 4: Synchronize every control from `LightSettings` and keep the dialog open**

  Implement `_sync_controls_from_settings()` with `QSignalBlocker` for material, sliders, spins, and rotation widget. It sets values from `self.settings`, refreshes color buttons, and updates numeric labels. In `_reset_defaults()`:

  ```python
  self.settings = LightSettings()
  self.material_name = "光泽塑料"
  self._sync_controls_from_settings()
  self.material_changed.emit(self.material_name)
  self._emit_change_now()
  ```

  Delete `self.close()`. Emit only after all controls show defaults.

- [ ] **Step 5: Run dialog tests and commit**

  Run: `uv run pytest tests/test_lighting_dialog.py tests/test_lighting.py tests/test_dialog_theming.py -q`

  Expected: PASS; the dialog remains open and every readout/control agrees with default settings.

  Commit:

  ```bash
  git add ui/lighting_dialog.py tests/test_lighting_dialog.py
  git commit -m "fix: reset lighting controls in place"
  ```

<!-- openspec-task: 10.2 -->
### Task 6: Constrain lecture content to an 80%-height scroll area

**Files:**
- Modify: `ui/linear_algebra_dialog.py`
- Modify: `tests/test_linear_algebra_dialog.py`

**Interfaces:**
- Produces: `content_scroll: QScrollArea` with `widgetResizable(True)` and `ScrollBarAsNeeded` policies.
- Produces: `showEvent()` maximum height `int(screen.availableGeometry().height() * 0.8)`.
- Preserves: the current tree/search actions, frameless popup behavior, and short-content natural layout.

- [ ] **Step 1: Add failing scroll-area and maximum-height tests**

  Extend `tests/test_linear_algebra_dialog.py`:

  ```python
  def test_content_is_owned_by_a_widget_resizable_scroll_area() -> None:
      dialog = make_linear_algebra_dialog()
      assert dialog.content_scroll.widget() is dialog.content_view
      assert dialog.content_scroll.widgetResizable()
      assert dialog.content_scroll.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded


  def test_show_limits_dialog_to_eighty_percent_of_available_screen(monkeypatch) -> None:
      dialog = make_linear_algebra_dialog()
      screen = FakeScreen(QRect(0, 0, 1200, 1000))
      monkeypatch.setattr(dialog, "screen", lambda: screen)
      dialog.show()
      QApplication.processEvents()
      assert dialog.maximumHeight() == 800
      assert dialog.height() <= 800
  ```

  Add long-content and short-content cases: long content makes `verticalScrollBar().maximum() > 0`; short content leaves it at 0 after layout processing.

- [ ] **Step 2: Run the focused tests and reproduce unbounded content**

  Run: `uv run pytest tests/test_linear_algebra_dialog.py -q`

  Expected: FAIL because `content_view` is inserted directly and `showEvent()` does not constrain height.

- [ ] **Step 3: Wrap only lecture content in a transparent scroll area**

  Import `QScrollArea` and create:

  ```python
  self.content_scroll = QScrollArea(self)
  self.content_scroll.setObjectName("linearAlgebraContentScroll")
  self.content_scroll.setWidgetResizable(True)
  self.content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
  self.content_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
  self.content_scroll.setWidget(self.content_view)
  layout.addWidget(self.content_scroll)
  ```

  Remove the previous direct `layout.addWidget(self.content_view)`. Synchronize `content_scroll` visibility with whether lecture content is visible so an empty/short catalog view does not reserve a blank region.

- [ ] **Step 4: Apply the active-screen height limit on every show**

  Implement:

  ```python
  def showEvent(self, event: QShowEvent) -> None:
      screen = self.screen() or QApplication.primaryScreen()
      if screen is not None:
          self.setMaximumHeight(int(screen.availableGeometry().height() * 0.8))
      super().showEvent(event)
  ```

  After content changes, call `adjustSize()` but cap the final height at `maximumHeight()`. Do not force a fixed height; short content must retain a zero scrollbar range.

- [ ] **Step 5: Run lecture and loading regressions, then commit**

  Run: `uv run pytest tests/test_linear_algebra_dialog.py tests/test_linear_algebra_loading.py tests/test_linear_algebra_explanations.py -q`

  Expected: PASS for long internal scrolling, screen-bound dialog height, and short content without an unnecessary scrollbar.

  Commit:

  ```bash
  git add ui/linear_algebra_dialog.py tests/test_linear_algebra_dialog.py
  git commit -m "fix: constrain lecture dialog content height"
  ```

<!-- openspec-task: 11.1 -->
### Task 7: Run the complete regression and artifact validation matrix

**Files:**
- Verify: `tests/`
- Verify: `ui/agent_web/src/`
- Verify: `ui/agent_web/dist/`
- Verify: `openspec/changes/improve-dark-theme-and-typography/`

**Interfaces:**
- Verifies: all Python tests, all frontend tests, TypeScript compilation through the Vite build, generated Agent assets, and strict OpenSpec validation.
- Produces: no source change when all preceding tasks are complete.

- [ ] **Step 1: Run focused suites for every changed subsystem**

  Run:

  ```powershell
  uv run pytest tests/test_ui_tokens.py tests/test_ui_typography.py tests/test_native_chrome.py tests/test_math_input_theme.py tests/test_panel_resize_handle.py tests/test_lighting_dialog.py tests/test_2d_geometry_toolbar.py tests/test_agent_settings.py tests/test_linear_algebra_dialog.py -q
  ```

  Expected: PASS.

- [ ] **Step 2: Run the full Python suite**

  Run: `uv run pytest tests -q`

  Expected: PASS, including existing 2D toolbar, linear algebra loading, Agent Web theme/bootstrap, sidebar visibility, scene theme, and icon tests.

- [ ] **Step 3: Run the complete frontend suite and production build**

  Run:

  ```powershell
  Push-Location ui/agent_web
  pnpm test
  pnpm build
  Pop-Location
  ```

  Expected: Vitest PASS and Vite emits a fresh `dist/manifest.json` whose referenced files all exist.

- [ ] **Step 4: Validate packaging and OpenSpec consistency**

  Run:

  ```powershell
  uv run pytest tests/test_agent_web_assets.py tests/test_agent_web_packaging.py tests/test_documentation.py -q
  openspec validate improve-dark-theme-and-typography --strict
  ```

  Expected: PASS. If any command fails, return to the owning mapped task instead of making an untested release-only patch: typography/QSS → 1.1–1.4/7.1/9.3; native chrome → 2.1–2.2; MathInput → 3.1–3.6; Agent Web → 1.5/4.1–4.3/8.1–8.4; panels → 5.1–5.3; lighting → 6.1/10.1; toolbar/icons → 7.2/9.1–9.2; lecture dialog → 10.2.

- [ ] **Step 5: Confirm the verification task has no accidental source diff**

  Run: `git status --short` and inspect `git diff --check`.

  Expected: only intentional task commits and the rebuilt `ui/agent_web/dist/` state are present; no new commit is required for this verification-only task unless a preceding mapped task was corrected and retested.

<!-- openspec-task: 11.2 -->
### Task 8: Record the complete dark-theme walkthrough with screenshots

**Files:**
- Create: `openspec/changes/improve-dark-theme-and-typography/verification/dark-theme-walkthrough.md`
- Create: `openspec/changes/improve-dark-theme-and-typography/verification/01-main-shell-dark.png`
- Create: `openspec/changes/improve-dark-theme-and-typography/verification/02-math-input-dark.png`
- Create: `openspec/changes/improve-dark-theme-and-typography/verification/03-lighting-dialog-dark.png`
- Create: `openspec/changes/improve-dark-theme-and-typography/verification/04-agent-sidebar-dark.png`
- Create: `openspec/changes/improve-dark-theme-and-typography/verification/05-dialogs-dark.png`

**Interfaces:**
- Produces: a reviewable checklist linking each screenshot to the relevant OpenSpec scenario.
- Verifies: title bar, algebra/MathInput surfaces, lighting, panel boundaries, overlay toolbar, status bar, Agent sidebar, and dialogs have no light-only residue.

- [ ] **Step 1: Start from a deterministic dark-theme state**

  Launch the app with the effective theme set to dark. Use a window size wide enough to show algebra, viewport, and Agent panels together; set Agent width near 720px and algebra near 320px. Load at least one long formula and one geometry object, open one completed Agent response, and keep representative controls focused/hovered as specified below.

- [ ] **Step 2: Capture the five fixed screenshots**

  Capture:

  1. `01-main-shell-dark.png`: native title bar, algebra panel, viewport overlay toolbar, both visible divider strips, and status bar.
  2. `02-math-input-dark.png`: formula list with selected/hovered rows, horizontally scrolled long formula, formula editor popup, and preview/fallback state where practical.
  3. `03-lighting-dialog-dark.png`: dark rotation card, live ambient/intensity readouts, and dialog remaining open after reset.
  4. `04-agent-sidebar-dark.png`: 720px Agent panel with compact response, pinned/unpinned timeline evidence, model popover, 28px controls, and Chinese copy.
  5. `05-dialogs-dark.png`: Agent settings circle visibility control plus a long linear-algebra lecture scrolling inside the 80%-height dialog.

  Crop only outside desktop chrome; do not edit colors or hide visual defects.

- [ ] **Step 3: Write the walkthrough index with explicit pass criteria**

  Create `dark-theme-walkthrough.md`:

  ```markdown
  # Dark Theme Walkthrough — improve-dark-theme-and-typography

  | Surface | Evidence | Pass criteria | Result |
  | --- | --- | --- | --- |
  | Native title bar and shell | [01-main-shell-dark.png](01-main-shell-dark.png) | Title bar, panels, overlays, dividers, and status bar use dark/token colors; focused control has a visible 2px accent ring. | PASS |
  | MathInput surfaces | [02-math-input-dark.png](02-math-input-dark.png) | No white row/editor/preview surface; selection remains readable; long formula scrolls with no visible scrollbar. | PASS |
  | Lighting dialog | [03-lighting-dialog-dark.png](03-lighting-dialog-dark.png) | Rotation card is token-dark, values are readable, reset leaves dialog open. | PASS |
  | Agent sidebar | [04-agent-sidebar-dark.png](04-agent-sidebar-dark.png) | Compact 12px/1.5 reading layout, centered 620px measure, Chinese copy, usable 720px width. | PASS |
  | Settings and lecture dialogs | [05-dialogs-dark.png](05-dialogs-dark.png) | Circle icon is SVG/tinted; lecture scrolls internally and stays within screen. | PASS |
  ```

  Add a short note naming OS, Qt version, display scaling, and the date; do not paste logs or modify proposal/design/tasks.

- [ ] **Step 4: Cross-check every screenshot against the scenario list**

  Re-open the five images and verify: no pale title bar; no white MathInput/lighting block; both dividers visible; 2D/3D text uses token scale; distinct 2D icons; focus ring visible; Agent copy Chinese; model popover dismissible; API-key circle icon correct; lighting reset/readouts correct; long lecture contained. Recapture any image that does not visibly prove its criteria.

- [ ] **Step 5: Commit only the new verification evidence**

  ```bash
  git add openspec/changes/improve-dark-theme-and-typography/verification
  git commit -m "docs: record dark theme walkthrough"
  ```

  Expected: five PNG files and one Markdown index are added; no existing OpenSpec artifact is modified.
