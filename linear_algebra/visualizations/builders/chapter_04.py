"""Chapter 4 family-bound builders."""
from __future__ import annotations
from linear_algebra.visualizations.common import RenderContext
from services.scene_commands import CommandPlan

_IDS = ("subspace.col-null", "dependence.redundancy", "basis.definition", "linear-map.definition", "linear-map.compare", "linear-map.matrix-columns", "kernel-image", "rank-nullity")

def _compile_evidence(topic: str):
    """Load the reviewed semantic graph and compile it through the real contract."""
    from linear_algebra.teaching.chapter_artifacts import load_reviewed_artifacts
    from linear_algebra.teaching.model import TeachingArtifact
    from linear_algebra.visualizations.compiler import VisualSemanticsCompiler
    from linear_algebra.visualizations.contracts import contract_for

    artifact = TeachingArtifact.from_dict(load_reviewed_artifacts()[topic])
    contract = contract_for(topic)
    compiled = VisualSemanticsCompiler().compile(artifact, contract, RenderContext.default(topic))
    return artifact, contract, artifact.source, compiled


def _build(context: RenderContext, artifact=None, contract=None, source_context=None, compiled=None) -> CommandPlan:
    topic = context.topic_id
    topic = topic.removeprefix("draw.")
    if compiled is None:
        artifact, contract, source_context, compiled = _compile_evidence(topic)
    if artifact is None or contract is None or source_context is None or compiled is None:
        raise ValueError(f"chapter 4 builder requires semantic evidence for {topic}")
    if getattr(artifact, "topic_id", None) != topic or getattr(contract, "topic_id", None) != topic:
        raise ValueError(f"chapter 4 evidence topic mismatch for {topic}")
    if getattr(source_context, "source_hash", None) != artifact.source.source_hash:
        raise ValueError(f"chapter 4 source context mismatch for {topic}")
    return compiled.plan

BUILDERS = {f"draw.ch04.{item}": _build for item in _IDS}
