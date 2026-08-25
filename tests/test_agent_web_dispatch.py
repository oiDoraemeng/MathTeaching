from __future__ import annotations

from agent.session_store import SessionStore
from agent.web_protocol import parse_envelope
from ui.agent_bridge import AgentBridge
from services.agent_worker import RuntimeTurnWorker


def test_dispatcher_receives_send_message_without_renderer_handle() -> None:
    received = []
    bridge = AgentBridge(received.append)
    bridge.send_json(
        '{"protocol_version":1,"type":"send_message","request_id":"r1","session_id":"s1","payload":{"text":"画曲线","mode":"Agent"}}'
    )

    assert received[0].type == "send_message"
    assert received[0].payload["text"] == "画曲线"


def test_snapshot_intent_can_be_handled_with_session_store(tmp_path) -> None:
    store = SessionStore(app_root=tmp_path)
    session = store.create_session("Chat")
    received = []
    bridge = AgentBridge(received.append)
    message = parse_envelope(
        {
            "protocol_version": 1,
            "type": "request_snapshot",
            "request_id": "r2",
            "session_id": session.id,
            "payload": {},
        }
    )

    received.append(message)
    assert received[0].type == "request_snapshot"
    assert store.get_session(session.id).id == session.id


def test_runtime_turn_worker_forwards_runtime_events() -> None:
    class FakeRuntime:
        def run_turn(self, session_id, prompt, **kwargs):
            class Result:
                turn_id = "turn-1"
                events = ()
            return Result()

        def stop(self, session_id):
            self.stopped = session_id

    from agent.events import AgentEvent

    class FakeRuntimeWithEvent(FakeRuntime):
        def run_turn(self, session_id, prompt, **kwargs):
            class Result:
                turn_id = "turn-1"
                events = (AgentEvent("message_delta", {"text": "ok"}, session_id=session_id),)
            return Result()

    worker = RuntimeTurnWorker(FakeRuntimeWithEvent(), "s1", "画图", mode="Agent", execution_mode="confirm")
    events: list[object] = []
    results: list[object] = []
    worker.event_ready.connect(events.append)
    worker.turn_finished.connect(results.append)
    worker.run()

    assert len(events) == 1
    assert events[0].turn_id == "turn-1"
    assert len(results) == 1
