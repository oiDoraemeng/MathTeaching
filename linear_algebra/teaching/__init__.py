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
    WorkedExample,
    WorkedExampleCheck,
)
from .parser import AgentReplyError, parse_agent_reply
from .validation import validate_teaching_depth, validate_source_evidence
from .source import LectureSourceRepository, SourceContext, SourceSpan, normalize_source_text
from .vocabulary import VisualVocabulary

__all__ = [
    "Claim",
    "AgentReplyError",
    "WorkedExample",
    "WorkedExampleCheck",
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
    "parse_agent_reply",
    "validate_source_evidence",
    "validate_teaching_depth",
    "normalize_source_text",
]
