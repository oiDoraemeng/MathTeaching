from __future__ import annotations

from linear_algebra.teaching.quality import refine_payload
from tests.teaching_fixtures import composition_artifact_payload


def test_vector_addition_refinement_keeps_the_lecture_parallelogram_reading() -> None:
    payload = composition_artifact_payload()
    payload["topic_id"] = "ch01.ops.addition"
    payload["explanation"]["worked_examples"] = [  # type: ignore[index]
        {
            "id": "example.addition",
            "title": "example",
            "kind": "vector_addition",
            "given": [[0, 0], [1, 1]],
            "calculation": [],
            "result": [1, 1],
            "checks": [],
            "claim_refs": ["claim.composition-order"],
        }
    ]

    refined = refine_payload(payload)

    meaning = refined["explanation"]["geometric_meaning"]
    assert "平行四边形" in meaning
    assert "三角形法则" not in meaning
    assert "\\n\\n" not in meaning
    assert "\b" not in meaning
    assert "交换律" in refined["explanation"]["invariants"][0]


def test_vector_addition_refinement_aligns_visual_values_with_the_explanation() -> None:
    payload = composition_artifact_payload()
    payload["topic_id"] = "ch01.ops.addition"
    payload["visual_semantics"]["relations"][0]["id"] = "rel.0.claim.ch01.ops.addition"  # type: ignore[index]

    refined = refine_payload(payload)

    entities = {item["id"]: item for item in refined["visual_semantics"]["entities"]}
    assert entities["flow_a"]["value"] == [3, 1]
    assert entities["flow_b"]["value"] == [1, 2]
    assert entities["flow_sum"]["value"] == [4, 3]
    assert [case["id"] for case in refined["explanation"]["case_layout"]["cases"]] == [
        "case.addition.objects",
        "case.addition.parallelogram",
    ]
    # 数学案例流程默认“全部显示”，两个步骤并排。
    assert refined["explanation"]["case_layout"]["default_pane_count"] == 2


def test_vector_magnitude_refinement_uses_the_confirmed_two_case_reading() -> None:
    payload = composition_artifact_payload()
    payload["topic_id"] = "ch01.vector.magnitude"
    payload["claims"][0]["id"] = "claim.ch01.vector.magnitude"  # type: ignore[index]
    payload["visual_semantics"]["relations"][0]["id"] = "rel.magnitude.original"  # type: ignore[index]

    refined = refine_payload(payload)

    explanation = refined["explanation"]
    assert explanation.get("derivation", []) == []
    assert "intuition" not in explanation
    assert "pitfalls" not in explanation
    assert [example["id"] for example in explanation["worked_examples"]] == [
        "example.magnitude.nonzero",
        "example.magnitude.zero",
    ]
    assert [case["id"] for case in explanation["case_layout"]["cases"]] == [
        "case.magnitude.nonzero",
        "case.magnitude.zero",
    ]
    assert explanation["case_layout"]["default_pane_count"] == 1


def test_point_vector_distinction_refinement_uses_position_and_origin_cases() -> None:
    payload = composition_artifact_payload()
    payload["topic_id"] = "ch01.vector.point-distinction"
    payload["claims"][0]["id"] = "claim.ch01.vector.point-distinction"  # type: ignore[index]

    refined = refine_payload(payload)

    explanation = refined["explanation"]
    assert explanation.get("derivation", []) == []
    assert "intuition" not in explanation
    assert "pitfalls" not in explanation
    assert r"\boldsymbol v=x\boldsymbol e_1+y\boldsymbol e_2" in explanation["formula"]
    assert [example["id"] for example in explanation["worked_examples"]] == [
        "example.point-distinction.location",
        "example.point-distinction.vector",
    ]
    assert [case["id"] for case in explanation["case_layout"]["cases"]] == [
        "case.point-distinction.location",
        "case.point-distinction.vector",
    ]


