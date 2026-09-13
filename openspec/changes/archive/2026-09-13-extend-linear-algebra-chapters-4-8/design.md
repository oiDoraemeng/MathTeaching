## Context

归档的前三章实现已经具备 `LessonEntry`、讲义树、`TeachingArtifact`、`VisualContract`、`VisualSemanticsCompiler` 和受控 `CommandPlan`。当前目录清单、解释资源、builder 注册表和发布校验都在 `chapter_01`–`chapter_03` 范围内；`CommandPlan` 已能表达二维向量/网格/投影/面积、二维子空间、阶段变换和基础三维向量/平面/平行六面体，但不能完整表达第 4–8 章的解集、矩阵 tableau、最小二乘、特征值谱和二次型等值线。

讲义下半部的章节标题层级不完全规整，且把证明、例题、练习和几何结论混在同一小节。绘图目录因此是一个显式、可审查的中间产物，不能由运行时按标题猜测。实现必须保持前三章资源可独立回放，并允许开发者单独修改某一章的 catalog、explanation、contract、builder 和 artifact。

本轮“发散 → 收敛”的候选方案、取舍和代表性主题故事板记录在同目录的 `brainstorm.md`；本文件只保留已收敛的工程决策。

## Goals / Non-Goals

**Goals:**

- 将第 4–8 章 39 个绘图主题接入同一套来源锚点、教学产物、视觉契约和原子加载流程。
- 通过独立章节模块维护目录和资源，修改一个主题不会重写其他章节的 digest 或 plan。
- 只新增能够表达讲义数学关系的受控语义/操作；每个新增能力都必须有 schema、渲染适配器和契约测试。
- 对 2D、3D、双空间、并排比较和静态 storyboard 提供稳定布局、角色颜色和失败诊断。
- 保留前三章的 topic ID、已发布 revision、旧解释适配和现有案例行为。

**Non-Goals:**

- 不修改 `.agents/线性代数讲义.md`，不把章节练习、自检、挑战题注册成主题。
- 不引入连续动画、运行时模型调用或让子智能体直接生成场景操作。
- 不新增自由格式的“画任意方程”接口；隐式直线/平面和二次型只支持受控数值字段。
- 不因第 4–8 章增加绘图主题而重写前三章解释内容或更改现有工具栏交互。

## Decisions

### 1. 用独立的绘图目录冻结“为什么画”

`drawing-catalog.md` 是来源审查结果，逐项记录 `topic_id`、讲义路径、教学主张、现有能力和缺口。catalog 不是第二套课程树：章节/小节顺序仍由 `LessonEntry` 提供，catalog 只决定哪些目录成为绘图叶子以及该叶子需要哪些视觉证据。

替代方案：在 builder 中看到关键词就自动画图。拒绝，因为同一个关键词可能出现在证明、练习或旁注里，无法保证和讲义主张一致。

### 2. 章节代码与资源分片

新增 `catalog/chapter_04.py` 至 `chapter_08.py`、`explanations/chapter_04.py` 至 `chapter_08.py`、`visualizations/chapter_04.py` 至 `chapter_08.py`、`visualizations/builders/chapter_04.py` 至 `chapter_08.py`，并由 manifest/index 显式合并。每章还拥有自己的 artifact/contract fixture 和发布索引，公共模型只放在现有 `catalog/model.py`、`teaching/model.py`、`visualizations/contracts.py` 等共享模块。

替代方案：把 39 个主题追加到一个大文件。拒绝，因为后续新增或修正章节时会造成跨章节冲突，也不符合单独可修改的要求。

### 3. 语义先扩展，操作后落地

第 4–8 章的视觉语义使用受控关系和原语，而不是直接写 `CommandPlan`。计划扩展分为两类：

- 复用现有操作：`geometry.subspace_region`、`geometry.projection`、`geometry.staged_transform`、`geometry.transformed_grid`、`plane3d.upsert`、`curve.create`、`annotation.formula` 等；
- 新增受控操作：`geometry.subspace3d`（3D 线/面/仿射集）、`geometry.affine_solution`（特解/零空间/平移解集）、`geometry.constraint`（2D 直线/3D 平面约束）、`geometry.mapping_bundle`（域/核/像双空间）、`geometry.matrix_tableau`（矩阵阶段）、`geometry.least_squares`（数据/拟合/残差）、`geometry.basis_grid` 与 `geometry.coordinate_readout`（备用基和双向坐标）、`geometry.spectrum`（特征根标记）、`geometry.projection3d`（3D 正交投影）、`geometry.orthogonalization`（Gram–Schmidt 阶段）、`geometry.quadratic_level_set`（2D/3D 二次型等值集）。

