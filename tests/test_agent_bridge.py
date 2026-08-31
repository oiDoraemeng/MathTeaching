from __future__ import annotations

import json
import os
from types import SimpleNamespace

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


def test_bridge_rejects_malformed_capability_event_payload() -> None:
    app = QApplication.instance() or QApplication([])
    emitted: list[dict[str, object]] = []
    bridge = AgentBridge(lambda _message: None)
    bridge.event_json.connect(lambda raw: emitted.append(json.loads(raw)))

    bridge.emit_event({"protocol_version": 1, "type": "tool_started", "request_id": "r", "session_id": "s", "payload": {"name": "scene.inspect"}})

    assert emitted[-1]["type"] == "error"
    assert emitted[-1]["payload"]["code"] == "invalid_event"


def test_bridge_forwards_turn_lifecycle_events() -> None:
    app = QApplication.instance() or QApplication([])
    emitted: list[dict[str, object]] = []
    bridge = AgentBridge(lambda _message: None)
    bridge.event_json.connect(lambda raw: emitted.append(json.loads(raw)))

    for event_type, payload in (
        ("user_message", {"text": "生成向量加法的几何教学图"}),
        ("session_started", {"mode": "Agent", "execution_mode": "continuous"}),
    ):
        bridge.emit_event(
            {
                "protocol_version": 1,
                "type": event_type,
                "request_id": "turn-1",
                "session_id": "s1",
                "turn_id": "t1",
                "payload": payload,
            }
        )

    assert [item["type"] for item in emitted] == ["user_message", "session_started"]


def test_web_host_owns_one_web_view() -> None:
    app = QApplication.instance() or QApplication([])
    host = AgentSidebarWeb(lambda _message: None)

    assert len(host.findChildren(QWebEngineView)) == 1
    assert host.view.url().scheme() == "mathagent"


def test_web_host_emits_a_json_safe_math_case_event() -> None:
    app = QApplication.instance() or QApplication([])
    host = AgentSidebarWeb(lambda _message: None)
    emitted: list[dict[str, object]] = []
    host.bridge.event_json.connect(lambda raw: emitted.append(json.loads(raw)))
    host._document_loaded = True

    host.show_math_case(
        SimpleNamespace(
            id="vector-subtraction",
            category="向量",
            name="向量减法",
            formula="a-b=(1,-1)",
            steps=("将减法改写成加上相反向量",),
            conclusion="减法等价于加上相反向量。",
            summary="用相反向量演示向量减法",
        )
    )

    assert emitted[-1]["type"] == "math_case"
    assert emitted[-1]["payload"]["case_id"] == "vector-subtraction"


def test_web_host_replays_latest_case_after_document_load() -> None:
    app = QApplication.instance() or QApplication([])
    host = AgentSidebarWeb(lambda _message: None)
    emitted: list[dict[str, object]] = []
    host.bridge.event_json.connect(lambda raw: emitted.append(json.loads(raw)))
    host._document_loaded = False

    from linear_algebra.registry import catalog_registry

    registry = catalog_registry()
    topic = registry.get_topic("ch01.ops.addition")
    explanation = registry.get_explanation(topic.explanation_id)
    host.show_math_case(explanation, case_id=topic.id, category=topic.source_path[1])
    assert not emitted

    host._document_loaded = True
    host._replay_pending_case()

    assert emitted[-1]["type"] == "math_case"
    assert emitted[-1]["payload"]["case_id"] == "ch01.ops.addition"
