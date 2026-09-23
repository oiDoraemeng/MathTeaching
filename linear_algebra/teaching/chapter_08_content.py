"""Reviewed lecture content and case layouts for Chapter 8 sections 8.1--8.4."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


CLAIM_FORMULAS = {
    "ch08.quadratic.matrix-form": r"Q(\boldsymbol x)=\boldsymbol x^{T}\boldsymbol A\boldsymbol x",
    "ch08.quadratic.level-sets": r"Q(x,y)=1",
    "ch08.principal-axis": r"\boldsymbol Q^{T}\boldsymbol A\boldsymbol Q=\boldsymbol D",
    "ch08.definiteness": r"\operatorname{signature}(\boldsymbol A)=(n_{+},n_{-},n_{0})",
}


CONTENT: dict[str, dict[str, Any]] = {
    "ch08.quadratic.matrix-form": {
        "title": "二次型",
        "summary": "二次型可以写成对称矩阵的矩阵形式，交叉项系数要平均拆到两个非对角元。",
        "definition": r"""一句话动机：$x^{2}+y^{2}=$ 圆，$2x^{2}+3y^{2}+xy=$？怎么快速判断是什么形状？

本节目标：能把二次函数写成矩阵形式 $\boldsymbol x^{T}\boldsymbol A\boldsymbol x$，并识别 $\boldsymbol A$ 的特征值与图形的关系。

**（二次型）** $n$ 个变量的二次型是所有项都为二次的齐次多项式：

$$
Q(x_1,\ldots,x_n)=\sum_{ij}a_{ij}x_ix_j.
$$

在二维中，通常写作：

$$
Q(x,y)=ax^2+2bxy+cy^2.
$$

**（二次型的矩阵表示）** 任何二次型都可以表示为：

$$
Q(\boldsymbol x)=\boldsymbol x^{T}\boldsymbol A\boldsymbol x,
$$

其中 $\boldsymbol A$ 是对称矩阵，即 $\boldsymbol A^{T}=\boldsymbol A$。具体地：

$$
Q(x,y)=ax^2+2bxy+cy^2
\Longleftrightarrow
\boldsymbol A=
\begin{pmatrix}
a&b\\
b&c
\end{pmatrix}.
$$

重点：交叉项系数 $2b$ 在矩阵中拆成两个 $b$，放在两个非对角线位置。例如 $6xy\rightarrow b=3$，矩阵的两个非对角元都为 $3$。""",
        "derivation": (),
        "examples": (
            {
                "id": "example.ch08.quadratic.matrix-form.diagonal",
                "title": "例题：无交叉项",
                "kind": "determinant",
                "given": [[1, 0], [0, 1]],
                "result": 1,
                "check": "determinant",
                "lines": (r"""讲义中的前两组二次型没有交叉项。

$$
x^2+y^2
\Longleftrightarrow
\boldsymbol A=
\begin{pmatrix}
1&0\\
0&1
\end{pmatrix}.
$$

$$
2x^2+3y^2
\Longleftrightarrow
\boldsymbol A=
\begin{pmatrix}
2&0\\
0&3
\end{pmatrix}.
$$""",),
            },
            {
                "id": "example.ch08.quadratic.matrix-form.positive-cross",
                "title": "例题：正交叉项",
                "kind": "determinant",
                "given": [[1, 1], [1, 1]],
                "result": 0,
                "check": "determinant",
                "lines": (r"""交叉项的系数平均拆到两个非对角元：

$$
x^2+2xy+y^2
\Longleftrightarrow
\boldsymbol A=
\begin{pmatrix}
1&1\\
1&1
\end{pmatrix}.
$$

$$
x^2+6xy+9y^2
\Longleftrightarrow
\boldsymbol A=
\begin{pmatrix}
1&3\\
3&9
\end{pmatrix}.
$$""",),
            },
            {
                "id": "example.ch08.quadratic.matrix-form.negative-cross",
                "title": "例题：负交叉项",
                "kind": "determinant",
                "given": [[3, -1], [-1, 1]],
                "result": 2,
                "check": "determinant",
                "lines": (r"""对于

$$
3x^2-2xy+y^2,
$$

交叉项满足 $2b=-2$，所以 $b=-1$：

