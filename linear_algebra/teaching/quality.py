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
    elif topic_id == "ch01.vector.point-distinction":
        _refine_vector_point_distinction(explanation, visual)
        result["connections"] = []
        section_ids = [str(section.get("id")) for section in explanation.get("sections", []) if isinstance(section, Mapping) and section.get("id")]
        stage_ids = [str(stage.get("id")) for stage in visual.get("stages", []) if isinstance(stage, Mapping) and stage.get("id")]
        for claim in result.get("claims", []):
            if isinstance(claim, dict):
                claim["explanation_refs"] = section_ids
                claim["formula"] = r"\boldsymbol v=x\boldsymbol e_1+y\boldsymbol e_2"
                claim["formula_symbols"] = ["P", "v", "e_1", "e_2"]
                claim["entity_refs"] = ["point_P", "vector_v", "e1", "e2"]
                claim["relation_refs"] = ["rel.point-distinction.location", "rel.point-distinction.basis"]
                claim["stage_refs"] = stage_ids
    elif topic_id == "ch01.vector.coordinate-system":
        _refine_coordinate_system(explanation, visual, example)
        result["connections"] = []
        for claim in result.get("claims", []):
            if isinstance(claim, dict):
                claim["explanation_refs"] = [
                    "definition", "formula", "worked_examples", "geometric_meaning"
                ]
                claim["formula"] = (
                    r"\boldsymbol e_1=(1,0),\quad \boldsymbol e_2=(0,1),\quad "
                    r"\boldsymbol e_1\cdot\boldsymbol e_2=0"
                )
                claim["formula_symbols"] = ["e_1", "e_2"]
    elif topic_id == "ch01.vector.direction-examples":
        _refine_direction_examples(explanation, visual)
        result["connections"] = []
        for claim in result.get("claims", []):
            if isinstance(claim, dict):
                claim["explanation_refs"] = [
                    "definition", "formula", "worked_examples", "geometric_meaning"
                ]
                claim["formula"] = r"\boldsymbol v=(x,y),\qquad \lvert\boldsymbol v\rvert=\sqrt{x^2+y^2}"
                claim["formula_symbols"] = ["v"]
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
                claim["explanation_refs"] = ["definition", "formula", "derivation", "worked_examples", "geometric_meaning"]
                claim["formula"] = str(explanation.get("formula", ""))
                claim["formula_symbols"] = ["a", "b"]
    elif topic_id.startswith("ch01.inner.") or topic_id.startswith("ch01.projection.") or topic_id.startswith("ch01.proof."):
        _refine_remaining_chapter_one(topic_id, explanation, visual)
        result["connections"] = []
        symbols_by_topic = {
            "ch01.inner.definitions": ["a", "b"],
            "ch01.inner.applications": ["a", "b"],
            "ch01.inner.cauchy-schwarz": ["a", "b"],
            "ch01.projection.definition": ["v", "u", "p", "r"],
            "ch01.projection.properties": ["v", "u"],
            "ch01.projection.force": ["v", "u", "p", "r"],
            "ch01.proof.midline": ["a", "b"],
            "ch01.proof.centroid": ["a", "b"],
            "ch01.proof.parallelogram-diagonals": ["a", "b"],
        }
        for claim in result.get("claims", []):
            if isinstance(claim, dict):
                # 分节编号以产物为准：1.3.1 把公式并入「定义」、不再单列
                # 「几何意义」，claim 不能引用已被移除的分节。
                claim["explanation_refs"] = [
                    str(section["id"])
                    for section in explanation.get("sections", [])
                    if isinstance(section, Mapping) and section.get("id")
                ]
                claim["formula"] = str(explanation.get("formula", ""))
                claim["formula_symbols"] = symbols_by_topic.get(topic_id, ["a", "b"])
    elif topic_id == "ch02.matrix.composition":
        _refine_matrix_composition(result, explanation, visual, example)
    else:
        _refine_generic(topic_id, explanation, visual, example)

    # Chapters 2-8 publish the lecture verbatim (definitions, derivations,
    # worked cases and geometric readings) instead of the compressed template.
    # This runs before the claim refs are re-synchronised below so that any
    # extra storyboard stages become real claim bindings.
    from linear_algebra.teaching import lecture_content

    lecture_content.apply(result)

    # Refined case layouts may replace the template graph.  Keep the single
    # source-grounded claim bound to the exact entities, relations and stages
    # that are now published, rather than leaving stale template references.
    for claim in result.get("claims", []):
        if isinstance(claim, dict):
            claim["entity_refs"] = [str(item["id"]) for item in visual.get("entities", []) if isinstance(item, Mapping) and item.get("id")]
            claim["relation_refs"] = [str(item["id"]) for item in visual.get("relations", []) if isinstance(item, Mapping) and item.get("id")]
            claim["stage_refs"] = [str(item["id"]) for item in visual.get("stages", []) if isinstance(item, Mapping) and item.get("id")]

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
        "summary": "向量加法按对应分量相加；几何上以两个向量为邻边作平行四边形，从原点出发的对角线就是和向量。",
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
        # 讲义在定义正下方给出的几何解释只有平行四边形法则，这里按讲义原文保留，
        # 不再补写讲义没有的三角形法则，也不改用几句话概括。
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

    # 只保留一个数学流程：第一步给出 a、b，第二步给出 a+b 与平行四边形。
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
        # 数学案例流程默认“全部显示”：两个步骤并排、共用同一视角。
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


def _refine_vector_point_distinction(
    explanation: dict[str, Any], visual: dict[str, Any]
) -> None:
    """Keep the point/vector distinction faithful to subsection 1.1.2.

    The prior generic artifact turned this topic into a difference-vector and
    inner-product calculation.  The lecture instead distinguishes a position
    from an origin-anchored vector and introduces the standard basis.
    """

    claim_refs = ["claim.ch01.vector.point-distinction"]
    explanation.update(
        {
            "title": "点与向量的本质区别",
            "summary": r"点表示位置；向量表示从原点出发的方向和长度。",
            "definition": (
                r"在平面直角坐标系中，点 $P=(x,y)$ 表示一个位置；其坐标回答“在哪里”。"
                "\n\n"
                r"向量 $\boldsymbol v=(x,y)$ 表示方向和长度。将它画成从原点 $O(0,0)$ "
                r"指向终点 $(x,y)$ 的有向线段；其坐标回答“沿哪个方向、多远”。"
            ),
            "formula": (
                r"\begin{gathered}"
                r"\boldsymbol e_1=(1,0),\qquad \boldsymbol e_2=(0,1),\\"
                r"\boldsymbol v=x\boldsymbol e_1+y\boldsymbol e_2="
                r"x(1,0)+y(0,1)."
                r"\end{gathered}"
            ),
            "geometric_meaning": (
                r"案例一中的点 $P=(3,4)$ 只标记平面中的一个位置。"
                "\n\n"
                r"案例二中的 $\boldsymbol v=(3,4)$ 是从原点出发的箭头；"
                r"其坐标分量对应 $\boldsymbol v=3\boldsymbol e_1+4\boldsymbol e_2$。"
            ),
            "worked_examples": [
                {
                    "id": "example.point-distinction.location",
                    "title": "案例一：位置点",
                    "kind": "vector_addition",
                    "given": [[3, 4], [0, 0]],
                    "calculation": [
                        r"$$P=(3,4)$$",
                        r"点 $P$ 标记平面中的位置 $(3,4)$。",
                    ],
                    "result": [3, 4],
                    "checks": [{"name": "position", "expected": [3, 4], "tolerance": 1e-9}],
                    "claim_refs": claim_refs,
                },
                {
                    "id": "example.point-distinction.vector",
                    "title": "案例二：原点向量与标准基",
                    "kind": "vector_addition",
                    "given": [[3, 4], [0, 0]],
                    "calculation": [
                        r"$$\boldsymbol v=(3,4)$$",
                        r"$$\boldsymbol v=3\boldsymbol e_1+4\boldsymbol e_2$$",
                        r"箭头从原点出发，终点为 $(3,4)$。",
                    ],
                    "result": [3, 4],
                    "checks": [{"name": "components", "expected": [3, 4], "tolerance": 1e-9}],
                    "claim_refs": claim_refs,
                },
            ],
            "symbol_roles": {
                "P": "vector_a",
                "v": "vector_a",
                "e_1": "basis_e1",
                "e_2": "basis_e2",
            },
        }
    )
    for key in (
        "intuition", "connections", "transfer_note", "conclusion", "read_guide",
        "analogy_boundary", "derivation", "invariants", "pitfalls",
    ):
        explanation.pop(key, None)

    visual["scene_kind"] = "2d"
    visual["entities"] = [
        {
            "id": "point_P", "kind": "point", "dimension": 2, "value": [3, 4],
            "role": "vector_a", "label": "P", "claim_refs": claim_refs,
        },
        {
            "id": "vector_v", "kind": "vector", "dimension": 2, "value": [3, 4],
            "role": "vector_a", "label": "v", "claim_refs": claim_refs,
        },
        {
            "id": "e1", "kind": "vector", "dimension": 2, "value": [1, 0],
            "role": "basis_e1", "label": "e₁", "claim_refs": claim_refs,
        },
        {
            "id": "e2", "kind": "vector", "dimension": 2, "value": [0, 1],
            "role": "basis_e2", "label": "e₂", "claim_refs": claim_refs,
        },
    ]
    visual["relations"] = [
        {
            "id": "rel.point-distinction.location", "kind": "invariant",
            "source_ref": "point_P", "target_ref": "point_P", "parameters": {},
            "claim_refs": claim_refs,
        },
        {
            "id": "rel.point-distinction.basis", "kind": "invariant",
            "source_ref": "vector_v", "target_ref": "vector_v", "parameters": {},
            "claim_refs": claim_refs,
        },
    ]
    visual["stages"] = [
        {
            "id": "stage.point-distinction.location", "title": "案例一：位置点",
            "caption": r"$P=(3,4)$ 表示平面中的一个位置。", "layout": "overlay",
            "input_entity_refs": ["point_P"], "output_entity_refs": [],
            "relation_refs": ["rel.point-distinction.location"],
            "expected_invariants": ["point marks the position (3,4)"],
        },
        {
            "id": "stage.point-distinction.vector", "title": "案例二：原点向量与标准基",
            "caption": r"$\boldsymbol v=(3,4)$ 从原点指向终点 $(3,4)$。", "layout": "overlay",
            "input_entity_refs": ["vector_v", "e1", "e2"], "output_entity_refs": [],
            "relation_refs": ["rel.point-distinction.basis"],
            "expected_invariants": ["vector starts at the origin and ends at (3,4)"],
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
                "id": "case.point-distinction.location",
                "topic_id": "ch01.vector.point-distinction",
                "example_ref": "example.point-distinction.location",
                "claim_refs": claim_refs,
                "stage_refs": ["stage.point-distinction.location"],
                "purpose": "案例一：位置点",
            },
            {
                "id": "case.point-distinction.vector",
                "topic_id": "ch01.vector.point-distinction",
                "example_ref": "example.point-distinction.vector",
                "claim_refs": claim_refs,
                "stage_refs": ["stage.point-distinction.vector"],
                "purpose": "案例二：原点向量与标准基",
            },
        ],
    }


