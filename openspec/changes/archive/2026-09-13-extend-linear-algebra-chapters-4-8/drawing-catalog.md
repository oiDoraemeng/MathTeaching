# 第 4–8 章几何绘图目录（来源：`.agents/线性代数讲义.md`）

## 筛选规则

本目录只收录满足以下至少一项的目录：

1. 讲义把几何对象、变换、方向、维数或图形类型作为结论；
2. 绘图能够直接呈现公式中的对象关系（例如核/像、特解+零空间、主轴）；
3. 绘图能够比较两个过程或显示不变量（例如换基前后、消元阶段、正交化阶段）。

以下内容不单独创建叶子主题：公理/定理的纯文字证明、逐行代数推导但没有新的空间关系、章节小结、基础练习、自检和挑战题。它们作为相邻主题的解释内容或读图提示保留。

当前前三章已有的能力记为“复用”；“缺口”表示需要先扩展受控视觉语义和 `CommandPlan`，不能用普通向量占位。

## 第 4 章 线性空间、线性无关与线性变换

| topic_id | 讲义目录 | 应呈现的图形 | 复用能力 | 缺口 |
| --- | --- | --- | --- | --- |
| `ch04.space.closure` | 4.1.1 线性空间 | 加法/数乘后的向量仍落在同一集合，比较 (R^2/R^3) 中的封闭性 | vector、polygon、annotation | 无；需新增 closure 语义校验 |
| `ch04.subspace.classification` | 4.1.2 子空间 | 原点、过原点直线、过原点平面、整个 (R^3)，并对比不经过原点的仿射集合 | plane3d、linear3d、subspace_region | 3D 子空间/仿射平面统一表达 |
| `ch04.subspace.intersection` | 4.1.2 子空间交集 | 两个子空间及其交集，显示并集不封闭的反例 | plane3d、polygon | 3D 交线/交点和交集高亮 |
| `ch04.subspace.col-null` | 4.1.3 列空间与零空间 | (A=\operatorname{diag}(1,0)) 将输入压到 x 轴；标出 Null 和 Col | transformed_grid、subspace_region | 同一变换的域/值域双空间布局 |
| `ch04.span.dimension` | 4.2.1 生成集 Span | 一根向量张成直线、两根不共线向量张成平面、三根不共面向量张成 (R^3) | subspace_region、plane3d | 2D/3D span 维数自动判定 |
| `ch04.dependence.redundancy` | 4.2.2 线性相关与无关 | 共线/共面与冗余向量对比，显示非零系数组合归零 | vector、staged_transform | 线性组合到零的关系链 |
| `ch04.nullspace.test` | 4.2.3 拼矩阵解 (Ax=0) | 系数空间中的非零解如何把列向量组合为零；无关组只显示零解 | staged_transform、annotation | 结构化系数空间/结果绑定 |
| `ch04.rank.collapse` | 4.2.4 极大无关组与秩 | rank 2 不压扁、rank 1 压成直线、rank 0 压到原点 | transformed_grid、subspace_region | rank 级别与实际塌缩结果契约 |
| `ch04.basis.span` | 4.3.1 基 | 最小且完整的向量组；对比少了不满、多了冗余 | vector、subspace_region | 基的“独立+生成”双条件标注 |
| `ch04.dimension.ladder` | 4.3.2 维数 | 点/线/面/体的维数阶梯与子空间包含关系 | plane3d、annotation | 维数层级/包含关系图元 |
| `ch04.coordinates.readout` | 4.3.3 坐标 | 同一向量在标准基和斜基下的分解，显示坐标系与系数 | transformed_grid、vector | 备用基网格和坐标读数标注 |
| `ch04.linear-map.definition` | 4.4.1 线性变换 | 网格/向量经过保持加性与齐性的映射，原点固定 | transformed_grid、staged_transform | 加性/齐性不变量标记 |
| `ch04.linear-map.compare` | 4.4.2 是 vs 不是线性变换 | 旋转、拉伸、投影与平移、平方、加常数并排对比 | transformed_grid、vector | 非线性/非原点保持的诊断视图 |
| `ch04.linear-map.matrix-columns` | 4.4.3 矩阵表示 | 标准基 (e_j) 的像就是矩阵列，网格由列向量决定 | transformed_grid、vector | “输入基→输出列”绑定 |
| `ch04.kernel-image` | 4.5.1 核与像 | 域中被压到零的方向和输出中可达的子空间 | subspace_region、staged_transform | 域/值域双平面或双视口 |
| `ch04.rank-nullity` | 4.5.2 秩-零化度 | 被压扁维数 + 保留维数 = 输入维数的守恒 | transformed_grid、subspace_region | 维数守恒数值牌和关系校验 |

**第 4 章绘图叶子数：16。** 4.0 回顾、证明、小结和练习不单独成图。

## 第 5 章 线性方程组

| topic_id | 讲义目录 | 应呈现的图形 | 复用能力 | 缺口 |
| --- | --- | --- | --- | --- |
| `ch05.homogeneous.solution-space` | 5.1 齐次方程组 (Ax=0) | 零解、解直线、解平面及其零空间基 | subspace_region、staged_transform | 3D 零空间和解集维数绑定 |
| `ch05.affine.solution-set` | 5.2 非齐次方程组 (Ax=b) | 特解 (x_p) 加零空间，显示平移后的仿射直线/平面 | subspace_region(origin)、vector | 3D 仿射子空间和特解标签 |
| `ch05.consistency.geometry` | 5.3 存在性与唯一性 | 相交一点、无穷多交点、平行无交的直线/平面组 | linear、plane3d | 线性约束面、交集类型和解状态 |
| `ch05.gaussian-elimination` | 5.4 高斯消元 | 增广矩阵的行变换阶段与对应几何约束不变 | staged_transform、annotation | 结构化矩阵/行操作 storyboard |
| `ch05.least-squares.projection` | 5.5 最小二乘 | 离散数据、拟合线、投影点和正交残差 | point、curve、projection | 最小二乘 bundle 和残差集合 |
| `ch05.fundamental-solution-system` | 5.6 基础解系 | 自由变量生成零空间基，显示每个基向量和张成集 | subspace_region、vector | 自由变量→基向量来源标注 |
| `ch05.elementary-matrix-elimination` | 5.7 初等矩阵 | (E_k\cdots E_1A=U) 的矩阵链和每一步作用 | staged_transform、annotation | 矩阵乘法链/行操作标签 |
| `ch05.least-squares-derivation` | 5.8 最小二乘完整推导 | (b) 到 Col(A) 的正交投影与残差垂直 | projection、vector | 多维列空间投影和残差证据 |

