## Why

上一轮批量生成的 54 个主题把“向量加法”套进了通用解释模板：内容含有未被讲义要求的直觉和泛化段落，数学变量也没有遵守项目约定的向量 LaTeX 写法；可视化则把案例数固定为两个，无法表达讲义分析后需要一个、两个或多个案例的差异。本次先把一个小节做成可复用的、可审查的生成规范，再以它验证运行时展示。

## What Changes

- 在仓库 `.agents` 下新增线性代数数学解释 skill。skill 先读取 `.agents/数学解释.md`、`.agents/数学解释案例.md` 和对应讲义片段；需求、案例数量或布局不明确时必须停下来询问，不得臆造。
- 只重写 `ch01.ops.addition`：按讲师视角输出定义、公式、严格存在的推导、几何意义和讲义支持的必要案例；没有推导就省略，不输出直觉和无关扩展；常见误解只有在讲义或公式确实支持时才保留。
- 所有数学变量、向量、下标和算式遵守 LaTeX 约束，向量统一使用 `\boldsymbol{}`；案例中的数字、公式和图形数据必须一致并可复算。
- 增加向量加法案例布局模型：用户可创建 1、2、3 或 4 个 2D 单窗格，案例由内容产物声明，窗格同时可见，点击窗格可切换当前案例/阶段，不改变 Agent 会话。
- 保留旧主题和其他 53 个主题不变；失败时原场景和原解释保持不变。

## Capabilities

### New Capabilities

- `linear-algebra-explanation-skill`: 讲义约束的数学解释与案例规划规则，作为仓库内可版本控制的 skill。
- `linear-algebra-case-layout`: 向量加法的 1/2/3/4 窗格 2D 案例布局与切换行为。

### Modified Capabilities

- `linear-algebra-explanation-depth`: 向量加法不再强制生成直觉等通用字段；解释内容以定义、公式、必要推导、几何意义和有证据案例为准。
- `linear-algebra-case-tabs`: 向量加法案例页增加多窗格布局元数据和窗格选择事件，同时保留案例标签与 Agent 会话隔离。

## Impact

- 内容与规则：`.agents/linear-algebra-explanation-skill/`、`linear_algebra/teaching/quality.py`、向量加法已发布 artifact。
- Qt/Web 展示：案例 payload、案例阅读页、主窗口中央 2D 案例窗格布局。
- 测试：新增 skill 规则快照、向量加法内容约束、案例数量与 1–4 窗格布局、JSON bridge 和回归测试。
