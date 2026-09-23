from linear_algebra.registry import bundled_teaching_store
from linear_algebra.teaching.compile_resources import compiled_resource_store
from linear_algebra.teaching.content_validation import (
    lecture_source_repository,
    validate_chapter_artifacts,
)


def test_chapter_02_has_9_published_artifacts() -> None:
    report = validate_chapter_artifacts(2, bundled_teaching_store(), lecture_source_repository())
    assert (report.topic_count, report.errors) == (9, ())


def test_matrix_composition_artifact_has_two_ordered_paths() -> None:
    artifact = bundled_teaching_store().published("ch02.matrix.composition").artifact
    relation_kinds = [relation.kind for relation in artifact.visual_semantics.relations]
    assert relation_kinds.count("composition_order") == 2
    assert {"endpoint_diff", "compare"} <= set(relation_kinds)


def test_matrix_composition_preserves_the_lecture_and_uses_one_four_step_case() -> None:
    artifact = bundled_teaching_store().published("ch02.matrix.composition").artifact
    explanation = artifact.explanation

    assert [section.title for section in explanation.sections] == ["定义", "数学案例"]
    assert explanation.formula == ""
    assert explanation.derivation == ()
    assert explanation.geometric_meaning == ""
    assert len(explanation.worked_examples) == 1
    assert explanation.case_layout is not None
    assert explanation.case_layout.default_pane_count == 4
    assert len(explanation.case_layout.cases) == 4
    assert len(artifact.visual_semantics.stages) == 4

    definition = explanation.definition
    for lecture_text in (
        "一句话动机",
        "（矩阵乘法）",
        "（矩阵乘法的几何含义）",
        "（乘法的结合律）",
        "（乘法不满足交换律）",
        "（矩阵乘法的分配律）",
        "证明（1）",
        "这是线性性质在矩阵层面的体现",
    ):
        assert lecture_text in definition
    assert "分层例题" not in definition
    assert "自检" not in definition

    calculation = "\n".join(explanation.worked_examples[0].calculation)
    assert r"\boldsymbol x=\begin{pmatrix}1\\1\end{pmatrix}" in calculation
    assert r"\boldsymbol A\boldsymbol B=\begin{pmatrix}0&-2\\1&0\end{pmatrix}" in calculation
    assert r"\boldsymbol B\boldsymbol A=\begin{pmatrix}0&-1\\2&0\end{pmatrix}" in calculation
    assert r"\boldsymbol x=(1,1)" not in calculation


def test_matrix_composition_compiles_distinct_fixed_scale_paths() -> None:
    resource = compiled_resource_store().get("ch02.matrix.composition")
    operations = resource.plan["operations"]
    linear = {item["alias"]: item for item in operations if item["op"] == "linear.upsert"}
    grids = {item["alias"]: item for item in operations if item["op"] == "geometry.transformed_grid"}

    assert linear["sem__x"]["color"] == "#6B7280"
    assert {linear["sem__bx"]["color"], linear["sem__abx"]["color"]} == {"#2F6BFF"}
    assert {linear["sem__ax"]["color"], linear["sem__bax"]["color"]} == {"#F08A24"}
    assert grids["sem__grid_ab"]["matrix"] == [[0.0, -2.0], [1.0, 0.0]]
    assert grids["sem__grid_ba"]["matrix"] == [[0.0, -1.0], [2.0, 0.0]]
    assert next(item for item in operations if item["op"] == "view.fit")["bounds"] == [-3.0, 3.0, -3.0, 3.0]


def test_matrix_powers_preserves_the_lecture_definition_and_original_examples() -> None:
    artifact = bundled_teaching_store().published("ch02.matrix.powers").artifact
    explanation = artifact.explanation

    assert [section.title for section in explanation.sections] == ["定义", "数学案例"]
    assert explanation.formula == ""
    assert explanation.derivation == ()
    assert explanation.geometric_meaning == ""
    assert len(explanation.worked_examples) == 2
    assert explanation.case_layout is not None
    assert explanation.case_layout.default_pane_count == 2
    assert len(explanation.case_layout.cases) == 2
    assert len(artifact.visual_semantics.stages) == 2

    definition = explanation.definition
    for lecture_text in (
        "一句话动机：幂是重复做同一变换，转置是行与列的视角切换",
        "在第3章引入逆矩阵之前",
        "**（矩阵的幂）**",
        r"\boldsymbol A^{0}=\boldsymbol I",
        "只有方阵才能定义幂",
        "**（转置的性质）**",
        r"(\boldsymbol A^{\mathsf T})^{\mathsf T}=\boldsymbol A",
        r"(\boldsymbol A+\boldsymbol B)^{\mathsf T}",
        r"(k\boldsymbol A)^{\mathsf T}",
        r"(\boldsymbol A\boldsymbol B)^{\mathsf T}=\boldsymbol B^{\mathsf T}\boldsymbol A^{\mathsf T}",
        "证明（4）",
    ):
        assert lecture_text in definition
    assert "2.8.5" not in definition
    assert "2.8.6" not in definition

    first, second = explanation.worked_examples
    assert first.title == "例1：求转置与平方"
    assert second.title == "例2：验证乘积转置"
    calculation = "\n".join((*first.calculation, *second.calculation))
    assert r"\boldsymbol A=\begin{pmatrix}1&2\\3&4\end{pmatrix}" in calculation
    assert r"\boldsymbol A^{2}=\boldsymbol A\cdot\boldsymbol A" in calculation
    assert r"\begin{pmatrix}7&10\\15&22\end{pmatrix}" in calculation
    assert r"\boldsymbol B=\begin{pmatrix}5&6\\7&8\end{pmatrix}" in calculation
    assert r"\boldsymbol B^{\mathsf T}\boldsymbol A^{\mathsf T}" in calculation
    assert "(1,2;3,4)" not in calculation


def test_matrix_powers_compiles_two_clean_fixed_scale_grids() -> None:
    resource = compiled_resource_store().get("ch02.matrix.powers")
    operations = resource.plan["operations"]
    grids = [item for item in operations if item["op"] == "geometry.transformed_grid"]
    labels = [item for item in operations if item["op"] == "annotation.upsert"]
    fit = next(item for item in operations if item["op"] == "view.fit")

    assert [item["matrix"] for item in grids] == [
        [[1.0, 2.0], [3.0, 4.0]],
        [[7.0, 10.0], [15.0, 22.0]],
    ]
    assert [item["bounds"] for item in grids] == [
        [-1.0, 1.0, -1.0, 1.0],
        [-1.0, 1.0, -1.0, 1.0],
    ]
    assert [item["color"] for item in grids] == ["#2F6BFF", "#F08A24"]
    assert [item["text"] for item in labels] == [
        r"$A=\left[\genfrac{}{}{0}{}{1\quad 2}{3\quad 4}\right]$",
        r"$A^{2}=\left[\genfrac{}{}{0}{}{\ 7\quad 10}{15\quad 22}\right]$",
    ]
    assert not any("invariant:" in str(item.get("text", "")) for item in operations)
    assert fit == {"op": "view.fit", "padding": 1.15, "bounds": [-18.0, 18.0, -38.0, 38.0]}
    assert [stage["title"] for stage in resource.stages] == [
        "第一步：作用一次",
        "第二步：再作用一次",
    ]
