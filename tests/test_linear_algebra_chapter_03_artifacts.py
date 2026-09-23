from pathlib import Path

from linear_algebra.registry import bundled_teaching_store, catalog_registry
from linear_algebra.teaching.content_validation import (
    lecture_source_repository,
    validate_chapter_artifacts,
)
from linear_algebra.teaching.source import LectureSourceRepository
from ui.teaching_case_panes import case_plan


def test_chapter_03_has_8_published_artifacts() -> None:
    report = validate_chapter_artifacts(3, bundled_teaching_store(), lecture_source_repository())
    assert (report.topic_count, report.errors) == (8, ())


def test_sections_3_3_to_3_6_publish_lecture_and_cases_without_drawings() -> None:
    store = bundled_teaching_store()
    registry = catalog_registry()
    expected = {
        "ch03.cramer.area-ratio": (["定义", "数学案例"], 1),
        "ch03.inverse.undo": (["定义", "数学案例"], 4),
        "ch03.adjugate.matrix": (["定义", "推导", "数学案例"], 1),
        "ch03.det.zero.equivalence": (["定义", "推导", "数学案例"], 2),
    }

    for topic_id, (section_titles, example_count) in expected.items():
        artifact = store.published(topic_id).artifact
        compiled = registry.resolve_bundle(topic_id, artifact_store=store).compiled
        assert [section.title for section in artifact.explanation.sections] == section_titles
        assert len(artifact.explanation.worked_examples) == example_count
        assert artifact.explanation.formula == ""
        assert artifact.explanation.case_layout is None
        assert artifact.visual_semantics.entities == ()
        assert artifact.visual_semantics.relations == ()
        assert artifact.visual_semantics.stages == ()
        assert compiled.storyboard == ()
        assert compiled.plan.operations == ({"op": "view.fit", "padding": 1.15},)


def test_cramer_and_inverse_keep_the_complete_lecture_cases() -> None:
    store = bundled_teaching_store()
    cramer = store.published("ch03.cramer.area-ratio").artifact.explanation
    inverse = store.published("ch03.inverse.undo").artifact.explanation

    assert "**（Cramer 法则）**" in cramer.definition
    assert "定理 3.5" not in cramer.definition
    assert r"x_{i}=\frac{\det(\boldsymbol A_{i})}{\det(\boldsymbol A)}" in cramer.definition
    assert r"以 $\boldsymbol b$ 替第一列" in cramer.definition
    assert cramer.worked_examples[0].given == (((2, 1), (1, 3)), (2, 1))
    assert cramer.worked_examples[0].result == (5, 5)
    cramer_case = "\n".join(cramer.worked_examples[0].calculation)
    assert r"\begin{pmatrix}" in cramer_case
    assert r"x=\frac{10}{5}=2" in cramer_case
    assert r"y=\frac{5}{5}=1" in cramer_case

    assert r"一句话动机：变换 $\boldsymbol A$ 把空间拉伸旋转了" in inverse.definition
    assert "**（逆矩阵）**" in inverse.definition
    assert "**（可逆的充要条件）**" in inverse.definition
    assert "定义 3.2" not in inverse.definition
    assert "定理 3.6" not in inverse.definition
    assert r"口诀：对角线交换，反对角线变号，前乘 $1/\det$。" in inverse.definition
    assert [example.title for example in inverse.worked_examples] == ["例1", "例2", "例3", "例4"]
    assert [example.result for example in inverse.worked_examples] == [
        ((1, 0), (0, 1)),
        0,
        ((1, 0), (0, 1)),
        (3, 1),
    ]


def test_adjugate_keeps_both_lecture_blocks_and_confirmed_matrix_case() -> None:
    artifact = bundled_teaching_store().published("ch03.adjugate.matrix").artifact
    explanation = artifact.explanation

    assert len(artifact.source.spans) == 2
    assert "📖 选学本节，不做考试要求。考研同学需掌握。" in explanation.definition
    assert "**（伴随矩阵）**" in explanation.definition
    assert r"\boldsymbol A^{-1}=\operatorname{adj}\frac{\boldsymbol A}{\det(\boldsymbol A)}" in explanation.definition
    assert len(explanation.derivation) == 1
    assert r"\boldsymbol A\cdot\operatorname{adj}(\boldsymbol A)=\det(\boldsymbol A)\cdot\boldsymbol I" in explanation.derivation[0]
    example = explanation.worked_examples[0]
    assert example.given == (((2, 1), (3, 4)), ((4, -1), (-3, 2)))
    assert example.result == ((5, 0), (0, 5))
    calculation = "\n".join(example.calculation)
    for matrix in (
        "2 & 1",
        "4 & -3",
        "4 & -1",
        "5 & 0",
    ):
        assert matrix in calculation
    assert r"\boldsymbol A^{-1}" in calculation


