"""Agent provider 协议和 HTTP 安全边界测试。"""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from services.agent_provider import (
    AgentMessage,
    AgentSettings,
    OpenAICompatibleProvider,
    ProviderEvent,
    ProviderToolCall,
    ToolResultMessage,
    SceneContext,
)


class _Response:
    status = 200

    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class _StreamingResponse:
    status = 200

    def __iter__(self):
        return iter((b"data: [DONE]\\n",))

    def close(self) -> None:
        return None


class _StreamingLinesResponse:
    status = 200

    def __init__(self, *lines: bytes) -> None:
        self.lines = lines

    def __iter__(self):
        return iter(self.lines)

    def close(self) -> None:
        return None


class _StreamingProvider(OpenAICompatibleProvider):
    def _stream_request(self, messages, tools=None):
        yield {"choices": [{"delta": {"content": "解释"}}]}
        yield {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call-1", "function": {"name": "create_curve", "arguments": '{"expression":"x^2"'}}]}}]}
        yield {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": ',"range":[-1,1]}'}}]}}]}
        yield {"choices": [{"delta": {}, "finish_reason": "tool_calls"}]}


class _ResponsesStreamingProvider(OpenAICompatibleProvider):
    def _stream_responses_request(self, messages, catalog):
        yield {"type": "response.reasoning_summary_text.delta", "delta": "分析中"}
        yield {"type": "response.output_text.delta", "delta": "已完成"}
        yield {"type": "response.output_item.added", "item": {"id": "item-1", "type": "function_call", "call_id": "call-1", "name": "scene.inspect", "arguments": ""}}
        yield {"type": "response.function_call_arguments.done", "item_id": "item-1", "name": "scene.inspect", "arguments": "{}"}


class AgentProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = AgentSettings(
            base_url="https://model.example/v1/",
            api_key="secret-token",
            model="teaching-model",
            timeout_seconds=12,
        )

    def test_openai_compatible_request_and_fenced_plan(self) -> None:
        content = """```json
{"version": 1, "scene": "2d", "summary": "clear", "operations": [{"op": "scene.clear"}]}
```"""
        with patch("services.agent_provider.urlopen", return_value=_Response({
            "choices": [{"message": {"content": content}}],
        })) as opened:
            response = OpenAICompatibleProvider(self.settings).create_plan(
                (AgentMessage("user", "清空场景"),),
                SceneContext(scene_mode="2d"),
            )
        request = opened.call_args.args[0]
        self.assertEqual(request.full_url, "https://model.example/v1/chat/completions")
        self.assertEqual(request.get_header("Authorization"), "Bearer secret-token")
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "teaching-model")
        self.assertEqual(payload["temperature"], 0)
        self.assertEqual(payload["messages"][-1]["content"], "清空场景")
        self.assertIsNotNone(response.plan)

    def test_real_capability_catalog_is_sent_without_strict_in_both_protocols(self) -> None:
        """The registry has genuinely optional parameters, so ``strict`` must stay off.

        Server-side Structured Outputs requires every key in ``properties`` to
        appear in ``required``; six of the nine capabilities do not satisfy that,
        so sending ``strict`` gets the whole tool request rejected with HTTP 400.
        Local ``validate_tool_arguments`` is the real boundary instead.
        """
        from agent.capabilities import build_default_registry

        catalog = build_default_registry().catalog()["capabilities"]
        self.assertEqual(len(catalog), 9)
        optional_keys = {
            item["name"]
            for item in catalog
            if set(item["input_schema"].get("properties", {})) - set(item["input_schema"].get("required", []))
        }
        self.assertTrue(optional_keys, "catalog should still exercise optional parameters")

        for protocol, reply in (
            ("chat_completions", {"choices": [{"message": {"content": "ok"}}]}),
            ("responses", {"output_text": "ok", "output": []}),
        ):
            settings = AgentSettings(base_url="https://model.example/v1", api_key="secret-token", model="teaching-model", protocol=protocol)
            with patch("services.agent_provider.urlopen", return_value=_Response(reply)) as opened:
                OpenAICompatibleProvider(settings).request_tools((AgentMessage("user", "画图"),), catalog)

            payload = json.loads(opened.call_args.args[0].data.decode("utf-8"))
            tools = payload["tools"]
            self.assertEqual(len(tools), 9, protocol)
            for definition in tools:
                self.assertNotIn("strict", definition, protocol)
                self.assertNotIn("strict", definition.get("function", {}), protocol)

    def test_system_prompt_declares_every_allowed_command_operation(self) -> None:
        """The JSON fallback prompt and the executor must list the same operations.

        The prompt is the only thing telling a model which operations exist on
        the JSON/fenced-plan path, so an operation missing here is unreachable
        even though ``SceneCommandService`` would accept it. Locking both
        directions also fails loudly if an operation is retired from the
        executor but left advertised.
        """
        import re

        from services.agent_provider import SYSTEM_PROMPT
        from services.scene_commands import _ALLOWED_OPERATIONS

        marker = "只能使用已注册的场景操作："
        self.assertIn(marker, SYSTEM_PROMPT)
        block = SYSTEM_PROMPT.split(marker, 1)[1].split("。", 1)[0]
        declared = set(re.findall(r"[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*", block))

        self.assertEqual(declared, set(_ALLOWED_OPERATIONS))

    def test_plain_text_reply_becomes_chat_message(self) -> None:
        with patch("services.agent_provider.urlopen", return_value=_Response({
            "choices": [{"message": {"content": "请问你想画哪个区间的图像？"}}],
        })):
            response = OpenAICompatibleProvider(self.settings).create_plan(
                (AgentMessage("user", "画个图"),), SceneContext()
            )
        self.assertIsNone(response.plan)
        self.assertEqual(response.text, "请问你想画哪个区间的图像？")

    def test_malformed_structured_reply_is_readable_and_does_not_expose_key(self) -> None:
        with patch("services.agent_provider.urlopen", return_value=_Response({
            "choices": [{"message": {"content": '{"operations": [oops] secret-token'}}],
        })):
            with self.assertRaises(ValueError) as raised:
                OpenAICompatibleProvider(self.settings).create_plan(
                    (AgentMessage("user", "x"),), SceneContext()
                )
        self.assertIn("合法", str(raised.exception))
        self.assertNotIn("secret-token", str(raised.exception))

    def test_network_error_masks_api_key(self) -> None:
        with patch("services.agent_provider.urlopen", side_effect=OSError("secret-token leaked")):
            with self.assertRaises(RuntimeError) as raised:
                OpenAICompatibleProvider(self.settings).create_plan(
                    (AgentMessage("user", "x"),), SceneContext()
                )
        self.assertNotIn("secret-token", str(raised.exception))

    def test_key_is_scrubbed_from_plan_display_fields(self) -> None:
        content = json.dumps({
            "version": 1,
            "summary": "secret-token",
            "operations": [{"op": "scene.export_png", "filename": "secret-token.png"}],
        })
        with patch("services.agent_provider.urlopen", return_value=_Response({
            "choices": [{"message": {"content": content}}],
        })):
            response = OpenAICompatibleProvider(self.settings).create_plan(
                (AgentMessage("user", "导出"),), SceneContext()
            )
        self.assertNotIn("secret-token", response.text)
        self.assertNotIn("secret-token", response.plan.to_json())

    def test_stream_emits_text_tool_call_and_completed_events(self) -> None:
        provider = _StreamingProvider(self.settings)

        events = list(provider.stream((AgentMessage("user", "画曲线"),), tools=()))

        self.assertEqual([event.type for event in events], ["message_delta", "tool_call", "completed"])
        self.assertEqual(events[0].data["text"], "解释")
        self.assertEqual(events[1].data["tool_call_id"], "call-1")
        self.assertEqual(events[1].data["name"], "create_curve")
        self.assertEqual(events[1].data["arguments"]["range"], [-1, 1])
        self.assertIsInstance(events[2], ProviderEvent)

    def test_stream_request_disables_parallel_tool_calls(self) -> None:
        provider = OpenAICompatibleProvider(self.settings)
        tools = [{"type": "function", "function": {"name": "scene.inspect", "parameters": {"type": "object"}}}]

        with patch("services.agent_provider.urlopen", return_value=_StreamingResponse()) as opened:
            list(provider.stream((AgentMessage("user", "检查场景"),), tools=tools))

        payload = json.loads(opened.call_args.args[0].data.decode("utf-8"))
        self.assertTrue(payload["stream"])
        self.assertFalse(payload["parallel_tool_calls"])
        self.assertEqual(payload["tools"], tools)

    def test_stream_tools_preserves_tool_transcript_on_continuation(self) -> None:
        provider = OpenAICompatibleProvider(self.settings)
        catalog = [{"name": "scene.inspect", "description": "inspect", "input_schema": {"type": "object", "additionalProperties": False}}]
        first = _StreamingLinesResponse(
            b'data: {"choices":[{"delta":{"tool_calls":[{"index":0,"id":"call-1","function":{"name":"scene.inspect","arguments":"{}"}}]}}]}\n',
            b"data: [DONE]\n",
        )
        second = _StreamingLinesResponse(
            b'data: {"choices":[{"delta":{"content":"\\u573a\\u666f\\u4e3a\\u7a7a"}}]}\n',
            b"data: [DONE]\n",
        )
        with patch("services.agent_provider.urlopen", side_effect=[first, second]) as opened:
            response = provider.stream_tools((AgentMessage("user", "检查场景"),), catalog)
            continuation = provider.stream_tools((
                AgentMessage("user", "检查场景"),
                AgentMessage.assistant_tool_calls((response.tool_calls[0],)),
                AgentMessage.tool_result(ToolResultMessage("call-1", "scene.inspect", "{}")),
            ), catalog)

        payload = json.loads(opened.call_args_list[1].args[0].data.decode("utf-8"))
        self.assertEqual(payload["messages"][-2]["tool_calls"][0]["id"], "call-1")
        self.assertEqual(payload["messages"][-1]["tool_call_id"], "call-1")
        self.assertEqual(continuation.text, "场景为空")

    def test_chat_tool_protocol_serializes_calls_results_and_catalog(self) -> None:
        provider = OpenAICompatibleProvider(self.settings)
        messages = (
            AgentMessage("user", "画曲线"),
            AgentMessage.assistant_tool_calls((ProviderToolCall("call-1", "scene.inspect", {}),)),
            AgentMessage.tool_result(ToolResultMessage("call-1", "scene.inspect", '{"scene_mode":"2d"}')),
        )
        catalog = [{"name": "scene.inspect", "description": "inspect", "input_schema": {"type": "object", "additionalProperties": False}}]
        with patch("services.agent_provider.urlopen", return_value=_Response({
            "choices": [{"message": {"content": "", "tool_calls": [{"id": "call-2", "function": {"name": "scene.find", "arguments": '{"alias":"f"}'}}]}}],
        })) as opened:
            response = provider.request_tools(messages, catalog)

        payload = json.loads(opened.call_args.args[0].data.decode("utf-8"))
        self.assertFalse(payload["parallel_tool_calls"])
        self.assertEqual(payload["tools"][0]["function"]["name"], "scene.inspect")
        self.assertEqual(payload["messages"][-2]["tool_calls"][0]["id"], "call-1")
        self.assertEqual(payload["messages"][-1]["tool_call_id"], "call-1")
        self.assertEqual(response.tool_calls[0].call_id, "call-2")
        self.assertEqual(response.tool_calls[0].arguments, {"alias": "f"})

    def test_responses_tool_protocol_uses_function_call_output_items(self) -> None:
        settings = AgentSettings(base_url="https://model.example/v1", api_key="secret-token", model="teaching-model", protocol="responses")
        provider = OpenAICompatibleProvider(settings)
        messages = (
            AgentMessage("user", "检查场景"),
            AgentMessage.assistant_tool_calls((ProviderToolCall("call-1", "scene.inspect", {}),)),
            AgentMessage.tool_result(ToolResultMessage("call-1", "scene.inspect", "{}")),
        )
        catalog = [{"name": "scene.inspect", "description": "inspect", "input_schema": {"type": "object", "additionalProperties": False}}]
        with patch("services.agent_provider.urlopen", return_value=_Response({
            "output_text": "场景为空",
            "output": [],
        })) as opened:
            response = provider.request_tools(messages, catalog)

        payload = json.loads(opened.call_args.args[0].data.decode("utf-8"))
        self.assertFalse(payload["parallel_tool_calls"])
        self.assertEqual(payload["tools"][0]["name"], "scene.inspect")
        self.assertEqual(payload["input"][-2]["type"], "function_call")
        self.assertEqual(payload["input"][-1]["type"], "function_call_output")
        self.assertEqual(payload["input"][-1]["call_id"], "call-1")
        self.assertEqual(response.text, "场景为空")

    def test_responses_stream_tools_forwards_reasoning_text_and_function_call(self) -> None:
        settings = AgentSettings(base_url="https://model.example/v1", api_key="secret-token", model="teaching-model", protocol="responses")
        provider = _ResponsesStreamingProvider(settings)
        events: list[ProviderEvent] = []

        response = provider.stream_tools((AgentMessage("user", "检查场景"),), [], on_event=events.append)

        self.assertEqual([(event.data["text"], event.data["kind"]) for event in events], [("分析中", "reasoning"), ("已完成", "content")])
        self.assertEqual(response.text, "已完成")
        self.assertEqual(response.tool_calls[0].call_id, "call-1")
        self.assertEqual(response.tool_calls[0].name, "scene.inspect")


if __name__ == "__main__":
    unittest.main()
