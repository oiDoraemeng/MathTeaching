"""Narrow JSON bridge between the local MathAgent WebView and Python."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

from agent.web_protocol import BridgeEnvelope, parse_envelope


class AgentBridge(QObject):
    """Expose one validated JSON slot and one serializable event signal."""

    event_json = Signal(str)

    def __init__(self, dispatcher: Callable[[BridgeEnvelope], Any], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._dispatcher = dispatcher

    @Slot(str)
    def send_json(self, raw: str) -> None:
        request_id = ""
        try:
            try:
                decoded = json.loads(raw)
                request_id = str(decoded.get("request_id", "")) if isinstance(decoded, dict) else ""
            except (TypeError, json.JSONDecodeError):
                pass
            envelope = parse_envelope(raw)
            request_id = envelope.request_id
            result = self._dispatcher(envelope)
            if result is not None:
                self.emit_event(result)
        except Exception as error:
            self.emit_event(
                {
                    "protocol_version": 1,
                    "type": "error",
                    "request_id": request_id,
                    "session_id": "",
                    "payload": {"message": str(error)},
                }
            )

    def emit_event(self, event: BridgeEnvelope | dict[str, Any]) -> None:
        if isinstance(event, BridgeEnvelope):
            payload = event.to_dict()
        else:
            payload = dict(event)
        self.event_json.emit(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
