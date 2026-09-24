"""Reviewed lecture content and case layouts for Chapter 6 sections 6.2--6.3."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


CLAIM_FORMULAS = {
    "ch06.basis-change.coordinates": r"\boldsymbol x=\boldsymbol P\boldsymbol c,\quad \boldsymbol c=\boldsymbol P^{-1}\boldsymbol x",
    "ch06.similarity-transform": r"\boldsymbol B=\boldsymbol P^{-1}\boldsymbol A\boldsymbol P",
}


CONTENT: dict[str, dict[str, Any]] = {
    "ch06.basis-change.coordinates": {
        "title": "基变换",
        "summary": "同一个向量在不同基下有不同的坐标，基变换矩阵负责在两种坐标之间翻译。",
        "definition": r"""**（基变换矩阵）** 设

$$
B=\{\boldsymbol v_1,\boldsymbol v_2,\ldots,\boldsymbol v_n\}
$$

是 $\mathbb R^n$ 的一组基。将这些向量按列排成矩阵

$$
\boldsymbol P=
\begin{pmatrix}
\vert&\vert&&\vert\\
\boldsymbol v_1&\boldsymbol v_2&\cdots&\boldsymbol v_n\\
\vert&\vert&&\vert
\end{pmatrix}.
$$

对任意向量 $\boldsymbol x$，标准基下的坐标与 $B$ 基下的坐标满足

$$
[\boldsymbol x]_{\mathrm{标准基}}
=\boldsymbol P[\boldsymbol x]_B.
$$

即：$\boldsymbol P$ 把“新基下的坐标”翻译成“标准基下的坐标”。

反过来：

$$
[\boldsymbol x]_B
=\boldsymbol P^{-1}[\boldsymbol x]_{\mathrm{标准基}}.
$$

$\boldsymbol P^{-1}$ 把标准坐标翻译成新基坐标。

几何理解：标准基 $\boldsymbol e_1,\boldsymbol e_2$ 与新基 $\boldsymbol v_1,\boldsymbol v_2$ 是两组不同的“尺子”。$\boldsymbol P$ 完成从新坐标到旧坐标的翻译，$\boldsymbol P^{-1}$ 完成从旧坐标到新坐标的翻译。

$\boldsymbol P$ 的列就是新基向量在标准基下的坐标。用它乘上“新坐标”就得到“老坐标”。""",
        "derivation": (),
        "examples": (
            {
                "id": "example.ch06.basis-change.coordinates.forward",
                "title": "例 1：新基坐标变成标准坐标",
                "kind": "matrix_transform",
                "given": [[[1, -1], [1, 1]], [2, 3]],
                "result": [-1, 5],
                "check": "transformed",
                "lines": (r"""新基为

$$
\boldsymbol v_1=
\begin{pmatrix}
1\\1
\end{pmatrix},\qquad
\boldsymbol v_2=
\begin{pmatrix}
-1\\1
\end{pmatrix}.
$$

向量在新基下的坐标为

$$
\boldsymbol c=
\begin{pmatrix}
2\\3
\end{pmatrix}.
$$

基变换矩阵为

$$
\boldsymbol P=
\begin{pmatrix}
1&-1\\
1&1
\end{pmatrix}.
$$

标准坐标为

$$
\boldsymbol x
=\boldsymbol P\boldsymbol c
=2\begin{pmatrix}1\\1\end{pmatrix}
+3\begin{pmatrix}-1\\1\end{pmatrix}
=\begin{pmatrix}2-3\\2+3\end{pmatrix}
=\begin{pmatrix}-1\\5\end{pmatrix}.
$$""",),
            },
        ),
        "stages": (
            ("forward", "新坐标变成标准坐标"),
            ("backward", "标准坐标变成新坐标"),
            ("identity", "标准基到标准基"),
        ),
        "default_pane_count": 1,
        "case_example_indices": (0,),
        "sections": (("definition", "定义"), ("worked_examples", "数学案例")),
    },
    "ch06.similarity-transform": {
        "title": "相似变换",
        "summary": "同一个线性变换在不同基下由相似矩阵表示。",
        "definition": r"""**（线性变换在不同基下的矩阵）** 设线性变换 $T$ 在标准基下的矩阵为 $\boldsymbol A$。在基 $B$ 下，基变换矩阵为 $\boldsymbol P$，则 $T$ 在基 $B$ 下的矩阵为

