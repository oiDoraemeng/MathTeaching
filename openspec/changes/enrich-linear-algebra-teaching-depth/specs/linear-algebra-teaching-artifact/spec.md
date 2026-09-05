## ADDED Requirements

### Requirement: Persist the paired teaching artifact

软件 SHALL 将已发布的 `TeachingArtifact` 作为版本化 UTF-8 JSON 资源保存，至少包含 `topic_id`、讲义来源锚点、source hash、生成元数据、数学解释和视觉语义。运行时加载不得执行资源中的代码。

#### Scenario: Published agent response survives restart

- **WHEN** 软件重启并打开已发布主题
- **THEN** 可以从内置内容仓库读取与上次相同的解释和视觉语义
- **AND** 不需要重新调用子智能体

### Requirement: Atomic publish and backward compatibility

发布 SHALL 先写入临时文件并完成 schema、来源、数字算例和视觉语义校验，再原子替换对应版本。旧版本在新版本校验失败时 SHALL 保留并继续可读。

旧的基础 `ExplanationContent` 资源 MAY 通过适配器读取，但新主题不得缺少 `TeachingArtifact` 的 `visual_semantics`。

#### Scenario: Failed publish keeps the previous version

- **WHEN** 新回复的数字算例或 source hash 校验失败
- **THEN** 发布命令返回具体字段错误
- **AND** 运行时仍读取上一个 published artifact

### Requirement: Tree and artifact identity

树模型、artifact store 和 visualization registry SHALL 对同一个 `topic_id` 返回同一个主题。artifact 的 `source_anchor` 必须与 `LessonEntry.source_anchor` 精确匹配；`connections` 只能指向存在的 topic ID。

#### Scenario: Tree selection resolves one bundle

- **WHEN** 用户点击树叶
- **THEN** 系统能通过该 `topic_id` 唯一解析 explanation、visual semantics、visual contract 和 recipe
- **AND** 不通过标题相似度或搜索结果文本选择图形

### Requirement: Staleness is diagnosable

当讲义片段的 hash 与 artifact 不同，加载器 SHALL 返回 `stale_source` 状态并指出主题 ID、旧 hash 和当前 hash。默认策略 SHALL 阻止发布旧内容，但可继续查看上一个稳定版本和其图形。

#### Scenario: Stale source blocks publication

- **WHEN** 当前讲义片段 hash 与 draft 中记录的 hash 不同
- **THEN** 发布命令拒绝该 draft 并报告 `stale_source`
- **AND** 上一个 published artifact 仍可在树节点中查看
