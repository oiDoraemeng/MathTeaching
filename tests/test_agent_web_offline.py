from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

from ui.agent_sidebar_web import AgentSidebarWeb, _LocalAssetHandler


def test_webview_uses_packaged_local_document_and_restrictive_csp() -> None:
    app = QApplication.instance() or QApplication([])
    host = AgentSidebarWeb(lambda _message: None)
    index = (Path(__file__).parents[1] / "ui" / "agent_web" / "dist" / "index.html").read_text(encoding="utf-8")
    assert host.view.url().scheme() == "mathagent"
    assert host.view.url().path().endswith("/index.html")
    assert "connect-src 'none'" in index
    assert "qrc:///qtwebchannel/qwebchannel.js" in index
    assert "font-src 'self' mathagent://app data:" in index
    assert "http" not in index.split("Content-Security-Policy", 1)[-1]


def test_local_assets_use_browser_mime_types_for_module_loading() -> None:
    assert _LocalAssetHandler._MIME_TYPES[".js"] == "text/javascript"
    assert _LocalAssetHandler._MIME_TYPES[".css"] == "text/css"
    assert _LocalAssetHandler._MIME_TYPES[".woff2"] == "font/woff2"


def test_web_layout_allows_sidebar_children_to_shrink_to_webview_width() -> None:
    styles = (Path(__file__).parents[1] / "ui" / "agent_web" / "src" / "styles" / "layout.css").read_text(encoding="utf-8")
    assert ".agent-app > * { min-width: 0; }" in styles
    assert ".model-selector { width: 62px; }" in styles
