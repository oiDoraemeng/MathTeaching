"""Read-only compatibility adapter for pre-artifact explanations."""

from __future__ import annotations

from dataclasses import dataclass

from linear_algebra.catalog.model import LessonEntry
from linear_algebra.explanations.model import ExplanationContent


@dataclass(frozen=True)
class LegacyTeachingArtifact:
    topic_id: str
    title: str
    explanation: ExplanationContent
    migration_state: str = "migration_pending"
    visual_semantics: None = None


def adapt_legacy_explanation(entry: LessonEntry, content: ExplanationContent) -> LegacyTeachingArtifact:
    if content.id != entry.explanation_id:
        raise ValueError("legacy explanation id does not match topic")
    return LegacyTeachingArtifact(topic_id=entry.id, title=content.title, explanation=content)


def publish_legacy_artifact(artifact: LegacyTeachingArtifact) -> None:
    """Reject legacy content until it has claims and visual semantics."""

    if artifact.visual_semantics is None:
        raise ValueError("legacy artifact cannot be published without visual_semantics")
    raise ValueError("legacy artifact publication is not supported")


__all__ = ["LegacyTeachingArtifact", "adapt_legacy_explanation", "publish_legacy_artifact"]
