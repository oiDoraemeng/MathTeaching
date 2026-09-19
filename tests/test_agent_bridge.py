from __future__ import annotations

import json
import os
from types import SimpleNamespace
from unittest.mock import MagicMock

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
            id="ch01.ops.subtraction",
            category="向量",
            name="向量减法",
            formula="a-b=(1,-1)",
            steps=("将减法改写成加上相反向量",),
            conclusion="减法等价于加上相反向量。",
            summary="用相反向量演示向量减法",
        )
    )

    assert emitted[-1]["type"] == "math_case"
    assert emitted[-1]["payload"]["case_id"] == "ch01.ops.subtraction"
    assert emitted[-1]["payload"]["scene_ready"] is True


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


def test_web_host_replays_current_case_after_render_surface_restore() -> None:
    app = QApplication.instance() or QApplication([])
    host = AgentSidebarWeb(lambda _message: None)
    emitted: list[dict[str, object]] = []
    host.bridge.event_json.connect(lambda raw: emitted.append(json.loads(raw)))
    host._document_loaded = True

    from linear_algebra.registry import catalog_registry

    registry = catalog_registry()
    topic = registry.get_topic("ch01.ops.addition")
    explanation = registry.get_explanation(topic.explanation_id)
    host.show_math_case(explanation, case_id=topic.id, category=topic.source_path[1])
    host.view.reload = MagicMock()
    emitted.clear()

    host.restore_render_surface()

    assert host._document_loaded is False
    host._request_initial_snapshot(True)
    assert emitted[-1]["type"] == "math_case"
    assert emitted[-1]["payload"]["case_id"] == topic.id


def test_web_math_case_keeps_structured_artifact_metadata_without_scene_ops() -> None:
    from linear_algebra.teaching.model import TeachingArtifact
    from linear_algebra.visualizations.common import RenderContext
    from linear_algebra.visualizations.compiler import VisualSemanticsCompiler
    from linear_algebra.visualizations.contracts import contract_for
    from tests.teaching_fixtures import projection_artifact_payload

    app = QApplication.instance() or QApplication([])
    host = AgentSidebarWeb(lambda _message: None)
    emitted: list[dict[str, object]] = []
    host.bridge.event_json.connect(lambda raw: emitted.append(json.loads(raw)))
    host._document_loaded = True
    artifact = TeachingArtifact.from_dict(projection_artifact_payload(with_residual=True))
    compiled = VisualSemanticsCompiler().compile(
        artifact,
        contract_for(artifact.topic_id),
        RenderContext.default(artifact.topic_id),
    )

    host.show_math_case(artifact, compiled=compiled)
    payload = emitted[-1]["payload"]
    assert payload["artifact_revision"] == artifact.revision
    assert payload["claims"][0]["id"] == artifact.claims[0].id
    assert payload["symbol_palette"]["u"]
    assert payload["storyboard"][0]["id"] == compiled.storyboard[0].id
    assert payload["source_excerpt"] == artifact.source.excerpt
    assert "operations" not in payload


def test_web_math_case_exposes_bounded_source_and_explanation_contract() -> None:
    from linear_algebra.teaching.model import TeachingArtifact
    from tests.teaching_fixtures import projection_artifact_payload

    app = QApplication.instance() or QApplication([])
    host = AgentSidebarWeb(lambda _message: None)
    emitted: list[dict[str, object]] = []
    host.bridge.event_json.connect(lambda raw: emitted.append(json.loads(raw)))
    host._document_loaded = True
    artifact = TeachingArtifact.from_dict(projection_artifact_payload(with_residual=True))

    host.show_math_case(
        artifact,
        case_id=artifact.topic_id,
        source_diagnostic=("stale_source", artifact.source.source_hash, "sha256:current"),
    )
    payload = emitted[-1]["payload"]
    assert payload["topic_id"] == artifact.topic_id
    assert payload["revision"] == artifact.revision
    assert payload["source"]["heading_path"] == list(artifact.source.heading_path)
    assert payload["source_diagnostic"]["code"] == "stale_source"
    assert payload["explanation"]["formula"] == artifact.explanation.formula
    assert payload["explanation"]["symbol_roles"] == dict(artifact.explanation.symbol_roles)
    encoded = json.dumps(payload, ensure_ascii=False)
    assert "operations" not in encoded
    assert "geometry." not in encoded
    assert "renderer" not in encoded
