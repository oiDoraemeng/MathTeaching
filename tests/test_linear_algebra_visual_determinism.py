from linear_algebra.registry import bundled_teaching_store
from linear_algebra.visualizations.common import RenderContext
from linear_algebra.visualizations.compiler import VisualSemanticsCompiler


def test_compiler_plan_digest_is_stable_for_same_context() -> None:
    artifact = bundled_teaching_store().published("ch02.matrix.transformed-grid").artifact
    compiler = VisualSemanticsCompiler()
    first = compiler.compile(artifact, context=RenderContext.default(artifact.topic_id))
    second = compiler.compile(artifact, context=RenderContext.default(artifact.topic_id))
    assert first.plan_digest == second.plan_digest
    assert first.plan.operations == second.plan.operations


def test_storyboard_stage_ids_and_aliases_are_stable() -> None:
    artifact = bundled_teaching_store().published("ch03.det.multiplicativity").artifact
    compiler = VisualSemanticsCompiler()
    first = compiler.compile(artifact, context=RenderContext.default(artifact.topic_id))
    second = compiler.compile(artifact, context=RenderContext.default(artifact.topic_id))
    assert [stage.id for stage in first.storyboard] == [stage.id for stage in second.storyboard]
    assert [stage.visible_aliases for stage in first.storyboard] == [stage.visible_aliases for stage in second.storyboard]
