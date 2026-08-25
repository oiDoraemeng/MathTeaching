"""Strict JSON-only bridge between the local WebView and Python runtime."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, ClassVar

from .events import AgentEvent


CLIENT_MESSAGE_TYPES = frozenset(
    {
        "send_message",
        "approve_plan",
        "stop_session",
        "undo_turn",
        "branch_from_turn",
        "set_mode",
        "set_execution_mode",
        "set_model",
    }
)


@dataclass(frozen=True)
class ClientMessage:
    type: str
    session_id: str
    turn_id: str | None = None
    payload: dict[str, Any] | None = None
    TYPES: ClassVar[frozenset[str]] = CLIENT_MESSAGE_TYPES


def parse_client_message(value: str | dict[str, Any]) -> ClientMessage:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid bridge JSON: {error.msg}") from None
    if not isinstance(value, dict):
        raise ValueError("bridge message must be an object")
    message_type = str(value.get("type", ""))
    if message_type not in CLIENT_MESSAGE_TYPES:
        raise ValueError(f"unknown message type: {message_type}")
    session_id = str(value.get("session_id", "")).strip()
    if not session_id:
        raise ValueError("session_id is required")
    turn_id = value.get("turn_id")
    if message_type in {"approve_plan", "undo_turn", "branch_from_turn"} and not str(turn_id or "").strip():
        raise ValueError("turn_id is required")
    payload = value.get("payload", {})
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    return ClientMessage(message_type, session_id, str(turn_id) if turn_id is not None else None, dict(payload))


def serialize_event(event: AgentEvent) -> dict[str, Any]:
    return event.to_dict()
