from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

from ui.agent_sidebar_web import AgentSidebarWeb


def test_webview_uses_packaged_local_document_and_restrictive_csp() -> None:
    app = QApplication.instance() or QApplication([])
    host = AgentSidebarWeb(lambda _message: None)
    index = (Path(__file__).parents[1] / "ui" / "agent_web" / "dist" / "index.html").read_text(encoding="utf-8")
    assert host.view.url().scheme() == "mathagent"
    assert host.view.url().path().endswith("/index.html")
    assert "connect-src 'none'" in index
    assert "http" not in index.split("Content-Security-Policy", 1)[-1]
