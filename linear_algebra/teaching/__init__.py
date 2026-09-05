"""Lecture-grounded, claim-first teaching contracts."""

from .model import (
    Claim,
    ExplanationContentV2,
    GenerationReceipt,
    SourceRecord,
    TeachingArtifact,
    TeachingProfileRecord,
    TopicConnection,
    VisualEntity,
    VisualRelation,
    VisualSemantics,
    VisualStage,
)
from .source import LectureSourceRepository, SourceContext, SourceSpan, normalize_source_text

__all__ = [
    "Claim",
    "ExplanationContentV2",
    "GenerationReceipt",
    "LectureSourceRepository",
    "SourceRecord",
    "SourceContext",
    "SourceSpan",
    "TeachingArtifact",
    "TeachingProfileRecord",
    "TopicConnection",
    "VisualEntity",
    "VisualRelation",
    "VisualSemantics",
    "VisualStage",
    "normalize_source_text",
]
