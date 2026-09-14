## 方案

以稳定 `topic_id` 为删除边界，沿“来源 → 目录 → 解释/绘图 → 质量与生成注册 → 发布索引/产物 → 测试”的链路同步清理。运行时不保留隐藏回退主题，避免目录已经删除但 registry 或 artifact store 仍能解析旧 ID。

索引文件只移除目标主题对象，并保留工作区中其他尚未发布的教学修订。历史归档文件保持不变，用于审计和回溯。

## 一致性约束

- `ch01.inner.equivalence` 和 `ch01.inner.examples` 不得出现在当前 catalog、CONTENT、BUILDERS、quality maps、生成 spec、索引或当前数据产物中。
- 目录总数为 88，第 1 章为 19；章节 2–8 的数量保持不变。
- 删除后来源解析、目录唯一性和索引 JSON 仍须通过测试。
