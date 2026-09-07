"""Renderer-free compilation tests for teaching visual semantics."""

from __future__ import annotations

import pytest

from linear_algebra.teaching.model import TeachingArtifact, VisualSemantics
from linear_algebra.visualizations.common import RenderContext
from linear_algebra.visualizations.compiler import VisualCompileError, VisualSemanticsCompiler, storyboard_visibility
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
    assert tuple(stage.id for stage in first.storyboard) == ("stage.apply-B", "stage.apply-A")
    assert all(stage.visible_aliases for stage in first.storyboard)
    assert storyboard_visibility(first, "stage.apply-B")[1] != storyboard_visibility(first, "stage.apply-A")[1]
    assert "sem__stage.apply-B__title" in storyboard_visibility(first, "stage.apply-B")[1]
    assert "sem__stage.apply-A__title" not in storyboard_visibility(first, "stage.apply-B")[1]
    operation_names = [operation["op"] for operation in first.plan.operations]
    assert operation_names[-1] == "view.fit"
    assert operation_names.count("annotation.upsert") >= 2
    assert set(operation_names) >= {
        "linear.upsert",
        "linear_algebra.matrix_transform",
        "view.fit",
    }


def test_addition_storyboard_contains_distinct_geometry_examples() -> None:
    semantics = VisualSemantics.from_dict({
            "scene_kind": "2d",
            "entities": [
                {"id": "a", "kind": "vector", "dimension": 2, "value": [3, 1], "role": "vector_a", "label": "a", "claim_refs": []},
                {"id": "b", "kind": "vector", "dimension": 2, "value": [1, 2], "role": "vector_b", "label": "b", "claim_refs": []},
                {"id": "sum", "kind": "vector", "dimension": 2, "value": [4, 3], "role": "transformed_a", "label": "a+b", "claim_refs": []},
            ],
            "relations": [{"id": "sum-rel", "kind": "sum", "source_ref": "a", "target_ref": "b", "parameters": {}, "claim_refs": []}],
            "stages": [
                {"id": "stage.triangle", "title": "观察对象", "caption": "", "layout": "sequence", "input_entity_refs": ["a", "b"], "output_entity_refs": ["sum"], "relation_refs": ["sum-rel"], "expected_invariants": []},
                {"id": "stage.parallelogram", "title": "代数验证", "caption": "", "layout": "sequence", "input_entity_refs": ["a", "b"], "output_entity_refs": ["sum"], "relation_refs": ["sum-rel"], "expected_invariants": []},
            ],
        })
    compiled = VisualSemanticsCompiler().compile(semantics, _permissive_contract("ch01.ops.addition"), RenderContext.default("ch01.ops.addition"), topic_id="ch01.ops.addition")
    first, second = compiled.storyboard
    assert first.title == "三角形法则"
    assert second.title == "平行四边形法则"
    assert first.visible_aliases != second.visible_aliases
    assert any("triangle" in alias for alias in first.visible_aliases)
    assert any("parallelogram" in alias for alias in second.visible_aliases)


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


def test_storyboard_anchor_overflow_is_explicit() -> None:
    artifact = TeachingArtifact.from_dict(composition_artifact_payload())
    context = RenderContext(artifact.topic_id, bounds=(-0.24, 0.24, -0.24, 0.24), seed=17)

    with pytest.raises(VisualCompileError) as error:
        VisualSemanticsCompiler().compile(artifact, _permissive_contract(artifact.topic_id), context)

    assert any(issue.code == "layout_overflow" for issue in error.value.issues)


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


def test_compiler_maps_signed_area_and_volume_orientation_primitives() -> None:
    area = VisualSemantics.from_dict(
        {
            "scene_kind": "2d",
            "entities": [
                {
                    "id": "area",
                    "kind": "area",
                    "dimension": 2,
                    "value": [[2, 0], [0, 1]],
                    "role": "area",
                    "label": "oriented area",
                    "claim_refs": [],
                }
            ],
            "relations": [],
            "stages": [
                {
                    "id": "stage.area",
                    "title": "有向面积",
                    "caption": "",
                    "layout": "sequence",
                    "input_entity_refs": ["area"],
                    "output_entity_refs": ["area"],
                    "relation_refs": [],
                    "expected_invariants": [],
                }
            ],
        }
    )
    volume = VisualSemantics.from_dict(
        {
            "scene_kind": "3d",
            "entities": [
                {
                    "id": "volume",
                    "kind": "volume",
                    "dimension": 3,
                    "value": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
                    "role": "volume",
                    "label": "oriented volume",
                    "claim_refs": [],
                }
            ],
            "relations": [],
            "stages": [
                {
                    "id": "stage.volume",
                    "title": "有向体积",
                    "caption": "",
                    "layout": "sequence",
                    "input_entity_refs": ["volume"],
                    "output_entity_refs": ["volume"],
                    "relation_refs": [],
                    "expected_invariants": [],
                }
            ],
        }
    )

    area_plan = VisualSemanticsCompiler().compile(area, _permissive_contract("ch01.ops.cross-product"), RenderContext.default("ch01.ops.cross-product")).plan
    volume_plan = VisualSemanticsCompiler().compile(volume, _permissive_contract("ch03.det.multiplicativity"), RenderContext.default("ch03.det.multiplicativity")).plan

    assert any(operation["op"] == "geometry.oriented_area" for operation in area_plan.operations)
    assert any(operation["op"] == "geometry.oriented_volume" for operation in volume_plan.operations)
    assert SceneCommandService().validate(area_plan).valid
    assert SceneCommandService().validate(volume_plan).valid
