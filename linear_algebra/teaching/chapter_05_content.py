"""Reviewed lecture content and case layouts for Chapter 5 sections 5.1--5.5."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


CLAIM_FORMULAS = {
    "ch05.homogeneous.solution-space": r"\boldsymbol A\boldsymbol x=\boldsymbol 0,\quad \dim(\operatorname{Null}(\boldsymbol A))=n-\operatorname{rank}(\boldsymbol A)",
    "ch05.affine.solution-set": r"\{\boldsymbol x_p+\boldsymbol z\mid \boldsymbol z\in\operatorname{Null}(\boldsymbol A)\}",
    "ch05.consistency.geometry": r"\boldsymbol b\in\operatorname{Col}(\boldsymbol A),\quad \operatorname{Null}(\boldsymbol A)=\{\boldsymbol 0\}",
    "ch05.gaussian-elimination": r"\operatorname{Null}(\boldsymbol E\boldsymbol A)=\operatorname{Null}(\boldsymbol A),\quad x_j=\frac{\det(\boldsymbol A_j)}{\det(\boldsymbol A)}",
    "ch05.least-squares.projection": r"\boldsymbol A^{T}\boldsymbol A\hat{\boldsymbol x}=\boldsymbol A^{T}\boldsymbol b",
}


CONTENT: dict[str, dict[str, Any]] = {
    "ch05.homogeneous.solution-space": {
        "title": "齐次线性方程组",
        "summary": r"理解解齐次方程组 $=$ 求 $\operatorname{Null}(\boldsymbol A)=$ 求 $\operatorname{Ker}(T)$。",
        "definition": r"""一句话动机：要找哪些输入经过变换 $\boldsymbol A$ 之后“消失”了——这就是零空间。

本节目标：理解解齐次方程组 $=$ 求 $\operatorname{Null}(\boldsymbol A)=$ 求 $\operatorname{Ker}(T)$。

**（齐次线性方程组）** 方程组

$$
\boldsymbol A\boldsymbol x=\boldsymbol 0
$$

称为齐次线性方程组。其所有解构成的集合就是矩阵 $\boldsymbol A$ 的零空间 $\operatorname{Null}(\boldsymbol A)$。

**（齐次方程组的解结构）** $\operatorname{Null}(\boldsymbol A)$ 是一个向量空间。它的维数为

$$
\dim\bigl(\operatorname{Null}(\boldsymbol A)\bigr)=n-\operatorname{rank}(\boldsymbol A)
$$

这由秩-零化度定理得到。

一句话动机：具体怎么算？——高斯消元是解线性方程组的“标准操作流程”，做行变换不改变解集。

本节目标：掌握三种初等行变换，能独立完成 $3\times3$ 方程组的消元求解。

这意味着解集不是一个孤立的点，而是一个向量子空间。如果有一组基 $\{\boldsymbol v_1,\ldots,\boldsymbol v_k\}$ 张成 $\operatorname{Null}(\boldsymbol A)$，那么所有解就是这些基向量的全部线性组合。

几何理解：

- $\operatorname{rank}(\boldsymbol A)=n\rightarrow\operatorname{Null}(\boldsymbol A)=\{\boldsymbol 0\}\rightarrow$ 只有零解；
- $\operatorname{rank}(\boldsymbol A)=n-1\rightarrow\operatorname{Null}(\boldsymbol A)$ 是一条直线 $\rightarrow$ 所有解都在一条线上；
- $\operatorname{rank}(\boldsymbol A)=n-2\rightarrow\operatorname{Null}(\boldsymbol A)$ 是一个平面 $\rightarrow$ 所有解在一个平面上。""",
        "derivation": (r"""**（齐次方程组的解结构）**

设 $\boldsymbol x_1,\boldsymbol x_2\in\operatorname{Null}(\boldsymbol A)$，即

$$
\boldsymbol A\boldsymbol x_1=\boldsymbol 0,\qquad
\boldsymbol A\boldsymbol x_2=\boldsymbol 0.
$$

