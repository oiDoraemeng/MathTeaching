"""JSON projections for the MathAgent Web UI.

The projection deliberately contains no sqlite rows, Qt objects, renderer handles,
credentials, or provider response objects. Python remains the source of truth.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .events import AgentEvent
from .session_store import SessionStore, SessionRecord, TurnRecord


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if hasattr(value, "to_dict"):
        return _json_value(value.to_dict())
    return str(value)


def _turn_projection(store: SessionStore, turn: TurnRecord) -> dict[str, Any]:
    events = store.list_events(turn.session_id, turn_id=turn.id)
    return {
        "id": turn.id,
        "user_message": turn.user_message,
        "userMessage": turn.user_message,
        "assistant_message": turn.assistant_message,
        "assistantMessage": turn.assistant_message,
        "status": turn.execution_status,
        "agent_mode": turn.agent_mode,
        "mode": turn.agent_mode,
        "execution_mode": turn.execution_mode,
        "executionMode": turn.execution_mode,
        "command_plan": _json_value(turn.command_plan),
        "validation": _json_value(turn.validation),
        "scene_before": _json_value(turn.scene_before),
        "scene_after": _json_value(turn.scene_after),
        "created_at": turn.created_at,
        "events": [
            {
                "type": event.type,
                "session_id": event.session_id,
                "turn_id": event.turn_id,
                "payload": _json_value(event.payload),
                "created_at": event.created_at,
            }
            for event in events
        ],
    }


def _session_projection(store: SessionStore, session: SessionRecord) -> dict[str, Any]:
    return {
        "id": session.id,
        "title": session.title,
        "mode": session.active_mode,
        "execution_mode": session.execution_mode,
        "executionMode": session.execution_mode,
        "model": session.model,
        "current_turn_id": session.current_turn_id,
        "closed": session.closed_at is not None,
        "parent_session_id": session.parent_session_id,
        "turns": [_turn_projection(store, turn) for turn in store.list_turns(session.id)],
        "attachments": [
            {
                "id": item.id,
                "turn_id": item.turn_id,
                "path": item.path,
                "mime_type": item.mime_type,
                "byte_size": item.byte_size,
                "sha256": item.sha256,
            }
            for item in store.list_attachments(session.id)
        ],
        "events": [
            {
                "type": event.type,
                "session_id": event.session_id,
                "turn_id": event.turn_id,
                "payload": _json_value(event.payload),
                "created_at": event.created_at,
            }
            for event in store.list_events(session.id)
            if event.turn_id is None
        ],
    }


def build_session_snapshot(
    store: SessionStore,
    *,
    active_session_id: str | None,
    model_status: Mapping[str, Any] | None = None,
    settings_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    sessions = store.list_sessions(include_closed=True)
    return {
        "type": "session_snapshot",
        "active_session_id": active_session_id,
        "sessions": [_session_projection(store, session) for session in sessions],
        "model_status": _json_value(dict(model_status or {})),
        "settings_state": _json_value(dict(settings_state or {})),
    }


def project_runtime_event(event: AgentEvent, *, sequence: int, request_id: str = "runtime") -> dict[str, Any]:
    event_name = {
        "validation_result": "validation",
        "preview_ready": "preview",
        "execution_started": "execution",
        "execution_finished": "execution",
        "calculation_result": "calculation",
    }.get(event.type, event.type)
    return {
        "protocol_version": 1,
        "type": event_name,
        "request_id": request_id,
        "session_id": event.session_id or "",
        "turn_id": event.turn_id,
        "sequence": sequence,
        "payload": _json_value(event.payload),
        "created_at": event.created_at,
    }
