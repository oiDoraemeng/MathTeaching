## MODIFIED Requirements

### Requirement: Current lecture topic set

线性代数当前目录 SHALL 只注册仍在讲义来源和发布索引中的主题；已删除的主题不得被运行时解释、绘图或质量注册再次解析。

#### Scenario: Removed inner-product subsections are absent

- **WHEN** 系统构建线性代数目录、解释表和绘图表
- **THEN** `ch01.inner.equivalence` 与 `ch01.inner.examples` 均不存在
- **AND** 第 1 章包含 19 个主题，总目录包含 88 个主题
- **AND** 当前发布索引、compiled 快照和生命周期产物中不再有这两个主题

#### Scenario: Remaining inner-product topics still load

- **WHEN** 用户选择“1.3.1 内积的两种定义”、“1.3.2 内积的三条核心应用”或“1.3.3 柯西-施瓦茨不等式”
- **THEN** 对应主题仍通过稳定 `topic_id` 加载解释和绘图
- **AND** 删除的两个主题不会作为隐式回退被加载
