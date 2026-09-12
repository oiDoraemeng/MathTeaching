"""Strict Chapter 5 artifact-backed builders."""
from __future__ import annotations
from linear_algebra.visualizations.common import RenderContext

_IDS = ("homogeneous.solution-space", "affine.solution-set", "consistency.geometry", "gaussian-elimination", "least-squares.projection", "fundamental-solution-system", "elementary-matrix-elimination", "least-squares-derivation")

def _compile(context, *args, **kwargs):
    from linear_algebra.teaching.chapter_artifacts import load_reviewed_artifacts
    from linear_algebra.teaching.model import TeachingArtifact
    from linear_algebra.visualizations.compiler import VisualSemanticsCompiler
    from linear_algebra.visualizations.contracts import contract_for
    topic = context.topic_id.removeprefix("draw.")
    artifact = TeachingArtifact.from_dict(load_reviewed_artifacts()[topic])
    compiled = VisualSemanticsCompiler().compile(artifact, contract_for(topic), RenderContext.default(topic))
    return compiled.plan

BUILDERS = {f"draw.ch05.{item}": _compile for item in _IDS}
