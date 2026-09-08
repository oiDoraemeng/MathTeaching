## Purpose

为向量加法提供可由用户控制的二维案例窗格布局，使一个到四个独立案例能够同时可见并可单独选择，同时保持案例阅读内容与 Agent 会话相互隔离。

## ADDED Requirements

### Requirement: User-selectable pane count

向量加法案例视图 SHALL 支持单窗格、双窗格、三窗格和四窗格四种布局。布局切换 SHALL 只改变案例窗格排列，不重新生成解释、不调用模型，也不修改 Agent 会话历史。

#### Scenario: Switch pane count

- **WHEN** 用户将布局从单窗格切换为双窗格、三窗格或四窗格
- **THEN** 视图显示相应数量的独立 2D 案例窗格
- **AND** 已有案例数据和当前 Agent 会话保持不变

### Requirement: All visible panes are independent 2D cases

每个窗格 SHALL 是独立的二维视口，绑定一个有唯一 id 的案例；可见窗格同时显示，不得用同一画布复制冒充多个案例。案例不足当前窗格数时，空窗格 SHALL 明确显示可添加案例的状态，不得复制或臆造案例。

#### Scenario: Fewer cases than panes

- **WHEN** 产物只声明两个案例而用户选择四窗格
- **THEN** 两个案例窗格显示其各自图形
- **AND** 其余窗格显示空状态或添加入口，不重复已有案例

### Requirement: Case selection and focus

用户点击窗格 SHALL 将该案例设为当前案例，并同步案例阅读页的标题、公式、几何意义和阶段；切换焦点 SHALL 不关闭其他窗格，也不改变案例 id。

#### Scenario: Focus a pane

- **WHEN** 用户点击三窗格中的第二个案例
- **THEN** 第二个窗格显示选中状态，阅读页切换到该案例
- **AND** 第一和第三个窗格继续显示原案例

### Requirement: Layout persistence and safe bounds

当前窗格数量和案例绑定 SHALL 在本次应用会话中保持，取值只能为 `1`、`2`、`3`、`4`。非法数量、重复案例 id 或跨主题案例绑定 SHALL 被拒绝并保留上一次有效布局。

#### Scenario: Reject invalid layout

- **WHEN** 收到数量为 `0`、`5` 或重复/跨主题案例 id 的布局请求
- **THEN** 请求失败并显示可诊断错误
- **AND** 当前有效布局和画布不变
