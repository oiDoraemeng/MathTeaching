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
