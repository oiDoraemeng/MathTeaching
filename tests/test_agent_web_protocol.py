from __future__ import annotations

import pytest

from agent.events import AgentEvent
from agent.web_protocol import (
    MAX_PAYLOAD_BYTES,
    BridgeEnvelope,
    ProtocolError,
    parse_client_message,
    parse_envelope,
    serialize_event,
)


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


def test_envelope_requires_version_request_and_sequence() -> None:
    envelope = parse_envelope(
        {
            "protocol_version": 1,
            "type": "message_delta",
            "request_id": "req-1",
            "session_id": "s1",
            "turn_id": "t1",
            "sequence": 3,
            "payload": {"text": "hello"},
        }
    )

    assert isinstance(envelope, BridgeEnvelope)
    assert envelope.sequence == 3
    assert envelope.payload == {"text": "hello"}


def test_envelope_rejects_bad_version_unknown_type_and_large_payload() -> None:
    base = {
        "protocol_version": 1,
        "type": "send_message",
        "request_id": "req-1",
        "session_id": "s1",
        "payload": {"text": "hello"},
    }
    with pytest.raises(ValueError, match="protocol_version"):
        parse_envelope({**base, "protocol_version": 2})
    with pytest.raises(ValueError, match="unknown message"):
        parse_envelope({**base, "type": "run_python"})
    with pytest.raises(ValueError, match="payload"):
        parse_envelope({**base, "payload": {"text": "x" * MAX_PAYLOAD_BYTES}})


def test_snapshot_and_stop_intents_keep_id_rules() -> None:
    snapshot = parse_envelope(
        {
            "protocol_version": 1,
            "type": "request_snapshot",
            "request_id": "req-1",
            "session_id": "s1",
            "payload": {},
        }
    )
    assert snapshot.type == "request_snapshot"
    with pytest.raises(ValueError, match="turn_id"):
        parse_envelope(
            {
                "protocol_version": 1,
                "type": "approve_plan",
                "request_id": "req-2",
                "session_id": "s1",
                "payload": {},
            }
        )


def test_unknown_envelope_type_uses_stable_protocol_error_code() -> None:
    with pytest.raises(ProtocolError) as raised:
        parse_envelope({"protocol_version": 1, "type": "run_python", "request_id": "r", "session_id": "s", "payload": {}})
    assert raised.value.code == "unknown_message_type"


def test_capability_events_require_their_bounded_structured_fields() -> None:
    event = parse_envelope(
        {
            "protocol_version": 1,
            "type": "tool_finished",
            "request_id": "event-1",
            "session_id": "s1",
            "turn_id": "t1",
            "sequence": 3,
            "payload": {"call_id": "call-1", "name": "scene.inspect", "status": "ok", "result_kind": "data"},
        }
    )
    assert event.payload["name"] == "scene.inspect"
    with pytest.raises(ProtocolError, match="invalid type"):
        parse_envelope(
            {
                "protocol_version": 1,
                "type": "plan_composed",
                "request_id": "event-2",
                "session_id": "s1",
                "payload": {"summary": "plan", "operation_count": "two"},
            }
        )
