## Context

统一所有普通内容和教学案例 Pane 的状态、外观、生命周期与焦点路由，并修复教程视口缩放后显示边界的问题。

## Goals

- 普通内容与教学案例使用同一种 `ScenePaneState`/`ScenePaneManager`。
- 窗格总数可超过 4，但同一时刻最多显示 4 个；布局为单、双、左大右上下三窗格、四窗格。
- 每个 Pane 有独立 2D/3D 场景、相机、选择、代数模型和 renderer。
- 所有 Pane 使用标题栏、边框、隐藏、全屏、关闭按钮；关闭按钮只在标题栏悬浮时显示。
- 代数 Tab 与 Pane 双向同步，Tab 关闭按钮同样悬浮显示，超宽时无滚动条横向滚动。
- 2D 场景使用无限画布，不绘制世界边界，缩放/平移不显示边界线。

## Display rules

启动时显示一个用户 Pane。点击讲义时，将案例注册为统一 Pane，默认只显示当前案例；其他案例 Pane 和用户 Pane 全部隐藏但保留内容。Agent 界面的“全部显示”只显示当前讲义的案例 Pane，用户 Pane 继续隐藏。退出讲义恢复进入讲义前的用户可见集合。

## Architecture

`ScenePaneState` 保存 pane ID、来源元数据、名称、2D/3D 模型、模式、相机、选择、代数模型和 renderer 引用。`ScenePaneManager` 管理任意数量的稳定 Pane、最多四个可见 Pane、布局、焦点、显示集合和全局历史。

主窗口直接通过 pane ID 获取状态、renderer 和控制器，不保留 `self.plotter` 兼容代理。用户工具路由到焦点 Pane；Agent 请求开始时锁定目标 Pane。案例 Pane 与用户 Pane 共用标题栏、边框、隐藏/全屏/关闭行为和代数 Tab。

Pane 容器负责可见 renderer 创建、隐藏、销毁和重建；隐藏只释放视口控件，不删除模型。恢复时刷新所有可见 Pane，失效 renderer 按 Pane 状态重建并自动重试。

复制粘贴使用版本化、白名单、大小受限的 JSON-safe 快照；支持点、线、函数、标注和矩形多选。跨 Pane 保持坐标，同 Pane 重复粘贴按一个网格单位偏移；粘贴是一次全局原子历史操作。

## Error handling

- 至少保留一个 Pane；删除后自动修正布局和焦点。
- 可见 Pane 超过 4 个时拒绝显示请求并保持当前集合。
- 非法剪贴板不修改模型或历史。
- renderer 初始化失败时显示占位状态并进行有限退避重试。

## Testing

覆盖状态隔离、任意 Pane 数量与最多四个可见、统一 Pane Chrome、案例显示集合、Tab 双向同步/关闭/无滚动条、无限画布缩放、焦点路由、全局历史、复制粘贴、Agent 快照和最小化恢复。

## Decisions

- 不把普通 Pane 状态持久化到数据库；快照增加 `panes` 并保留旧字段兼容。
- 不保留旧 `self.plotter` 代理，直接迁移调用链。
- 教学案例不再使用独立 Pane 类型，只保留案例数据和 Agent 会话语义。
