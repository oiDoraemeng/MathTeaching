## MODIFIED Requirements

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
