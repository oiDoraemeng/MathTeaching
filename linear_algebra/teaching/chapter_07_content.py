"""Reviewed lecture content and case layouts for Chapter 7 sections 7.1--7.4."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


CLAIM_FORMULAS = {
    "ch07.eigen.direction": r"\boldsymbol A\boldsymbol v=\lambda\boldsymbol v",
    "ch07.characteristic-polynomial": r"p(\lambda)=\det(\boldsymbol A-\lambda\boldsymbol I)=0",
    "ch07.eigenspace": r"E_\lambda=\operatorname{Null}(\boldsymbol A-\lambda\boldsymbol I)",
    "ch07.diagonalization": r"\boldsymbol A=\boldsymbol P\boldsymbol D\boldsymbol P^{-1}",
}


CONTENT: dict[str, dict[str, Any]] = {
    "ch07.eigen.direction": {
        "title": "特征值与特征向量",
        "summary": "有些方向的线段经过变换后只改变长度而不改变方向，这些方向就是特征方向。",
        "definition": r"""**（特征值与特征向量）** 设 $\boldsymbol A$ 是一个 $n\times n$ 矩阵。如果存在非零向量 $\boldsymbol v$ 和标量 $\lambda$，使得

$$
\boldsymbol A\boldsymbol v=\lambda\boldsymbol v,
$$

则称 $\lambda$ 为 $\boldsymbol A$ 的一个特征值，$\boldsymbol v$ 为对应的特征向量。

核心含义：$\boldsymbol A$ 作用在 $\boldsymbol v$ 上，效果仅仅是把 $\boldsymbol v$ 拉长或缩短 $\lambda$ 倍。$\lambda>0$ 时方向不变，$\lambda<0$ 时反向，$\lambda=0$ 时消失。

**（特征空间）** 对应特征值 $\lambda$ 的所有特征向量加上零向量构成一个向量子空间，称为 $\lambda$ 的特征空间：

$$
E_\lambda
=\{\boldsymbol v\mid \boldsymbol A\boldsymbol v=\lambda\boldsymbol v\}
=\operatorname{Null}(\boldsymbol A-\lambda\boldsymbol I).
$$""",
        "derivation": (),
        "examples": (
            {
                "id": "example.ch07.eigen.direction.stretch",
                "title": "几何直觉例 1：拉伸变换",
                "kind": "matrix_transform",
                "given": [[[2, 0], [0, 1]], [1, 0]],
                "result": [2, 0],
                "check": "transformed",
                "lines": (r"""取拉伸变换

$$
\boldsymbol A=
\begin{pmatrix}
2&0\\
0&1
\end{pmatrix},
$$

即横轴方向拉伸为原来的 $2$ 倍，纵轴方向不变。对于

$$
\boldsymbol v_1=
\begin{pmatrix}
1\\
0
\end{pmatrix},
$$

变换后

$$
\boldsymbol A\boldsymbol v_1
=\begin{pmatrix}
2\\
0
\end{pmatrix}
=2\begin{pmatrix}
1\\
0
\end{pmatrix},
$$

所以 $\lambda=2$，方向不变。对于

$$
\boldsymbol v_2=
\begin{pmatrix}
0\\
1
\end{pmatrix},
$$

变换后

$$
\boldsymbol A\boldsymbol v_2
=\begin{pmatrix}
0\\
1
\end{pmatrix}
=1\begin{pmatrix}
0\\
1
\end{pmatrix},
$$

所以 $\lambda=1$，向量完全不变。""",),
            },
            {
                "id": "example.ch07.eigen.direction.projection",
                "title": "几何直觉例 2：投影到横轴",
                "kind": "matrix_transform",
                "given": [[[1, 0], [0, 0]], [0, 1]],
                "result": [0, 0],
                "check": "transformed",
                "lines": (r"""取投影到横轴的矩阵

$$
\boldsymbol A=
\begin{pmatrix}
1&0\\
0&0
\end{pmatrix}.
$$

横轴方向满足

$$
\boldsymbol A
\begin{pmatrix}
1\\
0
\end{pmatrix}
=\begin{pmatrix}
1\\
0
\end{pmatrix},
$$

所以对应 $\lambda=1$。纵轴方向满足

$$
\boldsymbol A
\begin{pmatrix}
0\\
1
\end{pmatrix}
=\begin{pmatrix}
0\\
0
\end{pmatrix},
$$

所以对应 $\lambda=0$，这个方向消失了。

特征值 $\lambda=0$ 的含义是这个方向上的向量被压没了，即 $\boldsymbol v\in\operatorname{Null}(\boldsymbol A)$。特征值 $0$ 对应的特征空间就是零空间。""",),
            },
            {
                "id": "example.ch07.eigen.direction.rotation",
                "title": "几何直觉例 3：旋转 90 度",
                "kind": "matrix_transform",
                "given": [[[0, -1], [1, 0]], [1, 0]],
                "result": [0, 1],
                "check": "transformed",
                "lines": (r"""取旋转 $90^\circ$ 的矩阵

