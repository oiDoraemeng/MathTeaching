from __future__ import annotations

from agent.events import AgentEvent
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


def test_runtime_turn_worker_forwards_stream_events_once_before_completion() -> None:
    from agent.events import AgentEvent

    streamed = AgentEvent("message_delta", {"text": "实时"}, session_id="s1", turn_id="turn-1")

    class StreamingRuntime:
        def run_turn(self, session_id, prompt, **kwargs):
            kwargs["on_event"](streamed)

            class Result:
                turn_id = "turn-1"
                events = (streamed, AgentEvent("turn_finished", {"status": "completed"}, session_id=session_id, turn_id="turn-1"))

            return Result()

        def stop(self, session_id):
            pass

    worker = RuntimeTurnWorker(StreamingRuntime(), "s1", "画图", mode="Agent", execution_mode="continuous")
    events: list[object] = []
    worker.event_ready.connect(events.append)
    worker.run()

    assert [event.type for event in events] == ["message_delta", "turn_finished"]


def test_runtime_turn_worker_coalesces_tiny_stream_deltas() -> None:
    from agent.events import AgentEvent

    deltas = [
        AgentEvent("message_delta", {"text": "a"}, session_id="s1", turn_id="turn-1"),
        AgentEvent("message_delta", {"text": "b"}, session_id="s1", turn_id="turn-1"),
        AgentEvent("message_delta", {"text": "c"}, session_id="s1", turn_id="turn-1"),
    ]

    class StreamingRuntime:
        def run_turn(self, session_id, prompt, **kwargs):
            for event in deltas:
                kwargs["on_event"](event)

            class Result:
                turn_id = "turn-1"
                events = tuple(deltas) + (AgentEvent("turn_finished", {"status": "completed"}, session_id=session_id, turn_id="turn-1"),)

            return Result()

        def stop(self, session_id):
            pass

    worker = RuntimeTurnWorker(StreamingRuntime(), "s1", "画图", mode="Agent", execution_mode="continuous")
    events: list[object] = []
    worker.event_ready.connect(events.append)
    worker.run()

    assert [event.type for event in events] == ["message_delta", "turn_finished"]
    assert events[0].payload["text"] == "abc"


def test_agent_event_relay_delivers_worker_events_on_gui_thread() -> None:
    from PySide6.QtCore import QEventLoop, QObject, QThread, QTimer, Signal
    from PySide6.QtWidgets import QApplication
    from ui.designer_window import _AgentEventRelay

    qapp = QApplication.instance() or QApplication([])
    received = []
    relay = _AgentEventRelay(received.append, qapp)
    class Emitter(QObject):
        emitted = Signal(object)

    worker_thread = QThread()
    emitter = Emitter()
    emitter.moveToThread(worker_thread)
    event = AgentEvent("message_delta", {"text": "live"}, session_id="s1", turn_id="t1")
    emitter.emitted.connect(relay.deliver)
    worker_thread.started.connect(lambda: emitter.emitted.emit(event))
    worker_thread.start()
    worker_thread.finished.connect(worker_thread.deleteLater)

    loop = QEventLoop()
    deadline = QTimer()
    deadline.setSingleShot(True)
    deadline.timeout.connect(loop.quit)
    deadline.start(1000)
    while not received and deadline.isActive():
        QTimer.singleShot(10, loop.quit)
        loop.exec()

    assert received == [event]
    assert relay.thread() == qapp.thread()
    worker_thread.quit()
    worker_thread.wait()
