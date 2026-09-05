"""Non-rendering boundary for the mathematical explanation sub-agent.

This module deliberately deals in source context, catalog identities, and
JSON-safe teaching artifacts only.  Prompt construction and strict response
parsing are separate tasks; imports for those modules are deferred so the
provider boundary can be exercised before those implementations land.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib
import json
from typing import Protocol, runtime_checkable

from linear_algebra.catalog.model import LessonEntry

from .model import TeachingArtifact
from .profiles import TeachingProfile
from .source import SourceContext
from .vocabulary import VisualVocabulary


@runtime_checkable
class JsonTextProvider(Protocol):
    """Provider contract returning one textual JSON response."""

    def request_json(self, *, system: str, user: str) -> str:
        """Request a JSON response; provider errors are intentionally exposed."""


class ExplanationAgent(Protocol):
    """Generate a lecture-grounded draft without access to a scene host."""

    def generate(
        self,
        context: SourceContext,
        topic: LessonEntry,
        profile: TeachingProfile,
        vocabulary: VisualVocabulary,
    ) -> "TeachingArtifactDraft":
        """Return one unreviewed artifact draft and its exact provider reply."""


@dataclass(frozen=True)
class TeachingArtifactDraft:
    """A parsed artifact paired with the exact accepted provider text."""

    artifact: TeachingArtifact
    raw_reply: str

    def __post_init__(self) -> None:
        if not isinstance(self.artifact, TeachingArtifact):
            raise TypeError("artifact: expected TeachingArtifact")
        if not isinstance(self.raw_reply, str):
            raise TypeError("raw_reply: expected str")


class ProviderExplanationAgent:
    """Adapt an injected JSON provider to the explanation-agent protocol.

    No scene host, command service, renderer, or UI object is accepted.  The
    provider owns cancellation; exceptions, including cancellation exceptions,
    are deliberately allowed to propagate without creating a draft.
    """

    def __init__(self, provider: JsonTextProvider) -> None:
        if not isinstance(provider, JsonTextProvider):
            raise TypeError("provider: expected an object implementing request_json")
        self.provider = provider

    def generate(
        self,
        context: SourceContext,
        topic: LessonEntry,
        profile: TeachingProfile,
        vocabulary: VisualVocabulary,
    ) -> TeachingArtifactDraft:
        if context.topic_id != topic.id:
            raise ValueError(
                f"context.topic_id {context.topic_id!r} does not match topic.id {topic.id!r}"
            )

        system, user = _build_prompt(context, topic, profile, vocabulary)
        raw_reply = self.provider.request_json(system=system, user=user)
        if not isinstance(raw_reply, str):
            raise TypeError("provider.request_json must return str")

        artifact = _parse_reply(raw_reply, expected_topic_id=topic.id)
        if not isinstance(artifact, TeachingArtifact):
            raise TypeError("agent parser must return TeachingArtifact")
        return TeachingArtifactDraft(artifact=artifact, raw_reply=raw_reply)


def _build_prompt(
    context: SourceContext,
    topic: LessonEntry,
    profile: TeachingProfile,
    vocabulary: VisualVocabulary,
) -> tuple[str, str]:
    """Use Task 8's prompt builder when available, with a narrow fallback."""

    module_name = f"{__package__}.prompt"
    try:
        prompt_module = importlib.import_module(".prompt", __package__)
    except ModuleNotFoundError as error:
        if error.name != module_name:
            raise
        return _fallback_prompt(context, topic, profile, vocabulary)

    builder = getattr(prompt_module, "build_explanation_prompt", None)
    if not callable(builder):
        raise RuntimeError("linear_algebra.teaching.prompt has no build_explanation_prompt")
    return builder(context, topic, profile, vocabulary)


def _parse_reply(raw_reply: str, *, expected_topic_id: str) -> TeachingArtifact:
    """Use Task 9's parser when available, with a strict JSON fallback."""

    module_name = f"{__package__}.parser"
    try:
        parser_module = importlib.import_module(".parser", __package__)
    except ModuleNotFoundError as error:
        if error.name != module_name:
            raise
        return _fallback_parse(raw_reply, expected_topic_id=expected_topic_id)

    parser = getattr(parser_module, "parse_agent_reply", None)
    if not callable(parser):
        raise RuntimeError("linear_algebra.teaching.parser has no parse_agent_reply")
    return parser(raw_reply, expected_topic_id=expected_topic_id)


def _fallback_prompt(
    context: SourceContext,
    topic: LessonEntry,
    profile: TeachingProfile,
    vocabulary: VisualVocabulary,
) -> tuple[str, str]:
    """Build the smallest inert-source request until Task 8 is implemented."""

    system = (
        "You are a linear-algebra mathematics explanation sub-agent. "
        "Return exactly one JSON object containing mathematical prose and "
        "non-executable visual semantics. Do not return code or executable "
        "drawing instructions."
    )
    contract = {
        "topic_id": topic.id,
        "topic_title": topic.title,
        "section_id": topic.section_id,
        "source_path": list(topic.source_path),
        "teaching_profile": profile.to_dict(),
        "visual_vocabulary": vocabulary.to_dict(),
        "required_top_level_fields": [
            "schema_version",
            "topic_id",
            "revision",
            "status",
            "source",
            "teaching_profile",
            "claims",
            "connections",
            "explanation",
            "visual_semantics",
            "generated",
        ],
    }
    user = (
        json.dumps(contract, ensure_ascii=False, sort_keys=True)
        + '\n<lecture-source data-is-inert="true">\n'
        + context.excerpt
        + "\n</lecture-source>"
    )
    return system, user


def _fallback_parse(raw_reply: str, *, expected_topic_id: str) -> TeachingArtifact:
    """Decode only the artifact model; full leakage checks belong to Task 9."""

    if not raw_reply.strip() or raw_reply.lstrip().startswith("```"):
        raise ValueError("agent reply must be one bare JSON object")
    try:
        payload = json.loads(raw_reply)
    except json.JSONDecodeError as error:
        raise ValueError("agent reply is not valid JSON") from error
    if not isinstance(payload, dict):
        raise ValueError("agent reply must decode to a JSON object")
    if "op" in payload:
        raise ValueError("agent reply must not contain executable operation fields")

    artifact = TeachingArtifact.from_dict(payload)
    if artifact.topic_id != expected_topic_id:
        raise ValueError(
            f"artifact.topic_id {artifact.topic_id!r} does not match expected {expected_topic_id!r}"
        )
    return artifact


__all__ = [
    "ExplanationAgent",
    "JsonTextProvider",
    "ProviderExplanationAgent",
    "TeachingArtifactDraft",
]
