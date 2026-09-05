"""Explicit L0-L4 completeness checks for explanation artifacts."""

from __future__ import annotations

from dataclasses import replace

from linear_algebra.teaching.model import TeachingArtifact, WorkedExample
from linear_algebra.teaching.validation import validate_teaching_depth

from tests.teaching_fixtures import composition_artifact_payload


def _artifact_with_explanation(**changes: object) -> TeachingArtifact:
    artifact = TeachingArtifact.from_dict(composition_artifact_payload())
    return replace(artifact, explanation=replace(artifact.explanation, **changes))


def test_l3_requires_example_geometry_and_invariant() -> None:
    artifact = _artifact_with_explanation(worked_examples=(), geometric_meaning="", invariants=())

    issues = validate_teaching_depth(artifact)
    codes = {issue.code for issue in issues}

    assert {"missing_worked_example", "missing_geometric_meaning", "missing_invariant"} <= codes


def test_l4_requires_connection_and_variant() -> None:
    artifact = _artifact_with_explanation(connections=(), transfer_note="")

    issues = validate_teaching_depth(artifact)
    codes = {issue.code for issue in issues}

    assert {"missing_connection", "missing_transfer_note"} <= codes


def test_complete_explicit_core_fields_have_no_depth_diagnostics() -> None:
    artifact = _artifact_with_explanation(
        definition="定义",
        formula="(AB)x=A(Bx)",
        derivation=("先算 Bx", "再算 A(Bx)"),
        worked_examples=(WorkedExample(kind="manual", given=None, calculation=("manual",), result=None),),
        geometric_meaning="两次变换依次作用",
        pitfalls=("不要把顺序写反",),
        invariants=("复合顺序保持",),
        connections=("矩阵与基",),
        transfer_note="比较 BA 得到变式",
    )
    issues = validate_teaching_depth(artifact)
    assert "missing_geometric_meaning" not in {issue.code for issue in issues}
