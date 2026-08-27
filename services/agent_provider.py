"""可替换的 AI provider 与受限命令计划解析。"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Iterable, Literal, Protocol, TYPE_CHECKING
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

if TYPE_CHECKING:
    from .scene_commands import CommandPlan


@dataclass(frozen=True)
class AgentMessage:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True)
class SceneContext:
    scene_mode: str = "2d"
    curves: tuple[dict[str, object], ...] = ()
    geometry: tuple[dict[str, object], ...] = ()
    last_plan_summary: str = ""


@dataclass(frozen=True)
class AgentSettings:
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    timeout_seconds: float = 60.0
    provider: str = "openai"
    # Keep direct programmatic construction backward-compatible; the settings
    # dialog explicitly defaults persisted UI configuration to Responses.
    protocol: str = "chat_completions"

    @property
    def is_complete(self) -> bool:
        provider = self.provider.strip().lower()
        if provider == "local":
            return True
        if provider == "deepseek":
            return bool(self.api_key.strip() and self.model.strip())
        return bool(self.base_url.strip() and self.api_key.strip() and self.model.strip())

    @property
    def normalized_protocol(self) -> str:
        return "chat_completions" if self.protocol == "chat_completions" else "responses"


@dataclass(frozen=True)
class AgentResponse:
    text: str
    plan: "CommandPlan | None"
    raw_content: str = ""


@dataclass(frozen=True)
class ProviderEvent:
    """Small serializable event emitted by a streaming model provider."""

    type: Literal["message_delta", "tool_call", "completed"]
    data: dict[str, Any]


@dataclass(frozen=True)
class ToolResultMessage:
    tool_call_id: str
    name: str
    content: str


class AgentProvider(Protocol):
    def create_plan(
        self,
        messages: tuple[AgentMessage, ...],
        scene_context: SceneContext,
    ) -> AgentResponse:
        ...

    def stream(
        self,
        messages: tuple[AgentMessage, ...],
        *,
        tools: Iterable[dict[str, Any]] = (),
    ) -> Iterable[ProviderEvent]:
        ...


SYSTEM_PROMPT = """你是 Math3DTeaching 的 Math Teacher Agent。
先解释数学概念；需要修改场景时，只能返回受限 CommandPlan JSON（或 JSON fenced block），不得输出或执行 Python。
只能使用已注册的场景操作：scene.set_mode、scene.clear、curve.create、curve.update、curve.delete、
point.upsert、point3d.upsert、point.delete、linear.upsert、linear.delete、teach.vector_addition、
annotation.upsert、annotation.delete、view.fit、scene.export_png、surface.create、surface.update、surface.delete、
calculus.derivative、calculus.integral_area、calculus.tangent、area.fill、linear_algebra.matrix_transform、
linear_algebra.determinant_area、geometry.intersection。
不要绕过 SceneCommandService，不要自行替代本地数学验证；不确定时用纯文本提出澄清问题，不生成命令计划。
纯文本只用于解释和提问，不要在其中混入命令计划片段。
"""


def _looks_like_structured_output(content: str) -> bool:
    """判断内容是否在尝试给出结构化计划；纯文本聊天回复不算。"""
    stripped = content.strip()
    return stripped.startswith(("{", "[", "```")) or '"operations"' in stripped


def parse_plan_response(content: str) -> "CommandPlan":
    """解析纯 JSON 或 ```json fenced block，并交给 CommandPlan 校验。"""
    from .scene_commands import CommandError, CommandPlan

    candidates = [content.strip()]
    marker = "```"
    if marker in content:
        for block in content.split(marker)[1::2]:
            cleaned = block.strip()
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].lstrip(" \r\n")
            candidates.append(cleaned)
    last_error: Exception | None = None
    for candidate in candidates:
        if not candidate:
            continue
        try:
            payload = json.loads(candidate)
            return CommandPlan.from_dict(payload)
        except (json.JSONDecodeError, CommandError, TypeError, ValueError) as error:
            last_error = error
    detail = f": {last_error}" if last_error else ""
    raise CommandError(f"模型没有返回合法的 CommandPlan JSON{detail}")


