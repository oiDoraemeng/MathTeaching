from pathlib import Path
import math

from linear_algebra.registry import runtime_teaching_store
from linear_algebra.visualizations.compiler import VisualSemanticsCompiler
from linear_algebra.visualizations.common import RenderContext
from ui.teaching_case_panes import case_plan


def test_vector_addition_skill_requires_evidence_and_nonfixed_cases() -> None:
    skill = Path(".agents/linear-algebra-explanation-skill/SKILL.md").read_text(encoding="utf-8")
    for required in ("先向用户确认", "可以是一个、两个、三个或四个", "来源路径与哈希", "\\boldsymbol{}", "已确认的向量加法契约"):
        assert required in skill

    contract = Path(".agents/linear-algebra-explanation-skill/references/vector-addition-accepted-contract.md").read_text(encoding="utf-8")
    for required in ("全部显示", "左右各一个", "结果行或校验行", "标题左对齐", "不得在原点叠加多个同名标签"):
        assert required in contract


def test_geometry_proof_skill_records_the_accepted_figures() -> None:
    skill = Path(".agents/linear-algebra-explanation-skill/SKILL.md").read_text(encoding="utf-8")
    for required in ("1.5 几何证明的已确认示例", "geometry-proof-accepted-contract.md", "渲染为空白"):
        assert required in skill

    contract = Path(
        ".agents/linear-algebra-explanation-skill/references/geometry-proof-accepted-contract.md"
    ).read_text(encoding="utf-8")
    for required in (
        "ch01.proof.midline",
        "ch01.proof.centroid",
        "ch01.proof.parallelogram-diagonals",
        "DE = ½ BC",
        "AG : GD = 2 : 1",
        "M(AC) = M(BD) = (a + b) / 2",
        "`→`",
        "`∥`",
        "padding=1.45",
    ):
        assert required in contract


def test_skill_records_the_default_pane_count_and_image_fit_rules() -> None:
    skill = Path(".agents/linear-algebra-explanation-skill/SKILL.md").read_text(encoding="utf-8")
    for required in ("流程类小节默认“全部显示”", "按窗格实际宽高比计算缩放", "不强制把原点放在正中间"):
        assert required in skill

    contract = Path(
        ".agents/linear-algebra-explanation-skill/references/vector-addition-accepted-contract.md"
    ).read_text(encoding="utf-8")
    for required in ("default_pane_count = 2", "按窗格实际宽高比", "不强制把原点放在正中间"):
        assert required in contract


def test_skill_selects_layers_by_section_nature() -> None:
    skill = Path(".agents/linear-algebra-explanation-skill/SKILL.md").read_text(encoding="utf-8")
    for required in ("定义性的小节", "全部都是案例的小节", "直接沿用讲义本身的组织与格式"):
        assert required in skill


def test_vector_addition_published_content_omits_unjustified_layers() -> None:
    artifact = runtime_teaching_store().published("ch01.ops.addition").artifact
    explanation = artifact.explanation
    assert explanation.derivation == ()
    assert explanation.intuition == ""
    assert explanation.connections == ()
    assert [case.id for case in explanation.case_layout.cases] == [
        "case.addition.objects",
        "case.addition.parallelogram",
    ]
    # 数学案例流程默认“全部显示”：首屏并排显示两个步骤窗格。
    assert explanation.case_layout.default_pane_count == 2


