"""Serializable runtime-to-UI event protocol."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, ClassVar


EVENT_TYPES = frozenset(
    {
        "session_started",
        "message_delta",
        "tool_started",
        "tool_finished",
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
