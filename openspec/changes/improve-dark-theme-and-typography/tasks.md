## 1. 字体体系与应用级排版

- [x] 1.1 在 `design/tokens.json` 增加 `font.family_stack`（Segoe UI + Microsoft YaHei UI + PingFang SC + Noto Sans CJK SC），更新 `ui/tokens.py` loader 与校验以暴露 `font_family_stack`，验证现有 token 测试通过并新增 family_stack 断言
- [ ] 1.2 修改 `main.py` 应用字体：`setFamilies(font_family_stack)` + `setPixelSize(12)` + `PreferAntialias`，新增测试断言 QApplication 字体的 pixelSize 为 12、families 包含中文字体
- [ ] 1.3 在 `ui/styles/base.qss.in` 为 QToolButton、QMenu、QToolTip、QComboBox QAbstractItemView、QTreeView/QListView/QListWidget 补充令牌字号（caption/body），并为 `#appStatusBar QToolButton` 增加 11px，验证生成 QSS 包含这些选择器且状态栏全部段字号一致
- [ ] 1.4 删除 `ui/agent_sidebar.py` 四处内联 `font-size: 14px` 标题样式并复用 `#sectionHeader` 样式，验证面板页标题渲染为令牌 caption 样式
- [ ] 1.5 更新 `ui/agent_web/src/styles/theme.css` 字体变量为带引号的 `Segoe UI, Microsoft YaHei UI, PingFang SC, sans-serif` 字体栈（light/dark 两组），执行 `npm run build` 重建 dist 并验证产物包含新字体栈

## 2. 原生标题栏跟随主题

- [ ] 2.1 新建 `ui/native_chrome.py`：`apply_native_titlebar_theme(window, effective_theme)` 用 ctypes 调用 `DwmSetWindowAttribute(DWMWA_USE_IMMERSIVE_DARK_MODE)`，非 Windows 或调用失败时静默跳过，监听 `windowIdChanged` 重应用；单元测试用 monkeypatch 断言 dark=1/light=0 参数与无异常回退
- [ ] 2.2 在 `designer_window.py` `_apply_style` 中对主窗口及已创建顶层对话框（Agent 设置、光照、记忆对话框）应用标题栏主题，验证主题循环切换时所有顶层窗口 chrome 同步变化（monkeypatch 断言调用次数与参数）

## 3. MathInputWidget WebView 主题化

- [ ] 3.1 新建 `MathInputWidget/theme_tokens.py`：从 `design/tokens.json` 生成 `--mi-*` CSS 变量块（light/dark），单元测试断言变量值与令牌一致且 dark 组完整
- [ ] 3.2 重写 `formula_list.html` 颜色为 `var(--mi-*, 浅色回退)` 并支持 `[data-theme="dark"]`，覆盖行背景、hover、选中、边框、提示条与 MathLive selection/contains-highlight 变量；浏览器直接打开仍呈浅色可读
- [ ] 3.3 同样改造 `mathlive.html`、`inline_formula_overlay.html`、`formula_preview.html`，并删除 `formula_preview.py:73` 兜底标签的内联 `#1f2937` 改走 QSS 令牌色
- [ ] 3.4 为 `FormulaListWidget`、`FormulaEditorPopup`、`FormulaPreviewWidget` 实现 `set_theme(theme)`（DocumentCreation 用户脚本设 `data-theme` + 已加载时 `runJavaScript` 更新 + 未加载缓存 pending），单元测试验证 pending 主题在 loadFinished 后生效、运行时切换不重载
- [ ] 3.5 在 `AlgebraPanel.sync_overlay_theme` 转发主题到三个组件，端到端验证：启动即深色、运行时切换、深色下打开公式编辑弹窗均无浅色残留
- [ ] 3.6 `formula_list.html` 长公式支持隐藏式横向滚动：去掉 `white-space: nowrap`、公式单元格 `overflow-x: auto` + `scrollbar-width: none` + `::-webkit-scrollbar{display:none}`，验证超宽公式可完整滚动查看且无可见滚动条

## 4. Agent 阅读密度与时间线滚动

- [ ] 4.1 调整 `ui/agent_web/src/styles/layout.css` 密度数值：`.assistant-content` 12px/1.5、`.event-card` padding 8px 10px + margin 6px 0 + 12px、`.turn-block` 下边距 18px、`.timeline` padding 16px 14px 20px、`.markdown-content p` margin 6px、`.reasoning-block`/`.thinking-section` 收紧，重建 dist 并核对产物数值
- [ ] 4.2 验证 hover-only turn actions 仍不改变卡片布局高度，且 `.turn-block`/阅读列 max-width 620px 保持（宽侧栏下行长可控）
- [ ] 4.3 `Timeline.tsx` 改为贴底跟随滚动：维护 isAtBottom 判定（距底 <40px），仅贴底时流式输出自动滚动，上翻阅读不被打断；组件测试覆盖"上翻+流式新增不回弹"与"贴底+流式新增跟随"两场景