$$
\boldsymbol A=
\begin{pmatrix}
3&-1\\
-1&1
\end{pmatrix}.
$$""",),
            },
        ),
        "stages": (("diagonal", "无交叉项：两个对角矩阵"), ("positive_cross", "正交叉项：系数拆到两个非对角元"), ("negative_cross", "负交叉项：负号随非对角元")),
        "default_pane_count": 1,
        "case_example_indices": (0, 1, 2),
        "sections": (("definition", "定义"), ("worked_examples", "数学案例")),
    },
    "ch08.quadratic.level-sets": {
        "title": "二次型的几何意义",
        "summary": "没有交叉项时主轴与坐标轴对齐，有交叉项时椭圆的主轴倾斜。",
        "definition": r"""一句话动机：$Q(x,y)=1$ 画出来是什么形状？

本节目标：理解“没有 $xy$ 项 $=$ 正的图形 $=$ 特征向量方向恰好和坐标轴一致”。

**（对角矩阵对应的图形）** 若

$$
\boldsymbol A=
\begin{pmatrix}
\lambda_1&0\\
0&\lambda_2
\end{pmatrix},
$$

则

$$
Q(x,y)=\lambda_1x^2+\lambda_2y^2.
$$

当 $\lambda_1>0$、$\lambda_2>0$ 时，$Q(x,y)=1$ 画出来是正的椭圆，$x$ 轴和 $y$ 轴就是椭圆的主轴。

反例（有 $xy$ 项）：

$$
Q(x,y)=2x^2+2y^2+2xy,
$$

它的矩阵是

$$
\boldsymbol A=
\begin{pmatrix}
2&1\\
1&2
\end{pmatrix},
$$

有非对角线元素，画出来是歪的椭圆。

| 矩阵类型 | 方程 | 图形 | 和坐标轴 |
| --- | --- | --- | --- |
| 对角矩阵 | $\lambda_1x^2+\lambda_2y^2=1$ | 椭圆 | 正（对齐） |
| 非对角矩阵 | $ax^2+2bxy+cy^2=1$ | 椭圆 | 歪（不对齐） |

核心问题：为什么有 $xy$ 项就歪？因为 $xy$ 项意味着“$x$ 和 $y$ 纠缠在一起”——沿 $x$ 轴的变化影响 $y$ 方向，沿 $y$ 轴的变化影响 $x$ 方向。这本质上就是矩阵没有在特征向量方向上被坐标化。""",
        "derivation": (),
        "examples": (
            {
                "id": "example.ch08.quadratic.level-sets.aligned",
                "title": "对照案例：与坐标轴对齐的椭圆",
                "kind": "determinant",
                "given": [[3, 0], [0, 1]],
                "result": 3,
                "check": "determinant",
                "lines": (r"""取没有交叉项的二次型

$$
3x^2+y^2=1,
$$

对应矩阵为

$$
\boldsymbol A=
\begin{pmatrix}
3&0\\
0&1
\end{pmatrix}.
$$

它的两个特征值是 $3$ 和 $1$，椭圆主轴与坐标轴对齐。""",),
            },
            {
                "id": "example.ch08.quadratic.level-sets.tilted",
                "title": "讲义反例：有交叉项的倾斜椭圆",
                "kind": "determinant",
                "given": [[2, 1], [1, 2]],
                "result": 3,
                "check": "determinant",
                "lines": (r"""讲义中的二次型

$$
2x^2+2xy+2y^2=1
$$

对应矩阵为

$$
\boldsymbol A=
\begin{pmatrix}
2&1\\
1&2
\end{pmatrix}.
$$

它的两个特征值同样是 $3$ 和 $1$，但非对角元不为零，椭圆主轴相对坐标轴发生倾斜。""",),
            },
        ),
        "stages": (("aligned", "无交叉项：椭圆与坐标轴对齐"), ("tilted", "有交叉项：椭圆主轴倾斜")),
        "default_pane_count": 1,
        "case_example_indices": (0, 1),
        "sections": (("definition", "定义"), ("worked_examples", "数学案例")),
    },
    "ch08.principal-axis": {
        "title": "主轴定理",
        "summary": "实对称矩阵可以通过正交变换对角化，二次型因此消去交叉项并转到主轴坐标。",
        "definition": r"""一句话动机：能不能找到一个旋转，让歪的椭圆变正？——能，旋转到特征向量的方向。

