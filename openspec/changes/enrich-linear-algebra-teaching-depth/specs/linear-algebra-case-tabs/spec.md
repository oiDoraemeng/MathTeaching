## MODIFIED Requirements

### Requirement: Lecture topic loading

每个主题 SHALL 通过稳定的 `topic_id` 关联讲义来源、已发布 `TeachingArtifact` 和 `VisualizationRecipe`。前三章 SHALL 继续覆盖 54 个需要几何表示的主题（24/15/15），不收录练习、自检、挑战或纯符号推导条目。

用户选择叶子主题时，系统 SHALL 使用同一个 `topic_id` 解析数学解释、数字算例、视觉语义和绘图配方；不得通过显示标题、公式或自然语言相似度选择绘图主题。

系统 SHALL 在内容和场景提交前完成 artifact schema、讲义锚点/哈希、视觉语义和 `CommandPlan` 校验。校验或执行失败时 SHALL 保留原场景和原解释，不得只加载其中一侧。

#### Scenario: Load a lecture topic

- **WHEN** 用户选择“3.3 克拉默法则”下的“面积比解方程组”主题
- **THEN** 系统使用该叶子的 `topic_id` 读取讲义来源、结构化数学解释和视觉语义
- **AND** 视觉语义编译出的计划显示系数列向量、目标向量和面积比构造
- **AND** 解释页显示公式、推导步骤、数字算例、几何意义和结论

#### Scenario: Reject mismatched explanation and drawing

- **WHEN** artifact 的 `topic_id`、source anchor 或 visualization recipe 与树叶不一致
- **THEN** 系统拒绝加载该 artifact
- **AND** 当前画布与当前解释保持不变
- **AND** 状态区指出主题 ID 和不匹配字段

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
