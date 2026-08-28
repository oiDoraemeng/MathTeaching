# 设计

## 组件边界

`models/linear_algebra_cases.py` 保存案例元数据、解释文本和经过验证的 `CommandPlan`，不依赖 Qt 或 WebView。`AlgebraPanel` 只负责入口和列表交互，通过信号把案例 id 交给主窗口。`DesignerWindow` 负责清场、执行案例计划和通知 Agent Web 宿主。`AgentSidebarWeb` 只发送 JSON 事件；React reducer 保存案例标签，`SessionTabs` 统一渲染 Agent 会话与案例标签。

## 数据流

1. 用户点击左侧“线性代数”按钮，弹出按分类分组的案例列表。
2. 用户选择案例 id，`DesignerWindow` 查找案例定义。
3. 主窗口执行 `scene.clear(all)` 与案例计划的二维操作，使用现有 `SceneCommandService` 做验证和原子事务；失败时不修改当前场景。
4. 主窗口调用 `AgentSidebarWeb.show_math_case()`，发出 `math_case` JSON 事件，携带案例 id、标题、公式、步骤、结论和简短说明。
5. Web reducer 按案例 id 去重并更新标签；首次出现时加入列表，重复出现时只更新内容并激活该标签。
6. Agent 会话仍通过 `request_snapshot` 和现有会话状态工作。切换案例标签不改变 Agent active session；切换 Agent 标签也不删除案例标签。

## 右侧标签模型

新增 `CaseProjection` 与 `AppState.cases`、`activeTab`。`activeTab` 采用 `session:<id>` 或 `case:<id>` 命名空间，避免案例 id 与会话 id 冲突。案例视图显示标题、公式、步骤、结论和图形状态，不显示 Agent composer。会话视图保持当前时间线和 composer。

`SessionTabs` 接收会话和案例两个数组，案例标签使用 `case` 样式但共享同一横向滚动容器。每个标签按标题自然宽度显示，并设置最小宽度 104px、最大宽度 240px，超长标题使用省略号；容器 `overflow-x: auto; scrollbar-width: none`，通过 CSS 隐藏 WebKit 滚动条；鼠标滚轮由浏览器原生横向滚动支持，触控板横向滚动同样有效。

## 场景案例

案例均使用二维场景和现有白名单操作。向量加法复用 `teach.vector_addition` 宏；减法使用 `a + (-b)` 的预置端点并用注释说明；数乘、内积和外积由点、向量、线段、注释和 `view.fit` 组成。所有案例计划先经过 `SceneCommandService.validate`，执行时以一个事务包裹清空和加载。

## 错误处理与兼容性

- 未知案例 id 只产生 Qt 状态提示，不向 WebView 发事件。
- 场景计划校验失败时保留原场景，并发送错误状态；案例标签不新增。
- Web 端对缺失或过长字段使用安全默认值，未知事件不会破坏现有会话 reducer。
- `math_case` 加入 bridge 事件白名单和 TypeScript 类型，但不增加任何客户端可调用的场景 intent。

## 测试策略

- Python：案例目录唯一 id、解释字段、计划可验证；AlgebraPanel 入口与主窗口案例执行/失败回滚测试。
- Web：reducer 对案例事件去重、激活、切换和关闭；SessionTabs 自适应宽度/关闭按钮/案例标签渲染；现有桥接和构建测试继续通过。
- 集成：发送 `math_case` 事件后标签栏出现案例名，重复事件不产生第二个标签。
