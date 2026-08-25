"""SQLite-backed local persistence for MathAgent conversations."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import sqlite3
from typing import Any, Iterator, Mapping
from uuid import uuid4

from .scene_snapshot import SceneSnapshot


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid4().hex


def _snapshot_json(value: SceneSnapshot | Mapping[str, Any] | None) -> str | None:
    if value is None:
        return None
    snapshot = value if isinstance(value, SceneSnapshot) else SceneSnapshot.from_dict(dict(value))
    return snapshot.to_json()


def _snapshot_value(value: str | None) -> SceneSnapshot | None:
    return SceneSnapshot.from_json(value) if value else None


@dataclass(frozen=True)
class SessionRecord:
    id: str
    title: str
    created_at: str
    updated_at: str
    active_mode: str = "Agent"
    execution_mode: str = "confirm"
    model: str = ""
    current_turn_id: str | None = None
    last_opened_at: str | None = None
    closed_at: str | None = None
    parent_session_id: str | None = None


@dataclass(frozen=True)
class TurnRecord:
    id: str
    session_id: str
    turn_index: int
    parent_turn_id: str | None
    branch_id: str | None
    user_message: str
    assistant_message: str
    agent_mode: str
    execution_mode: str
    command_plan: dict[str, Any] | None
    validation: dict[str, Any] | None
    execution_status: str
    scene_before: SceneSnapshot | None
    scene_after: SceneSnapshot | None
    preview_path: str | None
    created_at: str


@dataclass(frozen=True)
class EventRecord:
    id: int
    session_id: str
    turn_id: str | None
    type: str
    payload: dict[str, Any]
    created_at: str


@dataclass(frozen=True)
class AttachmentRecord:
    id: str
    session_id: str
    turn_id: str | None
    path: str
    mime_type: str
    byte_size: int
    sha256: str
    created_at: str


class SessionStore:
    """Short-transaction repository for the application-managed `.math` store."""

    def __init__(self, app_root: str | Path | None = None) -> None:
        self.app_root = Path(app_root) if app_root is not None else self.default_app_root()
        self.math_root = self.app_root / ".math"
        self.db_path = self.math_root / "mathagent.db"
        self.attachments_root = self.math_root / "attachments"
        self.previews_root = self.math_root / "previews"
        self.exports_root = self.math_root / "exports"
        for path in (self.math_root, self.attachments_root, self.previews_root, self.exports_root):
            path.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            self._initialize(connection)

    @staticmethod
    def default_app_root() -> Path:
        system = platform.system()
        if system == "Windows":
            return Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "Math3DTeaching"
        if system == "Darwin":
            return Path.home() / "Library" / "Application Support" / "Math3DTeaching"
        return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "Math3DTeaching"

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _initialize(connection: sqlite3.Connection) -> None:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
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
            );
            CREATE TABLE IF NOT EXISTS turns (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL REFERENCES sessions(id),
                turn_index INTEGER NOT NULL,
                parent_turn_id TEXT,
                branch_id TEXT,
                user_message TEXT NOT NULL,
                assistant_message TEXT NOT NULL,
                agent_mode TEXT NOT NULL,
                execution_mode TEXT NOT NULL,
                command_plan_json TEXT,
                validation_json TEXT,
                execution_status TEXT NOT NULL,
                scene_before_json TEXT,
                scene_after_json TEXT,
                preview_path TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS turns_session_index ON turns(session_id, turn_index);
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(id),
                turn_id TEXT,
                type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS attachments (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL REFERENCES sessions(id),
                turn_id TEXT,
                path TEXT NOT NULL,
                mime_type TEXT NOT NULL,
                byte_size INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS app_state (
                key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )

    @staticmethod
    def _session(row: sqlite3.Row) -> SessionRecord:
        return SessionRecord(**dict(row))

    def create_session(
        self,
        title: str = "New Chat",
        *,
        session_id: str | None = None,
        model: str = "",
        active_mode: str = "Agent",
        execution_mode: str = "confirm",
        parent_session_id: str | None = None,
    ) -> SessionRecord:
        session_id = session_id or _new_id()
        timestamp = _now()
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO sessions
                (id, title, created_at, updated_at, active_mode, execution_mode, model,
                 last_opened_at, parent_session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (session_id, title or "New Chat", timestamp, timestamp, active_mode, execution_mode, model, timestamp, parent_session_id),
            )
        return self.get_session(session_id)

    def get_session(self, session_id: str) -> SessionRecord:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            raise KeyError(f"unknown session: {session_id}")
        return self._session(row)

    def list_sessions(self, *, include_closed: bool = False) -> list[SessionRecord]:
        query = "SELECT * FROM sessions"
        if not include_closed:
            query += " WHERE closed_at IS NULL"
        query += " ORDER BY updated_at DESC"
        with self._connect() as connection:
            rows = connection.execute(query).fetchall()
        return [self._session(row) for row in rows]

    def rename_session(self, session_id: str, title: str) -> SessionRecord:
        with self._connect() as connection:
            connection.execute("UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?", (title.strip() or "New Chat", _now(), session_id))
        return self.get_session(session_id)

    def close_session(self, session_id: str) -> SessionRecord:
        timestamp = _now()
        with self._connect() as connection:
            connection.execute("UPDATE sessions SET closed_at = ?, updated_at = ? WHERE id = ?", (timestamp, timestamp, session_id))
        return self.get_session(session_id)

    def reopen_session(self, session_id: str) -> SessionRecord:
        timestamp = _now()
        with self._connect() as connection:
            connection.execute("UPDATE sessions SET closed_at = NULL, last_opened_at = ?, updated_at = ? WHERE id = ?", (timestamp, timestamp, session_id))
        return self.get_session(session_id)

    def set_session_preferences(self, session_id: str, *, active_mode: str | None = None, execution_mode: str | None = None, model: str | None = None) -> SessionRecord:
        current = self.get_session(session_id)
        values = (
            active_mode if active_mode is not None else current.active_mode,
            execution_mode if execution_mode is not None else current.execution_mode,
            model if model is not None else current.model,
            _now(),
            session_id,
        )
        with self._connect() as connection:
            connection.execute("UPDATE sessions SET active_mode = ?, execution_mode = ?, model = ?, updated_at = ? WHERE id = ?", values)
        return self.get_session(session_id)

    def append_turn(
        self,
        session_id: str,
        *,
        user_message: str,
        assistant_message: str,
        scene_before: SceneSnapshot | Mapping[str, Any] | None,
        scene_after: SceneSnapshot | Mapping[str, Any] | None,
        command_plan: Mapping[str, Any] | None,
        status: str,
        validation: Mapping[str, Any] | None = None,
        agent_mode: str | None = None,
        execution_mode: str | None = None,
        parent_turn_id: str | None = None,
        branch_id: str | None = None,
        preview_path: str | None = None,
    ) -> str:
        session = self.get_session(session_id)
        with self._connect() as connection:
            index = int(connection.execute("SELECT COALESCE(MAX(turn_index), 0) + 1 FROM turns WHERE session_id = ?", (session_id,)).fetchone()[0])
            turn_id = _new_id()
            timestamp = _now()
            connection.execute(
                """INSERT INTO turns
                (id, session_id, turn_index, parent_turn_id, branch_id, user_message,
                 assistant_message, agent_mode, execution_mode, command_plan_json,
                 validation_json, execution_status, scene_before_json, scene_after_json,
                 preview_path, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    turn_id,
                    session_id,
                    index,
                    parent_turn_id,
                    branch_id,
                    user_message,
                    assistant_message,
                    agent_mode or session.active_mode,
                    execution_mode or session.execution_mode,
                    json.dumps(dict(command_plan), ensure_ascii=False) if command_plan is not None else None,
                    json.dumps(dict(validation), ensure_ascii=False) if validation is not None else None,
                    status,
                    _snapshot_json(scene_before),
                    _snapshot_json(scene_after),
                    preview_path,
                    timestamp,
                ),
            )
            connection.execute("UPDATE sessions SET current_turn_id = ?, updated_at = ? WHERE id = ?", (turn_id, timestamp, session_id))
        return turn_id

    @staticmethod
    def _turn(row: sqlite3.Row) -> TurnRecord:
        values = dict(row)
        command_plan_json = values.pop("command_plan_json")
        validation_json = values.pop("validation_json")
        values["command_plan"] = json.loads(command_plan_json) if command_plan_json else None
        values["validation"] = json.loads(validation_json) if validation_json else None
        values["scene_before"] = _snapshot_value(values.pop("scene_before_json"))
        values["scene_after"] = _snapshot_value(values.pop("scene_after_json"))
        return TurnRecord(**values)

    def get_turn(self, turn_id: str) -> TurnRecord:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM turns WHERE id = ?", (turn_id,)).fetchone()
        if row is None:
            raise KeyError(f"unknown turn: {turn_id}")
        return self._turn(row)

    def list_turns(self, session_id: str) -> list[TurnRecord]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM turns WHERE session_id = ? ORDER BY turn_index", (session_id,)).fetchall()
        return [self._turn(row) for row in rows]

    def set_current_turn(self, session_id: str, turn_id: str | None) -> SessionRecord:
        with self._connect() as connection:
            connection.execute("UPDATE sessions SET current_turn_id = ?, updated_at = ? WHERE id = ?", (turn_id, _now(), session_id))
        return self.get_session(session_id)

    def update_turn_scene_snapshots(
        self,
        turn_id: str,
        *,
        scene_before: SceneSnapshot | Mapping[str, Any] | None = None,
        scene_after: SceneSnapshot | Mapping[str, Any] | None = None,
        status: str | None = None,
    ) -> TurnRecord:
        """Fill snapshots after a host-side execution or confirmation."""
        turn = self.get_turn(turn_id)
        before = turn.scene_before if scene_before is None else scene_before
        after = turn.scene_after if scene_after is None else scene_after
        next_status = status if status is not None else turn.execution_status
        with self._connect() as connection:
            connection.execute(
                "UPDATE turns SET scene_before_json = ?, scene_after_json = ?, execution_status = ? WHERE id = ?",
                (_snapshot_json(before), _snapshot_json(after), next_status, turn_id),
            )
        return self.get_turn(turn_id)

    def append_event(self, session_id: str, event_type: str, payload: Mapping[str, Any], *, turn_id: str | None = None) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO events (session_id, turn_id, type, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, turn_id, event_type, json.dumps(dict(payload), ensure_ascii=False), _now()),
            )
            return int(cursor.lastrowid)

    def list_events(self, session_id: str, *, turn_id: str | None = None) -> list[EventRecord]:
        query = "SELECT * FROM events WHERE session_id = ?"
        args: list[Any] = [session_id]
        if turn_id is not None:
            query += " AND turn_id = ?"
            args.append(turn_id)
        query += " ORDER BY id"
        with self._connect() as connection:
            rows = connection.execute(query, args).fetchall()
        return [EventRecord(id=row["id"], session_id=row["session_id"], turn_id=row["turn_id"], type=row["type"], payload=json.loads(row["payload_json"]), created_at=row["created_at"]) for row in rows]

    def add_attachment(self, session_id: str, *, turn_id: str | None, relative_path: str, mime_type: str, byte_size: int, sha256: str) -> str:
        attachment_id = _new_id()
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO attachments (id, session_id, turn_id, path, mime_type, byte_size, sha256, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (attachment_id, session_id, turn_id, relative_path, mime_type, int(byte_size), sha256, _now()),
            )
        return attachment_id

    def list_attachments(self, session_id: str, *, turn_id: str | None = None) -> list[AttachmentRecord]:
        query = "SELECT * FROM attachments WHERE session_id = ?"
        args: list[Any] = [session_id]
        if turn_id is not None:
            query += " AND turn_id = ?"
            args.append(turn_id)
        query += " ORDER BY created_at"
        with self._connect() as connection:
            rows = connection.execute(query, args).fetchall()
        return [AttachmentRecord(**dict(row)) for row in rows]

    def save_app_state(self, values: Mapping[str, Any]) -> None:
        timestamp = _now()
        with self._connect() as connection:
            for key, value in values.items():
                connection.execute(
                    "INSERT INTO app_state(key, value_json, updated_at) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at",
                    (key, json.dumps(value, ensure_ascii=False), timestamp),
                )

    def load_app_state(self) -> dict[str, Any]:
        with self._connect() as connection:
            rows = connection.execute("SELECT key, value_json FROM app_state").fetchall()
        return {row["key"]: json.loads(row["value_json"]) for row in rows}
