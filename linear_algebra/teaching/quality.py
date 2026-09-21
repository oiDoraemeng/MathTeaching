"""Lecture-grounded prose refinement for locally generated teaching artifacts.

The explanation agent owns the mathematical prose.  This module is the local
review adapter used when no remote provider is configured: it turns the
bounded semantic graph and checked numeric example into readable lecture text
without emitting renderer commands.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

_BATCH_INNER_PRODUCT_FORMULA = r"(\boldsymbol u\cdot V)_{j}=\boldsymbol u\cdot \boldsymbol v_{j}"


def refine_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a reviewed-quality payload while preserving source and graph data."""

    result = deepcopy(dict(payload))
    topic_id = str(result.get("topic_id", ""))
    explanation = result.setdefault("explanation", {})
    visual = result.setdefault("visual_semantics", {})
    example = _first_example(explanation)

    if topic_id == "ch01.ops.addition":
        _refine_vector_addition(explanation, visual, example)
        result["connections"] = []
        section_ids = [str(section.get("id")) for section in explanation.get("sections", []) if isinstance(section, Mapping) and section.get("id")]
        stage_ids = [str(stage.get("id")) for stage in visual.get("stages", []) if isinstance(stage, Mapping) and stage.get("id")]
        for claim in result.get("claims", []):
            if isinstance(claim, dict):
                claim["explanation_refs"] = section_ids
                claim["formula"] = r"\boldsymbol a+\boldsymbol b=(x_1+x_2,\,y_1+y_2)"
                claim["formula_symbols"] = ["a", "b"]
                claim["entity_refs"] = ["flow_a", "flow_b", "flow_sum"]
                claim["relation_refs"] = ["rel.addition.flow"]
                claim["stage_refs"] = stage_ids
    elif topic_id == "ch01.vector.magnitude":
        _refine_vector_magnitude(explanation, visual, example)
        result["connections"] = []
        section_ids = [str(section.get("id")) for section in explanation.get("sections", []) if isinstance(section, Mapping) and section.get("id")]
        stage_ids = [str(stage.get("id")) for stage in visual.get("stages", []) if isinstance(stage, Mapping) and stage.get("id")]
        for claim in result.get("claims", []):
            if isinstance(claim, dict):
                claim["explanation_refs"] = section_ids
                claim["formula"] = r"\lvert\boldsymbol v\rvert=\sqrt{x^2+y^2}"
                claim["formula_symbols"] = ["v"]
                claim["entity_refs"] = ["nonzero_v", "nonzero_length", "zero_v"]
                claim["relation_refs"] = ["rel.magnitude.nonzero", "rel.magnitude.zero"]
                claim["stage_refs"] = stage_ids
    elif topic_id == "ch01.ops.subtraction":
        _refine_vector_subtraction(explanation, visual)
        result["connections"] = []
        for claim in result.get("claims", []):
            if isinstance(claim, dict):
                claim["explanation_refs"] = [
                    "definition", "formula", "worked_examples", "geometric_meaning"
                ]
                claim["formula"] = r"\boldsymbol a-\boldsymbol b=\boldsymbol a+(-\boldsymbol b)"
                claim["formula_symbols"] = ["a", "b"]
    elif topic_id == "ch01.ops.scalar":
        _refine_vector_scalar(explanation, visual)
        result["connections"] = []
        for claim in result.get("claims", []):
            if isinstance(claim, dict):
                claim["explanation_refs"] = [
                    "definition", "formula", "worked_examples", "geometric_meaning"
                ]
                claim["formula"] = r"k\boldsymbol a=(kx,\,ky)"
                claim["formula_symbols"] = ["k", "a"]
    elif topic_id == "ch01.ops.linear-combination":
        _refine_linear_combination(explanation, visual)
        result["connections"] = []
        for claim in result.get("claims", []):
            if isinstance(claim, dict):
                claim["explanation_refs"] = ["definition", "formula", "worked_examples", "geometric_meaning"]
                claim["formula"] = r"\alpha_1\boldsymbol v_1+\cdots+\alpha_n\boldsymbol v_n"
                claim["formula_symbols"] = ["v_1", "v_2", "alpha_1", "alpha_2"]
    elif topic_id in _PROOF_TOPIC_SPECS:
        _refine_geometry_proof(topic_id, explanation, visual)
        result["connections"] = []
        for claim in result.get("claims", []):
            if isinstance(claim, dict):
                # 声明只能引用产物实际保留的分节。
                claim["explanation_refs"] = [
                    str(section["id"])
                    for section in explanation.get("sections", [])
                    if isinstance(section, Mapping) and section.get("id")
                ]
                claim["formula"] = str(explanation.get("formula", ""))
                claim["formula_symbols"] = ["a", "b"]
    elif topic_id == "ch01.inner.cauchy-schwarz":
        _refine_cauchy_schwarz(explanation, visual)
        result["connections"] = []
        for claim in result.get("claims", []):
            if isinstance(claim, dict):
                claim["statement"] = "对任意两个向量，内积的绝对值不超过模长之积；等号成立当且仅当两个向量共线。"
                claim["explanation_refs"] = ["definition", "derivation", "worked_examples"]
                claim["formula"] = r"\lvert\boldsymbol a\cdot\boldsymbol b\rvert\leq\lvert\boldsymbol a\rvert\cdot\lvert\boldsymbol b\rvert"
                claim["formula_symbols"] = ["a", "b"]
    elif topic_id.startswith("ch01.inner.") or topic_id.startswith("ch01.projection.") or topic_id.startswith("ch01.proof."):
        _refine_remaining_chapter_one(topic_id, explanation, visual)
        result["connections"] = []
        symbols_by_topic = {
            "ch01.inner.definitions": ["a", "b"],
            "ch01.inner.cauchy-schwarz": ["a", "b"],
            "ch01.projection.definition": ["v", "u", "p", "r"],
            "ch01.proof.midline": ["a", "b"],
            "ch01.proof.centroid": ["a", "b"],
            "ch01.proof.parallelogram-diagonals": ["a", "b"],
        }
        for claim in result.get("claims", []):
            if isinstance(claim, dict):
                # 1.3.1 的公式已并入"定义"。
                claim["explanation_refs"] = [
                    str(section["id"])
                    for section in explanation.get("sections", [])
                    if isinstance(section, Mapping) and section.get("id")
                ]
                claim["formula"] = str(explanation.get("formula", ""))
                claim["formula_symbols"] = symbols_by_topic.get(topic_id, ["a", "b"])
    elif topic_id in _SUBSPACE_LESSON_SPECS:
        _refine_subspace_lesson(topic_id, explanation, visual)
        spec = _SUBSPACE_LESSON_SPECS[topic_id]
        result["connections"] = []
        for claim in result.get("claims", []):
            if isinstance(claim, dict):
                # 本节只保留"定义"和"数学案例"。
                claim["explanation_refs"] = [
                    str(section["id"])
                    for section in explanation.get("sections", [])
                    if isinstance(section, Mapping) and section.get("id")
                ]
                claim["statement"] = str(spec["statement"])
                claim["formula"] = str(spec["claim_formula"])
                claim["formula_symbols"] = [str(item) for item in spec["formula_symbols"]]
    elif topic_id in _MATRIX_VECTOR_TOPIC_SPECS:
        _refine_matrix_vector_subsection(topic_id, explanation, visual)
        spec = _MATRIX_VECTOR_TOPIC_SPECS[topic_id]
        result["connections"] = []
        for claim in result.get("claims", []):
            if isinstance(claim, dict):
                # 2.5 的公式已并入定义和例题。
                claim["explanation_refs"] = [
                    str(section["id"])
                    for section in explanation.get("sections", [])
                    if isinstance(section, Mapping) and section.get("id")
                ]
                claim["statement"] = str(spec["statement"])
                claim["formula"] = str(spec["claim_formula"])
                claim["formula_symbols"] = [str(item) for item in spec["formula_symbols"]]
    elif topic_id == "ch02.batch.inner-products":
        _refine_batch_inner_products(explanation, visual)
        result["connections"] = []
        for claim in result.get("claims", []):
            if isinstance(claim, dict):
                # 定义 2.4 自带公式，声明仅保留机器可读简写。
                claim["statement"] = "行向量乘矩阵，结果的每一列是 u 与 V 对应列的内积——一次算出一批方向。"
                claim["formula"] = _BATCH_INNER_PRODUCT_FORMULA
                claim["formula_symbols"] = ["u", "V"]
    elif topic_id == "ch02.batch.projection":
        _refine_batch_projection(explanation, visual)
        result["connections"] = []
        for claim in result.get("claims", []):
            if isinstance(claim, dict):
                # 定义 2.5 自带公式，声明只保留机器可读形式。
                claim["statement"] = "单位向量 u 确定的投影矩阵 P=uu^T，把任意向量 v 投影到 u 方向。"
                claim["formula"] = (
                    r"P=uu^{\mathsf T},\quad "
                    r"P\boldsymbol v=(\boldsymbol u\cdot\boldsymbol v)\boldsymbol u"
                )
                claim["formula_symbols"] = ["P", "u", "v"]
    elif topic_id == "ch02.matrix.composition":
        _refine_matrix_composition(result, explanation, visual, example)
    elif topic_id == "ch03.det.oriented-area":
        _refine_det_geometry(explanation, visual)
        result["connections"] = []
        for claim in result.get("claims", []):
            if isinstance(claim, dict):
                # 3.1 的公式已并入"定义"，声明仅保留机器可读简写。
                claim["statement"] = "行列式等于以矩阵两列为邻边的平行四边形的有向面积，按 ad-bc 计算。"
                claim["formula"] = _DET_GEOMETRY_FORMULA
                claim["formula_symbols"] = ["a", "b", "area"]
    else:
        _refine_generic(topic_id, explanation, visual, example)

    # 第 2 至 8 章先合并讲义原文，再同步声明引用。
    from linear_algebra.teaching import lecture_content

    lecture_content.apply(result)
    if topic_id == "ch04.subspace.col-null":
        _refine_linear_space(result, explanation, visual)
    elif topic_id == "ch04.dependence.redundancy":
        _refine_linear_dependence(result, explanation, visual)
    elif topic_id == "ch04.basis.definition":
        _refine_basis_definition(result, explanation, visual)
    elif topic_id == "ch04.linear-map.definition":
        _refine_linear_map_definition(result, explanation, visual)

    # 案例布局变化后，将声明重新绑定到实际发布的实体、关系和阶段。
    for claim in result.get("claims", []):
        if isinstance(claim, dict):
            claim["entity_refs"] = [str(item["id"]) for item in visual.get("entities", []) if isinstance(item, Mapping) and item.get("id")]
            claim["relation_refs"] = [str(item["id"]) for item in visual.get("relations", []) if isinstance(item, Mapping) and item.get("id")]
            claim["stage_refs"] = [str(item["id"]) for item in visual.get("stages", []) if isinstance(item, Mapping) and item.get("id")]

    _sync_sections(explanation)
    # 合并讲义后，声明只能引用最终发布的分节。
    section_ids = [
        str(section["id"])
        for section in explanation.get("sections", [])
        if isinstance(section, Mapping) and section.get("id")
    ]
    for claim in result.get("claims", []):
        if isinstance(claim, dict):
            claim["explanation_refs"] = section_ids
    _sync_searchable_text(explanation)
    generated = result.setdefault("generated", {})
    generated.update({
        "provider": "math-explanation-sample",
        "model": "lecture-grounded-v2",
        "prompt_version": "teaching-artifact-v1",
    })
    return result


_DET_GEOMETRY_FORMULA = r"\det(\begin{pmatrix}a&b\\c&d\end{pmatrix})=ad-bc"

_COL_NULL_DEFINITION = "\n\n".join(
    (
        r"定义 4.3（列空间） $\operatorname{Col}(A) = \{Ax \mid x \in R^{n}\} = A$ 所有列向量的全部线性组合 $=$ 所有可能的输出。",
        r"列空间是子空间（含零向量 $+$ 加法/数乘封闭）。",
        r"定义 4.4（零空间） $\operatorname{Null}(A) = \{x \mid Ax = 0\} =$ 被变换压缩到零的全部输入。",
        r"零空间也是子空间。",
    )
)
_COL_NULL_PROOF = "\n\n".join(
    (
        r"Col(A) 是子空间的证明: $① 0 = A \cdot 0 \in \operatorname{Col}(A)$；",
        r"② 加法：$A \cdot x_{1}\in\operatorname{Col}(A), A \cdot x_{2}\in\operatorname{Col}(A) \rightarrow A \cdot x_{1}+A \cdot x_{2} = A \cdot (x_{1}+x_{2}) \in \operatorname{Col}(A) ✓$；",
        r"③ 数乘：$k \cdot (A \cdot x) = A \cdot (kx) \in \operatorname{Col}(A) ✓$。$\rightarrow \operatorname{Col}(A)$ 是子空间。",
        r"Null(A) 是子空间的证明: $① A \cdot 0 = 0 \rightarrow 0 \in \operatorname{Null}(A)$；",
        r"② 加法：$x_{1},x_{2}\in\operatorname{Null}(A) \rightarrow A \cdot (x_{1}+x_{2}) = 0 \rightarrow x_{1}+x_{2}\in\operatorname{Null}(A) ✓$；",
        r"③ 数乘：$A \cdot (kx) = k \cdot A \cdot x = k \cdot 0 = 0 \rightarrow kx\in\operatorname{Null}(A) ✓$。$\rightarrow \operatorname{Null}(A)$ 是子空间。",
    )
)
_COL_NULL_GEOMETRY = "\n".join(
    (
        r"几何直观：",
        r"$A = \begin{pmatrix}1 & 0 \\ 0 & 0\end{pmatrix}$（投影到 x 轴）",
        r"$\operatorname{Col}(A) = x$ 轴 $\leftarrow$ 能输出到的所有地方",
        r"$\operatorname{Null}(A) = y$ 轴 $\leftarrow$ 被压到零的全部方向",
    )
)
# 4.1.3 的不变量使用讲义原句，不暴露内部校验标识。
_COL_NULL_INVARIANTS = (
    r"$\operatorname{Col}(A)$ 含零向量，且对加法和数乘封闭。",
    r"$\operatorname{Null}(A)$ 含零向量，且对加法和数乘封闭。",
)


def _refine_col_null(result: dict[str, Any], explanation: dict[str, Any], visual: dict[str, Any]) -> None:
    """Keep 4.1.3 lecture prose verbatim and add the two checked 3D cases.

    讲义只给出二维直观图（$A=\\begin{pmatrix}1&0\\\\0&0\\end{pmatrix}$ 把平面压到 $x$ 轴）。
    三维案例把它升一维：$A=\\operatorname{diag}(1,1,0)$ 把空间压到 $xy$ 平面，于是
    「所有可能的输出」是那张平面，「被压到零的全部输入」是那条竖直的 $z$ 轴。
    两个案例各自回答定义 4.3、定义 4.4 中的一个，因此各自独立成一个窗格。
    """

    claim_id = "claim.ch04.subspace.col-null"
    column_example_id = "example.ch04.subspace.col-null.column-space"
    null_example_id = "example.ch04.subspace.col-null.null-space"
    projection_matrix = r"\boldsymbol A=\begin{pmatrix}1&0&0\\0&1&0\\0&0&0\end{pmatrix}"
    explanation.update(
        {
            "summary": _COL_NULL_DEFINITION.split("\n\n", 1)[0],
            "definition": _COL_NULL_DEFINITION,
            "formula": "",
            "derivation": [_COL_NULL_PROOF],
            # 分节顺序与讲义一致。
            "geometric_meaning": _COL_NULL_GEOMETRY,
            "worked_examples": [
                {
                    "id": column_example_id,
                    "title": "案例一：列空间——所有可能的输出",
                    "kind": "matrix_transform",
                    "given": [[[1, 0, 0], [0, 1, 0], [0, 0, 0]], [2, 0, 3]],
                    "calculation": [
                        r"$$" + projection_matrix + r"$$",
                        r"$$\boldsymbol x_1=(2,0,3)^{\mathsf T},\qquad \boldsymbol x_2=(-1,2,2)^{\mathsf T},\qquad \boldsymbol x_3=(-1,-2,1)^{\mathsf T}$$",
                        r"$$\boldsymbol A\boldsymbol x_1=(2,0,0)^{\mathsf T},\qquad \boldsymbol A\boldsymbol x_2=(-1,2,0)^{\mathsf T},\qquad \boldsymbol A\boldsymbol x_3=(-1,-2,0)^{\mathsf T}$$",
                        r"三支输入的高度、水平方向都不同，可它们的输出全部落在同一张平面上，并且朝平面里三个不同的方向铺开。",
                        r"$$\operatorname{Col}(\boldsymbol A)=\{\boldsymbol A\boldsymbol x\mid \boldsymbol x\in R^{3}\}=\operatorname{span}(\boldsymbol e_1,\boldsymbol e_2)$$",
                        r"所以 $\operatorname{Col}(\boldsymbol A)$ 就是这张平面：无论输入取什么，输出只会落在这里。",
                    ],
                    "result": [2.0, 0.0, 0.0],
                    "checks": [{"name": "result", "expected": [2.0, 0.0, 0.0], "tolerance": 1e-9}],
                    "claim_refs": [claim_id],
                },
                {
                    "id": null_example_id,
                    "title": "案例二：零空间——与平面垂直的输入被压成一点",
                    "kind": "matrix_transform",
                    "given": [[[1, 0, 0], [0, 1, 0], [0, 0, 0]], [0, 0, 3]],
                    "calculation": [
                        r"$$" + projection_matrix + r"$$",
                        r"$$\boldsymbol k=(0,0,3)^{\mathsf T}$$",
                        r"$$\boldsymbol A\boldsymbol k=(0,0,0)^{\mathsf T}$$",
                        r"这支输入沿着 $z$ 方向，也就是垂直于那张平面；它被压到原点。",
                        r"$$\operatorname{Null}(\boldsymbol A)=\{\boldsymbol x\mid \boldsymbol A\boldsymbol x=0\}=\operatorname{span}(\boldsymbol e_3)$$",
                        r"反向看：不沿 $z$ 方向的输入不会被压成零——步骤①里的 $\boldsymbol x_1,\boldsymbol x_2,\boldsymbol x_3$ 输出都还落在平面上、离原点有距离。",
                        r"所以 $\operatorname{Null}(\boldsymbol A)$ 就是这条垂直于平面的方向：只有它上面的输入被压成零。",
                    ],
                    "result": [0.0, 0.0, 0.0],
                    "checks": [{"name": "result", "expected": [0.0, 0.0, 0.0], "tolerance": 1e-9}],
                    "claim_refs": [claim_id],
                },
            ],
            "pitfalls": [],
            "connections": [],
            "intuition": "",
            "read_guide": [],
            "invariants": list(_COL_NULL_INVARIANTS),
            "symbol_roles": {"x": "input_vector_a", "A": "column_space", "k": "kernel_vector"},
            "sections": [
                {"id": "definition", "title": "定义", "text": "", "claim_refs": [claim_id]},
                {"id": "geometric_meaning", "title": "几何直观", "text": "", "claim_refs": [claim_id]},
                {"id": "derivation", "title": "列空间和零空间为子空间的证明", "text": "", "claim_refs": [claim_id]},
                {"id": "worked_examples", "title": "数学案例", "text": "", "claim_refs": [claim_id]},
            ],
            "case_layout": {
                # 两步案例首屏并排并共用视角。
                "default_pane_count": 2,
                "cases": [
                    {
                        "id": "case.ch04.subspace.col-null.column-space",
                        "topic_id": "ch04.subspace.col-null",
                        "example_ref": column_example_id,
                        "claim_refs": [claim_id],
                        "stage_refs": ["stage.ch04.subspace.col-null.column_space"],
                        "purpose": "① 列空间：三支输入，输出都落在这张平面上",
                    },
                    {
                        "id": "case.ch04.subspace.col-null.null-space",
                        "topic_id": "ch04.subspace.col-null",
                        "example_ref": null_example_id,
                        "claim_refs": [claim_id],
                        "stage_refs": ["stage.ch04.subspace.col-null.null_space"],
                        "purpose": "② 零空间：与平面垂直的输入被压成一点",
                    },
                ],
            },
        }
    )
    for claim in result.get("claims", []):
        if isinstance(claim, dict):
            claim["explanation_refs"] = ["definition", "geometric_meaning", "derivation", "worked_examples"]
            claim["formula"] = r"\boldsymbol A=\operatorname{diag}(1,1,0),\quad \operatorname{Null}(\boldsymbol A)=\operatorname{span}(\boldsymbol e_3),\quad \operatorname{Col}(\boldsymbol A)=\operatorname{span}(\boldsymbol e_1,\boldsymbol e_2)"
            claim["formula_symbols"] = ["A", "x", "k"]


_LINEAR_SPACE_DEFINITION = "\n\n".join(
    (
        r"**（线性空间 / 向量空间）** 一个集合 $V$，如果满足两条核心规则，就称为一个线性空间：",
        r"（1）加法封闭：$\boldsymbol u,\boldsymbol v\in V\Rightarrow\boldsymbol u+\boldsymbol v\in V$。\n（2）数乘封闭：$\boldsymbol v\in V,\ k\in R\Rightarrow k\boldsymbol v\in V$。",
        r"主例——$R^{n}$：所有 $n$ 维实向量的集合。加法：分量相加；数乘：每个分量乘 $k$。结果仍在 $R^{n}$ 中，$\therefore R^{n}$ 是线性空间。",
        r"其他例子：所有次数 $\leq2$ 的多项式 $a+bx+cx^{2}$，两个多项式相加还是多项式，乘以常数仍是多项式，构成线性空间。所有 $2\times2$ 矩阵，矩阵加法、数乘封闭，构成线性空间。",
        r"线性空间 $=$ 对加法和数乘“封闭”的集合。核心不是元素是什么（向量、多项式、矩阵都行），而是加法和数乘的自由操作永不“溢出”这个集合。",
        r"完整的 $8$ 条公理（供参考，不要求背）：加法四条：交换律 $\boldsymbol u+\boldsymbol v=\boldsymbol v+\boldsymbol u$、结合律 $(\boldsymbol u+\boldsymbol v)+\boldsymbol w=\boldsymbol u+(\boldsymbol v+\boldsymbol w)$、存在零元 $\boldsymbol v+\boldsymbol{0}=\boldsymbol v$、存在负元 $\boldsymbol v+(-\boldsymbol v)=\boldsymbol{0}$。数乘四条：分配律 $k(\boldsymbol u+\boldsymbol v)=k\boldsymbol u+k\boldsymbol v$、$(k+l)\boldsymbol v=k\boldsymbol v+l\boldsymbol v$，结合律 $k(l\boldsymbol v)=(kl)\boldsymbol v$，单位元 $1\cdot\boldsymbol v=\boldsymbol v$。前两条（加法封闭 $+$ 数乘封闭）是最核心的判定条件，后六条是保证这些运算“行为正常”的底层规则。在 $R^{n}$ 中它们都自然成立。",
        r"**线性空间的基本性质**",
        r"**（零元素唯一）** 线性空间中的零元素是唯一的。若 $\boldsymbol{0}_{1}$ 和 $\boldsymbol{0}_{2}$ 都是零元，则 $\boldsymbol{0}_{1}=\boldsymbol{0}_{1}+\boldsymbol{0}_{2}=\boldsymbol{0}_{2}+\boldsymbol{0}_{1}=\boldsymbol{0}_{2}$。用了加法的交换律和零元的定义。",
        r"**（负元素唯一）** 每个向量的负元素是唯一的。若 $(-\boldsymbol v)_{1}$ 和 $(-\boldsymbol v)_{2}$ 都是 $\boldsymbol v$ 的负元，则 $\boldsymbol v+(-\boldsymbol v)_{1}=\boldsymbol{0}=\boldsymbol v+(-\boldsymbol v)_{2}$。两边加 $(-\boldsymbol v)_{1}$，得 $(-\boldsymbol v)_{1}=(-\boldsymbol v)_{2}$。",
        r"**（$0\cdot\boldsymbol v=\boldsymbol{0}$）** 标量 $0$ 乘任何向量得到零向量。$0\cdot\boldsymbol v=(0+0)\cdot\boldsymbol v=0\cdot\boldsymbol v+0\cdot\boldsymbol v$。两边加 $-0\cdot\boldsymbol v$，得 $\boldsymbol{0}=0\cdot\boldsymbol v$。",
        r"**（$k\cdot\boldsymbol{0}=\boldsymbol{0}$）** 任何标量乘零向量等于零向量。$k\cdot\boldsymbol{0}=k\cdot(\boldsymbol{0}+\boldsymbol{0})=k\cdot\boldsymbol{0}+k\cdot\boldsymbol{0}$。两边加 $-k\cdot\boldsymbol{0}$，得 $\boldsymbol{0}=k\cdot\boldsymbol{0}$。",
        r"**（$(-1)\cdot\boldsymbol v=-\boldsymbol v$）** 标量 $-1$ 乘向量得到该向量的负元。$\boldsymbol v+(-1)\cdot\boldsymbol v=1\cdot\boldsymbol v+(-1)\cdot\boldsymbol v=(1+(-1))\cdot\boldsymbol v=0\cdot\boldsymbol v=\boldsymbol{0}$，$\therefore(-1)\cdot\boldsymbol v$ 满足负元的定义，由唯一性知 $(-1)\cdot\boldsymbol v=-\boldsymbol v$。",
        r"**（子空间）** $V$ 的子集 $H$ 称为子空间，当且仅当满足三条：\n1. 零向量在 $H$ 中（不含零向量的子集不可能是子空间）。\n2. 加法封闭：$\boldsymbol u,\boldsymbol v\in H\Rightarrow\boldsymbol u+\boldsymbol v\in H$。\n3. 数乘封闭：$\boldsymbol v\in H,\ k\in R\Rightarrow k\boldsymbol v\in H$。",
        r"几何理解：$R^{3}$ 中的子空间只有四种——$\{\boldsymbol{0}\}$（原点）、过原点的直线、过原点的平面、整个 $R^{3}$。不经过原点的直线/平面不是子空间（不包含零向量）。",
        r"子空间的基本性质：任何子空间必含零向量；两个子空间的交集仍是子空间；子空间的维数 $\leq$ 原空间的维数，即 $\dim(H)\leq\dim(V)$。一个平面（$\dim=2$）的子空间只能是直线（$\dim=1$）、原点（$\dim=0$）、或这个平面本身（$\dim=2$），不可能出现 $\dim=3$ 的子空间。",
        r"**（子空间交集仍是子空间）** 设 $H_{1},H_{2}$ 是 $V$ 的子空间。考虑 $H=H_{1}\cap H_{2}$。$\boldsymbol{0}\in H_{1}$ 且 $\boldsymbol{0}\in H_{2}\Rightarrow\boldsymbol{0}\in H$。取 $\boldsymbol u,\boldsymbol v\in H$，则它们同时在 $H_{1}$ 和 $H_{2}$ 中；$H_{1}$、$H_{2}$ 加法封闭，$\therefore\boldsymbol u+\boldsymbol v\in H$。同理，$k\boldsymbol u\in H_{1}$ 且 $k\boldsymbol u\in H_{2}\Rightarrow k\boldsymbol u\in H$，$\therefore H$ 是子空间。注：子空间的并集一般不是子空间。例如 $R^{2}$ 中 $x$ 轴 $\cup y$ 轴，取 $(1,0)+(0,1)=(1,1)$ 不在并集中——加法不封闭。",
        r"例 $4$（子空间判定——过原点的平面）：$H=\{(x,y,z)\mid x+y+z=0\}$ 是 $R^{3}$ 的子空间。$0+0+0=0$，零向量在 $H$ 中；两组满足条件的坐标相加仍满足和为 $0$；$k(x,y,z)=(kx,ky,kz)$ 且 $kx+ky+kz=k(x+y+z)=0$，数乘封闭。几何上：这是过原点的一个平面。",
        r"分层例题：$H=\{(x,0)\mid x\in R\}$ 是 $R^{2}$ 的子空间：零向量在其中，且对加法、数乘封闭（$x$ 轴）。$H=\{(x,1)\mid x\in R\}$ 不是：$\boldsymbol{0}=(0,0)\notin H$。$H=\{(x,x^{2})\mid x\in R\}$ 不是：$(1,1),(2,4)\in H$，但 $(1,1)+(2,4)=(3,5)$，$5\ne3^{2}=9$，加法不封闭。",
        r"**（列空间）** $\operatorname{Col}(\boldsymbol A)=\{\boldsymbol A\boldsymbol x\mid\boldsymbol x\in R^{n}\}=\boldsymbol A$ 所有列向量的全部线性组合 $=$ 所有可能的输出。列空间是子空间（含零向量 $+$ 加法/数乘封闭）。",
        r"**（零空间）** $\operatorname{Null}(\boldsymbol A)=\{\boldsymbol x\mid\boldsymbol A\boldsymbol x=\boldsymbol{0}\}=$ 被变换压缩到零的全部输入。零空间也是子空间。",
        r"几何直观：$$\boldsymbol A=\begin{pmatrix}1&0\\0&0\end{pmatrix}$$（投影到 $x$ 轴）。$\operatorname{Col}(\boldsymbol A)=x$ 轴，能输出到的所有地方；$\operatorname{Null}(\boldsymbol A)=y$ 轴，被压到零的全部方向。",
        r"**（列空间和零空间为子空间）** $\operatorname{Col}(\boldsymbol A)$ 含零向量：$\boldsymbol{0}=\boldsymbol A\boldsymbol{0}\in\operatorname{Col}(\boldsymbol A)$。若 $\boldsymbol A\boldsymbol x_{1},\boldsymbol A\boldsymbol x_{2}\in\operatorname{Col}(\boldsymbol A)$，则 $\boldsymbol A\boldsymbol x_{1}+\boldsymbol A\boldsymbol x_{2}=\boldsymbol A(\boldsymbol x_{1}+\boldsymbol x_{2})\in\operatorname{Col}(\boldsymbol A)$；$k(\boldsymbol A\boldsymbol x)=\boldsymbol A(k\boldsymbol x)\in\operatorname{Col}(\boldsymbol A)$。$\operatorname{Null}(\boldsymbol A)$ 含零向量：$\boldsymbol A\boldsymbol{0}=\boldsymbol{0}$。若 $\boldsymbol x_{1},\boldsymbol x_{2}\in\operatorname{Null}(\boldsymbol A)$，则 $\boldsymbol A(\boldsymbol x_{1}+\boldsymbol x_{2})=\boldsymbol{0}$；$\boldsymbol A(k\boldsymbol x)=k\boldsymbol A\boldsymbol x=k\boldsymbol{0}=\boldsymbol{0}$。",
        r"自检：$R^{2}$ 中不经过原点的直线是子空间吗？为什么？判断 $H=\{(x,2x)\mid x\in R\}$ 是否为 $R^{2}$ 的子空间。$\operatorname{Col}(\boldsymbol A)$ 和 $\operatorname{Null}(\boldsymbol A)$ 分别描述变换的什么？它们为什么一定是子空间？",
    )
)


