def _build(context,*args,**kwargs):
    from linear_algebra.teaching.chapter_artifacts import load_reviewed_artifacts
    from linear_algebra.teaching.model import TeachingArtifact
    from linear_algebra.visualizations.compiler import VisualSemanticsCompiler
    from linear_algebra.visualizations.common import RenderContext
    topic=context.topic_id.removeprefix('draw.')
    return VisualSemanticsCompiler().compile(TeachingArtifact.from_dict(load_reviewed_artifacts()[topic]),context=RenderContext.default(topic)).plan
BUILDERS={f'draw.ch08.{name}':_build for name in ('quadratic.matrix-form','quadratic.level-sets','principal-axis','definiteness','completing-square','congruence-inertia')}
