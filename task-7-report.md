# Task 7：代数窗格标签

完成代数面板多窗格标签修复：

- 标签切换通过 `ScenePaneManager.focus_pane` 同步场景焦点。
- 切换前调用原窗格 FormulaListWidget 的 `accept_edit`，沿用网页 `formulaSubmitted` 提交链路。
- 双击标签可编辑窗格名称，并同步到窗格状态。
- 主题切换遍历所有保留的窗格模型及弹层。
- 增加标签切换、提交和多窗格主题同步回归测试。

验证：`python -m pytest tests/test_algebra_panel.py -q`（24 passed）。
