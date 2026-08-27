# Proposal: 修复 MathAgent 侧栏交互与模型配置

## 目标

修复当前 React/WebView MathAgent 侧栏中历史记录、设置入口、工具栏、执行模式和对话视觉呈现问题，使其符合已确定的 VS Code 风格交互，同时保持 Math3D Teaching 的安全 Agent 架构不变。

## 变更范围

- 历史按钮打开侧栏内历史列表；会话支持标题编辑和隐藏，隐藏仅从界面移除，不删除本地记录、场景快照或附件。
- 设置按钮打开侧栏内设置页，提供模型、Skills、Memory、Rules 入口；模型配置通过 `OpenAI - Responses` 入口保存到本地 QSettings。
- 内置模型固定展示三款 DeepSeek 预设；自定义 OpenAI-compatible 模型单独分组管理。
- 移除执行策略选择器，统一定义 Agent、Ask、Plan 三种模式的运行语义。
- 输入工具栏仅保留 Skills 工具和 `+` 附件入口。
- 用户消息不再显示可见的“你”标签，改用无角色文字标签的消息气泡。

## 不在范围内

- 不改变 Agent 只能生成 CommandPlan 的约束。
- 不允许 WebView 直接访问 Qt、PyVista、Python callable 或 SceneCommandService。
- 不实现会话永久删除（会话只隐藏并可恢复）、外部 MCP、代码执行或多 Agent 管理。自定义模型配置允许永久删除，但不影响会话记录。
- 不替换现有本地 `.math` 存储、QSettings、Provider 和场景恢复机制。

## 成功标准

用户可以在右侧面板内完成历史浏览、标题编辑、隐藏会话、模型选择、DeepSeek/OpenAI Responses 配置和自定义模型配置；三种 Agent 模式行为清晰；未配置 DeepSeek 时请求仍发送并显示 Provider 错误；侧栏 440px 宽度下所有入口和按钮可见且不溢出。
