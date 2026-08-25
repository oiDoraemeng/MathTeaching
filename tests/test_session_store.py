from __future__ import annotations

import json
import sqlite3

from agent.scene_snapshot import SceneSnapshot
from agent.session_store import SessionStore


def test_store_creates_math_database_and_round_trips_turn(tmp_path) -> None:
    empty = SceneSnapshot()
    curve = SceneSnapshot(curves=({"alias": "f", "expression": "y=x^2"},))
    store = SessionStore(app_root=tmp_path)

    session = store.create_session("New Chat", model="deepseek-chat")
    turn_id = store.append_turn(
        session.id,
        user_message="画 y=x^2",
        assistant_message="已生成曲线计划",
        scene_before=empty,
        scene_after=curve,
        command_plan={"version": 1, "operations": []},
        status="completed",
    )

    assert (tmp_path / ".math" / "mathagent.db").exists()
    assert store.get_turn(turn_id).scene_after == curve

    with sqlite3.connect(tmp_path / ".math" / "mathagent.db") as connection:
        assert connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"


def test_store_preserves_session_metadata_and_closed_history(tmp_path) -> None:
    store = SessionStore(app_root=tmp_path)
    session = store.create_session(
        "Geometry",
        model="local-model",
        active_mode="Plan",
        execution_mode="confirm",
        parent_session_id="parent",
    )

    store.close_session(session.id)

    reopened = store.reopen_session(session.id)
    assert reopened.title == "Geometry"
    assert reopened.model == "local-model"
    assert reopened.active_mode == "Plan"
    assert reopened.execution_mode == "confirm"
    assert reopened.parent_session_id == "parent"
    assert store.list_sessions(include_closed=True)[0].id == session.id


def test_store_round_trips_events_attachments_and_app_state(tmp_path) -> None:
    store = SessionStore(app_root=tmp_path)
    session = store.create_session("Chat")
    store.append_event(session.id, "plan_ready", {"plan_id": "p1"})
    attachment_id = store.add_attachment(
        session.id,
        turn_id=None,
        relative_path="attachments/a.txt",
        mime_type="text/plain",
        byte_size=3,
        sha256="abc",
    )
    store.save_app_state(
        {"open_session_ids": [session.id], "active_session_id": session.id, "scene": {"version": 1}}
    )

    assert attachment_id
    assert store.list_events(session.id)[0].payload == {"plan_id": "p1"}
    assert store.list_attachments(session.id)[0].sha256 == "abc"
    assert store.load_app_state()["active_session_id"] == session.id


def test_store_rejects_unknown_snapshot_version(tmp_path) -> None:
    store = SessionStore(app_root=tmp_path)
    session = store.create_session("Chat")
    invalid = {"version": 99}

    try:
        store.append_turn(
            session.id,
            user_message="x",
            assistant_message="y",
            scene_before=invalid,
            scene_after=invalid,
            command_plan={},
            status="failed",
        )
    except ValueError as error:
        assert "snapshot" in str(error)
    else:
        raise AssertionError("invalid snapshots must be rejected")