每个新操作先加入 `SceneCommandService` 的 JSON schema 和验证，再加入 Qt/PyVista teaching controller；编译器只在对应的 `VisualContract` 通过后生成它。任何 unsupported relation 都返回主题 ID、关系名和能力缺口，不允许回退成普通向量。

### 4. 用静态 storyboard 表达推导步骤

高斯消元、基变换、相似变换、对角化、Gram–Schmidt、主轴变换采用既有 storyboard stage 模型。矩阵/tableau 或二次型等值线在每个 stage 有独立命名空间、标题、可见实体、强调关系和不变量；切换 stage 只改变展示状态，不重新调用模型或执行未经验证的新命令。

### 5. 对抽象空间采用“可见模型 + 边界说明”

线性空间、维数、秩-零化度和高维方程组不能直接画出任意 (n) 维对象。实现使用 (R^2/R^3) 的代表性模型，并在 artifact 中记录 `analogy_boundary`：图形证明的是该代表模型的结构，解释中明确不把 2D/3D 图形冒充一般 n 维对象。

### 6. 资源发布和运行时保持原子

所有 39 个主题先生成/审核/发布 artifact，再编译视觉语义快照。registry 解析 `topic_id` 时同时校验 source hash、artifact revision、VisualContract 和 compiled snapshot；任何一步失败都不提交场景或解释。第 4–8 章可以逐章发布，未发布章节不会污染前三章运行时索引。

## Capability gap matrix

| 缺口 | 受影响主题 | 方案 | 验证重点 |
| --- | --- | --- | --- |
| 3D 线/面/仿射子空间 | ch04、ch05 | `subspace3d`、仿射原点和维数标签 | 维数、原点/平移、边界 |
| 域/核/像双空间 | ch04 | `mapping_bundle` 和双空间布局 | 输入/输出实体闭合 |
| 线性约束交集 | ch05 | 约束线/面、交点/交线和解状态 | 唯一/无穷/无解 |
| 矩阵 tableau 阶段 | ch05 | `matrix_tableau` + 行操作 metadata | 阶段顺序和零空间不变 |
| 最小二乘 | ch05 | 数据点、拟合曲线、投影和残差 bundle | 残差正交、数值可复算 |
| 备用基/坐标读数 | ch04、ch06 | `basis_grid`/`coordinate_readout` | 双向坐标一致 |
| 特征根/谱 | ch07 | `spectrum` 和根标记 | 根与 Null(A-λI) 绑定 |
| Gram–Schmidt 正交化 | ch07 | `orthogonalization` stage bundle | 投影分量、残差和正交基闭合 |
| 3D 正交投影 | ch07 | `projection3d` | 垂足、残差和正交关系 |
| 二次型等值线/曲面 | ch08 | `quadratic_level_set` | 主轴、定性、退化和边界 |

## Risks / Trade-offs

- **[风险] 39 个主题的内容发布量大，来源锚点容易漂移。** → 每个 artifact 保存摘录 hash 和 heading occurrence；章节发布前运行 source coverage，源文变更时标记 `stale_source`。
- **[风险] 新操作增加 Qt/PyVista 适配复杂度。** → 先实现 schema/validator 和离线 plan replay，再接渲染；未接入 renderer 的操作不得发布。
- **[风险] 二次曲面和 3D 子空间在窄视口中重叠。** → 使用固定 RenderContext、布局槽位和边界检查，溢出时失败并保留旧场景。
- **[风险] 抽象 n 维概念被误解为低维结论。** → artifact 强制 `analogy_boundary` 和读图提示，验证器拒绝缺少边界说明的高维主题。
- **[风险] 与现有活动变更产生资源索引冲突。** → 只新增本变更前缀的章节文件和索引，运行时合并由单一 manifest 完成；不修改其他活动变更目录。

## Migration Plan

1. 先落地 drawing catalog、章节来源解析、模型和 delta specs，不改变运行时行为。
2. 增加第 4–8 章 catalog/树节点和空的发布索引，验证 93 个主题（54+39）的 ID、顺序和排除规则。
3. 按能力缺口实现新操作和 renderer，并为每个操作建立 golden plan 与失败 fixture。
4. 按第 4、5、6、7、8 章分别发布 artifact、contract 和 compiled snapshot；每章通过后再加入运行时索引。
5. 接入树选择、解释视图、storyboard 和搜索，执行全量测试、前端构建、讲义校验和手动逐章走查。