本节目标：理解二次型标准化 $=$ 用正交矩阵 $\boldsymbol Q$（由特征向量组成）做正交变换。

**（主轴定理）** 设 $\boldsymbol A$ 是 $n\times n$ 实对称矩阵。则存在正交矩阵 $\boldsymbol Q$，满足 $\boldsymbol Q^{-1}=\boldsymbol Q^{T}$，使得：

$$
\boldsymbol Q^{T}\boldsymbol A\boldsymbol Q
=\boldsymbol D
=\operatorname{diag}(\lambda_1,\lambda_2,\ldots,\lambda_n).
$$

其中 $\lambda_1,\lambda_2,\ldots,\lambda_n$ 是 $\boldsymbol A$ 的特征值，$\boldsymbol Q$ 的列是对应的正交归一化特征向量。

几何上，$y_1$ 轴等于第一个特征向量 $\boldsymbol q_1$ 的方向，是主轴一；$y_2$ 轴等于第二个特征向量 $\boldsymbol q_2$ 的方向，是主轴二。$\lambda_1$ 是沿主轴一的“紧度”系数，$\lambda_2$ 是沿主轴二的“紧度”系数。""",
        "derivation": (r"""做变量替换

$$
\boldsymbol x=\boldsymbol Q\boldsymbol y,
$$

二次型变为标准形：

$$
\begin{aligned}
Q(\boldsymbol x)
&=\boldsymbol x^{T}\boldsymbol A\boldsymbol x\\
&=(\boldsymbol Q\boldsymbol y)^{T}\boldsymbol A(\boldsymbol Q\boldsymbol y)\\
&=\boldsymbol y^{T}(\boldsymbol Q^{T}\boldsymbol A\boldsymbol Q)\boldsymbol y\\
&=\boldsymbol y^{T}\boldsymbol D\boldsymbol y\\
&=\lambda_1y_1^2+\lambda_2y_2^2+\cdots+\lambda_ny_n^2.
\end{aligned}
$$

原始二次型在 $\boldsymbol x$ 坐标中为

$$
Q(x,y)=ax^2+2bxy+cy^2,
$$

有 $xy$ 项，图形是歪的。旋转到特征基后，

$$
\boldsymbol y=\boldsymbol Q^{T}\boldsymbol x,
$$

并且

$$
Q(\boldsymbol y)=\lambda_1y_1^2+\lambda_2y_2^2,
$$

没有 $y_1y_2$ 项，图形变正。""",),
        "examples": (
            {
                "id": "example.ch08.principal-axis.complete",
                "title": "完整计算例题：将倾斜椭圆化为标准形",
                "kind": "determinant",
                "given": [[5, -3], [-3, 5]],
                "result": 16,
                "check": "determinant",
                "lines": (r"""将

$$
Q(x,y)=5x^2+5y^2-6xy
$$

化为标准形，画出图形。

第一步：写出矩阵。

$$
\boldsymbol A=
\begin{pmatrix}
5&-3\\
-3&5
\end{pmatrix}.
$$

第二步：求特征值。

$$
\begin{aligned}
\det(\boldsymbol A-\lambda\boldsymbol I)
&=(5-\lambda)^2-9\\
&=\lambda^2-10\lambda+16=0.
\end{aligned}
$$

$$
\lambda_1=8,\qquad \lambda_2=2.
$$

第三步：求特征向量。

当 $\lambda_1=8$ 时，

$$
\boldsymbol A-8\boldsymbol I=
\begin{pmatrix}
-3&-3\\
-3&-3
\end{pmatrix},
$$

所以

$$
\boldsymbol v_1=t
\begin{pmatrix}
1\\
-1
\end{pmatrix}.
$$

当 $\lambda_2=2$ 时，

$$
\boldsymbol A-2\boldsymbol I=
\begin{pmatrix}
3&-3\\
-3&3
\end{pmatrix},
$$

所以

$$
\boldsymbol v_2=t
\begin{pmatrix}
1\\
1
\end{pmatrix}.
$$

第四步：正交归一化。

$$
\boldsymbol q_1=
\begin{pmatrix}
\frac{1}{\sqrt2}\\
-\frac{1}{\sqrt2}
\end{pmatrix},\qquad
\boldsymbol q_2=
\begin{pmatrix}
\frac{1}{\sqrt2}\\
\frac{1}{\sqrt2}
\end{pmatrix}.
$$

