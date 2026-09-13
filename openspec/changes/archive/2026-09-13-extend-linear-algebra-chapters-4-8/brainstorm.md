# 第 4–8 章可视化：Superpowers 风格头脑风暴与收敛记录

> 本文件记录“发散候选 → 约束筛选 → 收敛决策”的过程。它是本次 OpenSpec 的设计证据，不是运行时配置，也不要求实现阶段逐字照搬其中的候选方案。

## 1. 设计问题与成功定义

第 4–8 章不是把 39 个标题各自画一张图，而是要让读者沿着一条可复用的几何叙事理解：

`子空间与解集 → 约束与消元 → 坐标改变 → 特征方向与正交分解 → 二次型主轴`

成功条件有三层：

1. **数学证据层**：每个绘图主题至少有一个可追溯的 claim、实体关系和不变量；图形必须能区分讲义要求区分的对象（例如无解/唯一解/无穷解）。
2. **工程边界层**：所有图形先通过 `TeachingArtifact`、`VisualContract` 和编译器，再进入 `CommandPlan`；未知关系、非有限数值、布局溢出和未接入的 renderer 都是可诊断失败。
3. **教学体验层**：图形采用静态 storyboard，读者可以看输入、变换、中间量和结论；解释、公式和图形通过同一个 `topic_id` 关联，切换阶段不重新生成数学内容。

## 2. 发散候选

### 候选 A：每个主题一个专用 builder

- 优点：实现直接，单个主题容易调坐标。
- 风险：39 个 builder 会复制消元、坐标变换和主轴逻辑；同一数学关系在不同主题上容易产生不同颜色、命名和数值误差；契约难以证明 builder 真的表达了 claim。

### 候选 B：一个通用“公式画图器”

- 优点：接口少，新增公式看似快捷。
- 风险：容易退化为任意表达式执行；无法保证交集状态、谱根绑定或残差正交；也不能从标题可靠推断应该画什么。

### 候选 C：少量场景族 + 主题级数据 fixture

- 优点：共同数学关系只有一份编译和渲染逻辑；主题仍能通过 fixture 单独修改数字例子、说明和 stage；可以对场景族编写黄金计划和属性测试。
- 代价：需要先设计稳定语义 payload 和能力边界，初期工作量大。

**暂定选择：C。** 39 个主题按场景族复用编译器，章节模块只负责目录、解释、契约和受控数据，不直接拼 `CommandPlan`。

### 候选 D：一个巨大的静态画布

- 优点：读者一次看到所有对象。
- 风险：窄视口中域/核/像、矩阵 tableau 和二次曲面会重叠；推导步骤不清晰；无法表达“同一对象在变换前后”的不变量。

### 候选 E：分车道 storyboard

- 每个 stage 使用固定槽位（`left` 输入、`center` 变换或关系、`right` 输出），必要时增加 `top` 公式与 `bottom` 读图提示。
- 只显示该阶段声明的实体，阶段之间共享稳定 alias；不使用连续动画模拟推导。

**暂定选择：E。** “同一实体跨阶段 alias 不变”是验证器可检查的证据，且适合 Qt、Web 和离线截图。

### 候选 F：把高维空间直接投影成任意 2D/3D 图

- 优点：渲染简单。
- 风险：读者会把低维示例误认为一般 (n) 维定理，且投影可能改变交集和秩的视觉关系。

### 候选 G：低维代表模型 + `analogy_boundary`

- 数值例子使用 (R^2/R^3)；实体和关系仍标注抽象名称（如 `Null(A)`、`Col(A)`）；解释明确哪些是代表模型、哪些是一般维数结论。
- 编译器拒绝没有边界说明的高维 profile。

**暂定选择：G。** 这与已有 artifact schema 和前三章的类比边界机制一致。

### 候选 H：把直线、平面、二次型都降级为 curve/surface

- 优点：可以少加 command op。
- 风险：`curve.create` 的表达式没有约束交集状态，`surface.create` 不能声明主轴或定性；结果虽然“看起来像图”，却没有教学证据。

### 候选 I：受控高层操作

新增操作只对应一类可验证关系：`subspace3d`、`constraint`、`mapping_bundle`、`matrix_tableau`、`least_squares`、`spectrum`、`projection3d`、`quadratic_level_set`。每个操作有有限字段、维度和数量上限，编译器负责展开为现有 renderer 可执行的原子操作。

**暂定选择：I。** 高层操作不是绕过 `SceneCommandService`，而是先 schema 校验、再展开、再对展开结果做同样的白名单和场景校验。

### 候选 J：运行时即时编译

- 优点：修改后马上可见。
- 风险：用户点击叶子时才发现源 hash、契约或 renderer 不完整，无法可靠保留上一场景。

### 候选 K：发布时编译快照

- 发布阶段生成 `artifact revision + contract digest + compiled plan digest`；运行时只加载完整快照。
- 单章发布或回滚只切换该章索引，前三章快照不变。

