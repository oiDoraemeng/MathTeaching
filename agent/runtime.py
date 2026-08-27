"""Agent 运行时门面，集中管理规则、Skill 和命令校验。"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Callable
from uuid import uuid4

from services.agent_provider import AgentMessage, AgentProvider, AgentResponse, SceneContext
from services.scene_commands import CommandPlan, CommandValidation, SceneCommandService

from .agent import MathTeacherAgent
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

    def execute(self, plan: CommandPlan) -> CommandValidation:
        """唯一的执行入口：再次校验后交给 SceneCommandService。"""
        return self.command_service.execute(plan)

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
        try:
            def on_stream_delta(delta_text: str, kind: str | None) -> None:
                payload = {"text": delta_text}
                if kind:
                    payload["kind"] = kind
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
                emit(AgentEvent("message_delta", {"text": "正在分析数学问题…"}, session_id=session_id))
                runtime_response = self.respond(prompt, scene_context)
                response = runtime_response.response
                validation = runtime_response.validation
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
            self.command_service.execute(response.plan)
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
    ) -> str | None:
        if self.session_store is None:
            return None
        plan = response.plan.to_dict() if response.plan is not None else None
        validation_data: dict[str, Any] | None = None
        if validation is not None:
            validation_data = {"valid": validation.valid, "messages": list(validation.messages)}
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