$$
\boldsymbol A=
\begin{pmatrix}
0&-1\\
1&0
\end{pmatrix}.
$$

几何上，旋转 $90^\circ$ 后，没有任何非零方向还指着原来的方向。因此在实数范围内，旋转 $90^\circ$ 没有实特征向量。

几何直觉总结如下：

| 变换 | 特征向量（哪些方向不变） | 特征值 |
| --- | --- | --- |
| 均匀放大 $2$ 倍 | **所有方向** | 全部为 $2$ |
| 横轴拉伸 $2$ 倍，纵轴不变 | 横轴方向、纵轴方向 | $2,1$ |
| 投影到横轴 | 横轴方向不变，纵轴方向消失 | $1,0$ |
| 旋转 $90^\circ$ | 无 | 无实特征值 |
| 关于原点反射 | 所有方向反向 | $-1$ |""",),
            },
            {
                "id": "example.ch07.eigen.direction.reflection",
                "title": "理解层例 1–2：关于直线 y=x 反射",
                "kind": "matrix_transform",
                "given": [[[0, 1], [1, 0]], [1, -1]],
                "result": [-1, 1],
                "check": "transformed",
                "lines": (r"""取

$$
\boldsymbol A=
\begin{pmatrix}
0&1\\
1&0
\end{pmatrix},
$$

它表示关于直线 $y=x$ 的反射。对于

$$
\boldsymbol v_1=
\begin{pmatrix}
1\\
1
\end{pmatrix},
$$

有

$$
\boldsymbol A\boldsymbol v_1
=\begin{pmatrix}
1\\
1
\end{pmatrix}
=\boldsymbol v_1,
$$

所以 $\boldsymbol v_1$ 是特征向量，$\lambda=1$。

对于

$$
\boldsymbol v_2=
\begin{pmatrix}
1\\
-1
\end{pmatrix},
$$

有

$$
\boldsymbol A\boldsymbol v_2
=\begin{pmatrix}
-1\\
1
\end{pmatrix}
=-\begin{pmatrix}
1\\
-1
\end{pmatrix},
$$

所以 $\lambda=-1$。""",),
            },
            {
                "id": "example.ch07.eigen.direction.not-eigenvector",
                "title": "计算层例 3：验证一个向量不是特征向量",
                "kind": "matrix_transform",
                "given": [[[1, 4], [2, 3]], [2, 1]],
                "result": [6, 7],
                "check": "transformed",
                "lines": (r"""验证

$$
\boldsymbol v=
\begin{pmatrix}
2\\
1
\end{pmatrix}
$$

是否为

$$
\boldsymbol A=
\begin{pmatrix}
1&4\\
2&3
\end{pmatrix}
$$

的特征向量。计算得

$$
\boldsymbol A\boldsymbol v
=\begin{pmatrix}
6\\
7
\end{pmatrix}.
$$

不存在标量 $k$ 使

$$
\begin{pmatrix}
6\\
7
\end{pmatrix}
=k\begin{pmatrix}
2\\
1
\end{pmatrix},
$$

所以 $\boldsymbol v$ 不是特征向量。""",),
            },
            {
                "id": "example.ch07.eigen.direction.projection-spaces",
                "title": "补充例 4：投影矩阵的特征值与特征向量",
                "kind": "determinant",
                "given": [[1, 0], [0, 0]],
                "result": 0,
                "check": "determinant",
                "lines": (r"""对于投影到横轴的矩阵

$$
\boldsymbol A=
\begin{pmatrix}
1&0\\
0&0
\end{pmatrix},
$$

特征值 $\lambda=1$ 对应横轴上的向量不变，特征值 $\lambda=0$ 对应纵轴被压扁。特征空间为

$$
E_1=\operatorname{span}\left\{
\begin{pmatrix}
1\\
0
\end{pmatrix}
\right\},\qquad
E_0=\operatorname{span}\left\{
\begin{pmatrix}
0\\
1
\end{pmatrix}
\right\}.
$$

$\lambda=0$ 对应的特征空间恰好等于 $\operatorname{Null}(\boldsymbol A)$，$\lambda=1$ 对应的特征空间是投影的目标线。""",),
            },
            {
                "id": "example.ch07.eigen.direction.diagonal",
                "title": "补充例 5：对角矩阵的特征值",
                "kind": "determinant",
                "given": [[4, 0, 0], [0, 7, 0], [0, 0, -2]],
                "result": -56,
                "check": "determinant",
                "lines": (r"""取

$$
\boldsymbol A=
\begin{pmatrix}
4&0&0\\
0&7&0\\
0&0&-2
\end{pmatrix}.
$$

可以直接读出特征值