def _refine_linear_space(result: dict[str, Any], explanation: dict[str, Any], visual: dict[str, Any]) -> None:
    """Publish merged lecture section 4.1 and its two confirmed 3D case panes."""

    claim_id = "claim.ch04.subspace.col-null"
    column_example_id = "example.ch04.subspace.col-null.column-space"
    null_example_id = "example.ch04.subspace.col-null.null-space"
    projection_matrix = r"\boldsymbol A=\begin{pmatrix}1&0&0\\0&1&0\\0&0&0\end{pmatrix}"
    explanation.update(
        {
            "summary": "线性空间是对加法和数乘封闭的集合。",
            "definition": _LINEAR_SPACE_DEFINITION,
            "formula": "",
            "derivation": [],
            "geometric_meaning": "",
            "worked_examples": [
                {
                    "id": column_example_id,
                    "title": "案例一：列空间——所有可能的输出",
                    "kind": "matrix_transform",
                    "given": [[[1, 0, 0], [0, 1, 0], [0, 0, 0]], [2, 1, 3]],
                    "calculation": [
                        r"$$" + projection_matrix + r"$$",
                        r"$$\boldsymbol x_1=\begin{pmatrix}2\\1\\3\end{pmatrix},\qquad \boldsymbol x_2=\begin{pmatrix}-2\\1\\2\end{pmatrix},\qquad \boldsymbol x_3=\begin{pmatrix}-1\\-2\\-2\end{pmatrix}$$",
                        r"$$\boldsymbol A\boldsymbol x_1=\begin{pmatrix}2\\1\\0\end{pmatrix},\qquad \boldsymbol A\boldsymbol x_2=\begin{pmatrix}-2\\1\\0\end{pmatrix},\qquad \boldsymbol A\boldsymbol x_3=\begin{pmatrix}-1\\-2\\0\end{pmatrix}$$",
                        r"$$\operatorname{Col}(\boldsymbol A)=\{\boldsymbol A\boldsymbol x\mid\boldsymbol x\in R^{3}\}=\operatorname{span}(\boldsymbol e_1,\boldsymbol e_2)$$",
                    ],
                    "result": [2.0, 1.0, 0.0],
                    "checks": [{"name": "result", "expected": [2.0, 1.0, 0.0], "tolerance": 1e-9}],
                    "claim_refs": [claim_id],
                },
                {
                    "id": null_example_id,
                    "title": "案例二：零空间——与平面垂直的输入被压成一点",
                    "kind": "matrix_transform",
                    "given": [[[1, 0, 0], [0, 1, 0], [0, 0, 0]], [0, 0, 3]],
                    "calculation": [
                        r"$$" + projection_matrix + r"$$",
                        r"$$\boldsymbol k=\begin{pmatrix}0\\0\\3\end{pmatrix}$$",
                        r"$$\boldsymbol A\boldsymbol k=\begin{pmatrix}0\\0\\0\end{pmatrix}$$",
                        r"$$\operatorname{Null}(\boldsymbol A)=\{\boldsymbol x\mid\boldsymbol A\boldsymbol x=\boldsymbol{0}\}=\operatorname{span}(\boldsymbol e_3)$$",
                    ],
                    "result": [0.0, 0.0, 0.0],
                    "checks": [{"name": "result", "expected": [0.0, 0.0, 0.0], "tolerance": 1e-9}],
                    "claim_refs": [claim_id],
                },
            ],
            "pitfalls": [],
            "connections": [],
            "intuition": "",
            "read_guide": [],
            "invariants": [],
            "symbol_roles": {"x": "input_vector_a", "A": "column_space", "k": "kernel_vector"},
            "sections": [
                {"id": "definition", "title": "定义", "text": "", "claim_refs": [claim_id]},
                {"id": "worked_examples", "title": "数学案例", "text": "", "claim_refs": [claim_id]},
            ],
            "case_layout": {
                "default_pane_count": 2,
                "cases": [
                    {"id": "case.ch04.subspace.col-null.column-space", "topic_id": "ch04.subspace.col-null", "example_ref": column_example_id, "claim_refs": [claim_id], "stage_refs": ["stage.ch04.subspace.col-null.column_space"], "purpose": "① 列空间：三支输入，输出都落在这张平面上"},
                    {"id": "case.ch04.subspace.col-null.null-space", "topic_id": "ch04.subspace.col-null", "example_ref": null_example_id, "claim_refs": [claim_id], "stage_refs": ["stage.ch04.subspace.col-null.null_space"], "purpose": "② 零空间：与平面垂直的输入被压成一点"},
                ],
            },
        }
    )
    for claim in result.get("claims", []):
        if isinstance(claim, dict):
            claim["explanation_refs"] = ["definition", "worked_examples"]
            claim["formula"] = r"\boldsymbol A=\begin{pmatrix}1&0&0\\0&1&0\\0&0&0\end{pmatrix},\quad \operatorname{Null}(\boldsymbol A)=\operatorname{span}(\boldsymbol e_3),\quad \operatorname{Col}(\boldsymbol A)=\operatorname{span}(\boldsymbol e_1,\boldsymbol e_2)"
            claim["formula_symbols"] = ["A", "x", "k"]


_LINEAR_DEPENDENCE_DEFINITION = "\n\n".join(
    (
        r"**（生成集）** $\operatorname{Span}\{\boldsymbol v_{1},...,\boldsymbol v_{k}\} = \{$ 这些向量的所有线性组合 $\}$。",
        r"几何：$\operatorname{Span}\{\boldsymbol v\} =$ 过原点的直线；$\operatorname{Span}\{\boldsymbol u,\boldsymbol v\}$（不共线）$=$ 过原点的平面；$\operatorname{Span}\{\boldsymbol u,\boldsymbol v,\boldsymbol w\}$（不共面）$=$ 整个 $R^{3}$。",
        r"**（线性无关）** $\boldsymbol v_{1},...,\boldsymbol v_{k}$ 线性无关 $\Leftrightarrow c_{1}\boldsymbol v_{1}+...+c_{k}\boldsymbol v_{k}=\boldsymbol 0$ 只有全零解 $c_{1}=...=c_{k}=0$。",
        r"**（线性相关）** 存在不全为零的系数使组合为零 $\Leftrightarrow$ 有向量是\"冗余\"的。",
        "\n".join(
            (
                r"| 情况 | 无关 | 相关 |",
                r"| --- | --- | --- |",
                r"| 2个在$R^{2}$ | 不共线 | 共线 |",
                r"| 3个在$R^{2}$ | 不可能 | 必相关 |",
                r"| 3个在$R^{3}$ | 不共面 | 共面 |",
            )
        ),
    )
)


def _refine_linear_dependence(result: dict[str, Any], explanation: dict[str, Any], visual: dict[str, Any]) -> None:
    """Publish 4.2.1–4.2.2 with the confirmed line/plane/space/redundancy cases."""

    claim_id = "claim.ch04.dependence.redundancy"
    line_example_id = "example.ch04.dependence.redundancy.line"
    plane_example_id = "example.ch04.dependence.redundancy.plane"
    independent_example_id = "example.ch04.dependence.redundancy.independent"
    dependent_example_id = "example.ch04.dependence.redundancy.dependent"
    explanation.update(
        {
            "summary": "",
            "definition": _LINEAR_DEPENDENCE_DEFINITION,
            "formula": "",
            "derivation": [],
            "geometric_meaning": "",
            "worked_examples": [
                {
                    "id": line_example_id,
                    "title": "案例一：一根向量张成直线",
                    "kind": "scalar_multiple",
                    "given": [2, [1, 0, 0]],
                    "calculation": [
                        r"$$\boldsymbol u=\begin{pmatrix}1\\0\\0\end{pmatrix}$$",
                        r"$$\operatorname{Span}\{\boldsymbol u\}=\{t\boldsymbol u\mid t\in R\}=\left\{\begin{pmatrix}t\\0\\0\end{pmatrix}\middle|t\in R\right\}$$",
                        r"当 $t$ 取遍 $R$，所有线性组合都落在经过原点、沿着 $\boldsymbol u$ 方向的直线上。",
                        r"图中取 $t=2$，得到 $2\boldsymbol u=\begin{pmatrix}2\\0\\0\end{pmatrix}$。",
                    ],
                    "result": [2.0, 0.0, 0.0],
                    "checks": [{"name": "result", "expected": [2.0, 0.0, 0.0], "tolerance": 1e-9}],
                    "claim_refs": [claim_id],
                },
                {
                    "id": plane_example_id,
                    "title": "案例二：两根不共线向量张成平面",
                    "kind": "linear_combination",
                    "given": [[[1, 0, 0], [0, 1, 0]], [2, -1]],
                    "calculation": [
                        r"$$\boldsymbol u=\begin{pmatrix}1\\0\\0\end{pmatrix},\qquad \boldsymbol v=\begin{pmatrix}0\\1\\0\end{pmatrix}$$",
                        r"$$a\boldsymbol u+b\boldsymbol v=\begin{pmatrix}a\\b\\0\end{pmatrix},\qquad a,b\in R$$",
                        r"$\boldsymbol u$ 与 $\boldsymbol v$ 不共线；它们的所有线性组合第三个分量都为 $0$，恰好铺满经过原点的平面。",
                        r"图中取 $a=2,b=-1$，得到 $2\boldsymbol u-\boldsymbol v=\begin{pmatrix}2\\-1\\0\end{pmatrix}$。",
                    ],
                    "result": [2.0, -1.0, 0.0],
                    "checks": [{"name": "result", "expected": [2.0, -1.0, 0.0], "tolerance": 1e-9}],
                    "claim_refs": [claim_id],
                },
                {
                    "id": independent_example_id,
                    "title": "案例三：加入平面外方向后张成整个三维空间",
                    "kind": "linear_combination",
                    "given": [[[1, 0, 0], [0, 1, 0], [0, 0, 1]], [1, 1, 1]],
                    "calculation": [
                        r"$$\boldsymbol u=\begin{pmatrix}1\\0\\0\end{pmatrix},\qquad \boldsymbol v=\begin{pmatrix}0\\1\\0\end{pmatrix},\qquad \boldsymbol w=\begin{pmatrix}0\\0\\1\end{pmatrix}$$",
                        r"$$\boldsymbol x=\begin{pmatrix}a\\b\\c\end{pmatrix}=a\boldsymbol u+b\boldsymbol v+c\boldsymbol w$$",
                        r"任意 $\boldsymbol x\in R^{3}$ 都能写成这三根不共面向量的线性组合，所以它们张成整个 $R^{3}$。图中取 $a=b=c=1$ 显示一个组合。",
                        r"$$c_1\boldsymbol u+c_2\boldsymbol v+c_3\boldsymbol w=\boldsymbol 0\ \Longrightarrow\ \begin{pmatrix}c_1\\c_2\\c_3\end{pmatrix}=\begin{pmatrix}0\\0\\0\end{pmatrix}$$",
                        r"这个组合只有全零解，因此 $\boldsymbol u,\boldsymbol v,\boldsymbol w$ 线性无关。",
                    ],
                    "result": [1.0, 1.0, 1.0],
                    "checks": [{"name": "result", "expected": [1.0, 1.0, 1.0], "tolerance": 1e-9}],
                    "claim_refs": [claim_id],
                },
                {
                    "id": dependent_example_id,
                    "title": "案例四：加入冗余方向后仍只张成原平面",
                    "kind": "linear_combination",
                    "given": [[[1, 0, 0], [0, 1, 0], [1, 1, 0]], [1, 1, -1]],
                    "calculation": [
                        r"$$\boldsymbol u=\begin{pmatrix}1\\0\\0\end{pmatrix},\qquad \boldsymbol v=\begin{pmatrix}0\\1\\0\end{pmatrix},\qquad \boldsymbol w=\begin{pmatrix}1\\1\\0\end{pmatrix}$$",
                        r"$$\boldsymbol u+\boldsymbol v-\boldsymbol w=\begin{pmatrix}1\\0\\0\end{pmatrix}+\begin{pmatrix}0\\1\\0\end{pmatrix}-\begin{pmatrix}1\\1\\0\end{pmatrix}=\begin{pmatrix}0\\0\\0\end{pmatrix}$$",
                        r"系数 $1,1,-1$ 不全为零，且三根向量共面，所以这组向量线性相关。",
                        r"$\boldsymbol w=\boldsymbol u+\boldsymbol v$，因此 $\boldsymbol w$ 是\"冗余\"的。",
                    ],
                    "result": [0.0, 0.0, 0.0],
                    "checks": [{"name": "result", "expected": [0.0, 0.0, 0.0], "tolerance": 1e-9}],
                    "claim_refs": [claim_id],
                },
            ],
            "pitfalls": [],
            "connections": [],
            "intuition": "",
            "conclusion": "",
            "analogy_boundary": "",
            "transfer_note": "",
            "read_guide": [],
            "invariants": [],
            "symbol_roles": {
                "u": "vector_a",
                "v": "vector_b",
                "w": "transformed_a",
            },
            "sections": [
                {"id": "definition", "title": "定义", "text": "", "claim_refs": [claim_id]},
                {"id": "worked_examples", "title": "数学案例", "text": "", "claim_refs": [claim_id]},
            ],
            "case_layout": {
                "default_pane_count": 4,
                "cases": [
                    {
                        "id": "case.ch04.dependence.redundancy.line",
                        "topic_id": "ch04.dependence.redundancy",
                        "example_ref": line_example_id,
                        "claim_refs": [claim_id],
                        "stage_refs": ["stage.ch04.dependence.redundancy.line"],
                        "purpose": "① 一根向量：张成直线",
                    },
                    {
                        "id": "case.ch04.dependence.redundancy.plane",
                        "topic_id": "ch04.dependence.redundancy",
                        "example_ref": plane_example_id,
                        "claim_refs": [claim_id],
                        "stage_refs": ["stage.ch04.dependence.redundancy.plane"],
                        "purpose": "② 两根不共线向量：张成平面",
                    },
                    {
                        "id": "case.ch04.dependence.redundancy.independent",
                        "topic_id": "ch04.dependence.redundancy",
                        "example_ref": independent_example_id,
                        "claim_refs": [claim_id],
                        "stage_refs": ["stage.ch04.dependence.redundancy.space"],
                        "purpose": "③ 加入平面外方向：张成整个三维空间",
                    },
                    {
                        "id": "case.ch04.dependence.redundancy.dependent",
                        "topic_id": "ch04.dependence.redundancy",
                        "example_ref": dependent_example_id,
                        "claim_refs": [claim_id],
                        "stage_refs": ["stage.ch04.dependence.redundancy.dependent"],
                        "purpose": "④ 加入冗余方向：仍只张成原平面",
                    },
                ],
            },
        }
    )
    for claim in result.get("claims", []):
        if isinstance(claim, dict):
            claim["explanation_refs"] = ["definition", "worked_examples"]
            claim["formula"] = r"\operatorname{Span}\{\boldsymbol v_1,\ldots,\boldsymbol v_k\}=\{\text{这些向量的所有线性组合}\}"
            claim["formula_symbols"] = []

# 4.3.1 至 4.3.3 合并为"定义"，仅修正数学定界符和集合花括号。
_BASIS_DEFINITION = "\n\n".join(
    (
        r"**（基）** $V$ 的一组基满足两个条件：",
        "\n".join(
            (
                r"1. 线性无关 —— 没有冗余",
                r"2. 生成整个空间 —— 任何向量都能写成基的线性组合",
            )
        ),
        r'基 $=$ "最小的完整尺子组"——少了量不全，多了有冗余。',
        r"标准基 $e_{1},...,e_{n}$ 是 $R^{n}$ 最常见的一组基。",
        "\n".join(
            (
                r"**（维数唯一性）** 同一空间任何基的向量个数相等。这个个数 $=$ 空间的维数 $\dim(V)$。",
                r"$R^{2}$ 的维数 $= 2$，$R^{3}$ 的维数 $= 3$。",
                r"维数的关键性质：",
                r"1. 若 $H$ 是 $V$ 的子空间，则 $\dim(H) \leq \dim(V)$",
                r"2. $\dim(R^{n}) = n$",
                r"3. 一组基恰好含有 $\dim(V)$ 个向量——不能多（多了必相关），不能少（少了张不满整个空间）",
                r'4. 若一组线性无关向量个数 $= \dim(V)$，则它自动构成一组基（不需要再验证"生成"条件）',
            )
        ),
        "\n".join(
            (
                r"**（坐标）** 给定基 $B=\{v_{1},...,v_{n}\}$，任何向量 $x$ 唯一写为 $x = c_{1}v_{1}+...+c_{n}v_{n}$。系数向量 $(c_{1},...,c_{n})$ 就是 $x$ 在基 $B$ 下的坐标。",
                r'坐标 $=$ 用一组基去"量"向量得到的读数。换一组基（换一套尺子），读数就变——这是第 6 章基变换的核心。',
            )
        ),
    )
)

# 保留讲义 4.3.2 的反证法原文。
_BASIS_PROOF = "\n\n".join(
    (
        r"设 $\{v_{1}, \dots ,v_{n}\}$ 是 $\dim(V)=n$ 的空间中 $n$ 个线性无关的向量。",
        r"若它们不生成 $V$，则存在 $w \in V$ 无法表示为它们的线性组合 $\rightarrow \{v_{1}, \dots ,v_{n},w\}$ 中有 $n+1$ 个向量线性无关 $\rightarrow$ 与 $\dim(V)=n$ 矛盾。",
        r"因此 $n$ 个线性无关向量必然生成整个空间，自动构成一组基。■",
    )
)

# 学生可见内容使用讲义原句，不显示内部校验标识。
_BASIS_INVARIANTS = (
    r"基的两个条件：线性无关——没有冗余；生成整个空间——任何向量都能写成基的线性组合。",
    r"标准基下 $x=5e_{1}+3e_{2}$，读数就是 $(5,3)$。",
    r"换一组基 $B=\{(1,1),(1,-1)\}$ 后 $x=4b_{1}+1b_{2}$，同一个向量的读数变成 $(4,1)$。",
)


def _refine_basis_definition(result: dict[str, Any], explanation: dict[str, Any], visual: dict[str, Any]) -> None:
    """搬入 4.3.1–4.3.3 的讲义原文，并给出例 4 的两窗格读数案例。

    讲义 4.3 只有一处推导（性质 4 的证明）和一个数值例子（例 4）。例 4 问的是「同一个
    向量换一组尺子之后读数是多少」，所以案例拆成两步：先在标准基这把尺子上读，再把尺子
    换成 $B=\\{(1,1),(1,-1)\\}$ 重新读。两步里那个点始终不动，动的只有尺子——这正是
    第 4.3.3 节"读数随基而变"的图形版，两步各占一个窗格、共用同一取景并排显示。
    """

    claim_id = "claim.ch04.basis.definition"
    standard_example_id = "example.ch04.basis.definition.standard"
    oblique_example_id = "example.ch04.basis.definition.oblique"
    basis_matrix = r"\begin{pmatrix}1&1\\1&-1\end{pmatrix}"
    explanation.update(
        {
            "summary": _BASIS_DEFINITION.split("\n\n", 1)[0],
            "definition": _BASIS_DEFINITION,
            "formula": "",
            "derivation": [_BASIS_PROOF],
            "worked_examples": [
                {
                    "id": standard_example_id,
                    "title": "第一步：标准基下的读数",
                    "kind": "matrix_transform",
                    # 输入为点和默认基。
                    "given": [[[1, 0], [0, 1]], [5, 3]],
                    "calculation": [
                        r"$$\boldsymbol x=(5,3)$$",
                        r"标准基 $e_{1}=(1,0)$、$e_{2}=(0,1)$ 就是横竖两把尺子：",
                        r"$$\boldsymbol x=5e_{1}+3e_{2}=5\begin{pmatrix}1\\0\end{pmatrix}+3\begin{pmatrix}0\\1\end{pmatrix}=\begin{pmatrix}5\\3\end{pmatrix}$$",
                        r"沿 $x$ 轴数 5 格、沿 $y$ 轴数 3 格，读数就是 $(5,3)$——这是最熟悉的一套尺子。",
                    ],
                    "result": [5.0, 3.0],
                    "checks": [{"name": "result", "expected": [5.0, 3.0], "tolerance": 1e-9}],
                    "claim_refs": [claim_id],
                },
                {
                    "id": oblique_example_id,
                    "title": "第二步：换一组基，同一个点的读数变了",
                    "kind": "matrix_transform",
                    # 将坐标代回基向量重组，以有界矩阵运算验证结果。
                    "given": [[[1, 1], [1, -1]], [4, 1]],
                    "calculation": [
                        r"同一个点 $\boldsymbol x=(5,3)$ 一步都没动，只把尺子换成 $b_{1}=(1,1)$、$b_{2}=(1,-1)$：",
                        r"$$\boldsymbol x=c_{1}b_{1}+c_{2}b_{2},\qquad c_{1}\begin{pmatrix}1\\1\end{pmatrix}+c_{2}\begin{pmatrix}1\\-1\end{pmatrix}=\begin{pmatrix}5\\3\end{pmatrix}$$",
                        r"把待求的读数写在右边，方程组写成矩阵形式：",
                        r"$$" + basis_matrix + r"\begin{pmatrix}c_{1}\\c_{2}\end{pmatrix}=\begin{pmatrix}5\\3\end{pmatrix}$$",
                        r"两边左乘逆矩阵，读数一次求出：",
                        r"$$\begin{pmatrix}c_{1}\\c_{2}\end{pmatrix}="
                        + basis_matrix
                        + r"^{-1}\begin{pmatrix}5\\3\end{pmatrix}=\frac{1}{-2}\begin{pmatrix}-1&-1\\-1&1\end{pmatrix}\begin{pmatrix}5\\3\end{pmatrix}=\begin{pmatrix}4\\1\end{pmatrix}$$",
                        r"验算：$4b_{1}+1b_{2}=4(1,1)+1(1,-1)=(5,3)$，回到原处。",
                        r"所以 $\boldsymbol x$ 在基 $B$ 下的坐标是 $(4,1)$：向右上数 4 格、向右下数 1 格。",
                        r"点没变，变的是尺子——坐标从来不是向量本身，而是它相对某一组基的读数。",
                    ],
                    # 展示坐标读数，校验项另行验证能否重组原向量。
                    "result": [4.0, 1.0],
                    "checks": [{"name": "reconstruction", "expected": [5.0, 3.0], "tolerance": 1e-9}],
                    "claim_refs": [claim_id],
                },
            ],
            "geometric_meaning": "",
            "pitfalls": [],
            "connections": [],
            "intuition": "",
            "analogy_boundary": "",
            "transfer_note": "",
            "conclusion": "",
            "read_guide": [],
            "invariants": list(_BASIS_INVARIANTS),
            "symbol_roles": {
                "x": "same_vector",
                "e_1": "standard_basis",
                "e_2": "standard_basis",
                "b_1": "oblique_basis",
                "b_2": "oblique_basis",
            },
            "sections": [
                {"id": "definition", "title": "定义", "text": "", "claim_refs": [claim_id]},
                {"id": "derivation", "title": "性质 4 的证明", "text": "", "claim_refs": [claim_id]},
                {"id": "worked_examples", "title": "数学案例", "text": "", "claim_refs": [claim_id]},
            ],
            "case_layout": {
                # 两种基下的读数并排显示并共用取景。
                "default_pane_count": 2,
                "cases": [
                    {
                        "id": "case.ch04.basis.definition.1",
                        "topic_id": "ch04.basis.definition",
                        "example_ref": standard_example_id,
                        "claim_refs": [claim_id],
                        "stage_refs": ["stage.ch04.basis.definition.standard"],
                        "purpose": "① 标准基下的读数：横竖各数格数，读出 (5,3)",
                    },
                    {
                        "id": "case.ch04.basis.definition.2",
                        "topic_id": "ch04.basis.definition",
                        "example_ref": oblique_example_id,
                        "claim_refs": [claim_id],
                        "stage_refs": ["stage.ch04.basis.definition.oblique"],
                        "purpose": "② 新基下的读数：同一个点，读数变成 (4,1)",
                    },
                ],
            },
        }
    )
    for claim in result.get("claims", []):
        if isinstance(claim, dict):
            claim["explanation_refs"] = ["definition", "derivation", "worked_examples"]
            claim["formula"] = r"\boldsymbol x=4\boldsymbol b_{1}+1\boldsymbol b_{2}=" + basis_matrix + r"\begin{pmatrix}4\\1\end{pmatrix}=(5,3)"
            claim["formula_symbols"] = ["x", "e_1", "e_2", "b_1", "b_2"]


_LINEAR_MAP_DEFINITION = "\n\n".join(
    (
        "\n".join(
            (
                r"定义 4.11（线性变换） 映射 T: $R^{n} \rightarrow R^{m}$ 是线性变换 $\Leftrightarrow$",
                r"加性：$T(u+v) = T(u)+T(v)$    齐性：$T(kv) = k \cdot T(v)$",
                r"等价条件——T 保持线性组合：$T(\alpha_{1}v_{1}+...+\alpha_{k}v_{k}) = \alpha_{1}T(v_{1})+...+\alpha_{k}T(v_{k})$。",
            )
        ),
        "\n".join(
            (
                r"| 是 | 公式 | 不是 | 公式 |",
                r"| --- | --- | --- | --- |",
                r"| 旋转 | $T(x,y)=(xcos\theta-ysin\theta, xsin\theta+ycos\theta)$ | 平移 | $T(x,y)=(x+1, y)$ |",
                r"| 拉伸 | $T(x,y)=(ax, by)$ | 平方 | $T(x)=x^{2}$ |",
                r"| 投影 | $T(v)=\operatorname{Proj}(v)$ | 加常数 | $T(v)=v+b (b\neq0)$ |",
            )
        ),
        r"判断平移：$T(v_{1}+v_{2})=(v_{11}+v_{21}+1, v_{12}+v_{22})$，但 $T(v_{1})+T(v_{2})=(v_{11}+1+v_{21}+1, ... ) \rightarrow$ 加性不成立。",
    )
)


def _refine_linear_map_definition(
    result: dict[str, Any], explanation: dict[str, Any], visual: dict[str, Any]
) -> None:
    """Publish 4.4.1–4.4.2 verbatim with the two confirmed numeric cases."""

    claim_id = "claim.ch04.linear-map.definition"
    stretch_example_id = "example.ch04.linear-map.definition.stretch"
    translation_example_id = "example.ch04.linear-map.definition.translation"
    result["connections"] = []
    explanation.update(
        {
            "summary": "",
            "definition": _LINEAR_MAP_DEFINITION,
            "formula": "",
            "derivation": [],
            "geometric_meaning": "",
            "worked_examples": [
                {
                    "id": stretch_example_id,
                    "title": "拉伸（是）",
                    "kind": "matrix_transform",
                    "given": [[[2, 0], [0, 1]], [1, 1]],
                    "calculation": [
                        r"$$\boldsymbol u=(1,0),\qquad \boldsymbol v=(0,1),\qquad k=2$$",
                        r"$$T(x,y)=(2x,y)$$",
                        r"$$T(\boldsymbol u+\boldsymbol v)=T(\boldsymbol u)+T(\boldsymbol v)=(2,1)$$",
                        r"$$T(2\boldsymbol u)=2T(\boldsymbol u)=(4,0)$$",
                    ],
                    "result": [2.0, 1.0],
                    "checks": [{"name": "result", "expected": [2.0, 1.0], "tolerance": 1e-9}],
                    "claim_refs": [claim_id],
                },
                {
                    "id": translation_example_id,
                    "title": "平移（不是）",
                    "kind": "vector_addition",
                    "given": [[2, 0], [1, 1]],
                    "calculation": [
                        r"$$\boldsymbol u=(1,0),\qquad \boldsymbol v=(0,1)$$",
                        r"$$T(x,y)=(x+1,y)$$",
                        r"$$T(\boldsymbol u+\boldsymbol v)=(2,1)$$",
                        r"$$T(\boldsymbol u)+T(\boldsymbol v)=(3,1)$$",
                    ],
                    "result": [3.0, 1.0],
                    "checks": [{"name": "result", "expected": [3.0, 1.0], "tolerance": 1e-9}],
                    "claim_refs": [claim_id],
                },
            ],
            "pitfalls": [],
            "connections": [],
            "intuition": "",
            "conclusion": "",
            "analogy_boundary": "",
            "transfer_note": "",
            "read_guide": [],
            "invariants": [],
            "symbol_roles": {
                "T": "stretch_map",
                "u": "stretch_result",
                "v": "translation_result",
            },
            "sections": [
                {"id": "definition", "title": "定义", "text": "", "claim_refs": [claim_id]},
                {"id": "worked_examples", "title": "数学案例", "text": "", "claim_refs": [claim_id]},
            ],
            "case_layout": {
                "default_pane_count": 2,
                "cases": [
                    {
                        "id": "case.ch04.linear-map.definition.stretch",
                        "topic_id": "ch04.linear-map.definition",
                        "example_ref": stretch_example_id,
                        "claim_refs": [claim_id],
                        "stage_refs": ["stage.ch04.linear-map.definition.stretch"],
                        "purpose": "拉伸（是）",
                    },
                    {
                        "id": "case.ch04.linear-map.definition.translation",
                        "topic_id": "ch04.linear-map.definition",
                        "example_ref": translation_example_id,
                        "claim_refs": [claim_id],
                        "stage_refs": ["stage.ch04.linear-map.definition.translation"],
                        "purpose": "平移（不是）",
                    },
                ],
            },
        }
    )
    for claim in result.get("claims", []):
        if isinstance(claim, dict):
            claim["statement"] = "映射 T 是线性变换，当且仅当它满足加性与齐性。"
            claim["explanation_refs"] = ["definition", "worked_examples"]
            claim["formula"] = r"T(u+v)=T(u)+T(v),\quad T(kv)=k\cdot T(v)"
            claim["formula_symbols"] = ["T", "u", "v"]

# 3.1.1 至 3.1.3 仅规范数学定界符，公式并入"定义"。
_DET_GEOMETRY_DEFINITION = "\n\n".join(
    (
        r"定义 3.1（行列式——几何定义） 设 $\boldsymbol A$ 是 $2 \times 2$ 矩阵。$\boldsymbol A$ 的行列式，记为 $\det(\boldsymbol A)$ 或 $|\boldsymbol A|$，等于以 $\boldsymbol A$ 的两列为邻边的平行四边形的有向面积。",
        "\n".join(
            (
                r"- 若 $\det(\boldsymbol A) > 0$，两列的顺序与 $e_{1} \rightarrow e_{2}$ 的旋转方向一致（逆时针）",
                r"- 若 $\det(\boldsymbol A) < 0$，方向相反（顺时针）",
                r"- 若 $\det(\boldsymbol A) = 0$，两列共线，平行四边形退化为线段$\rightarrow$面积为零",
            )
        ),
        r"定理 3.1（$2 \times 2$ 行列式公式）",
        r"$$\det(\begin{pmatrix} a & b \\ c & d \end{pmatrix}) = ad - bc$$",
        '推导直觉：$a$ 和 $d$ 构成"主轴方向的矩形面积"，$bc$ 是"交叉项"的修正。',
        r"$3 \times 3$ 行列式用三阶展开公式，几何上对应平行六面体的有向体积。",
    )
)

# 3.1.3 速查表规范为两列四行。
_DET_GEOMETRY_MEANING = "\n".join(
    (
        r"| $\det(\boldsymbol A)$ | 几何含义 |",
        r"| --- | --- |",
        r"| $= 0$ | 面积降为零$\rightarrow$信息丢失（至少一个维度被压扁） |",
        r"| $> 0$ | 面积放大且方向不变 |",
        '| $< 0$ | 面积放大但方向反转（"翻面"） |',
        r"| $|\det(\boldsymbol A)| = 1$ | 面积不变（如纯旋转） |",
    )
)

# 3.1 的两步案例用单位正方形和外接矩形展示行列式面积。
_DET_GEOMETRY_CASE_STEPS = (
    (
        "第一步：单位正方形",
        (
            r"标准基向量 $\boldsymbol e_{1}=(1,0)$、$\boldsymbol e_{2}=(0,1)$ 张成面积为 $1$ 的单位正方形。",
            r"$$|\det(\boldsymbol e_{1},\boldsymbol e_{2})|=1$$",
        ),
    ),
    (
        "第二步：矩阵变换得到的平行四边形",
        (
            r"取矩阵 $$\boldsymbol A=\begin{pmatrix} 2 & 1 \\ 1 & 3 \end{pmatrix},$$ 即定理 3.1 中的 $a=2$、$b=1$、$c=1$、$d=3$。",
            r"矩阵变换 $\boldsymbol A$ 把两条标准基向量分别送到它的两列：$$\boldsymbol A\boldsymbol e_{1}=(2,1)=\boldsymbol v_{1},\qquad \boldsymbol A\boldsymbol e_{2}=(1,3)=\boldsymbol v_{2}$$",
            r"于是第一格的单位正方形被这个矩阵变换成以 $\boldsymbol v_{1}$、$\boldsymbol v_{2}$ 为邻边的平行四边形：$\boldsymbol e_{1}$、$\boldsymbol e_{2}$ 的像就是它的两条邻边。",
            r"把两列放进外接矩形：宽 $a+b=3$、高 $c+d=4$，面积 $3\times4=12$。",
            r"从外接矩形右下角连到 $\boldsymbol v_{1}$、左上角连到 $\boldsymbol v_{2}$（图中灰色虚线），切掉四个直角三角形：两个底 $a+b=3$、高 $c=1$，面积各 $1.5$；两个底 $c+d=4$、高 $b=1$，面积各 $2$。",
            r"$$S=12-1.5-1.5-2-2=5$$",
            r"$$S=(a+b)(c+d)-c(a+b)-b(c+d)=ad-bc=2\times3-1\times1=5$$",
        ),
    ),
)


