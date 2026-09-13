## MODIFIED Requirements

### Requirement: Lecture-grounded teaching artifact

`ExplanationContent` SHALL 支持由讲义片段生成的结构化数学解释，并由同一个 `TeachingArtifact` 携带对应的视觉语义。产物 SHALL 记录 `topic_id`、`source_anchor`、`source_hash` 和生成元数据。

对于 `ch01.ops.addition`，数学解释 SHALL 至少包含定义、与讲义一致的公式、几何意义和一个或多个可复算数字案例；仅在讲义提供或可逐步验证时包含推导。该主题不强制生成直觉、主题关联或其他通用字段。

其他主题继续遵守其 profile 声明的必需字段。

#### Scenario: Vector addition uses only supported layers

- **WHEN** 子智能体为向量加法生成教学产物
- **THEN** 产物包含定义、公式、几何意义和讲义支持的必要案例
- **AND** 没有依据的推导、直觉或关联字段被省略

#### Scenario: A topic is grounded in the lecture

- **WHEN** 子智能体为一个树叶主题生成教学产物
- **THEN** 产物包含与 `LessonEntry.source_anchor` 相同的讲义路径和锚点
- **AND** 定义、公式和数字例题可以在当前主题片段中找到依据或直接推导
- **AND** `source_hash` 与生成时使用的规范化片段一致

### Requirement: Boundary cases and misconceptions

达到 L3 的主题 SHALL 说明至少一个不变量、边界情况或退化情况；常见误解不是固定必填字段。向量加法只有在讲义或公式能明确反驳时才列出误解，否则 SHALL 省略。

#### Scenario: Misconception is evidence based

- **WHEN** 讲义和公式能够反驳“向量长度直接相加”或“平移改变向量”
- **THEN** 解释可以列出对应误解及反驳公式/图形证据
- **AND** 不添加讲义未支持的学习心理或应用误解

#### Scenario: Degenerate case is explained

- **WHEN** 主题解释 `det=0`
- **THEN** 同时说明非零向量共线、面积塌缩和不可逆之间的关系
- **AND** 视觉语义包含 `collapses_to`、零面积或等价的退化证据

### Requirement: Explanation depth is visible in the lecture view

解释视图 SHALL 在存在对应字段时分别展示定义、公式、主推导、数字案例、几何意义、常见误解、不变量和读图提示。缺省字段 SHALL 隐藏，不得留下空白占位；向量加法的直觉和关联字段缺省时不得显示空区块。

#### Scenario: Optional sections stay absent

- **WHEN** 向量加法 artifact 没有 `intuition` 或 `connections`
- **THEN** Qt 和 Web 解释视图不显示这些标题或空白容器
- **AND** 定义、公式、案例和几何意义仍按顺序显示
