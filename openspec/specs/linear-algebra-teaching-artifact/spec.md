# linear-algebra-teaching-artifact Specification

## Purpose
保存数学解释子智能体生成的成对教学产物，使讲义来源、数学论断、视觉语义和树形主题绑定可审查、可回放、可回滚。

## Requirements

### Requirement: Persist the paired teaching artifact

软件 SHALL 将已发布的 `TeachingArtifact` 作为版本化 UTF-8 JSON 资源保存，至少包含 `topic_id`、讲义来源锚点、source hash、生成元数据、教学层级、数学解释、claims 和视觉语义。运行时加载不得执行资源中的代码。

#### Scenario: Published agent response survives restart

- **WHEN** 软件重启并打开已发布主题
- **THEN** 可以从内置内容仓库读取与上次相同的解释、claims 和视觉语义
- **AND** 不需要重新调用子智能体

### Requirement: Claim-first artifact identity

每个 `Claim` SHALL 有稳定 ID、学生可读论断、可选公式、来源引用和视觉证据引用。`TeachingArtifact` SHALL 通过 `artifact_digest` 唯一标识规范化内容，并通过 `topic_id`、revision 和 source hash 标识其主题版本。

#### Scenario: Artifact evidence is closed

- **WHEN** 产物引用不存在的 claim、实体、关系、阶段或 topic ID
- **THEN** artifact 校验失败并指出引用路径
- **AND** 该版本不能发布

### Requirement: Draft, reviewed, and published states

产物 SHALL 区分 `draft`、`reviewed` 和 `published`。draft 可以显示校验错误和审核信息，但运行时内容仓库只能读取 published。reviewed SHALL 记录审核结论和审核时间。

#### Scenario: Draft is not runtime content

- **WHEN** 子智能体返回合法 JSON 但尚未完成审核
- **THEN** 系统保存为 draft
- **AND** 树节点和运行时解释视图不得读取该 draft

### Requirement: Preserve accepted raw reply for audit

通过安全和结构校验的子智能体原始 JSON SHALL 被精确保存，并与规范化 artifact digest 关联。发布资源可以只引用审计记录，但审计记录必须能够恢复原始回复。被拒绝回复只保留 digest、错误代码和有界诊断。

#### Scenario: Raw reply and normalized artifact are comparable

- **WHEN** 审核者查看一个 published revision
- **THEN** 可以定位对应的原始子智能体回复和规范化字段
- **AND** 场景编译只使用规范化视觉语义

### Requirement: Atomic publish and backward compatibility

发布 SHALL 先完成 schema、来源、数字算例、claims、视觉 contract 和编译器校验，再写入版本化 draft、reviewed、published 与编译快照，并在最后原子替换 `index.json` 中当前主题的发布指针。运行时在索引存在时 SHALL 只读取索引指向的 published revision，不得按目录最大 revision 猜测已发布版本。旧版本在新版本校验、落盘或索引切换失败时 SHALL 保留并继续可读。

旧的基础 `ExplanationContent` 资源 MAY 通过适配器读取，但新主题不得缺少 `TeachingArtifact` 的 claims 和 `visual_semantics`。

#### Scenario: Failed publish keeps the previous version

- **WHEN** 新内容的数字例题、claim 引用、source hash、视觉 contract 或编译校验失败
- **THEN** 增量发布返回具体字段错误且不切换索引
- **AND** 运行时仍读取上一个 indexed published artifact

#### Scenario: Unindexed revision is not runtime content

- **WHEN** published 目录存在大于索引 revision 的中间文件
- **THEN** 运行时仍只读取索引 revision
- **AND** 中间文件不会因文件名较新而自动生效

### Requirement: Tree and artifact identity

树模型、artifact store、visual contract 和 visualization registry SHALL 对同一个 `topic_id` 返回同一个主题。artifact 的 source anchor 必须与 `LessonEntry.source_anchor` 精确匹配；connections 和 claim references 只能指向存在的 ID。

#### Scenario: Tree selection resolves one bundle

- **WHEN** 用户点击树叶
- **THEN** 系统能通过该 `topic_id` 唯一解析 explanation、claims、visual semantics、visual contract 和 recipe
- **AND** 不通过标题相似度或搜索结果文本选择图形

### Requirement: Staleness is diagnosable

当讲义片段的 hash 与 artifact 不同，加载器 SHALL 返回 `stale_source` 状态并指出主题 ID、旧 hash 和当前 hash。默认策略 SHALL 阻止发布旧内容，但可继续查看上一个稳定版本和其图形。

#### Scenario: Stale source blocks publication

- **WHEN** 当前讲义片段 hash 与 draft 中记录的 hash 不同
- **THEN** 发布命令拒绝该 draft 并报告 `stale_source`
- **AND** 上一个 published artifact 仍可在树节点中查看

### Requirement: Deterministic compiled snapshot

published artifact SHALL 记录编译器版本、渲染 profile、compiled plan digest 和生成该 digest 的 source/artifact digest。运行时可以复用匹配的编译快照；版本不匹配时必须重新编译而不是静默使用旧计划。

#### Scenario: Compiler version invalidates a snapshot

- **WHEN** 当前编译器版本或渲染 profile 与 published 记录不一致
- **THEN** 系统重新编译视觉语义并重新验证计划
- **AND** 不调用子智能体、不读取 raw reply 作为绘图输入

### Requirement: Incremental trusted authoring materialization

源码 checkout 中的正式应用 SHALL 在解析当前主题 bundle 前应用可信本地质量适配器。系统 SHALL 通过规范化 artifact digest 判断该主题是否变化；未变化时不得创建 revision 或改写索引，变化时只处理当前主题，不批量扫描其他主题。新内容仍须经过完整发布门禁，运行时不得直接读取 draft 或未校验 payload。

#### Scenario: A punctuation edit materializes on the next topic load

- **WHEN** 开发者只修改 `quality.py` 中当前主题的一处有效文字并重启应用
- **THEN** 打开或恢复该主题时只生成它的下一个正式 revision
- **AND** bundle 直接读取新 indexed revision，不需要重建全部章节

#### Scenario: Unchanged topic performs no writes

- **WHEN** 质量适配器输出与当前 indexed artifact 的规范化内容相同
- **THEN** 同步返回 `unchanged`
- **AND** draft、reviewed、published、snapshot、audit 和 index 均不产生写入