$$
\lambda_1=4,\qquad \lambda_2=7,\qquad \lambda_3=-2.
$$

对应的特征向量分别为

$$
\boldsymbol e_1=
\begin{pmatrix}
1\\
0\\
0
\end{pmatrix},\qquad
\boldsymbol e_2=
\begin{pmatrix}
0\\
1\\
0
\end{pmatrix},\qquad
\boldsymbol e_3=
\begin{pmatrix}
0\\
0\\
1
\end{pmatrix}.
$$

对角矩阵的特征向量就是标准基。""",),
            },
            {
                "id": "example.ch07.eigen.direction.triangular",
                "title": "补充例 6：三角矩阵的特征值",
                "kind": "determinant",
                "given": [[3, 5, -1], [0, -2, 4], [0, 0, 1]],
                "result": -6,
                "check": "determinant",
                "lines": (r"""取三角矩阵

$$
\boldsymbol A=
\begin{pmatrix}
3&5&-1\\
0&-2&4\\
0&0&1
\end{pmatrix}.
$$

三角矩阵的特征值就是对角线元素：

$$
\lambda=3,-2,1.
$$

对三角矩阵，

$$
\det(\boldsymbol A-\lambda\boldsymbol I)
=(a_{11}-\lambda)(a_{22}-\lambda)\cdots(a_{nn}-\lambda),
$$

所以对角线元素就是特征值。""",),
            },
        ),
        "stages": (("stretch", "拉伸：方向保持与方向改变"), ("projection", "投影：一个方向不变，一个方向消失"), ("rotation", "旋转 90 度：没有实特征方向"), ("reflection", "关于 y=x 反射：一个方向不变，一个方向反向")),
        "default_pane_count": 1,
        "case_example_indices": (0, 1, 2, 3),
        "sections": (("definition", "定义"), ("worked_examples", "数学案例")),
    },
    "ch07.characteristic-polynomial": {
        "title": "特征多项式",
        "summary": "用特征方程求出矩阵的全部特征值。",
        "definition": r"""**（特征方程与特征多项式）**

$$
p(\lambda)=\det(\boldsymbol A-\lambda\boldsymbol I)=0
$$

称为 $\boldsymbol A$ 的特征方程。$p(\lambda)$ 是一个关于 $\lambda$ 的 $n$ 次多项式，它的根就是 $\boldsymbol A$ 的特征值。

几何翻译：$\det(\boldsymbol A-\lambda\boldsymbol I)=0$ 在寻找一个 $\lambda$，使得变换 $\boldsymbol A-\lambda\boldsymbol I$ 把某些方向压扁。行列式等于 $0$ 表示面积消失，这些被压扁的方向上的向量就是特征向量。""",
        "derivation": (r"""要求非零向量 $\boldsymbol v$ 满足

$$
\boldsymbol A\boldsymbol v=\lambda\boldsymbol v.
$$

移项得到

$$
\boldsymbol A\boldsymbol v-\lambda\boldsymbol v=\boldsymbol 0.
$$

$\lambda$ 是标量，乘单位矩阵后可以与矩阵 $\boldsymbol A$ 相减：

$$
\boldsymbol A\boldsymbol v-\lambda\boldsymbol I\boldsymbol v=\boldsymbol 0.
$$

因此

$$
(\boldsymbol A-\lambda\boldsymbol I)\boldsymbol v=\boldsymbol 0.
$$

由齐次方程组的知识，$(\boldsymbol A-\lambda\boldsymbol I)\boldsymbol v=\boldsymbol 0$ 有非零解，当且仅当

$$
\det(\boldsymbol A-\lambda\boldsymbol I)=0.
$$""",),
        "examples": (
            {
                "id": "example.ch07.characteristic-polynomial.real",
                "title": "例 1：求两个实特征值",
                "kind": "determinant",
                "given": [[2, 1], [1, 2]],
                "result": 3,
                "check": "determinant",
                "lines": (r"""取

$$
\boldsymbol A=
\begin{pmatrix}
2&1\\
1&2
\end{pmatrix}.
$$

则

$$
\boldsymbol A-\lambda\boldsymbol I
=\begin{pmatrix}
2-\lambda&1\\
1&2-\lambda
\end{pmatrix}.
$$

特征方程为

$$
\begin{aligned}
\det(\boldsymbol A-\lambda\boldsymbol I)
&=(2-\lambda)^2-1\\
&=\lambda^2-4\lambda+3\\
&=(\lambda-3)(\lambda-1)=0.
\end{aligned}
$$

所以

$$
\lambda_1=3,\qquad \lambda_2=1.
$$

几何翻译：这个变换在一个方向上拉伸 $3$ 倍，在另一个方向上拉伸 $1$ 倍。""",),
            },
            {
                "id": "example.ch07.characteristic-polynomial.complex",
                "title": "例 2：没有实特征值",
                "kind": "determinant",
                "given": [[1, -1], [1, 1]],
                "result": 2,
                "check": "determinant",
                "lines": (r"""取