$$
\boldsymbol Q=
\begin{pmatrix}
\frac{1}{\sqrt2}&\frac{1}{\sqrt2}\\
-\frac{1}{\sqrt2}&\frac{1}{\sqrt2}
\end{pmatrix}.
$$

第五步：写出标准形。在特征基坐标 $\boldsymbol y=\boldsymbol Q^{T}\boldsymbol x$ 下：

$$
Q(\boldsymbol y)=8y_1^2+2y_2^2.
$$

$$
Q(\boldsymbol x)=1
\Longrightarrow
8y_1^2+2y_2^2=1
\Longrightarrow
\frac{y_1^2}{\frac18}+\frac{y_2^2}{\frac12}=1.
$$

图形是椭圆。沿 $y_1$ 轴，也就是方向 $(1,-1)$，半轴长度为

$$
\sqrt{\frac18}\approx0.354.
$$

沿 $y_2$ 轴，也就是方向 $(1,1)$，半轴长度为

$$
\sqrt{\frac12}\approx0.707.
$$

特征值与二次型的关系如下：

| 特征值的含义 | 第 7 章（线性变换） | 第 8 章（二次型） |
| --- | --- | --- |
| $\lambda>0$ | 沿该方向拉伸 $\lambda$ 倍 | 该主轴方向的“刚性”系数 |
| $\lambda=0$ | 沿该方向压扁为 $0$ | 该主轴退化为一条线 |
| $\lambda<0$ | 沿该方向拉伸并反向 | $Q(\boldsymbol x)$ 在该方向凹陷（恒为负） |""",),
            },
        ),
        "stages": (("original", "原始倾斜椭圆"), ("axes", "显示两条特征方向"), ("standard", "旋转后得到标准形")),
        "default_pane_count": 3,
        "case_example_indices": (0, 0, 0),
        "sections": (("definition", "定义"), ("derivation", "推导"), ("worked_examples", "数学案例")),
    },
    "ch08.definiteness": {
        "title": "定性：正定、负定、不定",
        "summary": "实对称矩阵特征值的正负决定二次型是正定、负定、不定还是半正定。",
        "definition": r"""一句话动机：看到特征值的正负，就知道图形是椭圆、双曲线还是马鞍面。

本节目标：根据二次型矩阵的特征值正负判断图形的定性。

**（二次型的定性）** 对实对称矩阵 $\boldsymbol A$：

| 条件 | 定性 | 二维图形 | 三维图形 |
| --- | --- | --- | --- |
| 所有 $\lambda>0$ | **正定** | 椭圆 | 椭球（碗） |
| 所有 $\lambda<0$ | **负定** | 无实图形（恒负） | — |
| $\lambda$ 有正有负 | **不定** | 双曲线 | 双曲抛物面（马鞍） |
| 所有 $\lambda\geq0$，至少一个 $\lambda=0$ | **半正定** | 退化为一条线 | 椭圆柱 |
| 有 $\lambda=0$ | **退化** | 两条直线或点 | — |

直观法则：

- 正定 $\Longrightarrow Q(\boldsymbol x)>0$ 对所有非零 $\boldsymbol x$ 成立 $\Longrightarrow$ 图形是凹向上的；
- 不定 $\Longrightarrow Q(\boldsymbol x)$ 在某些方向为正、某些方向为负 $\Longrightarrow$ 鞍面或双曲线。

**（顺序主子式判定法 / Sylvester 准则）** 设 $\boldsymbol A$ 为 $n\times n$ 实对称矩阵，其 $k$ 阶顺序主子式为 $\Delta_k$，即 $\boldsymbol A$ 左上角 $k\times k$ 子矩阵的行列式。则：

$$
\boldsymbol A\text{ 正定}
\Longleftrightarrow
\Delta_k>0,\qquad k=1,2,\ldots,n.
$$

$$
\boldsymbol A\text{ 负定}
\Longleftrightarrow
(-1)^k\Delta_k>0.
$$

也就是正负交替：

$$
\Delta_1<0,\quad \Delta_2>0,\quad \Delta_3<0,\quad\ldots
$$

