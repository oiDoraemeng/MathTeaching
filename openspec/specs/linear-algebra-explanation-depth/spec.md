# linear-algebra-explanation-depth Specification

## Purpose
把前三章线性代数主题从摘要式说明提升为可逐层阅读、可复算、可用图形验证的数学教学解释，并明确每一层的可验收目标。

## Requirements

### Requirement: Five-level explanation ladder

每个主题 SHALL 声明最低教学层级和对应内容：L0 看见对象，L1 读懂定义与公式，L2 算出数字例题，L3 解释几何意义与不变量，L4 迁移到关联主题或变式。

核心主题和桥接主题 SHALL 至少达到 L3；需要连接后续章节的主题 SHALL 达到 L4；高维类比主题可以停在 L3，但必须明确类比边界。

#### Scenario: A topic declares measurable depth

- **WHEN** 一个矩阵复合主题声明最低层级 L3
- **THEN** 产物包含定义、公式、推导、可复算例题、几何过程和不变量
- **AND** 缺少任一必需部分时校验器报告对应层级和字段

### Requirement: Claim-backed lecture explanation

解释 SHALL 由可追溯的数学 claims 组织。每个 claim SHALL 说明论断、公式或计算依据，并可以引用视觉实体、关系和阶段作为证据。解释区块不得只靠自然语言声称“图形可以说明”。

#### Scenario: Geometric statement has evidence

- **WHEN** 解释声称“投影残差与目标方向正交”
- **THEN** 至少有一个 claim 引用残差、目标方向和 `orthogonal_to` 关系
- **AND** 编译后的图形契约要求该关系可见

### Requirement: Lecture-grounded teaching artifact

`ExplanationContent` SHALL 支持由讲义片段生成的结构化数学解释，并由同一个 `TeachingArtifact` 携带对应的视觉语义。产物 SHALL 记录 `topic_id`、`source_anchor`、`source_hash` 和生成元数据。

数学解释 SHALL 至少包含：定义、与讲义一致的公式、主推导链、细化推导、具体数例、直觉、几何意义、结论、具体易错点、主题关联和读图提示。

#### Scenario: A topic is grounded in the lecture

- **WHEN** 子智能体为一个树叶主题生成教学产物
- **THEN** 产物包含与 `LessonEntry.source_anchor` 相同的讲义路径和锚点
- **AND** 定义、公式和数字例题可以在当前主题片段中找到依据或直接推导
- **AND** `source_hash` 与生成时使用的规范化片段一致

### Requirement: Derivation and visual reading are distinct

`steps` 和 `derivation` SHALL 只描述数学推理；`interaction_hint` SHALL 只描述如何将公式、对象和关系读成图像。任何字段 SHALL 不包含 CommandPlan、场景 op、Python、Qt 或 HTML 代码。

#### Scenario: No executable drawing leakage

- **WHEN** 校验器检查子智能体回复
- **THEN** 回复不得出现 `op` 字段、`geometry.*`、`linear.*`、Qt 类名或可执行代码块
- **AND** 仍必须提供可供视觉编译器使用的数学对象和关系语义

### Requirement: Worked examples are machine-checkable

每个达到 L2 的主题 SHALL 至少包含一个 `WorkedExample`，其字段为 `given`、`calculation`、`result` 和 `checks`。验证器 SHALL 对向量运算、内积、投影、行列式、面积/体积和矩阵变换等支持类型复算；无法复算的例题 SHALL 标为人工审核项。

#### Scenario: Numeric example catches an incorrect explanation

- **WHEN** 例题声称 `det(A)=6`，但 `checks` 按给定矩阵计算得到其他值
- **THEN** artifact 校验失败
- **AND** 旧的 published artifact 不被覆盖

### Requirement: Boundary cases and misconceptions

达到 L3 的主题 SHALL 说明至少一个不变量、边界情况或退化情况；所有主题 SHALL 至少列出一个与讲义内容相关的具体误解。误解必须能够被公式或图形证据反驳。

#### Scenario: Degenerate case is explained

- **WHEN** 主题解释 `det=0`
- **THEN** 同时说明非零向量共线、面积塌缩和不可逆之间的关系
- **AND** 视觉语义包含 `collapses_to`、零面积或等价的退化证据

### Requirement: Searchable deep content

`searchable_text` SHALL 自动聚合标题、摘要、公式、定义、直觉、推导、算例、误解、关联和读图提示。树搜索命中深度字段时 SHALL 保留主题的章节和小节祖先。

#### Scenario: Search a term introduced only in a derivation

- **WHEN** 用户搜索只出现在 `derivation` 或 `pitfalls` 中的术语
- **THEN** 对应主题叶子及其祖先路径仍然显示

### Requirement: Explanation and visual semantics are paired

每个已发布主题 SHALL 同时提供数学解释和 `visual_semantics`。数学解释中的公式变量、数字结果和结论 SHALL 能在视觉语义的实体、关系、阶段或不变量中找到对应证据。

#### Scenario: Explanation drives a matching visual

- **WHEN** 用户打开任意已发布叶子主题
- **THEN** 解释中的公式变量可以在视觉语义中找到对应实体
- **AND** 编译后的图形展示解释所声明的关系，而不是仅显示无关向量
