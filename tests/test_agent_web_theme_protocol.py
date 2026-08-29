from __future__ import annotations

import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from agent.web_protocol import ProtocolError, parse_envelope
from ui.agent_sidebar_web import AgentSidebarWeb


def test_theme_state_accepts_only_mode() -> None:
    envelope = parse_envelope({"protocol_version": 1, "type": "theme_state", "request_id": "r", "session_id": "", "payload": {"mode": "dark"}})
    assert envelope.payload == {"mode": "dark"}
    with pytest.raises(ProtocolError):
        parse_envelope({"protocol_version": 1, "type": "theme_state", "request_id": "r", "session_id": "", "payload": {"mode": "blue"}})
    with pytest.raises(ProtocolError):
        parse_envelope({"protocol_version": 1, "type": "theme_state", "request_id": "r", "session_id": "", "payload": {"mode": "dark", "tokens": {}}})


def test_web_host_queues_latest_theme_before_load_and_emits_after_load() -> None:
    app = QApplication.instance() or QApplication([])
    host = AgentSidebarWeb(lambda _message: None)
    emitted: list[dict[str, object]] = []
    host.bridge.event_json.connect(lambda raw: emitted.append(json.loads(raw)))
    host._document_loaded = False
    host.set_theme("dark", loaded=False)
    host.set_theme("light", loaded=False)
    assert not emitted
    host._request_initial_snapshot(True)
    assert [event["type"] for event in emitted] == ["theme_state"]
    assert emitted[0]["payload"] == {"mode": "light"}


def test_web_host_emits_loaded_theme_immediately() -> None:
    app = QApplication.instance() or QApplication([])
    host = AgentSidebarWeb(lambda _message: None)
    emitted: list[dict[str, object]] = []
    host.bridge.event_json.connect(lambda raw: emitted.append(json.loads(raw)))
    host._document_loaded = True
    host.set_theme("dark")
    assert emitted[-1]["type"] == "theme_state"
    assert emitted[-1]["payload"] == {"mode": "dark"}
