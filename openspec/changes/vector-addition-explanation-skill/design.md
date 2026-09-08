## Context

See `proposal.md` and the four delta specs. 当前已发布的 `ch01.ops.addition` artifact 是由通用质量适配器产生的扁平文本，包含 `intuition` 等本节不需要的字段；其 visual semantics 只有一个 sum 关系，编译器还按阶段索引硬编码三角形/平行四边形两个构造。主窗口当前只有一个 `QtInteractor`，案例标签在 Web 侧通过 storyboard 切换，但没有独立 2D 视口集合。

## Goals / Non-Goals

**Goals:**

- 将讲义规则、案例数量判断和 LaTeX 约束固化为仓库 skill 与可测试的内容校验。
- 为向量加法提供声明式案例集合；每个案例有独立数值、几何意义、claim/stage 引用和可复算结果。
- 在主窗口中央提供 1–4 个真实独立的 2D 视口，并通过 JSON-safe 事件同步当前窗格到案例阅读页。
- 保证旧主题、Agent 会话、原子 bundle 加载和失败回退行为不变。

**Non-Goals:**

- 不重写其他 53 个主题或改变前三章目录。
- 不引入运行时模型调用、连续动画、3D 案例或自由绘图命令。
- 不把“两个案例”改成新的固定默认数量；默认数量由 artifact 的案例集合决定，用户才可选择窗格数量。

## Decisions

### 1. Skill as repository-local authoring contract

新增 `.agents/linear-algebra-explanation-skill/SKILL.md`，并以 references 链接两份规则文件和案例格式文件。skill 明确“先读源、再判断字段/案例数量、最后输出结构化内容”的边界；需求不确定时要求提问。选择仓库内 skill 而不是个人安装目录，是为了和讲义、测试、OpenSpec 一起版本化。

替代方案：继续修改 `quality.py` 的通用模板。拒绝，因为模板会把“可选字段”重新变成隐式必填，无法约束未来主题生成。

### 2. Case-first artifact shape

在现有 `worked_examples` 之外增加 `case_layout` 元数据（`pane_count`、`cases[]`、每个 case 的 `id`、`topic_id`、`example_ref`、`stage_refs`、`purpose`）。数字案例仍复用现有 `WorkedExample` 与复算器；视觉案例引用同一 example，不复制数值来源。对于向量加法，至少提供定义/分量、三角形法则、平行四边形法则所需的案例，实际数量由讲义证据校验决定。

替代方案：用 storyboard stage 直接充当案例。拒绝，因为 stage 是同一案例的展示阶段，而窗格需要多个独立输入/结果。

### 3. Independent viewport grid at the shell boundary

主窗口保留现有全局场景作为非案例工作区；向量加法打开时，在中央 viewport host 内创建 1–4 个独立 `QtInteractor` 子视口，每个视口使用同一受控 renderer adapter 根据 case plan 渲染，不共享 actor 或 camera。布局使用 1×1、1×2、2×2 映射，三窗格采用 1×3；视口数量变化只重排/重建案例视口，不触发模型或 Agent 会话。

替代方案：在一个 plotter 中画四组向量。拒绝，因为用户要求单窗格且案例需独立可见、可分别缩放与选中。

### 4. JSON-only focus synchronization

案例窗格点击向 Web 发送 `select_math_case_pane`，payload 仅包含 `topic_id`、`case_id`、`pane_index`；Web reducer 更新当前案例，Qt 侧仅切换高亮和阅读内容。阶段切换沿用 `select_math_stage`，不携带场景命令。非法 id、跨主题绑定或超过四窗格均在边界校验阶段拒绝。

### 5. Optional explanation sections are data-driven

`quality.py` 对向量加法只生成定义、公式、必要推导、几何意义、案例和有证据的误解；不再填充 intuition/connections。Qt/Web 视图根据非空字段渲染，继续兼容其他主题的旧字段。

## Risks / Trade-offs

- [Risk] 多个 PyVista/QtInteractor 增加资源占用。→ 仅在向量加法案例视图激活时创建，最多四个；离开主题时销毁并恢复原单视口。
- [Risk] 旧 artifact schema 不认识 `case_layout`。→ schema 采用可选扩展并为旧 artifact 提供空布局适配；发布校验只对向量加法要求完整布局。
- [Risk] 三窗格在窄窗口中可读性下降。→ 每窗格设置最小尺寸，无法满足时显示布局错误并保留上一次有效布局。
- [Risk] 现有编译器/渲染器只支持一个 CommandPlan。→ 每个案例生成独立已验证 plan，使用统一 compiler 版本和 topic namespace，不把计划拼成跨案例的自由命令。

## Migration Plan

1. 新增 skill、delta specs 和测试夹具。
2. 扩展 artifact 模型/bridge payload，更新向量加法质量适配器与已发布 revision。
3. 实现案例窗格控制器和 1–4 布局 UI，接入窗格选择事件。
4. 运行向量加法回归、全量 Python 测试和 Web 构建；失败时回退到旧单视口与旧 artifact。
