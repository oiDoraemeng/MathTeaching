## MODIFIED Requirements

### Requirement: Teaching case panes remain separate from workspace panes

教学案例 Tab SHALL 继续使用其已有的案例数据、阶段和 Agent 会话隔离；通用多窗格工作区 SHALL 不依赖向量加法或其他教学案例才能创建。案例阅读焦点事件不得覆盖普通窗格的 pane ID、代数 Tab 或场景焦点。

#### Scenario: Open a case while workspace has panes

- **WHEN** 用户在普通多窗格工作区中打开线性代数教学案例
- **THEN** 案例 Tab 按既有规则打开
- **AND** 普通窗格对象、布局、焦点和代数 Tab 不被清空或替换

### Requirement: Case panes share the unified workspace

案例视口 SHALL 注册为统一工作区 Pane，不再使用独立 Pane 类型。打开讲义默认只显示一个案例 Pane；Agent“全部显示”只显示当前讲义案例 Pane，用户 Pane 继续隐藏。案例焦点与代数 Tab SHALL 双向同步。

#### Scenario: Agent shows only lecture cases

- **WHEN** 用户点击 Agent 界面的“全部显示”
- **THEN** 当前讲义的案例 Pane 显示
- **AND** 用户之前创建的 Pane 仍隐藏
