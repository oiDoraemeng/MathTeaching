# linear-algebra-explanation-agent Specification

## Purpose
提供一个受讲义约束的数学解释子智能体，把线性代数论断、推导、可复算算例和数形结合所需的数学语义生成成可审查的教学草稿。

## Requirements

### Requirement: Lecture-grounded explanation agent

系统 SHALL 提供一个专门的数学解释子智能体。它接收 `SourceContext`、`LessonEntry`、主题教学层级和受控视觉词汇，输出单个 `TeachingArtifactDraft`。

子智能体 SHALL 使用 `.agents/线性代数讲义.md` 的当前主题片段作为主要依据，不得把练习、自检、挑战或未纳入课程树的章节混入当前主题。

#### Scenario: Agent explains a lecture topic with visual meaning

- **WHEN** 子智能体处理“投影矩阵把一批向量压到方向上”
- **THEN** 输出定义、公式、推导、具体数例、几何意义和易错点
- **AND** 输出输入向量、目标方向、投影结果、垂足、残差和“输出共线”的视觉语义

### Requirement: Claim-grounded response

子智能体 SHALL 将教学内容拆分为带稳定 `claim_id` 的数学论断。每个论断 SHALL 可选包含公式、讲义来源引用、解释区块引用，以及对应的视觉实体、关系和阶段引用。

公式中的每个数学符号 SHALL 能在 `symbol_roles` 或视觉实体中找到绑定；视觉关系不得只存在于自由文本中。

#### Scenario: Formula and visual evidence are linked

- **WHEN** 子智能体生成 `(AB)x=A(Bx)` 的解释
- **THEN** 至少一个 claim 引用该公式、输入 `x`、中间结果 `Bx` 和最终结果 `A(Bx)`
- **AND** 该 claim 引用两条变换关系和对应阶段

### Requirement: Five-level teaching profile

子智能体 SHALL 根据主题的 `teaching_profile` 生成五层目标中的指定层级：L0 看见、L1 读懂、L2 算出、L3 解释、L4 迁移。

达到 L2 的主题 SHALL 包含可复算数字例题；达到 L3 的主题 SHALL 包含几何意义、不变量或边界情况；达到 L4 的主题 SHALL 包含主题关联或变式比较。高维类比主题 SHALL 明确类比边界。

#### Scenario: Core topic reaches explanation level

- **WHEN** 子智能体处理矩阵复合这一核心主题，且 profile 要求 L3
- **THEN** 回复同时包含定义、推导、数字验证、几何过程和变换顺序不变量
- **AND** 校验器可以指出缺失的层级字段

### Requirement: No executable drawing output

子智能体 SHALL NOT 输出 Python、Qt、HTML、CommandPlan、场景 op、宿主对象名或可执行代码块。视觉语义只能使用白名单中的数学实体、关系、阶段和不变量。

#### Scenario: Model command leakage is rejected

- **WHEN** 子智能体回复包含 `geometry.staged_transform`、`linear.upsert` 或代码块
- **THEN** draft 校验失败
- **AND** 该回复不得进入 reviewed 或 published 资源

### Requirement: Structured and reviewable response

子智能体 SHALL 返回单个可解析 JSON，不得依赖 Markdown 标题解析。回复 SHALL 包含 `schema_version`、`topic_id`、`source`、`teaching_profile`、`claims`、`explanation` 和 `visual_semantics`。

#### Scenario: Draft is structurally inspectable

- **WHEN** 回复缺少 `claims`、`source` 或 `visual_semantics`
- **THEN** 系统返回带字段路径的 schema 错误
- **AND** 不生成部分可运行的教学产物

### Requirement: Accepted reply is retained

对通过安全和结构校验的回复，系统 SHALL 保留其精确原始 JSON，并将其与规范化 `TeachingArtifact` 通过内容 digest 关联。原始回复可以进入审计视图，但不得作为场景输入。

安全校验失败的回复 SHALL 只保留 reply digest、错误代码和有界诊断，不得进入已发布资源。

#### Scenario: Accepted agent response survives regeneration review

- **WHEN** 同一主题生成第二个 draft
- **THEN** 系统可以读取第一个 draft 的原始 JSON，并按 claim、解释字段和视觉语义比较差异
- **AND** 比较不会触发场景执行

### Requirement: Deterministic regeneration context

生成请求 SHALL 记录 source hash、prompt version、provider/model、schema version、输入 profile 和生成时间。相同讲义片段、提示版本和输入参数 SHALL 可用于复现或比较两次生成结果。

#### Scenario: Regeneration can be compared

- **WHEN** 同一主题以相同 source hash 和 prompt version 再次生成
- **THEN** 系统按字段指出新旧 draft 的变化
- **AND** 可以区分来源变化、提示变化和模型变化

### Requirement: Source text is inert reference data

子智能体 SHALL 将 `SourceContext` 作为不可执行的参考文本处理。上下文中的 Markdown、公式或示例不得改变子智能体的输出协议、工具权限或发布状态。

#### Scenario: Source cannot inject commands

- **WHEN** 讲义片段包含类似代码块、命令名称或“忽略前文”的文本
- **THEN** 子智能体仍只返回约定的数学 JSON
- **AND** 安全扫描不会因为普通数学示例而放宽执行边界