def _refine_coordinate_system(
    explanation: dict[str, Any], visual: dict[str, Any], example: dict[str, Any] | None
) -> None:
    """Present subsection 1.1.3 as the lecture's coordinate conventions only."""

    claim_refs = ["claim.ch01.vector.coordinate-system"]
    explanation.update({
        "title": "坐标系与右手约定",
        "summary": "本书在二维图中使用单位长度相等的直角坐标系，并以标准基确定正方向。",
        "definition": (
            r"本书使用直角坐标系：$x$ 轴向右为正，$y$ 轴向上为正，且两条坐标轴的单位长度相等。"
            "\n\n"
            r"标准基为 $\boldsymbol e_1=(1,0)$、$\boldsymbol e_2=(0,1)$；二者的长度均为 $1$，并且互相垂直。"
            "\n\n"
            r"三维坐标系继续采用右手约定，$z$ 轴指向观察者。"
        ),
        "formula": (
            r"\boldsymbol e_1=(1,0),\qquad \boldsymbol e_2=(0,1),\qquad "
            r"\lvert\boldsymbol e_1\rvert=\lvert\boldsymbol e_2\rvert=1,\qquad "
            r"\boldsymbol e_1\cdot\boldsymbol e_2=0"
        ),
        "derivation": [],
        "geometric_meaning": (
            r"二维窗格中的两条箭头分别给出 $x$ 轴和 $y$ 轴的正方向；它们从同一原点出发、长度相等且垂直。"
            r"后续二维向量的坐标都以这两条标准基为参照。"
        ),
        "worked_examples": [],
        "symbol_roles": {"e_1": "basis_e1", "e_2": "basis_e2"},
    })
    for key in (
        "intuition", "connections", "transfer_note", "conclusion", "read_guide",
        "analogy_boundary", "invariants", "pitfalls",
    ):
        explanation.pop(key, None)
    coordinate_case = example if example is not None else {}
    coordinate_case.update({
        "id": "example.coordinate-system.standard-basis",
        "title": "案例一：标准基与坐标轴",
        "kind": "inner_product",
        "given": [[1, 0], [0, 1]],
        "calculation": [
            r"$$\boldsymbol e_1=(1,0),\qquad \boldsymbol e_2=(0,1)$$",
            r"$$\lvert\boldsymbol e_1\rvert=\lvert\boldsymbol e_2\rvert=1,\qquad \boldsymbol e_1\cdot\boldsymbol e_2=0$$",
        ],
        "result": 0,
        "checks": [{"name": "dot", "expected": 0, "tolerance": 1e-9}],
        "claim_refs": claim_refs,
    })
    explanation["worked_examples"] = [coordinate_case]
    visual.update({
        "scene_kind": "2d",
        "entities": [
            {"id": "e1", "kind": "vector", "dimension": 2, "value": [1, 0], "role": "basis_e1", "label": "e₁", "claim_refs": claim_refs},
            {"id": "e2", "kind": "vector", "dimension": 2, "value": [0, 1], "role": "basis_e2", "label": "e₂", "claim_refs": claim_refs},
        ],
        "relations": [
            {"id": "rel.coordinate-system.orthogonal", "kind": "orthogonal_to", "source_ref": "e1", "target_ref": "e2", "parameters": {}, "claim_refs": claim_refs},
        ],
        "stages": [
            {
                "id": "stage.coordinate-system.standard-basis", "title": "案例一：标准基与坐标轴", "caption": "", "layout": "overlay",
                "input_entity_refs": ["e1", "e2"], "output_entity_refs": [],
                "relation_refs": ["rel.coordinate-system.orthogonal"],
                "expected_invariants": ["unit orthogonal standard basis"],
            },
        ],
    })
    explanation["sections"] = [
        {"id": section_id, "title": section_id, "text": "", "claim_refs": claim_refs}
        for section_id in ("definition", "formula", "worked_examples", "geometric_meaning")
    ]
    explanation["case_layout"] = {
        "default_pane_count": 1,
        "cases": [
            {
                "id": "case.coordinate-system.standard-basis", "topic_id": "ch01.vector.coordinate-system",
                "example_ref": "example.coordinate-system.standard-basis", "claim_refs": claim_refs,
                "stage_refs": ["stage.coordinate-system.standard-basis"],
                "purpose": "案例一：标准基与坐标轴",
            },
        ],
    }