加法封闭：

$$
\boldsymbol A(\boldsymbol x_1+\boldsymbol x_2)
=\boldsymbol A\boldsymbol x_1+\boldsymbol A\boldsymbol x_2
=\boldsymbol 0+\boldsymbol 0
=\boldsymbol 0
\rightarrow
\boldsymbol x_1+\boldsymbol x_2\in\operatorname{Null}(\boldsymbol A).
$$

数乘封闭：

$$
\boldsymbol A(k\boldsymbol x_1)
=k\boldsymbol A\boldsymbol x_1
=k\boldsymbol 0
=\boldsymbol 0
\rightarrow
k\boldsymbol x_1\in\operatorname{Null}(\boldsymbol A).
$$

含零向量：

$$
\boldsymbol A\boldsymbol 0=\boldsymbol 0
\rightarrow
\boldsymbol 0\in\operatorname{Null}(\boldsymbol A).
$$

满足子空间三条件，$\operatorname{Null}(\boldsymbol A)$ 是向量空间。维数结论由秩-零化度定理得到：

$$
\dim\bigl(\operatorname{Null}(\boldsymbol A)\bigr)=n-\operatorname{rank}(\boldsymbol A).
$$""",),
        "examples": (
            {
                "id": "example.ch05.homogeneous.solution-space.line",
                "title": "例题：二维齐次方程组",
                "kind": "matrix_transform",
                "given": [[[1, 2], [2, 4]], [-2, 1]],
                "result": [0, 0],
                "check": "transformed",
                "lines": (r"""解方程组：

$$
\begin{cases}
x_1+2x_2=0,\\
2x_1+4x_2=0.
\end{cases}
$$

$$
\boldsymbol A=
\begin{pmatrix}
1&2\\
2&4
\end{pmatrix},\qquad
\operatorname{rank}(\boldsymbol A)=1.
$$

这两个方程等价于

$$
x_1+2x_2=0\rightarrow x_1=-2x_2.
$$

因此

$$
\operatorname{Null}(\boldsymbol A)
=\left\{
t\begin{pmatrix}-2\\1\end{pmatrix}
\mathrel{\Big|}t\in\mathbb R
\right\},
$$

是一条经过原点、方向为 $\begin{pmatrix}-2\\1\end{pmatrix}$ 的直线。""",),
            },
            {
                "id": "example.ch05.homogeneous.solution-space.three-variables",
                "title": "补充例题：三元齐次方程组",
                "kind": "linear_combination",
                "given": [[[1, 2], [2, -1], [1, 3]], [-7, 1, 5]],
                "result": [0, 0],
                "check": "linear_combination",
                "lines": (r"""求方程组

$$
\begin{cases}
x_1+2x_2+x_3=0,\\
2x_1-x_2+3x_3=0
\end{cases}
$$

的解空间的一组基。矩阵为

$$
\boldsymbol A=
\begin{pmatrix}
1&2&1\\
2&-1&3
\end{pmatrix}.
$$

消元得到

$$
\begin{pmatrix}
1&2&1\\
2&-1&3
\end{pmatrix}
\xrightarrow{R_2-2R_1}
\begin{pmatrix}
1&2&1\\
0&-5&1
\end{pmatrix}
\longrightarrow
\begin{pmatrix}
1&0&\frac75\\
0&1&-\frac15
\end{pmatrix}.
$$

令 $x_3=5t$，则 $x_1=-7t$、$x_2=t$。所以

$$
\operatorname{Null}(\boldsymbol A)
=\operatorname{span}\left\{
\begin{pmatrix}-7\\1\\5\end{pmatrix}
\right\},\qquad
\dim\bigl(\operatorname{Null}(\boldsymbol A)\bigr)=1.
$$

验证：$\operatorname{rank}(\boldsymbol A)=2$，$n=3$，所以

