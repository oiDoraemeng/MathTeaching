## 1. 来源与教学契约

- [x] 1.1 新增 `SourceContext` 与讲义片段读取器：按 `LessonEntry.source_anchor` 提取当前主题正文、相邻主题标题和文本指纹，并排除练习/自检/挑战；用来源解析测试验证前三章锚点顺序和排除规则
- [x] 1.2 定义 `Claim`、`TeachingProfile`、`SourceRef`、`VisualEntity`、`VisualRelation`、`VisualStage` 和 `TeachingArtifact` 的 JSON 可序列化模型；用 round-trip 测试验证嵌套引用和旧 `ExplanationContent` 适配读取
- [x] 1.3 定义 L0-L4 教学层级和 54 个主题的最低 profile；用清单测试验证核心主题达到 L3/L4、高维类比标记类比边界
- [x] 1.4 定义视觉语义实体/关系/阶段白名单和有限数值类型；用反例测试拒绝代码、颜色、相机对象、任意表达式和非有限数值
- [x] 1.5 为 artifact 编写 schema 和闭合引用校验：topic、source、claims、解释区块、视觉实体/关系/阶段和 topic connections 必须完整；用缺字段和断链 fixture 验证错误路径
- [ ] 1.6 为每个 claim 增加解释字段、公式变量和视觉证据引用；用矩阵复合、投影和行列式 fixture 验证公式变量可解析到实体或 symbol role

## 2. 数学解释子智能体

- [ ] 2.1 新增 `ExplanationAgent` 协议和 provider 适配器：输入 SourceContext、LessonEntry、TeachingProfile、视觉词汇，输出单个 draft；用 fake provider 验证请求边界和取消行为
- [ ] 2.2 编写子智能体提示模板：只依据讲义片段生成定义、公式、推导、例题、直觉、几何意义、误解、关联、claims 和视觉语义；用提示快照测试验证字段和禁止项
- [ ] 2.3 实现 JSON 回复解析和防泄漏校验：拒绝 Markdown 代码块、`op` 字段、scene op、Qt/PyVista 名称和越界视觉关系；用恶意回复 fixture 验证不进入 reviewed
- [ ] 2.4 实现来源证据校验：claim source ref 必须落在当前 excerpt 或允许的相邻上下文，且 source hash 一致；用改写讲义 fixture 验证 `stale_source`
- [ ] 2.5 实现五层教学完整性校验：按 profile 检查推导、数字例题、不变量、边界情况和迁移关联；用 L2/L3/L4 缺字段 fixture 验证诊断
- [ ] 2.6 实现数字例题复算器：覆盖向量运算、内积、投影、矩阵变换、行列式、面积和体积；用精确有理数和容差边界测试验证正确/错误结果
- [ ] 2.7 增加 draft 生成命令和测试夹具：记录 provider、model、prompt_version、schema_version、source_hash 和输入 profile；用相同输入的比较测试验证元数据稳定

## 3. 教学产物存储与发布

- [ ] 3.1 新增版本化 `TeachingArtifactStore`：按章节保存 UTF-8 稳定排序 JSON、revision 和 artifact digest；用文件 round-trip 和跨平台换行测试验证可审查性
- [ ] 3.2 保存通过校验的精确 raw reply，并与 normalized artifact digest 建立审计关联；用 draft/reviewed/published fixture 验证原始回复可恢复且不作为绘图输入
- [ ] 3.3 实现原子发布：临时文件校验通过后替换 index，失败时保留旧 revision；用写入中断和 schema 失败测试验证旧版本可读
- [ ] 3.4 实现 source hash stale 检测和发布回退；用讲义片段变更测试验证旧 published 可继续查看、旧图形可继续使用
- [ ] 3.5 实现 artifact revision 比较：按 claims、解释区块、视觉语义和生成元数据输出差异；用同主题两版 fixture 验证比较不触发场景执行
- [ ] 3.6 为旧 `ExplanationContent` 增加只读适配器，并将迁移状态写入 registry；用旧资源测试验证兼容读取但禁止无 visual semantics 的新发布

## 4. 视觉语义编译器