def _refine_det_geometry(explanation: dict[str, Any], visual: dict[str, Any]) -> None:
    """3.1 的单一小节：定义（含公式）、几何意义速查表与两步数学案例。"""

    claim_id = "claim.ch03.det.oriented-area"
    explanation.update({
        "summary": r"行列式等于以矩阵两列为邻边的平行四边形的有向面积，按 $ad-bc$ 计算。",
        "definition": _DET_GEOMETRY_DEFINITION,
        "formula": "",
        "derivation": [],
        "geometric_meaning": _DET_GEOMETRY_MEANING,
        "symbol_roles": {"a": "vector_a", "b": "vector_b", "area": "area"},
    })
    for key in (
        "intuition", "connections", "transfer_note", "conclusion", "read_guide",
        "analogy_boundary", "invariants", "pitfalls",
    ):
        explanation.pop(key, None)
    # 分节标题沿用讲义，案例由本节补充。
    explanation["sections"] = [
        {"id": "definition", "title": "定义", "text": "", "claim_refs": [claim_id]},
        {"id": "geometric_meaning", "title": "几何意义速查", "text": "", "claim_refs": [claim_id]},
        {"id": "worked_examples", "title": "数学案例", "text": "", "claim_refs": [claim_id]},
    ]
    step_ids = (
        "example.ch03.det.oriented-area.1",
        "example.ch03.det.oriented-area.2",
    )
    givens = ([[1, 0], [0, 1]], [[2, 1], [1, 3]])
    results = (1.0, 5.0)
    explanation["worked_examples"] = [
        {
            "id": step_id,
            "title": step[0],
            "kind": "oriented_area",
            "given": given,
            "calculation": list(step[1]),
            "result": result,
            "checks": [{"name": "area", "expected": result, "tolerance": 1e-9}],
            "claim_refs": [claim_id],
        }
        for step_id, step, given, result in zip(
            step_ids, _DET_GEOMETRY_CASE_STEPS, givens, results
        )
    ]
    stage_ids = (
        "stage.case.ch03.det.oriented-area.1",
        "stage.case.ch03.det.oriented-area.2",
    )
    relation_ids = (
        "rel.case.ch03.det.oriented-area.1",
        "rel.case.ch03.det.oriented-area.2",
    )
    # 外接矩形由编译器按两列计算，此处只声明分解关系。
    box_relation_id = "rel.box.ch03.det.oriented-area"
    visual.update({
        "scene_kind": "2d",
        "entities": [
            {"id": "e1", "kind": "vector", "dimension": 2, "value": [1, 0], "role": "vector_a", "label": "e1", "claim_refs": [claim_id]},
            {"id": "e2", "kind": "vector", "dimension": 2, "value": [0, 1], "role": "vector_b", "label": "e2", "claim_refs": [claim_id]},
            {"id": "unit_square", "kind": "area", "dimension": 2, "value": [[1, 0], [0, 1]], "role": "neutral", "label": "unit square", "claim_refs": [claim_id]},
            {"id": "v1", "kind": "vector", "dimension": 2, "value": [2, 1], "role": "vector_a", "label": "v1", "claim_refs": [claim_id]},
            {"id": "v2", "kind": "vector", "dimension": 2, "value": [1, 3], "role": "vector_b", "label": "v2", "claim_refs": [claim_id]},
            {"id": "area", "kind": "area", "dimension": 2, "value": [[2, 1], [1, 3]], "role": "area", "label": "ad-bc=5", "claim_refs": [claim_id]},
        ],
        "relations": [
            {"id": relation_ids[0], "kind": "same_measure", "source_ref": "e1", "target_ref": "unit_square", "parameters": {}, "claim_refs": [claim_id]},
            {"id": relation_ids[1], "kind": "same_measure", "source_ref": "v1", "target_ref": "area", "parameters": {}, "claim_refs": [claim_id]},
            {"id": box_relation_id, "kind": "decomposes_into", "source_ref": "v1", "target_ref": "v2", "parameters": {}, "style": "dashed", "claim_refs": [claim_id]},
        ],
        "stages": [
            {
                "id": stage_ids[0],
                "title": _DET_GEOMETRY_CASE_STEPS[0][0],
                "caption": r"$\boldsymbol e_{1}=(1,0)$、$\boldsymbol e_{2}=(0,1)$ 张成面积为 $1$ 的单位正方形。",
                "layout": "overlay",
                "input_entity_refs": ["e1", "e2"],
                "output_entity_refs": ["unit_square"],
                "relation_refs": [relation_ids[0]],
                "expected_invariants": ["unit area"],
            },
            {
                "id": stage_ids[1],
                "title": _DET_GEOMETRY_CASE_STEPS[1][0],
                "caption": r"矩阵变换 $\boldsymbol A=\begin{pmatrix}2&1\\1&3\end{pmatrix}$ 把 $\boldsymbol e_{1},\boldsymbol e_{2}$ 送到 $\boldsymbol v_{1}=(2,1)$、$\boldsymbol v_{2}=(1,3)$；外接矩形减去四个直角三角形，面积正好是 $ad-bc$。",
                "layout": "overlay",
                "input_entity_refs": ["v1", "v2"],
                "output_entity_refs": ["area"],
                "relation_refs": [relation_ids[1], box_relation_id],
                "expected_invariants": ["signed area"],
            },
        ],
    })
    explanation["case_layout"] = {
        "default_pane_count": 2,
        "cases": [
            {
                "id": "case.ch03.det.oriented-area.1",
                "topic_id": "ch03.det.oriented-area",
                "example_ref": step_ids[0],
                "claim_refs": [claim_id],
                "stage_refs": [stage_ids[0]],
                "purpose": _DET_GEOMETRY_CASE_STEPS[0][0],
            },
            {
                "id": "case.ch03.det.oriented-area.2",
                "topic_id": "ch03.det.oriented-area",
                "example_ref": step_ids[1],
                "claim_refs": [claim_id],
                "stage_refs": [stage_ids[1]],
                "purpose": _DET_GEOMETRY_CASE_STEPS[1][0],
            },
        ],
    }


def _refine_vector_addition(explanation: dict[str, Any], visual: dict[str, Any], example: dict[str, Any]) -> None:
    explanation.update({
        "title": "向量加法",
        "summary": "向量加法按对应分量相加；几何上以两个向量为邻边作平行四边形，从原点出发的对角线就是和向量。",
        "definition": (
            "设\n\n"
            r"$$\boldsymbol a=(x_1,y_1),\qquad \boldsymbol b=(x_2,y_2).$$"
            "\n\n向量加法定义为\n\n"
            r"$$\boldsymbol a+\boldsymbol b=(x_1+x_2,\,y_1+y_2).$$"
            "\n\n即两个向量的对应分量分别相加。"
        ),
        # 声明保留机器可读公式，展示位置由定义块负责。
        "formula": r"\boldsymbol a+\boldsymbol b=(x_1+x_2,\,y_1+y_2)",
        "derivation": [],
        "invariants": [
            (
                r"对任意向量 $\boldsymbol a,\boldsymbol b,\boldsymbol c$，有："
                "\n\n交换律：\n\n"
                r"$$\boldsymbol a+\boldsymbol b=\boldsymbol b+\boldsymbol a$$"
                "\n\n结合律：\n\n"
                r"$$(\boldsymbol a+\boldsymbol b)+\boldsymbol c=\boldsymbol a+(\boldsymbol b+\boldsymbol c)$$"
                "\n\n零向量为加法单位元：\n\n"
                r"$$\boldsymbol a+\boldsymbol 0=\boldsymbol a$$"
                "\n\n负向量满足：\n\n"
                r"$$\boldsymbol a+(-\boldsymbol a)=\boldsymbol 0$$"
            )
        ],
        # 几何解释仅保留讲义中的平行四边形法则。
        "geometric_meaning": (
            r"以向量 $\boldsymbol a$ 和 $\boldsymbol b$ 为邻边作平行四边形，"
            r"从原点出发的对角线就是 $\boldsymbol a+\boldsymbol b$。"
            r"本质上，$\boldsymbol a+\boldsymbol b$ 就是先把 $\boldsymbol a$ 走一遍，"
            r"再从 $\boldsymbol a$ 的终点把 $\boldsymbol b$ 接上去。"
        ),
        "worked_examples": [],
        "symbol_roles": {"a": "vector_a", "b": "vector_b", "sum": "transformed_a"},
    })
    for key in (
        "intuition", "connections", "transfer_note", "conclusion", "read_guide", "pitfalls",
        "analogy_boundary",
    ):
        explanation.pop(key, None)

    # 加法案例分为输入向量和合成结果两步。
    del example
    explanation["worked_examples"] = [
        {
            "id": "example.addition.objects",
            "title": "第一步：向量 a 与 b",
            "kind": "vector_addition",
            "given": [[3, 1], [1, 2]],
            "calculation": [
                r"$$\boldsymbol a=(3,1),\quad \boldsymbol b=(1,2)$$",
            ],
            "result": [4, 3],
            "checks": [{"name": "sum", "expected": [4, 3], "tolerance": 1e-9}],
            "claim_refs": ["claim.ch01.ops.addition"],
        },
        {
            "id": "example.addition.parallelogram",
            "title": "第二步：a+b 与平行四边形",
            "kind": "vector_addition",
            "given": [[3, 1], [1, 2]],
            "calculation": [
                r"$$\boldsymbol a+\boldsymbol b=(3+1,\,1+2)=(4,3)$$",
            ],
            "result": [4, 3],
            "checks": [{"name": "sum", "expected": [4, 3], "tolerance": 1e-9}],
            "claim_refs": ["claim.ch01.ops.addition"],
        },
    ]
    claim_ref = ["claim.ch01.ops.addition"]
    visual["entities"] = [
        {"id": "flow_a", "kind": "vector", "dimension": 2, "value": [3, 1], "role": "vector_a", "label": "a", "claim_refs": claim_ref},
        {"id": "flow_b", "kind": "vector", "dimension": 2, "value": [1, 2], "role": "vector_b", "label": "b", "claim_refs": claim_ref},
        {"id": "flow_sum", "kind": "vector", "dimension": 2, "value": [4, 3], "role": "transformed_a", "label": "a+b", "claim_refs": claim_ref},
    ]
    visual["relations"] = [
        {"id": "rel.addition.flow", "kind": "sum", "source_ref": "flow_a", "target_ref": "flow_b", "parameters": {}, "claim_refs": claim_ref},
    ]
    explanation["sections"] = [
        {"id": section_id, "title": section_id, "text": "", "claim_refs": claim_ref}
        for section_id in ("definition", "formula", "invariants", "worked_examples", "geometric_meaning")
    ]
    visual["stages"] = [
        {
            "id": "stage.flow.objects",
            "title": "第一步：向量 a 与 b",
            "caption": r"$\boldsymbol a=(3,1)$、$\boldsymbol b=(1,2)$ 从原点出发。",
            "layout": "overlay",
            "input_entity_refs": ["flow_a", "flow_b"],
            "output_entity_refs": [],
            "relation_refs": [],
            "expected_invariants": ["两个向量共用同一个原点"],
        },
        {
            "id": "stage.flow.parallelogram",
            "title": "第二步：a+b 与平行四边形",
            "caption": r"以 $\boldsymbol a$、$\boldsymbol b$ 为邻边作平行四边形，对角线为 $\boldsymbol a+\boldsymbol b=(4,3)$。",
            "layout": "overlay",
            "input_entity_refs": ["flow_a", "flow_b"],
            "output_entity_refs": ["flow_sum"],
            "relation_refs": ["rel.addition.flow"],
            "expected_invariants": ["平行四边形对角线为 (4,3)"],
        },
    ]
    explanation["case_layout"] = {
        # 两步默认并排并共用视角。
        "default_pane_count": 2,
        "cases": [
            {
                "id": "case.addition.objects",
                "topic_id": "ch01.ops.addition",
                "example_ref": "example.addition.objects",
                "claim_refs": ["claim.ch01.ops.addition"],
                "stage_refs": ["stage.flow.objects"],
                "purpose": "第一步：向量 a、b",
            },
            {
                "id": "case.addition.parallelogram",
                "topic_id": "ch01.ops.addition",
                "example_ref": "example.addition.parallelogram",
                "claim_refs": ["claim.ch01.ops.addition"],
                "stage_refs": ["stage.flow.parallelogram"],
                "purpose": "第二步：a+b 与平行四边形",
            },
        ],
    }


def _refine_vector_magnitude(
    explanation: dict[str, Any], visual: dict[str, Any], example: dict[str, Any] | None
) -> None:
    """Shape the first lecture subsection without borrowing later subsections."""

    claim_refs = ["claim.ch01.vector.magnitude"]
    explanation.update(
        {
            "title": "向量的几何量：方向、长度与零向量",
            "summary": r"向量由从原点出发的有向线段表示；非零向量具有方向和长度。",
            "definition": (
                r"在平面直角坐标系中，向量是起点为原点 $O(0,0)$ 的有向线段，"
                r"其终点坐标记为 $\boldsymbol v=(x,y)$。"
                "\n\n"
                r"长度为零的向量称为零向量："
                "\n\n"
                r"$$\boldsymbol 0=(0,0).$$"
            ),
            "formula": r"\lvert\boldsymbol v\rvert=\sqrt{x^2+y^2}",
            "geometric_meaning": (
                r"向量箭头的方向由从原点指向终点的射线确定，箭头长度就是模 $\lvert\boldsymbol v\rvert$。"
                "\n\n"
                r"零向量 $\boldsymbol 0$ 的起点和终点重合，因此长度为 $0$，没有方向。"
            ),
            "worked_examples": [],
            "symbol_roles": {"v": "vector_a", "zero": "result"},
        }
    )
    for key in (
        "intuition", "connections", "transfer_note", "conclusion", "read_guide",
        "analogy_boundary", "derivation", "invariants", "pitfalls",
    ):
        explanation.pop(key, None)

    first = {
        "id": "example.magnitude.nonzero",
        "title": "案例一：非零向量的长度",
        "kind": "inner_product",
        "given": [[3, 4], [3, 4]],
        "calculation": [
            r"$$\boldsymbol v=(3,4)$$",
            r"$$\lvert\boldsymbol v\rvert=\sqrt{3^2+4^2}=5$$",
        ],
        "result": 25,
        "checks": [{"name": "result", "expected": 25, "tolerance": 1e-9}],
        "claim_refs": claim_refs,
    }
    second = {
        "id": "example.magnitude.zero",
        "title": "案例二：零向量",
        "kind": "inner_product",
        "given": [[0, 0], [0, 0]],
        "calculation": [
            r"$$\boldsymbol 0=(0,0)$$",
            r"$$\lvert\boldsymbol 0\rvert=\sqrt{0^2+0^2}=0$$",
        ],
        "result": 0,
        "checks": [{"name": "result", "expected": 0, "tolerance": 1e-9}],
        "claim_refs": claim_refs,
    }
    explanation["worked_examples"] = [first, second]
    visual["scene_kind"] = "2d"
    visual["entities"] = [
        {"id": "nonzero_v", "kind": "vector", "dimension": 2, "value": [3, 4], "role": "vector_a", "label": "v", "claim_refs": claim_refs},
        {"id": "nonzero_length", "kind": "point", "dimension": 2, "value": [3, 4], "role": "result", "label": "", "claim_refs": claim_refs},
        {"id": "zero_v", "kind": "vector", "dimension": 2, "value": [0, 0], "role": "vector_a", "label": "0", "claim_refs": claim_refs},
    ]
    visual["relations"] = [
        {"id": "rel.magnitude.nonzero", "kind": "invariant", "source_ref": "nonzero_v", "target_ref": "nonzero_length", "parameters": {}, "claim_refs": claim_refs},
        {"id": "rel.magnitude.zero", "kind": "invariant", "source_ref": "zero_v", "target_ref": "zero_v", "parameters": {}, "claim_refs": claim_refs},
    ]
    visual["stages"] = [
        {
            "id": "stage.magnitude.nonzero",
            "title": "案例一：非零向量的长度",
            "caption": r"$\boldsymbol v=(3,4)$ 的箭头长度为 $5$。",
            "layout": "overlay",
            "input_entity_refs": ["nonzero_v"],
            "output_entity_refs": ["nonzero_length"],
            "relation_refs": ["rel.magnitude.nonzero"],
            "expected_invariants": ["nonzero vector length is 5"],
        },
        {
            "id": "stage.magnitude.zero",
            "title": "案例二：零向量",
            "caption": r"$\boldsymbol 0=(0,0)$ 的起点和终点重合，长度为 $0$。",
            "layout": "overlay",
            "input_entity_refs": ["zero_v"],
            "output_entity_refs": [],
            "relation_refs": ["rel.magnitude.zero"],
            "expected_invariants": ["zero vector length is 0"],
        },
    ]
    explanation["sections"] = [
        {"id": section_id, "title": section_id, "text": "", "claim_refs": claim_refs}
        for section_id in ("definition", "formula", "worked_examples", "geometric_meaning")
    ]
    explanation["case_layout"] = {
        "default_pane_count": 1,
        "cases": [
            {
                "id": "case.magnitude.nonzero",
                "topic_id": "ch01.vector.magnitude",
                "example_ref": "example.magnitude.nonzero",
                "claim_refs": claim_refs,
                "stage_refs": ["stage.magnitude.nonzero"],
                "purpose": "案例一：非零向量的长度",
            },
            {
                "id": "case.magnitude.zero",
                "topic_id": "ch01.vector.magnitude",
                "example_ref": "example.magnitude.zero",
                "claim_refs": claim_refs,
                "stage_refs": ["stage.magnitude.zero"],
                "purpose": "案例二：零向量",
            },
        ],
    }


def _refine_vector_subtraction(explanation: dict[str, Any], visual: dict[str, Any]) -> None:
    """Present subsection 1.2.2 as the lecture's definition and endpoint reading.

    讲义 1.2.2 只有定义与几何解释，没有数值例。这里按讲义原文给出两者，并把
    “从 b 的终点指向 a 的终点”做成两步数学案例流程：第一步给出 a、b，第二步
    给出 a-b。复算采用 a=(3,1)、b=(1,2)。
    """

    claim_refs = ["claim.ch01.ops.subtraction"]
    explanation.update({
        "title": "向量减法",
        "summary": "向量减法定义为加上减向量的相反向量，坐标按对应分量相减。",
        "definition": (
            r"设二维向量 $\boldsymbol a=(x_1,y_1)$、$\boldsymbol b=(x_2,y_2)$。"
            "\n\n"
            r"$\boldsymbol a-\boldsymbol b$ 定义为 $\boldsymbol a$ 与 $\boldsymbol b$ 的负向量之和："
            "\n\n"
            r"$$\boldsymbol a-\boldsymbol b=\boldsymbol a+(-\boldsymbol b)=(x_1-x_2,\,y_1-y_2).$$"
        ),
        "formula": r"\boldsymbol a-\boldsymbol b=(x_1-x_2,\,y_1-y_2)",
        "derivation": [],
        # 讲义 1.2.2 的几何解释原文，位置紧随定义。
        "geometric_meaning": (
            r"从 $\boldsymbol b$ 的终点指向 $\boldsymbol a$ 的终点的箭头，恰好等于 $\boldsymbol a-\boldsymbol b$。"
            r"这是因为 $\boldsymbol b+(\boldsymbol a-\boldsymbol b)=\boldsymbol a$，"
            r"即从原点出发走到 $\boldsymbol b$，再走 $\boldsymbol a-\boldsymbol b$，到达 $\boldsymbol a$。"
        ),
        "worked_examples": [],
        "symbol_roles": {"a": "vector_a", "b": "vector_b"},
    })
    for key in (
        "intuition", "connections", "transfer_note", "conclusion", "read_guide",
        "analogy_boundary", "invariants", "pitfalls",
    ):
        explanation.pop(key, None)

    explanation["worked_examples"] = [
        {
            "id": "example.subtraction.operands",
            "title": "第一步：向量 a 与 b",
            "kind": "vector_addition",
            # a - b 就是 a + (-b)；复算按定义把 a 与 -b 相加。
            "given": [[3, 1], [-1, -2]],
            "calculation": [
                r"$$\boldsymbol a=(3,1),\qquad \boldsymbol b=(1,2),\qquad -\boldsymbol b=(-1,-2)$$",
            ],
            "result": [2.0, -1.0],
            "checks": [{"name": "sum", "expected": [2.0, -1.0], "tolerance": 1e-9}],
            "claim_refs": claim_refs,
        },
        {
            "id": "example.subtraction.difference",
            "title": "第二步：a-b 的终点关系",
            "kind": "vector_addition",
            "given": [[3, 1], [-1, -2]],
            "calculation": [
                r"$$\boldsymbol a-\boldsymbol b=\boldsymbol a+(-\boldsymbol b)=(3,1)+(-1,-2)=(2,-1)$$",
                r"$$\boldsymbol b+(\boldsymbol a-\boldsymbol b)=(1,2)+(2,-1)=(3,1)=\boldsymbol a$$",
            ],
            "result": [2.0, -1.0],
            "checks": [{"name": "sum", "expected": [2.0, -1.0], "tolerance": 1e-9}],
            "claim_refs": claim_refs,
        },
    ]
    visual.update({
        "scene_kind": "2d",
        "entities": [
            {"id": "a", "kind": "vector", "dimension": 2, "value": [3, 1], "role": "vector_a", "label": "a", "claim_refs": claim_refs},
            {"id": "b", "kind": "vector", "dimension": 2, "value": [1, 2], "role": "vector_b", "label": "b", "claim_refs": claim_refs},
        ],
        # 关系端点刻意是 b 再到 a：编译器据此画出从 b 的终点指向 a 的终点的 a-b。
        "relations": [{
            "id": "rel.subtraction.endpoints", "kind": "difference",
            "source_ref": "b", "target_ref": "a", "parameters": {}, "claim_refs": claim_refs,
        }],
        "stages": [
            {
                "id": "stage.subtraction.operands", "title": "第一步：向量 a 与 b",
                "caption": r"$\boldsymbol a=(3,1)$、$\boldsymbol b=(1,2)$ 从原点出发。",
                "layout": "overlay", "input_entity_refs": ["a", "b"], "output_entity_refs": [],
                "relation_refs": [], "expected_invariants": ["两个向量共用同一个原点"],
            },
            {
                "id": "stage.subtraction.difference", "title": "第二步：a-b 的终点关系",
                "caption": r"从 $\boldsymbol b$ 的终点指向 $\boldsymbol a$ 的终点的箭头等于 $\boldsymbol a-\boldsymbol b$。",
                "layout": "overlay", "input_entity_refs": ["a", "b"], "output_entity_refs": [],
                "relation_refs": ["rel.subtraction.endpoints"], "expected_invariants": ["b 加 a-b 得到 a"],
            },
        ],
    })
    explanation["sections"] = [
        {"id": section_id, "title": section_id, "text": "", "claim_refs": claim_refs}
        for section_id in ("definition", "formula", "worked_examples", "geometric_meaning")
    ]
    explanation["case_layout"] = {
        "default_pane_count": 2,
        "cases": [
            {
                "id": "case.subtraction.operands", "topic_id": "ch01.ops.subtraction",
                "example_ref": "example.subtraction.operands", "claim_refs": claim_refs,
                "stage_refs": ["stage.subtraction.operands"], "purpose": "第一步：向量 a、b",
            },
            {
                "id": "case.subtraction.difference", "topic_id": "ch01.ops.subtraction",
                "example_ref": "example.subtraction.difference", "claim_refs": claim_refs,
                "stage_refs": ["stage.subtraction.difference"], "purpose": "第二步：a-b 的终点关系",
            },
        ],
    }


def _refine_vector_scalar(explanation: dict[str, Any], visual: dict[str, Any]) -> None:
    """Present subsection 1.2.3 as the lecture's definition, scaling and collinearity.

    讲义 1.2.3 依次给出定义 1.7、几何解释（含 k 取值的效果表）与定义 1.8（共线）；
    数值例按用户确认改用 a=(2,1)、2a=(4,2)。这里按
    讲义顺序保留定义、定义正下方的几何解释与共线定义，并把它做成两步数学案例流程。
    """

    claim_refs = ["claim.ch01.ops.scalar"]
    explanation.update({
        "title": "向量数乘",
        "summary": "数乘按对应分量缩放向量：长度变为 |k| 倍，k<0 时反向，结果与原向量共线。",
        # 讲义 1.2.3 的定义自带公式，所以定义块只写定义本身。
        "definition": (
            r"设 $k$ 是一个实数（标量），$\boldsymbol a=(x,y)$ 是一个向量，"
            r"则 $k$ 与 $\boldsymbol a$ 的数乘为"
            "\n\n"
            r"$$k\cdot\boldsymbol a=(kx,ky).$$"
        ),
        "formula": r"k\boldsymbol a=(kx,ky)",
        "derivation": [],
        # 讲义 1.2.3 的几何解释与 k 取值表紧随定义，定义 1.8（共线）在两者之后。
        "geometric_meaning": (
            r"数乘就是缩放——把箭头的长度变为原来的 $\lvert k\rvert$ 倍；"
            r"若 $k<0$，则同时反转方向。"
            "\n\n"
            "| $k$ 的值 | 几何效果 |\n"
            "| --- | --- |\n"
            "| $k>1$ | 拉伸（伸长） |\n"
            "| $0<k<1$ | 压缩（缩短） |\n"
            "| $k=-1$ | 反向，长度不变 |\n"
            "| $k<0$ | 反向且缩放 |"
            "\n\n"
            r"定义 1.8（共线）：如果存在实数 $k$ 使得 $\boldsymbol b=k\boldsymbol a$，"
            r"则称 $\boldsymbol a$ 与 $\boldsymbol b$ 共线（方向相同或相反）。"
            r"此时 $\boldsymbol b$ 的箭头落在 $\boldsymbol a$ 所在的直线上。"
        ),
        "worked_examples": [],
        "symbol_roles": {"k": "scalar", "a": "vector_a", "ka": "result"},
    })
    for key in (
        "intuition", "connections", "transfer_note", "conclusion", "read_guide",
        "analogy_boundary", "invariants", "pitfalls",
    ):
        explanation.pop(key, None)

    explanation["worked_examples"] = [
        {
            "id": "example.scalar.vector",
            "title": "第一步：向量 a",
            "kind": "scalar_multiple",
            "given": [1, [2, 1]],
            "calculation": [r"$$\boldsymbol a=(2,1)$$"],
            "result": [2.0, 1.0],
            "checks": [{"name": "scalar_multiple", "expected": [2.0, 1.0], "tolerance": 1e-9}],
            "claim_refs": claim_refs,
        },
        {
            "id": "example.scalar.stretch",
            "title": "第二步：2a",
            "kind": "scalar_multiple",
            "given": [2, [2, 1]],
            "calculation": [r"$$2\boldsymbol a=2\cdot(2,1)=(4,2)$$"],
            "result": [4.0, 2.0],
            "checks": [{"name": "scalar_multiple", "expected": [4.0, 2.0], "tolerance": 1e-9}],
            "claim_refs": claim_refs,
        },
    ]
    visual.update({
        "scene_kind": "2d",
        "entities": [
            {"id": "a", "kind": "vector", "dimension": 2, "value": [2, 1], "role": "vector_a", "label": "a", "claim_refs": claim_refs},
            # 缩放向量使用变换色，与同射线原向量区分。
            {"id": "two_a", "kind": "vector", "dimension": 2, "value": [4, 2], "role": "transformed_a", "label": "2a", "claim_refs": claim_refs},
        ],
        "relations": [{
            "id": "rel.scalar.multiple", "kind": "scalar_multiple",
            "source_ref": "a", "target_ref": "two_a", "parameters": {"scalar": 2}, "claim_refs": claim_refs,
        }],
        "stages": [
            {
                "id": "stage.scalar.vector", "title": "第一步：向量 a",
                "caption": r"$\boldsymbol a=(2,1)$ 从原点出发，终点记为 A。",
                "layout": "overlay", "input_entity_refs": ["a"], "output_entity_refs": [],
                "relation_refs": [], "expected_invariants": ["向量 a 从原点出发"],
            },
            {
                "id": "stage.scalar.multiple", "title": "第二步：2a",
                "caption": r"把 $\boldsymbol a=(2,1)$ 沿原来的方向拉伸 2 倍得到 $2\boldsymbol a=(4,2)$，终点记为 B，两者共线。",
                "layout": "overlay", "input_entity_refs": ["a", "two_a"], "output_entity_refs": ["two_a"],
                "relation_refs": ["rel.scalar.multiple"],
                "expected_invariants": ["2a 与 a 方向相同，长度为 a 的 2 倍"],
            },
        ],
    })
    explanation["sections"] = [
        {"id": section_id, "title": section_id, "text": "", "claim_refs": claim_refs}
        for section_id in ("definition", "formula", "worked_examples", "geometric_meaning")
    ]
    explanation["case_layout"] = {
        "default_pane_count": 2,
        "cases": [
            {
                "id": "case.scalar.vector", "topic_id": "ch01.ops.scalar",
                "example_ref": "example.scalar.vector", "claim_refs": claim_refs,
                "stage_refs": ["stage.scalar.vector"], "purpose": "第一步：向量 a",
            },
            {
                "id": "case.scalar.stretch", "topic_id": "ch01.ops.scalar",
                "example_ref": "example.scalar.stretch", "claim_refs": claim_refs,
                "stage_refs": ["stage.scalar.multiple"], "purpose": "第二步：2a",
            },
        ],
    }


def _set_case_explanation(explanation: dict[str, Any], *, title: str, summary: str, definition: str,
                          formula: str, geometry: str, examples: list[dict[str, Any]],
                          claim_refs: list[str], section_ids: tuple[str, ...] = ("definition", "formula", "worked_examples", "geometric_meaning")) -> None:
    explanation.update({"title": title, "summary": summary, "definition": definition, "formula": formula,
                        "derivation": [], "geometric_meaning": geometry, "worked_examples": examples})
    for key in ("intuition", "connections", "transfer_note", "conclusion", "read_guide", "analogy_boundary", "invariants", "pitfalls"):
        explanation.pop(key, None)
    explanation["sections"] = [{"id": item, "title": item, "text": "", "claim_refs": claim_refs} for item in section_ids]


