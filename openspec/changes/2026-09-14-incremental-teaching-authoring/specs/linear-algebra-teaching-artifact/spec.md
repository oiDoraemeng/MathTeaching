## MODIFIED Requirements

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

## ADDED Requirements

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
