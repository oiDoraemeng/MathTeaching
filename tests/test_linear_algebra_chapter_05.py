from linear_algebra.visualizations.chapter_05 import RECIPES
from linear_algebra.visualizations.common import RenderContext
from services.scene_commands import SceneCommandService
import copy
import pytest

def test_chapter5_eight_recipes_validate():
    assert len(RECIPES)==8
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
    ("ch05.elementary-matrix-elimination", "elementary_matrices"),
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


def test_chapter5_consistency_emits_three_state_operations():
    from linear_algebra.teaching.chapter_artifacts import load_reviewed_artifacts
    from linear_algebra.teaching.model import TeachingArtifact
    from linear_algebra.visualizations.compiler import VisualSemanticsCompiler
    from linear_algebra.visualizations.contracts import contract_for
    topic = "ch05.consistency.geometry"
    compiled = VisualSemanticsCompiler().compile(TeachingArtifact.from_dict(load_reviewed_artifacts()[topic]), contract_for(topic), RenderContext.default(topic))
    tableau = [op for op in compiled.plan.operations if op.get("op") == "geometry.elimination_tableau"]
    assert {op["stages"][0]["solution_state"] for op in tableau} == {"unique", "none", "infinite"}