def _refine_cauchy_schwarz(explanation: dict[str, Any], visual: dict[str, Any]) -> None:
    """Present subsection 1.3.3 with the complete lecture theorem and proofs.

    The lecture supplies no numerical examples. The two cases isolate the
    strict-inequality and equality conditions with the same unit direction.
    """

    claim_refs = ["claim.ch01.inner.cauchy-schwarz"]
    definition = (
        r"定理 1.5（Cauchy-Schwarz 不等式）对任意两个向量 $\boldsymbol a,\boldsymbol b$，有："
        "\n\n"
        r"$$\lvert\boldsymbol a\cdot\boldsymbol b\rvert\leq\lvert\boldsymbol a\rvert\cdot\lvert\boldsymbol b\rvert$$"
        "\n\n"
        r"等号成立当且仅当 $\boldsymbol a$ 与 $\boldsymbol b$ 共线。"
        "\n\n"
        r"这说明：内积的绝对值不会超过模长之积。这符合直觉——“投影的长度”不可能超过“原向量的长度”。有了这个不等式，计算夹角时 $\cos\theta$ 的值一定落在 $[-1,1]$ 内。"
    )
    derivation = [
        r"设 $\boldsymbol a=(a_{1},a_{2})$、$\boldsymbol b=(b_{1},b_{2})$。需要证明：$\lvert\boldsymbol a\cdot\boldsymbol b\rvert\leq\lvert\boldsymbol a\rvert\cdot\lvert\boldsymbol b\rvert$。",
        (
            r"**Cauchy-Schwarz 不等式的 n 维推广证明**"
            "\n\n"
            r"以下用「构造二次函数判别式法」给出对任意 n 维向量的统一证明。此方法不依赖于维度，是线性代数中最优雅的证明之一。"
        ),
        (
            r"证明：设 $\boldsymbol a=(a_{1},\ldots,a_{n})$、$\boldsymbol b=(b_{1},\ldots,b_{n})\in R^{n}$。对任意实数 $t$，考虑向量 $\boldsymbol a-t\boldsymbol b$ 的模长平方："
            "\n\n"
            r"$$\lvert\boldsymbol a-t\boldsymbol b\rvert^{2}\geq0$$"
            "\n\n"
            r"（模长平方必然非负）"
        ),
        (
            r"展开左边："
            "\n\n"
            r"$$\lvert\boldsymbol a-t\boldsymbol b\rvert^{2}=(\boldsymbol a-t\boldsymbol b)\cdot(\boldsymbol a-t\boldsymbol b)$$"
            "\n\n"
            r"$$=\boldsymbol a\cdot\boldsymbol a-t(\boldsymbol a\cdot\boldsymbol b)-t(\boldsymbol b\cdot\boldsymbol a)+t^{2}(\boldsymbol b\cdot\boldsymbol b)$$"
            "\n\n"
            r"$$=\lvert\boldsymbol a\rvert^{2}-2t(\boldsymbol a\cdot\boldsymbol b)+t^{2}\lvert\boldsymbol b\rvert^{2}$$"
        ),
        r"令 $f(t)=\lvert\boldsymbol b\rvert^{2}\cdot t^{2}-2(\boldsymbol a\cdot\boldsymbol b)\cdot t+\lvert\boldsymbol a\rvert^{2}$。这是关于 $t$ 的二次函数（当 $\lvert\boldsymbol b\rvert^{2}>0$ 时）。由于 $f(t)=\lvert\boldsymbol a-t\boldsymbol b\rvert^{2}\geq0$ 对任意 $t$ 成立，该二次函数的图像全部位于 $t$ 轴上方（或相切），故其判别式 $\Delta\leq0$。",
        (
            r"$$\Delta=[-2(\boldsymbol a\cdot\boldsymbol b)]^{2}-4\cdot\lvert\boldsymbol b\rvert^{2}\cdot\lvert\boldsymbol a\rvert^{2}=4(\boldsymbol a\cdot\boldsymbol b)^{2}-4\lvert\boldsymbol a\rvert^{2}\lvert\boldsymbol b\rvert^{2}\leq0$$"
            "\n\n"
            r"$$\Rightarrow(\boldsymbol a\cdot\boldsymbol b)^{2}\leq\lvert\boldsymbol a\rvert^{2}\lvert\boldsymbol b\rvert^{2}$$"
            "\n\n"
            r"$$\Rightarrow\lvert\boldsymbol a\cdot\boldsymbol b\rvert\leq\lvert\boldsymbol a\rvert\cdot\lvert\boldsymbol b\rvert.\;■$$"
        ),
        (
            r"若 $\boldsymbol b=\boldsymbol0$，则不等式两边均为 $0$，等号自然成立。"
            "\n\n"
            r"等号成立条件：$\Delta=0\Longleftrightarrow f(t)$ 有唯一零点 $t_{0}$，使得 $\lvert\boldsymbol a-t_{0}\boldsymbol b\rvert^{2}=0\Longleftrightarrow\boldsymbol a=t_{0}\boldsymbol b$。即 $\boldsymbol a$ 与 $\boldsymbol b$ 共线。"
        ),
        r"方法评价：此证明只用到了内积的基本运算律和二次函数的判别式性质，没有展开分量——因此对任何内积空间（无穷维！）也成立。这是线性代数「从计算走向结构」的经典范例。",
        (
            r"等价于证明：$(a_{1}b_{1}+a_{2}b_{2})^{2}\leq(a_{1}^{2}+a_{2}^{2})(b_{1}^{2}+b_{2}^{2})$。展开右边 $-$ 左边："
            "\n\n"
            r"$$(a_{1}^{2}b_{1}^{2}+a_{1}^{2}b_{2}^{2}+a_{2}^{2}b_{1}^{2}+a_{2}^{2}b_{2}^{2})-(a_{1}^{2}b_{1}^{2}+2a_{1}b_{1}a_{2}b_{2}+a_{2}^{2}b_{2}^{2})$$"
            "\n\n"
            r"$$=a_{1}^{2}b_{2}^{2}+a_{2}^{2}b_{1}^{2}-2a_{1}b_{1}a_{2}b_{2}=(a_{1}b_{2}-a_{2}b_{1})^{2}\geq0$$"
        ),
        (
            r"差值为完全平方 $\rightarrow$ 不等式成立。等号成立 $\Longleftrightarrow a_{1}b_{2}-a_{2}b_{1}=0\Longleftrightarrow\boldsymbol a$ 与 $\boldsymbol b$ 共线。■"
            "\n\n"
            r"（对 n 维的推广：可用同样的「平方差$=$平方和」方法或归纳法证明，此处从略。）"
        ),
    ]
    examples = [
        {
            "id": "example.cauchy-schwarz.strict",
            "title": "案例一：严格不等式",
            "kind": "inner_product",
            "given": [[1, 0], [3, 4]],
            "result": 3.0,
            "calculation": [
                r"$$\boldsymbol a=(1,0),\qquad\boldsymbol b=(3,4)$$",
                r"$$\boldsymbol p=\operatorname{Proj}_{\boldsymbol a}(\boldsymbol b)=(3,0),\qquad\boldsymbol r=\boldsymbol b-\boldsymbol p=(0,4),\qquad\boldsymbol r\perp\boldsymbol a$$",
                r"$$\lvert\boldsymbol a\cdot\boldsymbol b\rvert=3<5=\lvert\boldsymbol a\rvert\lvert\boldsymbol b\rvert$$",
                r"图中 $\boldsymbol p$ 是 $\boldsymbol b$ 在 $\boldsymbol a$ 方向上的投影，投影长度小于 $\boldsymbol b$ 的长度。",
            ],
            "checks": [{"name": "dot", "expected": 3.0, "tolerance": 1e-9}],
            "claim_refs": claim_refs,
        },
        {
            "id": "example.cauchy-schwarz.equality",
            "title": "案例二：等号成立",
            "kind": "inner_product",
            "given": [[1, 0], [5, 0]],
            "result": 5.0,
            "calculation": [
                r"$$\boldsymbol a=(1,0),\qquad\boldsymbol b=(5,0)$$",
                r"$$\lvert\boldsymbol a\cdot\boldsymbol b\rvert=\lvert1\times5+0\times0\rvert=5=1\times5=\lvert\boldsymbol a\rvert\lvert\boldsymbol b\rvert$$",
                r"$\boldsymbol a$ 与 $\boldsymbol b$ 共线，所以等号成立。",
            ],
            "checks": [{"name": "dot", "expected": 5.0, "tolerance": 1e-9}],
            "claim_refs": claim_refs,
        },
    ]
    explanation.update({
        "title": "柯西—施瓦茨不等式",
        "summary": "",
        "definition": definition,
        "formula": "",
        "derivation": derivation,
        "worked_examples": examples,
        "symbol_roles": {"a": "vector_a", "b": "vector_b", "p": "projection", "r": "residual"},
        "sections": [
            {"id": "definition", "title": "定义", "text": "", "claim_refs": claim_refs},
            {"id": "derivation", "title": "Cauchy-Schwarz 不等式的证明（2D情形）", "text": "", "claim_refs": claim_refs},
            {"id": "worked_examples", "title": "数学案例", "text": "", "claim_refs": claim_refs},
        ],
        "case_layout": {
            "default_pane_count": 1,
            "cases": [
                {"id": "case.cauchy-schwarz.strict", "topic_id": "ch01.inner.cauchy-schwarz", "example_ref": "example.cauchy-schwarz.strict", "claim_refs": claim_refs, "stage_refs": ["stage.cauchy-schwarz.strict"], "purpose": "案例一：严格不等式"},
                {"id": "case.cauchy-schwarz.equality", "topic_id": "ch01.inner.cauchy-schwarz", "example_ref": "example.cauchy-schwarz.equality", "claim_refs": claim_refs, "stage_refs": ["stage.cauchy-schwarz.equality"], "purpose": "案例二：等号成立"},
            ],
        },
    })
    for key in ("intuition", "geometric_meaning", "conclusion", "connections", "transfer_note", "read_guide", "analogy_boundary", "invariants", "pitfalls"):
        explanation.pop(key, None)

    equality_entities = [
        {"id": "equality_b", "kind": "vector", "dimension": 2, "value": [5, 0], "role": "vector_b", "label": "b", "claim_refs": claim_refs},
        {"id": "equality_a", "kind": "vector", "dimension": 2, "value": [1, 0], "role": "vector_a", "label": "a", "claim_refs": claim_refs},
    ]
    strict_entities = [
        {"id": "strict_a", "kind": "vector", "dimension": 2, "value": [1, 0], "role": "vector_a", "label": "a", "claim_refs": claim_refs},
        {"id": "strict_b", "kind": "vector", "dimension": 2, "value": [3, 4], "role": "vector_b", "label": "b", "claim_refs": claim_refs},
        {"id": "strict_p", "kind": "vector", "dimension": 2, "value": [3, 0], "role": "projection", "label": "p", "claim_refs": claim_refs},
        {"id": "strict_r", "kind": "vector", "dimension": 2, "value": [0, 4], "role": "residual", "label": "r", "claim_refs": claim_refs},
    ]
    relations = [
        {"id": "rel.cauchy-schwarz.strict.projection", "kind": "projects_to", "source_ref": "strict_b", "target_ref": "strict_a", "parameters": {}, "style": "dashed", "claim_refs": claim_refs},
    ]
    visual.update({
        "scene_kind": "2d",
        "entities": [*equality_entities, *strict_entities],
        "relations": relations,
        "stages": [
            {"id": "stage.cauchy-schwarz.strict", "title": "案例一：严格不等式", "caption": r"$\boldsymbol p=(3,0)$ 是 $\boldsymbol b$ 在 $\boldsymbol a$ 方向上的投影，$\boldsymbol r=(0,4)$ 与 $\boldsymbol a$ 正交。", "layout": "overlay", "input_entity_refs": ["strict_a", "strict_b", "strict_p", "strict_r"], "output_entity_refs": [], "relation_refs": [item["id"] for item in relations], "expected_invariants": ["projection length is strictly shorter than the original vector"]},
            {"id": "stage.cauchy-schwarz.equality", "title": "案例二：等号成立", "caption": r"$\boldsymbol a=(1,0)$ 与 $\boldsymbol b=(5,0)$ 共线，$\lvert\boldsymbol a\cdot\boldsymbol b\rvert=\lvert\boldsymbol a\rvert\lvert\boldsymbol b\rvert$。", "layout": "overlay", "input_entity_refs": ["equality_a", "equality_b"], "output_entity_refs": [], "relation_refs": [], "expected_invariants": ["equality holds exactly for collinear vectors"]},
        ],
    })


def _refine_linear_combination(explanation: dict[str, Any], visual: dict[str, Any]) -> None:
    """Present subsection 1.2.4 as the lecture's definition and its reading.

    讲义 1.2.4 只给出定义 1.9 与一句说明，没有单独的几何图或数值例。这里用
    a=(3,1)、b=(1,2) 说明 2a-b=2a+(-b)=(5,0) 就是一个线性组合，
    并把它做成三步数学案例流程：第一步给出 a、b，第二步在 a、b 之上叠加带系数的
    各项 2a 与 -b（缩放项用与原向量不同的颜色区分），第三步给出线性组合的结果。
    """

    claim_refs = ["claim.ch01.ops.linear-combination"]
    explanation.update({
        "title": "线性组合",
        "summary": "线性组合把向量的数乘与加法合并为一个表达式；系数标明每个向量参与多少。",
        "definition": (
            r"给定向量 $\boldsymbol v_1,\boldsymbol v_2,\ldots,\boldsymbol v_n$ 和标量 "
            r"$\alpha_1,\alpha_2,\ldots,\alpha_n$，称"
            "\n\n"
            r"$$\alpha_1\boldsymbol v_1+\alpha_2\boldsymbol v_2+\cdots+\alpha_n\boldsymbol v_n$$"
            "\n\n"
            r"为 $\boldsymbol v_1,\ldots,\boldsymbol v_n$ 的一个线性组合；$\alpha_i$ 称为系数。"
        ),
        "formula": r"\alpha_1\boldsymbol v_1+\alpha_2\boldsymbol v_2+\cdots+\alpha_n\boldsymbol v_n",
        "derivation": [],
        # 讲义 1.2.4 只有定义与一句说明，没有独立的几何解释；按讲义原样给出。
        "geometric_meaning": (
            r"向量的加法与数乘组合在一起，就是线性组合：先按系数缩放各向量，再把所得向量相加。"
            "\n\n"
            r"后面第2章的“矩阵$\times$向量”本质就是矩阵各列的线性组合。"
        ),
        "worked_examples": [],
        "symbol_roles": {"v_1": "vector_a", "v_2": "vector_b", "alpha_1": "scalar", "alpha_2": "scalar"},
    })
    for key in (
        "intuition", "connections", "transfer_note", "conclusion", "read_guide",
        "analogy_boundary", "invariants", "pitfalls",
    ):
        explanation.pop(key, None)

    explanation["worked_examples"] = [
        {
            "id": "example.linear-combination.vectors",
            "title": "第一步：向量 a 与 b",
            "kind": "scalar_multiple",
            "given": [1, [3, 1]],
            "calculation": [r"$$\boldsymbol a=(3,1),\qquad \boldsymbol b=(1,2)$$"],
            "result": [3.0, 1.0],
            "checks": [{"name": "scalar_multiple", "expected": [3.0, 1.0], "tolerance": 1e-9}],
            "claim_refs": claim_refs,
        },
        {
            "id": "example.linear-combination.terms",
            "title": "第二步：2a 与 -b",
            "kind": "vector_addition",
            "given": [[6, 2], [-1, -2]],
            "calculation": [r"$$2\boldsymbol a=(6,2),\qquad -\boldsymbol b=(-1,-2)$$"],
            "result": [5.0, 0.0],
            "checks": [{"name": "sum", "expected": [5.0, 0.0], "tolerance": 1e-9}],
            "claim_refs": claim_refs,
        },
        {
            "id": "example.linear-combination.result",
            "title": "第三步：线性组合",
            "kind": "vector_addition",
            "given": [[6, 2], [-1, -2]],
            "calculation": [
                r"$$2\boldsymbol a-\boldsymbol b=2\boldsymbol a+(-\boldsymbol b)=(6,2)+(-1,-2)=(5,0)$$",
            ],
            "result": [5.0, 0.0],
            "checks": [{"name": "sum", "expected": [5.0, 0.0], "tolerance": 1e-9}],
            "claim_refs": claim_refs,
        },
    ]
    visual.update({
        "scene_kind": "2d",
        "entities": [
            {"id": "a", "kind": "vector", "dimension": 2, "value": [3, 1], "role": "vector_a", "label": "a", "claim_refs": claim_refs},
            {"id": "b", "kind": "vector", "dimension": 2, "value": [1, 2], "role": "vector_b", "label": "b", "claim_refs": claim_refs},
            {"id": "two_a", "kind": "vector", "dimension": 2, "value": [6, 2], "role": "transformed_a", "label": "2a", "claim_refs": claim_refs},
            {"id": "neg_b", "kind": "vector", "dimension": 2, "value": [-1, -2], "role": "transformed_b", "label": "-b", "claim_refs": claim_refs},
            {"id": "combination", "kind": "vector", "dimension": 2, "value": [5, 0], "role": "combination", "label": "2a-b", "claim_refs": claim_refs},
        ],
        "relations": [{
            "id": "rel.linear-combination.result", "kind": "linear_combination",
            "source_ref": "two_a", "target_ref": "neg_b", "parameters": {}, "claim_refs": claim_refs,
        }],
        "stages": [
            {
                "id": "stage.linear-combination.vectors", "title": "第一步：向量 a 与 b",
                "caption": r"$\boldsymbol a=(3,1)$、$\boldsymbol b=(1,2)$ 从原点出发。",
                "layout": "overlay", "input_entity_refs": ["a", "b"], "output_entity_refs": [],
                "relation_refs": [], "expected_invariants": ["两个向量共用同一个原点"],
            },
            {
                "id": "stage.linear-combination.terms", "title": "第二步：2a 与 -b",
                "caption": r"系数 2 与 −1 作用在 $\boldsymbol a$、$\boldsymbol b$ 上，得到 $2\boldsymbol a=(6,2)$ 与 $-\boldsymbol b=(-1,-2)$。",
                "layout": "overlay", "input_entity_refs": ["a", "b", "two_a", "neg_b"], "output_entity_refs": [],
                "relation_refs": [], "expected_invariants": ["按系数缩放各向量"],
            },
            {
                "id": "stage.linear-combination.result", "title": "第三步：线性组合 2a-b",
                "caption": r"把各项相加：$2\boldsymbol a+(-\boldsymbol b)=(5,0)$。",
                "layout": "overlay", "input_entity_refs": ["two_a", "neg_b"], "output_entity_refs": ["combination"],
                "relation_refs": ["rel.linear-combination.result"], "expected_invariants": ["系数 2、−1 的组合等于 (5,0)"],
            },
        ],
    })
    explanation["sections"] = [
        {"id": section_id, "title": section_id, "text": "", "claim_refs": claim_refs}
        for section_id in ("definition", "formula", "worked_examples", "geometric_meaning")
    ]
    explanation["case_layout"] = {
        # 线性组合按输入、缩放、合成三步并排展示。
        "default_pane_count": 3,
        "cases": [
            {
                "id": "case.linear-combination.vectors", "topic_id": "ch01.ops.linear-combination",
                "example_ref": "example.linear-combination.vectors", "claim_refs": claim_refs,
                "stage_refs": ["stage.linear-combination.vectors"], "purpose": "第一步：向量 a、b",
            },
            {
                "id": "case.linear-combination.terms", "topic_id": "ch01.ops.linear-combination",
                "example_ref": "example.linear-combination.terms", "claim_refs": claim_refs,
                "stage_refs": ["stage.linear-combination.terms"], "purpose": "第二步：2a 与 -b",
            },
            {
                "id": "case.linear-combination.result", "topic_id": "ch01.ops.linear-combination",
                "example_ref": "example.linear-combination.result", "claim_refs": claim_refs,
                "stage_refs": ["stage.linear-combination.result"], "purpose": "第三步：线性组合 2a-b",
            },
        ],
    }


_PROOF_TOPIC_SPECS: dict[str, dict[str, Any]] = {
    # 1.5 的构造图和复算结果共用讲义输入 `a`、`b`。
    "ch01.proof.midline": {
        # B、C 避开坐标轴，防止构造图退化。
        "a": [3.6, 1.2],
        "b": [1.2, 3.2],
        "case_title": "三角形中位线定理",
        "invariant": r"$DE$ 与 $BC$ 平行且长度恒为 $BC$ 的一半",
        "title": "三角形中位线定理",
        "summary": r"三角形两边中点的连线平行于第三边，且长度是第三边的一半。",
        "definition": r"三角形两边中点的连线平行于第三边，且长度是第三边的一半。",
        "formula": r"\overrightarrow{DE}=\frac12(\boldsymbol b-\boldsymbol a)=\frac12\overrightarrow{BC}",
        # 中位线定理按讲义保留为一段向量证明。
        "derivation": [
            r"取 $A$ 为原点，设 $\overrightarrow{AB}=\boldsymbol a$，$\overrightarrow{AC}=\boldsymbol b$"
            "\n\n"
            r"$\because D$ 是 $AB$ 中点，$E$ 是 $AC$ 中点"
            "\n\n"
            r"$\therefore \overrightarrow{AD}=\frac12\boldsymbol a$，$\overrightarrow{AE}=\frac12\boldsymbol b$"
            "\n\n"
            r"$\therefore \overrightarrow{DE}=\overrightarrow{AE}-\overrightarrow{AD}=\frac12\boldsymbol b-\frac12\boldsymbol a=\frac12(\boldsymbol b-\boldsymbol a)$"
            "\n\n"
            r"$\because \overrightarrow{BC}=\overrightarrow{AC}-\overrightarrow{AB}=\boldsymbol b-\boldsymbol a$"
            "\n\n"
            r"$\therefore \overrightarrow{DE}=\frac12\overrightarrow{BC}$"
            "\n\n"
            r"即 $DE$ 平行于 $BC$，且长度是 $BC$ 的一半",

        ],
        # 1.5.2 仅保留"命题"和"向量证明"。
        "sections": ("definition", "formula", "derivation"),
        "section_titles": {
            "definition": "命题",
            "derivation": "向量证明",
        },
    },
    "ch01.proof.centroid": {
        # B 避开 x 轴，防止构造图退化。
        "a": [4.5, 0.6],
        "b": [1.5, 3.0],
        "case_title": "三角形重心定理",
        "invariant": r"重心把每条中线都分成 $2:1$ 的两段",
        "title": "三角形重心定理",
        "summary": r"三角形三条中线交于一点（重心），且重心到顶点的距离是到对边中点距离的 $2$ 倍。",
        "definition": r"三角形三条中线交于一点（重心），且重心到顶点的距离是到对边中点距离的 $2$ 倍。",
        "formula": r"\overrightarrow{AG}=\frac23\overrightarrow{AD}=\frac{\boldsymbol a+\boldsymbol b}{3}",
        # 补充例题保留连续证明，并补全三条中线的 2:1 验证。
        "derivation": [
            r"取 $A$ 为原点，设 $\overrightarrow{AB}=\boldsymbol a$，$\overrightarrow{AC}=\boldsymbol b$"
            "\n\n"
            r"$\because D$ 是 $BC$ 边中点"
            "\n\n"
            r"$\therefore \overrightarrow{AD}=\frac{\boldsymbol a+\boldsymbol b}{2}$"
            "\n\n"
            r"设重心 $G$ 在 $AD$ 上且 $\overrightarrow{AG}:\overrightarrow{GD}=2:1$"
            "\n\n"
            r"$\therefore \overrightarrow{AG}=\frac23\overrightarrow{AD}=\frac{\boldsymbol a+\boldsymbol b}{3}$"
            "\n\n"
            r"再验证 $G$ 也在中线 $CE$ 上，其中 $E$ 是 $AB$ 边中点，$\overrightarrow{AE}=\frac12\boldsymbol a$"
            "\n\n"
            r"$\overrightarrow{CG}=\overrightarrow{AG}-\overrightarrow{AC}=\frac{\boldsymbol a+\boldsymbol b}{3}-\boldsymbol b=\frac{\boldsymbol a-2\boldsymbol b}{3}=\frac23\left(\frac{\boldsymbol a}{2}-\boldsymbol b\right)=\frac23\overrightarrow{CE}$"
            "\n\n"
            r"$\therefore \overrightarrow{CG}:\overrightarrow{GE}=2:1$，$G$ 在中线 $CE$ 上"
            "\n\n"
            r"同理 $F$ 是 $AC$ 边中点，$\overrightarrow{AF}=\frac12\boldsymbol b$"
            "\n\n"
            r"$\overrightarrow{BG}=\overrightarrow{AG}-\overrightarrow{AB}=\frac{\boldsymbol b-2\boldsymbol a}{3}=\frac23\left(\frac{\boldsymbol b}{2}-\boldsymbol a\right)=\frac23\overrightarrow{BF}$"
            "\n\n"
            r"$\therefore \overrightarrow{BG}:\overrightarrow{GF}=2:1$，$G$ 在中线 $BF$ 上"
            "\n\n"
            r"三条中线 $AD$、$CE$、$BF$ 交于同一点 $G$，且 $G$ 到顶点的距离是到对边中点距离的 $2$ 倍",
        ],
        # 补充例题仅保留"命题"和"向量证明"。
        "sections": ("definition", "formula", "derivation"),
        "section_titles": {
            "definition": "命题",
            "derivation": "向量证明",
        },
    },
    "ch01.proof.parallelogram-diagonals": {
        "a": [3.2, 0.4],
        "b": [1.0, 2.6],
        "case_title": "平行四边形对角线互相平分",
        "invariant": r"两条对角线拥有同一个中点",
        "title": "平行四边形对角线互相平分",
        "summary": r"平行四边形的两条对角线互相平分。",
        "definition": r"平行四边形的两条对角线互相平分。",
        "formula": r"M(AC)=M(BD)=\frac{\boldsymbol a+\boldsymbol b}{2}",
        # BD 中点推导按讲义原式连续展示。
        "derivation": [
            r"取 $A$ 为原点，设 $\overrightarrow{AB}=\boldsymbol a$，$\overrightarrow{AD}=\boldsymbol b$"
            "\n\n"
            r"$\therefore C=\boldsymbol a+\boldsymbol b$"
            "\n\n"
            r"对角线 $AC$ 的中点为 $\frac{\boldsymbol a+\boldsymbol b}{2}$"
            "\n\n"
            r"$\therefore$ 对角线 $BD$ 的中点为 $\frac{\boldsymbol a+(\boldsymbol a+\boldsymbol b-\boldsymbol a)}{2}=\frac{2\boldsymbol a+\boldsymbol b-\boldsymbol a}{2}=\frac{\boldsymbol a+\boldsymbol b}{2}$"
            "\n\n"
            r"两条对角线的中点重合，即两条对角线互相平分",
        ],
        "sections": ("definition", "formula", "derivation"),
        "section_titles": {
            "definition": "命题",
            "derivation": "向量证明",
        },
    },
}


def _refine_geometry_proof(topic_id: str, explanation: dict[str, Any], visual: dict[str, Any]) -> None:
    """Publish the constructed figure for one section 1.5 geometry proof.

    The graph declares only the two lecture inputs; the compiler derives the
    midpoints, medians and diagonals from them, so the visual evidence cannot
    disagree with the worked numbers.
    """

    spec = _PROOF_TOPIC_SPECS[topic_id]
    claim_refs = [f"claim.{topic_id}"]
    section_ids = tuple(
        spec.get(
            "sections",
            ("definition", "formula", "derivation", "worked_examples", "geometric_meaning"),
        )
    )
    # 软件分节标题直接沿用讲义标题。
    section_titles = {
        "definition": "定义",
        "formula": "公式",
        "derivation": "向量证明",
        "worked_examples": "案例",
        "geometric_meaning": "几何意义",
    }
    section_titles.update(dict(spec.get("section_titles", {})))
    # 讲义没有案例时不生成案例布局，图形由唯一阶段绘制。
    with_case = "worked_examples" in section_ids
    example: dict[str, Any] | None = None
    if with_case:
        example = {
            "id": f"example.{topic_id}",
            "title": spec["case_title"],
            "kind": spec["example_kind"],
            "given": spec["example_given"],
            "calculation": list(spec["example_calculation"]),
            "result": spec["example_result"],
            "checks": [
                {
                    "name": spec["example_check"],
                    "expected": spec["example_result"],
                    "tolerance": 1e-9,
                }
            ],
            "claim_refs": claim_refs,
        }
    explanation.update(
        {
            "title": spec["title"],
            "summary": spec["summary"],
            "definition": spec["definition"],
            "formula": spec["formula"],
            "derivation": list(spec["derivation"]),
            "geometric_meaning": (
                spec.get("geometric_meaning", "") if "geometric_meaning" in section_ids else ""
            ),
            "worked_examples": [example] if example is not None else [],
        }
    )
    for key in (
        "intuition", "connections", "transfer_note", "conclusion", "read_guide",
        "analogy_boundary", "invariants", "pitfalls",
    ):
        explanation.pop(key, None)
    explanation["sections"] = [
        {"id": item, "title": section_titles.get(item, item), "text": "", "claim_refs": claim_refs}
        for item in section_ids
    ]
    explanation["symbol_roles"] = {"a": "vector_a", "b": "vector_b"}

    relation_id = f"rel.proof.{topic_id}"
    # 窗格边框已显示案例用途，阶段前缀用于抑制场景内重复标题。
    steps = list(spec.get("steps", ()) or ())
    if steps:
        # 过程型内容每步使用一个窗格。
        stage_ids = [f"stage.case.{topic_id}.{index}" for index in range(1, len(steps) + 1)]
        stages = [
            {
                "id": stage_id, "title": title, "caption": "",
                "layout": "overlay",
                "input_entity_refs": ["proof_a", "proof_b"], "output_entity_refs": [],
                "relation_refs": [relation_id],
                "expected_invariants": [spec["invariant"]],
            }
            for stage_id, title in zip(stage_ids, steps)
        ]
        cases = [
            {
                "id": f"case.proof.{topic_id}.{index}", "topic_id": topic_id,
                "example_ref": example["id"], "claim_refs": claim_refs,
                "stage_refs": [stage_id], "purpose": title,
            }
            for index, (stage_id, title) in enumerate(zip(stage_ids, steps), start=1)
        ]
        default_pane_count = len(steps)
    else:
        stage_id = f"stage.case.{topic_id}.1"
        stages = [
            {
                "id": stage_id, "title": spec["case_title"], "caption": "",
                "layout": "overlay",
                "input_entity_refs": ["proof_a", "proof_b"], "output_entity_refs": [],
                "relation_refs": [relation_id],
                "expected_invariants": [spec["invariant"]],
            }
        ]
        cases = (
            [
                {
                    "id": f"case.proof.{topic_id}", "topic_id": topic_id,
                    "example_ref": example["id"], "claim_refs": claim_refs,
                    "stage_refs": [stage_id], "purpose": spec["case_title"],
                }
            ]
            if example is not None
            else []
        )
        default_pane_count = 1
    visual.update(
        {
            "scene_kind": "2d",
            "entities": [
                {
                    "id": "proof_a", "kind": "vector", "dimension": 2, "value": list(spec["a"]),
                    "role": "vector_a", "label": "a", "claim_refs": claim_refs,
                },
                {
                    "id": "proof_b", "kind": "vector", "dimension": 2, "value": list(spec["b"]),
                    "role": "vector_b", "label": "b", "claim_refs": claim_refs,
                },
            ],
            "relations": [
                {
                    "id": relation_id, "kind": "invariant",
                    "source_ref": "proof_a", "target_ref": "proof_b",
                    "parameters": {}, "claim_refs": claim_refs,
                }
            ],
            "stages": stages,
        }
    )
    if cases:
        explanation["case_layout"] = {
            "default_pane_count": default_pane_count,
            "cases": cases,
        }
    else:
        explanation.pop("case_layout", None)


