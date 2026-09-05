"""Complete teaching-artifact payloads shared by focused contract tests."""

from __future__ import annotations

from copy import deepcopy


_COMPOSITION_SPAN_ID = (
    "第2章 矩阵的诞生——向量的批处理 / 2.6 矩阵 $\\times$ 矩阵::1::"
    "sha256:249f825ba9ab6a2d3d042a39fa709e8e6e22611b121cfdf2759e82f232484499"
)


def composition_artifact_payload() -> dict[str, object]:
    """Return an isolated, valid artifact for matrix-composition tests."""
    payload: dict[str, object] = {
        "schema_version": 1,
        "topic_id": "ch02.matrix.composition",
        "revision": 1,
        "status": "draft",
        "source": {
            "source_path": [
                "第2章 矩阵的诞生——向量的批处理",
                "2.6 矩阵 $\\times$ 矩阵",
                "复合变换与 AB ≠ BA",
            ],
            "heading_path": [
                "第2章 矩阵的诞生——向量的批处理",
                "2.6 矩阵 $\\times$ 矩阵",
            ],
            "heading_level": 3,
            "occurrence": 1,
            "excerpt": "矩阵乘法表示变换的复合。",
            "source_hash": "sha256:249f825ba9ab6a2d3d042a39fa709e8e6e22611b121cfdf2759e82f232484499",
            "spans": [
                {
                    "id": _COMPOSITION_SPAN_ID,
                    "heading_path": [
                        "第2章 矩阵的诞生——向量的批处理",
                        "2.6 矩阵 $\\times$ 矩阵",
                    ],
                    "start_line": 767,
                    "end_line": 810,
                    "fingerprint": "sha256:249f825ba9ab6a2d3d042a39fa709e8e6e22611b121cfdf2759e82f232484499",
                    "text": "矩阵乘法表示变换的复合。",
                }
            ],
            "neighboring_titles": [
                "2.5 矩阵 $\\times$ 向量（核心节）",
                "2.7 矩阵与基",
            ],
        },
        "teaching_profile": {
            "minimum_level": 3,
            "required_sections": [
                "definition",
                "formula",
                "derivation",
                "worked_examples",
                "geometric_meaning",
                "pitfalls",
            ],
            "requires_analogy_boundary": False,
        },
        "claims": [
            {
                "id": "claim.composition-order",
                "statement": "先做 B 后做 A 等于 AB。",
                "formula": "(AB)x=A(Bx)",
                "formula_symbols": ["A", "B", "x", "Bx", "ABx"],
                "source_refs": [_COMPOSITION_SPAN_ID],
                "explanation_refs": ["definition", "derivation"],
                "entity_refs": ["x", "Bx", "ABx"],
                "relation_refs": ["B_maps_x_to_Bx", "A_maps_Bx_to_ABx"],
                "stage_refs": ["stage.apply-B", "stage.apply-A"],
            }
        ],
        "connections": [
            {
                "id": "connection.composition-basis",
                "target_topic_id": "ch02.matrix.basis",
                "relation": "prerequisite",
                "description": "复合变换建立在矩阵列与基坐标的表示之上。",
                "claim_refs": ["claim.composition-order"],
            }
        ],
        "explanation": {
            "title": "复合变换与 AB ≠ BA",
            "summary": "矩阵乘法按从右到左的顺序复合变换。",
            "sections": [
                {
                    "id": "definition",
                    "title": "定义",
                    "text": "AB 表示先应用 B，再应用 A。",
                    "claim_refs": ["claim.composition-order"],
                },
                {
                    "id": "derivation",
                    "title": "推导",
                    "text": "先计算 Bx，再计算 A(Bx)。",
                    "claim_refs": ["claim.composition-order"],
                },
            ],
            "symbol_roles": {
                "A": "matrix_a",
                "B": "matrix_b",
                "x": "vector_a",
                "Bx": "transformed_a",
                "ABx": "transformed_b",
            },
        },
        "visual_semantics": {
            "scene_kind": "2d",
            "entities": [
                {
                    "id": "x",
                    "kind": "vector",
                    "dimension": 2,
                    "value": [1, 1],
                    "role": "vector_a",
                    "label": "x",
                    "claim_refs": ["claim.composition-order"],
                },
                {
                    "id": "Bx",
                    "kind": "vector",
                    "dimension": 2,
                    "value": [2, 1],
                    "role": "transformed_a",
                    "label": "Bx",
                    "claim_refs": ["claim.composition-order"],
                },
                {
                    "id": "ABx",
                    "kind": "vector",
                    "dimension": 2,
                    "value": [-1, 2],
                    "role": "transformed_b",
                    "label": "A(Bx)",
                    "claim_refs": ["claim.composition-order"],
                },
            ],
            "relations": [
                {
                    "id": "B_maps_x_to_Bx",
                    "kind": "maps_to",
                    "source_ref": "x",
                    "target_ref": "Bx",
                    "parameters": {"matrix": [[2, 0], [0, 1]]},
                    "claim_refs": ["claim.composition-order"],
                },
                {
                    "id": "A_maps_Bx_to_ABx",
                    "kind": "maps_to",
                    "source_ref": "Bx",
                    "target_ref": "ABx",
                    "parameters": {"matrix": [[0, -1], [1, 0]]},
                    "claim_refs": ["claim.composition-order"],
                },
            ],
            "stages": [
                {
                    "id": "stage.apply-B",
                    "title": "先应用 B",
                    "caption": "x 变为 Bx。",
                    "layout": "sequence",
                    "input_entity_refs": ["x"],
                    "output_entity_refs": ["Bx"],
                    "relation_refs": ["B_maps_x_to_Bx"],
                    "expected_invariants": ["input identity"],
                },
                {
                    "id": "stage.apply-A",
                    "title": "再应用 A",
                    "caption": "Bx 变为 A(Bx)。",
                    "layout": "sequence",
                    "input_entity_refs": ["Bx"],
                    "output_entity_refs": ["ABx"],
                    "relation_refs": ["A_maps_Bx_to_ABx"],
                    "expected_invariants": ["composition order"],
                },
            ],
        },
        "generated": {
            "provider": "fixture",
            "model": "fixture-model",
            "prompt_version": "teaching-artifact-v1",
            "generated_at": "2026-09-05T00:00:00Z",
            "source_hash": "sha256:249f825ba9ab6a2d3d042a39fa709e8e6e22611b121cfdf2759e82f232484499",
            "raw_reply_digest": "sha256:fixture-raw-reply",
            "artifact_digest": "sha256:fixture-artifact",
        },
    }
    return deepcopy(payload)


