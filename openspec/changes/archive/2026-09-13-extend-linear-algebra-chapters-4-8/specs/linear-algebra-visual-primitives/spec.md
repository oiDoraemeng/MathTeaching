## MODIFIED Requirements

### Requirement: High-level primitives express core claims

编译器或其 builder helper SHALL 继续支持前三章已有的 `grid_transform`、`subspace_span`、`projection_bundle`、`batch_mapping`、`staged_transform`、`signed_area`、`volume_orientation`、`comparison_layout` 和 `orientation_marker`，并新增受控语义以表达第 4 至第 8 章绘图目录中的核心关系：

- `subspace_family`：原点、直线、平面、(R^3) 及非子空间仿射对象的维数和包含关系；
- `domain_image_map`：同一线性变换的输入域、核、像和维数守恒；
- `affine_solution_set`：特解加零空间形成的平移直线/平面；
- `constraint_intersection`：方程组约束线/面的唯一、无穷和无解交集状态；
- `elimination_tableau`：增广矩阵/初等矩阵的有序行变换阶段；
- `least_squares_bundle`：数据、拟合对象、投影点和正交残差；
- `basis_coordinate_map`：标准基/备用基的双向坐标翻译；
- `eigen_direction` 与 `spectral_roots`：特征方向、特征值、特征空间和特征多项式根；
- `orthogonalization_bundle`：原向量、投影分量、残差和标准正交基阶段；
- `quadratic_level_set`：二维等值线与三维二次曲面，包含主轴、定性和退化状态。

这些语义 SHALL 映射到现有受控操作或新增同样受校验的操作；不得用几根未关联向量、空白网格或普通 polygon 代替上述关系。

#### Scenario: Compile a chapter-four subspace claim

- **WHEN** artifact 声明列空间、零空间和 rank-nullity 的 `domain_image_map`
- **THEN** 计划包含输入域、核、像、输出和维数标签
- **AND** 缺少核/像关系时编译失败，不生成降级图

#### Scenario: Compile a chapter-five affine solution

- **WHEN** artifact 声明 (x_p+\operatorname{Null}(A)) 的 `affine_solution_set`
- **THEN** 计划同时包含特解、零空间方向和对应平移后的解集
- **AND** 只有特解点而没有零空间证据时契约校验失败

#### Scenario: Compile a chapter-eight level set

- **WHEN** artifact 声明含交叉项的二次型和主轴变换
- **THEN** 计划显示原坐标等值线、特征向量主轴和变换后的标准等值线
- **AND** 正定、不定或退化状态必须在视觉元数据和标注中可区分

#### Scenario: Core claims are visible

- **WHEN** 渲染前三章的零空间、AB 与 BA 或 `det(AB)` 主题
- **THEN** 场景继续包含既有契约要求的零空间区域、阶段链、可区分终点和面积数值
- **AND** 新增的第 4 至第 8 章原语不得改变前三章的 plan digest 语义

### Requirement: Topic visual contracts

每个第 4 至第 8 章绘图主题 SHALL 有静态 `VisualContract`，声明讲义来源支持的 claims、实体、关系、语义原语、最小阶段数、不变量和必须区分的对象。验证器 SHALL 对 39 个新增主题逐项检查契约与实际 plan op 的一致性，并保留前三章现有契约行为。

#### Scenario: Extended capability reaches an actual operation

- **WHEN** `ch07.diagonalization` 声明特征基三步路径
- **THEN** 编译计划包含换基、独立缩放和换回的阶段操作以及两个可追踪终点
- **AND** 只声明 `staged_transform` 但缺少阶段链时验证失败

#### Scenario: Declared capability and visual contract agree

- **WHEN** 主题声明 `transformed_grid` 和 `composition_order`
- **THEN** artifact 的视觉语义、VisualContract 和最终 plan 都包含对应网格/阶段表达
- **AND** 任一层缺失都会指出主题 ID、claim、语义关系和预期原语

### Requirement: Deterministic layout and visual roles

第 4 至第 8 章的新增语义 SHALL 使用稳定 seed、命名空间、章节级角色颜色和可校验边界。双空间、并排比较、矩阵 tableau 和二次曲面布局发生重叠、溢出或角色未知时，编译 SHALL 返回明确诊断，不得静默裁剪或改画成无关图形。

#### Scenario: Same artifact has stable layout

- **WHEN** 同一个第 8 章 artifact 在相同渲染 profile 下编译两次
- **THEN** 两次计划的别名、阶段顺序、坐标和角色颜色一致
- **AND** 布局越界时两次都返回同一类布局错误而不提交场景

### Requirement: Static storyboard stages

视觉语义 SHALL 支持静态 storyboard。每个阶段可以声明标题、说明、可见实体、强调关系、不变量和布局槽位；阶段可以按顺序快照、并排车道或叠加图展示，不要求连续动画。第 4 至第 8 章的消元、换基、特征基和主轴变换 SHALL 复用该机制。

#### Scenario: Read an extended derivation by stages

- **WHEN** 用户阅读高斯消元、Gram–Schmidt 或主轴定理的 storyboard
- **THEN** 可以按顺序看到输入、阶段中间量、结果和不变量
- **AND** 切换阶段只改变展示状态，不重新生成数学内容或绕过场景校验

#### Scenario: Read a derivation by stages

- **WHEN** 用户阅读投影公式的 storyboard
- **THEN** 可以依次看到输入、投影、垂足、残差和正交关系
- **AND** 切换阶段只改变展示状态，不重新生成数学内容或绕过场景校验

### Requirement: Single rendering path

主题 recipe SHALL 统一经过 `recipe_for_entry`、`VisualSemanticsCompiler` 和 `SceneCommandService`。第 4 至第 8 章不得引入按标题或能力名称自动拼装的旁路；不得保留未被主题调用的模板渲染路径。

#### Scenario: No dead template path for chapters four through eight

- **WHEN** 生成任意第 4 至第 8 章课程主题图形
- **THEN** 只使用主题 artifact 的视觉语义和对应 builder/compiler
- **AND** 不存在绕过 VisualContract 的 `_build_plan` 模板路径

#### Scenario: No dead template path

- **WHEN** 生成任意课程主题图形
- **THEN** 只使用主题 artifact 的视觉语义和对应 builder/compiler
- **AND** 不存在绕过 VisualContract 的 `_build_plan` 模板路径