# 2.4 用两条路线到达同一终点解释分配律；2.5 保留四步矩阵变换案例；2.7 用两个窗格对比同一旋转在不同基下的矩阵。
_MATRIX_VECTOR_TOPIC_SPECS: dict[str, dict[str, Any]] = {
    "ch02.matrix.additive-distributivity": {
        "title": "矩阵加法与变换分配律",
        "statement": "矩阵按对应位置相加、按元素数乘；先加矩阵再变换等于先各自变换再加结果。",
        "summary": "一句话动机：向量有加法和数乘，矩阵作为向量的集合，自然也继承了这些运算。",
        "definition": "\n\n".join(
            (
                r"一句话动机：向量有加法和数乘，矩阵作为向量的集合，自然也继承了这些运算。",
                r"**（矩阵加法）** 两个同型矩阵 $\boldsymbol A = [a_{ij}]$ 和 $\boldsymbol B = [b_{ij}]$（都是 $m \times n$），其和为",
                r"$$(\boldsymbol A + \boldsymbol B)_{ij} = a_{ij} + b_{ij}$$",
                r"即对应位置的元素相加。写成矩阵就是",
                r"$$\boldsymbol A+\boldsymbol B=\begin{pmatrix}a_{11}&a_{12}\\a_{21}&a_{22}\end{pmatrix}+\begin{pmatrix}b_{11}&b_{12}\\b_{21}&b_{22}\end{pmatrix}=\begin{pmatrix}a_{11}+b_{11}&a_{12}+b_{12}\\a_{21}+b_{21}&a_{22}+b_{22}\end{pmatrix}$$",
                r"**（矩阵数乘）** 标量 $k$ 乘以矩阵 $\boldsymbol A$，就是每个元素都乘以 $k$：",
                r"$$(k\boldsymbol A)_{ij} = k \cdot a_{ij}$$",
                r"即每个元素都乘以 $k$。写成矩阵就是",
                r"$$k\boldsymbol A=\begin{pmatrix}k\,a_{11}&k\,a_{12}\\k\,a_{21}&k\,a_{22}\end{pmatrix}$$",
                r"**（分配律）** 先加矩阵再变换 $=$ 先各自变换再加结果：",
                r"$$(\boldsymbol A + \boldsymbol B)\boldsymbol x = \boldsymbol A\boldsymbol x + \boldsymbol B\boldsymbol x$$",
                r"例题：",
                r"$$\boldsymbol A = \begin{pmatrix}1 & 2 \\ 3 & 4\end{pmatrix},\qquad \boldsymbol B = \begin{pmatrix}5 & 6 \\ 7 & 8\end{pmatrix}$$",
                r"$$\boldsymbol A + \boldsymbol B = \begin{pmatrix}1+5 & 2+6 \\ 3+7 & 4+8\end{pmatrix} = \begin{pmatrix}6 & 8 \\ 10 & 12\end{pmatrix}$$",
            )
        ),
        "claim_formula": r"(\boldsymbol A+\boldsymbol B)\boldsymbol x=\boldsymbol A\boldsymbol x+\boldsymbol B\boldsymbol x",
        "formula_symbols": ["A", "B", "x"],
        "symbol_roles": {"A": "matrix_a", "B": "matrix_b", "x": "vector_a"},
        "sections": (("definition", "定义"), ("worked_examples", "数学案例")),
        "entities": (
            # 第一窗格（先加矩阵再变换）：A+B = 3I 把 x=(1,1) 送到 (3,3)。
            ("mv_add_grid", "grid", [[3, 0], [0, 3]], "transformed_a", "A+B"),
            ("mv_add_x", "vector", [1, 1], "vector_a", "x"),
            ("mv_add_y1", "vector", [3, 3], "result", "(A+B)x"),
            # 第二窗格（先各自变换再相加）：Ax 与 Bx 相加也落在同一个终点 (3,3)。
            ("mv_add_ax", "vector", [2, 1], "transformed_a", "Ax"),
            ("mv_add_bx", "vector", [1, 2], "transformed_b", "Bx"),
            ("mv_add_y2", "vector", [3, 3], "result", "Ax+Bx"),
        ),
        "relations": (
            ("rel.case.ch02.matrix.additive-distributivity.endpoint", "compare", "mv_add_y1", "mv_add_y2"),
        ),
        "steps": (
            {
                "purpose": "第一步：先加矩阵，再变换",
                "invariant": "先加矩阵再变换：A+B=3I 把 x 送到 (3,3)",
                "given": [[[3, 0], [0, 3]], [1, 1]],
                "result": [3, 3],
                "lines": (
                    r"取两个各自只沿一个坐标轴拉伸的矩阵，再加上向量 $\boldsymbol x$：",
                    r"$$\boldsymbol A=\begin{pmatrix}2&0\\0&1\end{pmatrix},\qquad \boldsymbol B=\begin{pmatrix}1&0\\0&2\end{pmatrix},\qquad \boldsymbol x=\begin{pmatrix}1\\1\end{pmatrix}$$",
                    r"按定义把两个矩阵相加（对应位置相加），再让结果作用到 $\boldsymbol x$：",
                    r"$$\boldsymbol A+\boldsymbol B=\begin{pmatrix}2+1&0+0\\0+0&1+2\end{pmatrix}=\begin{pmatrix}3&0\\0&3\end{pmatrix}=3\begin{pmatrix}1&0\\0&1\end{pmatrix}$$",
                    r"$$(\boldsymbol A+\boldsymbol B)\boldsymbol x=3\begin{pmatrix}1\\1\end{pmatrix}=\begin{pmatrix}3\\3\end{pmatrix}$$",
                    r"这条路线的终点是 $(3,3)$。",
                ),
                "inputs": ("mv_add_grid", "mv_add_x", "mv_add_y1"),
                "outputs": (),
                "relations": (),
            },
            {
                "purpose": "第二步：先各自变换，再相加",
                "invariant": "先各自变换再相加：Ax+Bx 也落在 (3,3)",
                "given": [[[2, 0], [0, 1]], [1, 1]],
                "result": [2, 1],
                "lines": (
                    r"换一条路线：先让 $\boldsymbol A$、$\boldsymbol B$ 分别作用于 $\boldsymbol x$：",
                    r"$$\boldsymbol A\boldsymbol x=\begin{pmatrix}2&0\\0&1\end{pmatrix}\begin{pmatrix}1\\1\end{pmatrix}=\begin{pmatrix}2\\1\end{pmatrix},\qquad \boldsymbol B\boldsymbol x=\begin{pmatrix}1&0\\0&2\end{pmatrix}\begin{pmatrix}1\\1\end{pmatrix}=\begin{pmatrix}1\\2\end{pmatrix}$$",
                    r"再把两个结果按向量加法相加：",
                    r"$$\boldsymbol A\boldsymbol x+\boldsymbol B\boldsymbol x=\begin{pmatrix}2\\1\end{pmatrix}+\begin{pmatrix}1\\2\end{pmatrix}=\begin{pmatrix}3\\3\end{pmatrix}$$",
                    r"两条路线的终点都是 $(3,3)$，于是 $(\boldsymbol A+\boldsymbol B)\boldsymbol x=\boldsymbol A\boldsymbol x+\boldsymbol B\boldsymbol x$。",
                ),
                "inputs": ("mv_add_ax", "mv_add_bx", "mv_add_y2"),
                "outputs": (),
                "relations": ("rel.case.ch02.matrix.additive-distributivity.endpoint",),
            },
        ),
    },
    "ch02.matrix.transformed-grid": {
        "title": "矩阵变换",
        "statement": "矩阵的两列分别是标准基向量的像；知道两列如何移动，就能确定整张坐标网格的拉伸、旋转或压扁。",
        "summary": "一句话动机：矩阵乘以向量——本节是整门课最重要的运算，没有之一。",
        "definition": "\n\n".join(
            (
                r"设 $\boldsymbol A$ 是 $m \times n$ 矩阵，$\boldsymbol x$ 是 $n$ 维列向量。",
                r"$$\boldsymbol A=\begin{pmatrix}a_{11}&a_{12}&\cdots&a_{1n}\\a_{21}&a_{22}&\cdots&a_{2n}\\\vdots&\vdots&\ddots&\vdots\\a_{m1}&a_{m2}&\cdots&a_{mn}\end{pmatrix},\qquad \boldsymbol x=\begin{pmatrix}x_{1}\\x_{2}\\\vdots\\x_{n}\end{pmatrix}$$",
                r"算法一（行视角 — 内积法）：$\boldsymbol A\boldsymbol x$ 的第 $i$ 个分量 $=$ $\boldsymbol A$ 的第 $i$ 行与 $\boldsymbol x$ 的内积。",
                '这是"怎么算"——算得快，但不解释"什么意思"。',
                "算法二（列视角 — 线性组合法）：",
                r"$$\boldsymbol A\boldsymbol x=x_{1}\cdot\begin{pmatrix}a_{11}\\a_{21}\\\vdots\\a_{m1}\end{pmatrix}+x_{2}\cdot\begin{pmatrix}a_{12}\\a_{22}\\\vdots\\a_{m2}\end{pmatrix}+\cdots+x_{n}\cdot\begin{pmatrix}a_{1n}\\a_{2n}\\\vdots\\a_{mn}\end{pmatrix}$$",
                r'这就是"什么意思"：把矩阵各列取出来，用 $\boldsymbol x$ 的分量当系数，组合起来。结果向量的每一项都是"第 $k$ 列 $\times$ 系数"的叠加。',
                r"**（矩阵变换的基向量解释）** 设 $\boldsymbol A$ 是 $2 \times 2$ 矩阵。则：",
                r"- $\boldsymbol A$ 的第 1 列 $=$ 标准基向量 $\boldsymbol e_{1}$ 被 $\boldsymbol A$ 送到的新位置",
                r"- $\boldsymbol A$ 的第 2 列 $=$ $\boldsymbol e_{2}$ 被 $\boldsymbol A$ 送到的新位置",
                r"任何向量 $\boldsymbol x=(x_{1},x_{2})$ 被 $\boldsymbol A$ 变换后：",
                r"$$\boldsymbol A\boldsymbol x=x_{1}\cdot(\boldsymbol e_{1}\text{ 被 }\boldsymbol A\text{ 送到哪儿})+x_{2}\cdot(\boldsymbol e_{2}\text{ 被 }\boldsymbol A\text{ 送到哪儿})$$",
                r'直觉总结：矩阵 $\boldsymbol A$ 的两列 $=$ 两根"新尺子"的方向和长度。$\boldsymbol A\boldsymbol x=$ 用新尺子重新"量"出 $\boldsymbol x$ 的位置。',
                r'整个坐标网格被 $\boldsymbol A$ 拉伸、旋转、压扁——网格的变形由两列完全确定。这就是"线性变换"的视觉本质。',
            )
        ),
        "claim_formula": r"\boldsymbol A\boldsymbol x=x_{1}\boldsymbol A\boldsymbol e_{1}+x_{2}\boldsymbol A\boldsymbol e_{2}",
        "formula_symbols": ["A", "x"],
        "symbol_roles": {"A": "matrix_a", "x": "combination"},
        "sections": (("definition", "定义"), ("worked_examples", "数学案例")),
        "entities": (
            # 第一窗格（标准基向量）：只画两根标尺，不画网格。
            ("mv_e1", "vector", [1, 0], "basis_e1", "e1"),
            ("mv_e2", "vector", [0, 1], "basis_e2", "e2"),
            # 参考网格只作为「两列决定网格变形」这一不变式的左端保留，不再进入任何窗格。
            ("mv_grid_base", "grid", [[1, 0], [0, 1]], "construction", "I"),
            # 第二窗格（横向拉伸）：A = [[2, 0], [0, 1]]，两列落在坐标轴上。
            ("mv_grid_stretch", "grid", [[2, 0], [0, 1]], "transformed_a", "A"),
            ("mv_stretch_e1", "vector", [2, 0], "vector_a", "Ae1"),
            ("mv_stretch_e2", "vector", [0, 1], "vector_b", "Ae2"),
            # 第三窗格（逆时针旋转）：R = [[0, -1], [1, 0]]。
            ("mv_grid_rotate", "grid", [[0, -1], [1, 0]], "transformed_a", "R"),
            ("mv_rotate_e1", "vector", [0, 1], "vector_a", "Re1"),
            ("mv_rotate_e2", "vector", [-1, 0], "vector_b", "Re2"),
            # 第四窗格（两列的像与网格变形）：沿用原有 A = [[2, 1], [1, 2]]。
            ("mv_grid_A", "grid", [[2, 1], [1, 2]], "transformed_a", "A"),
            ("mv_ae1", "vector", [2, 1], "vector_a", "Ae1"),
            ("mv_ae2", "vector", [1, 2], "vector_b", "Ae2"),
        ),
        "relations": (
            ("rel.case.ch02.matrix.transformed-grid.basis", "invariant", "mv_grid_base", "mv_grid_A"),
        ),
        "steps": (
            {
                "purpose": "第一步：标准基向量",
                "invariant": "标准基 (1, 0)、(0, 1) 指出两个坐标方向",
                "given": [[[1, 0], [0, 1]], [1, 0]],
                "result": [1, 0],
                "lines": (
                    r"图中画出标准基 $\boldsymbol e_{1}=(1,0)$（终点 $E_1$）、$\boldsymbol e_{2}=(0,1)$（终点 $E_2$）。",
                    r"$$\boldsymbol e_{1}=(1,0),\qquad \boldsymbol e_{2}=(0,1)$$",
                    r"它们是量出平面内任何向量位置的两根“标尺”。",
                ),
                # 第一窗格只展示标准基向量，不画网格。
                "inputs": ("mv_e1", "mv_e2"),
                "outputs": (),
                "relations": (),
            },
            {
                "purpose": "第二步：横向拉伸",
                "invariant": "对角矩阵把 x 方向拉伸 2 倍，y 方向不动",
                "given": [[[2, 0], [0, 1]], [1, 0]],
                "result": [2, 0],
                "lines": (
                    r"取 $\boldsymbol A=\begin{pmatrix}2&0\\0&1\end{pmatrix}$，"
                    r"网格沿 $x$ 方向被拉伸 $2$ 倍：$\boldsymbol e_{1}$ 被送到 $(2,0)$（终点 $G_1$），"
                    r"$\boldsymbol e_{2}$ 停在 $(0,1)$（终点 $G_2$）。",
                    r"$$\boldsymbol A\boldsymbol e_{1}=(2,0),\qquad \boldsymbol A\boldsymbol e_{2}=(0,1)$$",
                ),
                "inputs": ("mv_grid_stretch", "mv_stretch_e1", "mv_stretch_e2"),
                "outputs": (),
                "relations": (),
            },
            {
                "purpose": "第三步：逆时针旋转",
                "invariant": "旋转保持长度，只改变方向",
                "given": [[[0, -1], [1, 0]], [1, 0]],
                "result": [0, 1],
                "lines": (
                    r"取 $\boldsymbol R=\begin{pmatrix}0&-1\\1&0\end{pmatrix}$，"
                    r"网格整体逆时针转过 $90^\circ$：$\boldsymbol e_{1}$ 被送到 $(0,1)$（终点 $H_1$），"
                    r"$\boldsymbol e_{2}$ 被送到 $(-1,0)$（终点 $H_2$）。",
                    r"$$\boldsymbol R\boldsymbol e_{1}=(0,1),\qquad \boldsymbol R\boldsymbol e_{2}=(-1,0)$$",
                ),
                "inputs": ("mv_grid_rotate", "mv_rotate_e1", "mv_rotate_e2"),
                "outputs": (),
                "relations": (),
            },
            {
                "purpose": "第四步：两列的像与网格变形",
                "invariant": "两列就是两条标准基向量被送到的位置",
                "given": [[[2, 1], [1, 2]], [1, 0]],
                "result": [2, 1],
                "lines": (
                    r"图中画出 $\boldsymbol A=\begin{pmatrix}2&1\\1&2\end{pmatrix}$ 作用后的网格，"
                    r"以及标准基被送到的新位置 $\boldsymbol A\boldsymbol e_{1}=(2,1)$（终点 $F_1$）、$\boldsymbol A\boldsymbol e_{2}=(1,2)$（终点 $F_2$）——它们就是 $\boldsymbol A$ 的两列。",
                    r"$$\boldsymbol A\boldsymbol e_{1}=(2,1),\qquad \boldsymbol A\boldsymbol e_{2}=(1,2)$$",
                ),
                "inputs": ("mv_grid_A", "mv_ae1", "mv_ae2"),
                "outputs": (),
                "relations": ("rel.case.ch02.matrix.transformed-grid.basis",),
            },
        ),
    },
    "ch02.matrix.basis": {
        "title": "基",
        "statement": "同一个变换，用不同的基描述，矩阵就不同。",
        "summary": "同一个变换，用不同的基描述，矩阵就不同。",
        "definition": "\n\n".join(
            (
                r"一句话动机：同一个变换，用不同的基描述，矩阵就不同——这是「坐标系自由」的第一步。",
                r"**（基）** $R^{n}$ 中 $n$ 个线性无关的向量组成的一组有序向量，称为 $R^{n}$ 的一组基。",
                r"我们平时用的 $(\boldsymbol e_{1}, \boldsymbol e_{2})$ 只是众多基中的一组——它是标准基，但不是唯一的基。",
                r'核心认知：变换本身是客观的（比如"逆时针旋转 $90^\circ$"），但描述它的矩阵取决于你用什么基来记录坐标。',
                r"用标准基时，旋转 $90^\circ$ 的矩阵是 $\begin{pmatrix}0 & -1 \\ 1 & 0\end{pmatrix}$；但换一组基，同样的旋转，矩阵就变了。",
            )
        ),
        "claim_formula": (
            r"\boldsymbol A=\begin{pmatrix}0&-1\\1&0\end{pmatrix}\ (\text{标准基}),\qquad "
            r"\boldsymbol B=\begin{pmatrix}-1&-2\\1&1\end{pmatrix}\ (\text{新基})"
        ),
        "formula_symbols": ["A", "B"],
        "symbol_roles": {"A": "matrix_a", "B": "matrix_a"},
        "sections": (("definition", "定义"), ("worked_examples", "数学案例")),
        "entities": (
            # 两个窗格画同一个物理输入 x=(2,1) 及其输出 (-1,2)。
            ("mv_basis_grid_a", "grid", [[0, -1], [1, 0]], "transformed_a", "A"),
            ("mv_basis_e1", "vector", [1, 0], "basis_primary", "e1"),
            ("mv_basis_e2", "vector", [0, 1], "basis_secondary", "e2"),
            ("mv_basis_x_a", "vector", [2, 1], "vector_a", "x"),
            ("mv_basis_rx_a", "vector", [-1, 2], "vector_b", "Rx"),
            # 第二窗格把同一个旋转写在新基 B=(b1,b2) 下。
            ("mv_basis_grid_b", "grid", [[-1, -2], [1, 1]], "transformed_a", "B"),
            ("mv_basis_b1", "vector", [1, 0], "basis_primary", "b1"),
            ("mv_basis_b2", "vector", [1, 1], "basis_secondary", "b2"),
            ("mv_basis_x_b", "vector", [2, 1], "vector_a", "x"),
            ("mv_basis_rx_b", "vector", [-1, 2], "vector_b", "Rx"),
        ),
        "relations": (
            ("rel.case.ch02.matrix.basis.change", "compare", "mv_basis_grid_a", "mv_basis_grid_b"),
        ),
        "steps": (
            {
                "purpose": "第一步：标准基描述",
                "invariant": "x=(2,1) 经过逆时针旋转 90° 后变为 (-1,2)",
                "given": [[[0, -1], [1, 0]], [2, 1]],
                "result": [-1, 2],
                "lines": (
                    r"取输入向量 $\boldsymbol x=(2,1)$，用标准基描述逆时针旋转 $90^\circ$。",
                    r"$$\boldsymbol A=\begin{pmatrix}0&-1\\1&0\end{pmatrix},\qquad \boldsymbol A\boldsymbol x=(-1,2)$$",
                    r"因此输入向量的几何终点从 $(2,1)$ 到 $(-1,2)$。",
                ),
                "inputs": ("mv_basis_grid_a", "mv_basis_e1", "mv_basis_e2", "mv_basis_x_a"),
                "outputs": ("mv_basis_rx_a",),
                "relations": (),
            },
            {
                "purpose": "第二步：换一组基，矩阵改变",
                "invariant": "同一个旋转的物理输入和输出不变，只是坐标变为 [x]_B=(1,1)、[Ax]_B=(-3,2)",
                "given": [[[-1, -2], [1, 1]], [1, 1]],
                "result": [-3, 2],
                "lines": (
                    r"换一组基 $\boldsymbol b_{1}=(1,0)$、$\boldsymbol b_{2}=(1,1)$，同一个逆时针旋转 $90^\circ$ 的矩阵改写为 $\boldsymbol B$。",
                    r"$$\boldsymbol B=\begin{pmatrix}-1&-2\\1&1\end{pmatrix},\qquad [\boldsymbol x]_{B}=(1,1),\qquad [\boldsymbol A\boldsymbol x]_{B}=(-3,2)$$",
                    r"第二窗格中的输入和输出仍在同一组物理位置 $(2,1)$、$(-1,2)$；改变的是记录它们所用的基。",
                ),
                "inputs": ("mv_basis_grid_b", "mv_basis_b1", "mv_basis_b2", "mv_basis_x_b"),
                "outputs": ("mv_basis_rx_b",),
                "relations": ("rel.case.ch02.matrix.basis.change",),
            },
        ),
    },
}


# 2.9 用对照案例展示线性相关性，并以四个矩阵展示不同秩。
_SUBSPACE_LESSON_SPECS: dict[str, dict[str, Any]] = {
    "ch02.subspace.independence": {
        "title": "线性无关与线性相关",
        "statement": "一组向量线性无关，当且仅当只有全零系数才能把它们的线性组合变成零向量；只要有一个向量能被其余向量拼出来，这组向量就线性相关。",
        "summary": r'记忆口诀：线性无关 $=$ 每个向量都是"必要的"，少一个就不完整。',
        "definition": "\n\n".join(
            (
                r"**（线性无关）** 一组向量 $\boldsymbol v_{1}, \boldsymbol v_{2}, ..., \boldsymbol v_{k}$ 称为线性无关的，如果只有当所有系数都为零时，它们的线性组合才等于零向量：",
                r"$$c_{1} \cdot \boldsymbol v_{1} + c_{2} \cdot \boldsymbol v_{2} + ... + c_{k} \cdot \boldsymbol v_{k} = 0 \Rightarrow c_{1} = c_{2} = ... = c_{k} = 0$$",
                r"**（线性相关）** 如果存在不全为零的系数使上述组合为零，则称这组向量线性相关。",
                r'换句话说，线性相关 $=$ 至少有一个向量可以被其他向量"拼出来"。',
                "几何理解（最核心）：",
                "\n".join(
                    (
                        "| 向量数量 | 线性无关 | 线性相关 |",
                        "| --- | --- | --- |",
                        r"| 2个在 $R^{2}$ | 不共线（两个方向不同） | 共线（一个方向） |",
                        r'| 3个在 $R^{2}$ | 不可能——必相关 | 三个都在同一平面上，至少有一个"多余" |',
                        r"| 2个在 $R^{3}$ | 不共线 | 共线 |",
                        r"| 3个在 $R^{3}$ | 不共面（三个方向张成整个空间） | 共面 |",
                    )
                ),
                r'💡 记忆口诀：线性无关 $=$ 每个向量都是"必要的"，少一个就不完整。',
            )
        ),
        "claim_formula": r"c_{1}\boldsymbol v_{1}+c_{2}\boldsymbol v_{2}=0\Rightarrow c_{1}=c_{2}=0",
        "formula_symbols": ["v_1", "v_2"],
        "symbol_roles": {"v_1": "vector_a", "v_2": "vector_b"},
        "sections": (("definition", "定义"), ("worked_examples", "数学案例")),
        "entities": (
            # 第一步：两个方向不同，张成整个平面。
            ("ind_v1", "vector", [2, 1], "vector_a", "v1"),
            ("ind_v2", "vector", [-1, 2], "vector_b", "v2"),
            ("ind_plane", "region", [[2, 1], [-1, 2]], "area", "span"),
            # 第二步：第二个向量是第一个的反向数乘，两条落在同一条直线上。
            ("ind_v2_collinear", "vector", [-2, -1], "vector_b", "v2"),
            ("ind_line", "region", [[2, 1]], "area", "span"),
            # 第三步：第三个向量正好是前两个的和。
            ("ind_v3", "vector", [1, 3], "combination", "v3"),
        ),
        "relations": (
            ("rel.case.ch02.subspace.independence.compare", "compare", "ind_v1", "ind_v2"),
            ("rel.case.ch02.subspace.independence.collinear", "linear_dependence", "ind_v1", "ind_v2_collinear"),
            ("rel.case.ch02.subspace.independence.combine", "linear_combination", "ind_v1", "ind_v3"),
        ),
        "steps": (
            {
                "purpose": "第一步：两个方向不同（线性无关）",
                "invariant": r"只有全零系数才能让 $c_{1}\boldsymbol v_{1}+c_{2}\boldsymbol v_{2}=\boldsymbol 0$ 成立",
                "given": [[[2, -1], [1, 2]], [1, 1]],
                "result": [1, 3],
                "lines": (
                    r"图中画出两条方向不同的向量 $\boldsymbol v_{1}=(2,1)$、$\boldsymbol v_{2}=(-1,2)$：它们不共线，两个方向各自有效，一起张成整个平面。",
                    r"$$\boldsymbol v_{1}+\boldsymbol v_{2}=(2,1)+(-1,2)=(1,3)$$",
                    r"要让 $c_{1}\boldsymbol v_{1}+c_{2}\boldsymbol v_{2}=\boldsymbol 0$，只能取 $c_{1}=c_{2}=0$——这就是线性无关。",
                ),
                "inputs": ("ind_v1", "ind_v2", "ind_plane"),
                "outputs": (),
                "relations": ("rel.case.ch02.subspace.independence.compare",),
            },
            {
                "purpose": "第二步：两个方向相同（线性相关）",
                "invariant": r"存在不全为零的系数 $c_{1}=1$、$c_{2}=1$ 使 $c_{1}\boldsymbol v_{1}+c_{2}\boldsymbol v_{2}=\boldsymbol 0$",
                "given": [[[2, -2], [1, -1]], [1, 1]],
                "result": [0, 0],
                "lines": (
                    r"把第二个向量换成 $\boldsymbol v_{2}=(-2,-1)=-\boldsymbol v_{1}$：它与 $\boldsymbol v_{1}=(2,1)$ 落在同一条直线上。",
                    r"$$\boldsymbol v_{1}+\boldsymbol v_{2}=(2,1)+(-2,-1)=(0,0)$$",
                    r"系数 $1$ 与 $1$ 不全为零，却拼出了零向量，所以这两个向量线性相关：其中一个可以被另一个拼出来。",
                ),
                "inputs": ("ind_v1", "ind_v2_collinear", "ind_line"),
                "outputs": (),
                "relations": ("rel.case.ch02.subspace.independence.collinear",),
            },
            {
                "purpose": "第三步：三个向量中有一个能被拼出来（必相关）",
                "invariant": r"$\boldsymbol v_{3}=\boldsymbol v_{1}+\boldsymbol v_{2}$，第三个向量是前两个的线性组合",
                "given": [[[2, -1], [1, 2]], [1, 1]],
                "result": [1, 3],
                "lines": (
                    r"再取第三个向量 $\boldsymbol v_{3}=(1,3)$：它正好是前两个的和 $\boldsymbol v_{1}+\boldsymbol v_{2}=(1,3)$。",
                    r"$$\boldsymbol v_{1}+\boldsymbol v_{2}-\boldsymbol v_{3}=(2,1)+(-1,2)-(1,3)=(0,0)$$",
                    r"系数 $(1,1,-1)$ 不全为零，所以平面里的三个向量一定线性相关——其中有一个是多余的。",
                ),
                "inputs": ("ind_v1", "ind_v2", "ind_v3"),
                "outputs": (),
                "relations": ("rel.case.ch02.subspace.independence.combine",),
            },
        ),
    },
    "ch02.subspace.rank": {
        "title": "秩",
        "statement": "矩阵的秩等于它的列向量中最大线性无关组的个数，也就是变换后空间的真实维度：满秩是面，秩 1 是线，秩 0 是点。",
        "summary": r'秩 $=$ 矩阵"真正有效"的列数——去掉那些"可以被其他列拼出来"的冗余列之后还剩几个。',
        "definition": "\n\n".join(
            (
                r"**（秩）** 矩阵 $\boldsymbol A$ 的秩，记为 $\operatorname{rank}(\boldsymbol A)$，等于 $\boldsymbol A$ 的列向量中最大线性无关组的个数。",
                r'简单理解：秩 $=$ 矩阵"真正有效"的列数——去掉那些"可以被其他列拼出来"的冗余列之后还剩几个。',
                "几何理解：",
                r'秩 $=$ 变换后空间的"真实维度"',
                "\n".join(
                    (
                        r'$\operatorname{rank} = 2 \rightarrow$  变换后是一个"面"（没有压缩）',
                        r'$\operatorname{rank} = 1 \rightarrow$  变换后是一条"线"（压缩了一维）',
                        r'$\operatorname{rank} = 0 \rightarrow$  变换后是一个"点"（全压缩为零矩阵）',
                    )
                ),
                "\n".join(
                    (
                        r"| 矩阵 | $\operatorname{rank}$ | 几何含义 |",
                        "| --- | --- | --- |",
                        r"| $\begin{pmatrix}1 & 0 \\ 0 & 1\end{pmatrix}$ | 2 | 什么都没压扁，全二维 |",
                        r"| $\begin{pmatrix}2 & 0 \\ 0 & 0\end{pmatrix}$ | 1 | y 方向全被压到零 $\rightarrow$ 只剩 x 轴 |",
                        r"| $\begin{pmatrix}1 & 2 \\ 2 & 4\end{pmatrix}$ | 1 | 两列共线 $\rightarrow$ 只张成一条线 |",
                        r"| $\begin{pmatrix}0 & 0 \\ 0 & 0\end{pmatrix}$ | 0 | 全压到原点 |",
                    )
                ),
                r"**（秩与行列式）** 对 $n \times n$ 矩阵 $\boldsymbol A$：$\operatorname{rank}(\boldsymbol A) = n \Leftrightarrow \det(\boldsymbol A) \neq 0 \Leftrightarrow \boldsymbol A$ 可逆",
                r'这意味着：$\det \neq 0$ 不仅仅是"面积不为零"——它等价于"所有列都线性无关"，即"变换没有压缩任何维度"。这条定理连通第2章和第3章。',
            )
        ),
        "claim_formula": r"\operatorname{rank}(\boldsymbol A)=\dim\operatorname{Col}(\boldsymbol A)",
        "formula_symbols": ["A"],
        "symbol_roles": {"A": "matrix_a"},
        "sections": (("definition", "定义"), ("worked_examples", "数学案例")),
        "entities": (
            # 第一步：单位阵，网格仍是整个平面（秩 2）。
            ("rk_grid_i", "grid", [[1, 0], [0, 1]], "construction", "A"),
            ("rk_plane", "region", [[1, 0], [0, 1]], "area", "Col(A)"),
            ("rk_a1_i", "vector", [1, 0], "vector_a", "a1"),
            ("rk_a2_i", "vector", [0, 1], "vector_b", "a2"),
            # 第二步：y 方向被压到零，只剩 x 轴（秩 1）。
            ("rk_grid_axis", "grid", [[2, 0], [0, 0]], "transformed_a", "A"),
            ("rk_a1_axis", "vector", [2, 0], "vector_a", "a1"),
            # 第三步：两列共线，只张成一条斜线（秩 1）。
            ("rk_grid_line", "grid", [[1, 2], [2, 4]], "transformed_a", "A"),
            ("rk_a1_line", "vector", [1, 2], "vector_a", "a1"),
            ("rk_a2_line", "vector", [2, 4], "vector_b", "a2"),
            # 第四步：全部压到原点（秩 0）。
            ("rk_grid_zero", "grid", [[0, 0], [0, 0]], "transformed_a", "A"),
        ),
        "relations": (
            ("rel.case.ch02.subspace.rank.full", "invariant", "rk_a1_i", "rk_a2_i"),
            ("rel.case.ch02.subspace.rank.axis", "collapses_to", "rk_grid_axis", "rk_a1_axis"),
            ("rel.case.ch02.subspace.rank.collinear", "linear_dependence", "rk_a1_line", "rk_a2_line"),
        ),
        "steps": (
            {
                "purpose": "第一步：什么都没压扁（秩 2）",
                "invariant": r"$\operatorname{rank}(\boldsymbol A)=2$：两列不共线，网格仍是整个平面",
                "given": [[1, 0], [0, 1]],
                "result": 1.0,
                "kind": "determinant",
                "check": "determinant",
                "lines": (
                    r"图中画出 $\boldsymbol A=\begin{pmatrix}1&0\\0&1\end{pmatrix}$ 作用后的网格：它仍是整个平面，什么都没被压扁。",
                    r"$$\det(\boldsymbol A)=1\times1-0\times0=1\neq0$$",
                    r"两列 $\boldsymbol a_{1}=(1,0)$、$\boldsymbol a_{2}=(0,1)$ 不共线，最大线性无关组有 $2$ 个向量，所以 $\operatorname{rank}(\boldsymbol A)=2$。",
                ),
                "inputs": ("rk_grid_i", "rk_plane", "rk_a1_i", "rk_a2_i"),
                "outputs": (),
                "relations": ("rel.case.ch02.subspace.rank.full",),
            },
            {
                "purpose": "第二步：y 方向被压到零（秩 1）",
                "invariant": r"$\operatorname{rank}(\boldsymbol A)=1$：两列相关，网格被压到 x 轴",
                "given": [[2, 0], [0, 0]],
                "result": 0.0,
                "kind": "determinant",
                "check": "determinant",
                "lines": (
                    r"图中画出 $\boldsymbol A=\begin{pmatrix}2&0\\0&0\end{pmatrix}$ 作用后的网格：y 方向全被压到零，整个平面只剩 $x$ 轴这条线。",
                    r"$$\det(\boldsymbol A)=2\times0-0\times0=0$$",
                    r"两列 $\boldsymbol a_{1}=(2,0)$、$\boldsymbol a_{2}=(0,0)$ 线性相关，最大线性无关组只有 $1$ 个向量，所以 $\operatorname{rank}(\boldsymbol A)=1$。",
                ),
                "inputs": ("rk_grid_axis", "rk_a1_axis"),
                "outputs": (),
                "relations": ("rel.case.ch02.subspace.rank.axis",),
            },
            {
                "purpose": "第三步：两列共线（秩 1）",
                "invariant": r"$\operatorname{rank}(\boldsymbol A)=1$：$\boldsymbol a_{2}=2\boldsymbol a_{1}$，网格被压到一条斜线",
                "given": [[1, 2], [2, 4]],
                "result": 0.0,
                "kind": "determinant",
                "check": "determinant",
                "lines": (
                    r"图中画出 $\boldsymbol A=\begin{pmatrix}1&2\\2&4\end{pmatrix}$ 作用后的网格：两列 $\boldsymbol a_{1}=(1,2)$、$\boldsymbol a_{2}=(2,4)=2\boldsymbol a_{1}$ 共线，平面被压到这条斜线上。",
                    r"$$\det(\boldsymbol A)=1\times4-2\times2=0$$",
                    r"$\boldsymbol a_{2}$ 能被 $\boldsymbol a_{1}$ 拼出来，最大线性无关组只有 $1$ 个向量，所以 $\operatorname{rank}(\boldsymbol A)=1$。",
                ),
                "inputs": ("rk_grid_line", "rk_a1_line", "rk_a2_line"),
                "outputs": (),
                "relations": ("rel.case.ch02.subspace.rank.collinear",),
            },
            {
                "purpose": "第四步：全压到原点（秩 0）",
                "invariant": r"$\operatorname{rank}(\boldsymbol A)=0$：两列都是零向量，网格缩成原点",
                "given": [[0, 0], [0, 0]],
                "result": 0.0,
                "kind": "determinant",
                "check": "determinant",
                "lines": (
                    r"图中画出 $\boldsymbol A=\begin{pmatrix}0&0\\0&0\end{pmatrix}$ 作用后的网格：全部压到原点。",
                    r"$$\det(\boldsymbol A)=0\times0-0\times0=0$$",
                    r"两列都是零向量，没有线性无关的列，最大线性无关组有 $0$ 个向量，所以 $\operatorname{rank}(\boldsymbol A)=0$。",
                ),
                "inputs": ("rk_grid_zero",),
                "outputs": (),
                "relations": (),
            },
        ),
    },
}