$$
\operatorname{rank}(\boldsymbol A)+\dim\bigl(\operatorname{Null}(\boldsymbol A)\bigr)=2+1=3.
$$""",),
            },
        ),
        "stages": (("solution", "零空间直线"),),
        "default_pane_count": 1,
        "case_example_indices": (0,),
        "sections": (("definition", "定义"), ("derivation", "证明"), ("worked_examples", "数学案例")),
    },
    "ch05.affine.solution-set": {
        "title": "非齐次方程组的解结构",
        "summary": r"掌握非齐次方程组的通解 $=$ 一个特解 $+\operatorname{Null}(\boldsymbol A)$ 的全部元素。",
        "definition": r"""一句话动机：$\boldsymbol b$ 不是零——那解是什么结构？

本节目标：掌握非齐次方程组的通解 $=$ 一个特解 $+\operatorname{Null}(\boldsymbol A)$ 的全部元素。

**（非齐次方程组的解结构）** 设 $\boldsymbol x_p$ 是 $\boldsymbol A\boldsymbol x=\boldsymbol b$ 的一个特解，即任意一个解。则 $\boldsymbol A\boldsymbol x=\boldsymbol b$ 的所有解为

$$
\left\{\boldsymbol x_p+\boldsymbol z\mathrel{\Big|}\boldsymbol z\in\operatorname{Null}(\boldsymbol A)\right\}.
$$

即：通解 $=$ 特解 $+$ 零空间，一个平移后的线性子空间。

几何理解：

- 齐次方程的解集是一条穿过原点的直线或平面——一个子空间；
- 非齐次方程的解集是那条直线或平面平移到特解 $\boldsymbol x_p$ 的位置——一个仿射空间；
- 这和向量加减法完全一致：

$$
\boldsymbol b
=\boldsymbol A(\boldsymbol x_p+\boldsymbol z)
=\boldsymbol A\boldsymbol x_p+\boldsymbol A\boldsymbol z
=\boldsymbol A\boldsymbol x_p+\boldsymbol 0.
$$""",
        "derivation": (r"""**（非齐次方程组的解结构）**

设 $\boldsymbol x_p$ 是 $\boldsymbol A\boldsymbol x=\boldsymbol b$ 的一个特解，即

$$
\boldsymbol A\boldsymbol x_p=\boldsymbol b.
$$

任取 $\boldsymbol z\in\operatorname{Null}(\boldsymbol A)$，则

$$
\boldsymbol A(\boldsymbol x_p+\boldsymbol z)
=\boldsymbol A\boldsymbol x_p+\boldsymbol A\boldsymbol z
=\boldsymbol b+\boldsymbol 0
=\boldsymbol b,
$$

所以 $\boldsymbol x_p+\boldsymbol z$ 也是解。

若 $\boldsymbol x$ 是 $\boldsymbol A\boldsymbol x=\boldsymbol b$ 的任意解，则

$$
\boldsymbol A(\boldsymbol x-\boldsymbol x_p)
=\boldsymbol A\boldsymbol x-\boldsymbol A\boldsymbol x_p
=\boldsymbol b-\boldsymbol b
=\boldsymbol 0,
$$

所以 $\boldsymbol x-\boldsymbol x_p\in\operatorname{Null}(\boldsymbol A)$。令 $\boldsymbol z=\boldsymbol x-\boldsymbol x_p$，则

$$
\boldsymbol x=\boldsymbol x_p+\boldsymbol z,\qquad
\boldsymbol z\in\operatorname{Null}(\boldsymbol A).
$$

综合以上两方面，$\boldsymbol A\boldsymbol x=\boldsymbol b$ 的解集恰好为

$$
\left\{\boldsymbol x_p+\boldsymbol z\mathrel{\Big|}\boldsymbol z\in\operatorname{Null}(\boldsymbol A)\right\}.
$$""",),
        "examples": (
            {
                "id": "example.ch05.affine.solution-set.line",
                "title": "例题：平移后的解直线",
                "kind": "matrix_transform",
                "given": [[[1, 2], [2, 4]], [3, 0]],
                "result": [3, 6],
                "check": "transformed",
                "lines": (r"""解方程组：

