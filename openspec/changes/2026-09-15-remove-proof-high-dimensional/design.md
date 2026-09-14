# 设计

## 主题边界

删除以下稳定主题及其所有派生资源：

- `ch01.proof.method`
- `ch01.high-dimensional.analogy`

保留同属 1.5 的三个几何证明主题，并保留 1.6 高维预览中仍属于讲义主线的内容；删除源文件中完整的 1.7 标题块至“本章练习”之前。

## 资源链路

1. 从 `.agents/线性代数讲义.md` 删除两个小节正文。
2. 从 catalog、explanation、teaching profile、quality adapter、chapter builder 和 compiler 特殊分支删除主题注册。
3. 从 draft/review/audit/published/compiled 目录删除两个主题的精确 revision 文件夹和 JSON 文件。
4. 从 `index.json` 和 `topic-digests.json` 删除主题记录，更新总数。
5. 更新计数、稳定主题摘要和“已删除主题不得存在”的回归测试。

## 一致性约束

运行时 `topic_entries()`、解释映射、builder 映射和发布索引均不得返回这两个 ID。源讲义不得包含 `1.5.1 基本方法` 或 `1.7 n维向量的几何直觉拓展` 标题。其余主题的 plan digest 保持不变。
