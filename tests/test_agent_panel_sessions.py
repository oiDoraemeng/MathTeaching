from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from ui.agent_panel import AgentPanel


def test_panel_starts_with_one_new_chat_tab_and_can_create_sessions() -> None:
    app = QApplication.instance() or QApplication([])
    panel = AgentPanel()

    assert panel.session_tabs.count() == 1
    assert panel.session_tabs.tabText(0) == "New Chat"

    session_id = panel.new_chat()

    assert session_id == panel.active_session_id
    assert panel.session_tabs.count() == 2
    assert panel.session_tabs.currentIndex() == 1


def test_panel_cannot_close_last_session_tab() -> None:
    app = QApplication.instance() or QApplication([])
    panel = AgentPanel()

    panel.close_chat(0)

    assert panel.session_tabs.count() == 1
    assert panel.active_session_id


def test_mode_and_execution_strategy_are_stored_per_session() -> None:
    app = QApplication.instance() or QApplication([])
    panel = AgentPanel()

    panel.mode_combo.setCurrentText("Plan")
    panel.execution_combo.setCurrentText("连续自动执行")
    first = panel.active_session_id
    panel.new_chat()

    assert panel.mode_combo.currentText() == "Agent"
    assert panel.execution_combo.currentText() == "确认执行"
    panel.session_tabs.setCurrentIndex(0)
    assert panel.active_session_id == first
    assert panel.mode_combo.currentText() == "Plan"
    assert panel.execution_combo.currentText() == "连续自动执行"
