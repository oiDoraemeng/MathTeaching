# Task 7 report

第7章六个主题已由 immutable spectral/orthogonal descriptors 生成：`eigen.direction`、`characteristic-polynomial`、`eigenspace`、`diagonalization`、`gram-schmidt`、`orthogonal-transform`。编译器逐实体、关系、阶段、标题/caption、引用、不变量和每个数值参数叶重新计算；不接受复根伪实方向。对角化验证 `P^-1 A P = D` 的三阶段端点，Gram–Schmidt 使用共享 3D compiler 验证投影/残差/标准化，正交变换验证 `Q^TQ`、长度、内积和面积。

资源通过 `python -m scripts.release_chapter07` 事务生成 6 reviewed/compiled 文件与索引；保留旧 81 行，最终 87 unique rows，无 ch08。事务测试覆盖 13 个目标逐点替换失败回滚及空 bundle 不写入。

验证命令：

前置红测：接管后创建正式 Chapter7 测试并运行 `pytest tests/test_linear_algebra_chapter_07.py -q --tb=short`，13 failed（非法 matrix/stage operations、generic annotation aliases、eigenspace 参数篡改未拒绝）。之后新增数值示例红测 6 failed、发布注册表/空 bundle 红测 2 failed，均在修复后回归通过。

- `pytest tests/test_linear_algebra_chapter_07.py tests/test_linear_algebra_spectral_family.py tests/test_linear_algebra_orthogonalization.py -q` — 47 passed，2 个既有 Paramiko deprecation warnings。
- `pytest tests/test_linear_algebra_compiled_resources.py tests/test_linear_algebra_chapters_4_8_artifacts.py tests/test_linear_algebra_builders.py tests/test_linear_algebra_visual_compiler.py tests/test_linear_algebra_extended_plan_replay.py tests/test_scene_command_dispatch.py -q` — 63 passed，2 个既有 Paramiko warnings。

host 测试使用实际 MainWindow bridge/controller 和现有 renderer doubles，覆盖六主题 execute、replay 和两者失败 rollback；不声称完成肉眼截图验收。重用宿主已有 transformed_grid、curve、subspace 和 3D projection/orthogonalization dispatch，补齐 projection3d schema 的既有参数名。旧 81 行全部字段保持一致，source/artifact/contract/plan digest 与磁盘 canonical recompile 一致。未勾选计划/OpenSpec；保留其他章节及用户脏改动。等待独立复审。
