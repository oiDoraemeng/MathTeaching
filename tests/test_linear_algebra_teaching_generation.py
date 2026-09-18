"""Stable metadata and selection tests for explanation draft generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from linear_algebra.catalog.chapter_02 import TOPICS
from linear_algebra.teaching.agent import TeachingArtifactDraft
from linear_algebra.teaching.generation import GenerationRequest, generate_draft, topics_for_request
from linear_algebra.teaching.profiles import profile_for
from linear_algebra.teaching.source import LectureSourceRepository
from tests.teaching_fixtures import composition_artifact_payload


class FakeAgent:
    def generate(self, context, topic, profile, vocabulary):
        from linear_algebra.teaching.model import TeachingArtifact

        artifact = TeachingArtifact.from_dict(composition_artifact_payload())
        return TeachingArtifactDraft(artifact=artifact, raw_reply=json.dumps(artifact.to_dict(), ensure_ascii=False))


def _request() -> GenerationRequest:
    topic = next(item for item in TOPICS if item.id == "ch02.matrix.composition")
    context = LectureSourceRepository(Path(".agents/线性代数讲义.md")).context_for(topic)
    return GenerationRequest(context=context, topic=topic, profile=profile_for(topic.id))


def test_generation_receipt_records_source_and_prompt_versions() -> None:
    draft = generate_draft(FakeAgent(), _request())
    assert draft.artifact.generated.source_hash == _request().context.source_hash
    assert draft.artifact.generated.prompt_version == "teaching-artifact-v1"
    assert draft.artifact.generated.schema_version == 1
    assert draft.artifact.generated.provider == "fixture"
    assert draft.artifact.status == "draft"


def test_topic_selection_requires_exactly_one_selector() -> None:
    with pytest.raises(ValueError):
        topics_for_request(TOPICS)
    with pytest.raises(ValueError):
        topics_for_request(TOPICS, topic_id=TOPICS[0].id, chapter=1)
    assert topics_for_request(TOPICS, topic_id="ch02.matrix.composition")[0].id == "ch02.matrix.composition"
    assert len(topics_for_request(TOPICS, chapter=2)) == 11