def _refine_subspace_lesson(topic_id: str, explanation: dict[str, Any], visual: dict[str, Any]) -> None:
    """Publish one 2.9 subsection as lecture text plus a step-by-step math case.

    定义块逐字搬入讲义（只按现行规则去掉「定义 X.Y / 定理 X.Y」的编号、把名称
    加粗，并把裸露的向量与矩阵统一写成 ``\\boldsymbol``）；案例由定义自定，
    一步一个窗格，各窗格共用同一视角。
    """

    spec = _SUBSPACE_LESSON_SPECS[topic_id]
    claim_refs = [f"claim.{topic_id}"]
    steps = tuple(spec["steps"])
    examples = [
        {
            "id": f"example.{topic_id}.{index}",
            "title": str(step["purpose"]),
            "kind": str(step.get("kind", "matrix_transform")),
            "given": deepcopy(step["given"]),
            "calculation": list(step["lines"]),
            "result": deepcopy(step["result"]),
            "checks": [
                {
                    "name": str(step.get("check", "transformed")),
                    "expected": deepcopy(step["result"]),
                    "tolerance": 1e-9,
                }
            ],
            "claim_refs": claim_refs,
        }
        for index, step in enumerate(steps, start=1)
    ]
    explanation.update(
        {
            "title": str(spec["title"]),
            "summary": str(spec["summary"]),
            "definition": str(spec["definition"]),
            # 讲义把公式与定理写在定义块内，软件不再单列「公式」或「几何意义」分节。
            "formula": "",
            "derivation": [],
            "geometric_meaning": "",
            "worked_examples": examples,
        }
    )
    for key in (
        "intuition", "connections", "transfer_note", "conclusion", "read_guide",
        "analogy_boundary", "invariants", "pitfalls",
    ):
        explanation.pop(key, None)
    explanation["sections"] = [
        {"id": section_id, "title": title, "text": "", "claim_refs": claim_refs}
        for section_id, title in spec["sections"]
    ]
    explanation["symbol_roles"] = dict(spec["symbol_roles"])

    visual["scene_kind"] = "2d"
    visual["entities"] = [
        {
            "id": entity_id, "kind": kind, "dimension": 2, "value": deepcopy(value),
            "role": role, "label": label, "claim_refs": claim_refs,
        }
        for entity_id, kind, value, role, label in spec["entities"]
    ]
    visual["relations"] = [
        {
            "id": relation_id, "kind": kind, "source_ref": source, "target_ref": target,
            "parameters": {}, "claim_refs": claim_refs,
        }
        for relation_id, kind, source, target in spec["relations"]
    ]
    stage_ids = [f"stage.case.{topic_id}.{index}" for index in range(1, len(steps) + 1)]
    visual["stages"] = [
        {
            "id": stage_id,
            "title": str(step["purpose"]),
            "caption": "",
            "layout": "overlay",
            "input_entity_refs": list(step["inputs"]),
            "output_entity_refs": list(step["outputs"]),
            "relation_refs": list(step["relations"]),
            "expected_invariants": [str(step["invariant"])],
        }
        for stage_id, step in zip(stage_ids, steps)
    ]
    explanation["case_layout"] = {
        # 数学案例流程默认“全部显示”：一步一个窗格，各窗格共用同一视角。
        "default_pane_count": len(steps),
        "cases": [
            {
                "id": f"case.{topic_id}.{index}", "topic_id": topic_id,
                "example_ref": examples[index - 1]["id"], "claim_refs": claim_refs,
                "stage_refs": [stage_id], "purpose": str(step["purpose"]),
            }
            for index, (stage_id, step) in enumerate(zip(stage_ids, steps), start=1)
        ],
    }


def _refine_matrix_vector_subsection(
    topic_id: str, explanation: dict[str, Any], visual: dict[str, Any]
) -> None:
    """Publish one 2.5 subsection as lecture text plus a step-by-step math case.

    The definition block carries the lecture wording (only bare symbols are
    wrapped in ``$...$``).  The case is authored from that definition and
    renders one pane per algebraic step, so the same result can be read off
    with two coordinate descriptions.
    """

    spec = _MATRIX_VECTOR_TOPIC_SPECS[topic_id]
    claim_refs = [f"claim.{topic_id}"]
    steps = tuple(spec["steps"])
    examples = [
        {
            "id": f"example.{topic_id}.{index}",
            "title": str(step["purpose"]),
            "kind": "matrix_transform",
            "given": deepcopy(step["given"]),
            "calculation": list(step["lines"]),
            "result": deepcopy(step["result"]),
            "checks": [
                {
                    "name": "transformed",
                    "expected": deepcopy(step["result"]),
                    "tolerance": 1e-9,
                }
            ],
            "claim_refs": claim_refs,
        }
        for index, step in enumerate(steps, start=1)
    ]
    explanation.update(
        {
            "title": str(spec["title"]),
            "summary": str(spec["summary"]),
            "definition": str(spec["definition"]),
            # 讲义把公式写在定义（2.5.1）与例题（2.5.3）里、把定理写在 2.5.2 里，
            # 软件不再单列「公式」分节；claim 仍保留一条机器可读的公式。
            "formula": "",
            "derivation": [],
            "geometric_meaning": "",
            "worked_examples": examples,
        }
    )
    for key in (
        "intuition", "connections", "transfer_note", "conclusion", "read_guide",
        "analogy_boundary", "invariants", "pitfalls",
    ):
        explanation.pop(key, None)
    explanation["sections"] = [
        {"id": section_id, "title": title, "text": "", "claim_refs": claim_refs}
        for section_id, title in spec["sections"]
    ]
    explanation["symbol_roles"] = dict(spec["symbol_roles"])

    visual["scene_kind"] = "2d"
    visual["entities"] = [
        {
            "id": entity_id, "kind": kind, "dimension": 2, "value": deepcopy(value),
            "role": role, "label": label, "claim_refs": claim_refs,
        }
        for entity_id, kind, value, role, label in spec["entities"]
    ]
    visual["relations"] = [
        {
            "id": relation_id, "kind": kind, "source_ref": source, "target_ref": target,
            "parameters": {}, "claim_refs": claim_refs,
        }
        for relation_id, kind, source, target in spec["relations"]
    ]
    stage_ids = [f"stage.case.{topic_id}.{index}" for index in range(1, len(steps) + 1)]
    visual["stages"] = [
        {
            "id": stage_id,
            "title": str(step["purpose"]),
            "caption": "",
            "layout": "overlay",
            "input_entity_refs": list(step["inputs"]),
            "output_entity_refs": list(step["outputs"]),
            "relation_refs": list(step["relations"]),
            "expected_invariants": [str(step["invariant"])],
        }
        for stage_id, step in zip(stage_ids, steps)
    ]
    explanation["case_layout"] = {
        # 数学案例流程默认“全部显示”：一步一个窗格，各窗格共用同一视角。
        "default_pane_count": len(steps),
        "cases": [
            {
                "id": f"case.{topic_id}.{index}", "topic_id": topic_id,
                "example_ref": examples[index - 1]["id"], "claim_refs": claim_refs,
                "stage_refs": [stage_id], "purpose": str(step["purpose"]),
            }
            for index, (stage_id, step) in enumerate(zip(stage_ids, steps), start=1)
        ],
    }


def _refine_batch_inner_products(explanation: dict[str, Any], visual: dict[str, Any]) -> None:
    """Publish 讲义 2.2 批量内积 as the lecture definition plus its worked case.

    讲义 2.2 只有「定义 2.4（行向量与矩阵乘法 — 批量内积）」+ 一句话总结与一组
    分层例题；例题只保留**一个**：u=(2,3)，V 是一个 2×2 矩阵，两列取 (2,1) 与
    (-1,2)（刻意不用标准基 e1、e2）。案例只写成一块、V 只写一次，u 一次乘 V
    就同时得到两个内积分量 u·V=[7,4]。画法沿用 1.3.1 已确认工件（一条 u、虚线
    投影与垂足、夹角弧，以及窗格上的模长标注），把 V 两列的整套图元叠进
    **同一个窗格**（``default_pane_count`` 为 1）。
    """

    topic_id = "ch02.batch.inner-products"
    claim_refs = [f"claim.{topic_id}"]
    u_value = [2.0, 3.0]
    # V 的两列刻意不用标准基 e1、e2：v1=(2,1)、v2=(-1,2)。
    columns = ([2.0, 1.0], [-1.0, 2.0])
    components = [
        u_value[0] * column[0] + u_value[1] * column[1] for column in columns
    ]
    examples = [
        {
            "id": f"example.{topic_id}.batch",
            "title": "u 一次乘 V：两个分量一起算出",
            "kind": "inner_product",
            "given": [list(u_value), list(columns[0])],
            "result": components[0],
            "calculation": [
                r"$$V=\begin{bmatrix}2 & -1\\ 1 & 2\end{bmatrix},\qquad \boldsymbol u=(2,3)$$",
                r"$V$ 的两列是 $\boldsymbol v_1=(2,1)$、$\boldsymbol v_2=(-1,2)$；"
                r"$\boldsymbol u\cdot V$ 就是 $\boldsymbol u$ 分别与这两列作内积：",
                r"$$(\boldsymbol u\cdot V)_1=\boldsymbol u\cdot\boldsymbol v_1=2\times2+3\times1=7,\qquad"
                r"(\boldsymbol u\cdot V)_2=\boldsymbol u\cdot\boldsymbol v_2=2\times(-1)+3\times2=4$$",
                r"把两个内积依次排成一行：$\boldsymbol u\cdot V=[7,\,4]$，"
                r"一次乘法同时算出两个方向上的内积。",
            ],
            "checks": [{"name": "dot", "expected": components[0], "tolerance": 1e-9}],
        }
    ]
    for example in examples:
        example["claim_refs"] = claim_refs
    explanation.update(
        {
            "title": "批量内积",
            "summary": "一次内积算一个角度——那要算一百个角度呢？答案是批量内积。",
            "definition": (
                r"定义 2.4（行向量与矩阵乘法 — 批量内积）设 $\boldsymbol u$ 是一个 $1\times m$ 行向量，"
                r"$V$ 是一个 $m\times n$ 矩阵。定义乘积 $\boldsymbol u\cdot V$ 为一个 $1\times n$ 行向量，"
                r"其第 $j$ 个分量是 $\boldsymbol u$ 与 $V$ 的第 $j$ 列的内积："
                "\n\n"
                r"$$(\boldsymbol u\cdot V)_{j}=u_{1}\cdot v_{1j}+u_{2}\cdot v_{2j}+\cdots+u_{m}\cdot v_{mj}$$"
                "\n\n"
                r"一句话总结：一行乘一矩阵，结果每一列给出一个内积——一次性完成。"
            ),
            # 定义 2.4 自带公式并被前端并入定义块，按讲义位置不再单列「公式」分节；
            # claim 仍保留一条机器可读的简写公式。
            "formula": "",
            "derivation": [],
            "geometric_meaning": "",
            "worked_examples": examples,
        }
    )
    for key in (
        "intuition", "connections", "transfer_note", "conclusion", "read_guide",
        "analogy_boundary", "invariants", "pitfalls",
    ):
        explanation.pop(key, None)
    explanation["sections"] = [
        {"id": "definition", "title": "定义", "text": "", "claim_refs": claim_refs},
        {"id": "worked_examples", "title": "数学案例", "text": "", "claim_refs": claim_refs},
    ]
    explanation["symbol_roles"] = {"u": "vector_a", "v": "vector_b", "V": "matrix_a"}

    entities: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    stage_input_refs: list[str] = []
    stage_output_refs: list[str] = []
    stage_relation_refs: list[str] = []
    # 两列投影叠加在同一窗格，并用不同颜色区分。
    column_roles = ("vector_b", "transformed_a")
    for index, column in enumerate(columns, start=1):
        suffix = str(index)
        u_id, v_id = f"case{suffix}_u", f"case{suffix}_v"
        dot = u_value[0] * column[0] + u_value[1] * column[1]
        denominator = u_value[0] * u_value[0] + u_value[1] * u_value[1]
        scale = dot / denominator
        projected = [scale * u_value[0], scale * u_value[1]]
        entities.extend([
            {
                "id": u_id, "kind": "vector", "dimension": 2, "value": list(u_value),
                "role": "vector_a", "label": "u", "claim_refs": claim_refs,
            },
            {
                "id": v_id, "kind": "vector", "dimension": 2, "value": list(column),
                "role": column_roles[index - 1], "label": f"v{index}", "claim_refs": claim_refs,
            },
        ])
        angle_id = f"rel.angle.{topic_id}.{suffix}"
        relations.append({
            "id": angle_id, "kind": "orientation", "source_ref": u_id, "target_ref": v_id,
            "parameters": {}, "claim_refs": claim_refs,
        })
        p_id, h_id = f"case{suffix}_p", f"case{suffix}_H"
        entities.extend([
            {
                "id": p_id, "kind": "vector", "dimension": 2, "value": projected,
                "role": "projection", "label": f"p{index}", "claim_refs": claim_refs,
            },
            {
                "id": h_id, "kind": "point", "dimension": 2, "value": projected,
                "role": "foot", "label": f"H{index}", "claim_refs": claim_refs,
            },
        ])
        project_id = f"rel.case.{topic_id}.{suffix}"
        relations.append({
            "id": project_id, "kind": "projects_to", "source_ref": v_id, "target_ref": u_id,
            "parameters": {}, "style": "dashed", "claim_refs": claim_refs,
        })
        stage_relation_refs.extend([project_id, angle_id])
        stage_input_refs.extend([u_id, v_id, p_id])
        stage_output_refs.append(h_id)

    # 两列共用一个阶段并叠加渲染。
    stage_id = f"stage.case.{topic_id}.1"
    stages = [
        {
            "id": stage_id, "title": "一步：u 与 V 的两列", "caption": (
                r"$\boldsymbol u=(2,3)$ 与矩阵 $V$ 的两列 $\boldsymbol v_1=(2,1)$、"
                r"$\boldsymbol v_2=(-1,2)$ 从同一原点出发，夹角分别为 $\theta_1,\theta_2$；"
                r"把两列分别投影到 $\boldsymbol u$ 上（虚线），垂足为 $H_1,H_2$，"
                r"用 $\lvert\boldsymbol u\rvert=\sqrt{13}$ 乘各自的投影长度即得 "
                r"$\boldsymbol u\cdot V=[7,4]$。"
            ),
            "layout": "overlay",
            "input_entity_refs": stage_input_refs,
            "output_entity_refs": stage_output_refs,
            "relation_refs": stage_relation_refs,
            "expected_invariants": ["u·V=[7,4]：一次乘法同时得到两个内积分量"],
        }
    ]
    cases = [
        {
            "id": f"case.{topic_id}.1", "topic_id": topic_id,
            "example_ref": str(examples[0]["id"]), "claim_refs": claim_refs,
            "stage_refs": [stage_id], "purpose": "一个窗格：u 与 V 的两列 v1、v2",
        }
    ]

    visual.update({
        "scene_kind": "2d",
        "entities": entities,
        "relations": relations,
        "stages": stages,
    })
    explanation["case_layout"] = {
        # 批量内积在一个窗格中同时显示两列。
        "default_pane_count": 1,
        "cases": cases,
    }


def _refine_batch_projection(explanation: dict[str, Any], visual: dict[str, Any]) -> None:
    """Publish 讲义 2.3 and the user-confirmed single batch-projection case.

    定义块完整保留讲义的动机、定义、公式与 x 轴说明；公式不另拆分节。
    讲义没有数值案例，因此使用用户确认的三个向量，在一个窗格中同时投影到
    x 轴。每个输入向量、它的投影和垂直辅助线共用同一种对象颜色。
    """

    topic_id = "ch02.batch.projection"
    claim_refs = [f"claim.{topic_id}"]
    vectors = ([3.0, 2.0], [-2.0, 3.0], [1.0, -3.0])
    projections = ([3.0, 0.0], [-2.0, 0.0], [1.0, 0.0])
    example_id = f"example.{topic_id}.batch"
    examples = [
        {
            "id": example_id,
            "title": "案例一：三个向量投影到横轴",
            "kind": "batch_projection",
            "given": [
                [list(vector) for vector in vectors],
                [1.0, 0.0],
            ],
            "result": [list(projection) for projection in projections],
            "calculation": [
                (
                    r"$$\boldsymbol u=(1,0),\qquad "
                    r"\boldsymbol P=\boldsymbol u\boldsymbol u^{\mathsf T}="
                    r"\begin{pmatrix}1 & 0\\0 & 0\end{pmatrix}$$"
                ),
                "取三个向量：",
                (
                    r"$$\boldsymbol v_1=(3,2),\qquad "
                    r"\boldsymbol v_2=(-2,3),\qquad "
                    r"\boldsymbol v_3=(1,-3)$$"
                ),
                (
                    r"$$\boldsymbol P\boldsymbol v_1=(3,0),\qquad "
                    r"\boldsymbol P\boldsymbol v_2=(-2,0),\qquad "
                    r"\boldsymbol P\boldsymbol v_3=(1,0)$$"
                ),
            ],
            "checks": [
                {
                    "name": "projections",
                    "expected": [list(projection) for projection in projections],
                    "tolerance": 1e-9,
                }
            ],
            "claim_refs": claim_refs,
        }
    ]
    explanation.update(
        {
            "title": "投影矩阵",
            "summary": "投影也能批处理——矩阵乘法的雏形已经萌芽。",
            "definition": (
                r"**（投影矩阵）** 设 $\boldsymbol u$ 是单位向量"
                r"（$\lvert\boldsymbol u\rvert=1$）。矩阵 "
                r"$\boldsymbol P=\boldsymbol u\boldsymbol u^{\mathsf T}$ 称为沿 "
                r"$\boldsymbol u$ 方向的投影矩阵。对任意 $\boldsymbol v$："
                "\n\n"
                r"$$\boldsymbol P\boldsymbol v=(\boldsymbol u\cdot\boldsymbol v)"
                r"\boldsymbol u=\operatorname{Proj}_{\boldsymbol u}(\boldsymbol v)$$"
                "\n\n"
                r"即用投影矩阵乘 $\boldsymbol v$，一步得到投影结果。"
                "\n\n"
                r"例如：投影到 $x$ 轴的投影矩阵 "
                r"$=\begin{pmatrix}1 & 0\\0 & 0\end{pmatrix}$——乘任何向量，"
                r"$y$ 分量归零，只保留 $x$ 分量。"
            ),
            # 定义 2.5 自带公式，不再单列「公式」分节。
            "formula": "",
            "derivation": [],
            "geometric_meaning": "",
            "worked_examples": examples,
        }
    )
    for key in (
        "intuition", "connections", "transfer_note", "conclusion", "read_guide",
        "analogy_boundary", "invariants", "pitfalls",
    ):
        explanation.pop(key, None)
    explanation["sections"] = [
        {"id": "definition", "title": "定义", "text": "", "claim_refs": claim_refs},
        {"id": "worked_examples", "title": "数学案例", "text": "", "claim_refs": claim_refs},
    ]
    explanation["symbol_roles"] = {
        "P": "matrix_a",
        "u": "direction",
        "v": "vector_a",
        "v_1": "vector_a",
        "v_2": "vector_b",
        "v_3": "transformed_a",
    }

    roles = ("vector_a", "vector_b", "transformed_a")
    entities: list[dict[str, Any]] = [
        {
            "id": "u", "kind": "vector", "dimension": 2, "value": [1.0, 0.0],
            "role": "direction", "label": "u", "claim_refs": claim_refs,
        }
    ]
    relations: list[dict[str, Any]] = []
    vector_refs: list[str] = []
    projection_refs: list[str] = []
    relation_refs: list[str] = []
    for index, (vector, projection, role) in enumerate(
        zip(vectors, projections, roles), start=1
    ):
        vector_id = f"batch{index}_v"
        projection_id = f"batch{index}_p"
        relation_id = f"rel.batch-projection.{index}"
        entities.extend(
            [
                {
                    "id": vector_id, "kind": "vector", "dimension": 2,
                    "value": list(vector), "role": role, "label": f"v{index}",
                    "claim_refs": claim_refs,
                },
                {
                    "id": projection_id, "kind": "vector", "dimension": 2,
                    "value": list(projection), "role": "projection", "label": f"p{index}",
                    "claim_refs": claim_refs,
                },
            ]
        )
        relations.append(
            {
                "id": relation_id, "kind": "projects_to", "source_ref": vector_id,
                "target_ref": "u", "parameters": {}, "style": "dashed",
                "claim_refs": claim_refs,
            }
        )
        vector_refs.append(vector_id)
        projection_refs.append(projection_id)
        relation_refs.append(relation_id)

    stage_id = f"stage.case.{topic_id}.1"
    visual.update(
        {
            "scene_kind": "2d",
            "entities": entities,
            "relations": relations,
            "stages": [
                {
                    "id": stage_id,
                    "title": "三个向量同时投影到横轴",
                    "caption": "",
                    "layout": "overlay",
                    # x 轴本身就是目标方向，不再叠画与 p3 重合的单位向量 u。
                    "input_entity_refs": vector_refs,
                    "output_entity_refs": projection_refs,
                    "relation_refs": relation_refs,
                    "expected_invariants": ["三个输出的纵向分量都为 0"],
                }
            ],
        }
    )
    explanation["case_layout"] = {
        "default_pane_count": 1,
        "cases": [
            {
                "id": f"case.{topic_id}.1",
                "topic_id": topic_id,
                "example_ref": example_id,
                "claim_refs": claim_refs,
                "stage_refs": [stage_id],
                "purpose": "案例一：三个向量投影到横轴",
            }
        ],
    }


