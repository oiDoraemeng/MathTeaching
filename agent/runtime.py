"""Agent 运行时门面，集中管理规则、Skill 和命令校验。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
        self._stopped_sessions.add(str(session_id))

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
    ) -> RuntimeTurnResult:
        events: list[AgentEvent] = [AgentEvent("session_started", {"mode": mode, "execution_mode": execution_mode}, session_id=session_id)]
        if session_id in self._stopped_sessions:
            self._stopped_sessions.discard(session_id)
            response = AgentResponse("已停止本轮请求。", None)
            events.append(AgentEvent("stopped", {}, session_id=session_id))
            return RuntimeTurnResult("stopped", response, None, tuple(events))
        try:
            events.append(AgentEvent("message_delta", {"text": "正在分析数学问题…"}, session_id=session_id))
            runtime_response = self.respond(prompt, scene_context)
            response = runtime_response.response
            validation = runtime_response.validation
            if response.plan is None:
                events.append(AgentEvent("execution_finished", {"status": "answered"}, session_id=session_id))
                status = "answered"
                turn_id = self._persist_turn(session_id, prompt, response, validation, status, scene_before, scene_after, mode, execution_mode)
                return RuntimeTurnResult(status, response, validation, tuple(events), turn_id)
            events.append(AgentEvent("plan_ready", {"plan": response.plan.to_dict()}, session_id=session_id))
            if validation is None or not validation.valid:
                events.append(AgentEvent("validation_result", {"valid": False, "messages": list(validation.messages if validation else ("缺少验证结果",))}, session_id=session_id))
                status = "rejected"
                turn_id = self._persist_turn(session_id, prompt, response, validation, status, scene_before, None, mode, execution_mode)
                return RuntimeTurnResult(status, response, validation, tuple(events), turn_id)
            events.append(AgentEvent("validation_result", {"valid": True}, session_id=session_id))
            if mode == "Plan":
                events.append(AgentEvent("preview_ready", {"summary": response.plan.summary}, session_id=session_id))
                status = "planned"
                turn_id = self._persist_turn(session_id, prompt, response, validation, status, scene_before, None, mode, execution_mode)
                return RuntimeTurnResult(status, response, validation, tuple(events), turn_id)
            if mode == "Ask" or execution_mode != "continuous":
                events.append(AgentEvent("approval_required", {"summary": response.plan.summary}, session_id=session_id))
                status = "approval_required"
                turn_id = self._persist_turn(session_id, prompt, response, validation, status, scene_before, None, mode, execution_mode)
                return RuntimeTurnResult(status, response, validation, tuple(events), turn_id)
            if session_id in self._stopped_sessions:
                self._stopped_sessions.discard(session_id)
                events.append(AgentEvent("stopped", {}, session_id=session_id))
                status = "stopped"
                turn_id = self._persist_turn(session_id, prompt, response, validation, status, scene_before, None, mode, execution_mode)
                return RuntimeTurnResult(status, response, validation, tuple(events), turn_id)
            events.append(AgentEvent("execution_started", {"summary": response.plan.summary}, session_id=session_id))
            self.command_service.execute(response.plan)
            events.append(AgentEvent("execution_finished", {"status": "completed"}, session_id=session_id))
            status = "completed"
            turn_id = self._persist_turn(session_id, prompt, response, validation, status, scene_before, scene_after, mode, execution_mode)
            return RuntimeTurnResult(status, response, validation, tuple(events), turn_id)
        except Exception as error:
            events.append(AgentEvent("error", {"message": str(error)}, session_id=session_id))
            response = AgentResponse("本轮执行失败。", None)
            turn_id = self._persist_turn(session_id, prompt, response, None, "failed", scene_before, None, mode, execution_mode)
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
        )
