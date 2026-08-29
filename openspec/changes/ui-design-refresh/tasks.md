# Tasks

> 设计基线：机制层（design.md §1–§10）与美学层（§11）2026-08-27 sign-off 冻结；案例层（§12，D9–D11，含**案例标签瞬态语义 D10**）2026-08-29 确认。
>
> 实现批次（Superpowers 3–5 任务/批 + 人工检查点）：
> - **Batch 1（第 1 组，基建）**：纯新增文件，不触碰现有行为
> - **Batch 2（第 3 组，Web 主题管线 + 案例页）**：依赖 Batch 1 的 tokens.json
> - **Batch 3（第 2 组，Qt 视觉统一 + 案例弹窗）**：依赖 Batch 1 的 QSS 模板
> - **Batch 4（第 4 组，布局架构）**：状态栏 + 双手柄，相对独立
> - **Batch 5（第 5 组，全量验证）**

## 1. 设计令牌与主题基建（Batch 1）

- [x] 1.1 新建 `design/tokens.json`（语义化颜色/字号/间距/圆角/阴影两级/动效时长曲线，light/dark 两套完整定义，含 `bg.scene` 画布色）与 `ui/tokens.py` typed loader（schema 校验、启动快速失败、递归展平）。
- [x] 1.2 新建 `ui/styles/base.qss.in` QSS 模板与 `build_qss(theme)`（`string.Template` 替换）；`designer_window._apply_style()` 迁移到模板渲染。
- [x] 1.3 新建 `ui/agent_web/scripts/gen-theme.mjs`：读取 `design/tokens.json` 生成 `src/styles/theme.css`（`[data-theme]` 双分支 + `color-scheme` 跟随），内置浅色 fallback，接入 Vite 构建。
- [x] 1.4 `main.py` 设置 `QApplication` 全局字体与主题解析（QSettings `ui/theme`，默认 `system`，监听 `QStyleHints.colorSchemeChanged`）。
- [x] 1.5 增加令牌测试 `tests/test_ui_tokens.py`：双主题键集一致、`build_qss` 无 `$` 残留、含/不含关键选择器断言、schema 非法即 `TokenError`。

**Batch 1 检查点**：`pytest tests/test_ui_tokens.py -q` 绿；`node ui/agent_web/scripts/gen-theme.mjs` 生成成功；`pnpm -C ui/agent_web build` 通过。

## 2. Qt 主窗口视觉统一（Batch 3）

- [x] 2.1 主 QSS 模板化时删除旧 Qt 聊天面板死选择器（`#agentPanel`/`#agentUserBubble`/`#agentPlanCard` 等全部 `#agent*` 残留）与 `#agentCollapsedBar` 相关样式。
- [x] 2.2 新增 `ui/icons.py`（内嵌 lucide SVG + `currentColor` 替换着色 + DPR 感知渲染 + 缓存）；替换视口主工具栏（⚙→`settings-2`、✦→`sparkles`）、2D 工具栏（➤●╱#↶↷→`play/circle-dot/slash/type/undo-2/redo-2`）、左面板（`+`/`⋮`→`plus/ellipsis`）按钮，统一 36px/16px 规格（图层行内小按钮 28px）。
- [x] 2.3 悬浮层（主工具栏、2D 工具栏 flyout、场景设置弹层）统一样式：overlay 底色、subtle 边框、8px 圆角、overlay 阴影、hover 令牌化；对话框 10px 圆角 + modal 阴影。
- [x] 2.4 标题层级收敛（左面板 20px→15px 令牌）；清理 `algebra_panel.py` 颜色按钮内联样式与 22pt 按钮、`widgets/LightRotationWidget.py` 硬编码字体。
- [x] 2.5 `SceneAppearance.background` 值域扩展 `"auto"`（默认），combo 增"跟随主题"项；`rendering/scene.py` 与 `rendering/two_d_scene.py` 在 auto 下按有效主题取背景/网格色（`bg.scene`）；主题切换时重渲 auto 外观。
- [x] 2.6 `LightingDialog` 等 QDialog 纳入令牌模板（QGroupBox 边框/文字色）。
- [x] 2.7 视觉质感：面板分隔去边框改色阶（light canvas 加深、QSS 去 `border-right`）；`LayerRow` 卡片化（elevated 底、8px 圆角、4px 左色条、hover 边框/选中 accent 态、可见性 eye 图标、设置钮 40×40/22pt → 28px `ellipsis`）；节标题模式（11px/muted/字距）；键盘焦点环（2px accent）；控件高度三档（36/32/28）全量替换 38/40/30 随机值；弹层 150ms 淡入位移、面板动画统一 200ms OutCubic；Web 侧 `prefers-reduced-motion` 支持。
- [ ] 2.8 案例弹窗纳入规范（§12.4）：`#linearAlgebraCasePopup`/`linearAlgebraCaseRow`/`linearAlgebraCaseTitle`/`linearAlgebraCaseSummary` 入 QSS 模板（overlay 底、lg 圆角、overlay 阴影、150ms 出现动画）；案例行卡片化（8/12px 内距、hover soft_bg + 左 3px accent 指示条、摘要单行省略 muted）；工具栏"函数"/"线性代数"文字按钮统一 32px 高入令牌。

