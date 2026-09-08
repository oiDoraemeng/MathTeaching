from pathlib import Path

from linear_algebra.registry import runtime_teaching_store


def test_vector_addition_skill_requires_evidence_and_nonfixed_cases() -> None:
    skill = Path(".agents/linear-algebra-explanation-skill/SKILL.md").read_text(encoding="utf-8")
    for required in ("先向用户确认", "可以是一个、两个、三个或四个", "来源路径与哈希", "\\boldsymbol{}", "已确认的向量加法契约"):
        assert required in skill

    contract = Path(".agents/linear-algebra-explanation-skill/references/vector-addition-accepted-contract.md").read_text(encoding="utf-8")
    for required in ("全部显示", "左侧并跨两行", "结果行或校验行", "标题左对齐"):
        assert required in contract


def test_vector_addition_published_content_omits_unjustified_layers() -> None:
    artifact = runtime_teaching_store().published("ch01.ops.addition").artifact
    explanation = artifact.explanation
    assert explanation.derivation == ()
    assert explanation.intuition == ""
    assert explanation.connections == ()
    assert [case.id for case in explanation.case_layout.cases] == [
        "case.components",
        "case.geometry",
        "case.velocity",
    ]
