from __future__ import annotations

from agent.session_store import SessionStore
from agent.ui_projection import build_session_snapshot, project_runtime_event
from agent.events import AgentEvent
from agent.model_catalog import CustomModelStore


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
def test_model_catalog_redacts_custom_api_keys_and_validates_context_tiers(tmp_path, monkeypatch) -> None:
    from PySide6.QtCore import QSettings

    settings = QSettings("Math3DTeachingTests", "CatalogProjection")
    settings.clear()
    monkeypatch.setattr(CustomModelStore, "_settings", staticmethod(lambda: settings))
    CustomModelStore.save("custom-1", {"base_url": "https://example.test/v1", "model": "math", "api_key": "sentinel", "input_context": "64K", "output_context": "16K"})
    snapshot = build_session_snapshot(SessionStore(app_root=tmp_path), active_session_id=None)
    assert "sentinel" not in str(snapshot)
    assert snapshot["model_catalog"]["custom"][0]["id"] == "custom-1"
    try:
        CustomModelStore.save("bad", {"base_url": "https://example.test/v1", "model": "math", "input_context": "999K"})
    except ValueError as error:
        assert str(error) == "invalid_input_context"
    else:
        raise AssertionError("unsupported context tiers must be rejected")
    settings.clear()


def test_closed_session_is_marked_for_tabs_but_kept_in_history(tmp_path) -> None:
    store = SessionStore(app_root=tmp_path)
    closed = store.create_session("Closed")
    open_session = store.create_session("Open")
    store.close_session(closed.id)

    snapshot = build_session_snapshot(store, active_session_id=open_session.id)

    by_id = {item["id"]: item for item in snapshot["sessions"]}
    assert by_id[closed.id]["closed"] is True
    assert by_id[open_session.id]["closed"] is False
    assert any(item["id"] == closed.id for item in snapshot["history"]["visible"])
