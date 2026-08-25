from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from ui.agent_sidebar import AgentSidebar, AgentSidebarState


def test_sidebar_is_hidden_without_a_collapsed_layout_slot() -> None:
    app = QApplication.instance() or QApplication([])
    sidebar = AgentSidebar()

    assert sidebar.state == AgentSidebarState.COLLAPSED
    assert not sidebar.isVisible()
    assert sidebar.layout().indexOf(sidebar.collapsed_bar) == -1


def test_open_sidebar_has_fixed_width_and_close_hides_it() -> None:
    app = QApplication.instance() or QApplication([])
    sidebar = AgentSidebar()

    sidebar.expand()
    assert sidebar.state == AgentSidebarState.EXPANDED
    assert sidebar.isVisible()
    assert sidebar.width() == 440

    sidebar.collapse()
    assert sidebar.state == AgentSidebarState.COLLAPSED
    assert not sidebar.isVisible()