$$
\begin{cases}
x_1+2x_2=3,\\
2x_1+4x_2=6.
\end{cases}
$$

$$
\boldsymbol A=
\begin{pmatrix}
1&2\\
2&4
\end{pmatrix},\qquad
\boldsymbol b=
\begin{pmatrix}
3\\6
\end{pmatrix}.
$$

注意

$$
\boldsymbol b=3\begin{pmatrix}1\\2\end{pmatrix},
$$

即 $\boldsymbol b\in\operatorname{Col}(\boldsymbol A)$，所以有解。由 $x_1=3-2x_2$，取 $x_2=0$，得到特解

$$
\boldsymbol x_p=
\begin{pmatrix}
3\\0
\end{pmatrix}.
$$

又

$$
\operatorname{Null}(\boldsymbol A)
=\left\{
t\begin{pmatrix}-2\\1\end{pmatrix}
\mathrel{\Big|}t\in\mathbb R
\right\}.
$$

通解为

$$
\boldsymbol x
=\begin{pmatrix}3\\0\end{pmatrix}
+t\begin{pmatrix}-2\\1\end{pmatrix},\qquad t\in\mathbb R,
$$

是一条不过原点的直线。""",),
            },
            {
                "id": "example.ch05.affine.solution-set.three-by-three",
                "title": "补充例题：三元非齐次方程组",
                "kind": "matrix_transform",
                "given": [[[1, 1, 1], [1, -1, 2], [2, 0, 3]], [5.5, 0.5, 0]],
                "result": [6, 5, 11],
                "check": "transformed",
                "lines": (r"""解方程组：

$$
\begin{cases}
x_1+x_2+x_3=6,\\
x_1-x_2+2x_3=5,\\
2x_1+3x_3=11.
\end{cases}
$$

增广矩阵消元得到

$$
x_1+\frac32x_3=\frac{11}{2},\qquad
x_2-\frac12x_3=\frac12.
$$

令 $x_3=t$，则

$$
x_1=\frac{11}{2}-\frac32t,\qquad
x_2=\frac12+\frac12t.
$$

取 $t=0$ 得特解

$$
\boldsymbol x_p=
\begin{pmatrix}
\frac{11}{2}\\[2pt]
\frac12\\[2pt]
0
\end{pmatrix}.
$$

对应齐次解可取方向向量

$$
\begin{pmatrix}-3\\1\\2\end{pmatrix}.
$$

因此通解为

$$
\boldsymbol x=
\begin{pmatrix}
\frac{11}{2}\\[2pt]
\frac12\\[2pt]
0
\end{pmatrix}
+s\begin{pmatrix}-3\\1\\2\end{pmatrix},\qquad s\in\mathbb R.
$$

验证：$\operatorname{rank}(\boldsymbol A)=2$，$n=3$，所以零空间维数为 $1$，满足秩-零化度定理。""",),
            },
        ),
        "stages": (("homogeneous", "零空间"), ("solution", "平移后的解集")),
        "default_pane_count": 2,
        "case_example_indices": (0, 0),
        "sections": (("definition", "定义"), ("derivation", "证明"), ("worked_examples", "数学案例")),
    },
    "ch05.consistency.geometry": {
        "title": "解的存在性与唯一性",
        "summary": "用列空间和零空间的语言判断“有没有解”和“解是否唯一”。",
        "definition": r"""本节目标：用列空间和零空间的语言判断“有没有解”和“解是否唯一”。

**（存在性 / 唯一性判定）**

