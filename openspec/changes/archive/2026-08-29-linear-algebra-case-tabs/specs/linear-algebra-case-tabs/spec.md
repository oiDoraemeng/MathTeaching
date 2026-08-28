# 线性代数案例标签规格

## ADDED Requirements

### Requirement: Linear algebra entry

左侧代数面板 SHALL 在“函数”按钮之后显示名称为“线性代数”的按钮。点击按钮 SHALL 打开线性代数案例列表，并按“向量”分类显示第一版案例。

#### Scenario: Open vector case list
- **WHEN** 用户点击“线性代数”按钮
- **THEN** 弹出列表包含“向量加法”“向量减法”“向量数乘”“向量内积”“向量外积”

### Requirement: Built-in case loading

每个案例 SHALL 提供稳定 id、用户可见名称、公式、解释步骤、结论和二维 `CommandPlan`。用户选择案例时 SHALL 清空当前场景并原子加载该计划；计划验证或执行失败时 SHALL 保留原场景。

#### Scenario: Load vector subtraction
- **WHEN** 用户选择“向量减法”
- **THEN** 当前画布被清空并显示预置向量、结果向量和辅助构造线
- **AND** 场景状态对应案例的固定公式与向量数据

### Requirement: Case tabs in shared strip

右侧横向会话标签栏 SHALL 同时显示 Agent 会话标签和案例标签。案例标签标题 SHALL 使用案例名称，点击案例标签 SHALL 展示该案例的解释内容；每个标签 SHALL 提供关闭按钮，关闭案例标签后回到当前 Agent 会话，不得覆盖 Agent 会话记录。

#### Scenario: Keep agent and case tabs independent
- **WHEN** 用户打开“向量加法”案例后切换回 Agent 会话
- **THEN** Agent 时间线和 composer 保持原状态
- **WHEN** 用户再点击“向量加法”案例标签
- **THEN** 仍显示原案例解释，不创建新案例标签

### Requirement: Case deduplication

系统 SHALL 按案例 id 对案例标签去重。重复选择同一案例 SHALL 激活既有标签并刷新其内容，不得增加同名标签。

#### Scenario: Reuse a case tab
- **WHEN** 用户连续两次选择同一案例
- **THEN** 标签栏中该案例只出现一次
- **AND** 当前活动标签为该案例

### Requirement: Stable horizontal tab sizing

标签栏 SHALL 按每个标题的自然文字宽度显示标签，同时设置最小宽度与最大宽度上限，不得因标签数量增加而压缩文字；超过最大宽度的标题使用省略号。超出可见宽度时 SHALL 支持横向滚轮滚动并隐藏原生滚动条。

#### Scenario: Many case tabs
- **WHEN** 用户打开多个不同案例导致标签超出栏宽度
- **THEN** 已有标签宽度保持稳定
- **AND** 用户可以通过横向滚轮访问隐藏标签
- **AND** 不显示可见滚动条

### Requirement: JSON-only event contract

案例通知 SHALL 通过现有版本化 JSON bridge 以 `math_case` 事件传递，只包含 JSON-safe 的案例字段；WebView SHALL 不能通过该事件直接调用 Qt、PyVista 或场景服务。

#### Scenario: Render a case event
- **WHEN** Python 发出合法 `math_case` 事件
- **THEN** Web reducer 创建或更新对应案例标签
- **AND** 未发送任何场景 mutation intent
