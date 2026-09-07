# Design: 深色主题覆盖缺口、字体体系、阅读密度与 UI 可用性修复

## Context

上一轮 ui-design-refresh 的令牌体系覆盖了 Qt QSS 与 Agent Web，但多个表面逃逸在外：平台原生标题栏、MathInputWidget 的四个 WebView 页面、以磅为单位的应用字体、Agent 时间线的密度与侧栏手柄的可发现性，以及探索确认的十五处系统性缺口。本变更不引入新框架或新依赖，只把既有令牌管线延伸到这些表面并修复交互缺陷。所有产品层取舍已由用户逐项确认（见文末"已确认的产品决策"）。

## Goals / Non-Goals

- Goals: 深色主题下无任何浅色残留表面；中英文字体栈一致、全部 chrome 控件字号回落到同一基准；Agent 回复同等内容行数减少约 15–25%；侧栏手柄一眼可发现、拖拽范围放宽；键盘导航、公式查看、流式阅读、弹层关闭等基础交互无缺陷。
- Non-Goals: 不做用户自定义字号/密度设置界面（仅收紧默认值）；不改 Agent 会话/桥接协议语义（复用既有 `theme_state` 模式，不新增事件类型）；不替换 MathLive 或公式渲染引擎；不实现自定义无边框标题栏（继续使用平台原生 chrome）；不做无边框弹窗屏幕越界钳制（用户明确排除 S4）。

## 主题传播链路（全局数据流）

```
tokens.json ──► tokens.py (flatten) ──► build_qss(theme) ──► QSS 字符串
     │                                      │
     │                                      ▼
     │                            designer_window._apply_style()
     │                              ├─ window.setStyleSheet(qss)
     │                              ├─ sync_overlay_theme() ──► AlgebraPanel ──► MathInput×3 set_theme
     │                              ├─ apply_icon() 重着色（各按钮）
     │                              ├─ agent_sidebar.set_theme() ──► theme_state 事件
     │                              ├─ scene_settings / lighting_dialog.set_effective_theme()
     │                              └─ native_chrome：标题栏 + app 属性记录当前主题
     │
     └──► MathInputWidget/theme_tokens.py ──► --mi-* CSS 变量块 ──► 4 个 WebView 注入
```

新接入点只有三个：`_apply_style` 尾部（标题栏）、`AlgebraPanel.sync_overlay_theme`（MathInput）、`LightingDialog.set_effective_theme`（旋转控件）。其余组件走既有链路。

## D1. 原生标题栏 —— `ui/native_chrome.py` 新模块

**接口**

```python
def apply_native_titlebar_theme(window: QWidget, effective_theme: str) -> bool
    """Windows 上设置 DWMWA_USE_IMMERSIVE_DARK_MODE(20)；其他平台/失败返回 False。"""

def install_titlebar_tracker(app: QApplication) -> None
    """装 app 级 eventFilter：顶层窗口 Show 时按 app 属性记录的当前主题应用标题栏。"""
```

**机制**

- Windows：`ctypes.windll.dwmapi.DwmSetWindowAttribute(int(window.winId()), 20, byref(c_int(1 if dark else 0)), 4)`，HRESULT==0 为成功。`windll`/`dwmapi` 属性不存在（非 Windows、旧系统）即静默返回 False。
- 主题记录：`_apply_style` 把当前 `effective_theme` 写到 `app.setProperty("math3d_effective_theme", ...)`；tracker 读它。这解决"主题切换后才创建的对话框"（Agent 设置/光照/记忆对话框）标题栏不跟随的问题——新窗口 Show 时 tracker 自动应用，无需在每个对话框创建点插代码。
- `_apply_style` 同时遍历 `QApplication.topLevelWidgets()` 对已存在窗口立即应用（主题切换即时生效）。
- 测试：monkeypatch `ctypes.windll` 记录调用参数；monkeypatch `sys.platform` 断言非 Windows 零调用零异常。

**备选及排除**：切换 QApplication palette 让 Qt 自动处理（Qt 6.8+ 才有可靠 API，且 palette 与 QSS 大面积互相干扰，风险高）；在每个对话框创建点手动调用（遗漏风险，tracker 一处兜底）。

## D2. MathInputWidget 主题化 —— 变量注入 + data-theme

**新模块 `MathInputWidget/theme_tokens.py`**

