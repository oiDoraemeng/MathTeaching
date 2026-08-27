# Deep Technical Design: 统一视觉设计与信息架构

## 1. 设计令牌单一事实源

### 1.1 令牌模型

新增 `ui/tokens.py`，以 Python dataclass + 常量定义全部视觉令牌，每个令牌有稳定语义名。颜色按角色而非位置命名：

| 令牌组 | 语义名（示例） | 用途 |
|---|---|---|
| `bg` | `canvas` / `panel` / `elevated` / `overlay` | 3D 画布底、左右面板底、卡片/输入框底、弹层底 |
| `text` | `primary` / `secondary` / `muted` / `on_accent` | 三级文字与强调底上的文字 |
| `border` | `subtle` / `default` / `strong` | 收敛现有 5 种近似灰为 3 档 |
| `accent` | `default` / `hover` / `pressed` / `soft_bg` | 品牌蓝及其状态变体 |
| `status` | `success` / `warning` / `error` / `info` | 语义色，含 `soft_bg` 变体 |
| `font` | `family` / `size.{caption, body, subtitle, title}` / `weight.{regular, medium, bold}` | 字号收敛为 11/12/13/15 四档，全部 px |
| `space` | `1..6`（4/8/12/16/24/32px） | 间距阶梯 |
| `radius` | `sm` 4px / `md` 6px / `lg` 8px | 圆角三档 |
| `shadow` | `overlay` / `popover` | 悬浮层两级阴影（含暗色主题加深） |

浅色主题保留现主窗口基调（`bg.canvas #f7f8fa`、accent 取 `#2f7ebd` 系），深色主题以现 Agent Web 暗色为基（`bg.canvas #1a1b1e`、面板 `#202124`），accent 在两套主题下统一为同一色相蓝（浅色 `#2f7ebd` / 深色 `#4c9ee8`，对比度均满足 WCAG AA 4.5:1）。现有 `#3794ff`/`#006ab1` 两个 Web accent 废弃。

### 1.2 双输出通道

`tokens.py` 提供两个导出函数：

- `build_qss(theme: Theme) -> str`：以 f-string 模板渲染主 QSS。`designer_window._apply_style()` 改为调用它；面板文件中的 5 处零散内联 `setStyleSheet`（`agent_sidebar.py:83`、`algebra_panel.py:211`、`widgets/LightRotationWidget.py:79-82` 等）改为引用令牌常量拼装。
- `dump_json(theme: Theme) -> str`：导出扁平 JSON，供前端构建消费。

前端构建链：`scripts/` 或 `ui/agent_web/scripts/` 新增 Node 脚本调用 `python -c "from ui.tokens import dump_json; ..."`（或读取预生成的 `tokens.json`），生成 `src/styles/theme.css` 中的 CSS 自定义属性。CI/本地构建时先跑 Python 导出再跑 Vite；`tokens.json` 提交入库以保证无 Python 环境时前端可独立构建。

### 1.3 主题状态

`Theme` 为 `light | dark | system` 三态枚举。Qt 侧在 `main.py` 启动时解析：读取 QSettings `ui/theme`（默认 `system`），`system` 时跟随 `QStyleHints.colorScheme()`，监听其 `colorSchemeChanged` 信号实时切换。解析后的**有效主题**（light 或 dark）用于 QSS 渲染与 Web 注入，原始三态用于设置回显。

## 2. Web 侧栏主题注入

### 2.1 注入协议

WebView 移除 `theme.css` 中的 `@media (prefers-color-scheme: light)` 分支与 `color-scheme: dark` 默认值。主题以数据流进入：

1. **初始化**：`agent_bridge.py` 在文档加载完成（`loadFinished`）后发送 `theme_state` 事件，payload 为 `{ mode: "light"|"dark", tokens: {...} }`。
2. **运行时切换**：宿主主题变化时重发 `theme_state`；React reducer 存入全局 store。
3. **应用**：`App` 根元素设置 `data-theme` 属性；CSS 变量改为两套 `[data-theme="dark"]` / 默认浅色定义（令牌构建产物）。`tokens` 字段作为覆盖层由 JS 写入 `documentElement.style`，保证未重新打包时宿主仍可控关键色。

### 2.2 桥接扩展