**暂定选择：K。** 调试模式可以离线重新编译，但不能把未发布结果提交给用户画布。

## 3. 收敛后的五个场景族

| 场景族 | 主题范围 | 最小视觉证据 | 必须区分的状态 |
| --- | --- | --- | --- |
| `subspace_structure` | Ch4 span、子空间、维数、秩、核/像；Ch5 齐次解 | 生成向量、包含关系、原点/维数、核与像 | 子空间 vs 仿射集；独立 vs 冗余 |
| `constraint_solution` | Ch5 非齐次解、交集、高斯消元、最小二乘 | 约束线/面、交集或残差、增广矩阵 stage | 唯一/无解/无穷；精确解 vs 拟合 |
| `basis_coordinate` | Ch4 坐标读数；Ch6 基变换、相似变换 | 两套基、同一几何向量的双坐标、变换前后矩阵 | 几何向量不变 vs 坐标数字改变 |
| `spectral_orthogonal` | Ch7 特征方向、谱、特征空间、对角化、Gram–Schmidt | 特征方向/空间、根绑定、投影分量、正交基 | 特征向量 vs 任意方向；正交 vs 非正交 |
| `quadratic_shape` | Ch8 等值线、主轴、定性、配方法、合同惯性 | 原坐标等值线、主轴、标准形、签名/退化标记 | 椭圆/双曲线/抛物型/退化 |

一个主题可以使用一个主场景族和最多一个辅助场景族，但必须在 contract 中显式声明组合；禁止通过标题猜测组合。

## 4. 四个代表性主题的最小故事板

### `ch04.subspace.col-null`

1. `input`: 域中的向量和矩阵作用。
2. `collapse`: 核中的方向被映射到零点。
3. `output`: 像空间中的结果向量。
4. `invariant`: `rank + nullity = domain_dimension`。

必须存在 `maps_to`、`collapses_to`、`spans` 关系；只有画两条孤立线不能通过 contract。

### `ch05.consistency.geometry`

1. `unique`: 两条约束线相交于一个点。
2. `none`: 平行且不重合，交集为空。
3. `infinite`: 重合或约束秩不足，交集为线。

三个状态使用同一 `constraint_id` 命名规则和同一布局槽位，保证比较时只改变数据和状态，不改变图例语义。

### `ch07.diagonalization`

1. `basis`: 原坐标中的向量和特征基。
2. `scale`: 在特征坐标中沿独立轴缩放。
3. `return`: 换回原坐标，终点与直接应用矩阵一致。

contract 必须同时约束 `change_basis`、`diagonal_scale`、`change_basis_back` 和终点比较；仅有三个 stage 标题而没有这些关系不能通过。

### `ch08.principal-axis`

1. `original`: 含交叉项的倾斜等值线。
2. `axes`: 特征向量标出的主轴和特征值。
3. `standard`: 旋转后的无交叉项标准形。

同一个二次型矩阵 (Q) 必须出现在 payload、解释公式和主轴实体的 claim refs 中；主轴旋转后数值误差由确定性 tolerance 校验，而不是靠截图人工判断。

## 5. 统一的失败语义

任何阶段只能得到以下可分类结果：

- `source_stale`：讲义 occurrence/hash 已变化；
- `contract_missing_evidence`：claim、实体角色、关系或不变量缺失；
- `unsupported_scene_family`：主题声明的场景族没有 renderer；
- `numeric_invalid`：非有限数值、维度不匹配或矩阵条件不满足；
- `layout_overflow`：固定槽位或边界检查失败；
- `plan_invalid`：高层操作展开后不符合 `SceneCommandService`；
- `renderer_unavailable`：目标宿主未注册所需适配器。

失败必须包含 `topic_id`、场景族、stage（若有）和第一个可修复字段；运行时保留当前画布和解释，不生成“近似替代图”。

## 6. 资源上限与确定性预算

- 2D 场景最多 48 个可见实体、3D 场景最多 32 个可见实体；单主题最多 6 个 storyboard stage。
- 二次型隐式网格默认不超过 (128\times128)，3D 采样默认不超过 (64\times64\times64)；超过上限必须在发布阶段拒绝。
- 所有随机示例使用 `RenderContext.seed`；排序键为 `(chapter, section, topic_id, entity_id)`。
- 别名使用 `<topic_id>__<stage>__<semantic_id>` 形式，不能用显示标题生成别名。
- 每个阶段只更新可见状态，不重新生成 artifact、公式或 claim。

## 7. 最终决策

本次实现以 **C + E + G + I + K** 为基线：场景族复用、静态故事板、低维模型边界、受控高层操作、发布时快照。后续若需要新图形，先判断是否属于现有场景族；只有无法表达且有新的讲义关系时，才新增操作和对应 schema/renderer/contract/golden fixture。

