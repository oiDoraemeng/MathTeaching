## Why

`linear_algebra/teaching/quality.py` 是教学解释和视觉语义的本地质量适配器，但应用运行时只读取已经生成的 published artifact。过去修改一个句号后仍要手工重跑整批生成、审核、发布和编译；若目录里残留了更大的 `rN.json`，运行时还会绕过 `index.json` 直接读取它。结果既慢，也无法保证失败版本不会进入界面。

## What Changes

- 新增单主题增量发布服务：打开或恢复案例时，只对当前主题执行 `quality.py`；语义未变化时不写任何文件。
- 有变化时依次通过 schema、来源、数学例题、claim 引用、教学深度、视觉 contract 和编译器校验，再生成 draft、reviewed、published 与编译快照。
- 将 `index.json` 设为真实运行时发布指针，并在所有产物成功落盘后最后原子切换；校验失败继续读取旧 revision。
- 正式应用入口启用本地 authoring，同一服务也供批量升级脚本复用；打包环境、测试默认构造和外部 artifact root 不自动写仓库。
- 目录搜索索引只读取已发布解释并复用同一个 store，不再为全部主题解析和编译场景 bundle。

## Capabilities

### Modified Capabilities

- `linear-algebra-teaching-artifact`: 增加可信本地质量适配器的按主题增量发布、索引激活和失败回退要求。

## Impact

- 教学存储与发布：`linear_algebra/teaching/store.py`、`linear_algebra/teaching/authoring.py`。
- 应用加载：`main.py`、`ui/designer_window.py`。
- 目录性能：`ui/linear_algebra_tree_model.py`。
- 维护脚本与测试：`scripts/upgrade_teaching_artifacts.py`、教学 store/authoring 回归测试。
