## MODIFIED Requirements

### Requirement: Main viewport controls

主窗口 SHALL 在右上角 viewport toolbar 提供场景模式、单/双/三/四窗格布局和 Agent 控件。窗格布局控件 SHALL 使用统一 SVG 图标和至少 36px 命中区域，不得使用下拉菜单替代四种布局按钮，并 SHALL 暴露中文 accessible name。

#### Scenario: Layout controls are discoverable

- **WHEN** 用户查看 2D 或 3D 主视图右上角
- **THEN** 可以直接看到四个窗格布局图标
- **AND** 当前布局按钮具有选中态

### Requirement: Algebra panel follows viewport focus

代数区域 SHALL 按可用窗格显示可编辑 Tab；当前窗格获得焦点时，代数区域 SHALL 自动激活对应 Tab，所有编辑和图层操作 SHALL 只修改该窗格。

#### Scenario: Algebra tab follows focus

- **WHEN** 用户点击不同场景窗格
- **THEN** 左侧代数 Tab 自动切换到该窗格
- **AND** 其他 Tab 的对象和编辑状态保持不变

### Requirement: Pane title bar and algebra tab overflow

每个场景 Pane SHALL 显示标题和边框，并在标题栏提供隐藏、全屏和悬浮关闭按钮；关闭后 SHALL 自动修正布局和焦点。代数 Tab 的关闭按钮仅在悬浮时显示，Tab 超宽时支持横向滚动且不显示滚动条。
