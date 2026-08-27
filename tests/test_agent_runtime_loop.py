from __future__ import annotations

from agent.events import AgentEvent
from agent.runtime import AgentRuntime
from agent.scene_snapshot import SceneSnapshot
from agent.session_store import SessionStore
from services.agent_provider import AgentResponse
from services.agent_provider import ProviderEvent
from services.agent_provider import NativeToolResponse, ProviderToolCall
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


class _UnavailableProvider:
    def create_plan(self, messages, scene_context):
        raise RuntimeError("provider_unconfigured")


class _ExplanationOnlyProvider:
    def create_plan(self, messages, scene_context):
        return AgentResponse("DeepSeek explanation", None, "DeepSeek explanation")


class _StreamingExplanationProvider:
    def create_plan(self, messages, scene_context):
        raise AssertionError("streaming provider should not fall back to create_plan")

    def stream(self, messages, *, tools=()):
        yield ProviderEvent("message_delta", {"text": "正在解释", "kind": "reasoning"})
        yield ProviderEvent("message_delta", {"text": "并准备绘图。"})
        yield ProviderEvent("completed", {"text": "正在解释并准备绘图。", "tool_calls": []})


class _NativeToolProvider:
    supports_native_tools = True

    def __init__(self) -> None:
        self.requests = []

    def request_tools(self, messages, catalog):
        self.requests.append((messages, tuple(catalog)))
        if len(self.requests) == 1:
            return NativeToolResponse("", (ProviderToolCall("call-1", "scene.edit", {"action": "upsert", "object_type": "point", "alias": "P", "coordinates": [1, 2]}),))
        return NativeToolResponse("已创建点 P。")

    def create_plan(self, messages, scene_context):
        raise AssertionError("native tool path should not use one-shot plan")


class _NativeFallbackProvider(_NativeToolProvider):
    def request_tools(self, messages, catalog):
        raise RuntimeError("native_transport_unsupported")

    def create_plan(self, messages, scene_context):
        from services.scene_commands import CommandPlan

        return AgentResponse("fallback", CommandPlan(summary="fallback", operations=({"op": "point.upsert", "alias": "P", "coordinates": [1, 2]},)), "")


def _runtime(tmp_path):
    host = _Host()
    store = SessionStore(app_root=tmp_path)
    runtime = AgentRuntime(command_service=SceneCommandService(host), session_store=store)
    session = store.create_session("Chat")
    return runtime, store, session, host


def test_agent_mode_executes_without_confirmation_selector(tmp_path) -> None:
    runtime, _, session, host = _runtime(tmp_path)

    result = runtime.run_turn(session.id, "创建点 P(1,2)", mode="Agent", execution_mode="confirm")

    assert result.status == "completed"
    assert host.operations
    assert not any(event.type == "approval_required" for event in result.events)


def test_continuous_mode_executes_after_validation(tmp_path) -> None:
    runtime, _, session, host = _runtime(tmp_path)

    result = runtime.run_turn(session.id, "创建点 P(1,2)", mode="Agent", execution_mode="continuous")

    assert result.status == "completed"
    assert host.events == ["begin", "commit"]
    assert any(event.type == "execution_finished" for event in result.events)


def test_native_tool_loop_injects_canonical_catalog_and_composes_once(tmp_path) -> None:
    provider = _NativeToolProvider()
    host = _Host()
    store = SessionStore(app_root=tmp_path)
    runtime = AgentRuntime(provider=provider, command_service=SceneCommandService(host), session_store=store)
    session = store.create_session("Chat")

    result = runtime.run_turn(session.id, "创建点 P(1,2)", mode="Agent", scene_before=SceneSnapshot())

    assert result.status == "completed"
    assert len(provider.requests) == 2
    assert {item["name"] for item in provider.requests[0][1]} == {
        "scene.inspect", "scene.find", "scene.edit", "scene.clear", "math.calculate", "math.derive", "view.control", "result.export", "teaching.explain",
    }
    assert provider.requests[1][0][-1].tool_result.tool_call_id == "call-1"
    assert [operation["op"] for operation in host.operations] == ["scene.set_mode", "point.upsert"]
    assert any(event.type == "tool_started" for event in result.events)
    assert any(event.type == "plan_composed" for event in result.events)


def test_native_tool_transport_failure_uses_same_provider_json_fallback(tmp_path) -> None:
    host = _Host()
    store = SessionStore(app_root=tmp_path)
    runtime = AgentRuntime(provider=_NativeFallbackProvider(), command_service=SceneCommandService(host), session_store=store)
    session = store.create_session("Chat")

    result = runtime.run_turn(session.id, "创建点 P(1,2)", mode="Agent")

    assert result.status == "completed"
    assert result.response.text == "fallback"
    assert any(event.type == "capability_fallback" for event in result.events)