**（惯性定理 / Sylvester 惯性定律）** 二次型经过任意可逆线性替换化为标准形时，正平方项的个数 $p$（正惯性指数）和负平方项的个数 $q$（负惯性指数）是不变量。$p-q$ 称为符号差。

几何含义：无论怎么变换坐标，图形的类型不变——正定（椭圆）永远是椭圆，不定（双曲线）永远是双曲线。""",
        "derivation": (r"""**（顺序主子式判定法 / Sylvester 准则）**

由主轴定理，存在正交矩阵 $\boldsymbol Q$，使

$$
\boldsymbol Q^{T}\boldsymbol A\boldsymbol Q
=\boldsymbol D
=\operatorname{diag}(\lambda_1,\ldots,\lambda_n).
$$

若 $\boldsymbol A$ 正定，也就是所有 $\lambda_i>0$，则

$$
\det(\boldsymbol A)=\prod_i\lambda_i>0.
$$

对于每个主子矩阵 $\boldsymbol A_k$，考虑向量 $\boldsymbol x$ 只在 $\boldsymbol A_k$ 对应分量上非零时的二次型值，可递推得到各顺序主子式均为正。

反之，若所有顺序主子式 $\Delta_k>0$，可用归纳法配合 Cholesky 分解证明 $\boldsymbol A$ 的所有特征值都大于 $0$。完整证明略。""",),
        "examples": (
            {
                "id": "example.ch08.definiteness.positive",
                "title": "例题 1：正定",
                "kind": "determinant",
                "given": [[1, 0], [0, 2]],
                "result": 2,
                "check": "determinant",
                "lines": (r"""$$
Q_1(x,y)=x^2+2y^2,
$$

对应矩阵为

$$
\boldsymbol A=
\begin{pmatrix}
1&0\\
0&2
\end{pmatrix}.
$$

特征值为 $1,2$，都为正，所以二次型正定，$Q_1(x,y)=1$ 是椭圆。""",),
            },
            {
                "id": "example.ch08.definiteness.negative",
                "title": "按定义补充：负定",
                "kind": "determinant",
                "given": [[-1, 0], [0, -2]],
                "result": 2,
                "check": "determinant",
                "lines": (r"""取

$$
Q(x,y)=-x^2-2y^2,
$$

对应矩阵为

$$
\boldsymbol A=
\begin{pmatrix}
-1&0\\
0&-2
\end{pmatrix}.
$$

特征值为 $-1,-2$，都为负，所以二次型负定。因为 $Q(x,y)$ 恒为负，$Q(x,y)=1$ 没有实图形。""",),
            },
            {
                "id": "example.ch08.definiteness.indefinite",
                "title": "例题 2：不定",
                "kind": "determinant",
                "given": [[1, 0], [0, -1]],
                "result": -1,
                "check": "determinant",
                "lines": (r"""$$
Q_2(x,y)=x^2-y^2,
$$

对应矩阵为

$$
\boldsymbol A=
\begin{pmatrix}
1&0\\
0&-1
\end{pmatrix}.
$$

特征值为 $1,-1$，一正一负，所以二次型不定，$Q_2(x,y)=1$ 是双曲线。""",),
            },
            {
                "id": "example.ch08.definiteness.semidefinite",
                "title": "例题 3：半正定",
                "kind": "determinant",
                "given": [[1, 1], [1, 1]],
                "result": 0,
                "check": "determinant",
                "lines": (r"""$$
Q_3(x,y)=(x+y)^2=x^2+2xy+y^2,
$$

对应矩阵为

$$
\boldsymbol A=
\begin{pmatrix}
1&1\\
1&1
\end{pmatrix}.
$$

特征值为 $2,0$，所以二次型半正定，零等值集退化为一条直线。""",),
            },
            {
                "id": "example.ch08.definiteness.sylvester",
                "title": "例 9：Sylvester 判定",
                "kind": "determinant",
                "given": [[2, 1, 0], [1, 3, -1], [0, -1, 2]],
                "result": 8,
                "check": "determinant",
                "lines": (r"""判断

$$
\boldsymbol A=
\begin{pmatrix}
2&1&0\\
1&3&-1\\
0&-1&2
\end{pmatrix}
$$

的定性。

$$
\Delta_1=2>0.
$$