def projection_artifact_payload(*, with_residual: bool = True) -> dict[str, object]:
    """Return a compact projection artifact for claim/evidence validation.

    The incomplete variant intentionally keeps the residual symbol declaration
    but omits its entity and evidence links, mirroring a model response that
    explains a residual without drawing it.
    """

    payload = composition_artifact_payload()
    payload["topic_id"] = "ch01.projection.definition"
    payload["source"]["source_path"] = [  # type: ignore[index]
        "第1章 从向量到线性组合",
        "1.4 投影",
        "1.4.1 投影的定义",
    ]
    payload["source"]["heading_path"] = [  # type: ignore[index]
        "第1章 从向量到线性组合",
        "1.4 投影",
    ]
    payload["claims"] = [
        {
            "id": "claim.projection-residual",
            "statement": "向量 v 可以分解为投影 p 与正交残差 r。",
            "formula": "v=p+r",
            "formula_symbols": ["u", "v", "p", "H", "r"],
            "source_refs": [_COMPOSITION_SPAN_ID],
            "explanation_refs": ["definition", "decomposition"],
            "entity_refs": ["v", "u", "p", "H", "r"]
            if with_residual
            else ["v", "u", "p", "H"],
            "relation_refs": ["v_projects_to_p", "v_decomposes_p_r", "r_orthogonal_u"]
            if with_residual
            else ["v_projects_to_p"],
            "stage_refs": ["stage.input", "stage.projection", "stage.residual"]
            if with_residual
            else ["stage.input", "stage.projection"],
        }
    ]
    payload["connections"] = [
        {
            "id": "connection.projection-inner-product",
            "target_topic_id": "ch01.inner.definitions",
            "relation": "prerequisite",
            "description": "投影的长度由内积计算。",
            "claim_refs": ["claim.projection-residual"],
        }
    ]
    payload["explanation"] = {
        "title": "投影、垂足与残差",
        "summary": "投影把向量分解为方向分量和正交残差。",
        "sections": [
            {
                "id": "definition",
                "title": "定义",
                "text": "p 是 v 在 u 方向上的投影。",
                "claim_refs": ["claim.projection-residual"],
            },
            {
                "id": "decomposition",
                "title": "分解",
                "text": "v=p+r，且 r 与 u 正交。",
                "claim_refs": ["claim.projection-residual"],
            },
        ],
        "symbol_roles": {
            "u": "direction",
            "v": "vector_a",
            "p": "projection",
            "H": "foot",
            "r": "residual",
        },
    }
    entities = [
        {
            "id": "v",
            "kind": "vector",
            "dimension": 2,
            "value": [2, 2],
            "role": "vector_a",
            "label": "v",
            "claim_refs": ["claim.projection-residual"],
        },
        {
            "id": "u",
            "kind": "vector",
            "dimension": 2,
            "value": [2, 0],
            "role": "direction",
            "label": "u",
            "claim_refs": ["claim.projection-residual"],
        },
        {
            "id": "p",
            "kind": "vector",
            "dimension": 2,
            "value": [2, 0],
            "role": "projection",
            "label": "p",
            "claim_refs": ["claim.projection-residual"],
        },
        {
            "id": "H",
            "kind": "point",
            "dimension": 2,
            "value": [2, 0],
            "role": "foot",
            "label": "H",
            "claim_refs": ["claim.projection-residual"],
        },
    ]
    if with_residual:
        entities.append(
            {
                "id": "r",
                "kind": "vector",
                "dimension": 2,
                "value": [0, 2],
                "role": "residual",
                "label": "r",
                "claim_refs": ["claim.projection-residual"],
            }
        )
    payload["visual_semantics"] = {
        "scene_kind": "2d",
        "entities": entities,
        "relations": [
            {
                "id": "v_projects_to_p",
                "kind": "projects_to",
                "source_ref": "v",
                "target_ref": "p",
                "parameters": {},
                "claim_refs": ["claim.projection-residual"],
            }
        ],
        "stages": [
            {
                "id": "stage.input",
                "title": "输入向量",
                "caption": "给出 v 和方向 u。",
                "layout": "sequence",
                "input_entity_refs": ["v", "u"],
                "output_entity_refs": [],
                "relation_refs": [],
                "expected_invariants": ["input identity"],
            },
            {
                "id": "stage.projection",
                "title": "投影与垂足",
                "caption": "沿 u 方向得到 p 和垂足 H。",
                "layout": "sequence",
                "input_entity_refs": ["v", "u"],
                "output_entity_refs": ["p", "H"],
                "relation_refs": ["v_projects_to_p"],
                "expected_invariants": ["projection direction"],
            },
        ],
    }
    if with_residual:
        payload["visual_semantics"]["relations"].extend(  # type: ignore[index]
            [
                {
                    "id": "v_decomposes_p_r",
                    "kind": "decomposes_into",
                    "source_ref": "v",
                    "target_ref": "p",
                    "parameters": {},
                    "claim_refs": ["claim.projection-residual"],
                },
                {
                    "id": "r_orthogonal_u",
                    "kind": "orthogonal_to",
                    "source_ref": "r",
                    "target_ref": "u",
                    "parameters": {},
                    "claim_refs": ["claim.projection-residual"],
                },
            ]
        )
        payload["visual_semantics"]["stages"].append(  # type: ignore[index]
            {
                "id": "stage.residual",
                "title": "正交残差",
                "caption": "r 是垂直于 u 的残差。",
                "layout": "sequence",
                "input_entity_refs": ["v", "p"],
                "output_entity_refs": ["r"],
                "relation_refs": ["v_decomposes_p_r", "r_orthogonal_u"],
                "expected_invariants": ["orthogonality"],
            }
        )
    return payload