- [ ] 4.1 定义 `VisualContract`：required claims/entities/relations/primitives、minimum stages、invariants 和 distinguishable roles；用投影、零空间、AB/BA、det(AB) fixture 验证契约解析
- [ ] 4.2 新增 `VisualSemanticsCompiler`：执行 schema、引用、contract、数值和 scene-scope 校验后再产生 `CommandPlan`；用编译器单元测试验证错误不触发 renderer
- [ ] 4.3 实现 claim evidence 检查：每个 visual claim 必须落到实体、关系和阶段，禁止只有文字而无图形证据；用缺少 endpoint 或 residual 的 fixture 验证失败
- [ ] 4.4 实现语义到现有原语的映射：grid_transform、subspace_span、projection_bundle、batch_mapping、staged_transform、signed_area、volume_orientation 和 orientation_marker；用 golden plan 验证实际 op
- [ ] 4.5 实现比较布局和静态 storyboard：支持 sequence、side_by_side、overlay，阶段具有独立别名、标题和可见实体；用 AB/BA 和投影阶段 fixture 验证布局不重叠
- [ ] 4.6 实现稳定 seed、命名空间、标签位置和边界检查；用相同 RenderContext 的两次编译比较 plan digest，并用溢出 fixture 验证明确失败
- [ ] 4.7 接入教学角色 palette，禁止 semantic payload 和 compiler 产生任意教学颜色字面量；用角色连续性和未知角色测试验证稳定颜色与 neutral 诊断
- [ ] 4.8 盘点并清理 capability-only `_build_plan` 路径；用全主题编译测试验证每个 plan 都来自 artifact 语义和 VisualContract

## 5. 三章教学资源与重点图

- [ ] 5.1 基于讲义生成并审核第 1 章 24 个 artifact：向量、运算、内积、投影、叉积、混合积、几何证明和 n 维类比；用章节覆盖和 source hash 校验
- [ ] 5.2 基于讲义生成并审核第 2 章 15 个 artifact：批量内积/投影、行列视角、基向量网格、复合、幂、秩、零空间、列空间和高维类比；用章节覆盖和 claim 闭合校验
- [ ] 5.3 基于讲义生成并审核第 3 章 15 个 artifact：有向面积、ad-bc、det 符号/零/一、乘法性、克拉默法则、逆矩阵和高维体积；用章节覆盖和数字复算校验
- [ ] 5.4 为投影、变换网格、AB/BA、零空间、det(AB)、叉积和逆矩阵编写黄金 visual semantics 与 VisualContract；用关系级回归断言验证数学主张可见
- [ ] 5.5 为每个重点主题生成已发布 compiled snapshot 和读图提示；用 plan digest、stage count、必需实体和不变量清单验证可回放

## 6. 树形、案例视图与运行时

- [ ] 6.1 registry 增加按 `topic_id` 解析统一 bundle 的 API：LessonEntry、published artifact、VisualContract、recipe 和 compiled snapshot；用 54 个 topic 的一一对应测试验证无 orphan
- [ ] 6.2 更新树叶选择流程：先解析/校验 bundle，再 preview/执行 plan，成功后同时提交场景和解释；用失败注入测试验证旧场景和旧解释保持不变
- [ ] 6.3 更新 Qt 解释视图：分区渲染教学层级、claims、定义、推导、算例、直觉、几何意义、误解、关联和读图提示；用缺省字段和长公式测试验证不留空占位
- [ ] 6.4 更新 Web `math_case` payload 和案例标签：传递 artifact revision、claim metadata、symbol roles、palette 和 storyboard，不暴露 scene op；用 JSON bridge schema 测试验证字段边界
- [ ] 6.5 实现案例 storyboard 导航：支持顺序快照、并排比较和叠加展示，切换阶段不调用模型、不新增标签、不修改会话历史；用 AB/BA 交互测试验证状态隔离
- [ ] 6.6 更新搜索索引：聚合定义、推导、算例、误解、关联和读图提示，并保留命中叶子的章节/小节祖先；用只出现在 derivation 的关键词测试验证路径保留
- [ ] 6.7 统一 Qt/Web 的 claim 高亮和角色颜色；用同一 artifact snapshot 比较两个 payload 的 claim IDs、角色和公式变量绑定

## 7. 校验、回归与交付

- [ ] 7.1 扩展 `linear_algebra.validation`：验证 54 个主题为 24/15/15、来源锚点/hash、artifact revision、claims、视觉引用和发布状态；用命令输出记录全量结果
- [ ] 7.2 增加“解释变量 ⇒ 视觉实体”和“视觉关系 ⇒ claim/VisualContract”一致性校验；用断链、错 topic 和漏关系 fixture 验证诊断
- [ ] 7.3 增加“声明能力 ⇒ 编译 plan 实际 op”校验，并给每个声明性跳过写理由；用 capability mismatch fixture 验证不允许静默降级
- [ ] 7.4 更新颜色契约和场景角色值的一致性：验证 palette、builder helper 和 SceneCommandService 的角色词汇一致；用全主题 plan 验证无未知角色
- [ ] 7.5 更新单元、集成和 Web/Qt 测试：覆盖 artifact round-trip、raw reply 审计、agent 防泄漏、算例复算、重点图、storyboard、原子加载和旧资源兼容；用完整测试套件验证
- [ ] 7.6 运行 `python -m linear_algebra.validation`、完整测试套件和构建检查；保存 54 主题、claim 覆盖和 plan digest 汇总到变更验证记录
- [ ] 7.7 手动逐章走查树形选择、解释分层、数字例题、claim 高亮、视觉阶段和失败回退；为重点主题保存截图并记录 artifact revision、source hash 和编译器版本
