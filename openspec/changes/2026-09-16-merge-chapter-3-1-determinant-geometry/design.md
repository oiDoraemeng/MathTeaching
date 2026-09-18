# 设计

## 主题边界

- 目录 `ch03.s31`（显示名改为「行列式的几何意义」）只保留一个主题 `ch03.det.oriented-area`，显示名改为「行列式的几何定义」。
- 退役 `ch03.det.ad-bc`、`ch03.det.sign-zero-one`、`ch03.det.examples` 三个稳定主题及其全部派生资源。
- 全课程主题数 86 → 83，第 3 章 15 → 12；第 3 章节数仍为 7。

## 内容约束

- 正文逐字取讲义 3.1.1–3.1.3：只做三类排版处理——矩阵写成 `pmatrix` 块公式（不再压成一行）、散落的数学符号补进 `$...$`、3.1.3 速查表规范为有效的两列四行（文字仍用讲义原话）。
- 分节标题听命讲义：定理 3.1 的公式并入「定义」分节，不另立「公式」分节；3.1.3 保留「几何意义速查」标题。
- 讲义 3.1.1–3.1.3 没有数值案例：按定义自定两步案例——第一步单位正方形（`e1`、`e2`），第二步两个像 `v1=(2,1)`、`v2=(1,3)` 张成的平行四边形。两步各占一个窗格，首屏「全部显示」两格共用同一固定视角。
- 第二步用外接矩形解释 `ad - bc`：灰色虚线画出以原点与 `v1+v2` 为对角的外接矩形 `(a+b) x (c+d)`，再从矩形右下角连到 `v1`、左上角连到 `v2`，把矩形切成平行四边形加四个直角三角形（两个底 `a+b`、高 `c`，两个底 `c+d`、高 `b`），四个三角形都是「底 x 高 / 2」，于是 `S = (a+b)(c+d) - c(a+b) - b(c+d) = ad - bc`。虚线属于辅助构造，统一用 construction 表示色，图内标注只写可渲染字符。
- 外接矩形与两条切角辅助线由 compiler 依两列数值计算生成（`decomposes_into` 关系的 3.1 专属分支），图形与标注数值不会与实体漂移；案例窗格必须把计划里声明的 `style` 传给几何对象，否则虚线会画成实线。
- 3.1.4 分层例题不进正文、不进检索文本。

## 资源链路

1. `catalog/chapter_03.py`、`explanations/chapter_03.py`、`teaching/profiles.py`、`teaching/quality.py`、`visualizations/builders/chapter_03.py`、`scripts/generate_chapter3_local.py` 同步改注册。
2. 重新发布 `ch03.det.oriented-area`（draft → review → published）并重编 compiled 与 snapshot。
3. 删除三个退役主题的 draft/review/audit/published/snapshot/compiled 资源。
4. 更新 `index.json`、`topic-digests.json` 与第 3 章本地草稿索引。
5. 第 4–8 章载荷中指向 `ch03.det.ad-bc` 的「前置」连接改指 `ch03.det.oriented-area`，并刷新其摘要与索引链接字段（图形与 plan digest 不变）。
6. 更新计数、冻结 plan digest 与相关回归测试。

## 一致性约束

运行时 `topic_entries()`、解释映射、builder 映射、compiled 资源与发布索引均不得返回三个退役主题 ID。讲义源文件仍包含 3.1.1–3.1.4 四个标题（不改讲义）。第 3 章以外主题的 plan digest 保持不变，`ch03.det.oriented-area` 的冻结 plan digest 更新为合并后的图形。