$$
\boldsymbol A=
\begin{pmatrix}
1&-1\\
1&1
\end{pmatrix}.
$$

它的特征方程为

$$
\begin{aligned}
\det(\boldsymbol A-\lambda\boldsymbol I)
&=(1-\lambda)^2+1\\
&=\lambda^2-2\lambda+2=0.
\end{aligned}
$$

判别式为

$$
\Delta=4-8=-4<0,
$$

所以没有实特征值，但有两个共轭复特征值

$$
\lambda=1\pm i.
$$""",),
            },
        ),
        "stages": (("real", "例 1：两个实特征值"), ("complex", "例 2：没有实特征值")),
        "default_pane_count": 1,
        "case_example_indices": (0, 1),
        "sections": (("definition", "定义"), ("derivation", "推导"), ("worked_examples", "数学案例")),
    },
    "ch07.eigenspace": {
        "title": "求特征向量",
        "summary": "对每个特征值求齐次方程组的零空间，得到对应的特征空间。",
        "definition": r"""本节目标：对每个 $\lambda$，解

$$
(\boldsymbol A-\lambda\boldsymbol I)\boldsymbol v=\boldsymbol 0
$$

求出对应的特征空间。

方法：对每个特征值 $\lambda$，解齐次方程组 $(\boldsymbol A-\lambda\boldsymbol I)\boldsymbol v=\boldsymbol 0$。

- 代入 $\lambda$，得到矩阵 $\boldsymbol A-\lambda\boldsymbol I$；
- 用高斯消元解方程 $(\boldsymbol A-\lambda\boldsymbol I)\boldsymbol v=\boldsymbol 0$；
- 得到 $\operatorname{Null}(\boldsymbol A-\lambda\boldsymbol I)$ 的一组基，这就是 $\lambda$ 对应的特征空间。

**（特征值的乘积与行列式）**

$$
\det(\boldsymbol A)=\lambda_1\lambda_2\cdots\lambda_n.
$$

几何含义：所有特征值的乘积等于行列式的值。行列式等于各方向缩放倍数的乘积，也就是变换后体积的放大率。

**（特征值的和与迹）**

$$
\operatorname{tr}(\boldsymbol A)=\lambda_1+\lambda_2+\cdots+\lambda_n,
$$

其中

$$
\operatorname{tr}(\boldsymbol A)=\sum_i a_{ii}
$$

是对角线元素之和。

**（不同特征值对应的特征向量线性无关）** 设 $\lambda_1,\ldots,\lambda_k$ 是 $\boldsymbol A$ 的两两不同的特征值，$\boldsymbol v_1,\ldots,\boldsymbol v_k$ 是对应的特征向量，则 $\boldsymbol v_1,\ldots,\boldsymbol v_k$ 线性无关。

推论：若 $n\times n$ 矩阵有 $n$ 个不同的特征值，则它一定可以对角化，因为它有 $n$ 个线性无关的特征向量。

**（代数重数与几何重数）** 设 $\lambda_0$ 是 $\boldsymbol A$ 的特征值：

- 代数重数 $m_a(\lambda_0)$ 是 $\lambda_0$ 作为特征多项式根的重复次数；
- 几何重数

$$
m_g(\lambda_0)
=\dim(E_{\lambda_0})
=\dim\operatorname{Null}(\boldsymbol A-\lambda_0\boldsymbol I),
$$

即对应特征空间的维数。

**（重数关系）** 对每个特征值 $\lambda_0$，都有

$$
1\leq m_g(\lambda_0)\leq m_a(\lambda_0).
$$

矩阵 $\boldsymbol A$ 可对角化，当且仅当对所有特征值都有 $m_g=m_a$。若存在某个特征值满足 $m_g<m_a$，则该矩阵不能对角化，因为特征向量不够 $n$ 个。""",
        "derivation": (
            r"""**（特征值的乘积与行列式）**

特征多项式为

$$
p(\lambda)
=\det(\boldsymbol A-\lambda\boldsymbol I)
=(-1)^n\lambda^n+(-1)^{n-1}\operatorname{tr}(\boldsymbol A)\lambda^{n-1}+\cdots+\det(\boldsymbol A).
$$

另一方面，若 $\lambda_1,\ldots,\lambda_n$ 是特征值并计算重数，则

$$
p(\lambda)
=(-1)^n(\lambda-\lambda_1)(\lambda-\lambda_2)\cdots(\lambda-\lambda_n).
$$

比较常数项：

$$
\begin{aligned}
p(0)
&=\det(\boldsymbol A)\\
&=(-1)^n(-\lambda_1)(-\lambda_2)\cdots(-\lambda_n)\\
&=\lambda_1\lambda_2\cdots\lambda_n.
\end{aligned}
$$""",
            r"""**（特征值的和与迹）**

