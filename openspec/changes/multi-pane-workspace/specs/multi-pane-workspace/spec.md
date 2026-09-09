# multi-pane-workspace Specification

## Purpose

为数学场景提供可独立编辑、可保留内容的多窗格工作区。

## ADDED Requirements

### Requirement: Independent pane layouts

系统 SHALL 支持单窗格、双窗格、三窗格和四窗格四种布局；每个窗格 SHALL 拥有独立的场景对象、相机、选择状态和渲染上下文。

#### Scenario: Create additional panes

- **WHEN** 用户从单窗格切换到双窗格、三窗格或四窗格
- **THEN** 新出现的窗格为空白
- **AND** 已有窗格中的对象、相机和历史状态保持不变

#### Scenario: Hide panes without deleting content

- **WHEN** 用户从多窗格切换到单窗格
- **THEN** 仅显示当前焦点窗格
- **AND** 其他窗格被隐藏但其内容不被删除
- **WHEN** 用户再次增加窗格数量
- **THEN** 之前隐藏的窗格恢复其原有内容

### Requirement: Icon layout controls

右上角 SHALL 提供四个可识别的 SVG 图标按钮，分别表示单、双、三、四窗格；控件 SHALL 不使用下拉菜单承载布局选择，并 SHALL 提供中文可访问名称和选中状态。

#### Scenario: Select layout icon

- **WHEN** 用户点击布局图标
- **THEN** 中央场景按对应布局排列
- **AND** 当前焦点窗格保持不变，除非它不再可见

### Requirement: Focus-routed editing

工具栏、鼠标工具、键盘快捷键和场景命令 SHALL 作用于当前获得焦点的窗格；点击窗格 SHALL 更新焦点高亮和当前 pane ID。

#### Scenario: Edit focused pane

- **WHEN** 用户点击第二个窗格后使用点、线、函数或选择工具
- **THEN** 新增、修改、删除和选择只发生在第二个窗格
- **AND** 其他窗格保持不变

### Requirement: Pane-scoped algebra tabs

代数区域 SHALL 为每个窗格提供可编辑 Tab；激活窗格后 SHALL 自动切换到对应 Tab，Tab 中的图层列表、公式编辑、显隐、删除和撤销/重做 SHALL 只作用于该窗格。

#### Scenario: Switch focus updates algebra tab

- **WHEN** 用户点击第三个窗格
- **THEN** 左侧代数区域自动激活第三个窗格的 Tab
- **AND** Tab 显示第三个窗格的对象而不显示其他窗格对象

### Requirement: Safe pane copy and paste

系统 SHALL 支持将当前窗格选中的对象复制为受版本和大小限制的 JSON-safe 快照，并粘贴到当前焦点窗格；粘贴 SHALL 生成新的对象 ID 并作为一个可撤销原子操作执行。

#### Scenario: Paste into a new pane

- **WHEN** 用户在窗格 A 复制对象并将焦点切换到空白窗格 B 后粘贴
- **THEN** 窗格 B 出现等价对象
- **AND** 窗格 A 的对象、ID 和历史不变

### Requirement: Mode support

窗格管理 SHALL 支持 2D 和 3D 场景；每个窗格 SHALL 保持自己的场景模式和相机状态，且现有 Agent、场景命令和教学案例 SHALL 不因创建普通窗格而改变语义。

#### Scenario: Use multiple 3D panes

- **WHEN** 用户在 3D 模式切换到多窗格
- **THEN** 每个可见窗格显示独立的 3D 视图
- **AND** 对一个窗格的相机操作不会改变其他窗格相机

### Requirement: Unified pane chrome and visibility sets

所有用户 Pane 和讲义案例 Pane SHALL 使用统一标题栏、边框、隐藏、全屏和关闭按钮；关闭按钮仅在标题栏悬浮时显示。窗格总数可超过 4，但可见 Pane 不得超过 4。

#### Scenario: Open lecture with existing panes

- **WHEN** 用户已有多个 Pane 并点击讲义
- **THEN** 默认只显示当前案例 Pane
- **AND** 其他案例 Pane 和用户 Pane 隐藏但内容保留

#### Scenario: Agent show all cases

- **WHEN** 用户在 Agent 界面点击“全部显示”
- **THEN** 只显示当前讲义的案例 Pane
- **AND** 用户 Pane 继续隐藏

### Requirement: Infinite 2D canvas

教程和普通 2D Pane SHALL 不绘制人工世界边界；缩放、平移和恢复 SHALL 只裁剪视口内容，不显示边界矩形。

#### Scenario: Zoom without visible world boundary

- **WHEN** 用户缩小或平移教程 2D Pane
- **THEN** 视口只显示画布内容
- **AND** 不出现世界边界矩形
