# Task 5（窗格容器生命周期）报告

已完成普通工作区窗格容器接入。`ScenePaneWidget` 按 `ScenePaneManager` 的可见集合创建独立 QtInteractor；布局缩小时销毁可视控件并保留 `ScenePaneState`，再次显示时重新创建控件并恢复状态。删除窗格后由管理器修正布局和焦点，主窗口布局按钮改为通过容器同步。

验证：`pytest -q tests/test_scene_pane_widget.py tests/test_scene_pane_manager.py`（10 passed）。

暂未处理代数标签页、恢复重试和复制粘贴，符合 Task 5 范围。

复审修订：布局按钮在轻量测试窗口中无容器时直接回退到 manager；窗格 interactor 重建支持回调，以便主窗口清空旧控制器并按 pane 状态重绘。追加回归测试覆盖 2→1→2 恢复。

再次修订：创建 interactor 时先写入 pane.renderer_2d/renderer_3d，再触发重建回调，避免启动或恢复期间回调读取到空 renderer。

复审补丁：主窗口尚未完成初始化时延后 pane 重绘，避免轻量 fixture 缺少 algebra_panel 导致启动异常；初始化完成后统一补绘。恢复回归明确覆盖 pane2 的 2→1→2 隐藏、内容保留及回调读取。当前相关测试共 18 项通过（另有 2 个环境警告）。