`agent/web_protocol.py` 序列化层新增 `theme_state` 事件类型（纯 JSON、无敏感字段、受现有 payload 大小限制约束）。`ui_projection.py` 不参与；主题事件由 `AgentBridge` 直接发送以避免依赖会话快照时序。快照（`history_snapshot`/`settings_snapshot`）保持不变；若文档加载早于主题事件，React 以浅色渲染并在事件到达后无闪烁切换（CSS 变量替换不触发布局抖动，颜色过渡加 `transition: background-color .15s`）。

### 2.3 组件去硬编码

`layout.css` 中所有字面量颜色（如 `rgb(0 0 0 / 30%)` 阴影、`#fff` 按钮文字）替换为语义变量；`Composer`、`EventCard`、`PlanCard` 等组件中残留的 `#fff` 文字色改用 `--agent-text-on-accent`。亮暗两套主题下事件卡左侧状态条色（`--agent-success` 等）各有一档，保证暗底对比度。

## 3. 主窗口信息架构

### 3.1 底部状态栏（新增）

在 `rootLayout` 下方追加水平布局容器（QSS 类 `#appStatusBar`，高 30px，`bg.panel` 底、上边框 `border.default`），左侧依次为：

- **模式指示**：`2D 绘图` / `3D 场景`（来自现有 SceneMode）。
- **渲染状态**：场景重建耗时（现有 `time` 计时数据，`designer_window.py` 已采集）或错误摘短。
- **Agent 状态**：`未连接` / `就绪` / `运行中`（复用 `agent_sidebar.py:83` 的三色圆点语义，令牌化颜色），点击可展开/收起 Agent 面板。

右侧为**主题切换按钮**（sun/moon 图标循环 light→dark→system，tooltip 显示当前模式）。状态栏不做拖拽、不承载业务操作。2D 工具激活态（如"正在放置点"）在模式指示右侧以 `accent.soft_bg` 胶囊显示。

### 3.2 标题层级收敛

| 现状 | 调整 |
|---|---|
| 左面板主标题 20px/700（`designer_window.py:2866`） | 15px/600 + 11px 副标题 |
| Agent 标题 15px | 15px/600（与左面板一致） |
| 弹层标题 13px | 13px/600（不变） |
| 正文 12px、次要 11px | 12px / 11px（不变，纳入令牌） |

窗口标题 `"Math 教学 "` 修正为 `"Math3D Teaching"`（`main_window.ui:6`）。

### 3.3 悬浮层统一

三处悬浮层（视口右上主工具栏、右侧 2D 工具栏、场景设置弹层）共享一套 `overlay` 样式：`bg.overlay` 底、`border.default` 边、`radius.md` 圆角、`shadow.overlay` 阴影、`space.1` 内距。按钮从 38×38 收敛为 32×32（图标 16px），减少对 3D 画布的遮挡；hover 使用 `accent.soft_bg`。2D 工具栏 flyout 与主工具栏同样式。`SceneSettingsPanel` 宽 264px 保持，标题改令牌字号。

### 3.4 面板宽度行为

- 左栏：保持 300–360px 可调。
- 右栏（AgentSidebar）：`setFixedWidth(440)` 改为 `setMinimumWidth(360)` + `setMaximumWidth(560)`，插入 `QSplitter`-less 的手柄方案：`rootLayout` 改为 `QSplitter`（三段：AlgebraPanel / viewportHost / AgentSidebar），viewportHost 为弹性段，splitter 手柄宽 5px 且仅在 Agent 面板可见时第三段存在。会话宽度持久化到 QSettings `ui/agent_panel_width`（默认 440）。
- `AgentSidebarState` 注释与常量统一为 `MIN 360 / DEFAULT 440 / MAX 560`，删除已 `hide()` 的 `AgentCollapsedBar` 死类（`agent_sidebar.py:34-72`）。

### 3.5 死代码清理

- 删除 `ui/main_window.py`（旧紫色 QMainWindow，无引用）。
- `main_window.ui` 移除 294px 死侧栏配置，仅保留 `rootLayout`/`centralwidget`/`viewportHost`/几何；`tests/test_main_window_layout.py` 同步更新断言。
- 主 QSS 删除 `#agentPanel`、`#agentMessageScroll`、`#agentUserBubble`、`#agentAssistantBubble`、`#agentPlanCard`、`#agentModeHint` 等永不匹配的选择器（`designer_window.py:2892-2907`）；Agent 相关提示改由 Web 侧渲染。
- `algebra_panel.py:456-458` 的 22pt 强制字号按钮改为标准图标按钮。

