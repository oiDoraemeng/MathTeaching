from linear_algebra.visualizations.common import RenderContext
_IDS=('eigen.direction','characteristic-polynomial','eigenspace','diagonalization')
def _build(context,*args,**kwargs):
    from linear_algebra.teaching.chapter_artifacts import load_reviewed_artifacts
    from linear_algebra.teaching.model import TeachingArtifact
    from linear_algebra.visualizations.compiler import VisualSemanticsCompiler
    from linear_algebra.visualizations.contracts import contract_for
    topic=context.topic_id.removeprefix('draw.')
    return VisualSemanticsCompiler().compile(TeachingArtifact.from_dict(load_reviewed_artifacts()[topic]),contract_for(topic),context).plan
BUILDERS={f'draw.ch07.{item}':_build for item in _IDS}
