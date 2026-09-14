# 线性代数课程目录

## REMOVED Requirements

### Requirement: 删除已撤下主题
系统 SHALL 不再注册或发布 `ch01.proof.method` 与 `ch01.high-dimensional.analogy`。

#### Scenario: 构建课程目录
- **WHEN** 系统构建线性代数目录
- **THEN** 目录、解释映射、绘图映射和发布索引均不包含这两个主题 ID

## MODIFIED Requirements

### Requirement: 讲义源与目录一致
系统 SHALL 让讲义源不再包含“1.5.1 基本方法”和“1.7 n维向量的几何直觉拓展”两个小节。

#### Scenario: 校验讲义来源
- **WHEN** 运行讲义来源校验
- **THEN** 已注册主题的来源锚点均能在源文件中找到，且两个已删除标题不存在

### Requirement: 保留相邻教学主题
系统 SHALL 保留 1.5 节的中位线、重心和平行四边形对角线三个主题，并保持它们的资源和 plan digest 不变。

#### Scenario: 加载相邻主题
- **WHEN** 用户选择任一保留的 1.5 主题
- **THEN** 解释和绘图仍可按原主题 ID 原子加载