```python
def math_input_theme_css() -> str
    """从 tokens.json 生成 ':root{--mi-*} [data-theme=dark]{--mi-*}' 变量块。"""
def math_input_theme_script(theme: str) -> str
    """DocumentCreation 注入：插入 <style id='mi-theme-vars'> + 设 documentElement.dataset.theme。"""
```

**变量清单**（取自 formula_list.html/mathlive.html 现有硬编码值，HTML 内统一写成 `var(--mi-x, 浅色字面值)` 保证无注入时可调试）

| 变量 | 浅色默认（现值） | 令牌来源 |
| --- | --- | --- |
| `--mi-bg-panel` | `#ffffff` | `bg.panel` |
| `--mi-text-primary` | `#1f2937` | `text.primary` |
| `--mi-row-bg` | `#f9fafb` | `bg.elevated` |
| `--mi-border` | `#cfd8e1` | `border.default` |
| `--mi-selected-bg` | `#eaf2fd` | `accent.soft_bg` |
| `--mi-selected-border` | `#8ab4f8` | `accent.default` |
| `--mi-btn-hover` | `#eef2f5` | `bg.elevated` |
| `--mi-editing-bg` | `#fffdf4` | `bg.overlay` |
| `--mi-editing-border` | `#e59b00` | 常量保留（警示琥珀，两主题可读） |
| `--mi-focus` | `#2f7ebd` | `accent.default` |
| `--mi-toolbar-bg` | `#2c2e2f` | 常量保留（MathLive 工具栏为深色菜单） |
| `--mi-toolbar-accent` | `#2f7ebd` | `accent.default` |
| `--mi-toolbar-hover` | `#eeeeee` | 常量（dark 用 `#3a3d40`） |
| `--mi-layer-fallback` | `#8ab4f8` | `accent.default` |

**组件桥**：新 `MathInputWidget/theme_bridge.py` 的 `ThemeBridge(view)` 封装三态逻辑（与 `AgentSidebarWeb._pending_theme` 同构）：

```
install(theme):  page.scripts().insert(QWebEngineScript(DocumentCreation, math_input_theme_script(theme)))
set_theme(t):    页面已加载 → runJavaScript("document.documentElement.dataset.theme='...'")
                 未加载 → 缓存 _pending_theme，loadFinished 时应用
```

应用到 4 个宿主：`FormulaListWidget`（formula_list.html）、`MathInputWidget`（mathlive.html）、`FormulaPreviewWidget`（formula_preview.html）、`InlineFormulaEditorOverlay`（inline_formula_overlay.html，`inline_formula_overlay.py:76`）。`AlgebraPanel.sync_overlay_theme` 追加转发；`designer_window._apply_style` 已调它，无新链路。`formula_preview.py:73` 兜底标签删除内联 `color:#1f2937`（objectName `formulaPreviewFallback` 已在 QSS 用令牌色）。

**MathLive 深色**：mathlive.html 中 `--selection-background-color` 等浅色值改为 `var(--mi-*)`；`[data-theme="dark"]` 下补 `--contains-highlight-background-color` 等。

**长公式滚动（S5）**：`formula_list.html` 的 `.formula-cell` 改 `overflow-x: auto; scrollbar-width: none;` + `&::-webkit-scrollbar{display:none}`；`math-field` 保持 `nowrap`；`body` 保持 `overflow-x:hidden`（行级滚动发生在单元格内）；`visibility-button` 绝对定位于 `.formula-row` 不随内容滚动，无需调整。

**文案中文化**：`'Hide function'/'Show function'` → `'隐藏函数'/'显示函数'`，`'Function display and sampling settings'` → `'函数显示与采样设置'`，aria-label `'Formula'/'Geometry object'` → `'公式'/'几何对象'`，`'Delete'` → `'删除'`。

## D3. 像素级字体体系

**tokens.json** 增 `"family_stack": ["Segoe UI", "Microsoft YaHei UI", "PingFang SC", "Noto Sans CJK SC"]`；`tokens.py` 校验为非空字符串列表，导出 `font_family_stack()`（`family_default` 保留兼容）。

**main.py**

```python
font = QFont()
font.setFamilies(font_family_stack())   # Qt6 setFamilies 支持 fallback 链
font.setPixelSize(12)                   # = token body；杜绝 12pt→16px
font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
app.setFont(font)
```

