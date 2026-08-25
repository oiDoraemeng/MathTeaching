"""在 Qt 工作线程中调用可替换的 Agent provider。"""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QObject, Signal, Slot

from .agent_provider import AgentMessage, AgentResponse, AgentProvider, SceneContext
from .scene_commands import CommandError, CommandPlan, RuleBasedAgentProvider


class RuntimeTurnWorker(QObject):
    """Run the event-driven AgentRuntime without exposing Qt to the runtime."""

    event_ready = Signal(object)
    turn_finished = Signal(object)
    error = Signal(str)
    finished = Signal()

    def __init__(
        self,
        runtime,
        session_id: str,
        prompt: str,
        *,
        mode: str,
        execution_mode: str,
        scene_context=None,
        scene_before=None,
        scene_after=None,
    ) -> None:
        super().__init__()
        self.runtime = runtime
        self.session_id = session_id
        self.prompt = prompt
        self.mode = mode
        self.execution_mode = execution_mode
        self.scene_context = scene_context
        self.scene_before = scene_before
        self.scene_after = scene_after

    @Slot()
    def run(self) -> None:
        try:
            result = self.runtime.run_turn(
                self.session_id,
                self.prompt,
                mode=self.mode,
                execution_mode=self.execution_mode,
                scene_context=self.scene_context,
                scene_before=self.scene_before,
                scene_after=self.scene_after,
            )
            # Runtime persistence allocates the durable turn id after provider
            # work completes. Attach it to every streamed event before the
            # browser projection sees the batch so one prompt stays one card.
            for event in result.events:
                if result.turn_id and getattr(event, "turn_id", None) != result.turn_id:
                    event = replace(event, turn_id=result.turn_id)
                self.event_ready.emit(event)
            self.turn_finished.emit(result)
        except Exception as error:
            self.error.emit(str(error))
        finally:
            self.finished.emit()

    @Slot()
    def stop(self) -> None:
        self.runtime.stop(self.session_id)


class AgentWorker(QObject):
    """只负责自然语言到命令计划，不接触窗口或绘图器。"""

    plan_ready = Signal(object)
    response_ready = Signal(object)
    error = Signal(str)
    finished = Signal()

    def __init__(
        self,
        prompt: str | None = None,
        provider: AgentProvider | None = None,
        *,
        messages: tuple[AgentMessage, ...] | None = None,
        scene_context: SceneContext | None = None,
        agent: object | None = None,
    ) -> None:
        super().__init__()
        self.prompt = prompt or ""
        self.provider = provider or RuleBasedAgentProvider()
        self.messages = messages
        self.scene_context = scene_context or SceneContext()
        self.agent = agent

    @Slot()
    def run(self) -> None:
        try:
            messages = self.messages or (AgentMessage("user", self.prompt),)
            if self.agent is not None and callable(getattr(self.agent, "respond", None)):
                response = self.agent.respond(messages, self.scene_context)
            else:
                response = self.provider.create_plan(messages, self.scene_context)
            if isinstance(response, CommandPlan):
                response = AgentResponse(text="", plan=response, raw_content=response.to_json())
            self.response_ready.emit(response)
            if getattr(response, "plan", None) is not None:
                self.plan_ready.emit(response.plan)
        except (CommandError, ValueError) as error:
            self.error.emit(str(error))
        except Exception as error:  # provider/network errors become UI-safe messages
            self.error.emit(str(error))
        finally:
            self.finished.emit()