def test_coordinate_system_refinement_keeps_only_the_lecture_standard_basis_case() -> None:
    payload = composition_artifact_payload()
    payload["topic_id"] = "ch01.vector.coordinate-system"
    payload["claims"][0]["id"] = "claim.ch01.vector.coordinate-system"  # type: ignore[index]

    refined = refine_payload(payload)

    explanation = refined["explanation"]
    assert explanation.get("derivation", []) == []
    assert "intuition" not in explanation
    assert "pitfalls" not in explanation
    assert explanation["formula"] == (
        r"\boldsymbol e_1=(1,0),\qquad \boldsymbol e_2=(0,1),\qquad "
        r"\lvert\boldsymbol e_1\rvert=\lvert\boldsymbol e_2\rvert=1,\qquad "
        r"\boldsymbol e_1\cdot\boldsymbol e_2=0"
    )
    assert [case["id"] for case in explanation["case_layout"]["cases"]] == [
        "case.coordinate-system.standard-basis",
    ]
    assert refined["visual_semantics"]["scene_kind"] == "2d"


def test_direction_examples_refinement_keeps_the_four_lecture_cases() -> None:
    payload = composition_artifact_payload()
    payload["topic_id"] = "ch01.vector.direction-examples"
    payload["claims"][0]["id"] = "claim.ch01.vector.direction-examples"  # type: ignore[index]

    refined = refine_payload(payload)

    explanation = refined["explanation"]
    assert explanation.get("derivation", []) == []
    assert "intuition" not in explanation
    assert "pitfalls" not in explanation
    assert [example["id"] for example in explanation["worked_examples"]] == [
        "example.direction.right-up",
        "example.direction.vertical",
        "example.direction.quadrants",
        "example.direction.northeast",
    ]
    assert [case["id"] for case in explanation["case_layout"]["cases"]] == [
        "case.direction-examples.1",
        "case.direction-examples.2",
        "case.direction-examples.3",
        "case.direction-examples.4",
    ]
    assert explanation["case_layout"]["default_pane_count"] == 1
    stages = refined["visual_semantics"]["stages"]
    assert stages[0]["input_entity_refs"] == ["direction_1_a"]
    assert stages[2]["input_entity_refs"] == ["direction_3_a", "direction_3_b"]


def test_vector_subtraction_refinement_uses_endpoint_difference_case() -> None:
    payload = composition_artifact_payload()
    payload["topic_id"] = "ch01.ops.subtraction"
    payload["claims"][0]["id"] = "claim.ch01.ops.subtraction"  # type: ignore[index]

    refined = refine_payload(payload)

    explanation = refined["explanation"]
    assert explanation.get("derivation", []) == []
    assert "intuition" not in explanation
    assert "pitfalls" not in explanation
    assert explanation["formula"] == r"\boldsymbol a-\boldsymbol b=(x_1-x_2,\,y_1-y_2)"
    # 讲义 1.2.2 与 1.2.1 同构：定义自带公式，几何解释写在定义正下方。
    assert "定义为" in explanation["definition"]
    assert r"$$\boldsymbol a-\boldsymbol b=\boldsymbol a+(-\boldsymbol b)=(x_1-x_2,\,y_1-y_2).$$" in explanation["definition"]
    assert explanation["geometric_meaning"].startswith(r"从 $\boldsymbol b$ 的终点指向 $\boldsymbol a$ 的终点的箭头")
    assert [section["id"] for section in explanation["sections"]] == [
        "definition",
        "formula",
        "worked_examples",
        "geometric_meaning",
    ]
    assert explanation["worked_examples"][0]["result"] == [2.0, -1.0]
    assert explanation["case_layout"]["default_pane_count"] == 2
    assert refined["visual_semantics"]["relations"][0]["source_ref"] == "b"
    assert refined["visual_semantics"]["relations"][0]["target_ref"] == "a"


