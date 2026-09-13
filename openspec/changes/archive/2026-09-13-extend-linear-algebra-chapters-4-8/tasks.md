## 0. 设计固化与实现前门禁

- [x] 0.1 固化 semantic primitive 与 CommandPlan 操作的显式映射，建立受控字段 schema、dimension/数量上限和 alias 命名规则；禁止实现阶段新增未登记的自由操作
- [x] 0.2 为五个场景族建立最小 fixture 矩阵（正常、边界、失败各一组），覆盖子空间/解集、约束/消元、双坐标、谱/正交、二次型主轴
- [x] 0.3 实现 `idle → resolving → source_checked → artifact_checked → contract_checked → compiled → plan_validated → staged → committed/rejected` 状态转移的测试夹具和错误码表
- [x] 0.4 为 2D/3D render profile 固化实体数、stage 数、隐式采样分辨率、tolerance、bounds 和布局槽位，超限必须在发布前失败
- [x] 0.5 为每章准备至少一个端到端验收主题和回滚 fixture，确认章节索引可独立发布/撤回且前三章 digest 不变

## 1. 来源解析与绘图目录

- [x] 1.1 扩展讲义来源读取器，支持第 4–8 章不规则标题层级、重复 occurrence 和相邻上下文，并验证练习/自检/挑战排除规则
- [x] 1.2 将 `drawing-catalog.md` 转为可校验的章节绘图索引，验证 39 个主题按 16/8/3/6/6 分布且无重复 topic ID
- [x] 1.3 扩展 `LessonEntry`/`LessonNode` 与 manifest，注册第 4–8 章完整路径、来源锚点和章节独立模块，并验证 54+39 个主题顺序稳定
- [x] 1.4 更新讲义树搜索索引和默认展开行为，验证“主轴定理”“高斯消元”等关键词保留正确祖先且分支节点不触发加载

## 2. 教学产物与章节资源模型

- [x] 2.1 扩展教学 profile、source context 和 artifact schema，支持第 4–8 章的 `analogy_boundary`、视觉主张和新关系白名单
- [x] 2.2 为第 4–8 章新增 explanation 模块，按章节维护定义、公式、推导、数字例题、几何意义、误解和读图提示，并验证向量/矩阵 LaTeX 约束
- [x] 2.3 扩展 artifact store、published index 和 compiled snapshot 索引，支持按章节独立发布、stale source 检测和单主题回滚
- [x] 2.4 为 39 个主题生成并审核 teaching artifact fixture，验证每个 claim、公式变量、视觉实体、关系和阶段引用闭合

## 3. 视觉语义与新 CommandPlan 能力

- [x] 3.1 扩展视觉词汇、VisualContract 和编译器关系映射，加入 `subspace_family`、`domain_image_map`、`affine_solution_set`、`constraint_intersection`、`basis_coordinate_map`、`eigen_direction`、`orthogonalization_bundle` 和 `quadratic_level_set`
- [x] 3.2 实现 3D 线/面/仿射子空间和域/核/像双空间布局，验证子空间维数、原点约束、平移和布局边界
- [x] 3.3 实现线性约束线/面、交点/交线和唯一/无穷/无解状态，验证方程组几何与数值解一致
- [x] 3.4 实现 `geometry.matrix_tableau` 和 `elimination_tableau` storyboard，支持增广矩阵、行操作标签、阶段高亮和零空间不变性说明
- [x] 3.5 实现 `geometry.least_squares`、`basis_grid` 和双向坐标映射，验证拟合残差正交、标准基/备用基坐标可逆
- [x] 3.6 实现特征值谱/根标记、3D 正交投影和 Gram–Schmidt 阶段，验证特征根与特征空间、垂足/残差、正交关系闭合
- [x] 3.7 实现 `geometry.quadratic_level_set` 的 2D 等值线与 3D 二次曲面，支持主轴、正定/不定/半正定/退化元数据并验证边界和确定性布局
- [x] 3.8 将所有新操作加入 `SceneCommandService` schema、Qt/PyVista teaching controller 和 plan replay；未知字段、非有限数值、越界和未知角色必须明确失败

## 4. 第 4–8 章主题实现

- [x] 4.1 实现第 4 章 16 个主题的 catalog、explanation、VisualContract、builder 和 published snapshot，验证子空间/秩/核像/线性变换主张落到实际 op
- [x] 4.2 实现第 5 章 8 个主题的 catalog、explanation、VisualContract、builder 和 published snapshot，验证解集、交集、消元和最小二乘主张落到实际 op
- [x] 4.3 实现第 6 章 3 个主题的 catalog、explanation、VisualContract、builder 和 published snapshot，验证双坐标和 (P^{-1}AP) 三阶段路径
- [x] 4.4 实现第 7 章 6 个主题的 catalog、explanation、VisualContract、builder 和 published snapshot，验证特征方向、谱、对角化、正交化和正交变换
- [x] 4.5 实现第 8 章 6 个主题的 catalog、explanation、VisualContract、builder 和 published snapshot，验证等值线、主轴、定性、配方法和惯性证据

## 5. 树形运行时与展示

- [x] 5.1 扩展 registry 和原子主题加载事务，验证第 4–8 章主题的 artifact/contract/recipe/snapshot 一一对应，失败时旧场景和旧解释保持不变
- [x] 5.2 扩展 Qt 解释视图和 Web `math_case` payload，展示章节来源、视觉 claim、符号角色、读图提示和 analogy boundary，不暴露 scene op
- [x] 5.3 接入矩阵 tableau、双空间、主轴和二次曲面 storyboard 导航，验证切换阶段不调用模型、不新增标签、不修改 Agent 会话
- [x] 5.4 保持前三章工具栏和案例行为不变，验证打开第 4–8 章主题不会创建第二个工具栏或改变当前工具栏布局

## 6. 校验、回归与交付

- [x] 6.1 扩展 `linear_algebra.validation`，验证 93 个主题、章节计数、来源 hash、artifact revision、视觉契约和发布状态
- [x] 6.2 增加“声明能力 ⇒ 实际 plan op”“解释变量 ⇒ 视觉实体”“关系 ⇒ claim/contract”一致性校验，覆盖每个新增能力缺口
- [x] 6.3 增加章节级单元/集成/Qt/Web 测试，覆盖矩阵 tableau、约束交集、最小二乘、谱、3D 投影和二次型等值线 golden fixtures
- [ ] 6.4 运行 OpenSpec 严格校验、讲义校验、完整 Python 测试、前端测试和构建；保存 93 主题覆盖、能力映射和 plan digest 报告
- [ ] 6.5 手动逐章走查第 4–8 章树形选择、解释分层、图形阶段、失败回退和搜索；为每章至少一个重点主题保存截图和 artifact/source/compiler 版本记录

## 7. 执行依赖与并行边界

- 0.1–0.5 是所有实现任务的前置门禁；未完成时不得生成第 4–8 章 published snapshot。
- 1.x 与 2.x 可以分别在来源解析和 artifact schema 稳定后并行准备，但 4.x 必须等待 1.2、2.4 和 3.1。
- 3.2–3.7 按场景族实现；每个场景族必须先通过离线 `SceneCommandService.validate` 和 plan replay，才允许接入 Qt/PyVista。
- 4.1–4.5 按章节发布；章节内部主题可以并行制作，但 published index 只能在该章所有主题和失败 fixture 通过后更新。
- 5.x 只能消费已发布 snapshot，不得在 UI 层绕过 registry 直接调用 builder；6.x 是最终交付门禁。
