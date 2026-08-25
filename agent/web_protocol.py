"""Strict JSON-only bridge between the local WebView and Python runtime."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, ClassVar

from .events import AgentEvent


CLIENT_MESSAGE_TYPES = frozenset(
    {
        "create_session",
        "close_session",
        "send_message",
        "approve_plan",
        "stop_turn",
        "stop_session",
        "undo_turn",
        "branch_from_turn",
        "branch_turn",
        "restore_turn",
        "set_mode",
        "change_mode",
        "set_execution_mode",
        "change_execution_mode",
        "set_model",
        "change_model",
        "open_history",
        "open_settings",
        "attach_files",
        "request_snapshot",
    }
)

EVENT_MESSAGE_TYPES = frozenset(
    {
        "session_snapshot",
        "message_delta",
        "explanation",
        "scene_context",
        "calculation",
        "plan_ready",
        "validation",
        "preview",
        "execution",
        "context_usage",
        "model_status",
        "settings_state",
        "stopped",
        "error",
        "turn_finished",
    }
)

PROTOCOL_VERSION = 1
MAX_PAYLOAD_BYTES = 128 * 1024


@dataclass(frozen=True)
class ClientMessage:
    type: str
    session_id: str
    turn_id: str | None = None
    payload: dict[str, Any] | None = None
    TYPES: ClassVar[frozenset[str]] = CLIENT_MESSAGE_TYPES


@dataclass(frozen=True)
class BridgeEnvelope:
    protocol_version: int
    type: str
    request_id: str
    session_id: str
    turn_id: str | None = None
    sequence: int | None = None
    payload: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "protocol_version": self.protocol_version,
            "type": self.type,
            "request_id": self.request_id,
            "session_id": self.session_id,
            "payload": dict(self.payload or {}),
        }
        if self.turn_id is not None:
            value["turn_id"] = self.turn_id
        if self.sequence is not None:
            value["sequence"] = self.sequence
        return value


_TURN_REQUIRED_TYPES = frozenset(
    {"approve_plan", "restore_turn", "undo_turn", "branch_from_turn", "branch_turn"}
)


def _decode_object(value: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid bridge JSON: {error.msg}") from None
    else:
        decoded = value
    if not isinstance(decoded, dict):
        raise ValueError("bridge message must be an object")
    return decoded


def parse_envelope(value: str | dict[str, Any]) -> BridgeEnvelope:
    """Parse the versioned JSON boundary used by the local WebView."""
    decoded = _decode_object(value)
    if decoded.get("protocol_version") != PROTOCOL_VERSION:
        raise ValueError(f"unsupported protocol_version: {decoded.get('protocol_version')!r}")
    message_type = str(decoded.get("type", ""))
    if message_type not in CLIENT_MESSAGE_TYPES and message_type not in EVENT_MESSAGE_TYPES:
        raise ValueError(f"unknown message type: {message_type}")
    request_id = str(decoded.get("request_id", "")).strip()
    if not request_id:
        raise ValueError("request_id is required")
    session_id = str(decoded.get("session_id", "")).strip()
    if not session_id and message_type != "request_snapshot":
        raise ValueError("session_id is required")
    turn_id_value = decoded.get("turn_id")
    turn_id = str(turn_id_value).strip() if turn_id_value is not None else None
    if message_type in _TURN_REQUIRED_TYPES and not turn_id:
        raise ValueError("turn_id is required")
    sequence_value = decoded.get("sequence")
    if sequence_value is not None and (isinstance(sequence_value, bool) or not isinstance(sequence_value, int) or sequence_value < 0):
        raise ValueError("sequence must be a non-negative integer")
    payload = decoded.get("payload", {})
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    try:
        encoded = json.dumps(decoded, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ValueError(f"bridge message is not JSON serializable: {error}") from None
    if len(encoded) > MAX_PAYLOAD_BYTES:
        raise ValueError("payload exceeds maximum size")
    return BridgeEnvelope(
        protocol_version=PROTOCOL_VERSION,
        type=message_type,
        request_id=request_id,
        session_id=session_id,
        turn_id=turn_id,
        sequence=sequence_value,
        payload=dict(payload),
    )


def parse_client_message(value: str | dict[str, Any]) -> ClientMessage:
    value = _decode_object(value)
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


_EVENT_NAME_MAP = {
    "validation_result": "validation",
    "preview_ready": "preview",
    "execution_started": "execution",
    "execution_finished": "execution",
    "calculation_result": "calculation",
}


def serialize_bridge_event(
    event: AgentEvent,
    *,
    request_id: str,
    sequence: int,
) -> BridgeEnvelope:
    """Map legacy runtime events into the versioned Web UI envelope."""
    event_type = _EVENT_NAME_MAP.get(event.type, event.type)
    return BridgeEnvelope(
        protocol_version=PROTOCOL_VERSION,
        type=event_type,
        request_id=request_id,
        session_id=str(event.session_id or ""),
        turn_id=event.turn_id,
        sequence=sequence,
        payload=dict(event.payload),
    )