def test_vector_scalar_refinement_uses_the_lecture_example_as_a_two_step_flow() -> None:
    payload = composition_artifact_payload()
    payload["topic_id"] = "ch01.ops.scalar"
    payload["claims"][0]["id"] = "claim.ch01.ops.scalar"  # type: ignore[index]

    refined = refine_payload(payload)

    explanation = refined["explanation"]
    assert explanation.get("derivation", []) == []
    assert "intuition" not in explanation
    assert "pitfalls" not in explanation
    assert explanation["title"] == "向量数乘"
    # 讲义 1.2.3 的定义自带公式，定义块只写定义本身，公式按讲义写法。
    assert r"k\cdot\boldsymbol a=(kx,ky)" in explanation["definition"]
    assert explanation["formula"] == r"k\boldsymbol a=(kx,ky)"
    geometry = explanation["geometric_meaning"]
    assert geometry.startswith("数乘就是缩放")
    # k 取值表按讲义原表格保留，不压成几句话。
    assert "| $k$ 的值 | 几何效果 |" in geometry
    assert "| $k=-1$ | 反向，长度不变 |" in geometry
    # 定义 1.8（共线）紧随几何解释，保留讲义自己的编号与措辞。
    assert "定义 1.8（共线）" in geometry
    assert r"落在 $\boldsymbol a$ 所在的直线上" in geometry
    assert [section["id"] for section in explanation["sections"]] == [
        "definition",
        "formula",
        "worked_examples",
        "geometric_meaning",
    ]
    assert [example["id"] for example in explanation["worked_examples"]] == [
        "example.scalar.vector",
        "example.scalar.stretch",
    ]
    # 数值例按用户确认改用 a=(2,1)：沿原方向拉伸 2 倍得到 2a=(4,2)。
    assert explanation["worked_examples"][0]["result"] == [2.0, 1.0]
    assert explanation["worked_examples"][1]["calculation"] == [r"$$2\boldsymbol a=2\cdot(2,1)=(4,2)$$"]
    assert explanation["worked_examples"][1]["result"] == [4.0, 2.0]
    assert [case["id"] for case in explanation["case_layout"]["cases"]] == [
        "case.scalar.vector",
        "case.scalar.stretch",
    ]
    assert explanation["case_layout"]["default_pane_count"] == 2
    # 缩放后的 a 用调色板的 transformed_a，不再落到回退的中性灰。
    entities = {entity["id"]: entity for entity in refined["visual_semantics"]["entities"]}
    assert entities["a"]["value"] == [2, 1]
    assert entities["two_a"]["value"] == [4, 2]
    assert entities["two_a"]["role"] == "transformed_a"
    stages = refined["visual_semantics"]["stages"]
    assert stages[0]["expected_invariants"] == ["向量 a 从原点出发"]
    assert stages[1]["expected_invariants"] == ["2a 与 a 方向相同，长度为 a 的 2 倍"]
    assert refined["visual_semantics"]["scene_kind"] == "2d"


def test_linear_combination_refinement_uses_the_lecture_example_as_a_three_step_flow() -> None:
    payload = composition_artifact_payload()
    payload["topic_id"] = "ch01.ops.linear-combination"
    payload["claims"][0]["id"] = "claim.ch01.ops.linear-combination"  # type: ignore[index]

    refined = refine_payload(payload)

    explanation = refined["explanation"]
    assert explanation.get("derivation", []) == []
    assert "intuition" not in explanation
    assert "pitfalls" not in explanation
    assert [example["id"] for example in explanation["worked_examples"]] == [
        "example.linear-combination.vectors",
        "example.linear-combination.terms",
        "example.linear-combination.result",
    ]
    assert [case["id"] for case in explanation["case_layout"]["cases"]] == [
        "case.linear-combination.vectors",
        "case.linear-combination.terms",
        "case.linear-combination.result",
    ]
    # 三步并排：第一步 a、b，第二步 2a、-b，第三步组合结果。
    assert explanation["case_layout"]["default_pane_count"] == 3
    entities = {item["id"]: item for item in refined["visual_semantics"]["entities"]}
    assert entities["a"]["value"] == [3, 1]
    assert entities["b"]["value"] == [1, 2]
    assert entities["two_a"]["value"] == [6, 2]
    assert entities["neg_b"]["value"] == [-1, -2]
    assert entities["combination"]["value"] == [5, 0]
    # 第二步的 2a、-b 用与原向量不同的角色，取到与 a、b 不同的调色板颜色。
    assert entities["a"]["role"] == "vector_a"
    assert entities["b"]["role"] == "vector_b"
    assert entities["two_a"]["role"] == "transformed_a"
    assert entities["neg_b"]["role"] == "transformed_b"
    # 组合结果不能落到回退的中性灰（#6B7280），否则在画布上根本看不清。
    assert entities["combination"]["role"] == "combination"
    stages = refined["visual_semantics"]["stages"]
    assert [stage["id"] for stage in stages] == [
        "stage.linear-combination.vectors",
        "stage.linear-combination.terms",
        "stage.linear-combination.result",
    ]
    assert stages[0]["input_entity_refs"] == ["a", "b"]
    # 第二步同时显示原向量 a、b 与带系数的 2a、-b。
    assert stages[1]["input_entity_refs"] == ["a", "b", "two_a", "neg_b"]
    assert stages[2]["output_entity_refs"] == ["combination"]


