"""Lecture-grounded, claim-first teaching contracts."""

from .agent import ExplanationAgent, JsonTextProvider, ProviderExplanationAgent, TeachingArtifactDraft
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
from .vocabulary import VisualVocabulary

__all__ = [
    "Claim",
    "ExplanationContentV2",
    "ExplanationAgent",
    "GenerationReceipt",
    "JsonTextProvider",
    "LectureSourceRepository",
    "SourceRecord",
    "SourceContext",
    "SourceSpan",
    "TeachingArtifact",
    "TeachingArtifactDraft",
    "TeachingProfileRecord",
    "TopicConnection",
    "VisualEntity",
    "VisualRelation",
    "VisualSemantics",
    "VisualStage",
    "VisualVocabulary",
    "ProviderExplanationAgent",
    "normalize_source_text",
]
