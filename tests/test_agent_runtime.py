"""Math Teacher Agent 新架构的协议级回归测试。"""

from __future__ import annotations

from io import StringIO
import json
from tempfile import TemporaryDirectory
import unittest

from PySide6.QtCore import QSettings

from agent.instruction import InstructionStore
from agent.mcp_server import Math3DMCPServer
from agent.memory import MemoryProfile, MemoryStore
from agent.prompt_manager import PromptManager
from agent.runtime import AgentRuntime
from agent.scene_snapshot import SceneSnapshot
from agent.events import AgentEvent
from agent.skill_manager import SkillManager
from services.scene_commands import CommandPlan, CommandError, SceneCommandService


class _Host:
    def __init__(self) -> None:
        self.events: list[str] = []
        self.operations: list[dict[str, object]] = []

    def begin_scene_command_transaction(self) -> None:
        self.events.append("begin")

    def apply_scene_command(self, operation: dict[str, object]) -> None:
        self.operations.append(operation)

    def commit_scene_command_transaction(self) -> None:
        self.events.append("commit")

    def rollback_scene_command_transaction(self) -> None:
        self.events.append("rollback")


class _FingerprintHost(_Host):
    def __init__(self, matches: bool) -> None:
        super().__init__()
        self.matches = matches
        self.checked: list[str] = []

    def check_scene_fingerprint(self, expected: str) -> bool:
        self.checked.append(expected)
        return self.matches


class AgentRuntimeTests(unittest.TestCase):
    def test_all_builtin_skills_are_discovered_and_return_valid_plans(self) -> None:
        manager = SkillManager()
        self.assertEqual({item.name for item in manager.list_skills()}, {"geometry", "calculus", "linear_algebra"})
        for request in ("创建点 P(1,2)", "求导数 f(x)=x^2", "解释行列式为什么表示面积"):
            result = manager.create_plan_for_request(request)
            self.assertIsNotNone(result)
            assert result is not None
            self.assertTrue(manager.command_service.preview(result[1]).valid)

    def test_determinant_request_selects_teach_and_visualize(self) -> None:
        self.assertEqual(PromptManager().select("解释行列式为什么表示面积"), ("teach", "visualize"))
        result = AgentRuntime().respond("解释行列式为什么表示面积")
        self.assertIsNotNone(result.response.plan)
        self.assertTrue(result.validation and result.validation.valid)

    def test_memory_and_instruction_stores_use_json_qsettings(self) -> None:
        settings = QSettings("Math3DTeachingTests", "AgentRuntimeTests")
        settings.clear()
        memory = MemoryStore(settings)
        saved = memory.save(MemoryProfile("university", False, "zh-CN", ["determinant"]))
        self.assertEqual(memory.load(), saved)
        instructions = InstructionStore(settings=settings)
        self.assertIn("CommandPlan", instructions.save("任何场景修改都必须生成 CommandPlan。"))
        self.assertEqual(instructions.load(), "任何场景修改都必须生成 CommandPlan。")
        settings.clear()

    def test_mcp_json_rpc_and_stdio_use_command_service(self) -> None:
        host = _Host()
        server = Math3DMCPServer(SceneCommandService(host))
        listed = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        self.assertEqual(len(listed["result"]["tools"]), 7)
        request = {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "create_point", "alias": "P", "coordinates": [1, 2]}}
        response = server.handle_request(request)
        plan = CommandPlan.from_json(response["result"]["content"][0]["text"])
        self.assertTrue(SceneCommandService(host).preview(plan).valid)
        output = StringIO()
        server.serve_stdio(StringIO(json.dumps({"jsonrpc": "2.0", "id": 3, "method": "initialize"}) + "\n"), output)
        self.assertEqual(json.loads(output.getvalue())["result"]["serverInfo"]["name"], "Math3D MCP")

    def test_3d_plan_is_explicitly_scoped_and_executes_transaction(self) -> None:
        host = _Host()
        plan = CommandPlan(scene="3d", operations=({"op": "surface.create", "alias": "s", "kind": "explicit", "expression": "z=x+y"},))
        validation = SceneCommandService(host).execute(plan)
        self.assertTrue(validation.valid)
        self.assertEqual(host.events, ["begin", "commit"])
        self.assertEqual(host.operations[0], {"op": "scene.set_mode", "mode": "3d"})

    def test_scene_scope_rejects_cross_dimension_operations(self) -> None:
        with self.assertRaises(CommandError):
            SceneCommandService().execute(CommandPlan(scene="2d", operations=({"op": "surface.create", "alias": "s", "kind": "explicit", "expression": "z=x+y"},)))

    def test_fingerprint_is_checked_before_transaction(self) -> None:
        host = _FingerprintHost(matches=False)
        snapshot = SceneSnapshot()
        plan = CommandPlan(operations=({"op": "point.upsert", "alias": "P", "coordinates": [1, 2]},))

        with self.assertRaisesRegex(CommandError, "scene_changed_since_plan"):
            SceneCommandService(host).execute(plan, expected_scene_fingerprint=snapshot.fingerprint())

        self.assertEqual(host.events, [])
        self.assertEqual(host.operations, [])

    def test_runtime_persists_the_base_scene_fingerprint(self) -> None:
        from agent.session_store import SessionStore

        with TemporaryDirectory() as root:
            store = SessionStore(app_root=root)
            snapshot = SceneSnapshot()
            host = _FingerprintHost(matches=True)
            runtime = AgentRuntime(command_service=SceneCommandService(host), session_store=store)
            session = store.create_session("Chat")

            result = runtime.run_turn(session.id, "创建点 P(1,2)", scene_before=snapshot)

            self.assertEqual(result.status, "completed")
            self.assertEqual(store.get_turn(result.turn_id).validation["base_scene_fingerprint"], snapshot.fingerprint())
            self.assertEqual(host.checked, [snapshot.fingerprint()])

    def test_runtime_events_are_json_safe_bounded_and_redacted(self) -> None:
        event = AgentEvent("tool_finished", {"api_key": "secret", "summary": "x" * 700, "nested": {"token": "hidden"}})

        self.assertEqual(event.payload["api_key"], "***")
        self.assertEqual(event.payload["nested"]["token"], "***")
        self.assertEqual(len(event.payload["summary"]), 512)


if __name__ == "__main__":
    unittest.main()