## 5. 面板分隔手柄可发现与宽度范围

- [ ] 5.1 `_PanelResizeHandle` 设置 `objectName("panelResizeHandle")`、press/release 维护 `dragging` 属性、设置 resize tooltip；在 `base.qss.in` 增加手柄样式（常显细条、hover/dragging accent 高亮），测试断言生成 QSS 含选择器且属性切换正确
- [ ] 5.2 将 Agent 面板宽度范围改为 360–720px（`AgentSidebar.MIN/MAX_WIDTH`、`designer_window._install_agent_panel` 的 spec），更新现有布局测试对 560 上限的断言并新增 720 clamp 与 560–720 恢复场景测试
- [ ] 5.3 手动/冒烟验证：拖拽两栏手柄跟随指针且 clamp 生效、双击复位 320/440、重启后宽度持久化、Agent 面板关闭时手柄隐藏

## 6. 深色遗漏表面

- [ ] 6.1 `widgets/LightRotationWidget.py` 的颜色改从 `flatten_theme()` 取令牌（卡片底 bg.elevated、标签 text.secondary、accent accent.default），新增 `set_theme`；`LightingDialog.set_effective_theme` 同步调用，单元测试断言两主题下取色不同且为令牌值
- [ ] 6.2 与任务 3.3 合并验证：深色主题下光照对话框与公式预览兜底无浅色亮块/不可读文字

## 7. 键盘焦点环与 2D 工具可达性

- [ ] 7.1 修复 `base.qss.in` 焦点规则：删除不支持的 `:focus-visible` 规则，`:focus` 改为 2px accent 描边（必要时 padding 补偿防跳动），生成 QSS 断言无 Qt 不支持伪态且焦点规则存在；Tab 遍历主窗口控件验证描边可见
- [ ] 7.2 2D 线工具 flyout 键盘/点击可达：点击线按钮切换浮层、方向键在直线/线段/射线间移动、Enter 选择、Esc 关闭并回焦，保留 hover 展开行为；交互测试覆盖键盘全流程

## 8. Agent Web 交互修复

- [ ] 8.1 `HistoryView.tsx` 重命名 Escape 真正取消：Escape 置取消标记使 blur 保存短路，组件测试覆盖 Escape 不保存、Enter/blur 保存两路径
- [ ] 8.2 `ModelSelector.tsx` 弹层补 Esc/外部点击关闭与触发按钮 `aria-expanded`（复用 AttachmentActions 模式），组件测试覆盖三种关闭路径
- [ ] 8.3 `layout.css` 字号/点击目标下限：8–10px 文本提至 11px（context-ring、turn-actions、model-details、capability 描述等），22–25px 点击目标统一到 28px（附件按钮、tab 关闭、turn-actions），重建 dist 核对
- [ ] 8.4 界面文案统一中文：`HistoryView.tsx`（History/No conversations/turns）、`SettingsView.tsx`（Settings/Skills/Memory/Rules）、`formula_list.html`（Hide function 等 tooltip/aria-label），验证无英文残留

## 9. 图标体系统一

- [ ] 9.1 2D 工具栏图标去重：向量/射线、线工具/直线、角度/投影三组改用可区分独立图标（新 SVG path 进 `ui/icons.py` 内嵌表并参与 retint），测试断言同栏任意两按钮图标不同
- [ ] 9.2 `agent_settings.py` API Key 显隐按钮去 👁 emoji：密码可见显示实心圆、隐藏显示空心圆（`icons.py` 新增 circle-filled/circle-outline），测试断言图标切换与主题 retint
- [ ] 9.3 `designer_window.py` 视口工具栏 "2D"/"3D" 文字按钮归位令牌字号（去掉 QSS 18px 硬编码），主窗口工具栏与状态栏交互控件补 `setAccessibleName`，测试断言生成 QSS 无 18px 且控件 accessibleName 非空

## 10. 对话框行为修复

- [ ] 10.1 `lighting_dialog.py`："恢复默认光照"移除 `self.close()` 并重置后回写控件值；环境光/强度滑块旁加数值 QLabel 随 valueChanged 更新，测试验证重置后对话框仍打开且读数正确
- [ ] 10.2 `linear_algebra_dialog.py`：内容区包 `QScrollArea`（widgetResizable）并限制弹窗最大高度为屏幕可用高度 80%，验证长讲义弹窗内滚动且整体不超出屏幕、短内容无多余滚动条

## 11. 回归与文档

- [ ] 11.1 运行完整测试套件（含 2D 工具栏、线性代数加载、agent 主题既有测试）并修复因字号/宽度范围/手柄 objectName/图标变更引起的回归
- [ ] 11.2 深色主题全表面走查清单：标题栏、代数面板（含公式列表与弹窗）、光照对话框、三栏边界、悬浮工具栏、状态栏、Agent 侧栏、对话框——确认无浅色残留，截图记录到变更目录
