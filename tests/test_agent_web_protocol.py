from __future__ import annotations

import pytest

from agent.events import AgentEvent
from agent.web_protocol import parse_client_message, serialize_event


def test_protocol_accepts_json_ui_intents() -> None:
    message = parse_client_message('{"type":"approve_plan","session_id":"s1","turn_id":"t1"}')

    assert message.type == "approve_plan"
    assert message.session_id == "s1"
    assert message.turn_id == "t1"


def test_protocol_rejects_unknown_or_missing_identifiers() -> None:
    with pytest.raises(ValueError, match="unknown message"):
        parse_client_message({"type": "run_python", "session_id": "s1"})
    with pytest.raises(ValueError, match="session_id"):
        parse_client_message({"type": "stop_session"})


def test_protocol_serializes_runtime_event() -> None:
    event = AgentEvent("plan_ready", {"summary": "curve"}, session_id="s1", turn_id="t1")

    payload = serialize_event(event)

    assert payload["type"] == "plan_ready"
    assert payload["payload"]["summary"] == "curve"
