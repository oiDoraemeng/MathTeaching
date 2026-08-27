from __future__ import annotations

import json
import sqlite3

from agent.scene_snapshot import SceneSnapshot
from agent.session_store import SessionStore


def test_store_migrates_existing_sessions_table_with_hidden_at(tmp_path) -> None:
    math_root = tmp_path / ".math"
    math_root.mkdir()
    database_path = math_root / "mathagent.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                active_mode TEXT NOT NULL DEFAULT 'Agent',
                execution_mode TEXT NOT NULL DEFAULT 'confirm',
                model TEXT NOT NULL DEFAULT '',
                current_turn_id TEXT,
                last_opened_at TEXT,
                closed_at TEXT,
                parent_session_id TEXT
            )
            """
        )
        connection.execute(
            """
            INSERT INTO sessions
            (id, title, created_at, updated_at, active_mode, execution_mode, model,
             last_opened_at, parent_session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("legacy", "Legacy Chat", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z", "Agent", "confirm", "", "2026-01-01T00:00:00Z", None),
        )

    store = SessionStore(app_root=tmp_path)

    with sqlite3.connect(database_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(sessions)")}
    assert "hidden_at" in columns
    assert store.get_session("legacy").hidden_at is None


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


def test_session_thinking_preferences_round_trip_and_validate_level(tmp_path) -> None:
    store = SessionStore(app_root=tmp_path)
    session = store.create_session("Chat")
    assert session.thinking_enabled is True
    assert session.thinking_level == "High"

    updated = store.set_session_preferences(session.id, thinking_enabled=False, thinking_level="Low")
    assert updated.thinking_enabled is False
    assert updated.thinking_level == "Low"

    try:
        store.set_session_preferences(session.id, thinking_level="Extreme")
    except ValueError as error:
        assert str(error) == "invalid_thinking_level"
    else:
        raise AssertionError("unsupported thinking levels must be rejected")
