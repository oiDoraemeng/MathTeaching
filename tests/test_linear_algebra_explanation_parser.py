"""Executable-leakage and exact JSON tests for explanation replies."""

from __future__ import annotations

import json

import pytest

from linear_algebra.teaching.parser import AgentReplyError, parse_agent_reply

from tests.teaching_fixtures import composition_artifact_payload


@pytest.mark.parametrize(
    "raw",
    [
        "```json\n{}\n```",
        '{"op":"geometry.staged_transform"}',
        '{"note":"PySide6.QtWidgets.QWidget"}',
        '{"note":"linear.upsert"}',
    ],
)
def test_parser_rejects_non_contract_or_executable_reply(raw: str) -> None:
    with pytest.raises(AgentReplyError):
        parse_agent_reply(raw, expected_topic_id="ch02.matrix.composition")


def test_parser_rejects_wrong_topic_id() -> None:
    payload = composition_artifact_payload()
    payload["topic_id"] = "other"
    with pytest.raises(AgentReplyError, match="topic_id"):
        parse_agent_reply(json.dumps(payload, ensure_ascii=False), expected_topic_id="ch02.matrix.composition")


def test_parser_accepts_valid_bare_json_and_returns_typed_artifact() -> None:
    raw = json.dumps(composition_artifact_payload(), ensure_ascii=False)
    artifact = parse_agent_reply(raw, expected_topic_id="ch02.matrix.composition")
    assert artifact.topic_id == "ch02.matrix.composition"
    assert artifact.claims[0].formula_symbols == ("A", "B", "x", "Bx", "ABx")


@pytest.mark.parametrize(
    "payload",
    [
        {"nested": {"operations": []}},
        {"nested": {"note": "linear3d.upsert"}},
        {"nested": {"note": "<script>alert(1)</script>"}},
    ],
)
def test_parser_scans_nested_keys_and_values(payload: dict[str, object]) -> None:
    with pytest.raises(AgentReplyError, match="executable_leakage"):
        parse_agent_reply(json.dumps(payload), expected_topic_id="ch02.matrix.composition")


def test_parser_allows_mathematical_operation_word() -> None:
    payload = {"explanation": "The operation preserves orientation."}
    # The payload is intentionally incomplete; this assertion isolates the
    # leakage scanner from schema validation.
    with pytest.raises(AgentReplyError) as error:
        parse_agent_reply(json.dumps(payload), expected_topic_id="ch02.matrix.composition")
    assert error.value.code == "artifact_invalid"
