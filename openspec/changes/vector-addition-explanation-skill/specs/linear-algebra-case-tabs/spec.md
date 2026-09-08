## MODIFIED Requirements

### Requirement: Static storyboard navigation

案例页 SHALL 支持按顺序浏览阶段快照、并排比较或叠加视图，并支持向量加法的一到四个独立二维案例窗格。切换阶段或窗格 SHALL 只改变已发布 bundle 的展示状态，不调用子智能体、不生成任意命令，也不改变树节点身份。

#### Scenario: Compare vector addition cases

- **WHEN** 用户打开向量加法的多窗格视图
- **THEN** 每个窗格具有独立案例标题、案例编号和二维图形
- **AND** 点击窗格或阶段只更新当前阅读焦点，不新增案例标签或修改会话历史

#### Scenario: Compare two composition paths

- **WHEN** 用户打开 `AB` 与 `BA` 的并排 storyboard
- **THEN** 两条路径具有独立标题、阶段编号和终点标记
- **AND** 切换或返回阶段不会新增案例标签或修改会话历史

### Requirement: Claim-linked case reader

案例阅读页 SHALL 能根据当前阶段和当前窗格突出显示对应的 claim、公式变量和图中实体。阅读页不得显示场景命令文本；可以显示数学对象标签、读图提示、不变量和案例目的。

#### Scenario: Reader follows pane focus

- **WHEN** 用户在向量加法四窗格中选择第三个案例
- **THEN** 阅读页突出该案例的定义/公式、几何意义和相关 claim
- **AND** 其他案例窗格仍保持可见且不泄漏命令文本

#### Scenario: Reading highlights visual evidence

- **WHEN** 用户查看“先旋转再拉伸”的阶段
- **THEN** 阅读页突出对应的 `(AB)x=A(Bx)` claim、阶段说明和相关变量
- **AND** 画布中对应对象使用同一教学角色颜色
