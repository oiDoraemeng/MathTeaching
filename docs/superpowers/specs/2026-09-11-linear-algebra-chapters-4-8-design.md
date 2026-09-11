# 第 4–8 章线性代数几何讲义扩展设计

> 状态：待用户审阅
>
> 对应 OpenSpec：`openspec/changes/extend-linear-algebra-chapters-4-8/`
>
> 来源：`D:\github\Math3DTeaching\.agents\线性代数讲义.md` 第 4–8 章

## 1. 目标与范围

将讲义第 4–8 章中需要几何表示的内容接入现有线性代数讲义树、教学产物、视觉契约、编译器和场景命令链路。绘图目录固定为 39 个主题：第 4 章 16 个、第 5 章 8 个、第 6 章 3 个、第 7 章 6 个、第 8 章 6 个。练习、自检、挑战、章节小结和只有符号推导的内容不注册为绘图叶子。

本设计只扩展第 4–8 章，保留第 1–3 章的 topic ID、解释、已发布 revision、plan digest 和工具栏行为。每一章的 catalog、explanation、visualization、builder、artifact fixture、contract fixture 和 published index 独立维护，修改单个主题不重写其他章节资源。

### 非目标

- 不修改 `.agents/线性代数讲义.md` 原文。
- 不保留或迁移旧案例模型；第 4–8 章使用新的讲义主题 ID 和现有 registry 链路。
- 不增加自由格式“输入任意方程并执行”的接口。
- 不增加连续动画、运行时模型生成场景操作或绕过契约的模板 renderer。
- 不改变前三章的工具栏位置、树交互和现有主题行为。

## 2. 用户可见结果

点击“线性代数”后，树显示第 1–8 章；八个章节点和第二级小节默认展开，主题叶子默认折叠。搜索按主题名、摘要、公式和完整讲义路径过滤，并保留匹配叶子的祖先路径。只有主题叶子加载数学解释和图形；章/节节点只改变展开状态。

选择第 4–8 章叶子时，内容视图使用一个 `topic_id` 同时解析：

```text
讲义来源锚点
  → published TeachingArtifact
  → VisualContract
  → VisualSemanticsCompiler
  → validated CommandPlan
  → renderer adapter
```

任一环节失败，画布和当前解释保持不变，并显示包含主题 ID、失败阶段和可修复字段的错误摘要。

## 3. 场景族设计

39 个主题不各自设计一套绘图算法，而是归并为五个可测试的场景族：

| 场景族 | 主题范围 | 最小视觉证据 | 必须区分 |
| --- | --- | --- | --- |
| `subspace_structure` | Ch4 的 span、子空间、维数、秩、核/像；Ch5 齐次解 | 生成向量、包含关系、原点/维数、核和像 | 子空间与仿射集；独立与冗余 |
| `constraint_solution` | Ch5 非齐次解、交集、消元、最小二乘 | 约束线/面、交集或残差、增广矩阵阶段 | 唯一解、无解、无穷解；精确解与拟合 |
| `basis_coordinate` | Ch4 坐标读数；Ch6 换基和相似变换 | 两套基、同一几何向量的双坐标、前后矩阵 | 几何向量不变与坐标数字改变 |
| `spectral_orthogonal` | Ch7 特征方向、谱、对角化、Gram–Schmidt | 特征方向/空间、根绑定、投影分量、正交基 | 特征方向与任意方向；正交与非正交 |
| `quadratic_shape` | Ch8 等值线、主轴、定性、配方法、合同惯性 | 原坐标等值线、主轴、标准形、签名/退化标记 | 椭圆、双曲型、半正定、退化 |

一个主题可以有一个主场景族和一个辅助场景族，但组合必须写入该主题的 `VisualContract`，不得按标题或关键词推断。

## 4. 模块边界

```text
linear_algebra/
├─ catalog/
│  ├─ chapter_04.py ... chapter_08.py       # 章节主题和来源锚点
│  └─ manifest.py                            # 按章节合并，保持稳定顺序
├─ explanations/
│  ├─ chapter_04.py ... chapter_08.py        # 结构化数学解释
├─ visualizations/
│  ├─ chapter_04.py ... chapter_08.py        # recipe 元数据
│  └─ builders/
│     ├─ chapter_04.py ... chapter_08.py     # 主题 fixture/semantic graph
│     └─ families/                            # 五类场景族编译器
├─ teaching/
│  ├─ data/compiled/ch04 ... ch08             # published artifact/snapshot
│  └─ source.py/store.py                      # 来源和原子加载
├─ visualizations/
│  ├─ contracts.py                             # topic contract
│  ├─ compiler.py                              # semantic graph → plan
│  └─ snapshots.py                             # revision/source/plan digest
└─ validation.py                               # 章节和能力覆盖校验
```

公共模型继续放在现有 `catalog/model.py`、`teaching/model.py`、`visualizations/common.py` 和 `visualizations/contracts.py`。章节模块不得导入 PySide6、PyVista、主窗口或场景宿主。UI 只依赖 registry/service，不直接导入章节 builder。