def test_composition_refinement_binds_both_endpoints_to_the_visual_graph() -> None:
    refined = refine_payload(composition_artifact_payload())

    entities = {item["id"]: item for item in refined["visual_semantics"]["entities"]}
    assert entities["y"]["value"] == [-2, 1]
    assert entities["z"]["value"] == [-1, 2]
    assert entities["B"]["value"] == [[0, -1], [1, 0]]
    assert "先 B 后 A" in {stage["title"] for stage in refined["visual_semantics"]["stages"]}
    assert "先 A 后 B" in {stage["title"] for stage in refined["visual_semantics"]["stages"]}


def test_refinement_rebinds_claims_to_the_final_explanation_sections() -> None:
    """Lecture merging must not leave a claim pointing at a removed section."""

    payload = composition_artifact_payload()
    payload["topic_id"] = "ch02.batch.inner-products"
    payload["claims"][0]["explanation_refs"] = ["connections"]  # type: ignore[index]

    refined = refine_payload(payload)

    section_ids = [section["id"] for section in refined["explanation"]["sections"]]
    assert refined["claims"][0]["explanation_refs"] == section_ids


def test_inner_product_definitions_refinement_walks_both_definitions_in_two_panes() -> None:
    payload = composition_artifact_payload()
    payload["topic_id"] = "ch01.inner.definitions"
    payload["claims"][0]["id"] = "claim.ch01.inner.definitions"  # type: ignore[index]

    refined = refine_payload(payload)

    explanation = refined["explanation"]
    assert explanation.get("derivation", []) == []
    assert "intuition" not in explanation
    assert "pitfalls" not in explanation
    # 讲义 1.3.1 的定义块自带定义 1.10（几何定义）与定义 1.11（代数计算），
    # 公式写在定义块内，不再单列「公式」分节；「直观理解」按讲义位置并入定义。
    assert "定义 1.10" in explanation["definition"]
    assert "定义 1.11" in explanation["definition"]
    assert "直观理解" in explanation["definition"]
    assert explanation.get("formula", "") == ""
    # 分节标题照讲义原文：只有「定义」「数学案例」「内积的基本性质」三节。
    assert [(section["id"], section["title"]) for section in explanation["sections"]] == [
        ("definition", "定义"),
        ("worked_examples", "数学案例"),
        ("invariants", "内积的基本性质"),
    ]
    # 案例按数学流程分两步：第一步几何定义，第二步代数定义，共用同一对向量。
    assert [example["id"] for example in explanation["worked_examples"]] == [
        "example.inner.definition.geometric",
        "example.inner.definition.algebraic",
    ]
    assert [example["title"] for example in explanation["worked_examples"]] == [
        "第一步：几何定义",
        "第二步：代数定义",
    ]
    assert [example["result"] for example in explanation["worked_examples"]] == [4.0, 4.0]
    geometric, algebraic = explanation["worked_examples"]
    assert any("投影长度" in line for line in geometric["calculation"])
    assert any("a_1b_1+a_2b_2" in line for line in algebraic["calculation"])
    # 两个步骤并排显示，窗格切换按钮就是两步。
    assert explanation["case_layout"]["default_pane_count"] == 2
    assert [case["purpose"] for case in explanation["case_layout"]["cases"]] == [
        "第一步：几何定义",
        "第二步：代数定义",
    ]
    # 性质 1.1--1.4 统一写成「性质陈述 + 展示公式 + 证明」，公式用展示式排版，
    # 不能挤在一行里只靠行内 $...$ 显示。
    invariants = explanation["invariants"]
    assert "性质 1.1" in invariants[0]
    assert r"$$\boldsymbol a\cdot\boldsymbol b=\boldsymbol b\cdot\boldsymbol a$$" in invariants[0]
    assert "证明" in invariants[0]
    assert "性质 1.4" in invariants[3]
    assert (
        r"$$\boldsymbol a\cdot\boldsymbol a\geq0,\qquad \boldsymbol a\cdot\boldsymbol a=0\Longleftrightarrow\boldsymbol a=\boldsymbol0$$"
        in invariants[3]
    )
    # 角度/内积对照表保留讲义的三行，并补回讲义表格抽取时丢掉的 $a\cdot b$ 取值：
    # 同向取最大值 $|a||b|$，反向取最小值 $-|a||b|$。
    assert "角度与内积的对应关系" in invariants[4]
    assert "| $\\theta$ | $\\cos\\theta$ | $\\boldsymbol a\\cdot\\boldsymbol b$ | 几何含义 |" in invariants[4]
    assert "| $0^\\circ$ | $1$ | $\\lvert\\boldsymbol a\\rvert\\,\\lvert\\boldsymbol b\\rvert$（最大） | 完全同向——“最像” |" in invariants[4]
    assert "| $90^\\circ$ | $0$ | $0$ | 正交——“完全不像” |" in invariants[4]
    assert "| $180^\\circ$ | $-1$ | $-\\lvert\\boldsymbol a\\rvert\\,\\lvert\\boldsymbol b\\rvert$（最小） | 完全反向 |" in invariants[4]


