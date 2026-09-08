# Task 7 报告

已在代数面板加入按 pane ID 保留的公式标签页，并在 DesignerWindow 中连接场景 pane 焦点：场景焦点切换会激活对应标签，标签切换会提交未完成的行内编辑。每个 pane 的 FormulaListWidget 独立保存，隐藏 pane 不会丢失模型；讲义案例容器未改动。

验证：`python -m pytest tests/test_algebra_panel.py -q`（22 passed）。
