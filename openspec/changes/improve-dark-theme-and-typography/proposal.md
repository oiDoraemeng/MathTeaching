# Proposal: 深色主题覆盖缺口、字体体系、阅读密度与 UI 可用性修复

## Why

上一轮 ui-design-refresh 建立了令牌主题体系，但仍有四类表面未接入或配置错误，导致深色主题下界面割裂、字号失控、Agent 回复阅读体验差；探索式扫描又发现十五处系统性缺口（深色遗漏、可用性缺陷、图标与文案不一致、对话框行为粗糙）：

1. **标题栏不跟随深色主题**：主题切换只替换 QSS（`designer_window.py` `_apply_style`），从未通知平台原生窗口 chrome。Windows 上标题栏由 DWM 绘制，需要显式设置 `DWMWA_USE_IMMERSIVE_DARK_MODE` 才会变深；代码库中无任何此类调用。
2. **代数区域深色下泛白**：代数面板主体 `FormulaListWidget` 是加载 `MathInputWidget/formula_list.html` 的 WebView，HTML 内硬编码 `#ffffff`/`#f9fafb`/`#eaf2fd` 等浅色背景与选中色，完全不参与令牌主题体系；`mathlive.html`（公式编辑弹窗）、`inline_formula_overlay.html`、`formula_preview.html` 同样硬编码浅色。右侧 Agent Web 已令牌化，MathInputWidget 是遗留的第三块 Web 表面。
3. **全局字体以磅为单位设置导致字号失控**：`main.py` 以 `QFont("Segoe UI", 12)` 设置应用字体，构造器第二参数是磅值，12pt 在 96dpi 下约等于 16px；所有未被 QSS 字号覆盖的控件（状态栏 Agent 按钮、QMenu、下拉弹层、树/列表视图）渲染为 16px，与 QSS 指定的 11–12px 标签混排，产生"字体有大有小"；同时 `Segoe UI` 无中文字形，中文回退不受控，缺少 VSCode 式 `Segoe UI + Microsoft YaHei UI` 字体栈，观感生硬。
4. **Agent 回复密度松、侧栏宽度不可调的观感**：回复正文 13px/行高 1.55、事件卡 padding 11–12px、turn 间距 28px，同样内容占行数明显多于紧凑排版；侧栏分隔手柄虽功能存在（360–560px 拖拽、双击复位），但仅 5px 宽且无任何视觉样式与提示，在深色画布上不可见不可发现，且 560px 上限对宽屏用户太窄。
5. **深色遗漏表面**：`widgets/LightRotationWidget.py` 自绘卡片硬编码浅色（`#f4f6f9` 背景、`#475569` 文字），深色主题下光照对话框中央一块亮灰卡片；`formula_preview.py` 兜底标签内联 `#1f2937` 深色文字，深色面板下不可读。
6. **可用性缺陷**：QSS 使用 Qt 不支持的 `:focus-visible` 伪态且 `:focus` 规则把边框重置为默认色，键盘焦点环整体失效，Tab 导航零反馈；函数列表 `white-space: nowrap` 导致长公式被硬性裁切无查看途径；Agent 流式回复每个 token 都 `scrollIntoView`，上翻阅读被反复拽回底部；2D 线段/射线工具 flyout 仅鼠标悬停可达，键盘与触屏无法使用；历史重命名按 Escape 取消时因 blur 保存逻辑仍被提交。
7. **图标与文案不一致**：2D 工具栏三组工具共用相同图标（向量/射线、线工具/直线、角度/投影），只能靠 tooltip 分辨；API Key 显隐按钮用 👁 emoji 与 Lucide SVG 体系冲突；视口工具栏 "2D"/"3D" 文字按钮 QSS 硬编码 18px 超出令牌阶梯；Agent Web 存在 8–10px 亚令牌小字与 22–25px 小点击目标；侧栏与公式列表混入英文文案（History/Skills/Hide function 等）。
8. **对话框行为粗糙**：光照对话框"恢复默认"重置后直接关闭且滑块无数值读数；模型选择弹层无 Esc/外部点击关闭、无 `aria-expanded`；线性代数讲义弹窗无滚动区，长内容可将对话框顶出屏幕。

## What Changes

