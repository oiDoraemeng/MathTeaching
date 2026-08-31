## MODIFIED Requirements

### Requirement: Linear algebra lecture entry

左侧代数面板 SHALL 在“函数”按钮之后显示名称为“线性代数”的按钮。点击按钮 SHALL 打开以讲义前三章为来源的树形目录；目录 SHALL 只包含需要几何表示的章、节与主题，不显示练习、自检、挑战或纯符号推导条目。

#### Scenario: Open lecture tree
- **WHEN** 用户点击“线性代数”按钮
- **THEN** 弹窗显示“第1章 向量与几何测量”“第2章 矩阵的诞生——向量的批处理”“第3章 行列式”三个章节点
- **AND** 三个章节点默认展开并显示第二级节目录
- **AND** 节节点下的主题叶子默认折叠

#### Scenario: Open lecture topic list
- **WHEN** 用户点击“线性代数”按钮
- **THEN** 树形目录中包含讲义前三章的 54 个主题叶子，第一章 24 个、第二章 15 个、第三章 15 个

### Requirement: Lecture topic loading

每个主题 SHALL 提供稳定主题 ID、讲义目录路径、用户可见名称、公式、解释步骤、结论和经过校验的 2D 或 3D `CommandPlan`。主题目录 SHALL 覆盖前三章中确认需要几何表示的 54 个主题。用户选择叶子主题时 SHALL 清空当前场景并原子加载该计划；计划验证或执行失败时 SHALL 保留原场景。

#### Scenario: Load a lecture topic
- **WHEN** 用户选择“3.3 克拉默法则”下的“面积比解方程组”主题
- **THEN** 当前画布被清空并显示系数列向量、目标向量和面积比构造
- **AND** 主题解释页显示对应公式、推导步骤和结论

## ADDED Requirements

### Requirement: Tree expansion controls

线性代数弹窗 SHALL 在目录上方提供“展开全部”和“折叠”控制。“展开全部” SHALL 展开当前可见的全部目录；“折叠” SHALL 仅保留章节点可见。清空搜索 SHALL 恢复默认展开状态。

#### Scenario: Expand and collapse lecture tree
- **WHEN** 用户触发展开全部
- **THEN** 所有可见节节点及主题叶子均可见
- **WHEN** 用户随后触发折叠
- **THEN** 目录仅显示三个章节点

### Requirement: Lecture tree search

线性代数弹窗 SHALL 提供搜索框，并按主题名称、摘要、公式和完整讲义路径进行子串过滤。搜索结果 SHALL 保留匹配叶子的祖先上下文并自动展开匹配路径；无匹配时 SHALL 显示空目录而不触发主题加载。

#### Scenario: Search for Cramer topic
- **WHEN** 用户在搜索框输入“克拉默”
- **THEN** 目录显示第3章、3.3 克拉默法则和匹配主题叶子
- **AND** 其他不匹配的章、节与主题均隐藏

### Requirement: Leaf selection behavior

只有主题叶子 SHALL 触发绘图和数学解释；章或节节点 SHALL 只改变目录展开状态，不得清空或修改当前场景。

#### Scenario: Select branch then leaf
- **WHEN** 用户点击章或节节点
- **THEN** 当前场景和主题解释保持不变
- **WHEN** 用户点击该节下的主题叶子
- **THEN** 系统加载对应绘图并激活其数学解释标签
