from __future__ import annotations

from agent.session_store import SessionStore
from agent.ui_projection import build_session_snapshot, project_runtime_event
from agent.events import AgentEvent


def test_session_projection_contains_tabs_turns_and_preferences(tmp_path) -> None:
    store = SessionStore(app_root=tmp_path)
    session = store.create_session("Geometry", model="deepseek-chat")
    store.append_turn(
        session.id,
        user_message="画曲线",
        assistant_message="已生成计划",
        scene_before=None,
        scene_after=None,
        command_plan={"operations": []},
        status="completed",
    )
    store.append_event(session.id, "plan_ready", {"summary": "curve"})

    snapshot = build_session_snapshot(store, active_session_id=session.id, model_status={"connected": True})

    assert snapshot["active_session_id"] == session.id
    assert snapshot["sessions"][0]["mode"] == "Agent"
    assert snapshot["sessions"][0]["model"] == "deepseek-chat"
    assert snapshot["sessions"][0]["turns"][0]["user_message"] == "画曲线"
    assert snapshot["sessions"][0]["events"][0]["type"] == "plan_ready"
    assert "api_key" not in str(snapshot)


def test_runtime_event_projection_is_json_only() -> None:
    projected = project_runtime_event(AgentEvent("message_delta", {"text": "解释"}, session_id="s1", turn_id="t1"), sequence=4)

    assert projected["type"] == "message_delta"
    assert projected["session_id"] == "s1"
    assert projected["sequence"] == 4
    assert projected["payload"] == {"text": "解释"}