def test_unconfigured_remote_provider_reports_error_for_vector_request(tmp_path) -> None:
    host = _Host()
    store = SessionStore(app_root=tmp_path)
    runtime = AgentRuntime(
        provider=_UnavailableProvider(),
        command_service=SceneCommandService(host),
        session_store=store,
    )
    session = store.create_session("Chat")

    result = runtime.run_turn(
        session.id,
        "画向量 a=(2,1) 和 b=(1,3)，从原点出发，用平行四边形法表示 a+b，并显示三角形法",
        mode="Agent",
    )

    assert result.status == "failed"
    assert host.operations == []
    error = next(event for event in result.events if event.type == "error")
    assert error.payload["message"] == "provider_unconfigured"


def test_remote_explanation_is_combined_with_deterministic_vector_plan(tmp_path) -> None:
    host = _Host()
    store = SessionStore(app_root=tmp_path)
    runtime = AgentRuntime(
        provider=_ExplanationOnlyProvider(),
        command_service=SceneCommandService(host),
        session_store=store,
    )
    session = store.create_session("Chat")

    result = runtime.run_turn(
        session.id,
        "画向量 a=(2,1) 和 b=(1,3)，从原点出发，用平行四边形法表示 a+b，并显示三角形法",
        mode="Agent",
    )

    assert result.status == "completed"
    assert result.response.text == "DeepSeek explanation"
    assert any(operation.get("op") == "linear.upsert" for operation in host.operations)


def test_streaming_remote_explanation_keeps_deltas_and_vector_plan(tmp_path) -> None:
    host = _Host()
    store = SessionStore(app_root=tmp_path)
    runtime = AgentRuntime(
        provider=_StreamingExplanationProvider(),
        command_service=SceneCommandService(host),
        session_store=store,
    )
    session = store.create_session("Chat")
    streamed = []
    result = runtime.run_turn(
        session.id,
        "\u753b\u5411\u91cf a=(2,1) \u548c b=(1,3)\uff0c\u4ece\u539f\u70b9\u51fa\u53d1\uff0c\u7528\u5e73\u884c\u56db\u8fb9\u5f62\u6cd5\u8868\u793a a+b\uff0c\u5e76\u663e\u793a\u4e09\u89d2\u5f62\u6cd5",
        mode="Agent",
        on_event=streamed.append,
    )

    assert result.status == "completed"
    assert [event.payload.get("kind") for event in streamed if event.type == "message_delta"] == ["reasoning", "reasoning", None]
    assert streamed[0].payload["text"] == "正在分析数学问题…"
    assert result.response.text == "正在解释并准备绘图。"
    assert result.response.plan is not None
    assert any(operation.get("op") == "linear.upsert" for operation in host.operations)


def test_runtime_keeps_caller_turn_id_for_stream_events(tmp_path) -> None:
    host = _Host()
    store = SessionStore(app_root=tmp_path)
    runtime = AgentRuntime(
        provider=_StreamingExplanationProvider(),
        command_service=SceneCommandService(host),
        session_store=store,
    )
    session = store.create_session("Chat")
    streamed = []

    result = runtime.run_turn(
        session.id,
        "画点 P(1,2)",
        mode="Agent",
        turn_id="stable-turn",
        on_event=streamed.append,
    )

    assert result.turn_id == "stable-turn"
    assert streamed
    assert all(event.turn_id == "stable-turn" for event in streamed)


def test_ask_and_plan_modes_never_mutate_scene(tmp_path) -> None:
    runtime, _, session, host = _runtime(tmp_path)

    ask = runtime.run_turn(session.id, "创建点 P(1,2)", mode="Ask", execution_mode="continuous")
    plan = runtime.run_turn(session.id, "创建点 Q(2,3)", mode="Plan", execution_mode="continuous")

    assert ask.status == "approval_required"
    assert plan.status == "plan_pending"
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


def test_approval_ticket_is_single_use_and_stop_invalidates_it(tmp_path) -> None:
    runtime, store, session, _ = _runtime(tmp_path)
    turn_id = store.append_turn(
        session.id,
        user_message="draw",
        assistant_message="plan",
        scene_before=None,
        scene_after=None,
        command_plan={"scene": "2d", "operations": []},
        status="approval_required",
        agent_mode="Ask",
        execution_mode="confirm",
    )

    runtime.register_approval(session.id, turn_id)
    assert runtime.consume_approval(session.id, turn_id) is True
    assert runtime.consume_approval(session.id, turn_id) is False

    runtime.register_approval(session.id, turn_id)
    runtime.stop(session.id)
    assert runtime.consume_approval(session.id, turn_id) is False