$p(\lambda)=\det(\boldsymbol A-\lambda\boldsymbol I)$ 展开后，$\lambda^{n-1}$ 的系数为

$$
(-1)^{n-1}(a_{11}+\cdots+a_{nn})
=(-1)^{n-1}\operatorname{tr}(\boldsymbol A).
$$

同时，

$$
(-1)^n(\lambda-\lambda_1)\cdots(\lambda-\lambda_n)
$$

展开后，$\lambda^{n-1}$ 的系数为

$$
(-1)^{n-1}(\lambda_1+\cdots+\lambda_n).
$$

比较两个系数可得

$$
\operatorname{tr}(\boldsymbol A)=\lambda_1+\cdots+\lambda_n.
$$""",
            r"""**（不同特征值对应的特征向量线性无关）**

用数学归纳法证明。当 $k=1$ 时，非零向量自身线性无关。

假设结论对 $k-1$ 个向量成立。若

$$
c_1\boldsymbol v_1+\cdots+c_k\boldsymbol v_k=\boldsymbol 0,
$$

两边左乘 $\boldsymbol A-\lambda_k\boldsymbol I$，得到

$$
c_1(\lambda_1-\lambda_k)\boldsymbol v_1
+\cdots+
c_{k-1}(\lambda_{k-1}-\lambda_k)\boldsymbol v_{k-1}
+c_k\boldsymbol 0
=\boldsymbol 0.
$$

由归纳假设，$\boldsymbol v_1,\ldots,\boldsymbol v_{k-1}$ 线性无关，所以

$$
c_i(\lambda_i-\lambda_k)=0.
$$

又因为 $\lambda_i\neq\lambda_k$，所以

$$
c_1=\cdots=c_{k-1}=0.
$$

代回原式得

$$
c_k\boldsymbol v_k=\boldsymbol 0,
$$

因此 $c_k=0$。全部系数均为零，所以 $\boldsymbol v_1,\ldots,\boldsymbol v_k$ 线性无关。""",
        ),
        "examples": (
            {
                "id": "example.ch07.eigenspace.solve",
                "title": "例题：求两个特征空间",
                "kind": "matrix_transform",
                "given": [[[-1, 1], [1, -1]], [1, 1]],
                "result": [0, 0],
                "check": "transformed",
                "lines": (r"""沿用 7.2 例 1：

$$
\boldsymbol A=
\begin{pmatrix}
2&1\\
1&2
\end{pmatrix},\qquad
\lambda_1=3,\qquad \lambda_2=1.
$$

当 $\lambda_1=3$ 时，

$$
\boldsymbol A-3\boldsymbol I
=\begin{pmatrix}
-1&1\\
1&-1
\end{pmatrix}.
$$

方程 $-x+y=0$ 给出 $y=x$，所以

$$
\boldsymbol v_1=t
\begin{pmatrix}
1\\
1
\end{pmatrix}.
$$

当 $\lambda_2=1$ 时，

$$
\boldsymbol A-\boldsymbol I
=\begin{pmatrix}
1&1\\
1&1
\end{pmatrix}.
$$

方程 $x+y=0$ 给出 $y=-x$，所以

$$
\boldsymbol v_2=t
\begin{pmatrix}
1\\
-1
\end{pmatrix}.
$$""",),
            },
            {
                "id": "example.ch07.eigenspace.defective",
                "title": "例 7：不可对角化的矩阵",
                "kind": "matrix_transform",
                "given": [[[0, 1], [0, 0]], [1, 0]],
                "result": [0, 0],
                "check": "transformed",
                "lines": (r"""取

$$
\boldsymbol A=
\begin{pmatrix}
1&1\\
0&1
\end{pmatrix}.
$$

$\lambda=1$ 是二重根，所以

$$
m_a=2.
$$

而

$$
\boldsymbol A-\boldsymbol I
=\begin{pmatrix}
0&1\\
0&0
\end{pmatrix}
$$

的秩为 $1$，零空间维数为 $1$，所以

$$
m_g=1.
$$

由于 $m_g<m_a$，只有一个线性无关的特征向量，矩阵不能对角化。

几何含义：这个变换是水平切变，只有一个方向上的向量保持不变方向。""",),
            },
            {
                "id": "example.ch07.eigenspace.invariants",
                "title": "例 8：验证特征值的乘积、和与正交性",
                "kind": "determinant",
                "given": [[2, 1], [1, 2]],
                "result": 3,
                "check": "determinant",
                "lines": (r"""取

$$
\boldsymbol A=
\begin{pmatrix}
2&1\\
1&2
\end{pmatrix},\qquad
\lambda_1=3,\qquad \lambda_2=1.
$$

行列式满足

$$
\det(\boldsymbol A)=3=\lambda_1\lambda_2.
$$

迹满足

