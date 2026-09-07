# Implementation Plan: 深色主题覆盖缺口、字体体系、阅读密度与 UI 可用性修复

基于 `design.md`（D1–D12）与 `tasks.md`（34 项）的可执行计划。任务按**波次（Wave）**组织：同文件改动合并在同一波次内一次完成，避免来回编辑冲突；每波次有独立验收命令与回滚点。

## 运行约定

```powershell
# Qt 测试（单文件）
uv run pytest tests/test_xxx.py -q
# Qt 全量
uv run pytest tests -q
# Web 测试 / 构建（在 ui/agent_web 下）
pnpm test
pnpm build            # prebuild 自动跑 gen-theme（读 tokens.json）
# QSS 生成冒烟
uv run python -m ui.tokens build
# 工件校验
openspec validate improve-dark-theme-and-typography --strict
```

前置检查：工作区已有其他变更的未提交修改（`ui/algebra_panel.py`、`ui/designer_window.py`、`ui/two_d_tools.py` 等属于 `expand-linear-algebra-lecture-tree`），实施时**保留这些改动**，在其之上叠加；每波次结束跑一次相关测试确认无回归。

## Wave 0 — 令牌基座（对应任务 1.1）

| 任务 | 改动点 | 要点 | 验收 |
| --- | --- | --- | --- |
| 0.1 | `design/tokens.json` | `font` 节点加 `"family_stack": ["Segoe UI","Microsoft YaHei UI","PingFang SC","Noto Sans CJK SC"]` | `uv run pytest tests/test_ui_tokens.py -q` |
| 0.2 | `ui/tokens.py` | loader 校验 `family_stack` 为非空字符串列表（沿用现有 `_check` 风格）；导出 `font_family_stack(theme="light")` 返回 list；`_flat` 中保留为 list 不 join | 新增断言：非法值（空列表/非字符串）抛错；`uv run pytest tests/test_ui_tokens.py -q` |

注意：`agent_web/scripts/gen-theme.mjs` 读 tokens.json 生成 theme.css——检查它是否需要同步输出字体栈（若 gen-theme 已透传 font 节点则 0 改动，否则 Wave 4 处理）。

## Wave 1 — QSS 与应用字体（任务 1.2/1.3/1.4/5.1-部分/7.1/9.3-部分）

`base.qss.in` **一次性**完成全部模板改动：

| 任务 | 位置 | 改动 |
| --- | --- | --- |
| 1.1 | `QToolButton` 规则（27 行附近） | 加 `font-size: $font_caption;`；默认 `border: 2px solid transparent;`（焦点环占位，见 1.5） |
| 1.2 | 新增规则 | `QMenu, QComboBox QAbstractItemView { font-size: $font_body; }`、`QToolTip { font-size: $font_caption; }`、`QTreeView, QListView, QListWidget { font-size: $font_body; }` |
| 1.3 | `#appStatusBar` 块（229 行附近） | 加 `#appStatusBar QToolButton { font-size: $font_caption; }` |
| 1.4 | `#sceneModeButton`（138 行） | `font-size: 18px` → `font-size: $font_title;` |
| 1.5 | 焦点规则（33-34 行） | 删除 `*:focus-visible` 整块；`QToolButton:focus, QPushButton:focus { border-color: $accent_default; }`（默认 2px transparent 占位已防跳动）；其余控件 `:focus` 保持 `border-color: $accent_default` |
| 1.6 | 新增手柄规则 | `#panelResizeHandle { border-left: 1px solid $border_default; }` + `#panelResizeHandle:hover, #panelResizeHandle[dragging="true"] { background: $accent_soft_bg; border-left: 2px solid $accent_default; }` |

其余：

| 任务 | 改动点 | 要点 |
| --- | --- | --- |
| 1.7 | `main.py:44` | 按 D3 代码块改：`setFamilies(font_family_stack())` + `setPixelSize(12)` + `PreferAntialias` |
| 1.8 | `ui/agent_sidebar.py:108/138/150/169` | 删四处内联 `font-size: 14px` 标题样式（标题复用 QSS `#sectionHeader`） |

验收：`uv run pytest tests/test_ui_typography.py tests/test_ui_tokens.py tests/test_app_status_bar.py -q`；新增断言——app font `pixelSize()==12`、families 含 `Microsoft YaHei UI`；生成 QSS 含 `:focus` accent 规则、不含 `focus-visible`、不含 `18px`、含 `#appStatusBar QToolButton` 与 `#panelResizeHandle`。

## Wave 2 — 标题栏与主窗口（任务 2.1/2.2/5.2/9.3-部分）

