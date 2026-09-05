## ADDED Requirements

### Requirement: Lecture-grounded explanation agent

系统 SHALL 提供一个专门的数学解释子智能体。它接收 `SourceContext`、`LessonEntry` 和受控视觉词汇，输出单个 `TeachingArtifactDraft`；其职责是解释线性代数概念并指出数学对象之间的图形关系。

子智能体 SHALL 使用 `.agents/线性代数讲义.md` 的当前主题片段作为主要依据，不得把练习、自检、挑战或未纳入课程树的章节混入当前主题。

#### Scenario: Agent explains a lecture topic with visual meaning

- **WHEN** 子智能体处理“投影矩阵把一批向量压到方向上”
- **THEN** 输出定义、公式、推导、具体数例、几何意义和易错点
- **AND** 输出输入向量、目标方向、投影结果、垂足和“输出共线”的视觉语义

### Requirement: No executable drawing output

子智能体 SHALL NOT 输出 Python、Qt、HTML、CommandPlan、场景 op、宿主对象名或可执行代码块。视觉语义只能使用白名单中的数学实体、关系、阶段和不变量。

#### Scenario: Model command leakage is rejected

- **WHEN** 子智能体回复包含 `geometry.staged_transform` 或代码块
- **THEN** draft 校验失败
- **AND** 系统不保存或发布该回复

### Requirement: Structured and reviewable response

子智能体 SHALL 返回可解析的 JSON，不得依赖 Markdown 标题解析。每个字段 SHALL 有长度、数量和引用约束；公式变量必须能在 `visual_semantics.entities` 或 `symbol_roles` 中找到对应对象。

生成结果 SHALL 区分 `draft` 与 `published` 状态。模型回复只能先进入 draft；人工或受控发布命令确认后才能成为运行时资源。

#### Scenario: Draft is not runtime content

- **WHEN** 子智能体返回合法 JSON 但尚未完成审核
- **THEN** 系统保存为 `draft` 并允许显示校验错误和审核信息
- **AND** 运行时内容仓库不得读取该 draft

### Requirement: Deterministic regeneration context

生成请求 SHALL 记录 source hash、prompt version、provider/model、schema version 和生成时间。相同讲义片段、提示版本和输入参数 SHALL 可用于复现或比较两次生成结果。

#### Scenario: Regeneration can be compared

- **WHEN** 同一主题以相同 source hash 和 prompt version 再次生成
- **THEN** 系统可以按字段比较新旧 draft，并指出解释或视觉语义的变化
