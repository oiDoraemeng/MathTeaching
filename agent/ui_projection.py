"""JSON projections for the MathAgent Web UI.

The projection deliberately contains no sqlite rows, Qt objects, renderer handles,
credentials, or provider response objects. Python remains the source of truth.
"""

from __future__ import annotations

from collections.abc import Mapping
import json
from typing import Any

from .events import AgentEvent
from .events import sanitize_event_payload
from .session_store import SessionStore, SessionRecord, TurnRecord
from .model_catalog import CustomModelStore, default_model_id, model_catalog
from .capabilities import build_default_registry


_HIDDEN_TIMELINE_EVENTS = frozenset({"session_started", "capability_fallback", "execution_started", "execution_finished", "turn_finished", "approval_required"})
_EVENT_NAME_MAP = {
    "validation_result": "validation",
    "preview_ready": "preview",
    "execution_started": "execution",
    "execution_finished": "execution",
    "calculation_result": "calculation",
}


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


def _safe_command_plan(plan: Mapping[str, Any] | None, *, execution_status: str | None = None, validation: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    if not isinstance(plan, Mapping):
        return None
    try:
        safe_plan = sanitize_event_payload(dict(plan))
    except (TypeError, ValueError):
        return {"summary": "绘图指令", "operations": []}
    status = "已执行" if execution_status in {"completed", "success"} else "已撤销" if execution_status == "undone" else "待执行"
    validation_status = "已通过" if validation and validation.get("valid") is True else "未通过" if validation and validation.get("valid") is False else "待校验"
    operations: list[dict[str, str]] = []
    for index, operation in enumerate(safe_plan.get("operations", []) if isinstance(safe_plan.get("operations"), list) else []):
        if not isinstance(operation, Mapping):
            continue
        name = str(operation.get("op") or operation.get("name") or operation.get("type") or f"操作 {index + 1}")[:128]
        params = []
        for key, value in operation.items():
            if key in {"op", "name", "type"}:
                continue
            rendered = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            params.append(f"{key}={str(rendered)[:96]}")
        operations.append({"name": name, "summary": ", ".join(params)[:512] or name, "status": status, "validation": validation_status})
    return {"summary": str(safe_plan.get("summary") or "已生成绘图指令")[:512], "operations": operations[:128]}


def _project_event_payload(event_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    safe_payload = sanitize_event_payload(dict(payload))
    if event_type == "plan_ready":
        raw_plan = safe_payload.get("plan") if isinstance(safe_payload.get("plan"), Mapping) else safe_payload
        return {"plan": _safe_command_plan(raw_plan) or {"summary": "已生成绘图指令", "operations": []}}
    return safe_payload


def _turn_projection(store: SessionStore, turn: TurnRecord) -> dict[str, Any]:
    events = store.list_events(turn.session_id, turn_id=turn.id)
    safe_plan = _safe_command_plan(turn.command_plan, execution_status=turn.execution_status, validation=turn.validation)
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
        "command_plan": safe_plan,
        "commandPlan": safe_plan,
        "validation": _json_value(turn.validation),
        "scene_before": _json_value(turn.scene_before),
        "scene_after": _json_value(turn.scene_after),
        "created_at": turn.created_at,
        "events": [
            {
                "type": _EVENT_NAME_MAP.get(event.type, event.type),
                "session_id": event.session_id,
                "turn_id": event.turn_id,
                "payload": _json_value(_project_event_payload(event.type, event.payload)),
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
        "model": default_model_id(session.model, tuple(CustomModelStore.load().keys())),
        "thinking_enabled": session.thinking_enabled,
        "thinking_level": session.thinking_level,
        "current_turn_id": session.current_turn_id,
        "closed": session.closed_at is not None,
        "hidden": session.hidden_at is not None,
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


def _history_item(store: SessionStore, session: SessionRecord) -> dict[str, Any]:
    return {
        "id": session.id,
        "title": session.title,
        "updated_at": session.updated_at,
        "last_opened_at": session.last_opened_at,
        "turn_count": len(store.list_turns(session.id)),
        "hidden": session.hidden_at is not None,
        "closed": session.closed_at is not None,
    }


def build_session_snapshot(
    store: SessionStore,
    *,
    active_session_id: str | None,
    model_status: Mapping[str, Any] | None = None,
    settings_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    # Keep closed session metadata in the snapshot for persistence/history.
    # The Web UI filters closed records from the live tab strip.
    sessions = store.list_sessions(include_closed=True)
    history_sessions = store.list_sessions(include_closed=True)
    hidden_sessions = store.list_hidden_sessions(include_closed=True)
    visible_history = [_history_item(store, session) for session in history_sessions]
    visible_history = [item for item in visible_history if not item["hidden"]]
    hidden_history = [_history_item(store, session) for session in hidden_sessions]
    return {
        "type": "session_snapshot",
        "active_session_id": active_session_id,
        "sessions": [_session_projection(store, session) for session in sessions],
        "model_status": _json_value(dict(model_status or {})),
        "settings_state": _json_value(dict(settings_state or {})),
        "history": {"visible": visible_history, "hidden": hidden_history},
        "model_catalog": model_catalog(CustomModelStore.load()),
        "capability_catalog": build_default_registry().catalog(),
    }


def project_runtime_event(event: AgentEvent, *, sequence: int, request_id: str = "runtime") -> dict[str, Any]:
    event_name = _EVENT_NAME_MAP.get(event.type, event.type)
    return {
        "protocol_version": 1,
        "type": event_name,
        "request_id": request_id,
        "session_id": event.session_id or "",
        "turn_id": event.turn_id,
        "sequence": sequence,
        "payload": _json_value({**_project_event_payload(event.type, event.payload), **({"ui_hidden": True} if event.type in _HIDDEN_TIMELINE_EVENTS else {})}),
        "created_at": event.created_at,
    }
