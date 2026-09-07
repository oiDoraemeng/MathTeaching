# Math explanation sample 2

This file retains the current Codex math-explanation sub-agent response used
as the review baseline for the lecture artifacts. It is prose only; drawing
is derived from the mathematical objects and relations in the artifact.

## 向量加法

### 定义与公式

设 \(a=(x_1,y_1)\)、\(b=(x_2,y_2)\)，向量和按对应分量相加：

\[
a+b=(x_1+x_2,\ y_1+y_2).
\]

例如 \(a=(2,1)\)、\(b=(1,3)\) 时，\(a+b=(3,4)\)。

### 几何意义

三角形法则：把 \(b\) 平移，使其起点落在 \(a\) 的终点；从 \(a\) 的起点指向平移后 \(b\) 的终点的箭头，就是 \(a+b\)。

平行四边形法则：让 \(a,b\) 从同一起点出发，以它们为邻边补成平行四边形；共同起点到对角顶点的对角线就是 \(a+b\)。

## 矩阵乘法 \(AB\ne BA\)

### 定义与公式

对向量 \(x\) 有

\[
(AB)x=A(Bx),
\]

因此先做 \(B\)，再做 \(A\)。

### 几何意义

取

\[
A=\begin{pmatrix}2&0\\0&1\end{pmatrix},\qquad
B=\begin{pmatrix}0&-1\\1&0\end{pmatrix},\qquad x=(1,1)^T.
\]

先旋转再拉伸得到 \(ABx=(-2,1)^T\)，先拉伸再旋转得到 \(BAx=(-1,2)^T\)，所以 \(AB\ne BA\)。
