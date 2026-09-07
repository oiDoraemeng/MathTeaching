## Purpose

保存数学解释子智能体生成的成对教学产物，使讲义来源、数学论断、视觉语义和树形主题绑定可审查、可回放、可回滚。

## ADDED Requirements

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

发布 SHALL 先写入临时版本并完成 schema、来源、数字算例、claims 和视觉语义校验，再原子替换索引。旧版本在新版本校验失败时 SHALL 保留并继续可读。

旧的基础 `ExplanationContent` 资源 MAY 通过适配器读取，但新主题不得缺少 `TeachingArtifact` 的 claims 和 `visual_semantics`。

#### Scenario: Failed publish keeps the previous version

- **WHEN** 新回复的数字例题、claim 引用或 source hash 校验失败
- **THEN** 发布命令返回具体字段错误
- **AND** 运行时仍读取上一个 published artifact

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