| 任务 | 改动点 | 要点 |
| --- | --- | --- |
| 2.1 | 新建 `ui/native_chrome.py` | D1 接口：`apply_native_titlebar_theme(window, theme)->bool` + `install_titlebar_tracker(app)`；ctypes 包在 try/except，`sys.platform != "win32"` 直接返回 False |
| 2.2 | `main.py` | `install_titlebar_tracker(app)`（QApplication 创建后） |
| 2.3 | `designer_window.py` `_apply_style`（3633-3636） | setStyleSheet 后：`app.setProperty("math3d_effective_theme", effective_theme)` + 遍历 `QApplication.topLevelWidgets()` 调 `apply_native_titlebar_theme` |
| 2.4 | `designer_window.py:416` | `PanelResizeSpec(360, 560, 440, ...)` → `(360, 720, 440, ...)` |
| 2.5 | `ui/agent_sidebar.py:33-34` | `MIN_WIDTH=360` 保持、`MAX_WIDTH=560→720` |
| 2.6 | `designer_window.py` 主控件 | `scene_mode_button`/`scene_settings_button`/`agent_button`/状态栏三控件补 `setAccessibleName`（复用 tooltip 文本） |

验收：`uv run pytest tests/test_native_chrome.py tests/test_ui_design_integration.py -q`（新建前者：monkeypatch dwmapi 断言 dark=1/light=0、非 win32 零调用、tracker 对新 Show 顶层窗口生效）；适配既有 560 上限断言到 720。

## Wave 3 — MathInputWidget 主题化（任务 3.1–3.6，最大波次）

顺序：先生成器，再组件桥，再 HTML，最后转发。

| 任务 | 改动点 | 要点 |
| --- | --- | --- |
| 3.1 | 新建 `MathInputWidget/theme_tokens.py` | D2 的 14 变量映射表；`math_input_theme_css()` 生成 `:root{}` + `[data-theme=dark]{}`；单测对照 tokens.json 逐变量断言 |
| 3.2 | 新建 `MathInputWidget/theme_bridge.py` | `ThemeBridge(view)`：`install(theme)`（QWebEngineScript DocumentCreation 注入 style 块 + dataset）、`set_theme(t)`（loaded→runJavaScript；未加载→pending，loadFinished 应用）；参照 `agent_sidebar_web.py:62-69,118-124` |
| 3.3 | `formula_list.py` `_ensure_web_view`（86-110） | 接入 ThemeBridge；新增公开 `set_theme(theme)` |
| 3.4 | `widget.py`（MathInputWidget） | 同上接入 ThemeBridge + `set_theme` |
| 3.5 | `formula_preview.py` | 同上；并删 `:73` 内联 `color:#1f2937`（走 QSS `#formulaPreviewFallback`） |
| 3.6 | `inline_formula_overlay.py:76` 附近 | 同上接入 + `set_theme` |
| 3.7 | `formula_list.html` | 全部颜色字面值 → `var(--mi-x, 原值)`；`.formula-cell` 加 `overflow-x:auto; scrollbar-width:none;` + `::-webkit-scrollbar{display:none}`（S5）；四处英文文案改中文（D2 清单） |
| 3.8 | `mathlive.html` / `inline_formula_overlay.html` / `formula_preview.html` | 颜色 → `var(--mi-*)`；MathLive selection/toolbar 变量接入；`[data-theme="dark"]` 补深色覆盖 |
| 3.9 | `ui/algebra_panel.py` `sync_overlay_theme`（214 行） | 追加转发到 `formula_list`/`formula_popup.editor`/`_inline_overlay`/预览组件的 `set_theme` |
| 3.10 | `designer_window.py` | 确认 `_apply_style` 既有 `sync_overlay_theme` 调用覆盖公式弹窗场景；必要时对 `formula_popup` 单独同步 |

验收：`uv run pytest tests/test_math_input_theme.py tests/test_algebra_panel.py -q`（新建前者：变量完整性、ThemeBridge 三态、切换不触发 reload——断言 `setUrl` 调用次数不变）；offscreen WebEngine 已可用（conftest 已配）。

## Wave 4 — Agent Web（任务 1.5/4.1–4.3/8.1–8.4）

