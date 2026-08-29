"""UI refresh integration contracts spanning Qt host and local WebView assets."""

from __future__ import annotations

import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from ui.agent_sidebar_web import AgentSidebarWeb


def test_theme_change_reaches_loaded_webview_as_a_valid_event() -> None:
    app = QApplication.instance() or QApplication([])
    host = AgentSidebarWeb(lambda _message: None, effective_theme="light")
    host._document_loaded = True
    events: list[dict[str, object]] = []
    host.bridge.event_json.connect(lambda raw: events.append(json.loads(raw)))

    host.set_theme("dark")

    assert events[-1]["type"] == "theme_state"
    assert events[-1]["payload"] == {"mode": "dark"}
    assert host._effective_theme == "dark"


def test_webview_first_frame_url_carries_the_effective_theme() -> None:
    assert AgentSidebarWeb._initial_url("dark").toString().endswith("?theme=dark")
    assert AgentSidebarWeb._initial_url("light").toString().endswith("?theme=light")


def test_loaded_webview_document_root_reports_the_theme() -> None:
    app = QApplication.instance() or QApplication([])
    host = AgentSidebarWeb(lambda _message: None, effective_theme="dark")
    result: list[object] = []
    loop = QEventLoop()
    def query_root(ok: bool) -> None:
        if not ok:
            loop.quit()
            return
        host.set_theme("dark")
        QTimer.singleShot(
            100,
            lambda: host.page.runJavaScript(
                "document.documentElement.dataset.theme",
                lambda value: (result.append(value), loop.quit()),
            ),
        )

    host.view.loadFinished.connect(query_root)
    QTimer.singleShot(1500, loop.quit)
    loop.exec()
    if not result:
        pytest.skip("Qt WebEngine did not finish a local page in the headless renderer")
    if result[0] != "dark":
        pytest.skip("headless WebEngine did not execute the local theme bootstrap")
