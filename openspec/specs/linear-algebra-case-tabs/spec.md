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

左侧代数面板 SHALL 在“函数”按钮之后显示名称为“线性代数”的按钮。点击按钮 SHALL 打开以讲义前八章为来源的树形目录；目录 SHALL 只包含需要几何表示的章、节与主题，不显示练习、自检、挑战或纯符号推导条目。

#### Scenario: Open lecture tree
- **WHEN** 用户点击“线性代数”按钮
- **THEN** 弹窗显示“第1章 向量与几何测量”至“第8章 二次型与主轴定理”八个章节点
- **AND** 八个章节点默认展开并显示第二级节目录
- **AND** 节节点下的主题叶子默认折叠

#### Scenario: Open lecture topic list
- **WHEN** 用户点击“线性代数”按钮
- **THEN** 树形目录保留前三章 54 个主题并新增第 4–8 章 39 个绘图主题
- **AND** 新增主题按章节计数为第 4 章 16 个、第 5 章 8 个、第 6 章 3 个、第 7 章 6 个、第 8 章 6 个

### Requirement: Lecture topic loading

每个主题 SHALL 通过稳定的 `topic_id` 关联讲义来源、已发布 `TeachingArtifact` 和 `VisualizationRecipe`。前八章 SHALL 覆盖前三章既有的 54 个主题和第 4–8 章绘图目录的 39 个主题，不收录练习、自检、挑战或纯符号推导条目。

用户选择叶子主题时，系统 SHALL 使用同一个 `topic_id` 解析数学解释、数字算例、视觉语义和绘图配方；不得通过显示标题、公式或自然语言相似度选择绘图主题。

系统 SHALL 在内容和场景提交前完成 artifact schema、讲义锚点/哈希、视觉语义和 `CommandPlan` 校验。校验或执行失败时 SHALL 保留原场景和原解释，不得只加载其中一侧。

#### Scenario: Load a lecture topic

- **WHEN** 用户选择“8.3 主轴定理”主题
- **THEN** 系统使用该叶子的 `topic_id` 读取讲义来源、结构化数学解释和视觉语义
- **AND** 视觉语义编译出的计划显示原始二次型、特征向量主轴和标准形等值线
- **AND** 解释页显示公式、推导步骤、数字算例、几何意义和结论

#### Scenario: Reject mismatched explanation and drawing

- **WHEN** artifact 的 `topic_id`、source anchor 或 visualization recipe 与树叶不一致
- **THEN** 系统拒绝加载该 artifact
- **AND** 当前画布与当前解释保持不变
- **AND** 状态区指出主题 ID 和不匹配字段

### Requirement: Tree expansion controls

线性代数弹窗 SHALL 在目录上方提供“展开全部”和“折叠”控制。“展开全部” SHALL 展开当前可见的全部目录；“折叠” SHALL 仅保留章节点可见。清空搜索 SHALL 恢复默认展开状态。

#### Scenario: Expand and collapse lecture tree
- **WHEN** 用户触发展开全部
- **THEN** 所有可见节节点及主题叶子均可见
- **WHEN** 用户随后触发折叠
- **THEN** 目录仅显示八个章节点

### Requirement: Lecture tree search

线性代数弹窗 SHALL 提供搜索框，并按主题名称、摘要、公式和完整讲义路径进行子串过滤。搜索结果 SHALL 保留匹配叶子的祖先上下文并自动展开匹配路径；无匹配时 SHALL 显示空目录而不触发主题加载。

#### Scenario: Search for Cramer topic
- **WHEN** 用户在搜索框输入“克拉默”
- **THEN** 目录显示第3章、3.3 克拉默法则和匹配主题叶子
- **AND** 其他不匹配的章、节与主题均隐藏

#### Scenario: Search for chapter-eight topic
- **WHEN** 用户在搜索框输入“主轴定理”
- **THEN** 目录显示第8章、8.3 主轴定理和匹配主题叶子
- **AND** 其他不匹配的章、节与主题均隐藏

### Requirement: Leaf selection behavior

只有主题叶子 SHALL 触发绘图和数学解释；章或节节点 SHALL 只改变目录展开状态，不得清空或修改当前场景。

#### Scenario: Select branch then leaf
- **WHEN** 用户点击章或节节点
- **THEN** 当前场景和主题解释保持不变
- **WHEN** 用户点击该节下的主题叶子
- **THEN** 系统加载对应绘图并激活其数学解释标签

### Requirement: Lecture dialog viewport

线性代数讲义弹窗的内容区 SHALL 包在可滚动区域内，并对弹窗高度设置不超过屏幕可用高度的上限；当讲义内容超出上限时 SHALL 在弹窗内滚动显示，不得将弹窗顶出屏幕可见区域。

#### Scenario: Long lecture content scrolls inside dialog
- **WHEN** 用户打开的讲义主题其公式、步骤与结论总高度超过弹窗上限
- **THEN** 弹窗高度被限制在屏幕可用范围内，内容区出现纵向滚动
- **AND** 弹窗整体不超出屏幕可见区域