**base.qss.in 补充**（全部走令牌变量）：`QToolButton { font-size: $font_caption }`、`QMenu / QComboBox QAbstractItemView { font-size: $font_body }`、`QToolTip { font-size: $font_caption }`、`QTreeView / QListView / QListWidget { font-size: $font_body }`、`#appStatusBar QToolButton { font-size: $font_caption }`、`#sceneModeButton { font-size: $font_title }`（替换 18px 硬编码）。

**web 侧**：`theme.css` 两组 `--agent-font-family` 改带引号 `"Segoe UI", "Microsoft YaHei UI", "PingFang SC", sans-serif`。

**清理**：`agent_sidebar.py` 四处内联 `font-size: 14px` 删除，改 QSS `#sectionHeader`。

## D4. Agent 阅读密度

`layout.css` 数值（vs 现值）：`.assistant-content` 13px/1.55→**12px/1.5**；`.event-card` padding 11px 12px→**8px 10px**、margin 8px→**6px**、13px→**12px**；`.turn-block` 下边距 28→**18px**；`.timeline` padding 22px 16px 24px→**16px 14px 20px**；`.markdown-content p` margin 7→**6px**；`.reasoning-block` padding 8px 10px→**7px 9px**、12px→**11px**；`.thinking-section` margin 10px 0 12px→**8px 0 10px**。改后 `pnpm build`（prebuild 自动跑 gen-theme）。`.user-message` 与 hover-only turn actions 布局不变（spec 锁定行为）。

## D5. 侧栏手柄可发现 + 720px

- `_PanelResizeHandle`：`setObjectName("panelResizeHandle")`、`setToolTip("拖动调整宽度，双击复位")`；press/release 维护 `dragging` 动态属性并 `style().unpolish/polish`；`FIXED_WIDTH` 5→6。
- QSS：`#panelResizeHandle { border-left: 1px solid $border_default }`、`#panelResizeHandle:hover, #panelResizeHandle[dragging="true"] { background: $accent_soft_bg; border-left: 2px solid $accent_default }`。
- 范围：`AgentSidebar.MIN/MAX_WIDTH` 与 `_install_agent_panel` 的 `PanelResizeSpec(360, 720, 440, ...)`、`set_panel_width` clamp 常量同步。既有持久化宽度 560 内的旧值不受影响；曾 clamp 到 560 的值自然解封。

## D6. 焦点环 —— Qt 伪态修复

现状双重失效：`:focus-visible`（Qt 不支持，整条丢弃）+ `:focus` 只改 `border-color` 但 QToolButton/QPushButton 默认 `border:0` 无边框可变。修复：

- 删除 `:focus-visible` 规则块。
- `QToolButton / QPushButton { border: 2px solid transparent }`（默认占位防跳动），`:focus` 时 `border-color: $accent_default`。36px 固定尺寸按钮内缩 2px，图标仍居中。
- `QComboBox/QSpinBox/QDoubleSpinBox/QSlider/QLineEdit/...:focus` 保持 `border-color: $accent_default`（已有边框）。
- 鼠标点击后焦点环停留是 Qt 默认行为，与 VSCode 一致；不实现 keyboard-only 区分（Qt 侧成本过高）。

## D7. 时间线贴底跟随 —— 状态机

`Timeline.tsx`：

```
state: pinnedRef（默认 true）
onScroll(容器 .timeline): pinnedRef = scrollHeight - scrollTop - clientHeight < 40
流式 effect [turns.length, events.length, assistantText, reasoningText, progressLogs.length]:
    if pinnedRef → endRef.scrollIntoView({block:"nearest"})
会话切换 effect [sessionId]: pinnedRef = true
新 user turn（pending）出现: pinnedRef = true   // 用户刚发消息必然想看自己消息
```

vitest：jsdom 模拟 scrollTop/scrollHeight，覆盖"上翻+流式不回弹""贴底+流式跟随""发送后强制回底"三场景。

## D8. 线工具 flyout 键盘可达

保留 hover 展开，新增：点击 `line_button` 在浮层关时展开、已选线工具时再点击折叠；浮层打开时焦点给第一个按钮；浮层内按钮进 Tab 链；方向键 ←/→（竖排布局 ↑/↓）循环移动、`Enter/Space` 选择（走既有 `_activate_line_tool`）、`Esc` 关闭并回焦 `line_button`。实现放 `TwoDGeometryToolbar.keyPressEvent` + 浮层按钮 eventFilter，不改现有 hover/leave 逻辑。

