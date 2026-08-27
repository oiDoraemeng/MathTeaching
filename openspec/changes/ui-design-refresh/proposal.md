# Proposal: 统一 Math3D Teaching 视觉设计与信息架构

## Why

当前应用由三轮独立迭代拼装而成：左侧代数面板与悬浮工具栏使用手写浅蓝灰 QSS（`designer_window.py:2860-2911`），右侧 MathAgent 侧栏是独立构建的 React/WebView 文档并默认使用 VS Code 风格深色主题（`ui/agent_web/src/styles/theme.css`），旧版紫色 Qt 聊天面板的样式残留在主样式表中永不匹配。结果是：

- **主题割裂**：系统为暗色偏好时右侧 AI 栏呈深色（`#181818`），主窗口仍为浅色（`#f7f8fa`），accent 色也不一致（Qt `#2f7ebd` vs Web `#3794ff`/`#006ab1`）。
- **无设计令牌**：边框灰存在 5 种近似值（`#d9dde3`/`#d0d7df`/`#cbd3dd`/`#dfe3e8`/`#e0e5ea`），字号 px/pt 混用，未设置全局字体，`LightRotationWidget` 硬编码 "Segoe UI"。
- **图标语言不统一**：Qt 侧依赖 Unicode 字符（⚙ ✦ ➤ ● ╱ ↶ ↷）跨平台渲染大小不一，Web 侧已使用 lucide SVG 图标。
- **信息架构弱**：无顶栏与状态栏，2D/3D 模式、渲染与 Agent 状态无处呈现；窗口标题 "Math 教学 " 含尾随空格。
- **死样式与死代码**：主 QSS 中 `#agentPanel`、`#agentUserBubble` 等选择器服务于已被 WebEngine 替代的旧面板；`ui/main_window.py` 整个文件已无人引用；`main_window.ui` 中 294px 侧栏在运行时立即删除；`AgentSidebarState` 注释（折叠 40px/展开 380px）与实现（统一 440px）不一致。

问题集中在表现层与窗口骨架，数学引擎、Agent 安全管线（CommandPlan → Validator → SceneCommandService）与会话存储保持不变。

## What Changes

- **设计令牌单一事实源**：新增 `ui/tokens.py` 定义语义化颜色、字号阶梯、间距、圆角、阴影令牌，导出 Qt QSS 生成器与 Web CSS 变量输出；`ui/agent_web` 构建时消费同一份令牌。
- **明暗双主题**：Qt 侧提供 light/dark 两套完整令牌与主题切换入口（设置面板 + QSettings 持久化）；WebView 不再跟随 `prefers-color-scheme`，改为接收宿主通过 bridge 注入的主题模式与令牌。
- **主窗口信息架构**：新增 32px 底部状态栏（当前 2D/3D 模式、渲染状态、Agent 连接状态、主题切换）；统一三栏面板标题层级（20px → 15px）；修正窗口标题。
- **图标统一**：Qt 侧引入内嵌 lucide SVG 图标渲染（与 Web 侧同名同形），替换全部 Unicode 字符按钮；悬浮工具栏、2D 工具栏、场景设置弹层样式令牌化。
- **布局行为**：右侧 Agent 面板由固定 440px 改为可拖拽 360–560px（分隔手柄），左栏保持 300–360px；删除死样式、死选择器与废弃文件。

## 非目标

- 不重写 `agent/runtime.py`、`services/scene_commands.py`、数学解析与渲染引擎。
- 不改变 Agent 只能生成 CommandPlan 的安全约束，不允许 WebView 接触 Qt/PyVista/Python 对象。
- 不引入 UI 框架（QML/QtQuick/Electron）、不新增远程资源或 CDN 依赖，WebView 仍加载本地打包产物。
- 不替换现有 `.math` 会话数据库、QSettings 凭据存储、Provider 接口。
- 不做用户自定义主题编辑器（仅提供 light/dark 预设与跟随系统三个选项）。

## 成功标准

浅色与深色主题下，主窗口三栏、悬浮工具栏、弹层、对话框与右侧 Agent 侧栏呈现同一套颜色、字体、圆角与阴影语言；切换主题时 Qt 侧与 Web 侧同步变化且无需重启；Agent 面板在 360/440/560px 宽度下布局完整；全部 Unicode 图标按钮被 SVG 图标替代；死样式、废弃窗口文件与不一致注释被清除；现有 2D/3D 渲染回归与 Agent 桥接测试全部通过。

## Impact

- **UI（Qt）**：`designer_window.py`（状态栏、样式重写、悬浮层样式）、`algebra_panel.py`、`scene_settings.py`、`two_d_tools.py`、`agent_sidebar.py`、`lighting_dialog.py`、`widgets/LightRotationWidget.py`；删除 `ui/main_window.py`；`main_window.ui` 移除死配置。
- **UI（Web）**：`ui/agent_web` 的 `theme.css` 改为令牌生成产物，`qtBridge`/reducer 增加主题状态接收，组件移除硬编码颜色。
- **桥接**：`agent/ui_projection.py`/`web_protocol.py` 增加主题初始化与变更事件（纯 JSON，不含敏感信息）。
- **构建**：前端构建新增令牌生成步骤（Node 脚本读取 Python 令牌导出的 JSON）；Python 测试套件仍为主验证。
- **依赖**：Qt 侧图标使用内嵌 SVG 字符串（`QtSvg` 已随 PySide6 提供），不新增第三方依赖。