def _refine_remaining_chapter_one(topic_id: str, explanation: dict[str, Any], visual: dict[str, Any]) -> None:
    """Apply lecture-specific, compact structures to the remaining Chapter 1 topics."""

    claim_refs = [f"claim.{topic_id}"]
    definitions: dict[str, tuple[str, str, str, str]] = {
        "ch01.inner.definitions": (
            "1.3.1 内积的两种定义", "内积既可由夹角定义，也可按坐标分量计算。",
            r"设 $\boldsymbol a,\boldsymbol b$ 为非零向量，夹角为 $\theta$；在二维坐标中写作 $\boldsymbol a=(a_1,a_2)$、$\boldsymbol b=(b_1,b_2)$。",
            r"\boldsymbol a\cdot\boldsymbol b=\lvert\boldsymbol a\rvert\,\lvert\boldsymbol b\rvert\cos\theta=a_1b_1+a_2b_2",
        ),
        "ch01.inner.cauchy-schwarz": (
            "柯西—施瓦茨不等式", "内积的绝对值不超过两个向量长度的乘积。",
            r"对任意向量 $\boldsymbol a,\boldsymbol b$，内积的绝对值有一个由长度给出的上界。",
            r"\lvert\boldsymbol a\cdot\boldsymbol b\rvert\leq\lvert\boldsymbol a\rvert\,\lvert\boldsymbol b\rvert",
        ),
        "ch01.projection.definition": (
            "投影的定义", "正交投影沿目标方向，残差与目标方向正交。",
            r"设 $\boldsymbol u\neq\boldsymbol0$。$\boldsymbol v$ 在 $\boldsymbol u$ 所在直线上的投影记为 $\operatorname{proj}_{\boldsymbol u}\boldsymbol v$，并满足 $\boldsymbol v-\operatorname{proj}_{\boldsymbol u}\boldsymbol v\perp\boldsymbol u$。",
            r"\operatorname{proj}_{\boldsymbol u}\boldsymbol v=\frac{\boldsymbol v\cdot\boldsymbol u}{\boldsymbol u\cdot\boldsymbol u}\boldsymbol u,\qquad \boldsymbol v=\boldsymbol p+\boldsymbol r",
        ),
        "ch01.proof.midline": (
            "三角形中位线定理", "两边中点连线平行于第三边，长度为第三边的一半。",
            r"取 $A$ 为原点，设 $\overrightarrow{AB}=\boldsymbol a$、$\overrightarrow{AC}=\boldsymbol b$；$D,E$ 分别为 $AB,AC$ 的中点。",
            r"\overrightarrow{DE}=\frac12(\boldsymbol b-\boldsymbol a)=\frac12\overrightarrow{BC}",
        ),
        "ch01.proof.centroid": (
            "三角形重心定理", "三条中线交于一点，重心位置向量是三个顶点位置向量的平均。",
            r"取 $A$ 为原点，设 $\overrightarrow{AB}=\boldsymbol a$、$\overrightarrow{AC}=\boldsymbol b$。",
            r"\overrightarrow{AG}=\frac13(\boldsymbol a+\boldsymbol b)",
        ),
        "ch01.proof.parallelogram-diagonals": (
            "平行四边形对角线互相平分", "两条对角线的中点位置向量相同。",
            r"取 $A$ 为原点，设 $\overrightarrow{AB}=\boldsymbol a$、$\overrightarrow{AD}=\boldsymbol b$，则 $\overrightarrow{AC}=\boldsymbol a+\boldsymbol b$。",
            r"\frac{\boldsymbol a+\boldsymbol b}{2}=\frac{\boldsymbol a+(\boldsymbol a+\boldsymbol b-\boldsymbol a)}{2}",
        ),
    }
    title, summary, definition, formula = definitions[topic_id]
    if topic_id == "ch01.inner.definitions":
        definition = (
            r"**（内积 / 点积 — 几何定义）** 设 $\boldsymbol a,\boldsymbol b$ 为两个向量，"
            r"其夹角为 $\theta$（$0\leq\theta\leq\pi$），则："
            "\n\n"
            r"$$\boldsymbol a\cdot\boldsymbol b=\lvert\boldsymbol a\rvert\cdot\lvert\boldsymbol b\rvert\cdot\cos(\theta)$$"
            "\n\n"
            r"**（内积 — 代数计算）** 在 $\mathbb R^2$ 中，设 "
            r"$\boldsymbol a=(a_1,a_2)$，$\boldsymbol b=(b_1,b_2)$，则："
            "\n\n"
            r"$$\boldsymbol a\cdot\boldsymbol b=a_1\cdot b_1+a_2\cdot b_2$$"
            "\n\n"
            r"两个定义是等价的（由余弦定理可证）。"
            "\n\n"
            r"直观理解：内积本质上是“$\boldsymbol a$ 的长度 $\times$ $\boldsymbol b$ 在 $\boldsymbol a$ 方向上的投影长度”。"
            r"当两向量同向时，$\cos\theta=1$，内积取最大值 $=\lvert\boldsymbol a\rvert\cdot\lvert\boldsymbol b\rvert$；"
            r"垂直时 $\cos\theta=0$，内积为 $0$；反向时 $\cos\theta=-1$，内积取最小值。"
        )
        # 讲义 1.3.1 的公式直接写在定义块内，不再另立「公式」分节。
        formula = ""
    if topic_id == "ch01.projection.definition":
        # 1.4.1 的定义、定理和公式含义合并在定义块中。
        definition = (
            r"定义 1.13（投影向量）设 $\boldsymbol u$ 是一个非零向量。向量 $\boldsymbol v$ 在 "
            r"$\boldsymbol u$ 所在直线上的正交投影（简称投影）为一个沿 $\boldsymbol u$ 方向的向量，"
            r"记为 $\operatorname{Proj}_{\boldsymbol u}(\boldsymbol v)$，满足："
            "\n\n"
            r"$$\boldsymbol v-\operatorname{Proj}_{\boldsymbol u}(\boldsymbol v)\ \text{与}\ \boldsymbol u\ \text{正交}$$"
            "\n\n"
            r"即“从 $\boldsymbol v$ 的终点向 $\boldsymbol u$ 所在直线作垂线，垂足对应的向量”。"
            "\n\n"
            r"定理 1.6（投影公式）"
            "\n\n"
            r"$$\operatorname{Proj}_{\boldsymbol u}(\boldsymbol v)"
            r"=\left[\frac{\boldsymbol v\cdot\boldsymbol u}{\boldsymbol u\cdot\boldsymbol u}\right]\times\boldsymbol u"
            r"=\left[(\boldsymbol v\cdot\boldsymbol u)/\lvert\boldsymbol u\rvert^{2}\right]\times\boldsymbol u$$"
            "\n\n"
            r"当 $\boldsymbol u$ 为单位向量（$\lvert\boldsymbol u\rvert=1$）时，公式简化为："
            "\n\n"
            r"$$\operatorname{Proj}_{\boldsymbol u}(\boldsymbol v)=(\boldsymbol v\cdot\boldsymbol u)\times\boldsymbol u$$"
            "\n\n"
            r"公式的含义：系数 $\frac{\boldsymbol v\cdot\boldsymbol u}{\boldsymbol u\cdot\boldsymbol u}$ 计算的是"
            r"“$\boldsymbol v$ 在 $\boldsymbol u$ 上的影子长度是 $\boldsymbol u$ 的多少倍”；"
            r"乘以 $\boldsymbol u$ 是赋予它 $\boldsymbol u$ 的方向。"
        )
        formula = ""
    derivations: dict[str, list[str]] = {
        # 讲义「##### 定理 1.6（投影公式）的推导」原文（含末尾的「直观」一句）。
        "ch01.projection.definition": [
            r"由定义 1.13：$\boldsymbol v-\operatorname{Proj}_{\boldsymbol u}(\boldsymbol v)$ 与 $\boldsymbol u$ 正交，即 $(\boldsymbol v-\operatorname{Proj}_{\boldsymbol u}(\boldsymbol v))\cdot\boldsymbol u=0$。",
            r"设 $\operatorname{Proj}_{\boldsymbol u}(\boldsymbol v)=\alpha\cdot\boldsymbol u$（投影必然沿 $\boldsymbol u$ 的方向，$\alpha$ 是待定系数）。",
            r"代入：$(\boldsymbol v-\alpha\boldsymbol u)\cdot\boldsymbol u=0\rightarrow\boldsymbol v\cdot\boldsymbol u-\alpha(\boldsymbol u\cdot\boldsymbol u)=0\rightarrow\alpha=\frac{\boldsymbol v\cdot\boldsymbol u}{\boldsymbol u\cdot\boldsymbol u}$。",
            r"因此 $\operatorname{Proj}_{\boldsymbol u}(\boldsymbol v)=\left[\frac{\boldsymbol v\cdot\boldsymbol u}{\boldsymbol u\cdot\boldsymbol u}\right]\cdot\boldsymbol u$。",
            r"直观: 系数 $\alpha$ 是「$\boldsymbol v$ 在 $\boldsymbol u$ 方向上的影子长度是 $\boldsymbol u$ 的多少倍」。当 $\lvert\boldsymbol u\rvert=1$ 时，$\alpha=\boldsymbol v\cdot\boldsymbol u$。",
        ],
        "ch01.inner.cauchy-schwarz": [r"对任意实数 $t$，有 $\lvert\boldsymbol a-t\boldsymbol b\rvert^2\geq0$。", r"展开为 $\lvert\boldsymbol b\rvert^2t^2-2(\boldsymbol a\cdot\boldsymbol b)t+\lvert\boldsymbol a\rvert^2$，其判别式不大于零，故 $(\boldsymbol a\cdot\boldsymbol b)^2\leq\lvert\boldsymbol a\rvert^2\lvert\boldsymbol b\rvert^2$。"],
        "ch01.proof.midline": [r"$\overrightarrow{AD}=\frac12\boldsymbol a$、$\overrightarrow{AE}=\frac12\boldsymbol b$，所以 $\overrightarrow{DE}=\overrightarrow{AE}-\overrightarrow{AD}$。"],
        "ch01.proof.centroid": [r"边 $BC$ 的中点位置向量为 $\frac12(\boldsymbol a+\boldsymbol b)$；取中线上的二比一分点，得到 $\overrightarrow{AG}=\frac13(\boldsymbol a+\boldsymbol b)$。"],
        "ch01.proof.parallelogram-diagonals": [r"对角线 $AC$ 的中点为 $\frac12(\boldsymbol a+\boldsymbol b)$；对角线 $BD$ 的中点也化为同一向量。"],
    }
    examples_map: dict[str, list[dict[str, Any]]] = {
        "ch01.inner.definitions": [{"id": "example.inner.definition", "title": "案例一：同屏用两种定义求同一个内积", "kind": "inner_product", "given": [[2, 0], [1, 1]], "result": 2.0, "calculation": [r"$$\boldsymbol a=(2,0),\qquad \boldsymbol b=(1,1),\qquad \lvert\boldsymbol a\rvert=2,\qquad \lvert\boldsymbol b\rvert=\sqrt2,\qquad \theta=45^\circ$$", "几何定义：用两向量的长度和夹角计算。", r"$$\boldsymbol a\cdot\boldsymbol b=\lvert\boldsymbol a\rvert\,\lvert\boldsymbol b\rvert\cos\theta=2\times\sqrt2\times\frac{\sqrt2}{2}=2$$", "代数定义：用坐标分量分别相乘再相加。", r"$$\boldsymbol a\cdot\boldsymbol b=a_1b_1+a_2b_2=2\times1+0\times1=2$$", r"两种定义得到同一个值 $2$；图中 $\boldsymbol b$ 在 $\boldsymbol a$ 上的投影为 $\operatorname{proj}_{\boldsymbol a}\boldsymbol b=(1,0)$，投影长度 $\lvert\boldsymbol b\rvert\cos\theta=1$。"], "checks": [{"name": "dot", "expected": 2.0, "tolerance": 1e-9}]}],
        "ch01.inner.cauchy-schwarz": [{"id": "example.cauchy.bound", "title": "案例一：投影界", "kind": "inner_product", "given": [[3, 4], [1, 0]], "result": 3.0, "calculation": [r"$$\lvert\boldsymbol a\cdot\boldsymbol b\rvert=3\leq5=\lvert\boldsymbol a\rvert\,\lvert\boldsymbol b\rvert$$"], "checks": [{"name": "dot", "expected": 3.0, "tolerance": 1e-9}]}],
        # 以 u=(2,1)、v=(3,4) 构造投影、垂足和正交残差三步案例。
        "ch01.projection.definition": [
            {
                "id": "example.projection.definition.1",
                "title": "第一步：给出方向 u 与向量 v",
                "kind": "projection",
                "given": [[3, 4], [2, 1]],
                "result": [4.0, 2.0],
                "calculation": [
                    r"$$\boldsymbol u=(2,1),\qquad \boldsymbol v=(3,4)$$",
                    r"$\boldsymbol u$ 是一条斜直线，不是坐标轴；目标是求 $\boldsymbol v$ 在 $\boldsymbol u$ 所在直线上的投影。",
                ],
                "checks": [{"name": "projection", "expected": [4.0, 2.0], "tolerance": 1e-9}],
            },
            {
                "id": "example.projection.definition.2",
                "title": "第二步：作垂线，得投影 p 与垂足 H",
                "kind": "projection",
                "given": [[3, 4], [2, 1]],
                "result": [4.0, 2.0],
                "calculation": [
                    r"$$\operatorname{Proj}_{\boldsymbol u}\boldsymbol v=\left[\frac{\boldsymbol v\cdot\boldsymbol u}{\boldsymbol u\cdot\boldsymbol u}\right]\boldsymbol u=\frac{3\times2+4\times1}{2\times2+1\times1}(2,1)=\frac{10}{5}(2,1)=(4,2)$$",
                    r"从 $\boldsymbol v$ 的终点向 $\boldsymbol u$ 所在直线作垂线，垂足 $H$ 对应的向量就是 $\boldsymbol p=(4,2)$。",
                ],
                "checks": [{"name": "projection", "expected": [4.0, 2.0], "tolerance": 1e-9}],
            },
            {
                "id": "example.projection.definition.3",
                "title": "第三步：残差 r 与 u 正交",
                "kind": "projection",
                "given": [[3, 4], [2, 1]],
                "result": [4.0, 2.0],
                "calculation": [
                    r"$$\boldsymbol r=\boldsymbol v-\boldsymbol p=(3,4)-(4,2)=(-1,2)$$",
                    r"$$\boldsymbol r\cdot\boldsymbol u=(-1)\times2+2\times1=0\Longrightarrow\boldsymbol r\perp\boldsymbol u,\qquad \boldsymbol v=\boldsymbol p+\boldsymbol r=(4,2)+(-1,2)$$",
                ],
                "checks": [{"name": "projection", "expected": [4.0, 2.0], "tolerance": 1e-9}],
            },
        ],
        "ch01.proof.midline": [{"id": "example.proof.midline", "title": "案例一：中位线", "kind": "vector_addition", "given": [[2, 0], [0, 2]], "result": [2.0, 2.0], "calculation": [r"$$\overrightarrow{DE}=\frac12(\boldsymbol b-\boldsymbol a)=\frac12\overrightarrow{BC}$$"], "checks": [{"name": "sum", "expected": [2.0, 2.0], "tolerance": 1e-9}]}],
        "ch01.proof.centroid": [{"id": "example.proof.centroid", "title": "案例一：三角形重心", "kind": "vector_addition", "given": [[1, 0], [0, 1]], "result": [1.0, 1.0], "calculation": [r"$$\overrightarrow{AG}=\frac13(\boldsymbol a+\boldsymbol b)$$"], "checks": [{"name": "sum", "expected": [1.0, 1.0], "tolerance": 1e-9}]}],
        "ch01.proof.parallelogram-diagonals": [{"id": "example.proof.parallelogram", "title": "案例一：对角线中点", "kind": "vector_addition", "given": [[2, 1], [1, 3]], "result": [3.0, 4.0], "calculation": [r"$$M_{AC}=M_{BD}=\frac12(\boldsymbol a+\boldsymbol b)$$"], "checks": [{"name": "sum", "expected": [3.0, 4.0], "tolerance": 1e-9}]}],
    }
    examples = examples_map[topic_id]
    if topic_id == "ch01.inner.definitions":
        # 以同一组向量并排比较内积的几何定义与代数定义。
        examples = [
            {
                "id": "example.inner.definition.geometric",
                "title": "第一步：几何定义",
                "kind": "inner_product",
                "given": [[2, 1], [1, 2]],
                "result": 4.0,
                "calculation": [
                    r"$$\boldsymbol a=(2,1),\qquad \boldsymbol b=(1,2)$$",
                    r"$$\lvert\boldsymbol a\rvert=\sqrt{2^2+1^2}=\sqrt5,\qquad \lvert\boldsymbol b\rvert=\sqrt{1^2+2^2}=\sqrt5,\qquad \cos\theta=\frac45$$",
                    r"$$\boldsymbol a\cdot\boldsymbol b=\lvert\boldsymbol a\rvert\,\lvert\boldsymbol b\rvert\cos\theta=\sqrt5\times\sqrt5\times\frac45=4$$",
                    r"图中 $\boldsymbol b$ 在 $\boldsymbol a$ 上的投影向量为 $\boldsymbol p=(1.6,0.8)$，投影长度 $\lvert\boldsymbol b\rvert\cos\theta=\dfrac4{\sqrt5}$；用 $\lvert\boldsymbol a\rvert=\sqrt5$ 乘投影长度即得 $4$。",
                ],
                "checks": [{"name": "dot", "expected": 4.0, "tolerance": 1e-9}],
            },
            {
                "id": "example.inner.definition.algebraic",
                "title": "第二步：代数定义",
                "kind": "inner_product",
                "given": [[2, 1], [1, 2]],
                "result": 4.0,
                "calculation": [
                    r"$$\boldsymbol a=(2,1),\qquad \boldsymbol b=(1,2)$$",
                    r"$$\boldsymbol a\cdot\boldsymbol b=a_1b_1+a_2b_2=2\times1+1\times2=4$$",
                    r"两种定义得到同一个数 $4$，所以几何定义与代数定义等价。",
                ],
                "checks": [{"name": "dot", "expected": 4.0, "tolerance": 1e-9}],
            },
        ]
    for example in examples:
        example["claim_refs"] = claim_refs
    geometry_map = {
        # 1.3.1 的「直观理解」按讲义位置并入「定义」分节，此处不再单列几何意义。
        "ch01.inner.definitions": "",
        "ch01.inner.cauchy-schwarz": r"内积的绝对值不超过长度乘积，几何上表示带符号投影的绝对值不超过被投影向量的长度；案例一给出严格不等式。",
        # 1.4.1 的「从 v 的终点向 u 所在直线作垂线，垂足对应的向量」按讲义位置
        # 并入「定义」分节，此处不再单列几何意义。
        "ch01.projection.definition": "",
        "ch01.proof.midline": r"中位线向量是第三边向量的一半，因此与第三边平行且长度减半；案例一对应 $\overrightarrow{DE}=\frac12\overrightarrow{BC}$。",
        "ch01.proof.centroid": r"重心位于从顶点到对边中点的中线上，位置向量由三个顶点的平均关系确定；案例一给出该平均式。",
        "ch01.proof.parallelogram-diagonals": r"两条对角线的中点具有相同的位置向量，因而对角线互相平分；案例一写出这两个中点的共同表达式。",
    }
    _set_case_explanation(explanation, title=title, summary=summary, definition=definition, formula=formula,
                          geometry=geometry_map[topic_id],
                          examples=examples, claim_refs=claim_refs)
    if topic_id == "ch01.inner.definitions":
        explanation["invariants"] = [
            (
                r"**（交换律 / 对称性）**：对任意向量 $\boldsymbol a,\boldsymbol b$，"
                "\n\n"
                r"$$\boldsymbol a\cdot\boldsymbol b=\boldsymbol b\cdot\boldsymbol a$$"
                "\n\n"
                r"证明：按坐标展开 $\boldsymbol a\cdot\boldsymbol b=a_1b_1+a_2b_2$，两个分量只交换相乘顺序，"
                r"所以 $a_1b_1+a_2b_2=b_1a_1+b_2a_2=\boldsymbol b\cdot\boldsymbol a$。"
            ),
            (
                r"**（分配律 / 双线性1）**：对任意向量 $\boldsymbol a,\boldsymbol b,\boldsymbol c$，"
                "\n\n"
                r"$$\boldsymbol a\cdot(\boldsymbol b+\boldsymbol c)=\boldsymbol a\cdot\boldsymbol b+\boldsymbol a\cdot\boldsymbol c$$"
                "\n\n"
                r"证明：$\boldsymbol a\cdot(\boldsymbol b+\boldsymbol c)=a_1(b_1+c_1)+a_2(b_2+c_2)"
                r"=(a_1b_1+a_2b_2)+(a_1c_1+a_2c_2)=\boldsymbol a\cdot\boldsymbol b+\boldsymbol a\cdot\boldsymbol c$。"
            ),
            (
                r"**（数乘结合律 / 双线性2）**：对任意实数 $k$ 与向量 $\boldsymbol a,\boldsymbol b$，"
                "\n\n"
                r"$$(k\boldsymbol a)\cdot\boldsymbol b=k\,(\boldsymbol a\cdot\boldsymbol b)=\boldsymbol a\cdot(k\boldsymbol b)$$"
                "\n\n"
                r"证明：$(k\boldsymbol a)\cdot\boldsymbol b=(ka_1)b_1+(ka_2)b_2=k(a_1b_1+a_2b_2)=k\,(\boldsymbol a\cdot\boldsymbol b)$。"
            ),
            (
                r"**（正定性）**：对任意向量 $\boldsymbol a$，"
                "\n\n"
                r"$$\boldsymbol a\cdot\boldsymbol a\geq0,\qquad \boldsymbol a\cdot\boldsymbol a=0\Longleftrightarrow\boldsymbol a=\boldsymbol0$$"
                "\n\n"
                r"以上四条性质合称「内积是正定对称双线性型」。它们是所有内积空间（不限于 $\mathbb R^2$）的公理基础。"
            ),
            (
                "角度与内积的对应关系：\n\n"
                "| $\\theta$ | $\\cos\\theta$ | $\\boldsymbol a\\cdot\\boldsymbol b$ | 几何含义 |\n"
                "| --- | --- | --- | --- |\n"
                "| $0^\\circ$ | $1$ | $\\lvert\\boldsymbol a\\rvert\\,\\lvert\\boldsymbol b\\rvert$（最大） | 完全同向——“最像” |\n"
                "| $90^\\circ$ | $0$ | $0$ | 正交——“完全不像” |\n"
                "| $180^\\circ$ | $-1$ | $-\\lvert\\boldsymbol a\\rvert\\,\\lvert\\boldsymbol b\\rvert$（最小） | 完全反向 |"
            ),
        ]
        # 1.3.1 仅保留讲义中的"定义"和"内积的基本性质"。
        explanation["sections"] = [
            {"id": "definition", "title": "定义", "text": "", "claim_refs": claim_refs},
            {"id": "worked_examples", "title": "数学案例", "text": "", "claim_refs": claim_refs},
            {"id": "invariants", "title": "内积的基本性质", "text": "", "claim_refs": claim_refs},
        ]
    explanation["derivation"] = derivations.get(topic_id, [])
    if explanation["derivation"]:
        explanation["sections"].insert(2, {"id": "derivation", "title": "derivation", "text": "", "claim_refs": claim_refs})
    if topic_id == "ch01.projection.definition":
        # 1.4.1 仅保留讲义中的定义和投影公式推导。
        explanation["sections"] = [
            {"id": "definition", "title": "定义", "text": "", "claim_refs": claim_refs},
            {"id": "derivation", "title": "定理 1.6（投影公式）的推导", "text": "", "claim_refs": claim_refs},
            {"id": "worked_examples", "title": "数学案例", "text": "", "claim_refs": claim_refs},
        ]
    explanation["symbol_roles"] = {"a": "vector_a", "b": "vector_b", "c": "vector_b", "v": "vector_a", "u": "direction", "p": "projection", "r": "residual", "k": "scalar"}

    visual["scene_kind"] = "2d"
    entities: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    stages: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []
    for index, example in enumerate(examples, start=1):
        suffix = str(index)
        given = example["given"]
        kind = str(example["kind"])
        stage_id = f"stage.case.{topic_id}.{suffix}"
        case_id = f"case.{topic_id}.{suffix}"
        if kind == "projection":
            vector, direction, result = list(given[0]), list(given[1]), list(example["result"])
            ids = [f"case{suffix}_v", f"case{suffix}_u", f"case{suffix}_p", f"case{suffix}_H", f"case{suffix}_r"]
            entities.extend([
                {"id": ids[0], "kind": "vector", "dimension": 2, "value": vector, "role": "vector_a", "label": "v", "claim_refs": claim_refs},
                {"id": ids[1], "kind": "vector", "dimension": 2, "value": direction, "role": "direction", "label": "u", "claim_refs": claim_refs},
                {"id": ids[2], "kind": "vector", "dimension": 2, "value": result, "role": "projection", "label": "p", "claim_refs": claim_refs},
                {"id": ids[3], "kind": "point", "dimension": 2, "value": result, "role": "foot", "label": "H", "claim_refs": claim_refs},
                {"id": ids[4], "kind": "vector", "dimension": 2, "value": [vector[0]-result[0], vector[1]-result[1]], "role": "residual", "label": "r", "claim_refs": claim_refs},
            ])
            rid = f"rel.case.{topic_id}.{suffix}"
            relations.extend([{"id": rid, "kind": "projects_to", "source_ref": ids[0], "target_ref": ids[1], "parameters": {}, "claim_refs": claim_refs}, {"id": f"{rid}.decompose", "kind": "decomposes_into", "source_ref": ids[0], "target_ref": ids[2], "parameters": {}, "claim_refs": claim_refs}, {"id": f"{rid}.orthogonal", "kind": "orthogonal_to", "source_ref": ids[4], "target_ref": ids[1], "parameters": {}, "claim_refs": claim_refs}])
            stage_refs = [item["id"] for item in relations if str(item["id"]).startswith(rid)]
            input_refs, output_refs = ids[:2] + [ids[2], ids[4]], [ids[3]]
        elif topic_id == "ch01.inner.definitions":
            # 投影长度乘以 |a| 应与坐标分量求和一致。
            a_value, b_value = list(given[0]), list(given[1])
            denominator = a_value[0] * a_value[0] + a_value[1] * a_value[1]
            scale = (a_value[0] * b_value[0] + a_value[1] * b_value[1]) / denominator
            projected = [scale * a_value[0], scale * a_value[1]]
            ids = [f"case{suffix}_a", f"case{suffix}_b", f"case{suffix}_p", f"case{suffix}_H"]
            entities.extend([
                {"id": ids[0], "kind": "vector", "dimension": 2, "value": a_value, "role": "vector_a", "label": "a", "claim_refs": claim_refs},
                {"id": ids[1], "kind": "vector", "dimension": 2, "value": b_value, "role": "vector_b", "label": "b", "claim_refs": claim_refs},
                {"id": ids[2], "kind": "vector", "dimension": 2, "value": projected, "role": "projection", "label": "p", "claim_refs": claim_refs},
                {"id": ids[3], "kind": "point", "dimension": 2, "value": projected, "role": "foot", "label": "H", "claim_refs": claim_refs},
            ])
            rid = f"rel.case.{topic_id}.{suffix}"
            # 夹角弧需使用独立关系名，避免仅登记别名而不绘制。
            angle_rid = f"rel.angle.{topic_id}.{suffix}"
            relations.extend([
                # 投影辅助线使用虚线。
                {"id": rid, "kind": "projects_to", "source_ref": ids[1], "target_ref": ids[0], "parameters": {}, "style": "dashed", "claim_refs": claim_refs},
                {"id": angle_rid, "kind": "orientation", "source_ref": ids[0], "target_ref": ids[1], "parameters": {}, "claim_refs": claim_refs},
            ])
            stage_refs = [rid, angle_rid]
            input_refs, output_refs = [ids[0], ids[1], ids[2]], [ids[3]]
        else:
            dimension = len(given[0]) if isinstance(given[0], list) else 2
            vals = list(given) if isinstance(given, list) and all(isinstance(x, list) for x in given) else [[1, 0], [0, 1]]
            ids = [f"case{suffix}_{letter}" for letter in "ab"]
            for ent_id, value, label, role in zip(ids, vals[:2], ("a", "b"), ("vector_a", "vector_b")):
                entities.append({"id": ent_id, "kind": "vector", "dimension": dimension, "value": value, "role": role, "label": label, "claim_refs": claim_refs})
            result_value = example["result"] if isinstance(example["result"], list) else vals[0]
            result_id = f"case{suffix}_r"
            entities.append({"id": result_id, "kind": "vector", "dimension": len(result_value), "value": result_value, "role": "result", "label": "result", "claim_refs": claim_refs})
            rid = f"rel.case.{topic_id}.{suffix}"
            relation_kind = "orientation" if topic_id.startswith("ch01.inner") else "invariant"
            relations.append({"id": rid, "kind": relation_kind, "source_ref": ids[0], "target_ref": ids[1], "parameters": {}, "claim_refs": claim_refs})
            stage_refs = [rid]
            input_refs, output_refs = ids, [result_id]
        stages.append({"id": stage_id, "title": str(example["title"]), "caption": "", "layout": "overlay", "input_entity_refs": input_refs, "output_entity_refs": output_refs, "relation_refs": stage_refs, "expected_invariants": [f"lecture case {suffix}"]})
        cases.append({"id": case_id, "topic_id": topic_id, "example_ref": str(example["id"]), "claim_refs": claim_refs, "stage_refs": [stage_id], "purpose": str(example["title"])})
    visual.update({"entities": entities, "relations": relations, "stages": stages})
    if topic_id == "ch01.projection.definition":
        # 投影案例分三步，每个窗格只保留该步的实体和关系。
        steps = (
            {
                "title": "第一步：给出方向 u 与向量 v",
                "caption": r"$\boldsymbol u=(2,1)$、$\boldsymbol v=(3,4)$ 从同一原点出发；$\boldsymbol u$ 是一条斜直线，不是坐标轴。",
                "inputs": ("v", "u"), "outputs": (), "relations": (), "invariants": ["direction fixed"],
            },
            {
                "title": "第二步：作垂线，得投影 p 与垂足 H",
                "caption": (
                    r"从 $\boldsymbol v$ 的终点向 $\boldsymbol u$ 所在直线作垂线，垂足为 $H$；"
                    r"$\overrightarrow{OH}$ 就是投影 $\boldsymbol p=\frac{\boldsymbol v\cdot\boldsymbol u}{\boldsymbol u\cdot\boldsymbol u}\boldsymbol u=\frac{10}{5}(2,1)=(4,2)$。"
                ),
                "inputs": ("v", "u", "p"), "outputs": ("H",), "relations": ("", ".decompose"), "invariants": ["projection lies on direction"],
            },
            {
                "title": "第三步：残差 r 与 u 正交",
                "caption": (
                    r"$\boldsymbol r=\boldsymbol v-\boldsymbol p=(3,4)-(4,2)=(-1,2)$，"
                    r"$\boldsymbol r\cdot\boldsymbol u=(-1)\times2+2\times1=0$，所以 $\boldsymbol r\perp\boldsymbol u$，即 $\boldsymbol v=\boldsymbol p+\boldsymbol r$。"
                ),
                "inputs": ("v", "u", "p", "r"), "outputs": ("H",), "relations": ("", ".decompose", ".orthogonal"), "invariants": ["orthogonality"],
            },
        )
        for index, step in enumerate(steps, start=1):
            if index > len(stages):
                break
            ids = {name: f"case{index}_{name}" for name in ("v", "u", "p", "H", "r")}
            rid = f"rel.case.{topic_id}.{index}"
            stages[index - 1].update({
                "title": step["title"],
                "caption": step["caption"],
                "input_entity_refs": [ids[name] for name in step["inputs"]],
                "output_entity_refs": [ids[name] for name in step["outputs"]],
                "relation_refs": [f"{rid}{suffix}" for suffix in step["relations"]],
                "expected_invariants": step["invariants"],
            })
    if topic_id == "ch01.inner.definitions":
        # 内积第一步显示向量和夹角，第二步再加入投影。
        stages[0]["caption"] = (
            r"$\boldsymbol a=(2,1)$ 与 $\boldsymbol b=(1,2)$ 从同一原点出发，夹角为 $\theta$；"
            r"几何定义 $\boldsymbol a\cdot\boldsymbol b=\lvert\boldsymbol a\rvert\,\lvert\boldsymbol b\rvert\cos\theta"
            r"=\sqrt5\cdot\sqrt5\cdot\dfrac45=4$。"
        )
        stages[0]["input_entity_refs"] = [ref for ref in stages[0]["input_entity_refs"] if not ref.endswith(("_p", "_H"))]
        stages[0]["output_entity_refs"] = []
        stages[0]["relation_refs"] = [ref for ref in stages[0]["relation_refs"] if ref.startswith("rel.angle")]
        stages[1]["caption"] = (
            r"$\boldsymbol b$ 在 $\boldsymbol a$ 上的投影（虚线）为 $\boldsymbol p=(1.6,0.8)$，"
            r"投影长度 $\lvert\boldsymbol b\rvert\cos\theta=\dfrac4{\sqrt5}$；"
            r"乘以 $\lvert\boldsymbol a\rvert=\sqrt5$ 得 $\boldsymbol a\cdot\boldsymbol b=4$，"
            r"与按坐标分量相乘再相加（$2\times1+1\times2=4$）一致。"
        )
    default_pane_count = 1
    if topic_id == "ch01.inner.definitions":
        default_pane_count = 2
    elif topic_id == "ch01.projection.definition":
        # 讲义 1.4.1 的数学流程分三步，三步各占一个窗格。
        default_pane_count = 3
    explanation["case_layout"] = {
        "default_pane_count": default_pane_count,
        "cases": cases,
    }


def _refine_matrix_composition(result: dict[str, Any], explanation: dict[str, Any], visual: dict[str, Any], example: dict[str, Any]) -> None:
    explanation.update({
        "title": "复合变换与 AB≠BA",
        "summary": "矩阵乘法表示变换的复合，最右侧矩阵先作用；交换顺序通常会改变终点。",
        "definition": r"若 A、B 的维度匹配，则 (AB)x=A(Bx)，读作先做 B，再做 A。",
        "formula": r"(AB)x=A(Bx),\quad AB\ne BA",
        "derivation": [
            r"矩阵乘积的第 (i,j) 个元素为 (AB)_{ij}=\sum_k A_{ik}B_{kj}，所以 AB 代表复合变换。",
            r"先计算 Bx，再把 A 作用于 Bx；若交换顺序，则计算 Ax 后再作用 B。",
        ],
        "geometric_meaning": (
            r"取 A=\begin{pmatrix}2&0\\0&1\end{pmatrix}（水平拉伸 2 倍），"
            r"B=\begin{pmatrix}0&-1\\1&0\end{pmatrix}（逆时针旋转 90^\circ），x=(1,1)^T。\n\n"
            r"先旋转再拉伸：Bx=(-1,1)^T，ABx=(-2,1)^T。"
            r" 先拉伸再旋转：Ax=(2,1)^T，BAx=(-1,2)^T。"
            r" 两个终点不同，所以 AB\ne BA。"
        ),
        "worked_examples": [],
    })
    for key in (
        "intuition", "connections", "transfer_note", "conclusion", "read_guide",
        "analogy_boundary", "invariants", "pitfalls",
    ):
        explanation.pop(key, None)
    explanation.update({
        "connections": ["复合变换的顺序可迁移到矩阵幂、坐标变换和函数复合。"],
        "transfer_note": "遇到多个矩阵时从右向左执行，并用同一个输入比较交换顺序后的终点。",
        "invariants": ["两条路径使用同一输入，终点差异由变换顺序造成。"],
        "pitfalls": ["把 AB 误读成先做 A 后做 B，或默认矩阵乘法满足交换律。"],
    })
    if example is None:
        example = {
            "id": "example.ch02.matrix.composition",
            "kind": "matrix_transform",
            "given": [[[0, -2], [1, 0]], [1, 1]],
            "calculation": [], "result": [-2, 1],
            "checks": [{"name": "transformed", "expected": [-2, 1], "tolerance": 1e-9}],
            "claim_refs": [],
        }
        explanation["worked_examples"] = [example]
    if example:
        example.update({
            "title": "案例一：复合顺序比较",
            "given": [[[0, -2], [1, 0]], [1, 1]],
            "calculation": [
                r"A=\begin{pmatrix}2&0\\0&1\end{pmatrix},\quad B=\begin{pmatrix}0&-1\\1&0\end{pmatrix},\quad x=(1,1)^T。",
                r"Bx=(-1,1)^T，ABx=(-2,1)^T。",
                r"Ax=(2,1)^T，BAx=(-1,2)^T。",
            ],
            "result": [-2, 1],
            "checks": [{"name": "transformed", "expected": [-2, 1], "tolerance": 1e-9}],
        })
        explanation["worked_examples"] = [example]
    entities = visual.setdefault("entities", [])
    _upsert_entity(entities, "A", "matrix", [[2, 0], [0, 1]], "matrix_a", "A")
    _upsert_entity(entities, "B", "matrix", [[0, -1], [1, 0]], "matrix_b", "B")
    _upsert_entity(entities, "x", "vector", [1, 1], "vector_a", "x")
    _upsert_entity(entities, "y", "vector", [-2, 1], "transformed_a", "ABx")
    _upsert_entity(entities, "z", "vector", [-1, 2], "transformed_b", "BAx")
    relations = visual.setdefault("relations", [])
    _upsert_relation(relations, "composition_order", "composition_order", "x", "y", {"matrices": [[[0, -1], [1, 0]], [[2, 0], [0, 1]]]})
    _upsert_relation(relations, "composition_order_ba", "composition_order", "x", "z", {"matrices": [[[2, 0], [0, 1]], [[0, -1], [1, 0]]]})
    _upsert_relation(relations, "endpoint_diff", "endpoint_diff", "y", "z", {})
    _upsert_relation(relations, "composition_compare", "compare", "y", "z", {})
    claim = (result.get("claims") or [{}])[0]
    claim["entity_refs"] = [entity["id"] for entity in entities]
    claim["formula_symbols"] = ["A", "B", "x", "ABx", "BAx"]
    claim["relation_refs"] = [relation["id"] for relation in relations]
    visual["stages"] = [
        {"id": "stage.composition.input", "title": "固定输入", "caption": "同一向量 x 作为两条路径的输入。", "layout": "overlay", "input_entity_refs": ["x"], "output_entity_refs": [], "relation_refs": [], "expected_invariants": ["input fixed"]},
        {"id": "stage.composition.ab", "title": "先 B 后 A", "caption": "B 先旋转，再由 A 沿水平方向拉伸，终点为 ABx=(-2,1)。", "layout": "sequence", "input_entity_refs": ["x", "B"], "output_entity_refs": ["y"], "relation_refs": ["composition_order"], "expected_invariants": ["AB path"]},
        {"id": "stage.composition.ba", "title": "先 A 后 B", "caption": "A 先拉伸，再由 B 旋转，终点为 BAx=(-1,2)。", "layout": "sequence", "input_entity_refs": ["x", "A"], "output_entity_refs": ["z"], "relation_refs": ["composition_order_ba"], "expected_invariants": ["BA path"]},
        {"id": "stage.composition.compare", "title": "终点比较", "caption": "ABx 与 BAx 不同，因此 AB≠BA。", "layout": "side_by_side", "input_entity_refs": ["y", "z"], "output_entity_refs": [], "relation_refs": ["endpoint_diff", "composition_compare"], "expected_invariants": ["different endpoints"]},
        {"id": "stage.composition.formula", "title": "代数结论", "caption": "两条路径对应不同的矩阵乘积，得到 AB≠BA。", "layout": "overlay", "input_entity_refs": ["A", "B", "y", "z"], "output_entity_refs": [], "relation_refs": ["composition_compare"], "expected_invariants": ["AB != BA"]},
    ]
    claim["stage_refs"] = [stage["id"] for stage in visual["stages"]]
    explanation["symbol_roles"] = {"A": "matrix_a", "B": "matrix_b", "x": "vector_a", "ABx": "transformed_a", "BAx": "transformed_b"}
    explanation["sections"] = [
        {"id": section_id, "title": section_id, "text": "", "claim_refs": [claim["id"]]}
        for section_id in ("definition", "formula", "derivation", "worked_examples", "geometric_meaning")
    ]
    explanation["case_layout"] = {
        "default_pane_count": 1,
        "cases": [
            {
                "id": "case.composition.ab", "topic_id": "ch02.matrix.composition",
                "example_ref": str(example["id"]), "claim_refs": [claim["id"]],
                "stage_refs": ["stage.composition.ab"], "purpose": "案例一：先 B 后 A",
            },
            {
                "id": "case.composition.ba", "topic_id": "ch02.matrix.composition",
                "example_ref": str(example["id"]), "claim_refs": [claim["id"]],
                "stage_refs": ["stage.composition.ba"], "purpose": "案例二：先 A 后 B",
            },
            {
                "id": "case.composition.compare", "topic_id": "ch02.matrix.composition",
                "example_ref": str(example["id"]), "claim_refs": [claim["id"]],
                "stage_refs": ["stage.composition.compare"], "purpose": "案例三：终点比较",
            },
        ],
    }