$$
\boldsymbol B
=\boldsymbol P^{-1}\boldsymbol A\boldsymbol P.
$$

这正是第 7 章将要学习的对角化公式，那里的 $\boldsymbol P$ 恰好由特征向量组成。

**（相似）** 如果存在可逆矩阵 $\boldsymbol P$，使得

$$
\boldsymbol B
=\boldsymbol P^{-1}\boldsymbol A\boldsymbol P,
$$

则称 $\boldsymbol B$ 与 $\boldsymbol A$ 相似。

相似 $=$ 同一个线性变换的不同“面孔”（在不同基下的矩阵）。它们描述的是完全相同的几何操作，只是从不同角度“拍照”。

**（相似不变量）** 若

$$
\boldsymbol B
=\boldsymbol P^{-1}\boldsymbol A\boldsymbol P,
$$

则：

- $\det(\boldsymbol B)=\det(\boldsymbol A)$，行列式不变；
- $\operatorname{rank}(\boldsymbol B)=\operatorname{rank}(\boldsymbol A)$，秩不变；
- 特征值不变，拉伸倍数不依赖于基的选取；
- $\operatorname{tr}(\boldsymbol B)=\operatorname{tr}(\boldsymbol A)$，迹不变，其中矩阵的迹等于对角线元素之和；
- $\det(\boldsymbol B-\lambda\boldsymbol I)=\det(\boldsymbol A-\lambda\boldsymbol I)$，特征多项式不变。""",
        "derivation": (
            r"""**三步推导**

在 $B$ 基下输入坐标 $\boldsymbol c$。先由 $\boldsymbol P$ 翻译成标准坐标：

$$
\boldsymbol c\longmapsto\boldsymbol P\boldsymbol c.
$$

再由 $\boldsymbol A$ 执行标准基下的变换：

$$
\boldsymbol P\boldsymbol c
\longmapsto
\boldsymbol A(\boldsymbol P\boldsymbol c).
$$

最后由 $\boldsymbol P^{-1}$ 翻译回 $B$ 基坐标：

$$
\boldsymbol A(\boldsymbol P\boldsymbol c)
\longmapsto
\boldsymbol P^{-1}\boldsymbol A(\boldsymbol P\boldsymbol c)
=(\boldsymbol P^{-1}\boldsymbol A\boldsymbol P)\boldsymbol c.
$$

所以变换在 $B$ 基下的矩阵为

$$
\boldsymbol P^{-1}\boldsymbol A\boldsymbol P.
$$""",
            r"""**（相似不变量）**

行列式不变：

$$
\begin{aligned}
\det(\boldsymbol P^{-1}\boldsymbol A\boldsymbol P)
&=\det(\boldsymbol P^{-1})\det(\boldsymbol A)\det(\boldsymbol P)\\
&=\det(\boldsymbol A)\det(\boldsymbol P^{-1}\boldsymbol P)\\
&=\det(\boldsymbol A)\det(\boldsymbol I)\\
&=\det(\boldsymbol A).
\end{aligned}
$$

秩不变：$\boldsymbol P$ 和 $\boldsymbol P^{-1}$ 都是可逆矩阵，左乘或右乘可逆矩阵等价于对行或列做初等变换，而初等变换不改变秩。因此

$$
\operatorname{rank}(\boldsymbol P^{-1}\boldsymbol A\boldsymbol P)
=\operatorname{rank}(\boldsymbol A).
$$

迹不变：

$$
\begin{aligned}
\operatorname{tr}(\boldsymbol P^{-1}\boldsymbol A\boldsymbol P)
&=\operatorname{tr}(\boldsymbol A\boldsymbol P\boldsymbol P^{-1})\\
&=\operatorname{tr}(\boldsymbol A\boldsymbol I)\\
&=\operatorname{tr}(\boldsymbol A).
\end{aligned}
$$