def test_inner_product_definitions_refinement_projects_b_to_a_in_the_second_pane_only() -> None:
    payload = composition_artifact_payload()
    payload["topic_id"] = "ch01.inner.definitions"
    payload["claims"][0]["id"] = "claim.ch01.inner.definitions"  # type: ignore[index]

    refined = refine_payload(payload)

    visual = refined["visual_semantics"]
    assert visual["scene_kind"] == "2d"
    entities = {item["id"]: item for item in visual["entities"]}
    # 案例取 a=(2,1)、b=(1,2)：三个端点都不落在坐标轴上。
    assert entities["case1_a"]["value"] == [2, 1]
    assert entities["case1_b"]["value"] == [1, 2]
    assert entities["case1_p"]["value"] == [1.6, 0.8]
    assert entities["case1_p"]["role"] == "projection"
    assert entities["case1_H"]["value"] == [1.6, 0.8]
    assert entities["case1_H"]["role"] == "foot"
    relations = {item["id"]: item for item in visual["relations"]}
    # b 沿 a 的方向正交投影，投影结果与垂足同址；辅助作图用虚线。
    assert relations["rel.case.ch01.inner.definitions.1"]["kind"] == "projects_to"
    assert relations["rel.case.ch01.inner.definitions.1"]["source_ref"] == "case1_b"
    assert relations["rel.case.ch01.inner.definitions.1"]["target_ref"] == "case1_a"
    assert relations["rel.case.ch01.inner.definitions.1"]["style"] == "dashed"
    assert relations["rel.case.ch01.inner.definitions.2"]["style"] == "dashed"
    # 夹角弧必须用不带 rel.case. 前缀的关系名，否则只会登记别名而不落笔画。
    assert relations["rel.angle.ch01.inner.definitions.1"]["kind"] == "orientation"
    first, second = visual["stages"][:2]
    # 第一步（几何定义）只画 a、b 与夹角：投影由 projects_to 关系驱动，未引用该关系就不落笔。
    assert first["input_entity_refs"] == ["case1_a", "case1_b"]
    assert first["output_entity_refs"] == []
    assert first["relation_refs"] == ["rel.angle.ch01.inner.definitions.1"]
    # 第二步（代数定义）画 b 在 a 上的虚线投影与垂足，说明投影长度与内积的关系。
    assert second["input_entity_refs"] == ["case2_a", "case2_b", "case2_p"]
    assert second["output_entity_refs"] == ["case2_H"]
    assert second["relation_refs"] == [
        "rel.case.ch01.inner.definitions.2",
        "rel.angle.ch01.inner.definitions.2",
    ]
