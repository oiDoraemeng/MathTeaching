"""Serializable runtime-to-UI event protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, ClassVar

from .capabilities.contracts import MAX_EVENT_STRING_LENGTH, json_safe


EVENT_TYPES = frozenset(
    {
        "session_started",
        "message_delta",
        "tool_started",
        "tool_finished",
        "capability_fallback",
        "plan_composed",
        "scene_conflict",
        "calculation_result",
        "plan_ready",
        "validation_result",
        "approval_required",
        "preview_ready",
        "execution_started",
        "execution_finished",
        "undo_available",
        "branch_created",
        "stopped",
        "error",
        "context_usage",
        "turn_finished",
    }
)

_SENSITIVE_KEYS = frozenset({"api_key", "authorization", "password", "secret", "token", "headers"})


def sanitize_event_payload(value: dict[str, Any]) -> dict[str, Any]:
    """Detach bounded JSON-safe event data before it reaches storage or the UI."""
    def sanitize(item: Any, *, key: str = "") -> Any:
        if key.lower() in _SENSITIVE_KEYS:
            return "***"
        if isinstance(item, str):
            return item[:MAX_EVENT_STRING_LENGTH]
        if isinstance(item, dict):
            return {str(child_key)[:MAX_EVENT_STRING_LENGTH]: sanitize(child, key=str(child_key)) for child_key, child in item.items()}
        if isinstance(item, (list, tuple)):
            return [sanitize(child) for child in item[:64]]
        return item

    payload = sanitize(value)
    return json_safe(payload)


@dataclass(frozen=True)
class AgentEvent:
    type: str
    payload: dict[str, Any] = field(default_factory=dict)
    session_id: str | None = None
    turn_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    EVENT_TYPES: ClassVar[frozenset[str]] = EVENT_TYPES

    def __post_init__(self) -> None:
        if self.type not in EVENT_TYPES:
            raise ValueError(f"unknown event type: {self.type}")
        if not isinstance(self.payload, dict):
            raise ValueError("event payload must be an object")
        object.__setattr__(self, "payload", sanitize_event_payload(self.payload))

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "payload": dict(self.payload),
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AgentEvent":
        if not isinstance(value, dict):
            raise ValueError("event must be an object")
        return cls(
            type=str(value.get("type", "")),
            payload=dict(value.get("payload", {})),
            session_id=value.get("session_id"),
            turn_id=value.get("turn_id"),
            created_at=str(value.get("created_at") or datetime.now(timezone.utc).isoformat()),
        )
