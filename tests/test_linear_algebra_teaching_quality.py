from __future__ import annotations

from linear_algebra.teaching.model import TeachingArtifact
from linear_algebra.teaching.quality import refine_payload
from linear_algebra.catalog.manifest import lecture_manifest
from linear_algebra.visualizations.common import RenderContext
from linear_algebra.visualizations.compiler import VisualSemanticsCompiler
from linear_algebra.visualizations.contracts import contract_for
from tests.teaching_fixtures import composition_artifact_payload
from ui.teaching_case_panes import case_plan


def test_batch_projection_keeps_the_lecture_definition_and_one_confirmed_case() -> None:
    payload = composition_artifact_payload()
    payload["topic_id"] = "ch02.batch.projection"
    payload["claims"][0]["id"] = "claim.ch02.batch.projection"  # type: ignore[index]

    refined = refine_payload(payload)

    explanation = refined["explanation"]
    assert explanation["title"] == "投影矩阵"
    nodes = {node.id: node for node in lecture_manifest()}
    assert nodes["ch02.s23"].title == "2.3 批量投影"
    assert nodes["ch02.batch.projection"].title == "投影矩阵"
    assert explanation["summary"] == "投影也能批处理——矩阵乘法的雏形已经萌芽。"
    assert "**（投影矩阵）**" in explanation["definition"]
    assert r"$\lvert\boldsymbol u\rvert=1$" in explanation["definition"]
    assert r"\operatorname{Proj}_{\boldsymbol u}(\boldsymbol v)" in explanation["definition"]
    assert "乘任何向量" in explanation["definition"]
    assert "自检" not in explanation["definition"]
    assert explanation["formula"] == ""
    assert explanation["derivation"] == []
    assert explanation["geometric_meaning"] == ""
    assert [section["title"] for section in explanation["sections"]] == ["定义", "数学案例"]
    assert len(explanation["worked_examples"]) == 1
    example = explanation["worked_examples"][0]
    assert example["kind"] == "batch_projection"
    assert example["result"] == [[3.0, 0.0], [-2.0, 0.0], [1.0, 0.0]]
    assert explanation["case_layout"]["default_pane_count"] == 1
    assert len(explanation["case_layout"]["cases"]) == 1

    visual = refined["visual_semantics"]
    entities = {item["id"]: item for item in visual["entities"]}
    assert [entities[f"batch{index}_v"]["role"] for index in range(1, 4)] == [
        "vector_a", "vector_b", "transformed_a"
    ]
    assert [entities[f"batch{index}_p"]["value"] for index in range(1, 4)] == [
        [3.0, 0.0], [-2.0, 0.0], [1.0, 0.0]
    ]
    assert len(visual["stages"]) == 1
    assert visual["stages"][0]["relation_refs"] == [
        "rel.batch-projection.1",
        "rel.batch-projection.2",
        "rel.batch-projection.3",
    ]

    artifact = TeachingArtifact.from_dict(refined)
    compiled = VisualSemanticsCompiler().compile(
        artifact,
        contract_for("ch02.batch.projection"),
        RenderContext.default("ch02.batch.projection"),
    )
    operations = {
        str(operation.get("alias")): operation
        for operation in compiled.plan.operations
        if operation.get("op") in {"linear.upsert", "geometry.projection"}
    }
    expected_colors = ("#2F6BFF", "#F08A24", "#7B61FF")
    for index, color in enumerate(expected_colors, start=1):
        assert operations[f"sem__batch{index}_v"]["color"] == color
        assert operations[f"sem__batch{index}_p"]["color"] == color
        assert operations[f"sem__rel.batch-projection.{index}"]["color"] == color
    assert not any(
        operation.get("op") == "geometry.transformed_grid"
        for operation in compiled.plan.operations
    )
    pane_plan = case_plan(compiled, "stage.case.ch02.batch.projection.1")
    assert sum(
        operation.get("op") == "geometry.projection"
        for operation in pane_plan.operations
    ) == 3
    assert not any(
        operation.get("alias") == "sem__u"
        for operation in pane_plan.operations
    )


