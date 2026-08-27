# Tasks

## 1. 会话与历史

- [ ] 1.1 为 sessions 增加 `hidden_at` 字段和迁移/兼容读取逻辑。
- [ ] 1.2 实现 `rename_session()`、`hide_session()` 和默认可见过滤，保证至少保留一个可见会话。
- [ ] 1.3 增加历史快照投影，包含标题、最近活动时间、回合数和隐藏状态。
- [ ] 1.4 增加隐藏会话恢复入口，区分 `closed_at` 与 `hidden_at`，并定义活动会话回退顺序。

## 2. WebView 视图与桥接

- [ ] 2.1 在 React 侧栏增加 conversation/history/settings 视图和返回导航。
- [ ] 2.2 接入历史打开、重命名、隐藏、设置打开和 Skills 打开意图。
- [ ] 2.3 为未知设置/历史意图返回可序列化错误，不暴露 Qt/Python 对象。
- [ ] 2.4 为所有变更意图增加 request_id 幂等、乐观更新回滚和序列缺口快照恢复。

## 3. 模型与 Provider 配置

- [ ] 3.1 实现内置 DeepSeek 三模型目录、默认选中和 Pro hover 详情卡片。
- [ ] 3.2 实现 `OpenAI - Responses` 配置表单，使用 QSettings 本地保存并只回传脱敏状态。
- [ ] 3.3 实现自定义模型分组、保存、编辑、选择和能力/上下文配置。
- [ ] 3.4 支持 Responses/Chat Completions 协议选择，默认 `OpenAI - Responses`，并实现独立测试连接动作。
- [ ] 3.5 支持按会话保存思考开关与 Low/High/X-High 强度，以及自定义模型永久删除。
- [ ] 3.6 保持未配置或 DeepSeek 报错时请求照常发送并显示错误卡片。

## 4. 模式、工具栏与视觉

- [ ] 4.1 删除确认执行/连续执行选择器，固定 Agent/Ask/Plan 运行语义。
- [ ] 4.2 将输入工具栏收敛为 Skills 工具和 `+` 附件入口。
- [ ] 4.3 移除用户消息可见“你”标签，保持无障碍语义和稳定布局。
- [ ] 4.4 在 440px WebView 宽度下验证设置、模型、输入和发送控件不溢出。
- [ ] 4.5 在 320px 与 440px 宽度下验证历史、设置、模型详情和附件菜单的边界行为。

## 5. 验证

- [ ] 5.1 增加 SessionStore、bridge、provider 和运行模式的 Python 测试。
- [ ] 5.2 增加 React 历史、设置、模型、工具栏和消息视觉测试。
- [ ] 5.3 运行 focused/full tests、TypeScript 检查、前端构建和 OpenSpec 严格校验。
- [ ] 5.4 增加并发运行、后台事件累积、stale approval 和凭据泄漏扫描验证。
