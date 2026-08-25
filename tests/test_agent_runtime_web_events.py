from __future__ import annotations

from agent.events import AgentEvent
from agent.ui_projection import project_runtime_event


def test_runtime_events_project_to_monotonic_web_envelopes() -> None:
    first = project_runtime_event(AgentEvent("message_delta", {"text": "a"}, session_id="s", turn_id="t"), sequence=1)
    second = project_runtime_event(AgentEvent("plan_ready", {"summary": "curve"}, session_id="s", turn_id="t"), sequence=2)

    assert first["sequence"] == 1
    assert second["sequence"] == 2
    assert first["session_id"] == second["session_id"] == "s"


def test_runtime_persists_one_event_timeline_per_turn(tmp_path) -> None:
    from agent.runtime import AgentRuntime
    from agent.session_store import SessionStore

    store = SessionStore(app_root=tmp_path)
    session = store.create_session("Chat")
    runtime = AgentRuntime(session_store=store)
    result = runtime.run_turn(session.id, "解释点", mode="Ask", execution_mode="confirm")

    assert result.turn_id
    events = store.list_events(session.id, turn_id=result.turn_id)
    assert events
    assert all(event.turn_id == result.turn_id for event in events)
    assert events[-1].type == "turn_finished"
