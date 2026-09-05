"""Lecture-grounded, claim-first teaching contracts."""

from .agent import ExplanationAgent, JsonTextProvider, ProviderExplanationAgent, TeachingArtifactDraft
from .examples import ExampleCheck, ExampleCheckResult, verify_worked_example
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
from .revisions import ArtifactDiff, FieldChange, diff_artifacts
from .legacy import LegacyTeachingArtifact, adapt_legacy_explanation, publish_legacy_artifact
from .validation import validate_teaching_depth, validate_source_evidence, validate_worked_examples
from .content_validation import (
    ChapterArtifactReport,
    bundled_store,
    lecture_source_repository,
    validate_all_chapters,
    validate_chapter_artifacts,
)
from .source import LectureSourceRepository, SourceContext, SourceSpan, normalize_source_text
from .store import (
    ArtifactRevision,
    LoadedArtifact,
    PublishResult,
    RawReplyAudit,
    ReviewRecord,
    StoredArtifact,
    TeachingArtifactStore,
    reply_digest,
)
from .vocabulary import VisualVocabulary

__all__ = [
    "Claim",
    "AgentReplyError",
    "LegacyTeachingArtifact",
    "ArtifactDiff",
    "FieldChange",
    "WorkedExample",
    "WorkedExampleCheck",
    "ExplanationContentV2",
    "ExampleCheck",
    "ExampleCheckResult",
    "ExplanationAgent",
    "GenerationReceipt",
    "JsonTextProvider",
    "LectureSourceRepository",
    "SourceRecord",
    "SourceContext",
    "SourceSpan",
    "TeachingArtifact",
    "TeachingArtifactDraft",
    "TeachingArtifactStore",
    "StoredArtifact",
    "ArtifactRevision",
    "LoadedArtifact",
    "RawReplyAudit",
    "PublishResult",
    "ReviewRecord",
    "reply_digest",
    "TeachingProfileRecord",
    "TopicConnection",
    "VisualEntity",
    "VisualRelation",
    "VisualSemantics",
    "VisualStage",
    "VisualVocabulary",
    "ProviderExplanationAgent",
    "parse_agent_reply",
    "diff_artifacts",
    "adapt_legacy_explanation",
    "publish_legacy_artifact",
    "validate_source_evidence",
    "validate_teaching_depth",
    "verify_worked_example",
    "validate_worked_examples",
    "normalize_source_text",
    "ChapterArtifactReport",
    "bundled_store",
    "lecture_source_repository",
    "validate_all_chapters",
    "validate_chapter_artifacts",
]
