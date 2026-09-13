## Purpose

定义第 4 至第 8 章的讲义来源、几何绘图筛选和主题资源覆盖，确保新增章节不是只有树节点，而是每个几何主题都有可审查的解释、视觉契约和可回放计划。

## ADDED Requirements

### Requirement: Chapters four through eight lecture catalog

线性代数讲义树 SHALL 在保留第 1 至第 3 章主题的基础上增加第 4 至第 8 章。每个主题 SHALL 使用稳定的 `topic_id`、章节号、小节号、完整讲义路径、来源锚点、解释资源 ID 和可视化资源 ID；主题顺序 SHALL 与 `.agents/线性代数讲义.md` 一致。

#### Scenario: Catalog preserves lecture order

- **WHEN** 系统构建线性代数讲义树
- **THEN** 第 4 章至第 8 章按讲义顺序出现在第 3 章之后
- **AND** 每个主题的完整路径和来源锚点可以反查到讲义原文
- **AND** 练习、自检、挑战和章节小结不被错误注册为主题叶子

### Requirement: Drawing catalog is source-grounded

系统 SHALL 保存第 4 至第 8 章的绘图目录，逐项记录主题 ID、讲义目录、要证明的几何关系、复用的现有能力和新增能力缺口。绘图目录 SHALL 包含 39 个主题，按章节计数为 16/8/3/6/6；不满足几何筛选规则的目录 SHALL 明确记录为“仅解释”或被排除。

#### Scenario: Drawing coverage is auditable

- **WHEN** 运行绘图目录校验
- **THEN** 39 个绘图主题全部有有效讲义来源锚点和唯一 topic ID
- **AND** 每个绘图主题至少声明一个视觉关系和一个预期 plan 原语
- **AND** 被排除的纯证明、练习和自检条目不会出现在绘图主题索引中

### Requirement: Extended topic bundle is atomic

第 4 至第 8 章的每个绘图主题 SHALL 同时提供来源上下文、结构化数学解释、数字例题（适用时）、视觉语义、视觉契约和已验证的 `CommandPlan`。用户选择主题时，任一资源缺失、来源哈希过期、契约不满足或计划执行失败 SHALL 保留当前场景与解释，不得加载半套主题。

#### Scenario: Load a chapter-eight topic

- **WHEN** 用户选择“8.3 主轴定理”
- **THEN** 系统显示讲义来源、主轴解释和歪椭圆到主轴坐标的阶段图
- **AND** 解释中的特征值、特征向量和图中主轴对象可通过同一 topic ID 关联

#### Scenario: Reject incomplete extended topic

- **WHEN** 第 4 至第 8 章主题缺少视觉契约、来源锚点或实际 plan 原语
- **THEN** 发布/验证失败并指出章节、topic ID 和缺失字段
- **AND** 运行时继续保留上一个 published revision

### Requirement: Chapter resources are independently maintainable

第 4 至第 8 章的目录、解释、视觉契约、builders/semantic fixtures 和已发布 artifact SHALL 按章节与主题 ID 分模块保存。新增或修改单个主题不得要求修改其他章节的解释或绘图资源；章节级索引 SHALL 只引用这些模块的稳定 ID。

#### Scenario: Update one topic without cross-chapter coupling

- **WHEN** 开发者修改 `ch08.principal-axis` 的解释或绘图配方
- **THEN** 只需更新第 8 章对应模块、资源索引和该主题测试
- **AND** 第 1 至第 7 章主题的 topic ID、artifact digest 和 plan digest 不发生无关变化

### Requirement: Chapter tree interaction remains consistent

扩展后的目录 SHALL 继续使用现有的搜索、展开全部、折叠和叶子选择交互。默认打开时 SHALL 展开第 1 至第 8 章节点及其第二级小节；主题叶子默认折叠。搜索、分支选择和叶子加载的行为 SHALL 与前三章一致。

#### Scenario: Search and select a chapter-eight topic

- **WHEN** 用户输入“主轴定理”并选择匹配的第 8 章主题叶子
- **THEN** 树只保留第 8 章及其匹配小节/叶子并自动展开祖先路径
- **AND** 主题加载使用 `ch08.principal-axis`，不会因为标题相似而加载第 7 章特征值主题