_BATCH_LESSONS: dict[str, dict[str, Any]] = {
    "ch01.ops.subtraction": {
        "definition": r"向量减法定义为加上减向量的相反向量：$\boldsymbol a-\boldsymbol b=\boldsymbol a+(-\boldsymbol b)$。",
        "formula": r"\boldsymbol a-\boldsymbol b=(a_1-b_1,\,a_2-b_2)",
        "geometry": r"将 $\boldsymbol a$、$\boldsymbol b$ 的起点放在同一点，$\boldsymbol a-\boldsymbol b$ 是从 $\boldsymbol b$ 的终点指向 $\boldsymbol a$ 的终点的向量。",
        "case": ("案例一：终点间的位移", [r"$$\boldsymbol a=(4,3),\quad \boldsymbol b=(1,2),\quad -\boldsymbol b=(-1,-2)$$", r"$$\boldsymbol a-\boldsymbol b=\boldsymbol a+(-\boldsymbol b)=(3,1)$$"]),
    },
    "ch01.ops.scalar": {
        "definition": r"标量 $\lambda$ 与向量 $\boldsymbol v$ 的数乘逐分量进行。",
        "formula": r"\lambda\boldsymbol v=(\lambda v_1,\,\lambda v_2)",
        "geometry": r"当 $\lambda>0$ 时，$\lambda\boldsymbol v$ 与 $\boldsymbol v$ 同向；当 $\lambda<0$ 时反向；长度满足 $\lvert\lambda\boldsymbol v\rvert=\lvert\lambda\rvert\lvert\boldsymbol v\rvert$。它们始终共线。",
        "case": ("案例一：数乘与共线", [r"$$\boldsymbol v=(1,2),\qquad 2\boldsymbol v=(2,4)$$", r"$$-\boldsymbol v=(-1,-2)$$"]),
    },
    "ch01.ops.linear-combination": {
        "definition": r"给定向量 $\boldsymbol v_1,\ldots,\boldsymbol v_k$，它们的线性组合是各向量乘以标量后相加的结果。",
        "formula": r"c_1\boldsymbol v_1+\cdots+c_k\boldsymbol v_k",
        "geometry": r"二维标准基 $\boldsymbol e_1,\boldsymbol e_2$ 的线性组合给出平面中的位置；系数分别指定沿两条基方向的位移。",
        "case": ("案例一：标准基组合", [r"$$2\boldsymbol e_1+3\boldsymbol e_2=2(1,0)+3(0,1)=(2,3)$$"]),
    },
    "ch01.inner.definitions": {
        "definition": r"两非零向量的内积由其中一个向量在另一个方向上的带符号投影确定。",
        "formula": r"\boldsymbol a\cdot\boldsymbol b=\lvert\boldsymbol a\rvert\lvert\boldsymbol b\rvert\cos\theta",
        "geometry": r"当 $\theta$ 为锐角、直角、钝角时，投影分别为正、零、负，因此内积的符号编码夹角关系。",
        "case": ("案例一：投影长度", [r"$$\boldsymbol a=(2,0),\quad \boldsymbol b=(1,1),\quad \boldsymbol a\cdot\boldsymbol b=2$$"]),
    },
    "ch01.inner.cauchy-schwarz": {
        "definition": r"柯西—施瓦茨不等式给出两个向量内积绝对值的上界。",
        "formula": r"\lvert\boldsymbol a\cdot\boldsymbol b\rvert\leq\lvert\boldsymbol a\rvert\lvert\boldsymbol b\rvert",
        "derivation": [r"$\boldsymbol a$ 在 $\boldsymbol b$ 方向上的投影长度不超过 $\lvert\boldsymbol a\rvert$。", r"投影长度为 $\dfrac{\lvert\boldsymbol a\cdot\boldsymbol b\rvert}{\lvert\boldsymbol b\rvert}$，两边乘 $\lvert\boldsymbol b\rvert$ 即得不等式。"],
        "geometry": r"等号在两个非零向量共线时成立；不等式比较的是向量长度和沿另一方向的投影长度。",
        "case": ("案例一：投影界", [r"$$\boldsymbol a=(3,4),\quad \boldsymbol b=(1,0),\quad \lvert\boldsymbol a\cdot\boldsymbol b\rvert=3\leq5=\lvert\boldsymbol a\rvert\lvert\boldsymbol b\rvert$$"]),
    },
    "ch01.projection.definition": {
        "definition": r"设 $\boldsymbol u\ne\boldsymbol0$。$\boldsymbol v$ 在 $\boldsymbol u$ 方向上的正交投影是与 $\boldsymbol u$ 共线的向量 $\boldsymbol p$。",
        "formula": r"\operatorname{proj}_{\boldsymbol u}\boldsymbol v=\frac{\boldsymbol v\cdot\boldsymbol u}{\boldsymbol u\cdot\boldsymbol u}\boldsymbol u,\qquad \boldsymbol v=\boldsymbol p+\boldsymbol r",
        "geometry": r"从 $\boldsymbol v$ 的终点向 $\boldsymbol u$ 所在直线作垂线，垂足给出 $\boldsymbol p$ 的终点；残差 $\boldsymbol r=\boldsymbol v-\boldsymbol p$ 与 $\boldsymbol u$ 垂直。",
        "case": ("案例一：x 轴投影", [r"$$\boldsymbol v=(3,4),\quad \boldsymbol u=(1,0),\quad \boldsymbol p=(3,0)$$", r"$$\boldsymbol r=(0,4),\qquad \boldsymbol v=\boldsymbol p+\boldsymbol r$$"]),
    },
    "ch01.proof.midline": {
        "definition": r"三角形两边中点的连线称为中位线。",
        "formula": r"\overrightarrow{MN}=\frac12\overrightarrow{BC}",
        "derivation": [r"设 $M=\dfrac{A+B}{2},\ N=\dfrac{A+C}{2}$。", r"则 $\overrightarrow{MN}=N-M=\dfrac{C-B}{2}=\dfrac12\overrightarrow{BC}$。"],
        "geometry": r"$MN$ 与 $BC$ 同向且长度为 $BC$ 的一半，因此中位线平行于第三边。",
        "case": ("案例一：中点连线", [r"$$A=(0,0),\quad B=(4,0),\quad C=(0,6)$$", r"$$M=(2,0),\quad N=(0,3),\quad \overrightarrow{MN}=(-2,3)=\frac12\overrightarrow{BC}$$"]),
    },
    "ch01.proof.centroid": {
        "definition": r"三角形重心是三个顶点位置向量的平均。",
        "formula": r"\boldsymbol g=\frac{\boldsymbol a+\boldsymbol b+\boldsymbol c}{3}",
        "derivation": [r"边 $BC$ 的中点为 $\boldsymbol m=\dfrac{\boldsymbol b+\boldsymbol c}{2}$。", r"从 $A$ 到重心的向量为 $\boldsymbol g-\boldsymbol a=\dfrac23(\boldsymbol m-\boldsymbol a)$，所以重心按 $2:1$ 分中线。"],
        "geometry": r"三条中线相交于同一点；重心靠近顶点的一段是整条中线的 $\dfrac23$。",
        "case": ("案例一：重心坐标", [r"$$A=(0,0),\quad B=(6,0),\quad C=(0,3)$$", r"$$G=\frac{A+B+C}{3}=(2,1)$$"]),
    },
    "ch01.proof.parallelogram-diagonals": {
        "definition": r"平行四边形的两条对角线连接相对顶点。",
        "formula": r"\frac{\boldsymbol a+\boldsymbol c}{2}=\frac{\boldsymbol b+\boldsymbol d}{2}",
        "derivation": [r"若 $ABCD$ 是平行四边形，则 $\boldsymbol a+\boldsymbol c=\boldsymbol b+\boldsymbol d$。", r"两边除以 $2$，两条对角线的中点位置向量相同。"],
        "geometry": r"两条对角线在同一个中点相交，因此彼此平分。",
        "case": ("案例一：共同中点", [r"$$A=(0,0),\quad B=(4,0),\quad C=(5,2),\quad D=(1,2)$$", r"$$\frac{A+C}{2}=\frac{B+D}{2}=\left(\frac52,1\right)$$"]),
    },
    "ch02.batch.inner-products": {
        "definition": r"将多个向量组成列矩阵时，矩阵乘积可一次给出一批向量之间的内积。",
        "formula": r"(U^{\mathsf T}V)_{ij}=\boldsymbol u_i\cdot\boldsymbol v_j",
        "geometry": r"矩阵的每个元素对应一对向量的夹角信息；零元素表示对应方向正交。",
        "case": ("案例一：两组方向", [r"$$\boldsymbol u_1=(1,0),\quad \boldsymbol u_2=(0,1),\quad \boldsymbol v=(2,3)$$", r"$$\begin{pmatrix}\boldsymbol u_1\cdot\boldsymbol v\\\boldsymbol u_2\cdot\boldsymbol v\end{pmatrix}=\begin{pmatrix}2\\3\end{pmatrix}$$"]),
    },
    "ch02.matrix.additive-distributivity": {
        "definition": r"同型矩阵可以逐元素相加和数乘；矩阵表示的线性变换满足分配律。",
        "formula": r"(A+B)\boldsymbol x=A\boldsymbol x+B\boldsymbol x,\qquad (\lambda A)\boldsymbol x=\lambda(A\boldsymbol x)",
        "geometry": r"先将两个变换的输出相加，与先将矩阵相加后作用于同一向量，得到相同终点。",
        "case": ("案例一：分配律", [r"$$A+B=\begin{pmatrix}6&8\\10&12\end{pmatrix},\quad \boldsymbol x=(1,1)^{\mathsf T}$$", r"$$(A+B)\boldsymbol x=(14,22)^{\mathsf T}$$"]),
    },
    "ch02.matrix.transformed-grid": {
        "definition": r"线性变换 $A$ 完全由标准基向量的像 $A\boldsymbol e_1,A\boldsymbol e_2$ 确定。",
        "formula": r"A\boldsymbol x=x_1A\boldsymbol e_1+x_2A\boldsymbol e_2",
        "geometry": r"单位方格的边由 $\boldsymbol e_1,\boldsymbol e_2$ 变为 $A\boldsymbol e_1,A\boldsymbol e_2$；因此整张坐标网格随之拉伸、旋转或剪切。",
        "case": ("案例一：两列决定像", [r"$$A=\begin{pmatrix}2&1\\0&1\end{pmatrix},\quad A\boldsymbol e_1=(2,0),\quad A\boldsymbol e_2=(1,1)$$", r"$$A(1,2)^{\mathsf T}=(4,2)^{\mathsf T}$$"]),
    },
    "ch02.matrix.basis": {
        "definition": r"同一线性变换在不同基底下有不同的坐标矩阵；换基矩阵将一种坐标描述转换为另一种。",
        "formula": r"[T]_{\mathcal B}=S^{-1}AS",
        "geometry": r"变换本身不变，改变的是描述向量的坐标尺。新基向量在原坐标中的像构成换基矩阵的列。",
        "case": ("案例一：剪切变换", [r"$$A=\begin{pmatrix}1&1\\0&1\end{pmatrix},\quad \boldsymbol x=(2,3)^{\mathsf T},\quad A\boldsymbol x=(5,3)^{\mathsf T}$$"]),
    },
    "ch02.matrix.powers": {
        "definition": r"方阵的幂表示同一线性变换重复作用；$A^0$ 定义为单位矩阵。",
        "formula": r"A^k=\underbrace{A\cdots A}_{k\text{ 个}},\qquad A^0=I",
        "geometry": r"每乘一次 $A$ 就在上一步的输出上再作用一次同一变换；因此矩阵幂记录变换的迭代轨迹。",
        "case": ("案例一：重复拉伸", [r"$$A=\begin{pmatrix}2&0\\0&1\end{pmatrix},\quad \boldsymbol x=(1,1)^{\mathsf T},\quad A\boldsymbol x=(2,1)^{\mathsf T}$$", r"$$A(A\boldsymbol x)=A^2\boldsymbol x=(4,1)^{\mathsf T}$$"]),
    },
    "ch02.subspace.independence": {
        "definition": r"一组向量线性无关，当且仅当其线性组合等于零向量时所有系数都为零。",
        "formula": r"c_1\boldsymbol v_1+\cdots+c_k\boldsymbol v_k=\boldsymbol0\ \Longrightarrow\ c_1=\cdots=c_k=0",
        "geometry": r"在平面中两条不共线向量线性无关；若两条向量共线，其中一条可以由另一条数乘得到，方向信息重复。",
        "case": ("案例一：标准基独立", [r"$$c_1(1,0)+c_2(0,1)=(0,0)\Longrightarrow c_1=c_2=0$$"]),
    },
    "ch02.subspace.rank": {
        "definition": r"矩阵的秩是其列空间的维数，即独立输出方向的个数。",
        "formula": r"\operatorname{rank}(A)=\dim\operatorname{Col}(A)",
        "geometry": r"若矩阵列向量共线，二维输入平面会被映到一条输出直线；秩为 $1$，表示只保留一个独立方向。",
        "case": ("案例一：秩为一", [r"$$A=\begin{pmatrix}1&2\\2&4\end{pmatrix},\quad A_{:2}=2A_{:1},\quad \operatorname{rank}(A)=1$$"]),
    },
}

# 数值操作数与文案分离，并以数组交给有界校验器复算。
_BATCH_NUMERIC: dict[str, tuple[Any, Any]] = {
    "ch01.ops.subtraction": ([[4, 3], [-1, -2]], [3.0, 1.0]),
    "ch01.ops.scalar": ([[1, 2], [1, 2]], [2.0, 4.0]),
    "ch01.ops.linear-combination": ([[[1, 0], [0, 1]], [2, 3]], [2.0, 3.0]),
    "ch01.inner.definitions": ([[2, 0], [1, 1]], 2.0),
    "ch01.inner.cauchy-schwarz": ([[3, 4], [1, 0]], 3.0),
    "ch01.projection.definition": ([[3, 4], [1, 0]], [3.0, 0.0]),
    "ch01.proof.midline": ([[2, 1], [1, 3]], [3.0, 4.0]),
    "ch01.proof.centroid": ([[1, 0], [0, 1]], [1.0, 1.0]),
    "ch01.proof.parallelogram-diagonals": ([[2, 1], [1, 3]], [3.0, 4.0]),
    "ch02.batch.inner-products": ([[[1, 0], [0, 1]], [2, 3]], [2.0, 3.0]),
    "ch02.matrix.additive-distributivity": ([[[6, 8], [10, 12]], [1, 1]], [14.0, 22.0]),
    "ch02.matrix.transformed-grid": ([[[2, 1], [0, 1]], [1, 2]], [4.0, 2.0]),
    "ch02.matrix.basis": ([[[1, 1], [0, 1]], [2, 3]], [5.0, 3.0]),
    "ch02.matrix.powers": ([[[2, 0], [0, 1]], [1, 1]], [2.0, 1.0]),
}

# 仅讲义明确给出的对比例题各占一个二维窗格。
_MULTI_CASES: dict[str, tuple[dict[str, Any], ...]] = {
}


def _refine_generic(topic_id: str, explanation: dict[str, Any], visual: dict[str, Any], example: dict[str, Any]) -> None:
    """Apply the confirmed concise lecture-note structure to batch topics."""

    lesson = _BATCH_LESSONS.get(topic_id)
    if lesson is None:
        return
    case_title, case_lines = lesson["case"]
    explanation.update({
        "summary": str(lesson["definition"]),
        "definition": str(lesson["definition"]),
        "formula": str(lesson["formula"]),
        "derivation": list(lesson.get("derivation", ())),
        "geometric_meaning": str(lesson["geometry"]),
        "worked_examples": [],
    })
    for key in (
        "intuition", "connections", "transfer_note", "conclusion", "read_guide",
        "analogy_boundary", "invariants", "pitfalls",
    ):
        explanation.pop(key, None)
    if example:
        numeric = _BATCH_NUMERIC.get(topic_id)
        if numeric is not None:
            example["given"], example["result"] = deepcopy(numeric[0]), deepcopy(numeric[1])
            if example.get("checks"):
                example["checks"][0]["expected"] = deepcopy(numeric[1])
        example.update({"title": case_title, "calculation": list(case_lines)})
        explanation["worked_examples"] = [example]
    if topic_id == "ch01.ops.subtraction":
        for entity in visual.get("entities", []):
            if entity.get("id") == "b":
                entity["label"] = "-b"
            elif entity.get("id") == "r":
                entity["label"] = "a-b"
    if topic_id in _MULTI_CASES:
        _apply_multi_case_layout(topic_id, explanation, visual)


def _apply_multi_case_layout(topic_id: str, explanation: dict[str, Any], visual: dict[str, Any]) -> None:
    """Build one bounded, independently visible stage per lecture case."""

    claim_id = f"claim.{topic_id}"
    cases = _MULTI_CASES[topic_id]
    examples: list[dict[str, Any]] = []
    entities: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    stages: list[dict[str, Any]] = []
    layout_cases: list[dict[str, Any]] = []
    for index, case in enumerate(cases, start=1):
        suffix = str(index)
        example_id = f"example.{topic_id}.case-{suffix}"
        entity_ids: list[str]
        relation_id = f"rel.case.{topic_id}.{suffix}"
        matrix = case.get("matrix")
        if isinstance(matrix, list):
            a_id, x_id, y_id = f"case{suffix}_A", f"case{suffix}_x", f"case{suffix}_y"
            given = case["given"]
            entities.extend([
                {"id": a_id, "kind": "matrix", "dimension": 2, "value": matrix, "role": "matrix_a", "label": "A", "claim_refs": [claim_id]},
                {"id": x_id, "kind": "vector", "dimension": 2, "value": given[1], "role": "vector_a", "label": "x", "claim_refs": [claim_id]},
                {"id": y_id, "kind": "vector", "dimension": 2, "value": case["result"], "role": "transformed_a", "label": "Ax", "claim_refs": [claim_id]},
            ])
            relations.append({"id": relation_id, "kind": "maps_to", "source_ref": x_id, "target_ref": y_id, "parameters": {"matrix": matrix}, "claim_refs": [claim_id]})
            entity_ids = [a_id, x_id, y_id]
        elif case["kind"] == "projection":
            given = case["given"]
            vector, direction, projection = given[0], given[1], case["result"]
            v_id, u_id, p_id, h_id, r_id = (
                f"case{suffix}_v", f"case{suffix}_u", f"case{suffix}_p",
                f"case{suffix}_H", f"case{suffix}_r",
            )
            residual = [vector[0] - projection[0], vector[1] - projection[1]]
            entities.extend([
                {"id": v_id, "kind": "vector", "dimension": 2, "value": vector, "role": "vector_a", "label": "F", "claim_refs": [claim_id]},
                {"id": u_id, "kind": "vector", "dimension": 2, "value": direction, "role": "direction", "label": "u", "claim_refs": [claim_id]},
                {"id": p_id, "kind": "vector", "dimension": 2, "value": projection, "role": "projection", "label": "F∥", "claim_refs": [claim_id]},
                {"id": h_id, "kind": "point", "dimension": 2, "value": projection, "role": "foot", "label": "H", "claim_refs": [claim_id]},
                {"id": r_id, "kind": "vector", "dimension": 2, "value": residual, "role": "residual", "label": "F⊥", "claim_refs": [claim_id]},
            ])
            relations.extend([
                {"id": relation_id, "kind": "projects_to", "source_ref": v_id, "target_ref": u_id, "parameters": {}, "claim_refs": [claim_id]},
                {"id": f"{relation_id}.decompose", "kind": "decomposes_into", "source_ref": v_id, "target_ref": p_id, "parameters": {}, "claim_refs": [claim_id]},
                {"id": f"{relation_id}.orthogonal", "kind": "orthogonal_to", "source_ref": r_id, "target_ref": u_id, "parameters": {}, "claim_refs": [claim_id]},
            ])
            entity_ids = [v_id, u_id, p_id, h_id, r_id]
        else:
            vectors = case["vectors"]
            a_id, b_id, r_id = f"case{suffix}_a", f"case{suffix}_b", f"case{suffix}_r"
            entities.extend([
                {"id": a_id, "kind": "vector", "dimension": 2, "value": vectors[0], "role": "vector_a", "label": "a", "claim_refs": [claim_id]},
                {"id": b_id, "kind": "vector", "dimension": 2, "value": vectors[1], "role": "vector_b", "label": "b", "claim_refs": [claim_id]},
                {"id": r_id, "kind": "vector", "dimension": 2, "value": case["result"] if isinstance(case["result"], list) else vectors[0], "role": "result", "label": "p" if case["kind"] == "projection" else "", "claim_refs": [claim_id]},
            ])
            relation_kind = "projects_to" if case["kind"] == "projection" else "compare"
            relations.append({"id": relation_id, "kind": relation_kind, "source_ref": a_id, "target_ref": b_id, "parameters": {}, "claim_refs": [claim_id]})
            entity_ids = [a_id, b_id, r_id]
        stage_id = f"stage.case.{topic_id}.{suffix}"
        stages.append({
            "id": stage_id, "title": str(case["title"]), "caption": "", "layout": "overlay",
            "input_entity_refs": entity_ids[:-1], "output_entity_refs": [entity_ids[-1]],
            "relation_refs": [item["id"] for item in relations if str(item["id"]).startswith(relation_id)], "expected_invariants": [f"lecture case {suffix}"],
        })
        examples.append({
            "id": example_id, "title": str(case["title"]), "kind": str(case["kind"]),
            "given": deepcopy(case["given"]), "calculation": list(case["lines"]),
            "result": deepcopy(case["result"]),
            "checks": [{"name": str(case["check"]), "expected": deepcopy(case["result"]), "tolerance": 1e-9}],
            "claim_refs": [claim_id],
        })
        layout_cases.append({
            "id": f"case.{topic_id}.{suffix}", "topic_id": topic_id,
            "example_ref": example_id, "claim_refs": [claim_id], "stage_refs": [stage_id],
            "purpose": str(case["title"]),
        })
    explanation["worked_examples"] = examples
    explanation["case_layout"] = {"default_pane_count": 1, "cases": layout_cases}
    visual.update({"scene_kind": "2d", "entities": entities, "relations": relations, "stages": stages})

    claim_refs = [str(item.get("id")) for item in explanation.get("sections", []) if isinstance(item, Mapping) and str(item.get("id"))]
    claim_refs = [f"claim.{topic_id}"]
    section_ids = ["definition", "formula"]
    if explanation["derivation"]:
        section_ids.append("derivation")
    section_ids.extend(("worked_examples", "geometric_meaning"))
    explanation["sections"] = [
        {"id": section_id, "title": section_id, "text": "", "claim_refs": claim_refs}
        for section_id in section_ids
    ]
    # 单例题保持独立渲染，多案例主题沿用专用布局。
    stages = visual.get("stages", [])
    if visual.get("scene_kind") == "2d" and len(stages) == 1 and example:
        stage = stages[0]
        stage["title"] = case_title
        stage["caption"] = ""
        explanation["case_layout"] = {
            "default_pane_count": 1,
            "cases": [{
                "id": f"case.{topic_id}", "topic_id": topic_id,
                "example_ref": str(example["id"]), "claim_refs": claim_refs,
                "stage_refs": [str(stage["id"])], "purpose": case_title,
            }],
        }
    else:
        explanation.pop("case_layout", None)


def _meaning_for(kinds: set[str], source: str, target: str) -> str:
    if "projects_to" in kinds:
        return f"向量 {source} 分解为沿目标方向的投影和垂直残差；图中的垂足落在目标方向上，残差与目标方向正交。"
    if "orthogonal_to" in kinds:
        return f"{source} 与 {target} 的内积为零，图中两条方向互相垂直；直角标记对应代数中的正交关系。"
    if "collapses_to" in kinds:
        return f"变换把 {source} 所代表的一族方向压到更低维的 {target}；图形的面积、体积或自由度随之退化。"
    if "composition_order" in kinds:
        return f"同一输入沿不同的复合顺序到达不同输出；图中的路径顺序就是公式中矩阵从右到左的作用顺序。"
    if "orientation" in kinds:
        return f"图中两条向量的转向记录了方向符号；交换它们会改变有向量积的正负。"
    if "spans" in kinds or "same_measure" in kinds:
        return f"输入向量张成的区域承载了长度、面积或体积关系；图形测量值与公式中的不变量保持一致。"
    if "maps_to" in kinds or "batch_maps_to" in kinds:
        return f"{source} 经线性变换到达 {target}；网格或箭头的整体形状变化由矩阵的列向量决定。"
    if "difference" in kinds:
        return f"差向量连接两个终点，方向从被减对象指向被减数对象。"
    if "scalar_multiple" in kinds:
        return f"数乘只改变向量的长度和可能的方向，点仍落在同一条过原点的直线上。"
    if "sum" in kinds:
        return f"两个输入向量的合成终点就是总位移，分量加法与图中的箭头首尾相接相互对应。"
    return f"图中的 {source}、{target} 和对应关系把公式中的对象落到可观察的方向、长度或面积上。"


def _invariants_for(kinds: set[str], example: dict[str, Any]) -> list[str]:
    if "collapses_to" in kinds:
        return ["退化后的输出仍落在较低维子空间，零面积或零体积是可观察边界。"]
    if "composition_order" in kinds:
        return ["输入、变换集合保持不变，只改变先后顺序；比较阶段应显示两个不同终点。"]
    if "projects_to" in kinds:
        return ["投影点位于目标方向，残差与目标方向正交。"]
    if "orientation" in kinds:
        return ["绝对面积保持，交换方向时有向面积变号。"]
    result = example.get("result") if example else None
    return [f"数值例的输出为 {_fmt(result)}，应与图中对应实体的位置或测量值一致。"]


def _pitfalls_for(kinds: set[str]) -> list[str]:
    if "composition_order" in kinds:
        return ["把 AB 误读成先做 A 再做 B；矩阵乘法一般不满足交换律。"]
    if "projects_to" in kinds:
        return ["把投影向量和原向量混淆；投影在目标方向上，残差才与目标方向正交。"]
    if "collapses_to" in kinds:
        return ["把输出落在一条线或原点误认为输入为零；退化来自变换丢失方向。"]
    if "orientation" in kinds:
        return ["只比较面积绝对值而忽略方向符号；有向面积需要固定向量顺序。"]
    return ["不要只看图形外观；先核对公式变量、数值结果和图中对象的对应关系。"]


def _calculation(example: dict[str, Any] | None) -> list[str]:
    if not example:
        return []
    given, result = example.get("given"), example.get("result")
    kind = str(example.get("kind", ""))
    if kind == "vector_addition" and isinstance(given, list) and len(given) == 2:
        return [f"a={_fmt(given[0])}, b={_fmt(given[1])}。", f"按对应分量计算，结果为 {_fmt(result)}。"]
    if kind == "inner_product" and isinstance(given, list) and len(given) == 2:
        return [f"a={_fmt(given[0])}, b={_fmt(given[1])}。", f"a·b=({_fmt(given[0])})·({_fmt(given[1])})={_fmt(result)}。"]
    if kind == "projection" and isinstance(given, list) and len(given) == 2:
        return [f"输入向量 v={_fmt(given[0])}，目标方向 u={_fmt(given[1])}。", f"代入投影公式得到 p={_fmt(result)}。"]
    if kind == "matrix_transform" and isinstance(given, list) and len(given) == 2:
        return [f"A={_fmt(given[0])}，x={_fmt(given[1])}。", f"逐行计算 Ax，得到 {_fmt(result)}。"]
    if kind in {"determinant", "oriented_area", "oriented_volume"}:
        return [f"代入给定向量或矩阵 {_fmt(given)}。", f"按行列式/有向测量定义得到 {_fmt(result)}。"]
    return [f"代入给定数据 {_fmt(given)}。", f"得到 {_fmt(result)}。"]


def _first_example(explanation: Mapping[str, Any]) -> dict[str, Any] | None:
    values = explanation.get("worked_examples")
    if isinstance(values, list) and values and isinstance(values[0], dict):
        return values[0]
    return None


def _entity_labels(visual: Mapping[str, Any], relation: Mapping[str, Any]) -> tuple[str, str]:
    labels = {str(item.get("id")): str(item.get("label", item.get("id", ""))) for item in visual.get("entities", []) if isinstance(item, Mapping)}
    return labels.get(str(relation.get("source_ref", "输入")), "输入"), labels.get(str(relation.get("target_ref", "输出")), "输出")


def _upsert_entity(entities: list[dict[str, Any]], entity_id: str, kind: str, value: Any, role: str, label: str) -> None:
    for entity in entities:
        if entity.get("id") == entity_id:
            entity.update({"kind": kind, "dimension": len(value) if isinstance(value, list) else 2, "value": value, "role": role, "label": label})
            return
    claim_refs = [str(entities[0].get("claim_refs", [""])[0])] if entities else []
    entities.append({"id": entity_id, "kind": kind, "dimension": len(value) if isinstance(value, list) else 2, "value": value, "role": role, "label": label, "claim_refs": claim_refs})


def _upsert_relation(relations: list[dict[str, Any]], relation_id: str, kind: str, source: str, target: str, parameters: dict[str, Any]) -> None:
    for relation in relations:
        if relation.get("id") == relation_id:
            relation.update({"kind": kind, "source_ref": source, "target_ref": target, "parameters": parameters})
            return
    claim_refs = [str(relations[0].get("claim_refs", [""])[0])] if relations else []
    relations.append({"id": relation_id, "kind": kind, "source_ref": source, "target_ref": target, "parameters": parameters, "claim_refs": claim_refs})


def _set_stage_text(visual: dict[str, Any], values: Mapping[str, tuple[str, str]]) -> None:
    for stage in visual.get("stages", []):
        if stage.get("id") in values:
            stage["title"], stage["caption"] = values[stage["id"]]


def _sync_sections(explanation: dict[str, Any]) -> None:
    field_text = {
        "definition": explanation.get("definition", ""), "formula": explanation.get("formula", ""),
        "derivation": "\n".join(explanation.get("derivation", [])),
        "worked_examples": "\n".join(explanation.get("worked_examples", [{}])[0].get("calculation", [])) if explanation.get("worked_examples") else "",
        "intuition": explanation.get("intuition", ""), "geometric_meaning": explanation.get("geometric_meaning", ""),
        "conclusion": explanation.get("conclusion", ""), "pitfalls": "\n".join(explanation.get("pitfalls", [])),
        "invariants": "\n".join(explanation.get("invariants", [])), "connections": "\n".join(explanation.get("connections", [])),
        "transfer_note": explanation.get("transfer_note", ""), "read_guide": "\n".join(explanation.get("read_guide", [])),
    }
    sections = explanation.get("sections")
    if not isinstance(sections, list):
        sections = []
    by_id = {str(section.get("id")): section for section in sections if isinstance(section, dict)}
    for section_id, text in field_text.items():
        if not str(text).strip():
            continue
        section = by_id.get(section_id)
        if section is None:
            section = {"id": section_id, "title": section_id, "claim_refs": []}
            sections.append(section)
        section["text"] = str(text)
    explanation["sections"] = sections


def _sync_searchable_text(explanation: dict[str, Any]) -> None:
    values = [explanation.get("title", ""), explanation.get("summary", ""), explanation.get("formula", "")]
    for key in ("definition", "derivation", "geometric_meaning", "invariants", "pitfalls", "connections", "read_guide"):
        value = explanation.get(key, "")
        values.extend(value if isinstance(value, list) else [value])
    explanation["searchable_text"] = list(dict.fromkeys(str(value) for value in values if str(value).strip()))


def _fmt(value: Any) -> str:
    if isinstance(value, list):
        return "(" + ", ".join(_fmt(item) for item in value) + ")" if value and not isinstance(value[0], list) else "[" + "; ".join(_fmt(item) for item in value) + "]"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


__all__ = ["refine_payload"]