def _refine_direction_examples(explanation: dict[str, Any], visual: dict[str, Any]) -> None:
    """Use the four independent examples in lecture subsection 1.1.4."""

    claim_refs = ["claim.ch01.vector.direction-examples"]
    explanation.update({
        "title": "方向、象限与分层例题",
        "summary": "从方向和长度确定坐标，再由坐标符号判断象限。",
        "definition": (
            r"二维非零向量 $\boldsymbol v=(x,y)$ 的方向由从原点指向终点的射线确定。"
            "\n\n"
            r"若方向与 $x$ 轴正向的夹角为 $\theta$、长度为 $\lvert\boldsymbol v\rvert$，则坐标分量满足"
        ),
        "formula": r"\boldsymbol v=(x,y),\qquad \lvert\boldsymbol v\rvert=\sqrt{x^2+y^2}",
        "derivation": [],
        "geometric_meaning": (
            r"向量终点的横、纵坐标分别给出两个坐标轴方向的分量；$x,y$ 的符号决定终点所在象限。"
            r"下面四个案例分别对应由方向和长度求坐标、由坐标判断象限，以及东北方向的分量表示。"
        ),
        "worked_examples": [],
        "symbol_roles": {"v": "vector_a", "a": "vector_a", "b": "vector_b"},
    })
    for key in (
        "intuition", "connections", "transfer_note", "conclusion", "read_guide",
        "analogy_boundary", "invariants", "pitfalls",
    ):
        explanation.pop(key, None)
    examples = [
        {
            "id": "example.direction.right-up", "title": "案例一：右上方且成 45°",
            "kind": "inner_product", "given": [[2, 2], [2, 2]], "result": 8.0,
            "calculation": [
                r"$$\lvert\boldsymbol v\rvert\approx2.83,\qquad \theta=45^\circ\Longrightarrow x=y=a$$",
                r"$$\sqrt{a^2+a^2}=a\sqrt2\approx2.83\Longrightarrow a\approx2$$",
                r"$$\boldsymbol v=(2,2)$$",
            ],
            "checks": [{"name": "dot", "expected": 8.0, "tolerance": 1e-9}],
            "vectors": [[2, 2], [2, 2]], "relation": "compare",
        },
        {
            "id": "example.direction.vertical", "title": "案例二：竖直向上",
            "kind": "inner_product", "given": [[0, 3], [0, 3]], "result": 9.0,
            "calculation": [
                r"$$\theta=90^\circ,\qquad x=0,\qquad \lvert\boldsymbol v\rvert=3$$",
                r"$$\boldsymbol v=(0,3)$$",
            ],
            "checks": [{"name": "dot", "expected": 9.0, "tolerance": 1e-9}],
            "vectors": [[0, 3], [0, 3]], "relation": "compare",
        },
        {
            "id": "example.direction.quadrants", "title": "案例三：由坐标判断象限",
            "kind": "inner_product", "given": [[2, 3], [-1, 4]], "result": 10.0,
            "calculation": [
                r"$$\boldsymbol a=(2,3),\qquad \boldsymbol b=(-1,4)$$",
                r"$$a_x>0,\ a_y>0\Longrightarrow\boldsymbol a\text{ 的终点在第一象限}$$",
                r"$$b_x<0,\ b_y>0\Longrightarrow\boldsymbol b\text{ 的终点在第二象限}$$",
            ],
            "checks": [{"name": "dot", "expected": 10.0, "tolerance": 1e-9}],
            "vectors": [[2, 3], [-1, 4]], "relation": "compare",
        },
        {
            "id": "example.direction.northeast", "title": "案例四：东北方向的航行",
            "kind": "vector_addition", "given": [[7.07, 7.07], [0, 0]], "result": [7.07, 7.07],
            "calculation": [
                r"$$\lvert\boldsymbol v\rvert=10,\qquad \text{东北方向}\Longrightarrow x=y=a$$",
                r"$$a\sqrt2=10\Longrightarrow a=\frac{10}{\sqrt2}\approx7.07$$",
                r"$$\boldsymbol v\approx(7.07,7.07)$$",
            ],
            "checks": [{"name": "sum", "expected": [7.07, 7.07], "tolerance": 1e-9}],
            # This relation records that the displayed vector is compared with
            # the zero vector.  It is intentionally not ``sum``: the latter
            # asks the generic visual compiler to construct an addition
            # polygon, which is not part of this direction example.
            "vectors": [[7.07, 7.07], [0, 0]], "relation": "compare",
        },
    ]
    entities: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []
    stages: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []
    for index, item in enumerate(examples, start=1):
        first_id, second_id = f"direction_{index}_a", f"direction_{index}_b"
        entities.extend([
            {"id": first_id, "kind": "vector", "dimension": 2, "value": item["vectors"][0], "role": "vector_a", "label": "a" if index == 3 else "v", "claim_refs": claim_refs},
            {"id": second_id, "kind": "vector", "dimension": 2, "value": item["vectors"][1], "role": "vector_b", "label": "b", "claim_refs": claim_refs},
        ])
        relation_id = f"rel.direction-examples.{index}"
        relations.append({"id": relation_id, "kind": item["relation"], "source_ref": first_id, "target_ref": second_id, "parameters": {}, "claim_refs": claim_refs})
        stage_id = f"stage.direction-examples.{index}"
        stages.append({
            "id": stage_id, "title": item["title"], "caption": "", "layout": "overlay",
            # The first, second and fourth cases each explain one vector.
            # Keep the comparison target in the semantic graph but out of the
            # pane, so a vector is never drawn twice on top of itself.
            "input_entity_refs": [first_id, second_id] if index == 3 else [first_id], "output_entity_refs": [],
            "relation_refs": [relation_id], "expected_invariants": [f"direction example {index}"],
        })
        examples[index - 1]["claim_refs"] = claim_refs
        # ``vectors`` and ``relation`` are local construction hints only; the
        # artifact schema exposes typed operands through ``given``.
        examples[index - 1].pop("vectors", None)
        examples[index - 1].pop("relation", None)
        cases.append({
            "id": f"case.direction-examples.{index}", "topic_id": "ch01.vector.direction-examples",
            "example_ref": item["id"], "claim_refs": claim_refs, "stage_refs": [stage_id],
            "purpose": item["title"],
        })
    explanation["worked_examples"] = examples
    visual.update({"scene_kind": "2d", "entities": entities, "relations": relations, "stages": stages})
    explanation["sections"] = [
        {"id": section_id, "title": section_id, "text": "", "claim_refs": claim_refs}
        for section_id in ("definition", "formula", "worked_examples", "geometric_meaning")
    ]
    explanation["case_layout"] = {"default_pane_count": 1, "cases": cases}


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
            # 缩放后的 a 用调色板的 transformed_a（紫）而不是默认的回退灰，两个向量
            # 在同一射线上要一眼分得开。
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
        # 线性组合按三步展示：a、b → a、b 与 2a、-b → 组合结果；首屏并排三个窗格。
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
    # Section 1.5 draws a construction, not a pair of free arrows.  Each spec
    # fixes the two lecture inputs (a, b) and the readable label the 2D pane
    # shows, so the picture and the recomputed numbers come from one source.
    "ch01.proof.midline": {
        # 案例点刻意避开坐标轴：$B$、$C$ 都取在坐标轴之外，只有讲义规定的
        # 原点 $A$ 落在坐标原点上，图形不会退化成贴轴的直角三角形。
        "a": [3.6, 1.2],
        "b": [1.2, 3.2],
        "case_title": "案例：三角形中位线定理",
        "invariant": r"$DE$ 与 $BC$ 平行且长度恒为 $BC$ 的一半",
        "title": "三角形中位线定理",
        "summary": r"三角形两边中点的连线平行于第三边，且长度是第三边的一半。",
        "definition": r"三角形两边中点的连线平行于第三边，且长度是第三边的一半。",
        "formula": r"\overrightarrow{DE}=\frac12(\boldsymbol b-\boldsymbol a)=\frac12\overrightarrow{BC}",
        "derivation": [
            r"取 $A$ 为原点。设 $\overrightarrow{AB}=\boldsymbol a$，$\overrightarrow{AC}=\boldsymbol b$。",
            r"$D$ 是 $AB$ 中点 $\rightarrow \overrightarrow{AD}=\frac12\boldsymbol a$",
            r"$E$ 是 $AC$ 中点 $\rightarrow \overrightarrow{AE}=\frac12\boldsymbol b$",
            r"$\overrightarrow{DE}=\overrightarrow{AE}-\overrightarrow{AD}=\frac12\boldsymbol b-\frac12\boldsymbol a=\frac12(\boldsymbol b-\boldsymbol a)$",
            r"又 $\overrightarrow{BC}=\overrightarrow{AC}-\overrightarrow{AB}=\boldsymbol b-\boldsymbol a$",
            r"所以 $\overrightarrow{DE}=\frac12\overrightarrow{BC}$，即 $DE$ 平行于 $BC$，且长度是 $BC$ 的一半。",
        ],
        "geometric_meaning": r"全程没有添加一条辅助线，没有用到任何全等或相似三角形。这就是向量方法的威力——几何归约为代数。",
        "section_titles": {
            "definition": "定义",
            "derivation": "向量证明",
            "worked_examples": "案例",
            "geometric_meaning": "注意",
        },
        # 讲义把中位线定理写成一个先后过程，于是案例也逐步展开：一个窗格一步，
        # 窗格数与步骤数一致，再一步步拼出完整证明。
        "steps": [
            r"第一步：取 $A$ 为原点，设 $\overrightarrow{AB}=\boldsymbol a$、$\overrightarrow{AC}=\boldsymbol b$",
            r"第二步：两边的中点 $D$、$E$",
            r"第三步：中位线 $\overrightarrow{DE}=\frac12(\boldsymbol b-\boldsymbol a)$",
            r"第四步：$\overrightarrow{DE}=\frac12\overrightarrow{BC}$，平行且半长",
        ],
        "example_kind": "scalar_multiple",
        "example_given": [0.5, [-2.4, 2.0]],
        "example_result": [-1.2, 1.0],
        "example_check": "scalar_multiple",
        "example_calculation": [
            r"$$\boldsymbol a=(3.6,\ 1.2),\qquad \boldsymbol b=(1.2,\ 3.2)$$",
            r"$$\overrightarrow{BC}=\boldsymbol b-\boldsymbol a=(-2.4,\ 2)$$",
            r"$$\overrightarrow{AD}=\frac12\boldsymbol a=(1.8,\ 0.6),\qquad \overrightarrow{AE}=\frac12\boldsymbol b=(0.6,\ 1.6)$$",
            r"$$\overrightarrow{DE}=\overrightarrow{AE}-\overrightarrow{AD}=(-1.2,\ 1)=\frac12\overrightarrow{BC}$$",
        ],
    },
    "ch01.proof.centroid": {
        "a": [4.5, 0.0],
        "b": [1.5, 3.0],
        "case_title": "案例一：三条中线交于重心",
        "invariant": r"重心把每条中线都分成 $2:1$ 的两段",
        "title": "三角形重心定理",
        "summary": r"三角形三条中线交于一点，重心到顶点的距离是到对边中点距离的 $2$ 倍。",
        "definition": r"取 $A$ 为原点，设 $\overrightarrow{AB}=\boldsymbol a$、$\overrightarrow{AC}=\boldsymbol b$；三条中线交于重心 $G$。",
        "formula": r"\overrightarrow{AG}=\frac13(\boldsymbol a+\boldsymbol b)",
        "derivation": [
            r"边 $BC$ 的中点位置向量为 $\overrightarrow{AD}=\frac12(\boldsymbol a+\boldsymbol b)$。",
            r"重心在中线上且 $\overrightarrow{AG}=\frac23\overrightarrow{AD}$，所以 $\overrightarrow{AG}=\frac13(\boldsymbol a+\boldsymbol b)$。",
            r"三条中线的表达式对称，因此它们交于同一个点 $G$。",
        ],
        "geometric_meaning": r"重心是三个顶点位置向量的平均，落在每条中线的三等分点上；图中三条中线交于 $G$，且 $AG:GD=2:1$。",
        "example_kind": "scalar_multiple",
        "example_given": [1.0 / 3.0, [6.0, 3.0]],
        "example_result": [2.0, 1.0],
        "example_check": "scalar_multiple",
        "example_calculation": [
            r"$$\boldsymbol a=(4.5,\ 0),\qquad \boldsymbol b=(1.5,\ 3)$$",
            r"$$\boldsymbol a+\boldsymbol b=(6,\ 3)$$",
            r"$$\overrightarrow{AG}=\frac13(\boldsymbol a+\boldsymbol b)=\frac13(6,\ 3)=(2,\ 1)$$",
        ],
    },
    "ch01.proof.parallelogram-diagonals": {
        "a": [3.2, 0.4],
        "b": [1.0, 2.6],
        "case_title": "案例一：两条对角线的中点重合",
        "invariant": r"两条对角线拥有同一个中点",
        "title": "平行四边形对角线互相平分",
        "summary": r"平行四边形的两条对角线互相平分：它们的中点位置向量相同。",
        "definition": r"取 $A$ 为原点，设 $\overrightarrow{AB}=\boldsymbol a$、$\overrightarrow{AD}=\boldsymbol b$，则第四个顶点 $C=\boldsymbol a+\boldsymbol b$。",
        "formula": r"\frac{\boldsymbol a+\boldsymbol b}{2}=\frac{\boldsymbol a+(\boldsymbol a+\boldsymbol b-\boldsymbol a)}{2}",
        "derivation": [
            r"对角线 $AC$ 的中点为 $\frac12(\boldsymbol a+\boldsymbol b)$。",
            r"对角线 $BD$ 的两个端点位置向量为 $\boldsymbol a$ 与 $\boldsymbol a+\boldsymbol b$，其中点也是 $\frac{\boldsymbol a+(\boldsymbol a+\boldsymbol b)}{2}=\frac12(\boldsymbol a+\boldsymbol b)$。",
            r"两个中点重合，所以两条对角线互相平分。",
        ],
        "geometric_meaning": r"两条对角线在中点相遇：图中 $M(AC)$ 与 $M(BD)$ 是同一个点，位置向量都是 $\frac12(\boldsymbol a+\boldsymbol b)$。",
        "example_kind": "scalar_multiple",
        "example_given": [0.5, [4.2, 3.0]],
        "example_result": [2.1, 1.5],
        "example_check": "scalar_multiple",
        "example_calculation": [
            r"$$\boldsymbol a=(3.2,\ 0.4),\qquad \boldsymbol b=(1,\ 2.6)$$",
            r"$$\boldsymbol a+\boldsymbol b=(4.2,\ 3)$$",
            r"$$M_{AC}=M_{BD}=\frac12(\boldsymbol a+\boldsymbol b)=\frac12(4.2,\ 3)=(2.1,\ 1.5)$$",
        ],
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
    section_ids = ("definition", "formula", "derivation", "worked_examples", "geometric_meaning")
    # 讲义的小节标题就是软件里的分节标题：命题写成“定义”，向量证明写成
    # “向量证明”，不再出现“定义与公式”这类拼接出来的名字。
    section_titles = {
        "definition": "定义",
        "formula": "公式",
        "derivation": "向量证明",
        "worked_examples": "案例",
        "geometric_meaning": "几何意义",
    }
    section_titles.update(dict(spec.get("section_titles", {})))
    explanation.update(
        {
            "title": spec["title"],
            "summary": spec["summary"],
            "definition": spec["definition"],
            "formula": spec["formula"],
            "derivation": list(spec["derivation"]),
            "geometric_meaning": spec["geometric_meaning"],
            "worked_examples": [example],
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
    # The pane chrome already shows the case purpose; the ``stage.case.``
    # prefix keeps the compiler from repeating it as an in-scene title label.
    steps = list(spec.get("steps", ()) or ())
    if steps:
        # 讲义把这一节写成先后过程时，就一步一个窗格地展开，窗格数等于步骤数。
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
        cases = [
            {
                "id": f"case.proof.{topic_id}", "topic_id": topic_id,
                "example_ref": example["id"], "claim_refs": claim_refs,
                "stage_refs": [stage_id], "purpose": spec["case_title"],
            }
        ]
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
    explanation["case_layout"] = {
        "default_pane_count": default_pane_count,
        "cases": cases,
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
        "ch01.inner.applications": (
            "内积的长度、正交与夹角应用", "内积可计算长度、判定正交并求两个非零向量的夹角。",
            r"对向量 $\boldsymbol a,\boldsymbol b$，长度由自身内积确定；当内积为零时两向量正交。",
            r"\lvert\boldsymbol a\rvert=\sqrt{\boldsymbol a\cdot\boldsymbol a},\qquad \boldsymbol a\cdot\boldsymbol b=0\Longleftrightarrow\boldsymbol a\perp\boldsymbol b,\qquad \cos\theta=\frac{\boldsymbol a\cdot\boldsymbol b}{\lvert\boldsymbol a\rvert\,\lvert\boldsymbol b\rvert}",
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
        "ch01.projection.properties": (
            "投影的可加性与齐次性", "固定目标方向的正交投影满足加性和齐次性。",
            r"固定非零方向 $\boldsymbol u$，对向量和数乘分别考察同一投影算子。",
            r"\operatorname{proj}_{\boldsymbol u}(\boldsymbol v_1+\boldsymbol v_2)=\operatorname{proj}_{\boldsymbol u}\boldsymbol v_1+\operatorname{proj}_{\boldsymbol u}\boldsymbol v_2,\qquad \operatorname{proj}_{\boldsymbol u}(k\boldsymbol v)=k\operatorname{proj}_{\boldsymbol u}\boldsymbol v",
        ),
        "ch01.projection.force": (
            "坐标轴与斜面上的力分解", "力沿指定方向的有效分量由正交投影给出。",
            r"设力向量为 $\boldsymbol F$，目标方向为非零向量 $\boldsymbol u$；沿方向分量为投影，垂直分量为残差。",
            r"\boldsymbol F=\boldsymbol F_{\parallel}+\boldsymbol F_{\perp},\qquad \boldsymbol F_{\parallel}=\operatorname{proj}_{\boldsymbol u}\boldsymbol F",
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
            r"定义 1.10（内积 / 点积 — 几何定义） 设 $\boldsymbol a,\boldsymbol b$ 为两个向量，"
            r"其夹角为 $\theta$（$0\leq\theta\leq\pi$），则："
            "\n\n"
            r"$$\boldsymbol a\cdot\boldsymbol b=\lvert\boldsymbol a\rvert\cdot\lvert\boldsymbol b\rvert\cdot\cos(\theta)$$"
            "\n\n"
            r"定义 1.11（内积 — 代数计算） 在 $\mathbb R^2$ 中，设 "
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
        # 讲义 1.4.1 的正文依次给出「定义 1.13（投影向量）」「定理 1.6（投影公式）」
        # 与「公式的含义」，公式就写在定义块内，因此不再另立「公式」分节；
        # 「从 v 的终点向 u 所在直线作垂线，垂足对应的向量」按讲义位置并入定义块。
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
        "ch01.inner.applications": [{"id": "example.inner.length", "title": "案例一：由内积求长度", "kind": "inner_product", "given": [[3, 4], [3, 4]], "result": 25.0, "calculation": [r"$$\lvert\boldsymbol a\rvert=\sqrt{\boldsymbol a\cdot\boldsymbol a}=\sqrt{25}=5$$"], "checks": [{"name": "dot", "expected": 25.0, "tolerance": 1e-9}]}, {"id": "example.inner.orthogonal", "title": "案例二：正交判定", "kind": "inner_product", "given": [[2, 0], [0, 3]], "result": 0.0, "calculation": [r"$$\boldsymbol a\cdot\boldsymbol b=0\Longrightarrow\boldsymbol a\perp\boldsymbol b$$"], "checks": [{"name": "dot", "expected": 0.0, "tolerance": 1e-9}]}, {"id": "example.inner.angle", "title": "案例三：由内积求夹角", "kind": "inner_product", "given": [[1, 0], [1, 1]], "result": 1.0, "calculation": [r"$$\boldsymbol a\cdot\boldsymbol b=1,\qquad \cos\theta=\frac1{\sqrt2},\qquad \theta=45^\circ$$"], "checks": [{"name": "dot", "expected": 1.0, "tolerance": 1e-9}]}],
        "ch01.inner.cauchy-schwarz": [{"id": "example.cauchy.bound", "title": "案例一：投影界", "kind": "inner_product", "given": [[3, 4], [1, 0]], "result": 3.0, "calculation": [r"$$\lvert\boldsymbol a\cdot\boldsymbol b\rvert=3\leq5=\lvert\boldsymbol a\rvert\,\lvert\boldsymbol b\rvert$$"], "checks": [{"name": "dot", "expected": 3.0, "tolerance": 1e-9}]}],
        # 讲义 1.4.1 只给出定义 1.13 与定理 1.6，没有数值例，因此按讲义的定义自己构造案例：
        # 取 u=(2,1)、v=(3,4)（两条向量的终点都不落在坐标轴上），则
        # α=(v·u)/(u·u)=(3×2+4×1)/(2×2+1×1)=10/5=2，投影 p=2u=(4,2)、残差 r=v-p=(-1,2)，且 r·u=0。
        # 案例按数学流程拆成三步，每步一个窗格：给出 u 与 v → 作垂线得投影与垂足 → 残差与 u 正交。
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
        "ch01.projection.properties": [{"id": "example.projection.add", "title": "案例一：投影的可加性", "kind": "projection", "given": [[3, 4], [1, 0]], "result": [3.0, 0.0], "calculation": [r"$$\operatorname{proj}_{(1,0)}(3,4)=(3,0)$$"], "checks": [{"name": "projection", "expected": [3.0, 0.0], "tolerance": 1e-9}]}, {"id": "example.projection.homogeneous", "title": "案例二：投影的齐次性", "kind": "projection", "given": [[6, 8], [1, 0]], "result": [6.0, 0.0], "calculation": [r"$$\operatorname{proj}_{(1,0)}(6,8)=(6,0)=2(3,0)$$"], "checks": [{"name": "projection", "expected": [6.0, 0.0], "tolerance": 1e-9}]}],
        "ch01.projection.force": [{"id": "example.force.axis", "title": "案例一：坐标轴分解", "kind": "projection", "given": [[5, 0], [1, 0]], "result": [5.0, 0.0], "calculation": [r"$$\operatorname{proj}_{(1,0)}(5,0)=(5,0)$$"], "checks": [{"name": "projection", "expected": [5.0, 0.0], "tolerance": 1e-9}]}, {"id": "example.force.zero", "title": "案例二：垂直方向分量", "kind": "projection", "given": [[5, 0], [0, 1]], "result": [0.0, 0.0], "calculation": [r"$$\operatorname{proj}_{(0,1)}(5,0)=(0,0)$$"], "checks": [{"name": "projection", "expected": [0.0, 0.0], "tolerance": 1e-9}]}, {"id": "example.force.calc", "title": "案例三：计算层投影", "kind": "projection", "given": [[3, 4], [1, 0]], "result": [3.0, 0.0], "calculation": [r"$$\operatorname{proj}_{(1,0)}(3,4)=(3,0)$$"], "checks": [{"name": "projection", "expected": [3.0, 0.0], "tolerance": 1e-9}]}, {"id": "example.force.slope", "title": "案例四：斜面方向有效分力", "kind": "projection", "given": [[10, 20], [3, 1]], "result": [15.0, 5.0], "calculation": [r"$$\operatorname{proj}_{(3,1)}(10,20)=(15,5)$$"], "checks": [{"name": "projection", "expected": [15.0, 5.0], "tolerance": 1e-9}]}],
        "ch01.proof.midline": [{"id": "example.proof.midline", "title": "案例一：中位线", "kind": "vector_addition", "given": [[2, 0], [0, 2]], "result": [2.0, 2.0], "calculation": [r"$$\overrightarrow{DE}=\frac12(\boldsymbol b-\boldsymbol a)=\frac12\overrightarrow{BC}$$"], "checks": [{"name": "sum", "expected": [2.0, 2.0], "tolerance": 1e-9}]}],
        "ch01.proof.centroid": [{"id": "example.proof.centroid", "title": "案例一：三角形重心", "kind": "vector_addition", "given": [[1, 0], [0, 1]], "result": [1.0, 1.0], "calculation": [r"$$\overrightarrow{AG}=\frac13(\boldsymbol a+\boldsymbol b)$$"], "checks": [{"name": "sum", "expected": [1.0, 1.0], "tolerance": 1e-9}]}],
        "ch01.proof.parallelogram-diagonals": [{"id": "example.proof.parallelogram", "title": "案例一：对角线中点", "kind": "vector_addition", "given": [[2, 1], [1, 3]], "result": [3.0, 4.0], "calculation": [r"$$M_{AC}=M_{BD}=\frac12(\boldsymbol a+\boldsymbol b)$$"], "checks": [{"name": "sum", "expected": [3.0, 4.0], "tolerance": 1e-9}]}],
    }
    examples = examples_map[topic_id]
    if topic_id == "ch01.inner.definitions":
        # 讲义 1.3.1 只说明“两种定义给出同一个数”，案例按两步流程并排展示：
        # 第一步走几何定义（投影长度 × |a|），第二步走代数定义（坐标分量相乘相加）。
        # 两个步骤共用同一对向量 a=(2,1)、b=(1,2)，三个端点都不落在坐标轴上。
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
        "ch01.inner.applications": r"内积的三个结果分别对应向量长度、垂直关系和夹角；案例一、二、三按此顺序展示。",
        "ch01.inner.cauchy-schwarz": r"内积的绝对值不超过长度乘积，几何上表示带符号投影的绝对值不超过被投影向量的长度；案例一给出严格不等式。",
        # 1.4.1 的「从 v 的终点向 u 所在直线作垂线，垂足对应的向量」按讲义位置
        # 并入「定义」分节，此处不再单列几何意义。
        "ch01.projection.definition": "",
        "ch01.projection.properties": r"固定方向的投影保持向量加法和数乘，因此投影后的分量可按相同线性规则组合；两个案例分别核验加性和齐次性。",
        "ch01.projection.force": r"力向量分解为沿坐标轴或斜面方向的有效分量与正交分量；四个案例展示目标方向改变时投影的变化。",
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
                r"性质 1.1（交换律 / 对称性）：对任意向量 $\boldsymbol a,\boldsymbol b$，"
                "\n\n"
                r"$$\boldsymbol a\cdot\boldsymbol b=\boldsymbol b\cdot\boldsymbol a$$"
                "\n\n"
                r"证明：按坐标展开 $\boldsymbol a\cdot\boldsymbol b=a_1b_1+a_2b_2$，两个分量只交换相乘顺序，"
                r"所以 $a_1b_1+a_2b_2=b_1a_1+b_2a_2=\boldsymbol b\cdot\boldsymbol a$。"
            ),
            (
                r"性质 1.2（分配律 / 双线性1）：对任意向量 $\boldsymbol a,\boldsymbol b,\boldsymbol c$，"
                "\n\n"
                r"$$\boldsymbol a\cdot(\boldsymbol b+\boldsymbol c)=\boldsymbol a\cdot\boldsymbol b+\boldsymbol a\cdot\boldsymbol c$$"
                "\n\n"
                r"证明：$\boldsymbol a\cdot(\boldsymbol b+\boldsymbol c)=a_1(b_1+c_1)+a_2(b_2+c_2)"
                r"=(a_1b_1+a_2b_2)+(a_1c_1+a_2c_2)=\boldsymbol a\cdot\boldsymbol b+\boldsymbol a\cdot\boldsymbol c$。"
            ),
            (
                r"性质 1.3（数乘结合律 / 双线性2）：对任意实数 $k$ 与向量 $\boldsymbol a,\boldsymbol b$，"
                "\n\n"
                r"$$(k\boldsymbol a)\cdot\boldsymbol b=k\,(\boldsymbol a\cdot\boldsymbol b)=\boldsymbol a\cdot(k\boldsymbol b)$$"
                "\n\n"
                r"证明：$(k\boldsymbol a)\cdot\boldsymbol b=(ka_1)b_1+(ka_2)b_2=k(a_1b_1+a_2b_2)=k\,(\boldsymbol a\cdot\boldsymbol b)$。"
            ),
            (
                r"性质 1.4（正定性）：对任意向量 $\boldsymbol a$，"
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
        # 分节标题照讲义原文：1.3.1 只有「定义」与「内积的基本性质」两组标题，
        # 自造的「公式」「几何意义」分节不再出现。
        explanation["sections"] = [
            {"id": "definition", "title": "定义", "text": "", "claim_refs": claim_refs},
            {"id": "worked_examples", "title": "数学案例", "text": "", "claim_refs": claim_refs},
            {"id": "invariants", "title": "内积的基本性质", "text": "", "claim_refs": claim_refs},
        ]
    explanation["derivation"] = derivations.get(topic_id, [])
    if explanation["derivation"]:
        explanation["sections"].insert(2, {"id": "derivation", "title": "derivation", "text": "", "claim_refs": claim_refs})
    if topic_id == "ch01.projection.definition":
        # 分节标题照讲义原文：1.4.1 只有「定义 1.13 + 定理 1.6 + 公式的含义」与
        # 「##### 定理 1.6（投影公式）的推导」两组标题，自造的「公式」「几何意义」
        # 分节不再出现（垂足那句已按讲义位置并入定义）。
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
            # 1.3.1 的核心是“两种定义给出同一个内积值”：把 b 正交投影到 a，
            # 投影长度 |b|cosθ 乘以 |a| 就是几何定义的值，与按坐标分量求和一致。
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
            # 带 rel.case. 前缀的 orientation 关系只会登记别名、不落笔画；夹角弧需要
            # 用独立命名的关系，才能在案例窗格里真正画出来。
            angle_rid = f"rel.angle.{topic_id}.{suffix}"
            relations.extend([
                # 投影是辅助构造，按讲义习惯画成虚线（compiler 会转成 geometry.projection 的 style）。
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
        # 讲义 1.4.1 的数学流程分三步：给出方向与向量 → 作垂线得到投影与垂足 →
        # 给出残差并验证它与 u 正交。三步各占一个窗格，所以每一步只保留该步真正
        # 出现的实体与关系，否则三个窗格会画成同一张图。
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
        # 1.3.1 的两个步骤并排：第一步（几何定义）只给 a、b 与夹角，投影留到第二步
        # （代数定义）说明「|a| 乘投影长度」，否则两个窗格会画成同一张图。
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
    "ch01.vector.coordinate-system": {
        "definition": r"在三维直角坐标系中，用三个有序分量表示从原点出发的向量：$\boldsymbol v=(x,y,z)$。坐标轴的正向按右手系约定。",
        "formula": r"\boldsymbol v=x\boldsymbol e_1+y\boldsymbol e_2+z\boldsymbol e_3",
        "geometry": r"$\boldsymbol e_1,\boldsymbol e_2,\boldsymbol e_3$ 分别给出三个坐标轴的正方向。向量的终点坐标就是沿这三个基向量的分量。",
        "case": ("案例一：三维分量", [r"$$\boldsymbol v=(1,2,2),\qquad \lvert\boldsymbol v\rvert=\sqrt{1^2+2^2+2^2}=3$$"]),
    },
    "ch01.vector.direction-examples": {
        "definition": r"非零向量的方向由它所在的射线确定。二维向量 $(x,y)$ 所在象限由 $x,y$ 的符号确定。",
        "formula": r"\boldsymbol a\cdot\boldsymbol b=\lvert\boldsymbol a\rvert\lvert\boldsymbol b\rvert\cos\theta",
        "geometry": r"两个向量的夹角 $\theta$ 取从同一起点出发的较小夹角；内积为正、零、负分别对应锐角、直角、钝角。",
        "case": ("案例一：夹角与象限", [r"$$\boldsymbol a=(1,1),\quad \boldsymbol b=(-1,2),\quad \boldsymbol a\cdot\boldsymbol b=1>0$$", r"$$\therefore\ 0<\theta<90^\circ,\qquad \boldsymbol b\text{ 位于第二象限}$$"]),
    },
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
    "ch01.inner.applications": {
        "definition": r"内积可用于计算长度、判定正交和计算夹角。",
        "formula": r"\lvert\boldsymbol a\rvert=\sqrt{\boldsymbol a\cdot\boldsymbol a},\qquad \cos\theta=\frac{\boldsymbol a\cdot\boldsymbol b}{\lvert\boldsymbol a\rvert\lvert\boldsymbol b\rvert}",
        "geometry": r"$\boldsymbol a\cdot\boldsymbol b=0$ 当且仅当非零向量 $\boldsymbol a,\boldsymbol b$ 垂直；夹角由同起点的两条射线确定。",
        "case": ("案例一：正交判定", [r"$$\boldsymbol a=(2,0),\quad \boldsymbol b=(0,3),\quad \boldsymbol a\cdot\boldsymbol b=0$$", r"$$\therefore\ \boldsymbol a\perp\boldsymbol b$$"]),
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
    "ch01.projection.properties": {
        "definition": r"固定目标方向后的正交投影是线性变换。",
        "formula": r"P(\boldsymbol v+\boldsymbol w)=P\boldsymbol v+P\boldsymbol w,\qquad P(\lambda\boldsymbol v)=\lambda P\boldsymbol v",
        "geometry": r"先相加再投影，或分别投影后相加，终点落在同一目标直线上；数乘只沿该直线改变投影长度和方向。",
        "case": ("案例一：x 轴投影", [r"$$P(3,4)=(3,0),\qquad P(1,2)=(1,0)$$", r"$$P\bigl((3,4)+(1,2)\bigr)=(4,0)=(3,0)+(1,0)$$"]),
    },
    "ch01.projection.force": {
        "definition": r"力的分解把力向量表示为沿选定方向的分量与垂直于该方向的分量之和。",
        "formula": r"\boldsymbol F=\boldsymbol F_{\parallel}+\boldsymbol F_{\perp}",
        "geometry": r"以斜面方向为投影方向时，$\boldsymbol F_{\parallel}$ 沿斜面，$\boldsymbol F_{\perp}$ 沿法线；两分量构成直角三角形。",
        "case": ("案例一：斜向分量", [r"$$\boldsymbol F=(3,4),\quad \boldsymbol u=(1,1),\quad \operatorname{proj}_{\boldsymbol u}\boldsymbol F=\left(\frac72,\frac72\right)$$"]),
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
    "ch02.batch.projection": {
        "definition": r"单位向量 $\boldsymbol u$ 所在直线上的正交投影可写成矩阵 $P$。",
        "formula": r"P=\boldsymbol u\boldsymbol u^{\mathsf T},\qquad P\boldsymbol v=(\boldsymbol u\cdot\boldsymbol v)\boldsymbol u",
        "geometry": r"同一个投影矩阵把每一个输入终点沿垂线压到 $\boldsymbol u$ 所在直线；不同输入共享同一目标方向。",
        "case": ("案例一：投影矩阵", [r"$$\boldsymbol u=(1,0),\quad P=\begin{pmatrix}1&0\\0&0\end{pmatrix},\quad \boldsymbol v=(3,4)$$", r"$$P\boldsymbol v=(3,0)$$"]),
    },
    "ch02.matrix.additive-distributivity": {
        "definition": r"同型矩阵可以逐元素相加和数乘；矩阵表示的线性变换满足分配律。",
        "formula": r"(A+B)\boldsymbol x=A\boldsymbol x+B\boldsymbol x,\qquad (\lambda A)\boldsymbol x=\lambda(A\boldsymbol x)",
        "geometry": r"先将两个变换的输出相加，与先将矩阵相加后作用于同一向量，得到相同终点。",
        "case": ("案例一：分配律", [r"$$A+B=\begin{pmatrix}6&8\\10&12\end{pmatrix},\quad \boldsymbol x=(1,1)^{\mathsf T}$$", r"$$(A+B)\boldsymbol x=(14,22)^{\mathsf T}$$"]),
    },
    "ch02.matrix.row-column": {
        "definition": r"矩阵乘向量既可逐行与向量作内积，也可把矩阵列向量按输入分量作线性组合。",
        "formula": r"(A\boldsymbol x)_i=\operatorname{row}_i(A)\cdot\boldsymbol x=\sum_jx_jA_{:j}",
        "derivation": [r"逐行计算给出第 $i$ 个输出分量：$(A\boldsymbol x)_i=\sum_jA_{ij}x_j$。", r"按列收集同一系数，得到 $A\boldsymbol x=x_1A_{:1}+\cdots+x_nA_{:n}$。"],
        "geometry": r"列视角说明输入的每个坐标如何加权基向量的像；行视角说明每个输出坐标怎样从输入读出。两种计算定位同一个输出点。",
        "case": ("案例一：行列两种计算", [r"$$A=\begin{pmatrix}1&2\\3&4\end{pmatrix},\quad \boldsymbol x=(1,2)^{\mathsf T}$$", r"$$A\boldsymbol x=(5,11)^{\mathsf T}=1\begin{pmatrix}1\\3\end{pmatrix}+2\begin{pmatrix}2\\4\end{pmatrix}$$"]),
    },
    "ch02.matrix.transformed-grid": {
        "definition": r"线性变换 $A$ 完全由标准基向量的像 $A\boldsymbol e_1,A\boldsymbol e_2$ 确定。",
        "formula": r"A\boldsymbol x=x_1A\boldsymbol e_1+x_2A\boldsymbol e_2",
        "geometry": r"单位方格的边由 $\boldsymbol e_1,\boldsymbol e_2$ 变为 $A\boldsymbol e_1,A\boldsymbol e_2$；因此整张坐标网格随之拉伸、旋转或剪切。",
        "case": ("案例一：两列决定像", [r"$$A=\begin{pmatrix}2&1\\0&1\end{pmatrix},\quad A\boldsymbol e_1=(2,0),\quad A\boldsymbol e_2=(1,1)$$", r"$$A(1,2)^{\mathsf T}=(4,2)^{\mathsf T}$$"]),
    },
    "ch02.matrix.stretch-rotate-scale": {
        "definition": r"对角矩阵沿坐标轴缩放，旋转矩阵改变方向；一般矩阵可以组合这些线性效应。",
        "formula": r"\begin{pmatrix}s_1&0\\0&s_2\end{pmatrix}\begin{pmatrix}x\\y\end{pmatrix}=\begin{pmatrix}s_1x\\s_2y\end{pmatrix}",
        "geometry": r"矩阵使整个平面同步变形：平行线仍平行，原点保持不动；基向量的像决定拉伸和旋转后的网格方向。",
        "case": ("案例一：非均匀拉伸", [r"$$A=\begin{pmatrix}2&0\\0&1\end{pmatrix},\quad \boldsymbol x=(1,2)^{\mathsf T},\quad A\boldsymbol x=(2,2)^{\mathsf T}$$"]),
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
    "ch02.subspace.null": {
        "definition": r"零空间由所有被矩阵映到零向量的输入组成。",
        "formula": r"\operatorname{Null}(A)=\{\boldsymbol x\mid A\boldsymbol x=\boldsymbol0\}",
        "geometry": r"落在零空间中的整个方向在变换后收缩到原点；它是变换丢失的输入自由度。",
        "case": ("案例一：y 轴零空间", [r"$$A=\begin{pmatrix}1&0\\0&0\end{pmatrix},\quad \boldsymbol x=(0,2)^{\mathsf T},\quad A\boldsymbol x=(0,0)^{\mathsf T}$$"]),
    },
    "ch02.subspace.column": {
        "definition": r"矩阵的列空间是所有可写成 $A\boldsymbol x$ 的输出向量的集合。",
        "formula": r"\operatorname{Col}(A)=\{A\boldsymbol x\mid \boldsymbol x\in\mathbb R^n\}",
        "geometry": r"列空间描述输出端可到达的区域；若所有输出都落在 x 轴，该列空间就是 x 轴这条直线。",
        "case": ("案例一：x 轴列空间", [r"$$A=\begin{pmatrix}1&0\\0&0\end{pmatrix},\quad A(2,3)^{\mathsf T}=(2,0)^{\mathsf T}$$"]),
    },
    "ch02.subspace.rank-nullity": {
        "definition": r"对 $A:\mathbb R^n\to\mathbb R^m$，输入维数分为保留下来的独立输出方向与被压到零向量的自由方向。",
        "formula": r"\operatorname{rank}(A)+\operatorname{nullity}(A)=n",
        "geometry": r"秩数出输出空间的维数，零化度数出被压缩的输入方向数；二者恰好分完输入空间的维数。",
        "case": ("案例一：二维输入的投影", [r"$$A=\begin{pmatrix}1&0\\0&0\end{pmatrix},\quad \operatorname{rank}(A)=1,\quad \operatorname{nullity}(A)=1$$", r"$$1+1=2$$"]),
    },
    "ch02.high-dimensional.analogy": {
        "definition": r"$m\times n$ 矩阵表示从 $\mathbb R^n$ 到 $\mathbb R^m$ 的线性映射。",
        "formula": r"T(\boldsymbol x)=A\boldsymbol x,\qquad \operatorname{rank}(A)\leq\min(m,n)",
        "geometry": r"二维网格变形是低维代表；在高维中用列空间、零空间和秩描述可到达方向与被压缩方向，而不把二维图形直接当作高维图像。",
        "case": ("案例一：三维对角变换", [r"$$A=\operatorname{diag}(1,2,3),\quad \boldsymbol x=(1,2,3),\quad A\boldsymbol x=(1,4,9)$$"]),
    },
}

# Numeric operands are kept separately from prose so every displayed formula
# is backed by the same value that the bounded verifier recomputes.  The
# schema stores the operands as arrays (not executable expressions).
_BATCH_NUMERIC: dict[str, tuple[Any, Any]] = {
    "ch01.vector.coordinate-system": ([[1, 2, 2], [1, 2, 2]], 9.0),
    "ch01.vector.direction-examples": ([[1, 1], [-1, 2]], 1.0),
    "ch01.ops.subtraction": ([[4, 3], [-1, -2]], [3.0, 1.0]),
    "ch01.ops.scalar": ([[1, 2], [1, 2]], [2.0, 4.0]),
    "ch01.ops.linear-combination": ([[[1, 0], [0, 1]], [2, 3]], [2.0, 3.0]),
    "ch01.inner.definitions": ([[2, 0], [1, 1]], 2.0),
    "ch01.inner.applications": ([[2, 0], [0, 3]], 0.0),
    "ch01.inner.cauchy-schwarz": ([[3, 4], [1, 0]], 3.0),
    "ch01.projection.definition": ([[3, 4], [1, 0]], [3.0, 0.0]),
    "ch01.projection.properties": ([[3, 4], [1, 0]], [3.0, 0.0]),
    "ch01.projection.force": ([[3, 4], [1, 1]], [3.5, 3.5]),
    "ch01.proof.midline": ([[2, 1], [1, 3]], [3.0, 4.0]),
    "ch01.proof.centroid": ([[1, 0], [0, 1]], [1.0, 1.0]),
    "ch01.proof.parallelogram-diagonals": ([[2, 1], [1, 3]], [3.0, 4.0]),
    "ch02.batch.inner-products": ([[[1, 0], [0, 1]], [2, 3]], [2.0, 3.0]),
    "ch02.batch.projection": ([[3, 4], [1, 0]], [3.0, 0.0]),
    "ch02.matrix.additive-distributivity": ([[[6, 8], [10, 12]], [1, 1]], [14.0, 22.0]),
    "ch02.matrix.row-column": ([[[1, 2], [3, 4]], [1, 2]], [5.0, 11.0]),
    "ch02.matrix.transformed-grid": ([[[2, 1], [0, 1]], [1, 2]], [4.0, 2.0]),
    "ch02.matrix.stretch-rotate-scale": ([[[2, 0], [0, 1]], [1, 2]], [2.0, 2.0]),
    "ch02.matrix.basis": ([[[1, 1], [0, 1]], [2, 3]], [5.0, 3.0]),
    "ch02.matrix.powers": ([[[2, 0], [0, 1]], [1, 1]], [2.0, 1.0]),
    "ch02.subspace.independence": ([[[1, 0], [0, 1]], [1, 1]], [1.0, 1.0]),
    "ch02.subspace.rank": ([[[1, 2], [2, 4]], [1, 1]], [3.0, 6.0]),
    "ch02.subspace.null": ([[[1, 0], [0, 0]], [0, 2]], [0.0, 0.0]),
    "ch02.subspace.column": ([[[1, 0], [0, 0]], [2, 3]], [2.0, 0.0]),
    "ch02.subspace.rank-nullity": ([[[1, 0], [0, 0]], [0, 2]], [0.0, 0.0]),
    "ch02.high-dimensional.analogy": ([[[1, 0, 0], [0, 2, 0], [0, 0, 3]], [1, 2, 3]], [1.0, 4.0, 9.0]),
}

# These lecture subsections explicitly contain contrasting examples.  They are
# deliberately not forced onto every topic: each entry below corresponds to a
# distinct case in the source lecture and therefore earns its own 2D pane.
_MULTI_CASES: dict[str, tuple[dict[str, Any], ...]] = {
    "ch01.vector.direction-examples": (
        {"title": "案例一：第一象限方向", "kind": "inner_product", "given": [[1, 1], [1, 1]], "result": 2.0, "check": "dot", "vectors": [[1, 1], [1, 0]], "lines": [r"$$\boldsymbol v=(1,1),\qquad \theta=45^\circ$$"]},
        {"title": "案例二：第二象限方向", "kind": "inner_product", "given": [[-1, 2], [-1, 2]], "result": 5.0, "check": "dot", "vectors": [[-1, 2], [0, 1]], "lines": [r"$$\boldsymbol v=(-1,2),\qquad x<0,\ y>0$$", r"$$\therefore\ \boldsymbol v\text{ 位于第二象限}$$"]},
        {"title": "案例三：锐角判定", "kind": "inner_product", "given": [[1, 1], [-1, 2]], "result": 1.0, "check": "dot", "vectors": [[1, 1], [-1, 2]], "lines": [r"$$\boldsymbol a=(1,1),\quad \boldsymbol b=(-1,2),\quad \boldsymbol a\cdot\boldsymbol b=1>0$$", r"$$\therefore\ 0<\theta<90^\circ$$"]},
    ),
    "ch01.inner.applications": (
        {"title": "案例一：由内积求长度", "kind": "inner_product", "given": [[3, 4], [3, 4]], "result": 25.0, "check": "dot", "vectors": [[3, 4], [3, 0]], "lines": [r"$$\boldsymbol a=(3,4),\qquad \lvert\boldsymbol a\rvert=\sqrt{\boldsymbol a\cdot\boldsymbol a}=5$$"]},
        {"title": "案例二：正交判定", "kind": "inner_product", "given": [[2, 0], [0, 3]], "result": 0.0, "check": "dot", "vectors": [[2, 0], [0, 3]], "lines": [r"$$\boldsymbol a=(2,0),\quad \boldsymbol b=(0,3),\quad \boldsymbol a\cdot\boldsymbol b=0$$", r"$$\therefore\ \boldsymbol a\perp\boldsymbol b$$"]},
        {"title": "案例三：由内积求夹角", "kind": "inner_product", "given": [[1, 0], [1, 1]], "result": 1.0, "check": "dot", "vectors": [[1, 0], [1, 1]], "lines": [r"$$\boldsymbol a=(1,0),\quad \boldsymbol b=(1,1),\quad \cos\theta=\frac1{\sqrt2}$$", r"$$\theta=45^\circ$$"]},
    ),
    "ch01.projection.force": (
        {"title": "案例一：坐标轴分解", "kind": "projection", "given": [[3, 4], [1, 0]], "result": [3.0, 0.0], "check": "projection", "vectors": [[3, 4], [1, 0]], "lines": [r"$$\boldsymbol F=(3,4),\quad \operatorname{proj}_{(1,0)}\boldsymbol F=(3,0)$$", r"$$\boldsymbol F_{\perp}=(0,4)$$"]},
        {"title": "案例二：斜面方向分解", "kind": "projection", "given": [[3, 4], [1, 1]], "result": [3.5, 3.5], "check": "projection", "vectors": [[3, 4], [1, 1]], "lines": [r"$$\boldsymbol F=(3,4),\quad \boldsymbol u=(1,1)$$", r"$$\operatorname{proj}_{\boldsymbol u}\boldsymbol F=\left(\frac72,\frac72\right)$$"]},
    ),
    "ch02.matrix.stretch-rotate-scale": (
        {"title": "案例一：横向拉伸", "kind": "matrix_transform", "given": [[[2, 0], [0, 1]], [1, 0]], "result": [2.0, 0.0], "check": "transformed", "matrix": [[2, 0], [0, 1]], "lines": [r"$$A=\begin{pmatrix}2&0\\0&1\end{pmatrix},\quad A\boldsymbol e_1=(2,0),\quad A\boldsymbol e_2=(0,1)$$"]},
        {"title": "案例二：逆时针旋转", "kind": "matrix_transform", "given": [[[0, -1], [1, 0]], [1, 0]], "result": [0.0, 1.0], "check": "transformed", "matrix": [[0, -1], [1, 0]], "lines": [r"$$R=\begin{pmatrix}0&-1\\1&0\end{pmatrix},\quad R\boldsymbol e_1=(0,1)$$"]},
        {"title": "案例三：列视角计算", "kind": "matrix_transform", "given": [[[1, 2], [3, 4]], [1, 2]], "result": [5.0, 11.0], "check": "transformed", "matrix": [[1, 2], [3, 4]], "lines": [r"$$A=\begin{pmatrix}1&2\\3&4\end{pmatrix},\quad \boldsymbol x=(1,2)^{\mathsf T}$$", r"$$A\boldsymbol x=\begin{pmatrix}5\\11\end{pmatrix}$$"]},
        {"title": "案例四：等比缩放", "kind": "matrix_transform", "given": [[[0.5, 0], [0, 0.5]], [100, 200]], "result": [50.0, 100.0], "check": "transformed", "matrix": [[0.5, 0], [0, 0.5]], "lines": [r"$$A=\begin{pmatrix}0.5&0\\0&0.5\end{pmatrix},\quad A(100,200)^{\mathsf T}=(50,100)^{\mathsf T}$$"]},
    ),
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
    if topic_id == "ch02.high-dimensional.analogy":
        explanation.update({
            "intuition": "把二维或三维的分量计算当作低维示例，再用秩、列空间和零空间描述更高维的同一线性结构。",
            "connections": ["高维向量的分量运算可迁移到内积、投影、秩和零空间。"],
            "analogy_boundary": "二维和三维图形只承担示例作用；n 维结论必须由分量公式和代数不变量验证。",
            "invariants": ["逐坐标计算与矩阵乘法结果一致，且秩不超过输入和输出维数。"],
        })
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
    # A single, independently renderable example keeps the familiar vector-
    # addition layout without turning proof steps into fake extra cases.  The
    # established multi-case lessons retain their own hand-authored layouts.
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
