"""Deterministic draft-generation requests for the explanation sub-agent."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from linear_algebra.catalog.model import LessonEntry

from .agent import ExplanationAgent, TeachingArtifactDraft
from .model import GenerationReceipt
from .profiles import TeachingProfile
from .prompt import PROMPT_VERSION
from .source import SourceContext
from .vocabulary import VisualVocabulary


@dataclass(frozen=True)
class GenerationRequest:
    """All deterministic inputs needed for one explanation draft."""

    context: SourceContext
    topic: LessonEntry
    profile: TeachingProfile


def generate_draft(agent: ExplanationAgent, request: GenerationRequest) -> TeachingArtifactDraft:
    """Generate one draft and attach reproducibility metadata.

    Provider/model identity and digest values come from the adapter's receipt;
    this function only binds the source, prompt, and artifact schema versions
    known by the local contract.
    """

    draft = agent.generate(
        request.context,
        request.topic,
        request.profile,
        VisualVocabulary.v1(),
    )
    receipt = replace(
        draft.artifact.generated,
        source_hash=request.context.source_hash,
        prompt_version=PROMPT_VERSION,
        schema_version=1,
    )
    artifact = replace(draft.artifact, generated=receipt, status="draft")
    return replace(draft, artifact=artifact)


def topics_for_request(
    entries: Iterable[LessonEntry], *, topic_id: str | None = None, chapter: int | None = None
) -> tuple[LessonEntry, ...]:
    """Select topics deterministically for a topic or chapter generation run."""

    records = tuple(entries)
    if (topic_id is None) == (chapter is None):
        raise ValueError("exactly one of topic_id or chapter is required")
    if topic_id is not None:
        selected = tuple(entry for entry in records if entry.id == topic_id)
        if not selected:
            raise ValueError(f"unknown topic id: {topic_id}")
        return selected
    assert chapter is not None
    selected = tuple(entry for entry in records if entry.chapter_number == chapter)
    if not selected:
        raise ValueError(f"unknown chapter: {chapter}")
    return selected


__all__ = ["GenerationRequest", "generate_draft", "topics_for_request"]
