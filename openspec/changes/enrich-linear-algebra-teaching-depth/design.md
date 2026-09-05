# Design: 线性代数数形结合教学规划器

## 1. 设计结论

本变更把讲义解释、视觉语义和绘图计划拆成三层：

```text
线性代数讲义.md
        |
        v
Explanation Agent
        |
        v
TeachingArtifact = 数学解释 + 视觉语义
        |                         |
        |                         +--> VisualSemanticsCompiler --> CommandPlan
        v                                             |
版本化内容仓库                                      v
        |                                      SceneCommandService
        +--> 树节点 topic_id -------------------------> 场景
```

子智能体可以理解“要画什么数学关系”，但不能输出执行命令、Python、Qt 或 HTML。只有确定性的编译器能够产生 `CommandPlan`，并且最终计划仍须通过现有 `SceneCommandService` 校验。

运行时不在用户点击主题时调用模型。子智能体在内容生成/更新阶段运行，输出先保存为 draft，经过结构和来源校验后发布为软件内置资源。这样既保留子智能体回复，又保证同一个树节点每次打开得到一致的解释和图形。

## 2. 讲义来源与主题上下文

### 2.1 SourceContext

讲义是唯一知识来源。生成一个主题时，`LectureSourceRepository` 根据 `LessonEntry.source_anchor` 提取：

- 当前主题 heading 及其正文；
- 当前节的定义、公式和例题上下文；
- 前后相邻的已收录主题标题，用于生成 `connections`；
- 排除“练习”“自检”“挑战”和未纳入前三章课程树的正文。

提取结果保存为不可变的 `SourceContext`：

```text
source_path: [章, 节, 主题]
heading_path: string[]
heading_level: integer
occurrence: integer
excerpt: string
source_hash: sha256(normalized_excerpt)
```

`source_hash` 用于发现讲义更新。讲义内容发生变化时，旧产物可以继续读取，但验证命令必须将其标记为 stale，不能静默当作最新解释。

### 2.2 主题绑定

`topic_id` 是唯一绑定键，且必须同时出现在：

1. `LessonEntry.id`；
2. `TeachingArtifact.topic_id`；
3. `VisualizationRecipe.id` 所对应的主题；
4. 树叶的 `Qt.ItemDataRole.UserRole`；
5. 内容和场景加载事件的 payload。

显示标题、公式或搜索词不得用于运行时匹配图形，避免同名主题错配。

## 3. TeachingArtifact 数据模型

### 3.1 顶层结构

保存格式为 JSON，禁止通过 pickle 或动态 Python 导入恢复内容。推荐文件布局：

```text
linear_algebra/explanations/data/
  ch01/<topic_id>.json
  ch02/<topic_id>.json
  ch03/<topic_id>.json
```

每个文件包含：

```json
{
  "schema_version": 1,
  "topic_id": "ch01.vector.magnitude",
  "source": {
    "source_path": ["第1章 ...", "1.1 ...", "1.1.1 ..."],
    "heading_path": ["第1章 ...", "1.1 ...", "1.1.1 ..."],
    "heading_level": 4,
    "occurrence": 1,
    "source_hash": "sha256:..."
  },
  "generated": {
    "provider": "...",
    "model": "...",
    "prompt_version": "...",
    "created_at": "...",
    "status": "published"
  },
  "explanation": { "...": "..." },
  "visual_semantics": { "...": "..." }
}
```

时间戳和模型元数据用于审计，不参与搜索和渲染内容。发布文件必须是 UTF-8、稳定排序键和可复现的 JSON 序列化。

### 3.2 ExplanationContent

保留现有兼容字段：`title`、`summary`、`formula`、`steps`、`geometric_meaning`、`conclusion`、`searchable_text`。新增字段如下：

```text
definition: str
intuition: str
derivation: tuple[str, ...]
worked_examples: tuple[WorkedExample, ...]
pitfalls: tuple[str, ...]
connections: tuple[TopicConnection, ...]
interaction_hint: str
symbol_roles: dict[str, str]
```

约束：