回滚策略：移除对应章节的 published index 条目即可隐藏第 4–8 章主题，前三章资源和旧 compiled snapshot 不变；renderer 新操作保留为未注册能力，不影响旧 `CommandPlan`。

## Open Questions

无。2D/3D 表示边界、39 个绘图主题和新增能力集合已经由 `drawing-catalog.md` 固定，后续只需在不改变契约的范围内实现。

## Deep Design Addendum

### 7. 语义名称与 CommandPlan 操作的分层

为避免“contract 名称”和“命令名称”在实现中漂移，采用两层固定词汇：

| 语义 primitive（artifact/contract 使用） | 主要 CommandPlan 操作（compiler 输出） | 说明 |
| --- | --- | --- |
| `subspace_family` | `geometry.subspace_region` 或 `geometry.subspace3d` | 2D 区域、3D 线/面/仿射集；必须带 dimension/origin/translation |
| `domain_image_map` | `geometry.mapping_bundle` | 域、核、像、输入/输出向量一次性布局；关系由 metadata 追踪 |
| `affine_solution_set` | `geometry.subspace_region`/`geometry.subspace3d` + `geometry.affine_solution` | 特解、零空间基、平移后的解集必须来自同一 payload |
| `constraint_intersection` | `geometry.constraint` + `geometry.intersection` | 约束线/面和交集状态不能由普通 curve 替代 |
| `elimination_tableau` | `geometry.matrix_tableau` | 增广矩阵、行操作、阶段和高亮行绑定 |
| `least_squares_bundle` | `geometry.least_squares` | 数据、拟合对象、投影点、残差和正交关系为一个 bundle |
| `basis_coordinate_map` | `geometry.basis_grid` + `geometry.coordinate_readout` | 两套基、同一几何向量和双向坐标变换 |
| `eigen_direction`/`spectral_roots` | `geometry.spectrum` | 特征根必须关联到 `Null(A-λI)` 或特征方向实体 |
| `orthogonalization_bundle` | `geometry.orthogonalization` | Gram–Schmidt 的投影分量、残差和正交基按 stage 展开 |
| `quadratic_level_set` | `geometry.quadratic_level_set` | 2D 等值线/3D 曲面、主轴和定性元数据统一入口 |

语义 primitive 是可审查的数学意图；CommandPlan 操作是受 `SceneCommandService` 验证的传输格式。编译器只允许表中映射，任何新 primitive 必须先补表、schema、renderer 和契约测试。

### 8. 运行时状态机与原子提交

主题加载固定为以下状态，不允许从 `selected` 直接写入画布：

```text
idle
  -> resolving(topic_id)
  -> source_checked
  -> artifact_checked
  -> contract_checked
  -> compiled
  -> plan_validated
  -> staged
  -> committed
```

任一状态失败都进入 `rejected`，并携带 `topic_id`、失败阶段、诊断代码和上一份 published revision。只有 `staged` 同时具备解释 payload、compiled plan、evidence ledger 和 renderer capability 时，才允许调用宿主事务的 `begin → execute → commit`；提交失败执行 `rollback`，旧场景和旧解释保持一致。

树节点点击规则：章/节只更新树状态；叶子只提交完整事务；搜索结果没有叶子时不触发 `resolving`。storyboard 切换只在 `committed` 场景内改变可见 alias 集合，不回到 `resolving`。

### 9. 稳定 payload 契约

新增高层操作统一采用以下外层字段：

```json
{
  "op": "geometry.<family>",
  "alias": "<topic_id>__<stage>__<semantic_id>",
  "dimension": 2,
  "claim_refs": ["claim.id"],
  "stage_id": "input",
  "role": "primary",
  "data": {}
}
```

通用规则：`dimension` 只能是 2 或 3；`claim_refs` 必须引用 artifact 中存在的 claim；所有坐标、系数、阈值必须是有限数字；数组长度、实体数量和 stage 数量受 render profile 限制；`alias` 不可含显示标题或随机后缀。

各 family 的最小 data 字段如下：

