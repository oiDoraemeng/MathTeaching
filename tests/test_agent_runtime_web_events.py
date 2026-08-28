from __future__ import annotations

from agent.events import AgentEvent
from agent.ui_projection import project_runtime_event


def test_runtime_events_project_to_monotonic_web_envelopes() -> None:
    first = project_runtime_event(AgentEvent("message_delta", {"text": "a"}, session_id="s", turn_id="t"), sequence=1)
    second = project_runtime_event(AgentEvent("plan_ready", {"summary": "curve"}, session_id="s", turn_id="t"), sequence=2)

    assert first["sequence"] == 1
    assert second["sequence"] == 2
    assert first["session_id"] == second["session_id"] == "s"


def test_snapshot_projection_normalizes_and_sanitizes_plan_events(tmp_path) -> None:
    from agent.session_store import SessionStore

    store = SessionStore(app_root=tmp_path)
    session = store.create_session("Chat")
    turn_id = store.append_turn(
        session.id,
        user_message="画点",
        assistant_message="已完成",
        scene_before=None,
        scene_after=None,
        command_plan={"summary": "画点", "operations": [{"op": "point.upsert", "api_key": "secret-token", "alias": "P"}]},
        validation={"valid": True},
        status="completed",
    )
    store.append_event(session.id, "plan_ready", {"plan": {"summary": "画点", "operations": [{"op": "point.upsert", "api_key": "secret-token", "alias": "P"}]}}, turn_id=turn_id)
    store.append_event(session.id, "validation_result", {"valid": True}, turn_id=turn_id)

    from agent.ui_projection import build_session_snapshot

    projection = build_session_snapshot(store, active_session_id=session.id)
    turn = projection["sessions"][0]["turns"][0]
    assert turn["command_plan"]["operations"][0]["validation"] == "已通过"
    assert "secret-token" not in str(turn)
    assert turn["events"][0]["type"] == "plan_ready"
    assert turn["events"][1]["type"] == "validation"


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
