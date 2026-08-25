from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from ui.agent_sidebar import AgentSidebar


def test_history_is_an_in_panel_view_with_back_action() -> None:
    app = QApplication.instance() or QApplication([])
    sidebar = AgentSidebar()
    sidebar.expand()

    sidebar.show_history()

    assert sidebar.tool_pages.currentWidget() is sidebar.history_page
    assert sidebar.navigation_bar.isVisible()
    sidebar.history_back_button.click()
    assert sidebar.tool_pages.isHidden()
    assert sidebar.expanded_panel.isVisible()
