# 第 4–8 章线性代数交付验证

验证范围：93 个主题，章节分布为 24/15/15/16/8/3/6/6；第 4–8 章绘图目录为 39 个主题，分布为 16/8/3/6/6。

## 已通过

| 检查 | 结果 |
| --- | --- |
| `openspec validate extend-linear-algebra-chapters-4-8 --strict` | 通过 |
| `python -m linear_algebra.validation` | `93 topics validated` |
| `python scripts/validate_linear_algebra_drawing_catalog.py` | `39 topics; 16/8/3/6/6; 0 duplicates` |
| 第 4–8 章验证/证据/集成/Qt/运行时矩阵 | 97 passed |
| Web 全量 Vitest | 19 files, 62 tests passed |
| Web production build | Vite build passed |
| 关键原子加载与面板回归 | 29 passed |

集成矩阵逐主题核对 `topic_id`、scene、stage IDs、compiled resource 的 `plan_digest`；证据校验覆盖能力到操作、公式变量到实体、关系到 claim/contract。

## 全量套件记录

本工作区的 `pytest -q` 在一次完整运行中得到 **1651 passed, 11 failed, 1 skipped**。失败项来自既有增量发布测试对 70/81/87 主题、旧词汇集合、旧合同形状和旧讲义深度的断言，以及一个 snapshot 重建旧行为断言；本变更不通过放宽新校验来掩盖这些不一致。章节专项矩阵和本次新增测试均通过。

`openspec validate --all --strict` 的唯一失败是既有 `spec/multi-pane-workspace`；本变更自身严格校验通过。

## 版本与回滚证据

- 原子加载与完整 compiled witness 校验：`dbc1d16`
- 93 主题全量验证：`77e6a40`
- 语义证据一致性校验：`7b1259d`
- Agent prompt 扩展操作声明：`30ab391`
- Web/Qt 集成矩阵与 golden 元数据保存在 `tests/snapshots/linear_algebra_chapters_4_8_plans.json`

本环境未执行真实桌面逐章截图；截图和人工走查不应被本报告视为已完成证据。