- `steps` 是面向学生的主推导链，不再写“点击/拖动/画出”这类 UI 操作；至少 3 条，至少一条包含“因为/所以/即/由…得”等推导连接词。
- `derivation` 可以比 `steps` 更细，重点主题至少 3 个推导节点；桥接主题至少 2 个；拓展主题可以明确“这是类比而非证明”。
- `WorkedExample` 使用结构化字段：`given`、`calculation`、`result`、`checks`，其中 `checks` 至少包含一条可由验证器复算的数值关系。
- `pitfalls` 至少一条，必须对应讲义中实际容易混淆的语义或符号，不得用空泛的“注意细节”。
- `connections` 只引用存在的 `topic_id`，并说明 `prerequisite`、`extends` 或 `contrasts` 关系。
- `interaction_hint` 只解释“如何阅读图上的数学关系”，不写绘图命令。
- `symbol_roles` 是可选的符号到教学角色映射，例如 `a -> vector_a`、`det(A) -> area`。

`searchable_text` 由标题、摘要、公式、定义、直觉、推导、算例、误解和关联文本规范化聚合生成，不允许手工漏掉新增字段。

### 3.3 VisualSemantics

视觉语义是解释的数学投影，不是场景协议。它只允许以下受控词汇：

```text
scene: 2d | 3d
focus: vector | operation | linear_map | projection | subspace |
       determinant | inverse | cross_product | volume | analogy
entities[]: point | vector | basis | matrix | grid | region | area | volume
relations[]: sum | difference | scalar_multiple | maps_to | spans |
             projects_to | orthogonal_to | collapses_to | compare |
             composition_order | orientation | invariant
stages[]: { name, transform, inputs, outputs, expected_invariant }
annotations[]: { text, target, role }
layout: overlay | side_by_side | sequence
```

实体可以携带讲解所需的有限数字向量、矩阵和标签；不得携带 `op`、Qt 对象名、Python 表达式或任意代码。`relations` 引用实体 ID，`stages` 引用定义过的矩阵和输入。

例如 `ch02.matrix.composition` 的语义是两条 `composition_order` 链和一个 `compare` 关系；编译器再决定使用哪组具体坐标、阶段颜色和标注位置。

## 4. 数学解释子智能体

### 4.1 接口

新增 `ExplanationAgent` 协议：

```python
generate(context: SourceContext, topic: LessonEntry,
         visual_vocabulary: VisualVocabulary) -> TeachingArtifactDraft
```

适配器可以复用现有 provider 的连接和模型设置，但输出通道与生成 CommandPlan 的 agent 分离。子智能体的 system prompt 必须明确：

1. 只能依据提供的 `SourceContext`，不能补写讲义之外的新章节事实；
2. 使用中文和 KaTeX 兼容公式；
3. 输出单个结构化 JSON，不输出 Markdown 围栏、代码或命令；
4. 必须填写定义、推导、数字算例、几何意义和误解；
5. `visual_semantics` 只描述数学对象、关系和不变量，不出现场景 op；
6. 所有数字算例必须能由 `checks` 复算。

### 4.2 生成和发布流程

```text
读取 SourceContext
  -> 调用 ExplanationAgent
  -> JSON/schema 校验
  -> 数字算例复算
  -> topic_id/source_anchor/source_hash 校验
  -> visual_semantics 引用和词汇校验
  -> 保存 draft
  -> 人工确认后发布 bundled artifact
```

生成失败时保留旧的 published 版本，并将 draft 错误写入诊断日志；不得用截断文本或空字段自动发布。

## 5. 视觉语义编译器

### 5.1 编译边界

`VisualSemanticsCompiler` 是唯一允许把教学产物转换为 `CommandPlan` 的组件：

```python
compile(artifact.visual_semantics, contract, context) -> CommandPlan
```

它负责确定性坐标、命名空间、颜色角色、并排布局、阶段编号和标签位置。模型不得直接控制这些执行细节。

### 5.2 语义到原语的映射

| 数学语义 | 首选原语 | 典型教学用途 |
|---|---|---|
| `vector`, `sum`, `difference` | 2D/3D vector + polygon | 向量运算、线性组合 |
| `grid`, `maps_to`, `invariant` | transformed grid | 基向量变换、重复变换 |
| `projects_to`, `orthogonal_to` | projection + right-angle marker | 投影、内积、力分解 |
| `spans`, `collapses_to` | subspace region + vectors | 秩、零空间、列空间 |
| `composition_order`, `stages` | staged transform + stage snapshots | AB 与 BA、逆序、矩阵幂 |
| `area`, `orientation` | oriented area + labeled polygon | 行列式符号、面积缩放 |
| `volume` | parallelogram/parallelepiped/oriented volume | 混合积与高维类比 |
| `compare`, `annotations` | namespaced annotations and endpoint markers | 数值和终点对比 |