def test_det_zero_keeps_the_complete_lecture_definition_proof_and_cases() -> None:
    explanation = bundled_teaching_store().published(
        "ch03.det.zero.equivalence"
    ).artifact.explanation

    assert "**（$\\det=0$ 的等价条件）**" in explanation.definition
    assert "定理 3.7" not in explanation.definition
    assert "**（三角矩阵的行列式）**" in explanation.definition
    assert r"\operatorname{rank}(\boldsymbol A)<n" in explanation.definition
    assert r"\boldsymbol A\boldsymbol x=\boldsymbol 0" in explanation.definition
    assert len(explanation.derivation) == 1
    assert "证明：对上三角矩阵按最后一列展开" in explanation.derivation[0]
    assert "推论：对角矩阵" in explanation.derivation[0]
    assert [example.title for example in explanation.worked_examples] == ["例5", "例题"]
    assert [example.result for example in explanation.worked_examples] == [42, 0]
    calculations = "\n".join(
        line for example in explanation.worked_examples for line in example.calculation
    )
    assert r"\begin{pmatrix}" in calculations
    assert r"\det(\boldsymbol A)=2\times3\times7=42" in calculations
    assert r"\det(\boldsymbol A)=6-6=0" in calculations
    assert "自检" not in calculations


def test_determinant_multiplicativity_has_three_area_stages() -> None:
    artifact = bundled_teaching_store().published("ch03.det.multiplicativity").artifact
    assert len(artifact.visual_semantics.stages) >= 3
    assert "same_measure" in {relation.kind for relation in artifact.visual_semantics.relations}


def test_determinant_transpose_uses_the_confirmed_matrix_and_its_transpose() -> None:
    artifact = bundled_teaching_store().published("ch03.det.transpose").artifact
    matrices = [
        entity.value
        for entity in artifact.visual_semantics.entities
        if entity.kind == "matrix"
    ]
    areas = [
        entity.value
        for entity in artifact.visual_semantics.entities
        if entity.kind == "area"
    ]

    assert matrices == [((2, 2), (1, 3)), ((2, 1), (2, 3))]
    assert areas == [((2, 1), (2, 3)), ((2, 2), (1, 3))]
    assert [example.result for example in artifact.explanation.worked_examples] == [4.0, 4.0]


def test_determinant_core_topics_preserve_definition_case_sections_and_panes() -> None:
    store = bundled_teaching_store()
    expected = {
        "ch03.det.basic-properties": 4,
        "ch03.det.multiplicativity": 3,
        "ch03.det.transpose": 2,
    }
    for topic_id, pane_count in expected.items():
        artifact = store.published(topic_id).artifact
        assert [section.title for section in artifact.explanation.sections] == ["定义", "数学案例"]
        assert artifact.explanation.definition
        assert len(artifact.explanation.worked_examples) == pane_count
        assert len(artifact.visual_semantics.stages) == pane_count