def _scrub(value: object, secret: str) -> object:
    if isinstance(value, str):
        return value.replace(secret, "***") if secret else value
    if isinstance(value, dict):
        return {key: _scrub(item, secret) for key, item in value.items()}
    if isinstance(value, list):
        return [_scrub(item, secret) for item in value]
    if isinstance(value, tuple):
        return tuple(_scrub(item, secret) for item in value)
    return value


def _scrub_plan(plan: "CommandPlan", secret: str) -> "CommandPlan":
    from .scene_commands import CommandPlan

    return CommandPlan(
        version=plan.version,
        scene=plan.scene,
        summary=str(_scrub(plan.summary, secret)),
        operations=tuple(_scrub(dict(operation), secret) for operation in plan.operations),
    )


class OpenAICompatibleProvider:
    """使用标准库调用 /chat/completions 的 provider。"""

    def __init__(self, settings: AgentSettings) -> None:
        self.settings = settings
        if not settings.is_complete:
            raise ValueError("Base URL、API Key 和模型名必须完整。")

    def _safe_error(self, error: object) -> str:
        message = str(error)
        if self.settings.api_key:
            message = message.replace(self.settings.api_key, "***")
        return message

    def _request(self, messages: tuple[AgentMessage, ...], *, timeout: float | None = None) -> str:
        protocol = self.settings.normalized_protocol
        url = f"{self.settings.base_url.rstrip('/')}/{ 'responses' if protocol == 'responses' else 'chat/completions' }"
        request_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *({"role": message.role, "content": message.content} for message in messages),
        ]
        payload = {"model": self.settings.model, "temperature": 0}
        if protocol == "responses":
            payload["input"] = request_messages
        else:
            payload["messages"] = request_messages
        request = Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.settings.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=timeout or self.settings.timeout_seconds) as response:
                status = getattr(response, "status", 200)
                body = response.read().decode("utf-8")
        except HTTPError as error:
            raise RuntimeError(f"模型服务返回 HTTP {error.code}。") from None
        except (URLError, TimeoutError, OSError) as error:
            raise RuntimeError(f"无法连接模型服务：{self._safe_error(error)}") from None
        if status < 200 or status >= 300:
            raise RuntimeError(f"模型服务返回 HTTP {status}。")
        try:
            response_payload = json.loads(body)
            if protocol == "responses":
                content = response_payload.get("output_text")
                if not content:
                    content = response_payload["output"][0]["content"][0]["text"]
            else:
                content = response_payload["choices"][0]["message"]["content"]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as error:
            raise RuntimeError("模型服务返回了无法识别的 JSON。") from error
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("模型服务没有返回消息内容。")
        return content

    def _stream_request(
        self,
        messages: tuple[AgentMessage, ...],
        tools: Iterable[dict[str, Any]] = (),
    ) -> Iterable[dict[str, Any]]:
        """Yield decoded SSE data objects from an OpenAI-compatible endpoint."""
        url = f"{self.settings.base_url.rstrip('/')}/chat/completions"
        request_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *({"role": message.role, "content": message.content} for message in messages),
        ]
        payload: dict[str, Any] = {
            "model": self.settings.model,
            "messages": request_messages,
            "temperature": 0,
            "stream": True,
        }
        tool_list = list(tools)
        if tool_list:
            payload["tools"] = tool_list
            payload["tool_choice"] = "auto"
        request = Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.settings.api_key}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
            method="POST",
        )
        try:
            response = urlopen(request, timeout=self.settings.timeout_seconds)
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    decoded = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if isinstance(decoded, dict):
                    yield decoded
        except HTTPError as error:
            raise RuntimeError(f"模型服务返回 HTTP {error.code}。") from None
        except (URLError, TimeoutError, OSError) as error:
            raise RuntimeError(f"无法连接模型服务：{self._safe_error(error)}") from None
        finally:
            close = getattr(locals().get("response"), "close", None)
            if close is not None:
                close()

    def stream(
        self,
        messages: tuple[AgentMessage, ...],
        *,
        tools: Iterable[dict[str, Any]] = (),
    ) -> Iterable[ProviderEvent]:
        text_parts: list[str] = []
        tool_calls: dict[int, dict[str, Any]] = {}
        for chunk in self._stream_request(messages, tools):
            choices = chunk.get("choices") if isinstance(chunk, dict) else None
            if not isinstance(choices, list) or not choices:
                continue
            choice = choices[0] if isinstance(choices[0], dict) else {}
            delta = choice.get("delta") if isinstance(choice.get("delta"), dict) else {}
            # DeepSeek 等模型把思考过程放在 reasoning_content 字段，正式
            # 回答放在 content 字段；两者都作为流式增量转发，前端用 kind 区分。
            reasoning = delta.get("reasoning_content")
            if isinstance(reasoning, str) and reasoning:
                yield ProviderEvent("message_delta", {"text": reasoning, "kind": "reasoning"})
            content = delta.get("content")
            if isinstance(content, str) and content:
                text_parts.append(content)
                yield ProviderEvent("message_delta", {"text": content})
            calls = delta.get("tool_calls")
            if isinstance(calls, list):
                for call in calls:
                    if not isinstance(call, dict):
                        continue
                    index = int(call.get("index", 0))
                    item = tool_calls.setdefault(index, {"tool_call_id": "", "name": "", "arguments_text": ""})
                    if call.get("id"):
                        item["tool_call_id"] = str(call["id"])
                    function = call.get("function") if isinstance(call.get("function"), dict) else {}
                    if function.get("name"):
                        item["name"] = str(function["name"])
                    if isinstance(function.get("arguments"), str):
                        item["arguments_text"] += function["arguments"]
        normalized_calls: list[dict[str, Any]] = []
        for index in sorted(tool_calls):
            item = tool_calls[index]
            try:
                arguments = json.loads(item["arguments_text"] or "{}")
            except json.JSONDecodeError as error:
                raise RuntimeError(f"工具参数不是有效 JSON：{error.msg}") from None
            normalized = {
                "tool_call_id": item["tool_call_id"],
                "name": item["name"],
                "arguments": arguments,
            }
            normalized_calls.append(normalized)
            yield ProviderEvent("tool_call", normalized)
        yield ProviderEvent("completed", {"text": "".join(text_parts), "tool_calls": normalized_calls})

    def create_plan(
        self,
        messages: tuple[AgentMessage, ...],
        scene_context: SceneContext,
    ) -> AgentResponse:
        context_message = AgentMessage(
            "system",
            "当前场景上下文（只读）：" + json.dumps(
                {
                    "scene_mode": scene_context.scene_mode,
                    "curves": scene_context.curves,
                    "geometry": scene_context.geometry,
                    "last_plan_summary": scene_context.last_plan_summary,
                },
                ensure_ascii=False,
            ),
        )
        content = self._request((context_message, *messages))
        try:
            plan = parse_plan_response(content)
        except ValueError as error:
            # 模型可能回显上下文或凭据；错误文本永远不应包含 API key。
            from .scene_commands import CommandError

            safe_content = self._safe_error(content)
            try:
                payload = json.loads(content.strip())
            except (json.JSONDecodeError, TypeError):
                payload = None
            if isinstance(payload, dict) and isinstance(payload.get("question"), str):
                return AgentResponse(
                    text=self._safe_error(payload["question"]),
                    plan=None,
                    raw_content=safe_content,
                )
            if not _looks_like_structured_output(content):
                # 纯文本是合法的澄清或讲解回复，不应当作协议错误抛出。
                return AgentResponse(text=safe_content, plan=None, raw_content=safe_content)
            raise CommandError(self._safe_error(error)) from None
        safe_content = self._safe_error(content)
        safe_plan = _scrub_plan(plan, self.settings.api_key)
        return AgentResponse(
            text=safe_plan.summary or "已生成可验证的命令计划，请确认后执行。",
            plan=safe_plan,
            raw_content=safe_content,
        )

    def test_connection(self) -> None:
        self._request((AgentMessage("user", "请返回一个空的澄清问题，不要修改场景。"),), timeout=10.0)


# 新架构的通用命名，保留旧类名以兼容已有调用方。
ModelProvider = OpenAICompatibleProvider