## 5. 语义层与命令层

artifact/contract 使用稳定的语义 primitive；compiler 再把它们映射到受控 CommandPlan 操作：

| semantic primitive | CommandPlan 操作 | 约束 |
| --- | --- | --- |
| `subspace_family` | `geometry.subspace_region` / `geometry.subspace3d` | 必须声明维数、原点、生成方向和是否平移 |
| `domain_image_map` | `geometry.mapping_bundle` | 域、核、像、输入/输出实体一次性闭合 |
| `affine_solution_set` | `geometry.affine_solution` + 子空间操作 | 特解、零空间基和平移解集来自同一 payload |
| `constraint_intersection` | `geometry.constraint` + `geometry.intersection` | 必须声明约束和唯一/无解/无穷状态 |
| `elimination_tableau` | `geometry.matrix_tableau` | 增广矩阵、行操作、阶段和高亮行绑定 |
| `least_squares_bundle` | `geometry.least_squares` | 数据、拟合对象、投影点、残差和正交关系成组 |
| `basis_coordinate_map` | `geometry.basis_grid` + `geometry.coordinate_readout` | 同一几何向量的两套坐标可逆 |
| `eigen_direction` / `spectral_roots` | `geometry.spectrum` | 根必须绑定到特征空间或特征方向 |
| `orthogonalization_bundle` | `geometry.orthogonalization` | 投影分量、残差、正交基按阶段出现 |
| `quadratic_level_set` | `geometry.quadratic_level_set` | 等值线/曲面、主轴和定性来自同一矩阵 |

高层操作不是绕过命令服务的后门。每个操作必须先通过 typed payload validator，再展开为现有原子操作，最后重新调用 `SceneCommandService.validate()`。未知字段、未知角色、非有限数字、维度不匹配和越界都必须失败。

### 5.1 通用 payload

```json
{
  "op": "geometry.<family>",
  "alias": "<topic_id>__<stage_id>__<semantic_id>",
  "dimension": 2,
  "claim_refs": ["claim.id"],
  "stage_id": "input",
  "role": "primary",
  "data": {}
}
```

通用约束：`dimension` 只能为 2 或 3；`claim_refs` 必须引用 artifact 中的 claim；坐标、矩阵系数、level 和 tolerance 必须为有限数字；alias 不能由显示标题或随机后缀生成；单主题的实体、stage 和采样数量受 render profile 限制。

### 5.2 场景族接口

每个族提供相同的边界接口，内部可以使用不同的数值算法：

```python
class SceneFamilyCompiler(Protocol):
    family: str

    def validate(self, payload: Mapping[str, object], context: RenderContext) -> tuple[CompileIssue, ...]: ...

    def compile(
        self,
        payload: Mapping[str, object],
        context: RenderContext,
    ) -> FamilyCompileResult: ...
```

`FamilyCompileResult` 至少包含展开后的 operations、semantic-to-alias 映射、阶段可见集合和数学校验结果。family compiler 不接触 Qt/PyVista，不修改场景。

## 6. TeachingArtifact、Contract 和 Compiler

每个主题的 artifact 必须提供：

- `SourceRecord`：完整讲义路径、heading occurrence、source hash；
- claims：定义、公式、几何意义和结论；
- explanation：标题、摘要、公式、推导步骤、数值例题、读图提示和 `analogy_boundary`；
- `VisualSemantics`：`VisualEntity`、`VisualRelation` 和静态 `VisualStage`；
- generation/revision：artifact revision、schema version、生成摘要；
- 发布状态：只有 `published` artifact 可以生成 compiled snapshot。

每个 `VisualContract` 至少声明：`required_claims`、`required_entity_roles`、`required_relations`、`required_primitives`、最小 stage 数、不变量和必须区分的 role group。39 个主题逐项验证 contract 与最终 plan 的一致性。

`VisualSemanticsCompiler.compile()` 固定执行：

1. 检查 topic、source、artifact、scene dimension 和 vocabulary。
2. 检查 contract 的 claims、roles、relations、primitives、stages 和 invariants。
3. 执行矩阵/向量维度、秩、交集、正交、谱根和二次型分类校验。
4. 调用唯一的 scene-family compiler 生成高层操作。
5. 分配固定 layout lane/slot，检查 bounds、实体数量、采样分辨率和 alias 冲突。
6. 展开高层操作并调用 `SceneCommandService.validate()`，生成 plan digest 和 evidence ledger。

失败时抛出包含 `topic_id`、stage、family、字段路径和错误码的 `VisualCompileError`；不得用空图、普通向量或忽略关系作为 fallback。

## 7. Storyboard 与运行时状态机

消元、换基、相似变换、对角化、Gram–Schmidt 和主轴变换使用静态 storyboard。每个 stage 声明标题、说明、可见实体、强调关系、不变量和布局槽位；同一数学实体跨 stage 使用稳定 semantic ID/alias。

