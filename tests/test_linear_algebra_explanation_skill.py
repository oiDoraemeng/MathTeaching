from pathlib import Path

from linear_algebra.registry import runtime_teaching_store


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
        "ch01.proof.method",
        "ch01.proof.midline",
        "ch01.proof.centroid",
        "ch01.proof.parallelogram-diagonals",
        "BC = b - a",
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
