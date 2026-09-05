"""Contract tests for the non-rendering explanation-agent boundary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from linear_algebra.catalog.chapter_02 import TOPICS
from linear_algebra.teaching.agent import ProviderExplanationAgent
from linear_algebra.teaching.profiles import profile_for
from linear_algebra.teaching.source import LectureSourceRepository
from linear_algebra.teaching.vocabulary import VisualVocabulary
from tests.teaching_fixtures import composition_artifact_payload


class FakeProvider:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.request: tuple[str, str] | None = None

    def request_json(self, *, system: str, user: str) -> str:
        self.request = (system, user)
        return self.reply


def _inputs():
    topic = next(item for item in TOPICS if item.id == "ch02.matrix.composition")
    context = LectureSourceRepository(Path(".agents/线性代数讲义.md")).context_for(topic)
    return context, topic


def test_provider_adapter_returns_a_draft_without_scene_access() -> None:
    context, topic = _inputs()
    raw_reply = json.dumps(composition_artifact_payload(), ensure_ascii=False)
    provider = FakeProvider(raw_reply)

    draft = ProviderExplanationAgent(provider).generate(
        context, topic, profile_for(topic.id), VisualVocabulary.v1()
    )

    assert draft.artifact.topic_id == topic.id
    assert draft.raw_reply == raw_reply
    assert provider.request is not None
    system, user = provider.request
    assert "JSON" in system
    assert context.excerpt in user
    assert "CommandPlan" not in user
    assert "scene op" not in user.lower()


def test_provider_exception_is_propagated_without_creating_a_draft() -> None:
    context, topic = _inputs()

    class Cancelled(Exception):
        pass

    class CancellingProvider:
        def request_json(self, *, system: str, user: str) -> str:
            raise Cancelled("request cancelled")

    with pytest.raises(Cancelled, match="request cancelled"):
        ProviderExplanationAgent(CancellingProvider()).generate(
            context, topic, profile_for(topic.id), VisualVocabulary.v1()
        )


def test_context_topic_mismatch_is_rejected_before_provider_request() -> None:
    context, topic = _inputs()
    other_topic = next(item for item in TOPICS if item.id == "ch02.matrix.basis")
    provider = FakeProvider("{}")

    with pytest.raises(ValueError, match="does not match"):
        ProviderExplanationAgent(provider).generate(
            context, other_topic, profile_for(other_topic.id), VisualVocabulary.v1()
        )
    assert provider.request is None