def test_basic_determinant_properties_use_the_confirmed_four_case_calculations() -> None:
    artifact = bundled_teaching_store().published("ch03.det.basic-properties").artifact
    explanation = artifact.explanation

    assert [section.title for section in explanation.sections] == ["定义", "数学案例"]
    assert explanation.summary == (
        "行列式不是孤立的数字——它有一组强大的运算规则。"
        "掌握这些规则，行列式计算像搭积木。"
    )
    assert explanation.formula == ""
    assert explanation.derivation == ()
    assert explanation.geometric_meaning == ""
    assert not any(
        marker in explanation.definition
        for marker in ("补充例题", "分层例题", "自检")
    )
    for lecture_text in (
        "一句话动机：行列式不是孤立的数字",
        "**（行列式的基本性质）**",
        "换行变号",
        "行倍乘",
        "行叠",
        "性质1（单位矩阵的行列式为1）",
        "性质2（交换两行，行列式变号）",
        "性质3（某行乘以 $k$，行列式乘以 $k$）",
        "性质4（某行加上另一行的 $k$ 倍，行列式不变）",
        "性质5（有一行全零",
        "性质6（两行相等",
    ):
        assert lecture_text in explanation.definition

    examples = explanation.worked_examples
    assert [example.title for example in examples] == [
        "案例一：交换两行",
        "案例二：第一行乘 2",
        "案例三：第二行加上第一行的 2 倍",
        "案例四：第二行为零",
    ]
    assert [example.given for example in examples] == [
        ((1, 2), (2, 1)),
        ((4, 2), (1, 2)),
        ((2, 1), (5, 4)),
        ((2, 1), (0, 0)),
    ]
    assert [example.result for example in examples] == [-3.0, 6.0, 3.0, 0.0]
    calculation = "\n".join(line for example in examples for line in example.calculation)
    for matrix in (
        r"\begin{pmatrix}2&1\\1&2\end{pmatrix}",
        r"\begin{pmatrix}1&2\\2&1\end{pmatrix}",
        r"\begin{pmatrix}4&2\\1&2\end{pmatrix}",
        r"\begin{pmatrix}2&1\\5&4\end{pmatrix}",
        r"\begin{pmatrix}2&1\\0&0\end{pmatrix}",
    ):
        assert matrix in calculation

    assert explanation.case_layout is not None
    assert explanation.case_layout.default_pane_count == 4
    assert [case.example_ref for case in explanation.case_layout.cases] == [
        examples[0].id,
        examples[0].id,
        examples[1].id,
        examples[1].id,
    ]
    visual_matrices = [
        entity.value
        for entity in artifact.visual_semantics.entities
        if entity.kind == "matrix"
    ]
    assert visual_matrices == [
        ((2, 1), (1, 2)),
        ((1, 2), (2, 1)),
        ((2, 1), (1, 2)),
        ((4, 2), (1, 2)),
    ]
    assert ((2, 1), (5, 4)) not in visual_matrices
    assert ((2, 1), (0, 0)) not in visual_matrices
    assert artifact.claims[0].formula == (
        r"\det(\boldsymbol A_{\mathrm{swap}})=-\det(\boldsymbol A),\quad"
        r"\det(\boldsymbol A_{\mathrm{scale}})=k\det(\boldsymbol A),\quad"
        r"\det(\boldsymbol A_{\mathrm{add}})=\det(\boldsymbol A)"
    )


def test_basic_determinant_properties_four_panes_share_scale_and_row_colors() -> None:
    compiled = catalog_registry().resolve_bundle(
        "ch03.det.basic-properties",
        artifact_store=bundled_teaching_store(),
        source_repository=LectureSourceRepository(Path(".agents") / "线性代数讲义.md"),
    ).compiled
    expected = (
        ([[2.0, 1.0], [1.0, 2.0]], [("r1", "#2F6BFF"), ("r2", "#F08A24")]),
        ([[1.0, 2.0], [2.0, 1.0]], [("r2", "#F08A24"), ("r1", "#2F6BFF")]),
        ([[2.0, 1.0], [1.0, 2.0]], [("r1", "#2F6BFF"), ("r2", "#F08A24")]),
        ([[4.0, 2.0], [1.0, 2.0]], [("2r1", "#2F6BFF"), ("r2", "#F08A24")]),
    )

    assert len(compiled.storyboard) == 4
    for stage, (vectors, row_styles) in zip(compiled.storyboard, expected):
        operations = case_plan(compiled, stage.id).operations
        grids = [op for op in operations if op.get("op") == "geometry.transformed_grid"]
        area = [op for op in operations if op.get("op") == "geometry.oriented_area"]
        rows = [op for op in operations if op.get("op") == "linear.upsert"]
        fits = [op for op in operations if op.get("op") == "view.fit"]

        # The live matrix toolbar owns the grid. The lesson plan contributes
        # only the determinant objects and the shared viewport.
        assert grids == []
        assert [op["vectors"] for op in area] == [vectors]
        assert [(op["label"], op["color"]) for op in rows] == row_styles
        assert fits == [
            {"op": "view.fit", "padding": 1.15, "bounds": [-1.0, 6.0, -1.0, 5.0]}
        ]
