from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from agent.runtime import AgentRuntime
from agent.scene_snapshot import SceneSnapshot
from agent.session_store import SessionStore
from services.agent_provider import AgentResponse, NativeToolResponse, ProviderToolCall
from services.scene_commands import CommandError, CommandPlan, SceneCommandService


class _Host:
    def __init__(self, *, fingerprint_matches: bool = True) -> None:
        self.fingerprint_matches = fingerprint_matches
        self.events: list[str] = []
        self.operations: list[dict[str, object]] = []

    def check_scene_fingerprint(self, _expected: str) -> bool:
        return self.fingerprint_matches

    def begin_scene_command_transaction(self) -> None:
        self.events.append("begin")

    def apply_scene_command(self, operation: dict[str, object]) -> None:
        self.operations.append(operation)

    def commit_scene_command_transaction(self) -> None:
        self.events.append("commit")

    def rollback_scene_command_transaction(self) -> None:
        self.events.append("rollback")


@dataclass
class _NativeProvider:
    responses: list[NativeToolResponse]
    supports_native_tools: bool = True

    def __post_init__(self) -> None:
        self.requests: list[tuple[object, tuple[dict[str, object], ...]]] = []

    def request_tools(self, messages, catalog: Iterable[dict[str, object]]) -> NativeToolResponse:
        self.requests.append((messages, tuple(catalog)))
        return self.responses.pop(0)

    def create_plan(self, _messages, _scene_context) -> AgentResponse:
        raise AssertionError("native provider should not use the JSON fallback")


def _runtime(tmp_path, provider: _NativeProvider, host: _Host) -> tuple[AgentRuntime, str]:
    store = SessionStore(app_root=tmp_path)
    runtime = AgentRuntime(provider=provider, command_service=SceneCommandService(host), session_store=store)
    return runtime, store.create_session("E2E").id


def test_native_inspect_then_edit_stages_read_and_executes_one_transaction(tmp_path) -> None:
    provider = _NativeProvider(
        [
            NativeToolResponse("", (ProviderToolCall("inspect", "scene.inspect", {}),)),
            NativeToolResponse("", (ProviderToolCall("edit", "scene.edit", {"action": "upsert", "object_type": "point", "alias": "Q", "coordinates": [3, 4]}),)),
            NativeToolResponse("已创建 Q。"),
        ]
    )
    host = _Host()
    runtime, session_id = _runtime(tmp_path, provider, host)
    snapshot = SceneSnapshot(geometry=({"object_type": "point", "agent_alias": "P", "x": 1, "y": 2},))

    result = runtime.run_turn(session_id, "检查后创建 Q", scene_before=snapshot)

    assert result.status == "completed"
    assert host.events == ["begin", "commit"]
    assert [operation["op"] for operation in host.operations] == ["scene.set_mode", "point.upsert"]
    tool_result = provider.requests[1][0][-1].tool_result
    assert tool_result is not None and tool_result.tool_call_id == "inspect"
    assert any(event.type == "plan_composed" for event in result.events)


def test_native_derivative_and_tangent_compose_in_provider_order(tmp_path) -> None:
    provider = _NativeProvider(
        [
            NativeToolResponse("", (ProviderToolCall("derive", "math.derive", {"action": "derivative", "expression": "y=x^2", "curve_alias": "f", "presentation": "draw"}),)),
            NativeToolResponse("", (ProviderToolCall("tangent", "math.derive", {"action": "tangent", "expression": "y=x^2", "curve_alias": "f", "x": 1, "presentation": "draw"}),)),
            NativeToolResponse("已绘制导数与切线。"),
        ]
    )
    host = _Host()
    runtime, session_id = _runtime(tmp_path, provider, host)

    result = runtime.run_turn(session_id, "绘制导数和切线", scene_before=SceneSnapshot())

    assert result.status == "completed"
    assert host.events == ["begin", "commit"]
    assert [operation["op"] for operation in host.operations] == [
        "scene.set_mode", "curve.create", "curve.create", "annotation.upsert", "curve.create", "curve.create", "annotation.upsert",
    ]


