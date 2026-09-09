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
        "reopen_session",
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
        "restore_session_view",
        "rename_session",
        "hide_session",
        "restore_hidden_session",
        "save_model_provider",
        "test_model_provider",
        "save_custom_model",
        "update_custom_model",
        "delete_custom_model",
        "set_selected_model",
        "set_thinking_preferences",
        "open_skills",
        "attach_files",
        "request_snapshot",
        "select_math_stage",
        "select_math_case_pane",
        "set_math_case_pane_count",
    }
)

EVENT_MESSAGE_TYPES = frozenset(
    {
        "session_snapshot",
        "user_message",
        "session_started",
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
        "history_snapshot",
        "settings_snapshot",
        "model_catalog",
        "mutation_succeeded",
        "mutation_failed",
        "provider_test_result",
        "tool_started",
        "tool_finished",
        "capability_fallback",
        "plan_composed",
        "scene_conflict",
        "math_case",
        "math_case_focus",
        "theme_state",
    }
)

PROTOCOL_VERSION = 1
MAX_PAYLOAD_BYTES = 128 * 1024
MAX_IDENTIFIER_LENGTH = 128


class ProtocolError(ValueError):
    def __init__(self, code: str, message: str, *, field: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.field = field


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
        raise ProtocolError("unknown_message_type", f"unknown message type: {message_type}", field="type")
    request_id = str(decoded.get("request_id", "")).strip()
    if not request_id:
        raise ProtocolError("missing_request_id", "request_id is required", field="request_id")
    if len(request_id) > MAX_IDENTIFIER_LENGTH:
        raise ProtocolError("identifier_too_long", "request_id exceeds maximum length", field="request_id")
    session_id = str(decoded.get("session_id", "")).strip()
    if not session_id and message_type not in {"request_snapshot", "math_case", "math_case_focus", "theme_state"}:
        raise ProtocolError("missing_session_id", "session_id is required", field="session_id")
    if len(session_id) > MAX_IDENTIFIER_LENGTH:
        raise ProtocolError("identifier_too_long", "session_id exceeds maximum length", field="session_id")
    turn_id_value = decoded.get("turn_id")
    turn_id = str(turn_id_value).strip() if turn_id_value is not None else None
    if turn_id is not None and len(turn_id) > MAX_IDENTIFIER_LENGTH:
        raise ProtocolError("identifier_too_long", "turn_id exceeds maximum length", field="turn_id")
    if message_type in _TURN_REQUIRED_TYPES and not turn_id:
        raise ProtocolError("missing_turn_id", "turn_id is required", field="turn_id")
    sequence_value = decoded.get("sequence")
    if sequence_value is not None and (isinstance(sequence_value, bool) or not isinstance(sequence_value, int) or sequence_value < 0):
        raise ValueError("sequence must be a non-negative integer")
    payload = decoded.get("payload", {})
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    _validate_event_payload(message_type, payload)
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


def _validate_event_payload(message_type: str, payload: dict[str, Any]) -> None:
    """Reject malformed capability events before they reach the Web reducer."""
    if message_type in {"scene_context", "math_case", "math_case_focus", "select_math_case_pane"} and "pane_id" in payload:
        pane_id = payload.get("pane_id")
        if not isinstance(pane_id, str) or not pane_id.strip() or len(pane_id) > MAX_IDENTIFIER_LENGTH:
            raise ProtocolError("invalid_event_payload", "pane_id must be a non-empty identifier", field="pane_id")
    if message_type == "select_math_stage":
        if set(payload) != {"case_id", "stage_id"}:
            raise ProtocolError(
                "invalid_event_payload",
                "select_math_stage requires only case_id and stage_id",
                field="payload",
            )
        for field in ("case_id", "stage_id"):
            value = payload.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ProtocolError(
                    "invalid_event_payload",
                    f"select_math_stage requires a non-empty {field}",
                    field=field,
                )
        return
    if message_type == "select_math_case_pane":
        if set(payload) != {"case_id", "pane_id", "stage_id"}:
            raise ProtocolError(
                "invalid_event_payload",
                "select_math_case_pane requires only case_id, pane_id and stage_id",
                field="payload",
            )
        for field in ("case_id", "pane_id", "stage_id"):
            value = payload.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ProtocolError(
                    "invalid_event_payload",
                    f"select_math_case_pane requires a non-empty {field}",
                    field=field,
                )
        return
    if message_type == "set_math_case_pane_count":
        if set(payload) != {"case_id", "pane_count"}:
            raise ProtocolError(
                "invalid_event_payload",
                "set_math_case_pane_count requires only case_id and pane_count",
                field="payload",
            )
        case_id = payload.get("case_id")
        pane_count = payload.get("pane_count")
        if not isinstance(case_id, str) or not case_id.strip():
            raise ProtocolError("invalid_event_payload", "set_math_case_pane_count requires a non-empty case_id", field="case_id")
        if isinstance(pane_count, bool) or pane_count not in {1, 2, 3, 4}:
            raise ProtocolError("invalid_event_payload", "pane_count must be 1, 2, 3, or 4", field="pane_count")
        return
    if message_type == "math_case_focus":
        if set(payload) != {"case_id", "pane_id"}:
            raise ProtocolError(
                "invalid_event_payload",
                "math_case_focus requires only case_id and pane_id",
                field="payload",
            )
        for field in ("case_id", "pane_id"):
            value = payload.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ProtocolError(
                    "invalid_event_payload",
                    f"math_case_focus requires a non-empty {field}",
                    field=field,
                )
        return
    if message_type == "theme_state":
        if set(payload) != {"mode"} or payload.get("mode") not in {"light", "dark"}:
            raise ProtocolError("invalid_event_payload", "theme_state requires only mode=light|dark", field="mode")
        return
    required: dict[str, tuple[tuple[str, type | tuple[type, ...]], ...]] = {
        "tool_started": (("call_id", str), ("name", str), ("category", str), ("mutating", bool)),
        "tool_finished": (("call_id", str), ("name", str), ("status", str), ("result_kind", str)),
        "capability_fallback": (("reason", str),),
        "plan_composed": (("summary", str), ("operation_count", int)),
        "scene_conflict": (("code", str), ("message", str)),
        "math_case": (("case_id", str), ("name", str), ("formula", str), ("steps", list), ("conclusion", str)),
    }
    for field, expected_type in required.get(message_type, ()):
        value = payload.get(field)
        if isinstance(value, bool) and expected_type is int:
            raise ProtocolError("invalid_event_payload", f"{field} has an invalid type", field=field)
        if not isinstance(value, expected_type):
            raise ProtocolError("invalid_event_payload", f"{field} has an invalid type", field=field)


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