- **原生窗口 chrome 跟随主题**：主题切换时同步设置 Windows 深色标题栏属性（`DWMWA_USE_IMMERSIVE_DARK_MODE`），浅色主题恢复浅色标题栏；非 Windows 平台为 no-op。
- **MathInputWidget WebView 主题化**：四个 HTML（列表、编辑弹窗、行内覆盖层、预览）从硬编码浅色改为令牌生成的 CSS 变量，由宿主注入 `data-theme` 驱动浅/深两主题；`FormulaListWidget`/`FormulaEditorPopup`/`FormulaPreviewWidget` 暴露 `set_theme`，经 `AlgebraPanel.sync_overlay_theme` 与主窗口主题切换联动，切换不重载页面；预览兜底标签删除内联深色，走 QSS 令牌色。
- **像素级字体体系**：应用字体以 12px（`setPixelSize`）设置并声明中英文 fallback 字体栈与抗锯齿渲染策略；`design/tokens.json` 定义字体栈令牌；QSS 模板覆盖全部 chrome 控件类别（`QToolButton`、`QMenu`、`QToolTip`、`QComboBox` 弹层、`QTreeView`/`QListWidget`）的字号，使未显式覆盖的控件回落到一致的应用字体；状态栏所有段（含 Agent 状态按钮）统一 caption 11px；删除 `agent_sidebar.py` 内联 14px 标题样式；Web 侧字体变量加引号并声明中文字体栈。
- **Agent 阅读密度**：回复正文与事件卡收紧至 12px 正文、行高 1.5，压缩 timeline 内边距、卡片内边距与 turn 间距；`agent_web` 重新构建产物。
- **侧栏分隔手柄可发现**：分隔手柄获得令牌样式（常显细条、hover/拖拽 accent 高亮、tooltip 提示"拖动调整宽度，双击复位"）；Agent 侧栏宽度范围从 360–560px 放宽为 360–720px（默认 440px 不变），双击复位与宽度持久化行为保持；代数面板手柄同样获得可见样式。
- **光照控件令牌化与对话框行为**：`LightRotationWidget` 改为从主题令牌取色并接入主题传播；"恢复默认光照"重置后保持对话框打开并回写控件值；环境光/强度滑块旁显示数值读数。
- **键盘焦点环真实生效**：QSS 焦点规则改用 Qt 支持的 `:focus` 伪态，焦点控件显示 2px accent 描边，两种主题下均可见。
- **长公式隐藏式横向滚动**：公式列表单元格允许横向滚动但不显示滚动条（scrollbar-width none / webkit 隐藏），超宽公式可完整查看。**明确不做**无边框弹窗屏幕越界钳制——公式编辑弹窗允许超出屏幕外侧（用户决定）。
- **Agent 时间线贴底跟随滚动**：仅当用户已处于时间线底部时流式输出才自动跟随；上翻阅读不被打断。
- **2D 线工具 flyout 键盘可达**：点击线按钮展开浮层，支持方向键在直线/线段/射线间选择，Esc 关闭。
- **历史重命名 Escape 真正取消**：Escape 置取消标记，blur 保存逻辑短路。
- **图标去重与体系统一**：向量/射线、线工具/直线、角度/投影三组改用可区分的独立 Lucide 图标；API Key 显隐按钮改用实心圆（密码可见）/空心圆（密码隐藏）图形，不用眼睛图标；视口工具栏 "2D"/"3D" 文字按钮归位令牌字号，主窗口控件补 `setAccessibleName`。
- **Agent Web 字号与点击目标下限**：正文类小字不低于 11px，可点击目标不低于 28px（context-ring 8px 字、附件按钮 22×25 等统一归位）；侧栏界面文案统一为中文。
- **ModelSelector 弹层关闭路径**：补 Esc 关闭、外部点击关闭与 `aria-expanded` 状态（复用 AttachmentActions 的既有模式）。
- **线性代数讲义弹窗滚动**：内容区包滚动区并限高，长讲义不再顶出屏幕。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `ui-design-system`: 主题覆盖范围扩展到原生窗口 chrome、MathInput WebView 表面与光照旋转控件；排版规范升级为像素一致、带中英文 fallback 字体栈与抗锯齿策略；图标语言要求可区分且禁用 emoji；焦点环须用 Qt 支持伪态真实渲染。
- `app-shell`: 状态栏字号统一；面板分隔手柄须视觉可见可发现，Agent 面板宽度范围放宽至 360–720px；悬浮工具栏文字按钮归位令牌字号并补可访问名；新增光照对话框主题化与交互要求。
- `mathagent-sidebar`: 会话时间线获得紧凑阅读密度与贴底跟随滚动规范；侧栏宽度完整性范围更新至 360–720px；历史重命名 Escape 取消；模型弹层补关闭路径与 aria 状态；新增 Web UI 字号/点击目标下限与中文文案要求。
- `linear-algebra-case-tabs`: 讲义弹窗内容区须滚动限高。

## Impact

- **Qt UI**：`main.py`（应用字体）、`ui/designer_window.py`（主题切换传播原生标题栏属性、MathInput 主题联动、可访问名、2D/3D 按钮字号）、`ui/panel_resize_handle.py`（手柄样式与 Agent 上限）、`ui/agent_sidebar.py`（清理内联标题样式）、`ui/algebra_panel.py`（主题联动扩展）、`ui/two_d_tools.py`（图标去重、flyout 键盘可达）、`ui/lighting_dialog.py`（重置保持打开、滑块数值）、`ui/agent_settings.py`（显隐圆点图标）、`ui/styles/base.qss.in`（chrome 控件字号、状态栏字号、手柄样式、焦点环修复）、`ui/tokens.py` 与 `design/tokens.json`（字体栈令牌，loader 校验规则同步）、`widgets/LightRotationWidget.py`（令牌取色）、`ui/linear_algebra_dialog.py`（滚动区限高）。
- **MathInputWidget**：`formula_list.html`（令牌变量 + 隐藏式横向滚动）、`mathlive.html`、`inline_formula_overlay.html`、`formula_preview.html`、`formula_list.py`、`formula_popup.py`、`formula_preview.py`（主题注入、`set_theme` 桥、兜底标签去内联色）。
- **Agent Web**：`ui/agent_web/src/styles/theme.css`（字体栈）、`layout.css`（密度、字号/点击目标下限）、`components/Timeline.tsx`（贴底跟随）、`components/HistoryView.tsx`（Escape 取消 + 中文文案）、`components/SettingsView.tsx`（中文文案）、`components/ModelSelector.tsx`（关闭路径/aria），需重新 `npm run build` 更新 `dist` 产物。
- **测试**：新增/更新原生标题栏属性断言、MathInput 主题切换、应用字体像素值、状态栏字号一致、手柄可见性与宽度范围、时间线密度数值与贴底滚动、焦点环 QSS 伪态、光照控件令牌取色、图标唯一性、flyout 键盘交互、Escape 取消、弹层关闭路径、讲义弹窗滚动的回归测试；现有主题与布局测试适配 720px 上限。
