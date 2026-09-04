# linear-algebra-case-tabs Specification

## Purpose
TBD - created by archiving change linear-algebra-case-tabs. Update Purpose after archive.

## Requirements

### Requirement: Case tabs in shared strip

右侧横向会话标签栏 SHALL 同时显示 Agent 会话标签和案例标签。案例标签标题 SHALL 使用案例名称，点击案例标签 SHALL 展示该案例的解释内容；每个标签 SHALL 提供关闭按钮，关闭案例标签后回到当前 Agent 会话，不得覆盖 Agent 会话记录。

#### Scenario: Keep agent and case tabs independent
- **WHEN** 用户打开“向量加法”案例后切换回 Agent 会话
- **THEN** Agent 时间线和 composer 保持原状态
- **WHEN** 用户再点击“向量加法”案例标签
- **THEN** 仍显示原案例解释，不创建新案例标签

### Requirement: Case deduplication

系统 SHALL 按案例 id 对案例标签去重。重复选择同一案例 SHALL 激活既有标签并刷新其内容，不得增加同名标签。

#### Scenario: Reuse a case tab
- **WHEN** 用户连续两次选择同一案例
- **THEN** 标签栏中该案例只出现一次
- **AND** 当前活动标签为该案例

### Requirement: Stable horizontal tab sizing

标签栏 SHALL 按每个标题的自然文字宽度显示标签，同时设置最小宽度与最大宽度上限，不得因标签数量增加而压缩文字；超过最大宽度的标题使用省略号。超出可见宽度时 SHALL 支持横向滚轮滚动并隐藏原生滚动条。

#### Scenario: Many case tabs
- **WHEN** 用户打开多个不同案例导致标签超出栏宽度
- **THEN** 已有标签宽度保持稳定
- **AND** 用户可以通过横向滚轮访问隐藏标签
- **AND** 不显示可见滚动条

### Requirement: JSON-only event contract

案例通知 SHALL 通过现有版本化 JSON bridge 以 `math_case` 事件传递，只包含 JSON-safe 的案例字段；WebView SHALL 不能通过该事件直接调用 Qt、PyVista 或场景服务。

#### Scenario: Render a case event
- **WHEN** Python 发出合法 `math_case` 事件
- **THEN** Web reducer 创建或更新对应案例标签
- **AND** 未发送任何场景 mutation intent

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
