"""右侧 Agent 抽屉内容的交互测试。"""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from services.agent_provider import AgentResponse
from services.scene_commands import CommandPlan
from ui.agent_panel import AgentPanel


class AgentPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def test_message_plan_and_execute_signal(self) -> None:
        panel = AgentPanel()
        messages: list[str] = []
        executed: list[bool] = []
        panel.message_requested.connect(messages.append)
        panel.execute_requested.connect(lambda: executed.append(True))
        panel.prompt_edit.setPlainText("生成向量 a=(2,1) 和 b=(1,3)")
        QTest.keyClick(panel.prompt_edit, Qt.Key.Key_Return)
        self.assertEqual(messages, ["生成向量 a=(2,1) 和 b=(1,3)"])
        plan = CommandPlan(summary="demo", operations=({"op": "scene.clear"},))
        panel.show_response(AgentResponse("已生成", plan))
        self.assertIs(panel.plan, plan)
        panel.execute_button.click()
        self.assertEqual(executed, [True])

    def test_escape_emits_close_and_3d_disables_plan(self) -> None:
        panel = AgentPanel()
        closed: list[bool] = []
        panel.close_requested.connect(lambda: closed.append(True))
        panel.prompt_edit.setFocus()
        QTest.keyClick(panel.prompt_edit, Qt.Key.Key_Escape)
        self.assertEqual(closed, [True])
        panel.show_plan(CommandPlan(operations=({"op": "scene.clear"},)))
        panel.set_scene_mode(False)
        self.assertFalse(panel.execute_button.isEnabled())
        panel.set_scene_mode(True)
        self.assertTrue(panel.execute_button.isEnabled())

    def test_3d_plan_can_execute_only_in_3d_mode(self) -> None:
        panel = AgentPanel()
        panel.show_plan(CommandPlan(scene="3d", operations=({"op": "surface.create", "alias": "s", "kind": "explicit", "expression": "z=x+y"},)))
        self.assertFalse(panel.execute_button.isEnabled())
        panel.set_scene_mode(False)
        self.assertTrue(panel.execute_button.isEnabled())

    def test_busy_keeps_prompt_text_and_blocks_send(self) -> None:
        panel = AgentPanel()
        messages: list[str] = []
        panel.message_requested.connect(messages.append)
        panel.set_busy(True)
        panel.prompt_edit.setPlainText("画一条抛物线")
        QTest.keyClick(panel.prompt_edit, Qt.Key.Key_Return)

        self.assertEqual(messages, [])
        self.assertEqual(panel.prompt_edit.toPlainText(), "画一条抛物线")
        self.assertTrue(panel.send_button.isEnabled())
        self.assertEqual(panel.send_button.text(), "停止")

        panel.set_busy(False)
        self.assertTrue(panel.send_button.isEnabled())
        QTest.keyClick(panel.prompt_edit, Qt.Key.Key_Return)
        self.assertEqual(messages, ["画一条抛物线"])

    def test_busy_send_button_emits_stop_request(self) -> None:
        panel = AgentPanel()
        stopped: list[bool] = []
        panel.stop_requested.connect(lambda: stopped.append(True))
        panel.set_busy(True)
        panel.send_button.click()
        self.assertEqual(stopped, [True])

    def test_send_button_requires_non_empty_prompt(self) -> None:
        panel = AgentPanel()
        self.assertFalse(panel.send_button.isEnabled())
        panel.prompt_edit.setPlainText("   ")
        self.assertFalse(panel.send_button.isEnabled())
        panel.prompt_edit.setPlainText("画圆")
        self.assertTrue(panel.send_button.isEnabled())

    def test_status_returns_to_model_state_after_request(self) -> None:
        panel = AgentPanel()
        panel.set_model_status("teaching-model", enabled=True)
        panel.set_busy(True)
        self.assertEqual(panel.status_label.text(), "正在请求…")
        panel.set_busy(False)
        self.assertEqual(panel.status_label.text(), "teaching-model · 已连接")

    def test_error_after_cleared_plan_does_not_touch_deleted_widgets(self) -> None:
        panel = AgentPanel()
        panel.show_plan(CommandPlan(operations=({"op": "scene.clear"},)))
        panel.clear_plan()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

        panel.show_error("无法连接模型服务")
        self.assertEqual(panel.status_label.text(), "无法连接模型服务")
        self.assertIsNone(panel.plan)
        self.assertFalse(panel.execute_button.isEnabled())

    def test_invalid_plan_cannot_be_executed(self) -> None:
        panel = AgentPanel()
        panel.show_plan(
            CommandPlan(operations=({"op": "python.exec"},)),
            ("操作 1: 不支持的命令",),
        )
        self.assertFalse(panel.execute_button.isEnabled())
        self.assertIn("不支持的命令", panel.status_label.text())


if __name__ == "__main__":
    unittest.main()