这里使用了迹的循环性质：

$$
\begin{aligned}
\operatorname{tr}(\boldsymbol X\boldsymbol Y)
&=\sum_i\left(\sum_k x_{ik}y_{ki}\right)\\
&=\sum_k\left(\sum_i y_{ki}x_{ik}\right)\\
&=\operatorname{tr}(\boldsymbol Y\boldsymbol X).
\end{aligned}
$$

特征多项式不变：

$$
\begin{aligned}
\det(\boldsymbol P^{-1}\boldsymbol A\boldsymbol P-\lambda\boldsymbol I)
&=\det(\boldsymbol P^{-1}\boldsymbol A\boldsymbol P-\lambda\boldsymbol P^{-1}\boldsymbol I\boldsymbol P)\\
&=\det\!\left(\boldsymbol P^{-1}(\boldsymbol A-\lambda\boldsymbol I)\boldsymbol P\right)\\
&=\det(\boldsymbol P^{-1})\det(\boldsymbol A-\lambda\boldsymbol I)\det(\boldsymbol P)\\
&=\det(\boldsymbol A-\lambda\boldsymbol I).
\end{aligned}
$$

特征多项式不变，特征值也不变，因为特征值是特征多项式的根。""",
        ),
        "examples": (
            {
                "id": "example.ch06.similarity-transform.trace",
                "title": "例 7：验证迹不变",
                "kind": "matrix_product",
                "given": [[[1, -1], [0, 1]], [[2, 5], [1, 5]]],
                "result": [[1, 0], [1, 5]],
                "check": "result",
                "lines": (r"""取

$$
\boldsymbol A=
\begin{pmatrix}
2&3\\
1&4
\end{pmatrix},\qquad
\boldsymbol P=
\begin{pmatrix}
1&1\\
0&1
\end{pmatrix},\qquad
\boldsymbol P^{-1}=
\begin{pmatrix}
1&-1\\
0&1
\end{pmatrix}.
$$

计算得到

$$
\begin{aligned}
\boldsymbol B
&=\boldsymbol P^{-1}\boldsymbol A\boldsymbol P\\
&=
\begin{pmatrix}
1&-1\\
0&1
\end{pmatrix}
\begin{pmatrix}
2&3\\
1&4
\end{pmatrix}
\begin{pmatrix}
1&1\\
0&1
\end{pmatrix}\\
&=
\begin{pmatrix}
1&0\\
1&5
\end{pmatrix}.
\end{aligned}
$$

于是

$$
\operatorname{tr}(\boldsymbol A)=2+4=6,
\qquad
\operatorname{tr}(\boldsymbol B)=1+5=6.
$$""",),
            },
            {
                "id": "example.ch06.similarity-transform.characteristic-polynomial",
                "title": "例 8：验证特征多项式不变",
                "kind": "determinant",
                "given": [[2, 3], [1, 4]],
                "result": 5,
                "check": "determinant",
                "lines": (r"""对例 7 的 $\boldsymbol A$ 和 $\boldsymbol B$，分别计算特征多项式：

$$
\begin{aligned}
\det(\boldsymbol A-\lambda\boldsymbol I)
&=(2-\lambda)(4-\lambda)-3\\
&=\lambda^2-6\lambda+5,
\end{aligned}
$$

$$
\begin{aligned}
\det(\boldsymbol B-\lambda\boldsymbol I)
&=(1-\lambda)(5-\lambda)\\
&=\lambda^2-6\lambda+5.
\end{aligned}
$$

行列式、秩、特征值、迹、特征多项式——这些是线性变换的“DNA”，不因换基而改变。相似矩阵描述的是“同一个线性变换”的不同面孔，所以“不变特征”必须保持一致。""",),
            },
            {
                "id": "example.ch06.similarity-transform.invariants",
                "title": "例 6：验证两个矩阵的相似不变量",
                "kind": "determinant",
                "given": [[2, 1], [1, 2]],
                "result": 3,
                "check": "determinant",
                "lines": (r"""验证

$$
\boldsymbol A=
\begin{pmatrix}
2&1\\
1&2
\end{pmatrix},\qquad
\boldsymbol B=
\begin{pmatrix}
3&0\\
0&1
\end{pmatrix}
$$