| 条件 | 存在性 | 唯一性 |
| --- | --- | --- |
| $\boldsymbol b\in\operatorname{Col}(\boldsymbol A)$ | 有解 | — |
| $\boldsymbol b\notin\operatorname{Col}(\boldsymbol A)$ | 无解 | — |
| $\operatorname{Null}(\boldsymbol A)=\{\boldsymbol 0\}$ | — | 有且只有一个解 |
| $\operatorname{Null}(\boldsymbol A)\neq\{\boldsymbol 0\}$ | — | 无穷多解，用特解 $+\operatorname{Null}(\boldsymbol A)$ 表达 |

**（方阵的特殊情形）** 若 $\boldsymbol A$ 是 $n\times n$ 方阵且 $\det(\boldsymbol A)\neq0$，则 $\boldsymbol A\boldsymbol x=\boldsymbol b$ 有唯一解：

$$
\boldsymbol x=\boldsymbol A^{-1}\boldsymbol b.
$$

这是因为

$$
\det(\boldsymbol A)\neq0
\rightarrow
\operatorname{Null}(\boldsymbol A)=\{\boldsymbol 0\}
\rightarrow
\text{解唯一},
$$

且 $\boldsymbol A$ 可逆，因而

$$
\operatorname{Col}(\boldsymbol A)=\mathbb R^n
\rightarrow
\text{始终有解}.
$$""",
        "derivation": (),
        "examples": (
            {
                "id": "example.ch05.consistency.geometry.two-states",
                "title": "例题：同一列空间下的有解与无解",
                "kind": "matrix_transform",
                "given": [[[1, 2], [2, 4]], [1, 0]],
                "result": [1, 2],
                "check": "transformed",
                "lines": (r"""取

$$
\boldsymbol A=
\begin{pmatrix}
1&2\\
2&4
\end{pmatrix}.
$$

当

$$
\boldsymbol b_1=
\begin{pmatrix}
1\\2
\end{pmatrix}
\in\operatorname{Col}(\boldsymbol A)
$$

时，方程组有解；又因为 $\operatorname{Null}(\boldsymbol A)$ 非平凡，所以有无穷多解。

当

$$
\boldsymbol b_2=
\begin{pmatrix}
1\\0
\end{pmatrix}
\notin\operatorname{Col}(\boldsymbol A)
$$

时，方程组无解，因为第二行永远等于第一行的 $2$ 倍，而 $0\neq2\times1$。""",),
            },
        ),
        "stages": (("column_membership", "目标在列空间中"), ("infinite_solutions", "对应的无穷解集"), ("no_solution", "目标在列空间外")),
        "default_pane_count": 3,
        "case_example_indices": (0, 0, 0),
        "sections": (("definition", "定义"), ("worked_examples", "数学案例")),
    },
    "ch05.gaussian-elimination": {
        "title": "高斯消元",
        "summary": "掌握高斯消元的操作流程，理解消元的几何意义。",
        "definition": r"""一句话动机：有了理论工具还不够——具体怎么算？答案是高斯消元。

本节目标：掌握高斯消元的操作流程，理解消元的几何意义。

**（初等行变换）** 对矩阵的行执行以下三种操作，不会改变方程组的解集：

- 交换两行（$P$ 操作）——重新排列方程的编号；
- 某行乘以非零常数（$D$ 操作）——方程两边同乘非零数；
- 某行加上另一行的 $k$ 倍（$E$ 操作）——一个方程加上另一个方程的倍数。

**（行变换不改变零空间）** 初等行变换保持矩阵的零空间不变：

$$
\operatorname{Null}(\boldsymbol E\boldsymbol A)=\operatorname{Null}(\boldsymbol A),
$$

其中 $\boldsymbol E$ 是任意初等矩阵的乘积。

但行变换会改变列空间。行变换只保持零空间，列空间中向量的方向会变，但各列之间的线性组合关系保持不变。

教学口诀：“行操作解不变，列变关系不变。”——这就是为什么高斯消元时只做行变换。

**（克莱姆法则 / Cramer's Rule）** 设 $\boldsymbol A$ 为 $n\times n$ 可逆矩阵，即 $\det(\boldsymbol A)\neq0$，则线性方程组 $\boldsymbol A\boldsymbol x=\boldsymbol b$ 有唯一解：

