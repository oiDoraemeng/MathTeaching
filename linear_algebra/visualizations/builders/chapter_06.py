"""Artifact-backed Chapter 6 builders."""
from linear_algebra.visualizations.common import RenderContext
_IDS=('basis-change.motivation','basis-change.coordinates','similarity-transform')
def _build(context,*args,**kwargs):
    from linear_algebra.teaching.chapter_artifacts import load_reviewed_artifacts
    from linear_algebra.teaching.model import TeachingArtifact
    from linear_algebra.visualizations.compiler import VisualSemanticsCompiler
    from linear_algebra.visualizations.contracts import contract_for
    topic=context.topic_id.removeprefix('draw.')
    return VisualSemanticsCompiler().compile(TeachingArtifact.from_dict(load_reviewed_artifacts()[topic]),contract_for(topic),RenderContext.default(topic)).plan
BUILDERS={f'draw.ch06.{item}':_build for item in _IDS}
