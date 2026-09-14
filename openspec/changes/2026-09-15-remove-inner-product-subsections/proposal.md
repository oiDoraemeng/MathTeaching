## Why

第 1.3 节中的“两种定义等价性的证明”和“内积几何分层例题”已经不再作为独立教学主题展示。继续保留它们会让讲义来源、目录叶子、绘图配方和发布快照出现孤立条目，并增加启动时索引和校验负担。

## What Changes

- 从讲义来源中删除两段对应正文。
- 删除两个稳定 `topic_id` 的目录、解释、绘图、质量校验和本地生成注册。
- 删除对应的草稿、审核、复核、发布和 compiled 产物，并同步索引与主题摘要。
- 将全量目录基线从 90 个主题更新为 88 个主题，第 1 章从 21 个主题更新为 19 个主题。

## Impact

- 内容与运行时：`linear_algebra/catalog`、`linear_algebra/explanations`、`linear_algebra/visualizations`、`linear_algebra/teaching`。
- 发布数据：`linear_algebra/teaching/data` 下两个主题的全生命周期产物和索引。
- 验证：目录、来源、主题数量和快照覆盖测试。

## Non-goals

- 不修改历史 OpenSpec 归档或其他章节的数学内容。
- 不重生成与本次主题无关的教学快照。
