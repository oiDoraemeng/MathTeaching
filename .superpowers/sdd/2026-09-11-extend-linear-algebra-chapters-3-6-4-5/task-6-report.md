# Task 6 report

第6章三个主题已从新的 immutable descriptor 生成 reviewed artifact：`basis-change.motivation`、`basis-change.coordinates`、`similarity-transform`。CoordinateFamilyCompiler 独立计算 P/P⁻¹ 双向读数；相似变换独立重算 `P⁻¹AP`、三阶段 `change_basis`/`apply_operator`/`change_basis_back`、端点误差和不变量。

TDD 前置红测：初次运行因缺少 `chapter_06` recipe 模块收集失败。实现后：

`pytest tests/test_linear_algebra_chapter_06.py -q` — 27 passed, 2 existing Paramiko deprecation warnings。

`pytest tests/test_linear_algebra_chapter_06.py tests/test_linear_algebra_coordinate_family.py tests/test_linear_algebra_compiled_resources.py -q` — 33 passed, 2 existing Paramiko deprecation warnings。

`pytest tests/test_linear_algebra_chapters_4_8_artifacts.py tests/test_linear_algebra_builders.py tests/test_linear_algebra_visual_compiler.py tests/test_linear_algebra_extended_plan_replay.py tests/test_scene_command_dispatch.py -q` — 61 passed, 2 existing Paramiko deprecation warnings。

`python -m scripts.release_chapter06` 调用 `compile_chapter_06()` 事务性重建 3 reviewed/compiled resources 和 index，保留既有 78 行全部字段，生成 81 unique rows（ch04=16，ch05=8，ch06=3，无 ch07/ch08）。测试覆盖实体/关系/阶段及每个关系数值叶 mutation、source/artifact/contract/compiled/index digest parity、7 文件替换每一处失败回滚，以及实际 MainWindow bridge/controller execute/replay 与失败执行回滚。宿主测试使用现有测试渲染器替身，不声称肉眼渲染验收。

实现过程追加的红测还揭示 worked example 输入 schema、旧 alias-only evidence 测试兼容性和矩阵对象 host dispatch 问题，均已修复。矩阵对象使用宿主支持的真实 transformed_grid，关系和阶段使用真实 staged_transform；未增加 matrix_tableau UI 功能。全部三个 reviewed 和 compiled 均重新生成，不使用旧第6章 fixture。

范围说明：本任务未修改 ch01–5 用户脏文件，不提交计划/OpenSpec勾选。独立复审待主代理安排。

## Independent review fix

复审指出阶段标题/说明未被 descriptor 约束。现 `_validate` 逐阶段严格比较 `title == descriptor.title`、`caption == spec.formula`，新增三主题各阶段 title/caption 单字段 mutation 负例。重新执行 `python -m scripts.release_chapter06`；资源内容保持 canonical parity。复审修复验证：`pytest tests/test_linear_algebra_chapter_06.py -q` — 30 passed, 2 existing warnings。
