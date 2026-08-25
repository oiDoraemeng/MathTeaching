# MathAgent Sidebar Design

## 1. Goal

把 Math3D Teaching 右侧 AI 区域从一次性聊天框升级为类似现代 IDE Agent 的工作区，同时保留数学软件的安全边界：

```text
Agent 负责理解和规划
Skill/数学工具负责计算和生成计划
Command Validator 负责校验
SceneCommandService 负责唯一执行入口
PyVista/SymPy 负责显示和数学计算
```

Agent 不直接操作 Qt 控件、PyVista 或任意 Python。所有场景修改都必须经过 `CommandPlan -> Validator -> SceneCommandService`。

## 2. User Experience

### 2.1 Panel visibility

- 右侧面板默认隐藏。
- 主视口右上角提供 Agent 图标按钮。
- 点击 Agent 图标后，在主窗口右侧显示固定宽度的 MathAgent 面板。
- 关闭后整个面板隐藏，主视口恢复原宽度，不保留折叠工具条或空白槽位。
- 打开/关闭可以使用短水平动画，但不能重建 PyVista 场景或丢失会话。

### 2.2 Header

标题栏左侧显示 `MathAgent`。

右侧依次显示图标按钮：

1. `+`：新建对话
2. 时钟：打开历史记录
3. 设置：打开模型、Instructions、Memory、Skills 和自定义 Agent 配置

每个图标必须有 Tooltip。标题栏不放大段说明文字。

### 2.3 Conversation tabs

标题栏下方是横向会话标签栏，表现类似 VS Code 文件标签页：

```text
New Chat x | New Chat x | ...
```

- 每个标签代表一个独立会话 `session_id`。
- 当前标签高亮。
- 每个标签右侧有关闭按钮。
- 关闭带有未执行确认计划的会话时，先提示用户。
- 至少保留一个可输入会话。
- 新建对话不会清理或改变当前场景。
- 标签标题默认使用 `New Chat`，在首轮消息后可以由 Agent 生成短标题。

### 2.4 Empty state

没有发送消息时，主内容区显示空会话状态，不显示空白气泡：

- 大标题：MathAgent
- 副标题：用自然语言解释概念、生成图形并探索当前场景
- 功能卡片：创建几何图形、解释公式、绘制函数、演示向量/矩阵

功能卡片只把示例提示词放入输入框，不直接执行场景命令。

### 2.5 Conversation timeline

每轮 Agent 执行由多个事件卡片组成，而不是单个大气泡：

- 用户消息
- Agent 数学解释
- 场景上下文
- 数学计算
- CommandPlan
- 渲染预览
- 执行结果
- 错误或取消结果

工具和计划的原始 JSON 放在“技术详情”折叠区中，不能作为主要阅读内容。

### 2.6 Hover actions

只有鼠标悬浮在一轮已经成功执行的对话卡片上时，才显示三个操作按钮：

```text
恢复场景 | 撤销绘图 | 分支到新聊天记录
```

按钮默认隐藏，出现/消失使用短淡入淡出效果，不改变消息卡片的布局高度。

- `恢复场景`：用该轮的 `scene_after` 替换当前场景。
- `撤销绘图`：用该轮的 `scene_before` 恢复该轮执行前的场景。
- `分支到新聊天记录`：创建新的会话标签，复制该轮场景快照、上下文和必要消息，原会话保持不变。

没有成功执行的轮次不显示恢复和撤销按钮。

### 2.7 Composer

输入区固定在面板底部，主提示为：

```text
提问或输入 "/"快捷命令
```

输入框左侧工具栏图标：附件、图片、文档、菜单、工具。

输入框左下角：

- `+` 添加附件/图片
- Agent 模式选择下拉框

输入框右下角：

- 模型切换
- 当前上下文/会话信息
- 发送按钮

请求运行时发送按钮变为停止按钮。连续模式允许用户继续输入，后续消息按会话顺序排队。

## 3. Agent modes

下拉框提供：

### Agent

默认模式。自主分析任务、读取当前场景、调用数学工具、生成计划并绘图。

Agent 模式内部提供两种执行策略：

- 确认执行：生成解释、计划和预览，等待用户点击应用。
- 连续自动执行：计划校验通过后自动执行，每轮显示进度并提供撤销/停止。

### Ask

只读问答模式。可以读取场景和调用数学计算工具；任何修改场景的请求必须先向用户询问，不自动执行。

### Plan

规划模式。拆解需求、输出任务清单、数学解释和 CommandPlan，不执行场景修改。用户确认后可以转入 Agent 执行。

### 配置自定义智能体

打开设置页，为未来的高中数学、大学数学等角色配置 Instructions、可用 Skills 和工具权限。本阶段不实现多 Agent 协同。

## 4. Runtime architecture

### 4.1 State machine

```text
IDLE
  -> ANALYZING_CONTEXT
  -> PLANNING
  -> VALIDATING
       -> REPAIRING -> VALIDATING
       -> PREVIEWING -> WAITING_APPROVAL     (确认执行)
       -> APPLYING                           (连续自动执行)
  -> VERIFYING
       -> IDLE
       -> ERROR / STOPPED
```

每个用户动作对应一个原子 `CommandPlan` 事务。底层多个场景操作必须整体提交或整体回滚，不能让模型逐条直接修改场景。

