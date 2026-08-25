from __future__ import annotations

import pytest

from agent.events import AgentEvent


def test_event_round_trip_preserves_payload() -> None:
    event = AgentEvent("plan_ready", {"plan_id": "p1"}, session_id="s1", turn_id="t1")

    restored = AgentEvent.from_dict(event.to_dict())

    assert restored == event


def test_event_rejects_unknown_type() -> None:
    with pytest.raises(ValueError, match="event type"):
        AgentEvent.from_dict({"type": "unknown", "payload": {}})
