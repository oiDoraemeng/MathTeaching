from __future__ import annotations

import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineWidgets import QWebEngineView

from ui.agent_bridge import AgentBridge
from ui.agent_sidebar_web import AgentSidebarWeb


def test_bridge_forwards_valid_intent_and_emits_json_error() -> None:
    app = QApplication.instance() or QApplication([])
    received: list[object] = []
    emitted: list[dict[str, object]] = []
    bridge = AgentBridge(received.append)
    bridge.event_json.connect(lambda raw: emitted.append(json.loads(raw)))

    bridge.send_json(
        json.dumps(
            {
                "protocol_version": 1,
                "type": "send_message",
                "request_id": "req-1",
                "session_id": "s1",
                "payload": {"text": "画曲线"},
            }
        )
    )
    bridge.send_json('{"protocol_version":1,"type":"run_python","request_id":"req-2","session_id":"s1"}')

    assert received[0].type == "send_message"
    assert received[0].payload == {"text": "画曲线"}
    assert emitted[-1]["type"] == "error"
    assert emitted[-1]["request_id"] == "req-2"


def test_bridge_error_preserves_session_id_and_uses_bounded_payload() -> None:
    app = QApplication.instance() or QApplication([])
    emitted: list[dict[str, object]] = []
    bridge = AgentBridge(lambda _message: (_ for _ in ()).throw(ValueError("bad request")))
    bridge.event_json.connect(lambda raw: emitted.append(json.loads(raw)))
    bridge.send_json(json.dumps({"protocol_version": 1, "type": "send_message", "request_id": "r", "session_id": "s", "payload": {}}))
    assert emitted[-1]["session_id"] == "s"
    assert set(emitted[-1]["payload"]) == {"code", "message"}


def test_bridge_exposes_only_send_json_slot() -> None:
    app = QApplication.instance() or QApplication([])
    bridge = AgentBridge(lambda _message: None)
    methods = {
        bridge.metaObject().method(index).name().data().decode()
        for index in range(bridge.metaObject().methodCount())
        if bridge.metaObject().method(index).methodType().name == "Slot"
    }

    assert "send_json" in methods
    assert not {"execute_plan", "restore_scene", "run_python"} & methods


def test_web_host_owns_one_web_view() -> None:
    app = QApplication.instance() or QApplication([])
    host = AgentSidebarWeb(lambda _message: None)

    assert len(host.findChildren(QWebEngineView)) == 1
    assert host.view.url().scheme() == "mathagent"