$$
\operatorname{tr}(\boldsymbol A)=4=\lambda_1+\lambda_2.
$$

对应的特征向量

$$
\boldsymbol v_1=
\begin{pmatrix}
1\\
1
\end{pmatrix},\qquad
\boldsymbol v_2=
\begin{pmatrix}
1\\
-1
\end{pmatrix}
$$

互相垂直。这不是巧合，对称矩阵的所有不同特征值对应的特征向量一定正交。""",),
            },
        ),
        "stages": (("eigenspaces", "两个特征值对应两个特征空间"), ("defective", "例 7：切变矩阵不能对角化"), ("invariants", "例 8：用特征值验证行列式与迹")),
        "default_pane_count": 1,
        "case_example_indices": (0, 1, 2),
        "sections": (("definition", "定义"), ("derivation", "推导与证明"), ("worked_examples", "数学案例")),
    },
    "ch07.diagonalization": {
        "title": "对角化的几何意义",
        "summary": "以特征向量为新基，线性变换就变成沿各特征方向的独立缩放。",
        "definition": r"""**（对角化）** 若 $n\times n$ 矩阵 $\boldsymbol A$ 有 $n$ 个线性无关的特征向量 $\boldsymbol v_1,\ldots,\boldsymbol v_n$，对应特征值为 $\lambda_1,\ldots,\lambda_n$，则

$$
\boldsymbol A=\boldsymbol P\boldsymbol D\boldsymbol P^{-1},
$$

其中

$$
\boldsymbol P=
\begin{pmatrix}
\vert&\vert&&\vert\\
\boldsymbol v_1&\boldsymbol v_2&\cdots&\boldsymbol v_n\\
\vert&\vert&&\vert
\end{pmatrix},
$$

即特征向量按列排列，并且

$$
\boldsymbol D=
\begin{pmatrix}
\lambda_1&0&\cdots&0\\
0&\lambda_2&\cdots&0\\
\vdots&\vdots&\ddots&\vdots\\
0&0&\cdots&\lambda_n
\end{pmatrix}.
$$

等价地，

$$
\boldsymbol P^{-1}\boldsymbol A\boldsymbol P=\boldsymbol D.
$$

三步走直觉：在标准基下看，$\boldsymbol A$ 的各方向纠缠在一起；在特征基下看，可以分成三步。

第一步，换到特征基：

$$
\boldsymbol y=\boldsymbol P^{-1}\boldsymbol x,
$$

即用特征向量当尺子量 $\boldsymbol x$。

第二步，独立缩放：

$$
\boldsymbol D\boldsymbol y
=\begin{pmatrix}
\lambda_1y_1\\
\vdots\\
\lambda_ny_n
\end{pmatrix}.
$$

第三步，换回标准基：

$$
\boldsymbol P\boldsymbol D\boldsymbol y
=\boldsymbol A\boldsymbol x.
$$

核心：在特征基下，$\boldsymbol A$ 只是各方向独立的缩放，没有任何交叉。""",
        "derivation": (),
        "examples": (
            {
                "id": "example.ch07.diagonalization.verify",
                "title": "例题：验证对角化",
                "kind": "matrix_product",
                "given": [[[0.5, 0.5], [0.5, -0.5]], [[3, 1], [3, -1]]],
                "result": [[3, 0], [0, 1]],
                "check": "result",
                "lines": (r"""取

$$
\boldsymbol A=
\begin{pmatrix}
2&1\\
1&2
\end{pmatrix},
$$

$$
\boldsymbol P=
\begin{pmatrix}
1&1\\
1&-1
\end{pmatrix},\qquad
\boldsymbol D=
\begin{pmatrix}
3&0\\
0&1
\end{pmatrix},
$$

并且

$$
\boldsymbol P^{-1}
=\frac12
\begin{pmatrix}
1&1\\
1&-1
\end{pmatrix}.
$$

验证得

$$
\begin{aligned}
\boldsymbol P^{-1}\boldsymbol A\boldsymbol P
&=\frac12
\begin{pmatrix}
1&1\\
1&-1
\end{pmatrix}
\begin{pmatrix}
2&1\\
1&2
\end{pmatrix}
\begin{pmatrix}
1&1\\
1&-1
\end{pmatrix}\\
&=
\begin{pmatrix}
3&0\\
0&1
\end{pmatrix}
=\boldsymbol D.
\end{aligned}
$$""",),
            },
        ),
        "stages": (("change_basis", "第一步：换到特征基"), ("diagonal_scale", "第二步：沿特征方向独立缩放"), ("change_basis_back", "第三步：换回标准基")),
        "default_pane_count": 3,
        "case_example_indices": (0, 0, 0),
        "sections": (("definition", "定义"), ("worked_examples", "数学案例")),
    },
}


def _worked_example(spec: dict[str, Any], claim_id: str) -> dict[str, Any]:
    return {
        "id": str(spec["id"]), "title": str(spec["title"]), "kind": str(spec["kind"]),
        "given": deepcopy(spec["given"]), "calculation": list(spec["lines"]),
        "result": deepcopy(spec["result"]),
        "checks": [{"name": str(spec["check"]), "expected": deepcopy(spec["result"]), "tolerance": 1e-9}],
        "claim_refs": [claim_id],
    }


_EIGEN_DIRECTION_DEFINITION = r"""**（特征值与特征向量）** 设 $\boldsymbol A$ 是一个 $n \times n$ 矩阵。如果存在非零向量 $\boldsymbol v$ 和标量 $\lambda$，使得：

