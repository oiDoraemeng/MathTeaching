from __future__ import annotations

from agent.events import AgentEvent
from agent.runtime import AgentRuntime
from agent.scene_snapshot import SceneSnapshot
from agent.session_store import SessionStore
from services.scene_commands import SceneCommandService


class _Host:
    def __init__(self) -> None:
        self.operations = []
        self.events = []

    def begin_scene_command_transaction(self) -> None:
        self.events.append("begin")

    def apply_scene_command(self, operation) -> None:
        self.operations.append(operation)

    def commit_scene_command_transaction(self) -> None:
        self.events.append("commit")

    def rollback_scene_command_transaction(self) -> None:
        self.events.append("rollback")


def _runtime(tmp_path):
    host = _Host()
    store = SessionStore(app_root=tmp_path)
    runtime = AgentRuntime(command_service=SceneCommandService(host), session_store=store)
    session = store.create_session("Chat")
    return runtime, store, session, host


def test_confirmation_mode_waits_for_approval(tmp_path) -> None:
    runtime, _, session, host = _runtime(tmp_path)

    result = runtime.run_turn(session.id, "创建点 P(1,2)", mode="Agent", execution_mode="confirm")

    assert result.status == "approval_required"
    assert host.operations == []
    assert any(event.type == "approval_required" for event in result.events)


def test_continuous_mode_executes_after_validation(tmp_path) -> None:
    runtime, _, session, host = _runtime(tmp_path)

    result = runtime.run_turn(session.id, "创建点 P(1,2)", mode="Agent", execution_mode="continuous")

    assert result.status == "completed"
    assert host.events == ["begin", "commit"]
    assert any(event.type == "execution_finished" for event in result.events)


def test_ask_and_plan_modes_never_mutate_scene(tmp_path) -> None:
    runtime, _, session, host = _runtime(tmp_path)

    ask = runtime.run_turn(session.id, "创建点 P(1,2)", mode="Ask", execution_mode="continuous")
    plan = runtime.run_turn(session.id, "创建点 Q(2,3)", mode="Plan", execution_mode="continuous")

    assert ask.status == "approval_required"
    assert plan.status == "planned"
    assert host.operations == []


def test_completed_turn_persists_before_and_after_snapshots(tmp_path) -> None:
    runtime, store, session, _ = _runtime(tmp_path)
    before = SceneSnapshot()
    after = SceneSnapshot(geometry=({"alias": "P"},))

    result = runtime.run_turn(session.id, "创建点 P(1,2)", mode="Agent", execution_mode="continuous", scene_before=before, scene_after=after)
    turns = store.list_turns(session.id)

    assert result.status == "completed"
    assert turns[-1].scene_before == before
    assert turns[-1].scene_after == after
