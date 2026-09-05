# Implementation Tasks

## 1. 讲义来源与教学产物契约

- [ ] 1.1 新增 `SourceContext` 与讲义片段读取器：按 `LessonEntry.source_anchor` 提取当前主题正文、当前节上下文和相邻主题；排除练习、自检、挑战和未纳入前三章树的内容
- [ ] 1.2 扩展解释模型并定义 `TeachingArtifact`、`WorkedExample`、`TopicConnection`、`VisualSemantics`、实体/关系/阶段等 JSON 可序列化类型；保留旧 `ExplanationContent` 字段兼容读取
- [ ] 1.3 为 artifact 编写 schema 校验：`topic_id`、source anchor、source hash、生成元数据、解释字段、视觉语义引用和枚举值必须完整且无执行代码
- [ ] 1.4 新增版本化 `TeachingArtifactStore`：支持 draft/published、原子写入、旧版本保留、UTF-8 稳定序列化和按章节资源加载
- [ ] 1.5 为 source hash/stale 状态和失败发布回退增加测试

## 2. 数学解释子智能体

- [ ] 2.1 新增 `ExplanationAgent` 协议和 provider 适配器：输入 `SourceContext`、`LessonEntry`、受控视觉词汇，输出 `TeachingArtifactDraft`
- [ ] 2.2 编写子智能体提示模板：只依据讲义片段，生成定义、公式、推导、数字例题、直觉、几何意义、误解、关联和读图语义；禁止输出 Python、Qt、CommandPlan、scene op 或 UI
- [ ] 2.3 实现模型回复解析与防泄漏校验：拒绝 Markdown 代码块、`op` 字段、场景命令名、宿主对象名和不在白名单中的视觉关系
- [ ] 2.4 实现数字例题复算器：覆盖向量运算、内积、投影、矩阵变换、行列式、面积和体积；无法自动复算的例题标为人工审核项
- [ ] 2.5 增加生成命令/测试夹具：能够按主题生成 draft，并保留 provider、model、prompt_version、source_hash 和 schema_version
- [ ] 2.6 增加人工审核后 publish 流程；未审核 draft 不得进入运行时资源

## 3. 视觉语义与编译器

- [ ] 3.1 定义视觉语义白名单和 `VisualContract`：实体、关系、阶段、不变量、布局模式和最小数量约束
- [ ] 3.2 新增 `VisualSemanticsCompiler`：将向量、基、网格、投影、张成、阶段、面积、体积、方向和比较语义编译为合法 `CommandPlan`
- [ ] 3.3 实现确定性布局：使用 `RenderContext` seed 生成命名空间、并排偏移、阶段快照、标签位置和视图边界检查
- [ ] 3.4 接入教学角色 palette：视觉语义只引用角色，编译器、场景颜色和解释图例使用同一颜色映射
- [ ] 3.5 盘点现有原语与缺口：优先复用 `transformed_grid`、`subspace_region`、`projection`、`staged_transform`、`oriented_area` 和 3D 体几何；确实无法表达时新增受约束 helper/op
- [ ] 3.6 为不支持语义、实体引用断裂、布局溢出和契约不满足增加可诊断错误测试

## 4. 三章数学解释资源

- [ ] 4.1 基于讲义生成并审核第 1 章 24 个 `TeachingArtifact`：向量、运算、内积、投影、叉积、混合积、几何证明和 n 维类比
- [ ] 4.2 基于讲义生成并审核第 2 章 15 个 `TeachingArtifact`：批量内积/投影、行列视角、基向量网格、复合、幂、秩、零空间、列空间和高维类比
- [ ] 4.3 基于讲义生成并审核第 3 章 15 个 `TeachingArtifact`：有向面积、ad-bc、det 符号/零/一、乘法性、克拉默法则、逆矩阵和高维体积
- [ ] 4.4 校验 54 个产物的定义、推导、算例、误解、关联和讲义锚点；任何内容不得引入讲义之外的新主题

## 5. 重点数形结合图形

- [ ] 5.1 第 2 章重点图：零空间多向量汇聚与区域塌缩、拉伸/旋转/缩放并排、AB/BA 双链、真实变形网格、批量投影/内积、行列视角、秩/列空间着色和 2D/3D 类比
- [ ] 5.2 第 3 章重点图：det(AB) 三阶段面积、det=0 共线塌缩、ad-bc 面积分解、可逆/退化对比、正向/逆向撤销链
- [ ] 5.3 第 1 章重点图：叉积法向量与方向、四步证明链、2D/3D/n 维类比、斜面力分解、锐角/直角/钝角内积对比
- [ ] 5.4 为每个重点主题编写 `VisualContract` 回归断言，断言数学关系而非仅断言 op 数量

## 6. 树形与运行时集成

- [ ] 6.1 registry 增加按 `topic_id` 解析统一 bundle 的 API：`LessonEntry + TeachingArtifact + VisualContract + VisualizationRecipe`
- [ ] 6.2 更新树叶选择流程：先解析并校验 bundle，再 preview/执行 plan，成功后同时更新场景和解释视图
- [ ] 6.3 更新 Qt 解释视图：分区渲染定义、推导、算例、直觉、几何意义、误解、关联和读图提示；缺省区块隐藏
- [ ] 6.4 更新 Web payload、`CaseProjection` 和 `MathCaseView`：传递深度解释、symbol roles 和 palette，不暴露绘图命令
- [ ] 6.5 更新搜索索引：聚合所有深度字段，保留匹配叶子的章节/小节祖先
- [ ] 6.6 测试树节点、解释资源和绘图 recipe 的 ID 一致性，以及失败时原场景/旧解释保持不变

## 7. 校验与回归

- [ ] 7.1 扩展 `linear_algebra.validation`：54 主题数量 24/15/15、来源锚点/哈希、artifact schema、关联 ID 和发布状态
- [ ] 7.2 增加“解释变量 ⇒ 视觉实体”和“视觉关系 ⇒ 主题契约”一致性校验
- [ ] 7.3 增加“声明能力 ⇒ 编译 plan 含实际 op”校验，声明性能力通过带理由的白名单跳过
- [ ] 7.4 删除 `visualizations/common.py` 中无调用者的模板 `_build_plan` 及私有辅助；更新 chapter 02 builder 数量 docstring 为 15
- [ ] 7.5 更新单元、集成和 Web/Qt 测试：artifact round-trip、agent 防泄漏、算例复算、重点图元、颜色角色和旧资源兼容
- [ ] 7.6 运行 `python -m linear_algebra.validation`、完整测试套件和构建检查，记录 54 主题验证结果
- [ ] 7.7 手动逐章走查树形选择、解释区块、数字算例、视觉对应和重点图形；截图记录到变更目录