主题加载使用以下状态机：

```text
idle
  → resolving(topic_id)
  → source_checked
  → artifact_checked
  → contract_checked
  → compiled
  → plan_validated
  → staged
  → committed
```

任一阶段失败进入 `rejected`，保留上一份 published revision、当前画布和当前解释。只有解释 payload、compiled plan、evidence ledger 和目标 renderer capability 全部存在时，才执行宿主事务的 `begin → apply → commit`；执行失败走 `rollback`。

storyboard 切换只更新已提交场景中的可见 alias 集合，不重新调用模型、不生成新命令、不改变 artifact 或 claim。

## 8. 低维模型、渲染和数值边界

抽象的 (n) 维空间使用 (R^2/R^3) 代表模型，并在 artifact 中强制记录 `analogy_boundary`。图形只能证明代表模型中的结构，解释必须明确一般维数结论不是由像素直接证明。

渲染边界如下：

- 2D 约束线只绘制当前 bounds 内的 clipped segment；3D 平面只绘制固定盒体内 patch。
- 单主题最多 48 个 2D 实体、32 个 3D 实体和 6 个 storyboard stage。
- 二次型默认采样不超过 (128×128)，3D 曲面默认不超过 (64×64×64)。
- 所有随机样例使用 `RenderContext.seed`；相同 artifact/profile 必须产生相同坐标、alias、stage 顺序和颜色角色。
- 交集、正交和二次型分类使用 profile 的 absolute/relative tolerance，并保存数值证据，不能靠截图分类。
- 复特征根只显示代数根和“无实特征方向”说明，不伪造实平面箭头。
- 二次型必须先分类和主轴分解，再采样；采样失败返回 `numeric_invalid`，不降级为普通 `surface.create`。

## 9. UI 与发布

`catalog_registry()` 是唯一主题解析入口。registry 将 `LessonEntry`、解释、recipe、contract、artifact、compiled snapshot 和 source diagnostic 组成 `CurriculumBundle`。UI 不读取 scene op JSON，只读取 bundle 中的解释、阶段摘要、读图提示和错误摘要。

第 4–8 章按章节发布：

1. 先验证该章来源 coverage、主题顺序和排除规则。
2. 再发布 artifact、contract 和 compiled snapshot。
3. 该章全部主题和失败 fixture 通过后，才加入该章 published index。
4. 任一章失败时只移除该章 index，前三章索引和 snapshot 保持不变。

发布快照记录 `topic_id`、artifact revision、source hash、compiler version、render profile、plan digest、stage IDs、required roles、relations 和 invariants。运行时发现 digest 或 source 不匹配时拒绝加载旧快照。

## 10. 测试和验收

每个场景族至少有正常、边界和失败 fixture；每个章节至少有一个端到端验收主题：

| 层级 | 验证内容 | 典型失败 |
| --- | --- | --- |
| 来源/目录 | occurrence、hash、章节顺序、39 个主题计数 | 标题漂移、练习误注册 |
| artifact | claim、公式变量、实体和 analogy boundary 闭合 | 公式变量未定义 |
| contract | roles、relations、primitive、stage、invariant | 有特解但没有零空间证据 |
| compiler | family op、数值不变量、layout、alias 和 digest | 无穷解被画成唯一交点 |
| command/replay | 高层操作展开后的白名单和场景范围 | 新 op 未注册、2D/3D 越界 |
| UI/回归 | 搜索、展开/折叠、叶子原子加载、失败回退 | 章节点误触发加载 |

必须运行：

```text
openspec validate extend-linear-algebra-chapters-4-8 --strict
openspec validate --all
完整 Python 测试
前端测试和构建
第 4–8 章 source/artifact/compiler/replay 验收矩阵
```

交付报告记录 93 个主题（前三章 54 + 新增 39）的顺序、覆盖、source/artifact/contract/compiled digest 和章节发布状态。前三章旧 plan digest 的变化必须为零；若发生无关变化，发布门禁失败。

## 11. 方案取舍

### 方案 A：39 个独立 builder

实现直接，但会复制消元、坐标变换、投影和主轴算法，导致同一关系在不同主题中产生不一致的 alias、颜色和数值误差。拒绝。

### 方案 B：通用公式画图器

接口少，但会引入自由表达式执行，无法可靠表达解集状态、谱根绑定和二次型分类。拒绝。

### 方案 C：场景族 compiler + 主题 fixture

共同数学关系只实现一次，主题仍能独立修改来源、解释、数字例题、contract 和 stage。选择方案 C。

## 12. 设计自检结果

- 设计中没有未决事项、模糊占位或依赖人工猜测的实现步骤。
- 每个新 semantic primitive 都有对应 CommandPlan 操作、validator、renderer 边界和测试层级。
- 高维表示、发布快照和旧章节兼容边界已明确。
- 本文是 Superpowers 设计产物；OpenSpec 的 proposal、spec、design、tasks 和 drawing catalog 继续作为需求与追踪来源。