def test_matrix_vector_subsections_publish_the_lecture_verbatim() -> None:
    """2.5 的三个小节按讲义原文给出定义/定理/例题，不概括、不单列「公式」分节。"""

    store = runtime_teaching_store()

    row_column = store.published("ch02.matrix.row-column").artifact.explanation
    assert [(section.id, section.title) for section in row_column.sections] == [
        ("definition", "定义"),
        ("worked_examples", "数学案例"),
    ]
    for required in (
        "设 $\\boldsymbol A$ 是 $m \\times n$ 矩阵",
        "算法一（行视角 — 内积法）",
        "算法二（列视角 — 线性组合法）",
        "把矩阵各列取出来",
    ):
        assert required in row_column.definition
    assert row_column.formula == ""
    assert row_column.geometric_meaning == ""
    assert [case.purpose for case in row_column.case_layout.cases] == [
        "第一步：行视角（内积法）",
        "第二步：列视角（线性组合法）",
    ]
    assert row_column.case_layout.default_pane_count == 2

    transformed = store.published("ch02.matrix.transformed-grid").artifact.explanation
    # 讲义把这一小节写成「定理 2.2 + 直觉总结」：标题听命讲义，正文逐字保留。
    assert [section.title for section in transformed.sections] == ["定理", "数学案例"]
    for required in (
        "定理 2.2（矩阵变换的基向量解释）",
        "标准基向量 $\\boldsymbol e_{1}$ 被 $\\boldsymbol A$ 送到的新位置",
        "直觉总结",
        "整个坐标网格被 $\\boldsymbol A$ 拉伸、旋转、压扁",
    ):
        assert required in transformed.definition
    assert transformed.case_layout.default_pane_count == 3

    stretch = store.published("ch02.matrix.stretch-rotate-scale").artifact.explanation
    assert [section.title for section in stretch.sections] == ["分层例题", "数学案例"]
    for required in ("**【理解层】**", "例1：", "例2：", "**【计算层】**", "例3：", "**【应用层】**"):
        assert required in stretch.definition
    # 用户确认：例4 不进窗格，也从正文删去。
    assert "例4" not in stretch.definition
    assert [case.purpose for case in stretch.case_layout.cases] == [
        "第一步：未变换的标准网格",
        "第二步：例1 横向拉伸",
        "第三步：例2 逆时针旋转",
        "第四步：拉伸与旋转同时存在",
    ]
    assert stretch.case_layout.default_pane_count == 4


def test_matrix_vector_case_data_avoids_the_coordinate_axes() -> None:
    """2.5.1、2.5.2 的自定案例取值避开坐标轴（标准基向量由讲义固定，不在此列）。"""

    store = runtime_teaching_store()
    for topic_id in ("ch02.matrix.row-column", "ch02.matrix.transformed-grid"):
        artifact = store.published(topic_id).artifact
        for entity in artifact.visual_semantics.entities:
            if entity.kind != "vector" or entity.id in {"mv_e1", "mv_e2"}:
                continue
            value = tuple(float(item) for item in entity.value)
            assert all(abs(item) > 0.0 for item in value), (topic_id, entity.id, value)


def _pane_radius(plan) -> float:
    """Return the bounding-sphere radius of the objects that frame one case pane.

    The matrix-case grid is deliberately sampled far beyond the pane viewport and
    clipped by the viewport, so the pane camera ignores it (it is hidden while
    the camera is fitted); it therefore does not take part in the shared view.
    """

    points = [
        (float(operation["coordinates"][0]), float(operation["coordinates"][1]))
        for operation in plan.operations
        if operation.get("op") == "point.upsert"
    ]
    points.extend(
        (float(operation["position"][0]), float(operation["position"][1]))
        for operation in plan.operations
        if operation.get("op") in {"annotation.upsert", "annotation.formula"}
    )
    if not points:
        return 0.0
    width = max(point[0] for point in points) - min(point[0] for point in points)
    height = max(point[1] for point in points) - min(point[1] for point in points)
    return math.hypot(width / 2.0, height / 2.0)


def test_matrix_vector_case_panes_share_one_fixed_view() -> None:
    """数学案例流程默认“全部显示”：各窗格内容都落在同一个取景下，不出现一大一小。"""

    store = runtime_teaching_store()
    compiler = VisualSemanticsCompiler()
    for topic_id, pane_count in (
        ("ch02.matrix.row-column", 2),
        ("ch02.matrix.transformed-grid", 3),
        ("ch02.matrix.stretch-rotate-scale", 4),
    ):
        artifact = store.published(topic_id).artifact
        compiled = compiler.compile(artifact, context=RenderContext.default(topic_id))
        assert len(compiled.storyboard) == pane_count
        view = compiled.plan.operations[-1]
        assert view["op"] == "view.fit" and view.get("bounds")
        for stage in compiled.storyboard:
            plan = case_plan(compiled, stage.id)
            assert plan.operations
            # 窗格相机的取景下界是 6.5：参与取景的内容半径不超过它，各窗格才共用同一缩放。
            assert _pane_radius(plan) <= 6.5, (topic_id, stage.id)
