from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication

from ui.agent_sidebar_web import _LocalAssetHandler, _LocalPage


def test_asset_handler_rejects_traversal_and_unknown_files(tmp_path: Path) -> None:
    root = tmp_path / "dist"
    root.mkdir()
    (root / "index.html").write_text("ok", encoding="utf-8")
    handler = _LocalAssetHandler(root)

    assert handler._resolve(QUrl("mathagent://app/index.html")) == root / "index.html"
    assert handler._resolve(QUrl("mathagent://app/../secret.txt")) is None
    assert handler._resolve(QUrl("mathagent://app/secret.exe")) is None


def test_page_rejects_non_local_navigation() -> None:
    app = QApplication.instance() or QApplication([])
    page = _LocalPage()

    assert page.acceptNavigationRequest(QUrl("mathagent://app/index.html"), page.NavigationType.NavigationTypeLinkClicked, True)
    assert not page.acceptNavigationRequest(QUrl("https://example.com"), page.NavigationType.NavigationTypeLinkClicked, True)
    assert not page.acceptNavigationRequest(QUrl("file:///tmp/secret"), page.NavigationType.NavigationTypeLinkClicked, True)