**第 5 章绘图叶子数：8。** 5.1/5.2 的证明、克莱姆公式推导和练习并入对应解释，不重复建图。

## 第 6 章 基变换与相似变换

| topic_id | 讲义目录 | 应呈现的图形 | 复用能力 | 缺口 |
| --- | --- | --- | --- | --- |
| `ch06.basis-change.motivation` | 6.1 为什么要换基 | 同一向量用标准基和斜基测量时坐标不同 | transformed_grid、vector | 双坐标系并排布局 |
| `ch06.basis-change.coordinates` | 6.2 基变换 | (P) 将新基坐标翻译为标准坐标，(P^{-1}) 反向翻译 | transformed_grid、staged_transform | 双向坐标转换箭头和读数 |
| `ch06.similarity-transform` | 6.3 相似变换 | 同一变换在两组基下的三步路径 (P^{-1}AP)，并标出不变量 | staged_transform、transformed_grid | 多空间路径、矩阵不变量牌 |

**第 6 章绘图叶子数：3。** 6.4 作为 7.4 的读图引导，不单独创建重复主题。

## 第 7 章 特征值与特征向量

| topic_id | 讲义目录 | 应呈现的图形 | 复用能力 | 缺口 |
| --- | --- | --- | --- | --- |
| `ch07.eigen.direction` | 7.1 定义与几何意义 | 方向不变、拉伸、反向和消失的特征向量 | transformed_grid、vector | 特征方向/特征值角色标注 |
| `ch07.characteristic-polynomial` | 7.2 特征多项式 | (det(A-\lambda I)) 的函数曲线、根和零空间出现位置 | curve.create、annotation | 根标记/谱数轴语义 |
| `ch07.eigenspace` | 7.3 求特征向量 | (operatorname{Null}(A-\lambda I)) 的特征空间直线/平面 | subspace_region、vector | 按特征值分组的特征空间 |
| `ch07.diagonalization` | 7.4 对角化几何意义 | 标准基下的耦合变换与特征基下的独立缩放三步对比 | staged_transform、transformed_grid | 特征基三段路径和终点对应 |
| `ch07.gram-schmidt` | 7.5 施密特正交化 | 原向量、投影分量、残差和逐步得到的正交基 | projection、vector | 3D 投影 bundle 和阶段残差 |
| `ch07.orthogonal-transform` | 7.6 正交矩阵与正交变换 | 旋转/反射保持长度、夹角和面积绝对值 | transformed_grid、oriented_area | 长度/夹角不变量标记 |
**第 7 章绘图叶子数：6。** 7.7 保留文字和公式解释，不创建图形主题。

## 第 8 章 二次型与主轴定理

| topic_id | 讲义目录 | 应呈现的图形 | 复用能力 | 缺口 |
| --- | --- | --- | --- | --- |
| `ch08.quadratic.matrix-form` | 8.1 二次型的定义与矩阵表示 | 交叉项对应对称矩阵非对角元，并预览 (Q(x,y)=1) | polygon、annotation | 二次型/等值线语义 |
| `ch08.quadratic.level-sets` | 8.2 二次型的几何意义 | 对角矩阵的正椭圆与含 (xy) 项的倾斜椭圆 | polygon、transformed_grid | 椭圆/一般二次曲线等值线 |
| `ch08.principal-axis` | 8.3 主轴定理 | 歪椭圆旋转到特征向量主轴，显示 (Q^TAQ=D) 前后 | transformed_grid、staged_transform、vector | 主轴/椭圆参数化和旋转 storyboard |
| `ch08.definiteness` | 8.4 定性 | 正定椭圆/椭球、不定双曲线/马鞍、半正定退化图形 | surface.create、plane3d | 隐式二次曲线/二次曲面 level-set |
| `ch08.completing-square` | 8.4 配方法化标准形 | 配方前后同一二次型的标准形和图形类型 | staged_transform、annotation | 配方法步骤与图形绑定 |
| `ch08.congruence-inertia` | 8.5 合同变换与惯性定理 | 可逆坐标替换前后正/负惯性指数不变 | staged_transform、quadratic level set | 惯性计数与坐标替换关系 |
**第 8 章绘图叶子数：6。** 8.6 只有在引用已有图形证据时才显示，不复制一套图。

## 汇总

- 新增绘图主题：**39**（第 4 章 16、 第 5 章 8、 第 6 章 3、 第 7 章 6、 第 8 章 6）。
- 纯解释但不单独绘图：第 4 章公理/证明/练习、第 5 章证明和克莱姆推导、第 6 章 6.4、第 7 章 7.7 的公式验证，以及各章练习和自检。
- 需要新增或增强的能力集中在：3D 子空间/仿射集、线性约束交集、矩阵 tableau storyboard、双空间映射、最小二乘 bundle、备用基网格、特征值谱、3D 正交投影和二次型 level-set。