$$
\boldsymbol A \cdot \boldsymbol v = \lambda \cdot \boldsymbol v
$$

则称 $\lambda$ 为 $\boldsymbol A$ 的一个特征值（Eigenvalue），$\boldsymbol v$ 为对应的特征向量（Eigenvector）。

核心含义：$\boldsymbol A$ 作用在 $\boldsymbol v$ 上，效果仅仅是“把 $\boldsymbol v$ 拉长或缩短 $\lambda$ 倍”——方向不变（$\lambda>0$）、反向（$\lambda<0$），或消失（$\lambda=0$）。

**（特征空间）** 对应特征值 $\lambda$ 的所有特征向量（加上零向量）构成一个向量子空间，称为 $\lambda$ 的特征空间：

$$
E_{\lambda} = \{\boldsymbol v \mid \boldsymbol A\boldsymbol v = \lambda\boldsymbol v\} = \operatorname{Null}(\boldsymbol A - \lambda\boldsymbol I)
$$

**几何直觉（先看图）**

例1：拉伸变换

$$
\boldsymbol A = \begin{pmatrix}
2 & 0\\
0 & 1
\end{pmatrix}
$$

（$x$ 方向拉 $2$ 倍，$y$ 不变）

$$
\boldsymbol v_{1} = \begin{pmatrix}
1\\
0
\end{pmatrix}
$$

变换后

$$
\boldsymbol A \cdot \boldsymbol v_{1} = \begin{pmatrix}
2\\
0
\end{pmatrix}=2\begin{pmatrix}
1\\
0
\end{pmatrix}
$$

所以 $\lambda=2$，方向不变。对于

$$
\boldsymbol v_{2} = \begin{pmatrix}
0\\
1
\end{pmatrix}
$$

变换后

$$
\boldsymbol A \cdot \boldsymbol v_{2} = \begin{pmatrix}
0\\
1
\end{pmatrix}=1\begin{pmatrix}
0\\
1
\end{pmatrix}
$$

所以 $\lambda=1$，完全不变。

例2：投影到 $x$ 轴

$$
\boldsymbol A = \begin{pmatrix}
1 & 0\\
0 & 0
\end{pmatrix}
$$

$$
\boldsymbol v_{1} = \begin{pmatrix}
1\\
0
\end{pmatrix},\qquad \boldsymbol A \cdot \boldsymbol v_{1} = \begin{pmatrix}
1\\
0
\end{pmatrix}
$$

投影到自己，$\lambda=1$。对于

$$
\boldsymbol v_{2} = \begin{pmatrix}
0\\
1
\end{pmatrix}
$$

投影到

$$
\boldsymbol A \cdot \boldsymbol v_{2} = \begin{pmatrix}
0\\
0
\end{pmatrix}
$$

$\rightarrow \lambda=0$（方向消失了！）

特征值 $\lambda=0$ 的含义：这个方向上的向量被"压没了"——$\boldsymbol v \in \operatorname{Null}(\boldsymbol A)$。特征值 0 对应的特征空间 $=$ 零空间。

例3：旋转 $90^\circ$

$$
\boldsymbol A = \begin{pmatrix}
0 & -1\\
1 & 0
\end{pmatrix}
$$

有没有非零 $\boldsymbol v$ 满足 $\boldsymbol A \cdot \boldsymbol v = \lambda \cdot \boldsymbol v$？

几何上：旋转 $90^\circ$ 后，没有任何方向还指着原来的方向。

$\rightarrow$ 在实数范围内，旋转 $90^\circ$ 没有实特征向量。

**几何直觉总结表**

| 变换 | 特征向量（哪些方向不变） | 特征值 |
| --- | --- | --- |
| 均匀放大 2 倍 | **所有方向** | 全部 2 |
| x 拉 2 倍，y 不变 | x 轴方向，y 轴方向 | 2, 1 |
| 投影到 x 轴 | x 轴方向（不变），y 轴方向（消失） | 1, 0 |
| 旋转 $90^\circ$ | 无 | 无实特征值 |
| 关于原点反射 | 所有方向（但反向） | $-1$ |"""

_EIGEN_DIRECTION_EXAMPLE = {
    "id": "example.ch07.eigen.direction.contrast",
    "title": "拉伸下的方向保持与改变",
    "kind": "matrix_transform",
    "given": [[[2, 0], [0, 1]], [1, 0]],
    "result": [2, 0],
    "check": "transformed",
    "lines": (r"""取拉伸变换