| 任务 | 改动点 | 要点 |
| --- | --- | --- |
| 4.1 | `styles/theme.css` | 两组 `--agent-font-family` 改带引号字体栈（若由 gen-theme 生成则改 `scripts/gen-theme.mjs` 源） |
| 4.2 | `styles/layout.css` | D4 密度 7 处数值；D11 下限（`.turn-actions`/`model-details`/`capability-desc`→11px；`.turn-action`→28px；`.attachment-btn`→28×28；`.context-ring` SVG 特例同步 viewBox 16→18） |
| 4.3 | `components/Timeline.tsx:40-44` | D7 状态机：`scrollRef`/`pinnedRef`/`handleScroll`，sessionId 切换与新 user turn 重置 pinned=true |
| 4.4 | `components/HistoryView.tsx:15-19` | `cancelledRef` 短路 blur 保存；History→历史、No conversations→暂无会话、N turns→N 轮 |
| 4.5 | `components/ModelSelector.tsx:41-48` | 复制 `AttachmentActions.tsx:22-35` rootRef+document 监听模式；触发按钮 `aria-haspopup="listbox"` `aria-expanded={open}` |
| 4.6 | `components/SettingsView.tsx` | 标题/aria-label 中文化（Settings→设置、Skills→技能、Memory→记忆、Rules→规则、Back to conversation→返回会话 等） |
| 4.7 | 测试 | `Timeline.test.tsx`（贴底三场景）、`HistoryView.test.tsx`（Escape/Enter/blur）、`ModelSelector.test.tsx`（Esc/外部点击/aria） |

验收：`pnpm test` 全绿；`pnpm build` 后 grep dist 产物含 `Microsoft YaHei UI` 与 `12px` 密度值。

## Wave 5 — Qt 组件收尾（任务 6.1/7.2/9.1/9.2/10.1/10.2）

| 任务 | 改动点 | 要点 |
| --- | --- | --- |
| 5.1 | `widgets/LightRotationWidget.py` | D10 取色映射表；新增 `set_theme(flat)`（存色+`update()`）；`__init__` 默认用 light 令牌初始化 |
| 5.2 | `ui/lighting_dialog.py` | `set_effective_theme` 调 `rotation_widget.set_theme(flatten_theme(t))`；`_reset_defaults`（204 行）删 `self.close()`、回写全部控件（滑块/spinbox/颜色按钮/rotation）；环境光与三组强度滑块旁加 caption 数值 QLabel 随 `valueChanged` 更新 |
| 5.3 | `ui/icons.py` | `LUCIDE_SVG` 加 `pen-line`/`vector`/`angle`/`circle-filled`/`circle-outline`（D9 path 表，lucide stroke 风格一致） |
| 5.4 | `ui/two_d_tools.py:42-71` | 图标映射去重（`linearVectorToolButton`→`vector`、`lineToolButton`→`pen-line`、`angleToolButton`→`angle`） |
| 5.5 | `ui/two_d_tools.py:182-188` | D8 flyout 键盘可达：点击切换、方向键、Enter、Esc 回焦；保留 hover 行为 |
| 5.6 | `ui/agent_settings.py:96` | 👁 → `apply_icon` 显隐圆点（可见=`circle-filled`、隐藏=`circle-outline`），主题切换随 `retint_icons` |
| 5.7 | `ui/linear_algebra_dialog.py:42-50` | `title_row`+`content_view` 包 `QScrollArea(widgetResizable)`；`showEvent` 设 `setMaximumHeight(screen 可用高 80%)` |

验收：`uv run pytest tests/test_lighting_dialog.py tests/test_2d_geometry_toolbar.py tests/test_linear_algebra_dialog.py tests/test_ui_icons.py tests/test_icon_theming.py tests/test_agent_settings.py -q`，新增：重置不关闭、图标唯一性（同栏两按钮 icon_name 不同）、flyout 键盘流程、弹窗限高。

## Wave 6 — 回归与走查（任务 11.1/11.2）

1. `uv run pytest tests -q` 全量；`pnpm test` 全量。
2. 深色主题全表面走查（真机）：标题栏 / 代数面板（公式列表+编辑弹窗+行内覆盖+预览兜底）/ 光照对话框 / 三栏边界手柄 / 悬浮工具栏 / 状态栏 / Agent 侧栏 / 各对话框——截图存变更目录 `verification/`。
3. MathLive 虚拟键盘与菜单深色真机核对（风险表项）。
4. `openspec validate improve-dark-theme-and-typography --strict`。

## 依赖与并行度

```
Wave 0 ─► Wave 1 ─► Wave 2 ─┐
   └──────► Wave 3 ──────────┼─► Wave 6
   └──────► Wave 4 ──────────┤
   └──────► Wave 5 ──────────┘
```

Wave 2/3/4/5 互不依赖可并行（不同文件集）；Wave 3 是最大块，独占 MathInputWidget 目录。每波次完成后更新 `tasks.md` 对应 checkbox。

## 回滚点

- Wave 1 失败：QSS 模板与 main.py 为纯样式层，直接 git checkout 两文件。
- Wave 3 失败：MathInputWidget 新增两文件可删，HTML 改动可单文件回退；Qt 侧转发是追加式，删除即恢复原行为。
- Wave 4 失败：`git checkout ui/agent_web`（含 dist）。