def test_matrix_addition_keeps_the_lecture_text_and_confirmed_two_route_case() -> None:
    payload = composition_artifact_payload()
    payload["topic_id"] = "ch02.matrix.additive-distributivity"
    payload["claims"][0]["id"] = "claim.ch02.matrix.additive-distributivity"  # type: ignore[index]

    refined = refine_payload(payload)

    explanation = refined["explanation"]
    assert explanation["title"] == "矩阵加法与变换分配律"
    assert explanation["summary"] == "一句话动机：向量有加法和数乘，矩阵作为向量的集合，自然也继承了这些运算。"
    definition = explanation["definition"]
    assert "**（矩阵加法）**" in definition
    assert "**（矩阵数乘）**" in definition
    assert "**（分配律）**" in definition
    assert r"(\boldsymbol A + \boldsymbol B)_{ij} = a_{ij} + b_{ij}" in definition
    assert r"(k\boldsymbol A)_{ij} = k \cdot a_{ij}" in definition
    assert r"\begin{pmatrix}1 & 2 \\ 3 & 4\end{pmatrix}" in definition
    assert r"\begin{pmatrix}6 & 8 \\ 10 & 12\end{pmatrix}" in definition
    assert "自检" not in definition
    assert explanation["formula"] == ""
    assert explanation["derivation"] == []
    assert explanation["geometric_meaning"] == ""
    assert [section["title"] for section in explanation["sections"]] == ["定义", "数学案例"]
    assert [example["kind"] for example in explanation["worked_examples"]] == [
        "matrix_additive_distributivity",
        "matrix_additive_distributivity",
    ]
    assert [example["result"] for example in explanation["worked_examples"]] == [
        [3, 3],
        [3, 3],
    ]
    assert explanation["case_layout"]["default_pane_count"] == 2
    assert len(explanation["case_layout"]["cases"]) == 2
    assert len(refined["visual_semantics"]["stages"]) == 2

    artifact = TeachingArtifact.from_dict(refined)
    compiled = VisualSemanticsCompiler().compile(
        artifact,
        contract_for("ch02.matrix.additive-distributivity"),
        RenderContext.default("ch02.matrix.additive-distributivity"),
    )
    assert compiled.storyboard[0].anchor == compiled.storyboard[1].anchor
    operations = {
        str(operation.get("alias")): operation
        for operation in compiled.plan.operations
        if operation.get("alias")
    }
    assert operations["sem__mv_add_ax"]["color"] != operations["sem__mv_add_bx"]["color"]
    assert operations["sem__mv_add_y1"]["color"] == operations["sem__mv_add_y2"]["color"]
    first_pane = case_plan(compiled, "stage.case.ch02.matrix.additive-distributivity.1")
    second_pane = case_plan(compiled, "stage.case.ch02.matrix.additive-distributivity.2")
    assert any(operation.get("op") == "geometry.transformed_grid" for operation in first_pane.operations)
    assert sum(operation.get("op") == "linear.upsert" for operation in second_pane.operations) == 3


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
    assert entities["x"]["value"] == [1, 1]
    assert entities["abx"]["value"] == [-2, 1]
    assert entities["bax"]["value"] == [-1, 2]
    assert entities["grid_ab"]["value"] == [[0, -2], [1, 0]]
    assert entities["grid_ba"]["value"] == [[0, -1], [2, 0]]
    assert [stage["title"] for stage in refined["visual_semantics"]["stages"]] == [
        "第一步：共同输入",
        "第二步：先旋转后拉伸",
        "第三步：先拉伸后旋转",
        "第四步：比较终点",
    ]


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
    # 讲义 1.3.1 的定义块自带几何定义与代数计算两段（讲义编号在本批改动中
    # 统一改为加粗小标题），公式写在定义块内，不再单列「公式」分节；
    # 「直观理解」按讲义位置并入定义。
    assert "**（内积 / 点积 — 几何定义）**" in explanation["definition"]
    assert "**（内积 — 代数计算）**" in explanation["definition"]
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
    # 交换律、分配律、数乘结合律、正定性四条性质统一写成
    # 「加粗小标题 + 展示公式 + 证明」（讲义编号在本批改动中改为加粗小标题），
    # 公式用展示式排版，不能挤在一行里只靠行内 $...$ 显示。
    invariants = explanation["invariants"]
    assert "**（交换律 / 对称性）**" in invariants[0]
    assert r"$$\boldsymbol a\cdot\boldsymbol b=\boldsymbol b\cdot\boldsymbol a$$" in invariants[0]
    assert "证明" in invariants[0]
    assert "**（正定性）**" in invariants[3]
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


def test_projection_definition_uses_skill_compliant_headings_and_fractions() -> None:
    payload = composition_artifact_payload()
    payload["topic_id"] = "ch01.projection.definition"
    payload["claims"][0]["id"] = "claim.ch01.projection.definition"  # type: ignore[index]

    refined = refine_payload(payload)
    definition = refined["explanation"]["definition"]

    assert "**（投影向量）**" in definition
    assert "**（投影公式）**" in definition
    assert "定义 1.13" not in definition
    assert "定理 1.6" not in definition
    assert r"\begin{aligned}" in definition
    assert r"\frac{\boldsymbol v\cdot\boldsymbol u}{\lvert\boldsymbol u\rvert^{2}}" in definition
    assert r"(\boldsymbol v\cdot\boldsymbol u)/\lvert\boldsymbol u\rvert^{2}" not in definition