#### Scenario: Short content shows without scrollbar
- **WHEN** 讲义内容自然高度低于弹窗上限
- **THEN** 弹窗按内容自然高度显示且不出现多余滚动条

### Requirement: Explanation and visual semantics are paired

每个已发布主题 SHALL 同时提供数学解释和 `visual_semantics`。数学解释 SHALL 说明定义、公式、推导、数字例题、几何意义和常见误解；视觉语义 SHALL 说明公式变量在图上的对象、对象关系、阶段、不变量和需要强调的标注。

子智能体 MAY 生成这两部分内容，但其输出 SHALL 不包含可执行绘图命令、Python、Qt、HTML 或宿主对象名。运行时 SHALL 仅使用受控编译器将视觉语义转换为 `CommandPlan`。

#### Scenario: Explanation drives a matching visual

- **WHEN** 用户打开任意已发布叶子主题
- **THEN** 解释中的公式变量可以在视觉语义中找到对应实体
- **AND** 视觉语义编译后的图形展示解释所声明的关系，而不是仅显示无关向量

### Requirement: Explanation depth is visible in the lecture view

解释视图 SHALL 在存在对应字段时分别展示定义、主推导、数字算例、直觉、几何意义、常见误解、主题关联和读图提示。缺省字段 SHALL 隐藏，不得留下空白占位。

#### Scenario: Deep explanation sections render

- **WHEN** artifact 提供定义、推导、算例、误解和关联
- **THEN** Qt 和 Web 解释视图分别渲染这些区块
- **AND** 公式、数字算例和图中对象的符号角色保持一致

### Requirement: Atomic teaching bundle selection

主题叶子 SHALL 通过一次 `topic_id` 解析得到讲义来源、published artifact、visual contract 和编译计划。解释视图和画布 SHALL 只在同一 bundle 完成来源、claims、语义和场景校验后一起提交。

#### Scenario: Failed bundle keeps the previous case

- **WHEN** 新主题的 claim 引用断裂、视觉契约不满足或计划预览失败
- **THEN** 当前案例标签、解释内容和画布均保持不变
- **AND** 错误显示主题 ID、bundle revision 和失败阶段

### Requirement: Claim-linked case reader

案例阅读页 SHALL 能根据当前阶段突出显示对应的 claim、公式变量和图中实体。阅读页不得显示场景命令文本；可以显示数学对象标签、读图提示和不变量。

#### Scenario: Reading highlights visual evidence

- **WHEN** 用户查看“先旋转再拉伸”的阶段
- **THEN** 阅读页突出对应的 `(AB)x=A(Bx)` claim、阶段说明和相关变量
- **AND** 画布中对应对象使用同一教学角色颜色

### Requirement: Static storyboard navigation

案例页 SHALL 支持按顺序浏览阶段快照、并排比较或叠加视图。切换阶段 SHALL 只改变已发布 bundle 的展示状态，不调用子智能体、不生成任意命令，也不改变树节点身份。

#### Scenario: Compare two composition paths

- **WHEN** 用户打开 `AB` 与 `BA` 的并排 storyboard
- **THEN** 两条路径具有独立标题、阶段编号和终点标记
- **AND** 切换或返回阶段不会新增案例标签或修改会话历史

### Requirement: Topic identity is stable across case tabs

案例标签的去重和刷新 SHALL 使用 `topic_id` 与 artifact revision，而不是显示标题或公式文本。source hash 变化时，旧 revision 可以继续阅读，但必须显示 stale 状态。

#### Scenario: Refresh a case revision

- **WHEN** 同一 `topic_id` 发布了新的 reviewed revision
- **THEN** 当前案例标签可以刷新到新 revision 而不创建重复标签
- **AND** 用户仍能识别当前 revision 和 stale 状态

### Requirement: Teaching case data and Agent sessions retain their semantics

教学案例 SHALL 继续使用其已有的案例数据、阶段和 Agent 会话语义；通用多窗格工作区 SHALL 不依赖向量加法或其他教学案例才能创建。案例阅读焦点事件 SHALL 通过统一 Pane 焦点同步代数 Tab 和场景焦点，不得删除或替换用户 Pane 的数据。

#### Scenario: Open a case while workspace has panes

- **WHEN** 用户在普通多窗格工作区中打开线性代数教学案例
- **THEN** 案例 Pane 按讲义显示集合规则打开
- **AND** 用户 Pane 的对象和代数 Tab 不被清空、删除或替换

### Requirement: Case panes share the unified workspace

案例视口 SHALL 注册为统一工作区 Pane，不再使用独立 Pane 类型。打开讲义默认只显示一个案例 Pane；Agent“全部显示”只显示当前讲义案例 Pane，用户 Pane 继续隐藏。案例焦点与代数 Tab SHALL 双向同步。

#### Scenario: Agent shows only lecture cases

- **WHEN** 用户点击 Agent 界面的“全部显示”
- **THEN** 当前讲义的案例 Pane 显示
- **AND** 用户之前创建的 Pane 仍隐藏
