# Task 5（窗格容器生命周期）报告

已完成普通工作区窗格容器接入。`ScenePaneWidget` 按 `ScenePaneManager` 的可见集合创建独立 QtInteractor；布局缩小时销毁可视控件并保留 `ScenePaneState`，再次显示时重新创建控件并恢复状态。删除窗格后由管理器修正布局和焦点，主窗口布局按钮改为通过容器同步。

验证：`pytest -q tests/test_scene_pane_widget.py tests/test_scene_pane_manager.py`（10 passed）。

暂未处理代数标签页、恢复重试和复制粘贴，符合 Task 5 范围。