$$
x_j=\frac{\det(\boldsymbol A_j)}{\det(\boldsymbol A)},
$$

其中 $\boldsymbol A_j$ 是将 $\boldsymbol A$ 的第 $j$ 列替换为 $\boldsymbol b$ 得到的矩阵。

几何含义：每个未知数 $x_j=$ 将这一列换成 $\boldsymbol b$ 后得到的行列式 $\div$ 原行列式 $=$ 缩放比例的“方向分量”。""",
        "derivation": (r"""**（克莱姆法则 / Cramer's Rule）**

由 $\boldsymbol A\boldsymbol x=\boldsymbol b$ 且 $\boldsymbol A$ 可逆，得

$$
\boldsymbol x=\boldsymbol A^{-1}\boldsymbol b.
$$

利用伴随矩阵公式

$$
\boldsymbol A^{-1}
=\frac{1}{\det(\boldsymbol A)}\operatorname{adj}(\boldsymbol A),
$$

其中 $\operatorname{adj}(\boldsymbol A)$ 的第 $(j,i)$ 个元素为

$$
(-1)^{i+j}\det(\boldsymbol A\text{ 去掉第 }i\text{ 行第 }j\text{ 列}).
$$

于是

$$
x_j
=\frac{1}{\det(\boldsymbol A)}
\sum_i\operatorname{adj}(\boldsymbol A)_{ji}b_i
=\frac{\det(\boldsymbol A_j)}{\det(\boldsymbol A)}.
$$

这里 $\det(\boldsymbol A_j)$ 按第 $j$ 列展开即为 $\sum_i b_iC_{ij}$。""",),
        "examples": (
            {
                "id": "example.ch05.gaussian-elimination.process",
                "title": "例题：消元全过程",
                "kind": "matrix_transform",
                "given": [[[1, 2, 1], [2, 5, 2], [1, 1, -1]], [-2, 2, 1]],
                "result": [3, 8, -1],
                "check": "transformed",
                "lines": (r"""解方程组：

$$
\begin{cases}
x_1+2x_2+x_3=3,\\
2x_1+5x_2+2x_3=8,\\
x_1+x_2-x_3=-1.
\end{cases}
$$

增广矩阵为

$$
\left[
\begin{array}{ccc|c}
1&2&1&3\\
2&5&2&8\\
1&1&-1&-1
\end{array}
\right]
\xrightarrow[,R_3-R_1,]{,R_2-2R_1,}
\left[
\begin{array}{ccc|c}
1&2&1&3\\
0&1&0&2\\
0&-1&-2&-4
\end{array}
\right].
$$

继续消元：

$$
\left[
\begin{array}{ccc|c}
1&2&1&3\\
0&1&0&2\\
0&-1&-2&-4
\end{array}
\right]
\xrightarrow{R_3+R_2}
\left[
\begin{array}{ccc|c}
1&2&1&3\\
0&1&0&2\\
0&0&-2&-2
\end{array}
\right].
$$

回代得到

$$
x_3=1,\qquad x_2=2,\qquad x_1=-2.
$$""",),
            },
            {
                "id": "example.ch05.gaussian-elimination.cramer",
                "title": "补充例题：克莱姆法则求解二元方程组",
                "kind": "matrix_transform",
                "given": [[[2, 3], [1, 2]], [1, 2]],
                "result": [8, 5],
                "check": "transformed",
                "lines": (r"""用克莱姆法则解：

$$
\begin{cases}
2x+3y=8,\\
x+2y=5.
\end{cases}
$$

$$
\boldsymbol A=
\begin{pmatrix}
2&3\\
1&2
\end{pmatrix},\qquad
\det(\boldsymbol A)=4-3=1.
$$

$$
\boldsymbol A_1=
\begin{pmatrix}
8&3\\
5&2
\end{pmatrix}
\rightarrow
\det(\boldsymbol A_1)=16-15=1
\rightarrow
x=\frac11=1.
$$

