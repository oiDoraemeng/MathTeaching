## ADDED Requirements

### Requirement: Visual semantics are the drawing boundary

`VisualSemanticsCompiler` SHALL be the only component that converts a `TeachingArtifact.visual_semantics` value into a `CommandPlan`。子智能体、解释存储和树模型 SHALL NOT emit or execute scene operations directly。

视觉语义 SHALL 只包含受控的数学词汇：实体（向量、点、基、矩阵、网格、区域、面积、体积）、关系（求和、映射、张成、投影、正交、塌缩、比较、复合顺序、方向、不变量）和阶段。实体关系必须引用已定义的实体 ID。

#### Scenario: Semantic output compiles to a plan

- **WHEN** artifact 描述一个输入向量投影到方向向量
- **THEN** 编译器生成包含输入向量、投影向量、垂足和正交关系的合法 `CommandPlan`
- **AND** 编译过程不执行模型返回的代码或字符串命令

#### Scenario: Unsupported semantics fail loudly

- **WHEN** artifact 使用尚未支持的视觉关系
- **THEN** 编译器返回带关系名称和主题 ID 的能力缺口错误
- **AND** 不生成只画几根无关向量的降级计划

### Requirement: High-level primitives express core claims

编译器或其 builder helper SHALL 能表达以下高级语义，并通过 `services/scene_commands.py` 的白名单校验：

- `grid_transform`：变换前后网格与基向量；
- `subspace_span`：由基向量张成的直线/平面区域；
- `projection_bundle`：多个输入、投影、垂足和残差；
- `staged_transform`：带阶段标签和输入/输出快照的连续变换；
- `signed_area`：有向面积、方向和数值；
- `volume_orientation`：3D 平行六面体或有向体积；
- `comparison_layout`：并排或双链终点对比。

优先将这些语义编译为已有 `geometry.transformed_grid`、`geometry.subspace_region`、`geometry.projection`、`geometry.staged_transform`、`geometry.oriented_area`、`geometry.parallelogram3d`、`geometry.parallelepiped`、`geometry.oriented_volume` 和标注操作；只有已有协议不能表达必要信息时才新增受约束 op。

#### Scenario: Core claims are visible

- **WHEN** 渲染零空间主题
- **THEN** 场景包含着色零空间区域、至少三条输入向量和汇聚到原点的结果
- **WHEN** 渲染 AB 与 BA 主题
- **THEN** 场景包含两条阶段链、两个可区分终点和不等关系标注
- **WHEN** 渲染 `det(AB)` 主题
- **THEN** 场景包含单位区域、A 后区域和 B 后区域及各阶段面积数值

### Requirement: Topic visual contracts

每个主题 SHALL 有静态 `VisualContract`，声明所需实体、关系、语义原语和最小阶段数。编译器 SHALL 在生成 plan 前检查契约；验证器 SHALL 在生成 plan 后检查对应实际 op。

#### Scenario: Declared capability and visual contract agree

- **WHEN** 主题声明 `transformed_grid` 和 `composition_order`
- **THEN** artifact 的视觉语义、VisualContract 和最终 plan 都包含对应的网格/阶段表达
- **AND** 任一层缺失都会指出主题 ID、语义关系和预期原语

### Requirement: Deterministic layout and visual roles

编译器 SHALL 使用 `RenderContext` 的稳定 seed 和命名空间生成坐标、别名、阶段偏移和标签位置；同一 artifact 在相同版本下 SHALL 生成相同 plan。颜色 SHALL 通过教学角色 palette 获取，视觉语义不得携带任意颜色字面量。

并排布局必须保证各子场景具有独立别名和可见标题；重叠或超出视图边界时，编译器 SHALL 返回布局错误而不是静默裁剪。

#### Scenario: Same artifact has stable layout

- **WHEN** 相同 artifact 使用相同编译器版本和 `RenderContext` seed 编译两次
- **THEN** 两次 plan 的实体别名、坐标、阶段顺序和角色颜色一致
- **AND** 任一子场景溢出边界时编译失败并返回布局诊断

### Requirement: Single rendering path

主题 recipe SHALL 统一经过 `recipe_for_entry`、`VisualSemanticsCompiler` 和 `SceneCommandService`。不得保留按能力名称自动拼装、但未被主题调用的模板渲染路径。

#### Scenario: No dead template path

- **WHEN** 生成任意课程主题图形
- **THEN** 只使用主题 artifact 的视觉语义和对应 builder/compiler
- **AND** 不存在绕过 VisualContract 的 `_build_plan` 模板路径