**Batch 3 检查点**：`pytest tests/test_algebra_panel.py tests/test_main_window_layout.py -q` 绿；light/dark 两主题下主窗口、悬浮层、案例弹窗视觉走查通过。

## 3. Web Agent 侧栏主题同步（Batch 2）

- [x] 3.1 移除 `theme.css` 的 `prefers-color-scheme` 分支与默认 `color-scheme: dark`，改用 `gen-theme.mjs` 生成的 `[data-theme]` 双分支变量。
- [ ] 3.2 `agent_sidebar_web.py`：`_initial_url()` 拼接 `?theme=<mode>` 查询参数；注册 `QWebEngineScript`（DocumentCreation）读取参数设置 `data-theme`。
- [ ] 3.3 `web_protocol.py` 的 `EVENT_MESSAGE_TYPES` 增加 `theme_state`（payload 仅 `mode`，白名单校验，与已注册的 `math_case` 并存）；`agent_sidebar_web.set_theme()` 按加载状态发射事件。
- [ ] 3.4 React reducer 处理 `theme_state` → 切换 `documentElement` 的 `data-theme`（与 UserScript 幂等）；根容器颜色过渡 `.15s`。
- [ ] 3.5 清理 `layout.css` 与组件中的字面量颜色（`#fff`、`rgb(0 0 0 / 30%)` 等）改语义变量；增加"无字面量颜色"lint 断言。
- [ ] 3.6 案例阅读页令牌化（§12.3）：`MathCaseView` 卡片 5px 圆角+1px 边框 → `radius.md` + 默认无边框；步骤 `li::marker` accent 化、间距 12px；公式/结论卡对齐版式规范（文档标题 20px 独立于 chrome 15px）。
- [ ] 3.7 案例标签类型区分（§12.2 D9）：`.session-tab-case` 增加 12px `book-open` 前导图标（muted → 激活 accent）；验证 `close_case` 回退会话、运行中回合不受影响、同 id 重发复用标签（D10 瞬态语义）。

**Batch 2 检查点**：`pytest tests/test_agent_web_protocol.py -q` 绿；`pnpm -C ui/agent_web test`（reducer/主题/案例标签）绿；侧栏 light/dark 渲染与案例页版式走查通过。

## 4. 布局与信息架构（Batch 4）

- [ ] 4.1 新增底部状态栏（30px）：2D/3D 模式、激活工具胶囊、渲染耗时、Agent 状态段（点击开合面板）、主题切换按钮（sun/moon/monitor 循环三态）；rootLayout 包一层垂直布局容纳状态栏。
- [ ] 4.2 新增参数化 `_PanelResizeHandle`（5px 手柄，方向/范围/默认值/QSettings 键参数化）：左栏手柄 260–420（默认 320，键 `ui/algebra_panel_width`，常驻）+ 右栏手柄 360–560（默认 440，键 `ui/agent_panel_width`，随面板显隐），双击复位、钳制、持久化；`algebra_panel.py` 宽度约束改 260/420；`AgentSidebar` 三处 `setFixedWidth(440)` 统一为常量 + 存储宽度。
- [ ] 4.3 删除 `AgentSidebarState` 死注释与已隐藏的 `AgentCollapsedBar` 死类；常量统一 MIN 360 / DEFAULT 440 / MAX 560。
- [ ] 4.4 修正窗口标题为 `Math3D Teaching`；删除 `ui/main_window.py`；精简 `main_window.ui` 死侧栏配置并更新 `tests/test_main_window_layout.py`。

**Batch 4 检查点**：`pytest tests/test_main_window_layout.py -q` 绿；手动验证双手柄钳制/复位/重启持久化、状态栏三段显示与主题循环。

## 5. 验证（Batch 5）

- [ ] 5.1 Python 测试：主题三态解析与 QSettings 往返、`theme_state` 序列化（mode 白名单、无凭据）、双手柄（左栏 260–420/默认 320、右栏 360–560/默认 440）钳制/复位/持久化/拖动方向、`background=auto` 兼容旧值、令牌/QSS 快照断言。
- [ ] 5.2 React 测试：`theme_state` 事件应用与非法值忽略、无 `prefers-color-scheme` 依赖断言、两主题变量完整性、360/440/560 三宽度布局；案例标签（图标区分、upsert 复用、关闭回退、回合不中断）与案例阅读页（版式结构、KaTeX 渲染、卡片规范）测试。
- [ ] 5.3 案例弹窗 Qt 测试：弹窗样式选择器存在、案例行 hover/摘要截断、未知案例 id 场景不变 + 错误状态、加载案例触发侧栏案例页。
- [ ] 5.4 集成测试：`set_theme` 后 `runJavaScript` 断言 `data-theme`；URL 参数首帧注入断言；现有 2D/3D 渲染回归与桥接协议测试全绿。
- [ ] 5.5 运行 focused/full tests、TypeScript 检查、前端构建与 `openspec validate --strict`。

**Batch 5 检查点**：`pytest -q` 全绿；`pnpm -C ui/agent_web test && pnpm -C ui/agent_web build` 绿；`openspec validate ui-design-refresh --strict` 通过。






