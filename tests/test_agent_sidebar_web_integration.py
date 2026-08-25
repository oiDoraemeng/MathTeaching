from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from ui.agent_sidebar import AgentSidebar, AgentSidebarState
from ui.agent_sidebar_web import AgentSidebarWeb


def test_sidebar_uses_single_web_host_and_fixed_width() -> None:
    app = QApplication.instance() or QApplication([])
    sidebar = AgentSidebar(dispatcher=lambda _message: None)

    assert sidebar.state == AgentSidebarState.COLLAPSED
    assert not sidebar.isVisible()
    assert isinstance(sidebar.expanded_panel, AgentSidebarWeb)
    assert sidebar.width() == 440

    sidebar.expand()
    assert sidebar.isVisible()
    assert sidebar.expanded_panel.isVisible()
    sidebar.collapse()
    assert not sidebar.isVisible()


def test_tab_projection_does_not_call_scene_dispatcher() -> None:
    app = QApplication.instance() or QApplication([])
    calls: list[object] = []
    sidebar = AgentSidebar(dispatcher=calls.append)

    sidebar.expanded_panel.bridge.send_json(
        '{"protocol_version":1,"type":"request_snapshot","request_id":"r1","session_id":"","payload":{}}'
    )

    assert calls
    assert calls[0].type == "request_snapshot"
