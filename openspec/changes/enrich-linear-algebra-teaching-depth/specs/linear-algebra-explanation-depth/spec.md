## ADDED Requirements

### Requirement: Lecture-grounded teaching artifact

`ExplanationContent` SHALL 支持由讲义片段生成的结构化数学解释，并由同一个 `TeachingArtifact` 携带对应的视觉语义。产物 SHALL 记录 `topic_id`、`source_anchor`、`source_hash` 和生成元数据，以便审查和发现讲义更新。

数学解释 SHALL 至少包含：

- `definition`：概念或对象的严格定义；
- `formula`：与讲义一致、可渲染的公式；
- `steps`：面向学生的主推导链，至少 3 条；
- `derivation`：重点主题的细化推导；
- `worked_examples`：带具体数字、计算过程和可复算检查的例题；
- `intuition`：不替代定义的直觉类比；
- `geometric_meaning`：图形含义；
- `pitfalls`：至少一条具体易错点；
- `connections`：与其他已存在主题的关系；
- `interaction_hint`：如何阅读图中的数学关系。

#### Scenario: A topic is grounded in the lecture

- **WHEN** 子智能体为一个树叶主题生成教学产物
- **THEN** 产物包含与 `LessonEntry.source_anchor` 相同的讲义路径和锚点
- **AND** 解释中的定义、公式和数字例题可以在当前主题讲义片段中找到依据或直接推导
- **AND** `source_hash` 与生成时使用的规范化片段一致

### Requirement: Derivation and visual reading are distinct

`steps` 和 `derivation` SHALL 只描述数学推理；`interaction_hint` SHALL 只描述如何将公式、对象和关系读成图像。任何字段 SHALL 不包含 CommandPlan、场景 op、Python、Qt 或 HTML 代码。

#### Scenario: No executable drawing leakage

- **WHEN** 校验器检查子智能体回复
- **THEN** 回复不得出现 `op` 字段、`geometry.*`、`linear.*`、Qt 类名或可执行代码块
- **AND** 仍必须提供可供视觉编译器使用的数学对象和关系语义

### Requirement: Worked examples are machine-checkable

每个 `WorkedExample` SHALL 至少包含 `given`、`calculation`、`result` 和 `checks`。验证器 SHALL 对向量加法、内积、投影、行列式、面积/体积和矩阵变换等可支持类型复算；无法复算的例题 SHALL 标为人工审核项，不得伪装成自动通过。

#### Scenario: Numeric example catches an incorrect explanation

- **WHEN** 例题声称 `det(A)=6`，但 `checks` 按给定矩阵计算得到其他值
- **THEN** artifact 校验失败
- **AND** 旧的 published artifact 不被覆盖

### Requirement: Searchable deep content

`searchable_text` SHALL 自动聚合标题、摘要、公式、定义、直觉、推导、算例、误解、关联和读图提示。树搜索命中深度字段时 SHALL 保留主题的章节和小节祖先。

#### Scenario: Search a term introduced only in a derivation

- **WHEN** 用户搜索只出现在 `derivation` 或 `pitfalls` 中的术语
- **THEN** 对应主题叶子及其祖先路径仍然显示

### Requirement: Explanation agent output contract

数学解释子智能体 SHALL 接收 `SourceContext`、主题元数据和受控视觉词汇，返回单个 `TeachingArtifactDraft`。它 SHALL 只生成数学解释及其视觉语义，不得自行执行工具、写入场景或修改树结构。

#### Scenario: Agent returns a paired explanation

- **WHEN** 子智能体处理“矩阵复合与 AB ≠ BA”
- **THEN** 返回内容包含 `(AB)x=A(Bx)` 的推导、数字算例和两种顺序的 `composition_order` 视觉关系
- **AND** 返回内容不包含具体 CommandPlan 操作