## 4. 图标系统

### 4.1 Qt 侧

新增 `ui/icons.py`：内嵌 lucide 图标的 SVG path 字符串（与 `ui/agent_web` 已用图标同名：`settings-2`、`sparkles`、`history`、`plus`、`x`、`sun`、`moon`、`box`、`square`、`play`、`circle`、`line`、`text`、`undo-2`、`redo-2` 等），提供 `icon(name: str, color: str, size: int = 16) -> QIcon`，用 `QSvgRenderer` 着色生成 pixmap。替换范围：

- 视口主工具栏：⚙→`settings-2`、✦→`sparkles`、2D/3D→`square`/`box`。
- 2D 工具栏：➤●╱#↶↷→`play/circle/line/text/undo-2/redo-2`（`two_d_tools.py:143-159`）。
- 状态栏与面板标题行按钮。

图标色默认 `text.secondary`，hover `text.primary`，激活 `accent.default`；全部经 QIcon 着色而非 CSS filter，保证浅暗主题切换即时生效。

### 4.2 Web 侧

已使用 `lucide-react`，仅补充状态栏对应的宿主入口图标与主题图标，无结构性改动。

## 5. 主题切换时序与边界

1. 启动：解析 QSettings → 有效主题 → `_apply_style(effective)` 渲染 QSS → 窗口显示。WebView 懒加载（首次展开 Agent 面板时才 load），加载完成后立即收到 `theme_state`。
2. 切换：用户点状态栏按钮 → QSettings 写入三态 → 重算有效主题 → 重渲 QSS（整个 `self.window` 级联，LightingDialog 等子窗口自动跟随）→ 若 Agent 面板可见则发 `theme_state` → 若不可见则记录待发（下次 `loadFinished`/展开时发送）。
3. 系统主题变化：`colorSchemeChanged` 触发同 2（仅当三态为 `system`）。
4. 对话框：`LightingDialog` 等基于 parent 级联 QSS 自动适配；其内 `QGroupBox` 边框与文字色补入令牌模板。
5. 3D 画布：`rendering/scene.py` 默认背景 `#f7f8fb` 与 2D 网格线色（`rendering/two_d_scene.py:88`）增加主题分支：dark 模式下 3D 背景 `#202124`、2D 网格 `#3d4650`/浅线 `#4a545f`。场景设置面板中现有的"白色/黑色背景"选项保留，作为对当前主题默认值的覆盖。
6. 崩溃/异常边界：`dump_json` 失败或 `tokens.json` 缺失时前端构建使用内置 fallback 浅色令牌并打警告，不阻断构建；`theme_state` 事件丢失时 React 默认浅色并可被后续事件纠正。

## 6. 布局完整性约束

- Agent 面板 360px：Composer 单行收缩（模式/模型选择器换行为紧凑下拉），SessionTabs 横向滚动（现有行为），模型 popover 不超出右边界（现有 `right: 0` 定位保持）。
- 560px：时间线 `.turn-block` max-width 620px 保持居中，事件卡不拉伸满宽。
- 状态栏在任何窗口宽度（最小 1024px）下不换行，文字超长省略号。
- 左栏 300px 下公式行 48px 高度（`_MINIMUM_ROW_HEIGHT`）不变，颜色按钮 3px 圆角令牌化。

## 7. 测试与验收矩阵

- **Python**：`tokens.py` 快照测试（两主题 QSS/CSS 变量产物 diff 锁定）；主题解析（三态→有效主题）；QSettings 往返；`theme_state` 事件序列化含令牌且不含敏感字段；状态栏模式/Agent 状态投影；splitter 宽度持久化与边界钳制（360–560）；死文件删除后 `main_window_layout` 测试更新。
- **React**：`theme_state` 事件应用 `data-theme` 与变量覆盖；无 `prefers-color-scheme` 分支；组件在两主题下的视觉快照；360/440/560 三宽度布局测试（复用现有边界测试模式）。
- **集成**：Qt↔Web 主题同步（切换后 Web 根元素属性断言）；Agent 面板隐藏时切换主题再展开，首帧即为正确主题；现有 2D/3D 渲染回归与桥接协议测试全绿。
- **OpenSpec**：`openspec validate --strict` 通过。
