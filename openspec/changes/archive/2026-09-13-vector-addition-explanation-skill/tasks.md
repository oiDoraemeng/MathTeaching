## 1. 讲义约束 skill

- [x] 1.1 新增仓库内 `.agents/linear-algebra-explanation-skill/SKILL.md`，链接 `.agents/数学解释.md`、`.agents/数学解释案例.md` 和讲义读取规则，明确不确定需求必须询问
- [x] 1.2 为 skill 增加可执行的输出检查清单：LaTeX 分隔符、`\boldsymbol{}` 向量、无裸数学文本、无 HTML/代码/场景 op、来源锚点和哈希
- [x] 1.3 编写 skill 行为快照/验证测试，覆盖“只输出有证据字段”“案例数量不固定”“拒绝无关扩展”

## 2. 向量加法内容与 artifact

- [x] 2.1 扩展向量加法 artifact 模型，增加声明式 `case_layout`/`cases` 结构，并保持旧主题兼容读取
- [x] 2.2 重写 `ch01.ops.addition` 的定义、公式、必要推导、几何意义和案例；移除无依据的 intuition/connections，修正所有向量 LaTeX
- [x] 2.3 根据讲义内容决定案例集合，至少覆盖有证据的分量计算、三角形法则和平行四边形法则；每个案例绑定唯一 example、claim 和 stage
- [x] 2.4 更新发布校验与数字复算，拒绝重复 id、跨主题引用、错误坐标或未经证据支持的案例
- [x] 2.5 更新 Qt/Web 解释视图，缺省字段不渲染；案例正文只展示定义、公式、推导（如有）、几何意义、案例和有证据误解

## 3. 多 2D 案例窗格

- [x] 3.1 新增案例窗格布局模型和校验器，支持 1/2/3/4，定义 1×1、1×2、1×3、2×2 布局与空窗格行为
- [x] 3.2 实现独立 2D 视口控制器，每个窗格使用独立 camera/actor、topic namespace 和已验证 case plan
- [x] 3.3 在主窗口中央增加布局选择与案例窗格容器，支持点击窗格选中、保持其他窗格同时可见，并在非法请求时原子回退
- [x] 3.4 扩展 JSON bridge/reducer/types，增加 `select_math_case_pane` 事件；保持 Agent 会话和案例标签隔离
- [x] 3.5 为 1–4 窗格、案例不足、重复/跨主题 id、焦点同步和布局回退增加 Qt/Web/Python 测试

## 4. 验证与交付

- [x] 4.1 运行 OpenSpec 校验、skill quick validation、向量加法 artifact 校验与复算测试
- [x] 4.2 运行完整 Python 测试、Web 单元测试和前端构建，修复仅由本变更引入的回归
- [x] 4.3 手动走查向量加法：定义/公式、可选推导、必要案例、1/2/3/4 窗格、点击切换和 Agent 会话隔离，记录结果
