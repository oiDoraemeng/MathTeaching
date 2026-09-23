from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from ui.agent_sidebar import AgentSidebar, AgentSidebarState
from ui.designer_window import MainWindow


def test_sidebar_is_hidden_without_a_collapsed_layout_slot() -> None:
    app = QApplication.instance() or QApplication([])
    sidebar = AgentSidebar()

    assert sidebar.state == AgentSidebarState.COLLAPSED
    assert not sidebar.isVisible()
    assert not hasattr(sidebar, "collapsed_bar")


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


def test_agent_panel_toggle_shows_and_hides_its_resize_handle() -> None:
    window = object.__new__(MainWindow)
    window.scene_settings_panel = type("Panel", (), {"isVisible": lambda self: False})()
    states: list[bool] = []
    window.title_bar = type("TitleBar", (), {"set_right_panel_expanded": lambda self, expanded: states.append(expanded)})()
    window.agent_sidebar = AgentSidebar()
    window.agent_resize_handle = type("Handle", (), {"visible": False, "show": lambda self: setattr(self, "visible", True), "hide": lambda self: setattr(self, "visible", False)})()
    window._root_layout = type("Layout", (), {"activate": lambda self: None})()
    window.agent_panel = type("AgentPanel", (), {"view": type("View", (), {"setFocus": lambda self: None})()})()

    MainWindow._open_agent_panel(window)
    assert window.agent_resize_handle.visible
    MainWindow._close_agent_panel(window)
    assert not window.agent_resize_handle.visible
    assert states == [True, False]