$$
\boldsymbol A=\begin{pmatrix}
2&0\\
0&1
\end{pmatrix}.
$$

对于

$$
\boldsymbol v=\begin{pmatrix}
1\\
0
\end{pmatrix},
$$

有

$$
\boldsymbol A\boldsymbol v=\begin{pmatrix}
2\\
0
\end{pmatrix}=2\begin{pmatrix}
1\\
0
\end{pmatrix}=2\boldsymbol v.
$$

因此，$\boldsymbol v$ 是特征向量，特征值为 $\lambda=2$，方向不变。

再取

$$
\boldsymbol u=\begin{pmatrix}
1\\
1
\end{pmatrix}.
$$

有

$$
\boldsymbol A\boldsymbol u=\begin{pmatrix}
2\\
1
\end{pmatrix}.
$$

不存在标量 $k$ 使

$$
\begin{pmatrix}
2\\
1
\end{pmatrix}=k\begin{pmatrix}
1\\
1
\end{pmatrix},
$$

所以 $\boldsymbol u$ 不是特征向量；变换后方向发生了改变。""",),
}

def refine_chapter_07_topic(topic_id: str, payload: dict[str, Any], explanation: dict[str, Any], visual: dict[str, Any]) -> None:
    """Replace generic Chapter 7 prose with reviewed lecture content."""

    spec = CONTENT[topic_id]
    claim_id = f"claim.{topic_id}"
    is_eigen_direction = topic_id == "ch07.eigen.direction"
    definition = _EIGEN_DIRECTION_DEFINITION if is_eigen_direction else str(spec["definition"])
    example_specs = (_EIGEN_DIRECTION_EXAMPLE,) if is_eigen_direction else tuple(spec["examples"])
    examples = [_worked_example(item, claim_id) for item in example_specs]
    invariants = [] if is_eigen_direction else list(
        visual.get("stages", [{}])[0].get("expected_invariants", ())
        if visual.get("stages")
        else ()
    )
    stage_specs = spec["stages"]
    case_stage_specs = (("stretch", "拉伸下的方向保持与改变"),) if is_eigen_direction else stage_specs
    case_example_indices = (0,) if is_eigen_direction else spec["case_example_indices"]
    explanation.update({
        "title": str(spec["title"]), "summary": "" if is_eigen_direction else str(spec["summary"]),
        "definition": definition, "formula": "",
        "derivation": list(spec["derivation"]), "worked_examples": examples,
        "invariants": invariants,
        "geometric_meaning": "",
        "sections": [
            {"id": section_id, "title": title, "text": "", "claim_refs": [claim_id]}
            for section_id, title in spec["sections"]
        ] + ([{"id": "invariants", "title": "不变量", "text": "", "claim_refs": [claim_id]}] if invariants else []),
        "searchable_text": [str(spec["title"]), str(spec["summary"]), definition, *spec["derivation"], *invariants, *[line for item in example_specs for line in item["lines"]]],
    })
    for key in ("intuition", "pitfalls", "connections", "analogy_boundary", "transfer_note", "read_guide", "conclusion"):
        explanation.pop(key, None)

    stages = {stage["id"].rsplit(".", 1)[-1]: stage for stage in visual["stages"]}
    ordered_stages = []
    for stage_name, purpose in stage_specs:
        stage = stages[stage_name]
        stage.update({"title": purpose, "caption": "", "layout": "overlay"})
        ordered_stages.append(stage)
    visual["stages"] = ordered_stages

    explanation["case_layout"] = {
        "default_pane_count": int(spec["default_pane_count"]),
        "cases": [{
            "id": f"case.{topic_id}.{index}", "topic_id": topic_id,
            "example_ref": examples[example_index]["id"], "claim_refs": [claim_id],
            "stage_refs": [stage["id"]], "purpose": purpose,
        } for index, ((_, purpose), stage, example_index) in enumerate(zip(case_stage_specs, (stages[stage_name] for stage_name, _ in case_stage_specs), case_example_indices), start=1)],
    }

    claim = payload["claims"][0]
    claim.update({
        "statement": str(spec["summary"]), "formula": CLAIM_FORMULAS[topic_id],
        "formula_symbols": [entity["role"] for entity in visual["entities"]],
        "explanation_refs": [section_id for section_id, _ in spec["sections"]],
        "entity_refs": [entity["id"] for entity in visual["entities"]],
        "relation_refs": [relation["id"] for relation in visual["relations"]],
        "stage_refs": [stage["id"] for stage in ordered_stages],
    })
    payload["connections"] = []


__all__ = ["CONTENT", "refine_chapter_07_topic"]