$$
\boldsymbol A_2=
\begin{pmatrix}
2&8\\
1&5
\end{pmatrix}
\rightarrow
\det(\boldsymbol A_2)=10-8=2
\rightarrow
y=\frac21=2.
$$""",),
            },
            {
                "id": "example.ch05.gaussian-elimination.cramer-boundary",
                "title": "补充例题：克莱姆法则与唯一性",
                "kind": "determinant",
                "given": [[1, 2], [2, 4]],
                "result": 0,
                "check": "determinant",
                "lines": (r"""若

$$
\boldsymbol A=
\begin{pmatrix}
1&2\\
2&4
\end{pmatrix},
$$

能否用克莱姆法则解 $\boldsymbol A\boldsymbol x=\boldsymbol b$？

不能，因为

$$
\det(\boldsymbol A)=0,
$$

$\boldsymbol A$ 不可逆。克莱姆法则仅适用于 $\det(\boldsymbol A)\neq0$ 的方阵。""",),
            },
        ),
        "stages": (("initial", "初始增广矩阵"), ("eliminate", "消去第一列"), ("triangular", "上三角矩阵与回代")),
        "default_pane_count": 3,
        "case_example_indices": (0, 0, 0),
        "sections": (("definition", "定义"), ("derivation", "证明"), ("worked_examples", "数学案例")),
    },
    "ch05.least-squares.projection": {
        "title": "最小二乘解",
        "summary": "当精确方程无解时，用正交投影寻找残差最小的解。",
        "definition": r"""本节为选学内容，不作考试要求。

当 $\boldsymbol A\boldsymbol x=\boldsymbol b$ 无解时，即 $\boldsymbol b$ 不在列空间内，我们能做的最接近的事就是找到使得

$$
\lVert\boldsymbol A\boldsymbol x-\boldsymbol b\rVert
$$

最小的 $\boldsymbol x$——这就是最小二乘解。

**（最小二乘解）** $\hat{\boldsymbol x}$ 满足正规方程

$$
\boldsymbol A^{T}\boldsymbol A\hat{\boldsymbol x}
=\boldsymbol A^{T}\boldsymbol b.
$$

几何上，$\hat{\boldsymbol x}$ 使得 $\boldsymbol A\hat{\boldsymbol x}$ 是 $\boldsymbol b$ 在 $\operatorname{Col}(\boldsymbol A)$ 上的正交投影。""",
        "derivation": (),
        "examples": (
            {
                "id": "example.ch05.least-squares.projection.orthogonal",
                "title": "案例：投影到列空间",
                "kind": "projection",
                "given": [[2, 1], [1, 0]],
                "result": [2, 0],
                "check": "projection",
                "lines": (r"""取

$$
\boldsymbol A=
\begin{pmatrix}
1\\0
\end{pmatrix},\qquad
\boldsymbol b=
\begin{pmatrix}
2\\1
\end{pmatrix}.
$$

因为 $\boldsymbol b\notin\operatorname{Col}(\boldsymbol A)$，所以 $\boldsymbol A\boldsymbol x=\boldsymbol b$ 无精确解。正规方程为

$$
\begin{pmatrix}1&0\end{pmatrix}
\begin{pmatrix}1\\0\end{pmatrix}
\hat{x}
=
\begin{pmatrix}1&0\end{pmatrix}
\begin{pmatrix}2\\1\end{pmatrix},
$$

即 $\hat{x}=2$。于是

$$
\boldsymbol A\hat{x}
=\begin{pmatrix}2\\0\end{pmatrix},\qquad
\boldsymbol r
=\boldsymbol b-\boldsymbol A\hat{x}
=\begin{pmatrix}0\\1\end{pmatrix}.
$$

