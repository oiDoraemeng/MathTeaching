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


class _StreamingProvider(OpenAICompatibleProvider):
    def _stream_request(self, messages, tools=None):
        yield {"choices": [{"delta": {"content": "解释"}}]}
        yield {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call-1", "function": {"name": "create_curve", "arguments": '{"expression":"x^2"'}}]}}]}
        yield {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": ',"range":[-1,1]}'}}]}}]}
        yield {"choices": [{"delta": {}, "finish_reason": "tool_calls"}]}


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


if __name__ == "__main__":
    unittest.main()
