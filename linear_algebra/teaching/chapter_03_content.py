"""Reviewed lecture content for the text-only Chapter 3 sections 3.3--3.6."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


CONTENT: dict[str, dict[str, Any]] = {
    "ch03.cramer.area-ratio": {
        "title": "克拉默法则的面积比解方程组",
        "summary": "克拉默法则",
        "definition": r'''**（Cramer 法则）** 对于线性方程组 $\boldsymbol A\boldsymbol x=\boldsymbol b$（$\boldsymbol A$ 为 $n \times n$ 可逆矩阵），解的第 $i$ 个分量为：

$$
x_{i}=\frac{\det(\boldsymbol A_{i})}{\det(\boldsymbol A)}
$$

其中 $\boldsymbol A_{i}$ 是将 $\boldsymbol A$ 的第 $i$ 列替换为 $\boldsymbol b$ 后得到的新矩阵。

几何解读（$2 \times 2$）：

- $x_{1}=$ "以 $\boldsymbol b$ 替第一列"的平行四边形面积 / 原始平行四边形面积
- $x_{2}=$ "以 $\boldsymbol b$ 替第二列"的平行四边形面积 / 原始平行四边形面积''',
        "derivation": (),
        "examples": (
            {
                "id": "example.ch03.cramer.area-ratio.system",
                "title": "例题",
                "kind": "matrix_transform",
                "given": [[[2, 1], [1, 3]], [2, 1]],
                "result": [5, 5],
                "check": "transformed",
                "lines": (r'''方程组：$2x+y=5$，$x+3y=5$。

$$
\boldsymbol A=
\begin{pmatrix}
2 & 1 \\
1 & 3
\end{pmatrix},\qquad
\boldsymbol b=
\begin{pmatrix}
5 \\
5
\end{pmatrix}
$$

$$
\det(\boldsymbol A)=5
$$

$$
\det\begin{pmatrix}
5 & 1 \\
5 & 3
\end{pmatrix}=10 \rightarrow x=\frac{10}{5}=2
$$

$$
\det\begin{pmatrix}
2 & 5 \\
1 & 5
\end{pmatrix}=5 \rightarrow y=\frac{5}{5}=1
$$

$$
(x,y)=(2,1)\ \checkmark
$$''',),
            },
        ),
        "sections": (("definition", "定义"), ("worked_examples", "数学案例")),
        "statement": "克拉默法则把未知量表示为替换一列后的行列式与原行列式之比。",
        "claim_formula": r"x_i=\frac{\det(\boldsymbol A_i)}{\det(\boldsymbol A)}",
    },
    "ch03.inverse.undo": {
        "title": "逆矩阵",
        "summary": "逆矩阵",
        "definition": r'''**（逆矩阵）** 对 $n \times n$ 矩阵 $\boldsymbol A$，若存在 $n \times n$ 矩阵 $\boldsymbol B$ 使得：

$$
\boldsymbol A\boldsymbol B=\boldsymbol B\boldsymbol A=\boldsymbol I
$$

（$\boldsymbol I$ 是 $n \times n$ 单位矩阵）

则称 $\boldsymbol B$ 为 $\boldsymbol A$ 的逆矩阵，记为 $\boldsymbol A^{-1}$。若 $\boldsymbol A^{-1}$ 存在，称 $\boldsymbol A$ 可逆（或非奇异）；否则称 $\boldsymbol A$ 奇异（不可逆）。

**（可逆的充要条件）**

$$
\boldsymbol A\text{ 可逆}\Leftrightarrow\det(\boldsymbol A)\neq0
$$

几何上：$\det(\boldsymbol A)\neq0$ 意味着变换没有把空间压扁 $\rightarrow$ 每个输出都能唯一地"追溯"回输入 $\rightarrow$ 变换可逆。

若

$$
\boldsymbol A=
\begin{pmatrix}
a & b \\
c & d
\end{pmatrix}
$$

且 $\det(\boldsymbol A)=ad-bc\neq0$，则：

$$
\boldsymbol A^{-1}=\left(\frac{1}{\det(\boldsymbol A)}\right)\times
\begin{pmatrix}
d & -b \\
-c & a
\end{pmatrix}
$$

口诀：对角线交换，反对角线变号，前乘 $1/\det$。''',
        "derivation": (),
        "examples": (
            {
                "id": "example.ch03.inverse.undo.stretch",
                "title": "例1",
                "kind": "matrix_product",
                "given": [[[2, 0], [0, 1]], [[0.5, 0], [0, 1]]],
                "result": [[1, 0], [0, 1]],
                "check": "result",
                "lines": (r'''**【理解层】**

例1：

$$
\boldsymbol A=
\begin{pmatrix}
2 & 0 \\
0 & 1
\end{pmatrix}
$$

（横向拉伸 $2$ 倍）。逆变换？

$$
\boldsymbol A^{-1}=
\begin{pmatrix}
\frac{1}{2} & 0 \\
0 & 1
\end{pmatrix}
$$

（横向压缩到 $\frac{1}{2}$）。''',),
            },
            {
                "id": "example.ch03.inverse.undo.singular",
                "title": "例2",
                "kind": "determinant",
                "given": [[1, 2], [2, 4]],
                "result": 0,
                "check": "determinant",
                "lines": (r'''例2：

$$
\boldsymbol A=
\begin{pmatrix}
1 & 2 \\
2 & 4
\end{pmatrix},\qquad \det(\boldsymbol A)=0
$$

可逆吗？

不可逆——变换把平面压成一条线，信息丢失，无法还原。''',),
            },
            {
                "id": "example.ch03.inverse.undo.calculate",
                "title": "例3",
                "kind": "matrix_product",
                "given": [[[3, 1], [2, 4]], [[0.4, -0.1], [-0.2, 0.3]]],
                "result": [[1, 0], [0, 1]],
                "check": "result",
                "lines": (r'''**【计算层】**

例3：

$$
\boldsymbol A=
\begin{pmatrix}
3 & 1 \\
2 & 4
\end{pmatrix},\qquad \det(\boldsymbol A)=10
$$

求 $\boldsymbol A^{-1}$。

$$
\boldsymbol A^{-1}=\left(\frac{1}{10}\right)\cdot
\begin{pmatrix}
4 & -1 \\
-2 & 3
\end{pmatrix}
=
\begin{pmatrix}
0.4 & -0.1 \\
-0.2 & 0.3
\end{pmatrix}
$$''',),
            },
            {
                "id": "example.ch03.inverse.undo.application",
                "title": "例4",
                "kind": "matrix_transform",
                "given": [[[0.4, -0.1], [-0.2, 0.3]], [10, 10]],
                "result": [3, 1],
                "check": "transformed",
                "lines": (r'''**【应用层】**

例4：$\boldsymbol A\boldsymbol x=\boldsymbol b$，

$$
\boldsymbol A=
\begin{pmatrix}
3 & 1 \\
2 & 4
\end{pmatrix},\qquad
\boldsymbol b=
\begin{pmatrix}
10 \\
10
\end{pmatrix}
$$

求 $\boldsymbol x$。

$$
\boldsymbol x=\boldsymbol A^{-1}\boldsymbol b=
\begin{pmatrix}
3 \\
1
\end{pmatrix}
$$''',),
            },
        ),
        "sections": (("definition", "定义"), ("worked_examples", "数学案例")),
        "statement": "矩阵可逆当且仅当其行列式不为零。",
        "claim_formula": r"\boldsymbol A\boldsymbol B=\boldsymbol B\boldsymbol A=\boldsymbol I,\quad \boldsymbol A\text{ 可逆}\Leftrightarrow\det(\boldsymbol A)\neq0",
    },
    "ch03.adjugate.matrix": {
        "title": "伴随矩阵",
        "summary": "伴随矩阵",
        "definition": r'''**（伴随矩阵）** 对 $n \times n$ 矩阵 $\boldsymbol A$，其伴随矩阵 $\operatorname{adj}(\boldsymbol A)$ 的第 $(j,i)$ 元素为 $\boldsymbol A$ 的 $(i,j)$ 代数余子式。逆矩阵公式：

$$
\boldsymbol A^{-1}=\operatorname{adj}\frac{\boldsymbol A}{\det(\boldsymbol A)}
$$

当 $n=2$ 时即为 $3.4.2$ 的公式。

伴随矩阵：$\operatorname{adj}(\boldsymbol A)$ 的元素为 $(\operatorname{adj}(\boldsymbol A))_{ji}=A_{ij}$（代数余子式，注意下标是转置的！）。''',
        "derivation": (r'''关键证明 $\boldsymbol A\cdot\operatorname{adj}(\boldsymbol A)=\det(\boldsymbol A)\cdot\boldsymbol I$：

$$
(\boldsymbol A\cdot\operatorname{adj}(\boldsymbol A))_{ii}=\sum_{k}a_{ik}\cdot A_{ik}=\det(\boldsymbol A)
$$

（按第 $i$ 行展开）。

当 $i\neq j$ 时，

$$
(\boldsymbol A\cdot\operatorname{adj}(\boldsymbol A))_{ij}=\sum_{k}a_{ik}\cdot A_{jk}
$$

这相当于把 $\boldsymbol A$ 的第 $j$ 行换成第 $i$ 行后求行列式（两行相等 $\rightarrow$ 为 $0$）。

故 $\boldsymbol A\cdot\operatorname{adj}(\boldsymbol A)=\det(\boldsymbol A)\cdot\boldsymbol I$。若 $\det(\boldsymbol A)\neq0$，则 $\boldsymbol A^{-1}=\operatorname{adj}\frac{\boldsymbol A}{\det(\boldsymbol A)}$。''',),
        "examples": (
            {
                "id": "example.ch03.adjugate.matrix.two-by-two",
                "title": "数学案例",
                "kind": "matrix_product",
                "given": [[[2, 1], [3, 4]], [[4, -1], [-3, 2]]],
                "result": [[5, 0], [0, 5]],
                "check": "result",
                "lines": (r'''取

$$
\boldsymbol A=
\begin{pmatrix}
2 & 1 \\
3 & 4
\end{pmatrix}.
$$

$\boldsymbol A$ 的代数余子式矩阵为

$$
\begin{pmatrix}
4 & -3 \\
-1 & 2
\end{pmatrix}.
$$

将代数余子式矩阵转置，得到

$$
\operatorname{adj}(\boldsymbol A)=
\begin{pmatrix}
4 & -1 \\
-3 & 2
\end{pmatrix}.
$$

又

$$
\det(\boldsymbol A)=2\times4-1\times3=5.
$$

验证关键等式：

$$
\boldsymbol A\operatorname{adj}(\boldsymbol A)
=
\begin{pmatrix}
2 & 1 \\
3 & 4
\end{pmatrix}
\begin{pmatrix}
4 & -1 \\
-3 & 2
\end{pmatrix}
=
\begin{pmatrix}
5 & 0 \\
0 & 5
\end{pmatrix}
=5\boldsymbol I.
$$

因此

$$
\boldsymbol A^{-1}
=\frac{1}{5}\operatorname{adj}(\boldsymbol A)
=\frac{1}{5}
\begin{pmatrix}
4 & -1 \\
-3 & 2
\end{pmatrix}.
$$''',),
            },
        ),
        "sections": (("definition", "定义"), ("derivation", "推导"), ("worked_examples", "数学案例")),
        "statement": "伴随矩阵满足矩阵与其乘积等于行列式乘单位矩阵。",
        "claim_formula": r"\boldsymbol A\operatorname{adj}(\boldsymbol A)=\det(\boldsymbol A)\boldsymbol I",
    },
    "ch03.det.zero.equivalence": {
        "title": "det=0 的等价几何条件",
        "summary": "行列式为零的深度解释",
        "definition": r'''**（$\det=0$ 的等价条件）** 对 $n \times n$ 矩阵 $\boldsymbol A$，以下等价：

1. $\det(\boldsymbol A)=0$ — 变换后的"单位体积"为零
2. 列向量线性相关（定义见 $2.9.1$ 节） — 至少有一列是其他列的线性组合
3. $\operatorname{rank}(\boldsymbol A)<n$（定义见 $2.9.2$ 节） — 存在至少一个"冗余列"，变换压扁了某维度
4. $\boldsymbol A$ 不可逆 — 存在非零向量 $\boldsymbol x$ 使得 $\boldsymbol A\boldsymbol x=\boldsymbol 0$（$\operatorname{Null}(\boldsymbol A)$ 非平凡，见 $2.9.3$ 节）

几何上：$\det=0$ 意味着整个空间至少有一个方向被完全"压扁"了。从一条线（或一个平面）无法唯一地还原出原来的全部信息——因此变换不可逆。

这四种说法是等价的——它们从不同角度描述了同一件事：矩阵的列中有"多余的"。现在理解了 $\operatorname{rank}$ 和线性无关之后，第 $3$ 章的 $\det$ 和第 $2$ 章就有了统一的语言。

**（三角矩阵的行列式）** 若 $\boldsymbol A$ 是三角矩阵（上三角或下三角），则 $\det(\boldsymbol A)=$ 对角线元素之积：

$$
\det(\boldsymbol A)=a_{11}\cdot a_{22}\cdot\dots\cdot a_{nn}.
$$''',
        "derivation": (r'''证明：对上三角矩阵按最后一列展开（或反复按对角线下方的零元素展开），每次展开只留下对角线元素，最终结果即对角线乘积。

推论：对角矩阵 $\operatorname{diag}(\lambda_{1},\dots,\lambda_{n})$ 的行列式 $=\lambda_{1}\cdot\lambda_{2}\cdot\dots\cdot\lambda_{n}$。这是第 $7$ 章「特征值乘积 $=$ 行列式」的伏笔。''',),
        "examples": (
            {
                "id": "example.ch03.det.zero.equivalence.triangular",
                "title": "例5",
                "kind": "determinant",
                "given": [[2, 5, -1], [0, 3, 4], [0, 0, 7]],
                "result": 42,
                "check": "determinant",
                "lines": (r'''$$
\boldsymbol A=
\begin{pmatrix}
2 & 5 & -1 \\
0 & 3 & 4 \\
0 & 0 & 7
\end{pmatrix}.
$$

$$
\det(\boldsymbol A)=2\times3\times7=42.
$$''',),
            },
            {
                "id": "example.ch03.det.zero.equivalence.dependent-columns",
                "title": "例题",
                "kind": "determinant",
                "given": [[1, 3], [2, 6]],
                "result": 0,
                "check": "determinant",
                "lines": (r'''$$
\boldsymbol A=
\begin{pmatrix}
1 & 3 \\
2 & 6
\end{pmatrix}.
$$

第二列 $=3\times\begin{pmatrix}1\\2\end{pmatrix}=3\times$ 第一列。

$$
\det(\boldsymbol A)=6-6=0.
$$

两条"新基"在同一条线上 $\rightarrow$ 平面被压实到一条线上 $\rightarrow$ 信息不可恢复。''',),
            },
        ),
        "sections": (("definition", "定义"), ("derivation", "推导"), ("worked_examples", "数学案例")),
        "statement": "行列式为零、列向量线性相关、秩小于阶数和矩阵不可逆彼此等价。",
        "claim_formula": r"\det(\boldsymbol A)=0\Leftrightarrow\operatorname{rank}(\boldsymbol A)<n\Leftrightarrow\boldsymbol A\text{ 不可逆}",
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


def refine_chapter_03_text_topic(
    topic_id: str,
    payload: dict[str, Any],
    explanation: dict[str, Any],
    visual: dict[str, Any],
) -> None:
    """Apply the reviewed lecture prose and explicitly remove visual cases."""

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
            "symbol_roles": {},
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
        "case_layout",
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

    visual.update({"scene_kind": "2d", "scene_family": "", "entities": [], "relations": [], "stages": []})
    payload["connections"] = []
    claim = payload["claims"][0]
    claim.update(
        {
            "statement": str(spec["statement"]),
            "formula": str(spec["claim_formula"]),
            "formula_symbols": [],
            "explanation_refs": [section_id for section_id, _ in spec["sections"]],
            "entity_refs": [],
            "relation_refs": [],
            "stage_refs": [],
            "source_refs": [
                str(span["id"])
                for span in payload.get("source", {}).get("spans", [])
                if isinstance(span, dict) and span.get("id")
            ],
        }
    )


__all__ = ["CONTENT", "refine_chapter_03_text_topic"]
