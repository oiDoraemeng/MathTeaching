"""Lecture-grounded prose refinement for locally generated teaching artifacts.

The explanation agent owns the mathematical prose.  This module is the local
review adapter used when no remote provider is configured: it turns the
bounded semantic graph and checked numeric example into readable lecture text
without emitting renderer commands.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


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
                claim["entity_refs"] = [
                    "components_a", "components_b", "components_sum",
                    "geometry_a", "geometry_b", "geometry_sum",
                    "velocity_1", "velocity_2", "velocity_sum",
                ]
                claim["relation_refs"] = [
                    "rel.addition.components",
                    "rel.addition.geometry",
                    "rel.addition.velocity",
                ]
                claim["stage_refs"] = stage_ids
    elif topic_id == "ch02.matrix.composition":
        _refine_matrix_composition(result, explanation, visual, example)
    else:
        _refine_generic(topic_id, explanation, visual, example)

    _sync_sections(explanation)
    _sync_searchable_text(explanation)
    generated = result.setdefault("generated", {})
    generated.update({
        "provider": "math-explanation-sample",
        "model": "lecture-grounded-v2",
        "prompt_version": "teaching-artifact-v1",
    })
    return result


def _refine_vector_addition(explanation: dict[str, Any], visual: dict[str, Any], example: dict[str, Any]) -> None:
    explanation.update({
        "title": "向量加法",
        "summary": r"向量加法按对应分量相加；三角形法则和平行四边形法则给出同一个和向量。",
        "definition": (
            "设\n\n"
            r"$$\boldsymbol a=(x_1,y_1),\qquad \boldsymbol b=(x_2,y_2).$$"
            "\n\n向量加法定义为\n\n"
            r"$$\boldsymbol a+\boldsymbol b=(x_1+x_2,\,y_1+y_2).$$"
            "\n\n即两个向量的对应分量分别相加。"
        ),
        # This concise formula remains the claim's machine-readable formula.
        # The definition above owns its reader-facing placement and typography.
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
        "geometric_meaning": (
            r"三角形法则：将 $\boldsymbol b$ 平移，使其起点与 $\boldsymbol a$ 的终点重合；"
            r"从 $\boldsymbol a$ 的起点指向平移后 $\boldsymbol b$ 的终点的向量为 $\boldsymbol a+\boldsymbol b$。"
            "\n\n"
            r"平行四边形法则：让 $\boldsymbol a$、$\boldsymbol b$ 从同一点出发，以它们为邻边作平行四边形；"
            r"从该点出发的对角线为 $\boldsymbol a+\boldsymbol b$。"
        ),
        "worked_examples": [],
        "symbol_roles": {"a": "vector_a", "b": "vector_b", "sum": "transformed_a"},
    })
    for key in (
        "intuition", "connections", "transfer_note", "conclusion", "read_guide", "pitfalls",
        "analogy_boundary",
    ):
        explanation.pop(key, None)

    component_example = example if example is not None else {}
    component_example.update({
        "id": "example.addition.components",
        "title": "案例一：分量计算",
        "kind": "vector_addition",
        "given": [[3, 1], [1, 2]],
        "calculation": [
            r"$$\boldsymbol a=(3,1),\quad \boldsymbol b=(1,2)$$",
            r"$$\boldsymbol a+\boldsymbol b=(3+1,\,1+2)=(4,3)$$",
        ],
        "result": [4, 3],
        "checks": [{"name": "result", "expected": [4, 3], "tolerance": 1e-9}],
        "claim_refs": ["claim.ch01.ops.addition"],
    })
    explanation["worked_examples"] = [
        component_example,
        {
            "id": "example.addition.geometry",
            "title": "案例二：三角形法则与平行四边形法则",
            "kind": "vector_addition",
            "given": [[1, 2], [3, 4]],
            "calculation": [
                r"$$\boldsymbol a=(1,2),\quad \boldsymbol b=(3,4)$$",
                r"$$\boldsymbol a+\boldsymbol b=(1+3,\,2+4)=(4,6)$$",
                r"三角形法则和平行四边形法则得到的和向量均为 $\boldsymbol a+\boldsymbol b=(4,6)$。",
            ],
            "result": [4, 6],
            "checks": [{"name": "result", "expected": [4, 6], "tolerance": 1e-9}],
            "claim_refs": ["claim.ch01.ops.addition"],
        },
        {
            "id": "example.addition.velocity",
            "title": "案例三：速度向量相加",
            "kind": "vector_addition",
            "given": [[10, 0], [0, 5]],
            "calculation": [
                r"$$\boldsymbol v_1=(10,0),\quad \boldsymbol v_2=(0,5)$$",
                r"$$\boldsymbol v=\boldsymbol v_1+\boldsymbol v_2=(10,5)$$",
                r"$$\lvert\boldsymbol v\rvert=\sqrt{10^2+5^2}=\sqrt{125}\approx11.18$$",
                r"$$\tan\theta=\frac{5}{10},\qquad\theta\approx26.6^\circ$$",
            ],
            "result": [10, 5],
            "checks": [{"name": "result", "expected": [10, 5], "tolerance": 1e-9}],
            "claim_refs": ["claim.ch01.ops.addition"],
        },
    ]
    claim_ref = ["claim.ch01.ops.addition"]
    visual["entities"] = [
        {"id": "components_a", "kind": "vector", "dimension": 2, "value": [3, 1], "role": "vector_a", "label": "a", "claim_refs": claim_ref},
        {"id": "components_b", "kind": "vector", "dimension": 2, "value": [1, 2], "role": "vector_b", "label": "b", "claim_refs": claim_ref},
        {"id": "components_sum", "kind": "vector", "dimension": 2, "value": [4, 3], "role": "transformed_a", "label": "a+b", "claim_refs": claim_ref},
        {"id": "geometry_a", "kind": "vector", "dimension": 2, "value": [1, 2], "role": "vector_a", "label": "a", "claim_refs": claim_ref},
        {"id": "geometry_b", "kind": "vector", "dimension": 2, "value": [3, 4], "role": "vector_b", "label": "b", "claim_refs": claim_ref},
        {"id": "geometry_sum", "kind": "vector", "dimension": 2, "value": [4, 6], "role": "transformed_a", "label": "a+b", "claim_refs": claim_ref},
        {"id": "velocity_1", "kind": "vector", "dimension": 2, "value": [10, 0], "role": "vector_a", "label": "v1", "claim_refs": claim_ref},
        {"id": "velocity_2", "kind": "vector", "dimension": 2, "value": [0, 5], "role": "vector_b", "label": "v2", "claim_refs": claim_ref},
        {"id": "velocity_sum", "kind": "vector", "dimension": 2, "value": [10, 5], "role": "transformed_a", "label": "v", "claim_refs": claim_ref},
    ]
    visual["relations"] = [
        {"id": "rel.addition.components", "kind": "sum", "source_ref": "components_a", "target_ref": "components_b", "parameters": {}, "claim_refs": claim_ref},
        {"id": "rel.addition.geometry", "kind": "sum", "source_ref": "geometry_a", "target_ref": "geometry_b", "parameters": {}, "claim_refs": claim_ref},
        {"id": "rel.addition.velocity", "kind": "sum", "source_ref": "velocity_1", "target_ref": "velocity_2", "parameters": {}, "claim_refs": claim_ref},
    ]
    explanation["sections"] = [
        {"id": section_id, "title": section_id, "text": "", "claim_refs": claim_ref}
        for section_id in ("definition", "formula", "invariants", "worked_examples", "geometric_meaning")
    ]
    visual["stages"] = [
        {
            "id": "stage.claim.ch01.ops.addition.components",
            "title": "案例一：分量计算",
            "caption": r"由 $\boldsymbol a=(3,1)$、$\boldsymbol b=(1,2)$ 得到 $\boldsymbol a+\boldsymbol b=(4,3)$。",
            "layout": "overlay",
            "input_entity_refs": ["components_a", "components_b"],
            "output_entity_refs": ["components_sum"],
            "relation_refs": ["rel.addition.components"],
            "expected_invariants": ["component sum is (4,3)"],
        },
        {
            "id": "stage.claim.ch01.ops.addition.geometry",
            "title": "案例二：三角形法则与平行四边形法则",
            "caption": r"$\boldsymbol a=(1,2)$、$\boldsymbol b=(3,4)$ 的两种作图均给出 $\boldsymbol a+\boldsymbol b=(4,6)$。",
            "layout": "overlay",
            "input_entity_refs": ["geometry_a", "geometry_b"],
            "output_entity_refs": ["geometry_sum"],
            "relation_refs": ["rel.addition.geometry"],
            "expected_invariants": ["both constructions end at (4,6)"],
        },
        {
            "id": "stage.claim.ch01.ops.addition.velocity",
            "title": "案例三：速度向量相加",
            "caption": r"$\boldsymbol v_1=(10,0)$、$\boldsymbol v_2=(0,5)$ 的和为 $\boldsymbol v=(10,5)$。",
            "layout": "overlay",
            "input_entity_refs": ["velocity_1", "velocity_2"],
            "output_entity_refs": ["velocity_sum"],
            "relation_refs": ["rel.addition.velocity"],
            "expected_invariants": ["velocity sum is (10,5)"],
        },
    ]
    explanation["case_layout"] = {
        "default_pane_count": 1,
        "cases": [
            {
                "id": "case.components",
                "topic_id": "ch01.ops.addition",
                "example_ref": "example.addition.components",
                "claim_refs": ["claim.ch01.ops.addition"],
                "stage_refs": ["stage.claim.ch01.ops.addition.components"],
                "purpose": "案例一：分量计算",
            },
            {
                "id": "case.geometry",
                "topic_id": "ch01.ops.addition",
                "example_ref": "example.addition.geometry",
                "claim_refs": ["claim.ch01.ops.addition"],
                "stage_refs": ["stage.claim.ch01.ops.addition.geometry"],
                "purpose": "案例二：几何作图",
            },
            {
                "id": "case.velocity",
                "topic_id": "ch01.ops.addition",
                "example_ref": "example.addition.velocity",
                "claim_refs": ["claim.ch01.ops.addition"],
                "stage_refs": ["stage.claim.ch01.ops.addition.velocity"],
                "purpose": "案例三：速度向量",
            },
        ],
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
        "intuition": "矩阵乘法不是把两个矩阵的数字逐项相乘，而是把两个空间变换按时间顺序串起来。",
        "geometric_meaning": (
            r"取 A=\begin{pmatrix}2&0\\0&1\end{pmatrix}（水平拉伸 2 倍），"
            r"B=\begin{pmatrix}0&-1\\1&0\end{pmatrix}（逆时针旋转 90^\circ），x=(1,1)^T。\n\n"
            r"先旋转再拉伸：Bx=(-1,1)^T，ABx=(-2,1)^T。"
            r" 先拉伸再旋转：Ax=(2,1)^T，BAx=(-1,2)^T。"
            r" 两个终点不同，所以 AB\ne BA。"
        ),
        "conclusion": r"同一输入经过相同的两个变换，但顺序不同会到达不同终点；顺序是复合变换的一部分。",
        "pitfalls": [
            "AB 不是先做 A 再做 B；按作用在向量上的顺序，右侧 B 先作用。",
            "只有在特殊条件下才有 AB=BA，不能把交换律套到矩阵乘法。",
        ],
        "invariants": [r"两条路径都使用同一输入 x、同一对变换 A 和 B，唯一改变的是先后顺序。"],
        "read_guide": ["先固定输入向量，再分别沿 AB、BA 两条路径读中间结果和最终终点。"],
    })
    if example:
        example.update({
            "title": "旋转与水平拉伸的顺序比较",
            "given": [[[0, -2], [1, 0]], [1, 1]],
            "calculation": [
                r"A=\begin{pmatrix}2&0\\0&1\end{pmatrix},\quad B=\begin{pmatrix}0&-1\\1&0\end{pmatrix},\quad x=(1,1)^T。",
                r"Bx=(-1,1)^T，ABx=(-2,1)^T。",
                r"Ax=(2,1)^T，BAx=(-1,2)^T。",
            ],
            "result": [-2, 1],
            "checks": [{"name": "transformed", "expected": [-2, 1], "tolerance": 1e-9}],
        })
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


def _refine_generic(topic_id: str, explanation: dict[str, Any], visual: dict[str, Any], example: dict[str, Any]) -> None:
    relations = visual.get("relations") or []
    kinds = {str(item.get("kind", "")) for item in relations if isinstance(item, Mapping)}
    relation = next((item for item in relations if isinstance(item, Mapping)), {})
    source_label, target_label = _entity_labels(visual, relation)
    calculation = _calculation(example)
    meaning = _meaning_for(kinds, source_label, target_label)
    explanation["derivation"] = [
        "从讲义中的定义和公式确定输入对象，再逐步代入本主题的数值例。",
        calculation[-1] if calculation else "核对公式结果与图中输出对象一致。",
    ]
    explanation["geometric_meaning"] = meaning
    explanation["intuition"] = meaning.split("。", 1)[0] + "。"
    explanation["invariants"] = _invariants_for(kinds, example)
    explanation["pitfalls"] = _pitfalls_for(kinds)
    explanation["read_guide"] = ["先读输入对象和公式变量，再沿图中的关系读输出，最后核对数值和不变量。"]
    if calculation and example:
        example["calculation"] = calculation
        example.setdefault("title", "讲义数值例")


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