是否相似。之前已经算出

$$
\boldsymbol B=\boldsymbol P^{-1}\boldsymbol A\boldsymbol P.
$$

迹满足

$$
\operatorname{tr}(\boldsymbol A)=2+2=4,
\qquad
\operatorname{tr}(\boldsymbol B)=3+1=4.
$$

行列式满足

$$
\det(\boldsymbol A)=3,
\qquad
\det(\boldsymbol B)=3.
$$

$\boldsymbol A$ 的特征值为 $\lambda=3,1$，$\boldsymbol B$ 的对角线元素为 $3,1$，特征值相同。""",),
            },
            {
                "id": "example.ch06.similarity-transform.diagonal",
                "title": "例 4：求新基下的矩阵",
                "kind": "matrix_product",
                "given": [[[0.5, 0.5], [-0.5, 0.5]], [[3, -1], [3, 1]]],
                "result": [[3, 0], [0, 1]],
                "check": "result",
                "lines": (r"""标准基下

$$
\boldsymbol A=
\begin{pmatrix}
2&1\\
1&2
\end{pmatrix}.
$$

取新基

$$
\boldsymbol v_1=
\begin{pmatrix}1\\1\end{pmatrix},
\qquad
\boldsymbol v_2=
\begin{pmatrix}-1\\1\end{pmatrix}.
$$

则

$$
\boldsymbol P=
\begin{pmatrix}
1&-1\\
1&1
\end{pmatrix},\qquad
\boldsymbol P^{-1}
=\frac12
\begin{pmatrix}
1&1\\
-1&1
\end{pmatrix}.
$$

因此

$$
\begin{aligned}
\boldsymbol P^{-1}\boldsymbol A\boldsymbol P
&=\frac12
\begin{pmatrix}
1&1\\
-1&1
\end{pmatrix}
\begin{pmatrix}
2&1\\
1&2
\end{pmatrix}
\begin{pmatrix}
1&-1\\
1&1
\end{pmatrix}\\
&=
\begin{pmatrix}
3&0\\
0&1
\end{pmatrix}.
\end{aligned}
$$

新基下 $\boldsymbol A$ 变成了对角矩阵。这是因为 $\boldsymbol v_1,\boldsymbol v_2$ 恰好是 $\boldsymbol A$ 的特征向量——这就是第 7 章对角化的本质。""",),
            },
            {
                "id": "example.ch06.similarity-transform.determinant",
                "title": "例 5：验证行列式不变",
                "kind": "determinant",
                "given": [[2, 1], [1, 2]],
                "result": 3,
                "check": "determinant",
                "lines": (r"""在例 4 中，

$$
\det(\boldsymbol A)=2\times2-1\times1=3.
$$

同时

$$
\det(\boldsymbol P^{-1}\boldsymbol A\boldsymbol P)
=3\times1
=3.
$$""",),
            },
        ),
        "stages": (
            ("change_basis", "P：翻译为标准坐标"),
            ("apply_operator", "A：执行线性变换"),
            ("change_basis_back", "P⁻¹：翻译回新基"),
        ),
        "default_pane_count": 3,
        "case_example_indices": (3, 3, 3),
        "sections": (("definition", "定义"), ("derivation", "推导与证明"), ("worked_examples", "数学案例")),
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


def refine_chapter_06_topic(
    topic_id: str,
    payload: dict[str, Any],
    explanation: dict[str, Any],
    visual: dict[str, Any],
) -> None:
    """Replace the generic Chapter 6 prose with reviewed lecture content."""

    spec = CONTENT[topic_id]
    claim_id = f"claim.{topic_id}"
    examples = [_worked_example(item, claim_id) for item in spec["examples"]]
    explanation.update(
        {
            "title": str(spec["title"]),
            "summary": str(spec["summary"]),
            "definition": str(spec["definition"]),
            "formula": "",
            # 不变量属于讲义正文和编译校验语义，不单独生成通用分区。
            "invariants": [],
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


__all__ = ["CONTENT", "refine_chapter_06_topic"]
