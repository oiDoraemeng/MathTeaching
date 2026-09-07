## ADDED Requirements

### Requirement: Lecture dialog viewport

线性代数讲义弹窗的内容区 SHALL 包在可滚动区域内，并对弹窗高度设置不超过屏幕可用高度的上限；当讲义内容超出上限时 SHALL 在弹窗内滚动显示，不得将弹窗顶出屏幕可见区域。

#### Scenario: Long lecture content scrolls inside dialog
- **WHEN** 用户打开的讲义主题其公式、步骤与结论总高度超过弹窗上限
- **THEN** 弹窗高度被限制在屏幕可用范围内，内容区出现纵向滚动
- **AND** 弹窗整体不超出屏幕可见区域

#### Scenario: Short content shows without scrollbar
- **WHEN** 讲义内容自然高度低于弹窗上限
- **THEN** 弹窗按内容自然高度显示且不出现多余滚动条
