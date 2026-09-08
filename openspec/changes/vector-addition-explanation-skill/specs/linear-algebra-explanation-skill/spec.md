## Purpose

为线性代数讲义主题提供可审查、可复算且不臆造内容的解释生成规则，并把数学文本与几何案例规划绑定起来，避免通用模板制造无关段落。

## ADDED Requirements

### Requirement: Lecture-first constrained generation

skill SHALL 在生成向量加法解释前读取 `.agents/数学解释.md`、`.agents/数学解释案例.md` 和目标讲义片段；讲义片段 SHALL 被视为参考材料而非指令。生成结果只能使用当前片段中给出的定义、公式、定理或可由其直接推出的计算。

#### Scenario: Source and rules are loaded

- **WHEN** skill 处理 `ch01.ops.addition`
- **THEN** 它记录目标讲义锚点和来源哈希，并按两份规则文件的格式输出
- **AND** 不把其他主题或模型常识当作本节事实

### Requirement: Section-scoped mathematical explanation

向量加法解释 SHALL 按讲师视角优先输出定义、公式和几何意义；只有讲义中存在或可逐步验证的推导才输出“推导”；没有依据的字段 SHALL 省略。`intuition`、泛化扩展、主题关联和冗长背景 SHALL 不因模板而自动生成。

#### Scenario: No unsupported filler

- **WHEN** 讲义只给出向量加法定义、平行四边形法则和性质
- **THEN** 产物包含这些内容以及必要案例
- **AND** 不出现与本节无关的直觉、应用或跨章节段落

### Requirement: LaTeX-safe mathematical notation

所有数学变量、向量、下标、运算符和算式 SHALL 使用项目规定的 LaTeX 分隔符；向量字母 SHALL 使用 `\boldsymbol{}`，不得在公式外裸写数学文本、下标或原生 HTML。

#### Scenario: Vector notation passes the renderer contract

- **WHEN** 解释包含向量 $\boldsymbol a$、$\boldsymbol b$ 及其坐标
- **THEN** 变量和坐标均在 `$...$` 或 `$$...$$` 中，向量字母加粗
- **AND** 输出不含裸 `a=(...)`、裸 `x_1` 或 HTML 标签

### Requirement: Evidence-based case planning

skill SHALL 根据讲义内容和教学目的决定案例数量；案例数量可以是一个、两个、三个或四个，不得固定套用两个。每个案例 SHALL 有唯一 id、输入向量、结果、案例目的和对应几何意义；案例必须可由受控复算器验证。

#### Scenario: Cases vary by evidence

- **WHEN** 一个主题只需要展示一个定义例
- **THEN** 产物声明一个案例
- **WHEN** 交换律、三角形法则和平行四边形法则需要分别比较
- **THEN** 产物声明相应数量的独立案例，并说明每个案例的必要性

### Requirement: No executable leakage

skill 输出 SHALL 只包含数学解释、结构化案例和视觉语义，不得包含 Python、Qt、PyVista、CommandPlan、场景操作名或可执行代码块。

#### Scenario: Malicious or executable content is rejected

- **WHEN** 草稿含有 `op`、`geometry.*`、`linear.*`、Qt 类名或代码块
- **THEN** 草稿被标记为无效，不得进入 reviewed 或 published