## D9. 图标去重与显隐圆点

`icons.py` 的 `LUCIDE_SVG` 新增（全部参与 retint）：

| 名称 | 用途 | path（stroke 风格一致） |
| --- | --- | --- |
| `pen-line` | 线工具入口（lucide 官方） | 铅笔+横线 |
| `vector` | 3D 向量（自定义） | `<circle cx="5" cy="19" r="2" fill="currentColor" stroke="none"/><path d="M6.5 17.5 17 7"/><path d="M11 7h6v6"/>`（起点圆点+箭头线段，区别于射线 `arrow-up-right`） |
| `angle` | 角度测量（自定义） | 顶点左下的两射线+弧线（实施时打磨为 `<path d="M5 19h13"/><path d="M5 19 16 8"/><path d="M10.5 19a5.5 5.5 0 0 0-3.9-1.6"/>`） |
| `circle-filled` | API Key 可见态 | `<circle cx="12" cy="12" r="7" fill="currentColor" stroke="none"/>` |
| `circle-outline` | API Key 隐藏态 | `<circle cx="12" cy="12" r="7"/>` |

映射：`linearVectorToolButton`→`vector`（射线保留 `arrow-up-right`）；`lineToolButton`→`pen-line`（flyout 直线保留 `slash`、线段 `minus`）；`angleToolButton`→`angle`（投影保留 `corner-down-right`）。`agent_settings.py` 显隐按钮去 👁，按回显状态切换 `circle-filled`（可见）/`circle-outline`（隐藏），跟随主题 retint。新测试断言同栏任意两按钮 icon_name 不同。

## D10. 光照控件令牌化与对话框行为

`LightRotationWidget.set_theme(flat: dict)` 映射：

| 元素 | 现硬编码 | 令牌 |
| --- | --- | --- |
| 卡片 | `#f4f6f9` | `bg.elevated` |
| 标签 | `#475569` | `text.secondary` |
| 数值 | `#1d4ed8` | `accent.default` |
| 环渐变 | `#2563eb/#60a5fa/#1d4ed8` | `accent.default/hover/pressed` |
| 球渐变/边 | `#eef1f5…#727b88/#8b95a2` | `border.strong → text.muted` 渐变 |
| marker 边 | `#1e3a8a` | `text.primary` |
| 太阳/光线 | `#fbbf24/#f59e0b` | 常量保留（两主题可读） |

`LightingDialog.set_effective_theme` 调 `set_theme(flatten_theme(t))` + `update()`。`_reset_defaults` 移除 `self.close()`，重置后回写全部控件（滑块、spinbox、颜色按钮、`rotation_widget.set_rotation_from_elevation_angle`）并照常经 throttle 发一次 `material_changed`。环境光与每组强度滑块旁加 caption 样式数值 QLabel，随 `valueChanged` 实时更新。

## D11. Web 下限与文案、弹层、Escape

- `layout.css` 下限：`.turn-actions` 10→**11px**、`.model-details` 10→**11px**、`.capability-desc` 10→**11px**；`.turn-action` 25→**28px**、`.attachment-btn` 22×25→**28×28**。特例：`.context-ring .percent` 是 SVG 内 `<text>`（viewBox 16×16，8 为 SVG 单位），提升到 10 需同步把 SVG 尺寸 16→18 并重算 `textLength`，实施时核对渲染不裁切。
- `HistoryView.tsx`：`cancelledRef` 模式——Escape 置 true 后 `setEditing(false)`，blur 触发的 `save()` 首行 `if (cancelledRef.current) return`；Enter 正常保存。文案：History→历史、No conversations→暂无会话、N turns→N 轮。
- `ModelSelector.tsx`：复制 `AttachmentActions.tsx:22-35` 的 rootRef + document mousedown/keydown 模式补 Esc/外部点击关闭；触发按钮补 `aria-haspopup="listbox"` + `aria-expanded={open}`。
- `SettingsView.tsx`：Settings/Skills/Memory/Rules 标题与说明改中文（实施时逐条替换，复用 Qt 侧"技能/记忆/规则"术语）。

## D12. 讲义弹窗滚动限高

