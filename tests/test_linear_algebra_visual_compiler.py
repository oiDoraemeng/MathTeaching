"""Renderer-free compilation tests for teaching visual semantics."""

from __future__ import annotations

import pytest

from linear_algebra.teaching.model import TeachingArtifact, VisualSemantics
from linear_algebra.visualizations.common import RenderContext
from linear_algebra.visualizations.compiler import VisualCompileError, VisualSemanticsCompiler
from linear_algebra.visualizations.contracts import VisualContract
from linear_algebra.visualizations.evidence import build_evidence_ledger
from services.scene_commands import SceneCommandService
from tests.teaching_fixtures import composition_artifact_payload, projection_artifact_payload


def _permissive_contract(topic_id: str) -> VisualContract:
    return VisualContract(topic_id, (), (), (), (), 1)


def test_compiler_emits_valid_plan_and_stable_digest() -> None:
    artifact = TeachingArtifact.from_dict(composition_artifact_payload())
    contract = _permissive_contract(artifact.topic_id)
    context = RenderContext.default(artifact.topic_id)

    first = VisualSemanticsCompiler().compile(artifact, contract, context)
    second = VisualSemanticsCompiler().compile(artifact, contract, context)

    assert first.plan_digest == second.plan_digest
    assert first.plan.scene == "2d"
    assert SceneCommandService().validate(first.plan).valid
    assert first.aliases_for("Bx") == ("sem__Bx", "sem__Bx__end")
    assert {operation["op"] for operation in first.plan.operations} >= {
        "linear.upsert",
        "linear_algebra.matrix_transform",
        "view.fit",
    }


def test_compiler_rejects_contract_gap_before_renderer() -> None:
    artifact = TeachingArtifact.from_dict(projection_artifact_payload(with_residual=False))
    contract = VisualContract(
        artifact.topic_id,
        (),
        ("vector_a", "direction", "projection", "foot", "residual"),
        ("projects_to",),
        (),
        1,
    )

    with pytest.raises(VisualCompileError) as error:
        VisualSemanticsCompiler().compile(artifact, contract, RenderContext.default(artifact.topic_id))

    assert any(issue.code == "missing_entity_role" for issue in error.value.issues)


def test_compiler_does_not_require_or_invoke_a_scene_host() -> None:
    payload = composition_artifact_payload()
    payload["visual_semantics"] = {
        "scene_kind": "3d",
        "entities": [
            {
                "id": "u",
                "kind": "vector",
                "dimension": 3,
                "value": [1, 2, 1],
                "role": "vector_a",
                "label": "u",
                "claim_refs": [],
            }
        ],
        "relations": [],
        "stages": [
            {
                "id": "stage.u",
                "title": "向量",
                "caption": "三维向量",
                "layout": "sequence",
                "input_entity_refs": ["u"],
                "output_entity_refs": ["u"],
                "relation_refs": [],
                "expected_invariants": [],
            }
        ],
    }
    semantics = VisualSemantics.from_dict(payload["visual_semantics"])  # type: ignore[arg-type]
    compiled = VisualSemanticsCompiler().compile(
        semantics,
        _permissive_contract("ch02.matrix.composition"),
        RenderContext.default("ch02.matrix.composition"),
    )

    assert compiled.plan.scene == "3d"
    assert any(operation["op"] == "linear3d.upsert" for operation in compiled.plan.operations)
    assert SceneCommandService().validate(compiled.plan).valid


def test_evidence_ledger_rejects_relation_without_compiled_endpoint() -> None:
    artifact = TeachingArtifact.from_dict(composition_artifact_payload())

    class AliasView:
        def aliases_for(self, semantic_id: str) -> tuple[str, ...]:
            return {
                "x": ("x",),
                "B_maps_x_to_Bx": ("mapping",),
            }.get(semantic_id, ())

    _, issues = build_evidence_ledger(artifact, AliasView())  # type: ignore[arg-type]

    assert any(issue.code == "missing_endpoint_evidence" for issue in issues)
