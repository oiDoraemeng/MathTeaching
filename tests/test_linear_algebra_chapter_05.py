from linear_algebra.visualizations.chapter_05 import RECIPES
from linear_algebra.visualizations.common import RenderContext
from services.scene_commands import SceneCommandService

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
    try: VisualSemanticsCompiler().compile(TeachingArtifact.from_dict(p), contract_for('ch05.gaussian-elimination'), RenderContext.default('ch05.gaussian-elimination'))
    except (VisualCompileError, ValueError): return
    assert False