`LinearAlgebraDialog`：内容区（`title_row` + `content_view`）包入 `QScrollArea`（`widgetResizable`，QSS 已有 `QScrollArea{border:0;background:$bg_panel}` 样式）；`showEvent` 里 `setMaximumHeight(int(screen.availableGeometry().height()*0.8))`。空状态（content_view 隐藏）时滚动区同步隐藏，弹窗回到紧凑自然高度；长讲义在弹窗内滚动，整体不超出屏幕。

## 已确认的产品决策（探索确认轮）

- S4（无边框弹窗越界钳制）**明确排除**：公式编辑弹窗允许超出屏幕外侧；如日后反馈找回困难再单独立项。
- S5 长公式：**允许横向滚动但不显示滚动条**。
- M1 显隐图标：**实心圆=密码可见，空心圆=密码隐藏**，不用眼睛图形。
- Agent 面板宽度上限 720px（固定值，不随窗口百分比）。
- 密度数值按 D4 表固定收紧一档；"紧凑/舒适"双档设置不本期实现。

## 测试矩阵

**Qt（pytest + offscreen，monkeypatch）**

| 测试文件 | 覆盖 |
| --- | --- |
| `test_ui_typography.py`（扩展） | app font pixelSize==12、family_stack 含中文字体、QSS 新选择器字号断言、状态栏字号一致 |
| `test_native_chrome.py`（新） | dwmapi 调用参数 dark=1/light=0、非 Windows 零调用、tracker 对新建顶层窗口生效 |
| `test_math_input_theme.py`（新） | 变量块完整性（对照 tokens.json）、ThemeBridge 三态（pending/已加载/切换不重载） |
| `test_lighting_dialog.py`（扩展） | 重置不关闭、控件回写、数值读数、rotation_widget 两主题取色为令牌值 |
| `test_2d_geometry_toolbar.py`（扩展） | flyout 键盘全流程、同栏图标唯一性 |
| `test_linear_algebra_dialog.py`（扩展） | 长内容滚动、短内容无滚动条、最大高度≤屏幕 80% |
| `test_ui_icons.py`/`test_icon_theming.py`（扩展） | 新图标存在与 retint、显隐圆点切换 |
| 现有主题/布局测试 | 适配 720 上限与 `panelResizeHandle` objectName |

**Web（vitest + testing-library）**：`Timeline.test.tsx`（贴底三场景）、`HistoryView.test.tsx`（Escape 取消/Enter 保存）、`ModelSelector.test.tsx`（Esc/外部点击/aria-expanded）。

## 实施顺序与依赖

```
1. tokens.json + tokens.py（family_stack）
2. base.qss.in（字号/焦点环/手柄/18px）＋ main.py 字体
3. native_chrome.py + _apply_style 接入
4. MathInputWidget：theme_tokens/theme_bridge + 4×HTML + set_theme 桥 + 文案/滚动
5. agent_web：density/scroll/a11y/文案 → pnpm build
6. Qt 组件：光照、图标+显隐圆点+accessibleName、flyout、讲义弹窗
7. 全量回归 + 深色走查截图
```

依赖关系：2/3 依赖 1；4 依赖 1；5 依赖 1（gen-theme 读 tokens.json）；6 依赖 2（QSS 选择器）。

## Risks / Trade-offs

- **DWM 调用在旧 Windows/预览版可能返回错误码**：按 HRESULT 静默忽略，不影响 QSS 主题本身；测试用 monkeypatch 断言参数而非真机视觉。
- **QWebEngineScript 注入依赖 DocumentCreation 时机**：与 Agent 侧同模式已有先例；HTML 变量带回退默认值，注入失败仍呈浅色可读。
- **12px 正文字号对低视力用户偏小**：暂不做缩放设置（Non-Goal），令牌集中管理为将来 `font.scale` 留口。
- **720px 上限 vs 小屏幕**：clamp 永远受窗口宽度约束（布局收缩先于窗口最小宽），560→720 只是放宽上限而非默认值。
- **焦点环 2px transparent 边框占位**：图标按钮视觉内缩 2px，属可接受代价换取无跳动；如走查发现违和再降为 1px。
- **MathLive 内部 shadow DOM 变量穿透**：MathLive 组件读取宿主 CSS 变量是官方支持机制（mathlive 文档），但个别内部元素颜色若不受变量控制，深色下可能残留——实施时真机核对虚拟键盘与菜单。
