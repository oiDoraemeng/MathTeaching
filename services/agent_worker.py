"""在 Qt 工作线程中调用可替换的 Agent provider。"""

from __future__ import annotations

from dataclasses import replace
from time import monotonic

from PySide6.QtCore import QObject, Signal, Slot

from .agent_provider import AgentMessage, AgentResponse, AgentProvider, SceneContext
from .scene_commands import CommandError, CommandPlan, RuleBasedAgentProvider


_STREAM_FLUSH_INTERVAL_SECONDS = 0.04
_STREAM_MAX_CHARS = 48


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
        turn_id: str | None = None,
        pane_id: str | None = None,
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
        self.turn_id = turn_id
        self.pane_id = pane_id

    @Slot()
    def run(self) -> None:
        try:
            streamed_ids: set[int] = set()
            pending_event = None
            pending_text: list[str] = []
            pending_kind: str | None = None
            pending_size = 0
            last_flush = monotonic()

            def flush_stream() -> None:
                nonlocal pending_event, pending_text, pending_kind, pending_size, last_flush
                if pending_event is None:
                    return
                payload = dict(pending_event.payload)
                payload["text"] = "".join(pending_text)
                self.event_ready.emit(replace(pending_event, payload=payload))
                pending_event = None
                pending_text = []
                pending_kind = None
                pending_size = 0
                last_flush = monotonic()

            def on_event(event) -> None:
                nonlocal pending_event, pending_kind, pending_size
                streamed_ids.add(id(event))
                if event.type != "message_delta":
                    flush_stream()
                    self.event_ready.emit(event)
                    return
                text = event.payload.get("text")
                kind = event.payload.get("kind")
                if not isinstance(text, str) or not text:
                    flush_stream()
                    self.event_ready.emit(event)
                    return
                if pending_event is not None and kind != pending_kind:
                    flush_stream()
                if pending_event is None:
                    pending_event = event
                    pending_kind = kind if isinstance(kind, str) else None
                pending_text.append(text)
                pending_size += len(text)
                if pending_size >= _STREAM_MAX_CHARS or monotonic() - last_flush >= _STREAM_FLUSH_INTERVAL_SECONDS:
                    flush_stream()

            result = self.runtime.run_turn(
                self.session_id,
                self.prompt,
                mode=self.mode,
                execution_mode=self.execution_mode,
                scene_context=self.scene_context,
                scene_before=self.scene_before,
                scene_after=self.scene_after,
                turn_id=self.turn_id,
                on_event=on_event,
                **({"pane_id": self.pane_id} if self.pane_id is not None else {}),
            )
            flush_stream()
            # 持久化后将轮次标识补到流事件，保证同一提示词只生成一张卡片。
            for event in result.events:
                if id(event) in streamed_ids:
                    # 已实时转发过的事件不再重复发出。
                    continue
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
