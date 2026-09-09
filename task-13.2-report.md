# Task 13.2 实施报告

- 新增 `PaneChrome` 可复用窗格标题栏，提供标题、隐藏、全屏和悬浮显示关闭控件，并通过信号暴露交互。
- `AlgebraPanel` 使用自定义标签栏，关闭按钮仅在悬浮标签时显示；支持超宽标签横向滚动且隐藏滚动条。
- 标签关闭会调用 `ScenePaneManager.delete_pane`，自动修复可见布局与活动窗格；始终保留最后一个标签。

验证：`pytest -q tests/test_algebra_panel.py tests/test_scene_pane_widget.py`（32 passed）。

提交：`b29b241 feat: 统一窗格标题栏与代数标签交互`
