"""Agent 运行时门面，集中管理规则、Skill 和命令校验。"""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
from typing import Any, Callable
from uuid import uuid4

from services.agent_provider import AgentMessage, AgentProvider, AgentResponse, ProviderToolCall, SceneContext, ToolResultMessage
from services.scene_commands import CommandPlan, CommandValidation, SceneCommandService

from .agent import MathTeacherAgent
from .capabilities import CapabilityError, CapabilityResult, ToolCall, build_default_registry
from .capabilities.orchestrator import CapabilityOrchestrator, CapabilityTurn
from .instruction import InstructionStore
from .memory import MemoryStore
from .prompt_manager import PromptManager
from .skill_manager import SkillManager
from .events import AgentEvent
from .scene_snapshot import SceneSnapshot
from .session_store import SessionStore


@dataclass(frozen=True)
class RuntimeResponse:
    response: AgentResponse
    validation: CommandValidation | None = None


@dataclass(frozen=True)
class RuntimeTurnResult:
    status: str
    response: AgentResponse
    validation: CommandValidation | None
    events: tuple[AgentEvent, ...]
    turn_id: str | None = None


class AgentRuntime:
    """UI/worker 可调用的线程安全边界（内部对象不直接接触 Qt 控件）。"""

    def __init__(
        self,
        provider: AgentProvider | None = None,
        command_service: SceneCommandService | None = None,
        session_store: SessionStore | None = None,
    ) -> None:
        self.command_service = command_service or SceneCommandService()
        self.skill_manager = SkillManager(command_service=self.command_service)
        self.memory = MemoryStore()
        self.instructions = InstructionStore()
        self.prompts = PromptManager()
        self.capability_registry = build_default_registry()
        self.capability_orchestrator = CapabilityOrchestrator(self.capability_registry, self.command_service)
        self.session_store = session_store
        self._stopped_sessions: set[str] = set()
        self._approval_tickets: dict[str, set[str]] = {}
        self.agent = MathTeacherAgent(
            provider,
            skill_manager=self.skill_manager,
            memory=self.memory,
            instructions=self.instructions,
            prompts=self.prompts,
        )

    def respond(self, messages: tuple[AgentMessage, ...] | str, scene_context: SceneContext | None = None) -> RuntimeResponse:
        response = self.agent.respond(messages, scene_context)
        validation = self.command_service.preview(response.plan) if response.plan is not None else None
        return RuntimeResponse(response, validation)

    def validate(self, plan: CommandPlan) -> CommandValidation:
        return self.command_service.preview(plan)

    def execute(self, plan: CommandPlan, *, expected_scene_fingerprint: str | None = None) -> CommandValidation:
        """唯一的执行入口：再次校验后交给 SceneCommandService。"""
        return self.command_service.execute(plan, expected_scene_fingerprint=expected_scene_fingerprint)

    def _uses_native_tools(self) -> bool:
        provider = self.agent.provider
        return bool(getattr(provider, "supports_native_tools", False) and callable(getattr(provider, "request_tools", None)))

    def _native_turn(
        self,
        prompt: str,
        snapshot: SceneSnapshot,
        *,
        session_id: str,
        emit: Callable[[AgentEvent], None],
    ) -> tuple[AgentResponse, CapabilityTurn]:
        """Run sequential native calls while retaining one staged scene session."""
        staged = self.capability_orchestrator.start(snapshot)
        transcript = list(self.agent.native_tool_messages(prompt))
        catalog = self.capability_registry.catalog()["capabilities"]
        provider = self.agent.provider
        for _ in range(9):
            if session_id in self._stopped_sessions:
                return AgentResponse("已停止本轮请求。", None), CapabilityTurn(
                    tuple(staged.results), staged.index, error=CapabilityResult.error("cancelled", "capability.loop", CapabilityError("cancelled", "用户已停止本轮请求"))
                )
            stream_tools = getattr(provider, "stream_tools", None)

            def forward_provider_event(provider_event) -> None:
                if provider_event.type != "message_delta":
                    return
                text = provider_event.data.get("text")
                if not isinstance(text, str) or not text:
                    return
                payload: dict[str, Any] = {"text": text}
                kind = provider_event.data.get("kind")
                if isinstance(kind, str):
                    payload["kind"] = kind
                emit(AgentEvent("message_delta", payload, session_id=session_id))

            native_response = stream_tools(tuple(transcript), catalog, on_event=forward_provider_event) if callable(stream_tools) else provider.request_tools(tuple(transcript), catalog)
            calls = tuple(native_response.tool_calls)
            if not calls:
                turn = staged.finish()
                return AgentResponse(native_response.text or "已完成工具调用。", turn.plan, native_response.raw_content), turn
            for provider_call in calls:
                if session_id in self._stopped_sessions:
                    return AgentResponse("已停止本轮请求。", None), CapabilityTurn(
                        tuple(staged.results), staged.index, error=CapabilityResult.error("cancelled", "capability.loop", CapabilityError("cancelled", "用户已停止本轮请求"))
                    )
                result = self._dispatch_provider_call(staged, provider_call)
                canonical, category, mutating = self._capability_metadata(provider_call.name)
                emit(
                    AgentEvent(
                        "tool_started",
                        {"call_id": provider_call.call_id, "name": canonical, "category": category, "mutating": mutating, "arguments_summary": self._argument_summary(provider_call.arguments)},
                        session_id=session_id,
                    )
                )
                payload: dict[str, Any] = {
                    "call_id": provider_call.call_id,
                    "name": result.name,
                    "status": result.status,
                    "result_kind": "plan" if result.plan is not None else "data" if result.data is not None else "explanation",
                }
                if result.errors:
                    payload["error"] = result.errors[0].to_dict()
                emit(AgentEvent("tool_finished", payload, session_id=session_id))
                transcript.append(AgentMessage.assistant_tool_calls((provider_call,)))
                transcript.append(
                    AgentMessage.tool_result(
                        ToolResultMessage(provider_call.call_id, result.name, json.dumps(result.to_dict(), ensure_ascii=False, separators=(",", ":")))
                    )
                )
                if staged.terminal_error is not None:
                    turn = staged.finish()
                    return AgentResponse("工具调用已安全停止。", None), turn
        terminal = CapabilityResult.error("continuation", "capability.loop", CapabilityError("tool_call_limit", "工具继续请求超过限制"))
        return AgentResponse("工具调用已安全停止。", None), CapabilityTurn(tuple(staged.results), staged.index, error=terminal)

    def _dispatch_provider_call(self, staged, provider_call: ProviderToolCall) -> CapabilityResult:
        if provider_call.argument_error is not None or provider_call.arguments is None:
            return CapabilityResult.error(
                provider_call.call_id,
                provider_call.name,
                CapabilityError("invalid_tool_arguments", "工具参数不是有效 JSON"),
            )
        try:
            call = ToolCall(provider_call.call_id, provider_call.name, provider_call.arguments)
        except ValueError:
            return CapabilityResult.error(provider_call.call_id, provider_call.name, CapabilityError("invalid_tool_arguments", "工具参数必须是 JSON 对象"))
        return staged.dispatch(call)

    def _capability_metadata(self, name: str) -> tuple[str, str, bool]:
        try:
            canonical = self.capability_registry.resolve_name(name)
            spec = self.capability_registry.get(canonical)
            return canonical, spec.category, spec.mutating
        except ValueError:
            return name, "unknown", False

    @staticmethod
    def _argument_summary(arguments: dict[str, Any] | None) -> str:
        if not arguments:
            return "无参数"

        def safe_value(value: Any, key: str = "") -> Any:
            normalized_key = key.lower().replace("-", "_")
            if any(marker in normalized_key for marker in ("api_key", "authorization", "password", "secret", "token", "credential")):
                return "***"
            if isinstance(value, dict):
                return {str(child_key): safe_value(child, str(child_key)) for child_key, child in value.items()}
            if isinstance(value, (list, tuple)):
                return [safe_value(child) for child in value[:16]]
            if isinstance(value, str):
                return value[:96]
            if isinstance(value, (int, float, bool)) or value is None:
                return value
            return str(value)[:96]

        pairs: list[str] = []
        for key in sorted(arguments):
            rendered = safe_value(arguments[key], str(key))
            if not isinstance(rendered, str):
                rendered = json.dumps(rendered, ensure_ascii=False, separators=(",", ":"))
            pairs.append(f"{key}={str(rendered)[:96]}")
        return ", ".join(pairs)[:512]

    def stop(self, session_id: str) -> None:
        """Mark a session stopped; the running turn checks this before mutation."""
        session_id = str(session_id)
        self._stopped_sessions.add(session_id)
        self._approval_tickets.pop(session_id, None)

    def register_approval(self, session_id: str, turn_id: str) -> None:
        self._approval_tickets.setdefault(str(session_id), set()).add(str(turn_id))

    def consume_approval(self, session_id: str, turn_id: str) -> bool:
        tickets = self._approval_tickets.get(str(session_id))
        if not tickets or str(turn_id) not in tickets:
            return False
        tickets.remove(str(turn_id))
        if not tickets:
            self._approval_tickets.pop(str(session_id), None)
        return True

    @staticmethod
    def normalize_visible_mode(mode: str, execution_mode: str | None = None) -> tuple[str, str, bool]:
        """Map the three public modes to one stable execution contract."""
        visible = str(mode or "Agent").strip().title()
        if visible == "Ask":
            return "Ask", "confirm", True
        if visible == "Plan":
            return "Plan", "plan_pending", True
        return "Agent", "continuous", False

    def run_turn(
        self,
        session_id: str,
        prompt: str,
        *,
        mode: str = "Agent",
        execution_mode: str = "confirm",
        scene_context: SceneContext | None = None,
        scene_before: SceneSnapshot | None = None,
        scene_after: SceneSnapshot | None = None,
        turn_id: str | None = None,
        on_event: Callable[[AgentEvent], None] | None = None,
    ) -> RuntimeTurnResult:
        mode, execution_mode, approval_required = self.normalize_visible_mode(mode, execution_mode)
        base_scene_fingerprint = scene_before.fingerprint() if scene_before is not None else None
        # 预分配 turn_id，让流式事件（message_delta）在 UI 上始终归属到
        # 同一个 turn 卡片，避免实时转发时因 turn_id 缺失而拆成两个卡片。
        turn_id = str(turn_id or uuid4().hex)
        events: list[AgentEvent] = [AgentEvent("session_started", {"mode": mode, "execution_mode": execution_mode}, session_id=session_id, turn_id=turn_id)]

        def emit(event: AgentEvent) -> None:
            if getattr(event, "turn_id", None) is None:
                event = replace(event, turn_id=turn_id)
            events.append(event)
            if on_event is not None:
                on_event(event)

        def finish(status: str, response: AgentResponse, validation: CommandValidation | None, scene_after_value: SceneSnapshot | None) -> str | None:
            """Persist one complete turn and its serializable event timeline."""
            events.append(AgentEvent("turn_finished", {"status": status}, session_id=session_id, turn_id=turn_id))
            persisted_id = self._persist_turn(
                session_id,
                prompt,
                response,
                validation,
                status,
                scene_before,
                scene_after_value,
                mode,
                execution_mode,
                turn_id=turn_id,
                base_scene_fingerprint=base_scene_fingerprint,
            )
            if self.session_store is not None and persisted_id is not None:
                for event in events:
                    self.session_store.append_event(session_id, event.type, event.payload, turn_id=persisted_id)
            return persisted_id

        if session_id in self._stopped_sessions:
            self._stopped_sessions.discard(session_id)
            response = AgentResponse("已停止本轮请求。", None)
            events.append(AgentEvent("stopped", {}, session_id=session_id))
            turn_id = finish("stopped", response, None, None)
            return RuntimeTurnResult("stopped", response, None, tuple(events), turn_id)
        answer_streamed = False
        try:
            if self._uses_native_tools():
                emit(AgentEvent("message_delta", {"text": "正在分析数学问题…", "kind": "reasoning"}, session_id=session_id))
                try:
                    def emit_native(event: AgentEvent) -> None:
                        nonlocal answer_streamed
                        if event.type == "message_delta" and event.payload.get("kind") != "reasoning" and event.payload.get("text"):
                            answer_streamed = True
                        emit(event)

                    response, native_turn = self._native_turn(
                        prompt,
                        scene_before or SceneSnapshot(scene_mode=(scene_context.scene_mode if scene_context else "2d")),
                        session_id=session_id,
                        emit=emit_native,
                    )
                except Exception:
                    # Native tool calling is an optional transport feature. The
                    # same configured provider is retried once via its existing
                    # one-shot JSON plan protocol.
                    emit(AgentEvent("capability_fallback", {"reason": "native_tool_protocol_unavailable"}, session_id=session_id))
                    runtime_response = self.respond(prompt, scene_context)
                    response = runtime_response.response
                    validation = runtime_response.validation
                else:
                    if native_turn.error is not None:
                        error = native_turn.error.errors[0]
                        if error.code == "cancelled":
                            self._stopped_sessions.discard(session_id)
                            response = AgentResponse("已停止本轮请求。", None)
                            events.append(AgentEvent("stopped", {}, session_id=session_id))
                            turn_id = finish("stopped", response, None, None)
                            return RuntimeTurnResult("stopped", response, None, tuple(events), turn_id)
                        event_type = "scene_conflict" if error.code == "scene_conflict" else "error"
                        events.append(AgentEvent(event_type, {"code": error.code, "message": error.message}, session_id=session_id))
                        response = AgentResponse("本轮工具调用未完成。", None)
                        turn_id = finish("rejected", response, None, None)
                        return RuntimeTurnResult("rejected", response, None, tuple(events), turn_id)
                    if native_turn.plan is not None:
                        emit(AgentEvent("plan_composed", {"summary": native_turn.plan.summary, "operation_count": len(native_turn.plan.operations)}, session_id=session_id))
                    validation = self.command_service.preview(response.plan) if response.plan is not None else None
            elif False:
                # Kept as a branch separator for the existing streaming path.
                raise AssertionError("unreachable")
            if not self._uses_native_tools():
                def on_stream_delta(delta_text: str, kind: str | None) -> None:
                    nonlocal answer_streamed
                    payload = {"text": delta_text}
                    if kind:
                        payload["kind"] = kind
                    if kind != "reasoning" and delta_text:
                        answer_streamed = True
                    emit(AgentEvent("message_delta", payload, session_id=session_id))

                stream_response = getattr(self.agent, "respond_stream", None)
                if callable(stream_response) and getattr(self.agent.provider, "stream", None):
                    # Give the Web UI immediate feedback while the first model
                    # token is still in flight. Provider reasoning/content deltas
                    # follow this card and are merged by the frontend reducer.
                    emit(
                        AgentEvent(
                            "message_delta",
                            {"text": "正在分析数学问题…", "kind": "reasoning"},
                            session_id=session_id,
                        )
                    )
                    response = stream_response(
                        prompt,
                        scene_context,
                        on_delta=on_stream_delta,
                    )
                    validation = self.command_service.preview(response.plan) if response.plan is not None else None
                else:
                    emit(AgentEvent("message_delta", {"text": "正在分析数学问题…", "kind": "reasoning"}, session_id=session_id))
                    runtime_response = self.respond(prompt, scene_context)
                    response = runtime_response.response
                    validation = runtime_response.validation
            if response.text.strip() and not answer_streamed:
                emit(AgentEvent("message_delta", {"text": response.text}, session_id=session_id))
            if response.plan is None:
                events.append(AgentEvent("execution_finished", {"status": "answered"}, session_id=session_id))
                status = "answered"
                turn_id = finish(status, response, validation, scene_after)
                return RuntimeTurnResult(status, response, validation, tuple(events), turn_id)
            events.append(AgentEvent("plan_ready", {"plan": response.plan.to_dict()}, session_id=session_id))
            if validation is None or not validation.valid:
                events.append(AgentEvent("validation_result", {"valid": False, "messages": list(validation.messages if validation else ("缺少验证结果",))}, session_id=session_id))
                status = "rejected"
                turn_id = finish(status, response, validation, None)
                return RuntimeTurnResult(status, response, validation, tuple(events), turn_id)
            events.append(AgentEvent("validation_result", {"valid": True}, session_id=session_id))
            if mode == "Plan":
                events.append(AgentEvent("preview_ready", {"summary": response.plan.summary}, session_id=session_id))
                status = "plan_pending"
                turn_id = finish(status, response, validation, None)
                if turn_id is not None:
                    self.register_approval(session_id, turn_id)
                return RuntimeTurnResult(status, response, validation, tuple(events), turn_id)
            if approval_required:
                events.append(AgentEvent("approval_required", {"summary": response.plan.summary}, session_id=session_id))
                status = "approval_required"
                turn_id = finish(status, response, validation, None)
                if turn_id is not None:
                    self.register_approval(session_id, turn_id)
                return RuntimeTurnResult(status, response, validation, tuple(events), turn_id)
            if session_id in self._stopped_sessions:
                self._stopped_sessions.discard(session_id)
                events.append(AgentEvent("stopped", {}, session_id=session_id))
                status = "stopped"
                turn_id = finish(status, response, validation, None)
                return RuntimeTurnResult(status, response, validation, tuple(events), turn_id)
            events.append(AgentEvent("execution_started", {"summary": response.plan.summary}, session_id=session_id))
            self.command_service.execute(response.plan, expected_scene_fingerprint=base_scene_fingerprint)
            events.append(AgentEvent("execution_finished", {"status": "completed"}, session_id=session_id))
            status = "completed"
            turn_id = finish(status, response, validation, scene_after)
            return RuntimeTurnResult(status, response, validation, tuple(events), turn_id)
        except Exception as error:
            events.append(AgentEvent("error", {"message": str(error)}, session_id=session_id))
            response = AgentResponse("本轮执行失败。", None)
            turn_id = finish("failed", response, None, None)
            return RuntimeTurnResult("failed", response, None, tuple(events), turn_id)

    def _persist_turn(
        self,
        session_id: str,
        prompt: str,
        response: AgentResponse,
        validation: CommandValidation | None,
        status: str,
        scene_before: SceneSnapshot | None,
        scene_after: SceneSnapshot | None,
        mode: str,
        execution_mode: str,
        turn_id: str | None = None,
        base_scene_fingerprint: str | None = None,
    ) -> str | None:
        if self.session_store is None:
            return None
        plan = response.plan.to_dict() if response.plan is not None else None
        validation_data: dict[str, Any] | None = None
        if validation is not None:
            validation_data = {"valid": validation.valid, "messages": list(validation.messages)}
            if base_scene_fingerprint is not None:
                validation_data["base_scene_fingerprint"] = base_scene_fingerprint
        return self.session_store.append_turn(
            session_id,
            user_message=prompt,
            assistant_message=response.text,
            scene_before=scene_before,
            scene_after=scene_after,
            command_plan=plan,
            validation=validation_data,
            status=status,
            agent_mode=mode,
            execution_mode=execution_mode,
            turn_id=turn_id,
        )