def test_native_3d_create_and_scoped_clear_use_expected_target_modes(tmp_path) -> None:
    provider = _NativeProvider(
        [
            NativeToolResponse("", (ProviderToolCall("surface", "scene.edit", {"action": "upsert", "object_type": "surface", "alias": "plane", "kind": "explicit", "expression": "z=x+y"}),)),
            NativeToolResponse("已创建曲面。"),
        ]
    )
    host = _Host()
    runtime, session_id = _runtime(tmp_path, provider, host)

    result = runtime.run_turn(session_id, "创建 z=x+y 曲面", scene_before=SceneSnapshot(scene_mode="3d"))

    assert result.status == "completed"
    assert host.operations == [
        {"op": "scene.set_mode", "mode": "3d"},
        {"op": "surface.create", "alias": "plane", "kind": "explicit", "expression": "z=x+y"},
    ]

    clear_provider = _NativeProvider(
        [
            NativeToolResponse("", (ProviderToolCall("clear", "scene.clear", {"scope": "curves"}),)),
            NativeToolResponse("已清除曲线。"),
        ]
    )
    clear_host = _Host()
    clear_runtime, clear_session = _runtime(tmp_path / "clear", clear_provider, clear_host)
    cleared = clear_runtime.run_turn(
        clear_session,
        "清除曲线",
        scene_before=SceneSnapshot(curves=({"agent_alias": "f", "kind": "explicit", "expression": "y=x"},)),
    )
    assert cleared.status == "completed"
    assert clear_host.operations == [{"op": "scene.set_mode", "mode": "2d"}, {"op": "scene.clear", "scope": "curves"}]


def test_native_invalid_export_and_mixed_scene_conflict_never_begin_transaction(tmp_path) -> None:
    export_provider = _NativeProvider(
        [
            NativeToolResponse("", (ProviderToolCall("export", "result.export", {"filename": "../escape.png"}),)),
            NativeToolResponse("无法安全导出。"),
        ]
    )
    export_host = _Host()
    runtime, session_id = _runtime(tmp_path / "export", export_provider, export_host)
    export = runtime.run_turn(session_id, "导出", scene_before=SceneSnapshot())
    assert export.status == "answered"
    assert export_host.events == []
    assert any(event.type == "tool_finished" and event.payload.get("status") == "error" for event in export.events)

    conflict_provider = _NativeProvider(
        [
            NativeToolResponse("", (ProviderToolCall("mode-2d", "view.control", {"action": "set_mode", "mode": "2d"}),)),
            NativeToolResponse("", (ProviderToolCall("mode-3d", "view.control", {"action": "set_mode", "mode": "3d"}),)),
        ]
    )
    conflict_host = _Host()
    conflict_runtime, conflict_session = _runtime(tmp_path / "conflict", conflict_provider, conflict_host)
    conflict = conflict_runtime.run_turn(conflict_session, "混合场景", scene_before=SceneSnapshot())
    assert conflict.status == "rejected"
    assert conflict_host.events == []
    assert any(event.type == "scene_conflict" for event in conflict.events)


def test_stale_plan_and_cancellation_leave_host_unchanged(tmp_path) -> None:
    host = _Host(fingerprint_matches=False)
    plan = CommandPlan(operations=({"op": "point.upsert", "alias": "P", "coordinates": [1, 2]},))
    with __import__("pytest").raises(CommandError, match="scene_changed_since_plan"):
        SceneCommandService(host).execute(plan, expected_scene_fingerprint=SceneSnapshot().fingerprint())
    assert host.events == []

    provider = _NativeProvider(
        [NativeToolResponse("", (ProviderToolCall("point", "scene.edit", {"action": "upsert", "object_type": "point", "alias": "P", "coordinates": [1, 2]}),))]
    )
    cancel_host = _Host()
    runtime, session_id = _runtime(tmp_path / "cancel", provider, cancel_host)
    original_request = provider.request_tools

    def cancel_after_first(messages, catalog):
        response = original_request(messages, catalog)
        runtime.stop(session_id)
        return response

    provider.request_tools = cancel_after_first
    cancelled = runtime.run_turn(session_id, "创建后停止", scene_before=SceneSnapshot())
    assert cancelled.status == "stopped"
    assert cancel_host.events == []