$\boldsymbol A\hat{x}$ 是 $\boldsymbol b$ 在 $\operatorname{Col}(\boldsymbol A)$ 上的正交投影，残差 $\boldsymbol r$ 与列空间正交。""",),
            },
        ),
        "stages": (("projection", "最小二乘投影"),),
        "default_pane_count": 1,
        "case_example_indices": (0,),
        "sections": (("definition", "定义"), ("worked_examples", "数学案例")),
    },
}


def _worked_example(spec: dict[str, Any], claim_id: str) -> dict[str, Any]:
    return {
        "id": str(spec["id"]),
        "title": str(spec["title"]),
        "kind": str(spec["kind"]),
        "given": deepcopy(spec["given"]),
        "calculation": list(spec["lines"]),
        "result": deepcopy(spec["result"]),
        "checks": [
            {
                "name": str(spec["check"]),
                "expected": deepcopy(spec["result"]),
                "tolerance": 1e-9,
            }
        ],
        "claim_refs": [claim_id],
    }


def refine_chapter_05_topic(
    topic_id: str,
    payload: dict[str, Any],
    explanation: dict[str, Any],
    visual: dict[str, Any],
) -> None:
    """Replace the old generic Chapter 5 prose with reviewed lecture content."""

    spec = CONTENT[topic_id]
    claim_id = f"claim.{topic_id}"
    examples = [_worked_example(item, claim_id) for item in spec["examples"]]

    explanation.update(
        {
            "title": str(spec["title"]),
            "summary": str(spec["summary"]),
            "definition": str(spec["definition"]),
            "formula": "",
            "derivation": list(spec["derivation"]),
            "worked_examples": examples,
            "geometric_meaning": "",
            "sections": [
                {"id": section_id, "title": title, "text": "", "claim_refs": [claim_id]}
                for section_id, title in spec["sections"]
            ],
            "searchable_text": [
                str(spec["title"]),
                str(spec["summary"]),
                str(spec["definition"]),
                *[line for item in spec["examples"] for line in item["lines"]],
            ],
        }
    )
    for key in (
        "intuition",
        "invariants",
        "pitfalls",
        "connections",
        "analogy_boundary",
        "transfer_note",
        "read_guide",
        "conclusion",
    ):
        explanation.pop(key, None)

    stages = {stage["id"].rsplit(".", 1)[-1]: stage for stage in visual["stages"]}
    ordered_stages = []
    for stage_name, purpose in spec["stages"]:
        stage = stages[stage_name]
        stage.update(
            {
                "title": purpose,
                "caption": "",
                "layout": "overlay",
                # 保留一项闭合的数学证据供 claim/stage 审计；第五章编译器只将
                # 阶段自有别名放入窗格，审计实体不会叠加到教学图上。
                "input_entity_refs": [visual["entities"][0]["id"]],
                "output_entity_refs": [],
                "relation_refs": [],
            }
        )
        ordered_stages.append(stage)
    visual["stages"] = ordered_stages

    explanation["case_layout"] = {
        "default_pane_count": int(spec["default_pane_count"]),
        "cases": [
            {
                "id": f"case.{topic_id}.{index}",
                "topic_id": topic_id,
                "example_ref": examples[example_index]["id"],
                "claim_refs": [claim_id],
                "stage_refs": [stage["id"]],
                "purpose": purpose,
            }
            for index, ((_, purpose), stage, example_index) in enumerate(
                zip(spec["stages"], ordered_stages, spec["case_example_indices"]), start=1
            )
        ],
    }

    claim = payload["claims"][0]
    claim.update(
        {
            "statement": str(spec["summary"]),
            "formula": CLAIM_FORMULAS[topic_id],
            "formula_symbols": [entity["role"] for entity in visual["entities"]],
            "explanation_refs": [section_id for section_id, _ in spec["sections"]],
            "entity_refs": [entity["id"] for entity in visual["entities"]],
            "relation_refs": [relation["id"] for relation in visual["relations"]],
            "stage_refs": [stage["id"] for stage in ordered_stages],
        }
    )
    payload["connections"] = []


__all__ = ["CONTENT", "refine_chapter_05_topic"]
