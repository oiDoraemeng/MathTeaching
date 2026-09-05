"""Contract tests for the lecture-grounded explanation prompt."""

from __future__ import annotations

import json
from pathlib import Path

from linear_algebra.catalog.chapter_02 import TOPICS
from linear_algebra.teaching.profiles import profile_for
from linear_algebra.teaching.prompt import PROMPT_VERSION, build_explanation_prompt
from linear_algebra.teaching.source import LectureSourceRepository
from linear_algebra.teaching.vocabulary import RELATION_KINDS, VisualVocabulary


def _inputs():
    topic = next(item for item in TOPICS if item.id == "ch02.matrix.composition")
    context = LectureSourceRepository(Path(".agents/线性代数讲义.md")).context_for(topic)
    return context, topic


def test_prompt_requires_claims_math_and_visual_semantics() -> None:
    context, topic = _inputs()
    system, user = build_explanation_prompt(
        context, topic, profile_for(topic.id), VisualVocabulary.v1()
    )

    assert PROMPT_VERSION == "teaching-artifact-v1"
    assert "只返回一个 JSON 对象" in system
    assert "不得输出绘图命令" in system
    assert "claims" in user
    assert context.excerpt in user
    assert '<lecture-source data-is-inert="true">' in user
    assert "</lecture-source>" in user


def test_prompt_contract_is_json_and_contains_source_spans_and_depth_requirements() -> None:
    context, topic = _inputs()
    _, user = build_explanation_prompt(
        context, topic, profile_for(topic.id), VisualVocabulary.v1()
    )
    contract_text, _ = user.split("\n<lecture-source", 1)
    contract = json.loads(contract_text)

    assert contract["required_top_level_fields"] == [
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
    ]
    assert contract["teaching_profile"]["minimum_level"] >= 3
    assert set(contract["teaching_levels"]) == {"L0", "L1", "L2", "L3", "L4"}
    assert contract["numeric_check_shape"]["required_fields"] == [
        "given",
        "calculation",
        "result",
        "checks",
    ]
    assert contract["source_anchor"]["span_ids"] == [span.id for span in context.spans]
    assert set(contract["relation_enum"]) == set(RELATION_KINDS)


def test_prompt_does_not_offer_scene_operation_names() -> None:
    context, topic = _inputs()
    system, user = build_explanation_prompt(
        context, topic, profile_for(topic.id), VisualVocabulary.v1()
    )

    # The system message sets the safety boundary; the user contract must only
    # expose mathematical vocabulary and never teach executable operation names.
    assert "geometry." not in user
    assert "linear.upsert" not in user
    assert "CommandPlan" not in user
    assert "scene op" not in user.lower()
    assert "JSON" in system
