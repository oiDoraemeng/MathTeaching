# Task 8 report

第8章六个主题已由 topic-local quadratic descriptors 生成：matrix-form、level-sets、principal-axis、definiteness、completing-square、congruence-inertia。principal-axis 严格验证同一对称矩阵贯穿 `original/axes/standard`，`Q^T A Q=D`、端点和 cross-term；其余主题重算对称性、分类、符号/惯性、配方和合同变换数值证据。实体/关系/阶段、标题/caption/refs/invariants 以及参数 mutation/delete 均在计划生成前失败；语义 aliases 互斥且绑定真实几何操作。

前置红测：`pytest tests/test_linear_algebra_chapter_08.py -q` 初始 13 failures（缺 quadratic family/descriptor/recipe）；修复后 19 passed。

`python -m scripts.release_chapter08` 事务发布 6 reviewed/compiled 资源与索引，保留旧 87 行并生成 93 unique（无后续章节）。当前已覆盖空 bundle/13 文件发布事务测试、实际 MainWindow host execute/replay/rollback 及 canonical parity。

未勾选计划/OpenSpec，保留其他章节和用户脏改动，等待独立复审。

补充：修复 quadratic contour 对负/零方向的分段采样，并修正宿主 `add_teaching_quadratic_axes` 的实际 NameError 路径及 contour_segments 回放。最终 Chapter8 专项测试 47 项全部通过；required quadratic/compiled aggregate 55 passed；跨模块回归 61 passed（均仅 2 个既有 Paramiko warnings）。
