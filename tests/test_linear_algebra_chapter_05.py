from linear_algebra.visualizations.chapter_05 import RECIPES
from linear_algebra.visualizations.common import RenderContext
from services.scene_commands import SceneCommandService
import copy
import pytest

def test_chapter5_five_recipes_validate():
    assert len(RECIPES)==5
    service=SceneCommandService()
    for recipe in RECIPES:
        plan=recipe.builder(RenderContext.default(recipe.id))
        assert service.validate(plan).valid
        assert any(op['op'].startswith('geometry.') for op in plan.operations)

def test_chapter5_corrupted_reviewed_parameter_rejected():
    from linear_algebra.teaching.chapter_artifacts import load_reviewed_artifacts
    from linear_algebra.teaching.model import TeachingArtifact
    from linear_algebra.visualizations.compiler import VisualSemanticsCompiler, VisualCompileError
    from linear_algebra.visualizations.contracts import contract_for
    p=dict(load_reviewed_artifacts()['ch05.gaussian-elimination']); p['visual_semantics']=dict(p['visual_semantics']); p['visual_semantics']['relations']=[]
    with pytest.raises((VisualCompileError, ValueError)):
        VisualSemanticsCompiler().compile(TeachingArtifact.from_dict(p), contract_for('ch05.gaussian-elimination'), RenderContext.default('ch05.gaussian-elimination'))


@pytest.mark.parametrize("topic,field", [
    ("ch05.homogeneous.solution-space", "nullspace_basis"),
    ("ch05.affine.solution-set", "particular"),
    ("ch05.consistency.geometry", "consistency_states"),
    ("ch05.gaussian-elimination", "operations"),
    ("ch05.least-squares.projection", "residual"),
])
def test_chapter5_relation_parameters_are_executable_gates(topic, field):
    from linear_algebra.teaching.chapter_artifacts import load_reviewed_artifacts
    from linear_algebra.teaching.model import TeachingArtifact
    from linear_algebra.visualizations.compiler import VisualSemanticsCompiler, VisualCompileError
    from linear_algebra.visualizations.contracts import contract_for
    payload = copy.deepcopy(load_reviewed_artifacts()[topic])
    params = payload["visual_semantics"]["relations"][0]["parameters"]
    value = params[field]
    if isinstance(value, list) and value and isinstance(value[0], list) and value[0] and not isinstance(value[0][0], list):
        params[field][0][0] = float(params[field][0][0]) + 0.75
    elif isinstance(value, list) and value and isinstance(value[0], list):
        params[field][0][0][0] = float(params[field][0][0][0]) + 0.75
    elif isinstance(value, list):
        params[field][0] = float(params[field][0]) + 0.75
    else:
        params[field] = float(value) + 0.75
    with pytest.raises((VisualCompileError, ValueError)):
        VisualSemanticsCompiler().compile(TeachingArtifact.from_dict(payload), contract_for(topic), RenderContext.default(topic))


def test_chapter5_consistency_uses_the_two_lecture_system_states_and_three_panes():
    from linear_algebra.teaching.chapter_artifacts import load_reviewed_artifacts
    from linear_algebra.teaching.model import TeachingArtifact
    from linear_algebra.visualizations.compiler import VisualSemanticsCompiler
    from linear_algebra.visualizations.contracts import contract_for
    topic = "ch05.consistency.geometry"
    compiled = VisualSemanticsCompiler().compile(TeachingArtifact.from_dict(load_reviewed_artifacts()[topic]), contract_for(topic), RenderContext.default(topic))
    tableau = [op for op in compiled.plan.operations if op.get("op") == "geometry.elimination_tableau"]
    assert {op["stages"][0]["solution_state"] for op in tableau} == {"none", "infinite"}
    assert [stage.title for stage in compiled.storyboard] == [
        "目标在列空间中",
        "对应的无穷解集",
        "目标在列空间外",
    ]


def test_chapter5_explanations_keep_lecture_depth_and_matrix_layout():
    from linear_algebra.teaching.chapter_artifacts import artifact_payload_for

    homogeneous = artifact_payload_for("ch05.homogeneous.solution-space")["explanation"]
    affine = artifact_payload_for("ch05.affine.solution-set")["explanation"]
    gaussian = artifact_payload_for("ch05.gaussian-elimination")["explanation"]
    least_squares = artifact_payload_for("ch05.least-squares.projection")["explanation"]

    assert "**（齐次线性方程组）**" in homogeneous["definition"]
    assert "\\begin{pmatrix}" in homogeneous["worked_examples"][1]["calculation"][0]
    assert "2\\times3" not in homogeneous["worked_examples"][1]["calculation"][0]
    assert "\\boldsymbol x_p+\\boldsymbol z" in affine["definition"]
    assert "x_1=-2" in gaussian["worked_examples"][0]["calculation"][0]
    assert "x_1=-4" not in gaussian["worked_examples"][0]["calculation"][0]
    assert "\\boldsymbol A^{T}\\boldsymbol A\\hat{\\boldsymbol x}" in least_squares["definition"]
    assert "定义与公式" not in {section["title"] for section in least_squares["sections"]}


def test_chapter5_case_layouts_follow_the_confirmed_pane_counts():
    from linear_algebra.teaching.chapter_artifacts import artifact_payload_for

    expected = {
        "ch05.homogeneous.solution-space": (1, 1),
        "ch05.affine.solution-set": (2, 2),
        "ch05.consistency.geometry": (3, 3),
        "ch05.gaussian-elimination": (3, 3),
        "ch05.least-squares.projection": (1, 1),
    }
    for topic_id, (case_count, pane_count) in expected.items():
        layout = artifact_payload_for(topic_id)["explanation"]["case_layout"]
        assert len(layout["cases"]) == case_count
        assert layout["default_pane_count"] == pane_count
