## Purpose

为数学论断、视觉实体、场景对象和解释图例提供稳定的教学角色颜色，使数形结合中的“同一对象”和“不同路径”在各章节中保持可辨识。

## ADDED Requirements

### Requirement: Palette is the single source of teaching-role colors

`linear_algebra/visualizations/palette.py` SHALL define the single mapping from teaching roles to colors and expose `role_color(role: str) -> str`。视觉语义只能引用角色，不得携带十六进制颜色；视觉编译器、builder、Qt 图例和 Web 图例 SHALL 使用同一映射。

角色至少覆盖：`vector_a`、`vector_b`、`basis_e1`、`basis_e2`、`transformed_a`、`transformed_b`、`area`、`projection`、`residual`、`neutral`。

#### Scenario: Unknown role falls back to neutral

- **WHEN** `role_color` 收到未定义角色
- **THEN** 返回 `neutral` 颜色
- **AND** 不因单个缺失角色阻断整张教学图

### Requirement: Visual semantics and explanation share roles

`TeachingArtifact` 的 `symbol_roles` SHALL 将解释中的符号映射到教学角色。视觉语义实体和编译后的场景对象 SHALL 使用相同角色；不同主题中表示同一数学角色的对象 SHALL 保持颜色稳定。

#### Scenario: Formula and diagram agree

- **WHEN** artifact 将 `a` 映射到 `vector_a`、将 `det(A)` 映射到 `area`
- **THEN** 公式图例中的 `a` 与图中向量 a 使用同一角色颜色
- **AND** 面积标注与有向面积区域使用同一角色颜色

### Requirement: No hard-coded colors outside palette

视觉编译器和场景适配层 SHALL 禁止在 palette 之外硬编码教学颜色的十六进制字面量。

#### Scenario: No hard-coded colors outside palette

- **WHEN** 检索 `linear_algebra/visualizations/` 和视觉编译器实现
- **THEN** 除 palette 定义外不得存在教学颜色的十六进制字面量
- **AND** 场景命令中的颜色字段由角色映射产生

### Requirement: Claim and stage color continuity

同一个 claim 在不同 storyboard 阶段中的实体 SHALL 保持相同教学角色颜色；比较关系涉及的对象 SHALL 使用可区分的角色。Qt 和 Web 图例 SHALL 根据 artifact 的 `symbol_roles` 与同一 palette 生成，而不是重新猜测颜色。

#### Scenario: A path keeps its identity across stages

- **WHEN** `AB` 变换链在三个阶段中展示同一个输入向量和其结果
- **THEN** 输入、第一阶段结果和第二阶段结果的角色颜色符合 artifact 声明
- **AND** `BA` 链与 `AB` 链可通过角色或布局稳定区分

### Requirement: Palette errors are diagnostic

未知角色 SHALL 返回带主题 ID、实体 ID 和角色名称的可诊断错误或 `neutral` 回退状态。回退不得改变 claim、关系或阶段的身份，也不得注入任意颜色字面量。

#### Scenario: Unknown role does not corrupt semantic identity

- **WHEN** artifact 引用未定义的教学角色
- **THEN** 编译器返回角色诊断并按约定使用 `neutral` 回退
- **AND** 解释变量和视觉实体的绑定仍保持不变