### 4.2 Runtime components

- `ConversationSession`：模式、消息、事件、当前分支和最近计划。
- `SceneContextProvider`：当前二维/三维模式、图层、选中对象、最近执行结果。
- `ToolRegistry`：数学只读工具、计划工具和审批工具。
- `ModelStream`：DeepSeek/OpenAI-compatible 流式响应、文本增量、tool call 解析。
- `PlanValidator`：工具参数转换为 CommandPlan，并调用 `SceneCommandService.preview()`。
- `PlanExecutor`：确认模式等待审批，连续模式自动提交。
- `EventBus`：只传输可序列化事件，不把 Qt 控件传给 Agent。
- `CancellationToken`：停止请求、阻止后续工具调用和回滚未提交事务。

### 4.3 Event protocol

UI 至少支持以下事件类型：

```text
session_started
message_delta
tool_started
tool_finished
calculation_result
plan_ready
validation_result
approval_required
preview_ready
execution_started
execution_finished
undo_available
branch_created
stopped
error
```

UI 只能发送意图事件，例如 `send_message`、`approve_plan`、`stop_session`、`undo_turn` 和 `branch_from_turn`。真正的执行决定仍由 Runtime 作出。

## 5. Math tools

模型不直接拼接大型 CommandPlan，而是调用参数明确的数学工具，例如：

```text
inspect_scene()
calculate_expression(expression)
create_curve(expression, alias, range)
create_surface(expression, alias, range)
create_tangent(curve_alias, x)
create_integral_area(curve_alias, interval)
create_determinant_demo(vector_a, vector_b)
validate_plan(plan)
preview_plan(plan)
apply_plan(plan_id)
undo_last_plan()
```

每个工具内部执行：

```text
参数校验 -> SymPy/数学计算 -> CommandPlan -> preview()
```

只有 `apply_plan` 可以进入 `SceneCommandService.execute()`，并且必须重新校验。

## 6. Persistence

用户不创建数学项目。应用首次运行时自动创建应用数据目录中的 `.math`：

```text
应用数据目录/
└─ .math/
   ├─ mathagent.db
   ├─ attachments/
   ├─ previews/
   └─ exports/
```

推荐使用 SQLite，启用 WAL；UI 不直接访问数据库，由 `SessionStore` 统一读写。API Key 不进入数据库，继续使用 QSettings 或系统凭据存储。

### 6.1 Database records

```text
sessions
  id, title, created_at, updated_at, active_mode, model

turns
  id, session_id, turn_index, parent_turn_id, branch_id
  user_message, assistant_message, agent_mode, execution_mode
  command_plan_json, validation_json, execution_status
  scene_before_json, scene_after_json, preview_path, created_at

events
  id, session_id, turn_id, type, payload_json, created_at

attachments
  id, session_id, turn_id, path, mime_type, created_at
```

每一轮 Agent 执行单独保存，因此同一会话可以恢复任意轮次。

### 6.2 Scene snapshots

快照只保存 JSON 数据，不保存 PyVista 对象：

- 二维/三维模式
- 点、向量、线段、曲线、曲面
- 标注和图层设置
- 可恢复的相机/视图参数
- 必要的版本号

恢复不重新请求模型，而是通过 `SceneSnapshotService` 替换当前场景并触发现有渲染刷新流程。

## 7. Recovery and branches

恢复某轮：

```text
保存当前场景临时快照
  -> 应用该轮 scene_after
  -> 刷新场景
  -> 标记 current_turn_id
```

撤销某轮：

```text
应用该轮 scene_before
  -> 刷新场景
```

恢复旧轮后直接继续输入：在当前会话内形成新分支，旧记录不删除。

点击“分支到新聊天记录”：新建会话标签，复制该轮场景、上下文和必要消息，原会话不变。

## 8. Rendering technology

保留 PySide6 作为应用外壳，右侧聊天时间线使用本地 `QWebEngineView`：

```text
ui/agent_web/
  index.html
  app.js
  style.css
  katex/
```

WebView 负责 Markdown、KaTeX/MathJax、消息卡片、悬浮按钮和事件动画；Python 负责 Agent Runtime、数据库、场景和权限。两者通过受控消息桥通信，WebView 不直接访问 Qt 或 PyVista。

## 9. Non-goals

- 不实现代码 IDE 文件编辑器。
- 不允许 Agent 执行任意 Python。
- 不允许 Agent 直接操作 Qt/PyVista。
- 不实现多 Agent 协同、Hooks 或插件市场。
- 不把历史恢复实现为重新调用模型。
- 不使用复杂云端数据库或外部 MCP 服务作为前置依赖。

## 10. Verification criteria

- 面板关闭时不占用主视口布局空间。
- 点击主视口右上角 Agent 图标可打开面板。
- 多个会话标签可创建、切换和关闭。
- 默认空会话显示标题、副标题和功能卡片。
- Agent、Ask、Plan 三种模式行为不同且可见。
- 确认模式不会在用户确认前改变场景。
- 连续模式自动执行，但每轮可停止和撤销。
- 每轮成功执行都保存 `scene_before`、`scene_after` 和预览路径。
- 历史轮次可恢复任意场景。
- 恢复后继续输入会产生当前会话分支。
- “分支到新聊天记录”不修改原会话。
- 所有场景修改仍经过 `SceneCommandService`。
