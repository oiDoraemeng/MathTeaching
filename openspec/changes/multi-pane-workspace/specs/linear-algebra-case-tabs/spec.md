## MODIFIED Requirements

### Requirement: Teaching case panes remain separate from workspace panes

教学案例 Tab SHALL 继续使用其已有的案例数据、阶段和 Agent 会话隔离；通用多窗格工作区 SHALL 不依赖向量加法或其他教学案例才能创建。案例阅读焦点事件不得覆盖普通窗格的 pane ID、代数 Tab 或场景焦点。

#### Scenario: Open a case while workspace has panes

- **WHEN** 用户在普通多窗格工作区中打开线性代数教学案例
- **THEN** 案例 Tab 按既有规则打开
- **AND** 普通窗格对象、布局、焦点和代数 Tab 不被清空或替换
