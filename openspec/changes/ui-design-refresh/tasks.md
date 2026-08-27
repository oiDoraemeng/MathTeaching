# Tasks

## 1. 设计令牌与主题基建

- [ ] 1.1 新增 `ui/tokens.py`：语义化颜色/字号/间距/圆角/阴影令牌，light/dark 两套完整定义，`build_qss()` 与 `dump_json()` 双输出。
- [ ] 1.2 新增前端令牌构建步骤：生成 `ui/agent_web/src/styles/theme.css` 的 CSS 变量（两套 `[data-theme]` 分支），提交 `tokens.json` 并实现缺失时的内置浅色 fallback。
- [ ] 1.3 `main.py` 设置全局字体（`QApplication.setFont`）与初始主题解析（QSettings `ui/theme`，默认 `system`，监听 `colorSchemeChanged`）。
- [ ] 1.4 增加令牌快照测试：锁定两主题的 QSS 与 CSS 变量产物。

## 2. Qt 主窗口视觉统一

- [ ] 2.1 将 `designer_window._apply_style()` 迁移到令牌渲染的 QSS 模板，删除旧 Qt 聊天面板死选择器（`#agentPanel`/`#agentUserBubble`/`#agentPlanCard` 等）。
- [ ] 2.2 新增 `ui/icons.py`（内嵌 lucide SVG path + 着色 QIcon），替换视口主工具栏、2D 工具栏、面板与状态栏的全部 Unicode 字符按钮，按钮统一 32px/16px 图标。
- [ ] 2.3 悬浮层（主工具栏、2D 工具栏 flyout、场景设置弹层）统一样式：overlay 底色、边框、圆角、阴影、hover 令牌化。
- [ ] 2.4 左面板与 Agent 头部标题层级收敛（20px→15px 令牌字号），清理 `algebra_panel.py:456-458` 的 22pt 按钮、`algebra_panel.py:211` 与 `widgets/LightRotationWidget.py` 的内联样式/硬编码字体。
- [ ] 2.5 `rendering/scene.py` 3D 背景与 `rendering/two_d_scene.py` 网格线色增加主题分支，保留场景设置中的显式背景覆盖。
- [ ] 2.6 `LightingDialog` 等 QDialog 纳入令牌模板（QGroupBox 边框/文字色）。

## 3. Web Agent 侧栏主题同步

- [ ] 3.1 移除 `theme.css` 的 `prefers-color-scheme` 分支与默认 `color-scheme: dark`，改用令牌生成的 `[data-theme]` 变量。
- [ ] 3.2 `agent_bridge.py`/`web_protocol.py` 增加 `theme_state` 事件（mode + tokens，纯 JSON，受 payload 限制），`loadFinished` 后与主题切换时发送；面板隐藏时记录待发。
- [ ] 3.3 React 侧接收 `theme_state`：reducer 存储，根元素 `data-theme` + 变量覆盖，颜色过渡 `.15s`；无事件时默认浅色。
- [ ] 3.4 清理 `layout.css` 与组件中的字面量颜色（`#fff`、`rgb(0 0 0 / 30%)` 等），全部改语义变量；补充两主题对比度验证。

## 4. 布局与信息架构

- [ ] 4.1 新增底部状态栏：2D/3D 模式、激活工具胶囊、渲染状态、Agent 状态（可点击开合面板）、主题切换（sun/moon 循环三态）。
- [ ] 4.2 `rootLayout` 改为三段 QSplitter：左栏 300–360（保持）、视口弹性、Agent 栏 360–560（默认 440），宽度持久化到 QSettings，面板关闭时不占位。
- [ ] 4.3 删除 `AgentSidebarState` 死注释与已隐藏的 `AgentCollapsedBar`，常量统一 MIN 360 / DEFAULT 440 / MAX 560。
- [ ] 4.4 修正窗口标题为 `Math3D Teaching`；删除 `ui/main_window.py`；精简 `main_window.ui` 死侧栏配置并更新 `tests/test_main_window_layout.py`。

## 5. 验证

- [ ] 5.1 Python 测试：主题三态解析与 QSettings 往返、`theme_state` 序列化（含令牌、无凭据）、splitter 宽度钳制与持久化、死代码删除后的布局测试。
- [ ] 5.2 React 测试：主题事件应用与 fallback、无系统主题跟随断言、两主题视觉快照、360/440/560 三宽度布局。
- [ ] 5.3 集成测试：Qt↔Web 主题同步（隐藏时切换再展开首帧正确）、现有 2D/3D 渲染回归与桥接协议测试全绿。
- [ ] 5.4 运行 focused/full tests、TypeScript 检查、前端构建与 `openspec validate --strict`。