```json
{
  "geometry.mapping_bundle": {
    "domain_basis": [[1, 0], [0, 1]],
    "kernel_basis": [[1, -1]],
    "image_basis": [[1, 1]],
    "input_vectors": [[1, 1]],
    "output_vectors": [[2, 2]],
    "relations": [{"kind": "maps_to", "source": "u", "target": "Au"}]
  },
  "geometry.constraint": {
    "normal": [1, 2],
    "offset": 3,
    "constraint_id": "c1",
    "style": "solid"
  },
  "geometry.matrix_tableau": {
    "matrix": [[1, 2], [3, 4]],
    "rhs": [5, 6],
    "row_operation": {"kind": "swap|scale|eliminate", "source_rows": [0, 1], "factor": 1},
    "highlight_rows": [0]
  },
  "geometry.least_squares": {
    "data_points": [[0, 1], [1, 2]],
    "fit_kind": "line|plane",
    "fit_parameters": [1, 1],
    "projection_points": [[0, 1], [1, 2]],
    "residuals": [[0, 0], [0, 0]],
    "orthogonality_pairs": [["fit_direction", "residual"]]
  },
  "geometry.spectrum": {
    "matrix": [[2, 0], [0, 3]],
    "roots": [{"value": 2, "eigenspace_ref": "E2"}],
    "eigenspaces": [{"id": "E2", "basis": [[1, 0]]}]
  },
  "geometry.quadratic_level_set": {
    "matrix": [[3, 1], [1, 2]],
    "linear": [0, 0],
    "constant": -1,
    "level": 0,
    "classification": "positive_definite|indefinite|semidefinite|degenerate",
    "principal_axes": [[0.85065, 0.52573], [-0.52573, 0.85065]]
  }
}
```

示例字段是 schema 的最小集合，不是允许任意扩展的自由 JSON。实现中应使用 typed dataclass/validator，禁止把 `data` 原样传给 renderer。

### 10. 编译器流水线与证据闭合

`VisualSemanticsCompiler` 对第 4–8 章固定执行六步：

1. **结构校验**：topic、source hash、artifact revision、场景维度和 vocabulary。
2. **契约校验**：required claims、roles、relations、primitive、stage、invariant 和 distinguishable groups。
3. **数学校验**：矩阵/向量维度、秩与零化度、交集状态、投影正交、特征根绑定、二次型分类。
4. **族编译**：按 semantic primitive 调用唯一 family compiler，生成带 evidence 的高层操作。
5. **布局与资源预算**：分配固定 lane/slot，检查 bounds、实体数量、采样分辨率和 alias 冲突。
6. **命令回放校验**：高层操作展开为原子操作后，重新调用 `SceneCommandService.validate`，生成 plan digest 和 evidence ledger。

每一步都返回结构化 `CompileIssue`；禁止用“空图”“普通向量”或“忽略关系”作为 fallback。`_emit_declared_capability_evidence` 只可补充已有词汇允许的、可由实体值唯一推导的证据，不得为新场景族创造默认数据。

### 11. 渲染边界与数值政策

- 2D 线性约束只渲染有限 bounds 内的 clipped segment；3D 平面只渲染固定盒体内的 patch，不能无限创建 mesh。
- 交集计算采用 profile 的 `absolute_tolerance` 和 `relative_tolerance`；分类结果同时保留原始秩/残差，避免仅由像素判断。
- 特征根按实根优先；复根主题只能显示代数根和“无实方向”说明，不伪造实平面箭头。
- 二次型等值线先做特征分解和分类，再生成采样；采样失败时返回 `numeric_invalid`，不退回 `surface.create`。
- 主轴、特征方向和投影残差的颜色来自章节角色 palette，颜色不是数学关系的唯一证据；解释和 annotation 必须同时给出关系名称。
- 所有 renderer 适配器都必须提供离线 `replay(plan)`，Qt/PyVista 只是宿主，不负责推导数学数据。

### 12. 验证矩阵与发布门禁

每个主题至少覆盖以下四类 fixture：

| 层级 | 验证内容 | 失败示例 |
| --- | --- | --- |
| artifact | 来源 occurrence/hash、claim、变量和 analogy boundary | 讲义标题漂移、公式变量未定义 |
| contract | 语义关系、实体角色、stage 和 invariant | 有特解但没有零空间证据 |
| compiler | family op、alias、布局、数值不变量 | 无穷解被编译成唯一交点 |
| renderer/replay | 展开后的原子操作与截图/摘要 | 新 op 未注册、3D bounds 溢出 |

发布按章节设门禁：第 4 章通过后才加入 `chapter_04` index，随后依次是第 5、6、7、8 章。全量门禁要求 93 个主题（54 + 39）顺序稳定、旧主题 plan digest 不变、新主题的 source/artifact/contract/compiled digest 全部存在；任一章节失败只撤销该章节 published index。

### 13. 可观测性与诊断

发布报告至少记录：`topic_id`、chapter、scene family、source hash、artifact revision、contract digest、compiler version、plan digest、stage IDs、operation names、实体/采样计数和验证耗时。UI 只展示人类可读的错误摘要和修复提示，不暴露 scene op JSON；开发者诊断面板可通过 topic ID 查到完整 evidence ledger。
