## Why

当前“线性代数”入口只有五个扁平向量案例，无法反映《线性代数讲义》前三章的知识结构，也很难从课程目录快速定位需要几何直觉的主题。将讲义中适合绘图的内容整理成可搜索、可展开的课程树，可以让绘图与数学解释成为课程学习路径的一部分。

## What Changes

- 将线性代数弹窗从按类别排列的扁平列表改为与讲义前三章一致的树形目录，只收录需要几何表示的章节、节和主题。
- 在弹窗顶部增加搜索框、展开全部和折叠到章级按钮；默认展开章级以显示第二级节目录。
- 移除旧案例模型、旧案例 ID 和兼容适配器，改用 54 个稳定讲义主题 ID；每个叶子主题都提供确定性绘图、公式、解释步骤和结论。
- 将目录、数学解释、绘图配方和底层绘图能力拆成独立模块，复用原子场景加载通路，不改变 Agent 会话或 JSON bridge 的职责边界。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `linear-algebra-case-tabs`: 将线性代数入口扩展为讲义驱动的可搜索树形目录，并扩大内置几何案例覆盖面。

## Impact

- 数据模型：新增 `linear_algebra/catalog`、`linear_algebra/explanations`、`linear_algebra/visualizations` 和显式注册表。
- Qt UI：`ui/algebra_panel.py` 的线性代数弹窗改为搜索与树形导航；`ui/icons.py` 和 QSS 增加对应控件视觉。
- 场景与侧栏：沿用 `SceneCommandService`、`math_case` 事件和 `MathCaseView`，不新增外部依赖或跨边界调用。
- 测试：覆盖 54 个主题目录、独立解释、确定性配方、树形交互、搜索过滤和加载回归。