$$
\Delta_2=
\det\begin{pmatrix}
2&1\\
1&3
\end{pmatrix}
=6-1=5>0.
$$

$$
\begin{aligned}
\Delta_3
&=\det(\boldsymbol A)\\
&=2(3\cdot2-1)-1(1\cdot2-0)+0\\
&=2\cdot5-1\cdot2=8>0.
\end{aligned}
$$

所有顺序主子式都大于 $0$，所以 $\boldsymbol A$ 正定。""",),
            },
            {
                "id": "example.ch08.definiteness.completing-square",
                "title": "例 10：配方法与惯性定理",
                "kind": "determinant",
                "given": [[1, 1, 0], [1, 2, 1], [0, 1, 3]],
                "result": 2,
                "check": "determinant",
                "lines": (r"""用配方法将

$$
Q(x,y,z)=x^2+2xy+2y^2+2yz+3z^2
$$

化为标准形，并确定其定性。

$$
\begin{aligned}
Q
&=(x^2+2xy+y^2)+(y^2+2yz+z^2)+2z^2\\
&=(x+y)^2+(y+z)^2+2z^2.
\end{aligned}
$$

令

$$
u=x+y,\qquad v=y+z,\qquad w=z,
$$

则

$$
Q=u^2+v^2+2w^2.
$$

三个平方项系数全为正，所以二次型正定。惯性定理保证无论用什么方法化标准形，正项个数，也就是正惯性指数，都不变。""",),
            },
        ),
        "stages": (("positive", "正定：椭圆"), ("negative", "负定：单位正等值集为空"), ("indefinite", "不定：双曲线"), ("semidefinite", "半正定：零等值集退化为直线")),
        "default_pane_count": 1,
        "case_example_indices": (0, 1, 2, 3),
        "sections": (("definition", "定义"), ("derivation", "推导"), ("worked_examples", "数学案例")),
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
        "checks": [{"name": str(spec["check"]), "expected": deepcopy(spec["result"]), "tolerance": 1e-9}],
        "claim_refs": [claim_id],
    }


def refine_chapter_08_topic(topic_id: str, payload: dict[str, Any], explanation: dict[str, Any], visual: dict[str, Any]) -> None:
    """Replace the generic Chapter 8 prose with the reviewed lecture content."""

    spec = CONTENT[topic_id]
    claim_id = f"claim.{topic_id}"
    examples = [_worked_example(item, claim_id) for item in spec["examples"]]
    explanation.update({
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
            str(spec["title"]), str(spec["summary"]), str(spec["definition"]),
            *spec["derivation"], *[line for item in spec["examples"] for line in item["lines"]],
        ],
    })
    for key in ("intuition", "pitfalls", "connections", "analogy_boundary", "transfer_note", "read_guide", "conclusion"):
        explanation.pop(key, None)

    stages = {stage["id"].rsplit(".", 1)[-1]: stage for stage in visual["stages"]}
    ordered_stages = []
    for stage_name, purpose in spec["stages"]:
        stage = stages[stage_name]
        stage.update({"title": purpose, "caption": "", "layout": "overlay"})
        ordered_stages.append(stage)
    visual["stages"] = ordered_stages

    explanation["case_layout"] = {
        "default_pane_count": int(spec["default_pane_count"]),
        "cases": [{
            "id": f"case.{topic_id}.{index}",
            "topic_id": topic_id,
            "example_ref": examples[example_index]["id"],
            "claim_refs": [claim_id],
            "stage_refs": [stage["id"]],
            "purpose": purpose,
        } for index, ((_, purpose), stage, example_index) in enumerate(
            zip(spec["stages"], ordered_stages, spec["case_example_indices"]), start=1
        )],
    }

    claim = payload["claims"][0]
    claim.update({
        "statement": str(spec["summary"]),
        "formula": CLAIM_FORMULAS[topic_id],
        "formula_symbols": [entity["role"] for entity in visual["entities"]],
        "explanation_refs": [section_id for section_id, _ in spec["sections"]],
        "entity_refs": [entity["id"] for entity in visual["entities"]],
        "relation_refs": [relation["id"] for relation in visual["relations"]],
        "stage_refs": [stage["id"] for stage in ordered_stages],
    })
    payload["connections"] = []


__all__ = ["CONTENT", "refine_chapter_08_topic"]
