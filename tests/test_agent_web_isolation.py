from __future__ import annotations

import json

from agent.web_protocol import CLIENT_MESSAGE_TYPES, EVENT_MESSAGE_TYPES, MAX_PAYLOAD_BYTES, parse_envelope
from ui.agent_bridge import AgentBridge


def test_protocol_matrix_and_oversized_payload_are_rejected() -> None:
    for message_type in CLIENT_MESSAGE_TYPES:
        session_id = "s1"
        turn_id = "t1" if message_type in {"approve_plan", "restore_turn", "undo_turn", "branch_turn", "branch_from_turn"} else None
        raw = {"protocol_version": 1, "type": message_type, "request_id": message_type, "session_id": session_id, "payload": {}}
        if turn_id:
            raw["turn_id"] = turn_id
        assert parse_envelope(raw).type == message_type
    assert EVENT_MESSAGE_TYPES
    oversized = {"protocol_version": 1, "type": "send_message", "request_id": "large", "session_id": "s1", "payload": {"text": "x" * MAX_PAYLOAD_BYTES}}
    try:
        parse_envelope(oversized)
    except ValueError as error:
        assert "maximum size" in str(error)
    else:
        raise AssertionError("oversized payload was accepted")


def test_bridge_error_is_serializable_and_dispatcher_has_no_renderer() -> None:
    emitted: list[dict[str, object]] = []
    bridge = AgentBridge(lambda _message: (_ for _ in ()).throw(RuntimeError("blocked")))
    bridge.event_json.connect(lambda raw: emitted.append(json.loads(raw)))
    bridge.send_json('{"protocol_version":1,"type":"send_message","request_id":"r","session_id":"s","payload":{"text":"x"}}')
    assert emitted[-1]["type"] == "error"
    assert "blocked" in str(emitted[-1]["payload"])