现有原语可以满足大多数 2D 主题。若语义要求“3D 旋转弧”“阶段中的完整形状快照”而现有原语无法表达，先增加 builder-level helper；只有 helper 无法编译为合法场景对象时，才扩展 scene command 白名单和宿主渲染器。

### 5.3 主题视觉契约

每个主题维护一个静态 `VisualContract`，内容包括：

```text
required_entities: tuple[str, ...]
required_relations: tuple[str, ...]
required_semantic_primitives: tuple[str, ...]
minimum_stage_count: int
```

例如：

- 零空间：`region + input_vectors + collapses_to`，至少 3 条输入向量；
- AB 与 BA：两条 `composition_order` 链、两个终点和 `compare`；
- det(AB)：至少 3 个面积阶段、每阶段数值标注；
- 叉积：`a`、`b`、`cross_result`、`orientation` 和右手关系。

编译器必须同时满足语义契约和 catalog 的 `required_capabilities`。计划中实际出现的 op 由验证器再次检查。

## 6. 树形结合与原子加载

用户点击树叶时：

1. `LinearAlgebraTreeModel` 发出 `topic_id`；
2. registry 解析 `LessonEntry` 和 published `TeachingArtifact`；
3. 校验来源哈希、解释完整性、视觉契约并编译 plan；
4. `SceneCommandService.preview()` 成功后，才提交场景清空/执行；
5. 场景提交成功后，Qt/Web 内容视图显示解释；
6. 任一步失败，原场景和旧解释保持不变，并显示主题 ID、失败阶段和修复提示。

解释视图按定义、公式、推导、算例、几何意义、常见误解、主题关联和读图提示分区。`visual_semantics` 不直接展示成命令文本；可以依据 `symbol_roles` 和 palette 渲染符号图例。

## 7. 三章教学覆盖标准

### 第 1 章：向量与几何测量

核心叙事是“对象、运算、测量和证明方法”：

- 向量/点/坐标：区分位置与位移；
- 加法/数乘/线性组合：用首尾相接、平行四边形和系数解释可达性；
- 内积/投影：同一公式同时解释长度、夹角、正交和分解；
- 叉积/混合积：补方向、法向量、有向面积和体积；
- 几何证明/n 维类比：明确低维图是结构类比，不是假装画出 n 维空间。

### 第 2 章：矩阵的诞生

核心叙事是“矩阵作为批处理和线性变换”：

- 批量内积/投影：一对多测量和统一方向；
- 行/列视角：同一个 `Ax` 的两种等价计算；
- 基向量/网格：两列决定整个网格；
- 拉伸/旋转/缩放、复合和矩阵幂：阶段和顺序必须可见；
- 秩/零空间/列空间：输出维度、丢失方向和可达区域必须用区域/汇聚表达；
- 高维类比：保留规则，不虚构高维图形。

### 第 3 章：行列式与逆矩阵

核心叙事是“有向测度、可逆性和面积/体积缩放”：

- `ad-bc`：面积分解和符号来源；
- det 的正/零/负/一：方向翻转、塌缩和保持面积；
- 乘法性：单位区域、A 后区域、B 后区域的三阶段数值对比；
- 逆矩阵：可逆与退化并排、正向和逆向撤销链；
- n 阶类比：面积、体积和高维测度的共同结构。

## 8. 验证、测试与回退

验证分为四层：

1. **来源层**：54 个主题仍为 24/15/15，锚点、顺序和 `source_hash` 正确；
2. **内容层**：字段完整、推导和算例可复算、关联 ID 存在、无模型命令泄漏；
3. **语义层**：实体/关系引用闭合，语义词汇和主题视觉契约满足；
4. **执行层**：编译出的 plan 通过 `SceneCommandService`，且 catalog 能力映射的实际 op 全部存在。

测试重点包括：

- agent JSON 解析、拒绝代码/命令和 source-only 约束；
- artifact round-trip、draft/published 版本和 stale hash；
- 数字算例复算及错误报告；
- 54 个 topic 的树节点到 artifact/recipe 一一对应；
- 重点主题的零空间汇聚、AB/BA 双链、det(AB) 三阶段和叉积方向；
- Qt/Web 新解释区块和旧 artifact 的向后兼容；
- 编译器遇到不支持语义时明确失败，不生成降级的无关图。

内容资源可以按章节独立发布；任何一章的产物出错都不影响其他章节和已发布版本。可视化编译器和场景协议的变更必须保留旧命令的兼容行为。
