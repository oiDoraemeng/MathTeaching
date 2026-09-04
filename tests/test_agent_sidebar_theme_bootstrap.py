from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QSettings
from PySide6.QtWebEngineCore import QWebEngineScript
from PySide6.QtWidgets import QApplication

from ui.agent_sidebar_web import AgentSidebarWeb


def test_initial_url_validates_theme_and_preserves_local_app_url() -> None:
    assert AgentSidebarWeb._initial_url("dark").toString() == "mathagent://app/index.html?theme=dark"
    assert AgentSidebarWeb._initial_url("invalid").toString() == "mathagent://app/index.html?theme=light"
    assert AgentSidebarWeb._initial_url(None).toString() == "mathagent://app/index.html?theme=light"


def test_theme_bootstrap_script_is_document_creation_and_reads_location_theme() -> None:
    app = QApplication.instance() or QApplication([])
    host = AgentSidebarWeb(lambda _message: None)
    scripts = [script for script in host.page.scripts().toList() if script.name() == "theme-bootstrap"]

    assert len(scripts) == 1
    script = scripts[0]
    assert script.injectionPoint() == QWebEngineScript.InjectionPoint.DocumentCreation
    assert script.worldId() == QWebEngineScript.ScriptWorldId.MainWorld
    assert "new URLSearchParams(location.search).get(\"theme\")" in script.sourceCode()
    assert "root.dataset.theme = mode" in script.sourceCode()
    assert "if (!root) return false" in script.sourceCode()
    assert "MutationObserver" in script.sourceCode()


def test_theme_bootstrap_uses_loaded_theme_when_initializing() -> None:
    app = QApplication.instance() or QApplication([])
    host = AgentSidebarWeb(lambda _message: None, effective_theme="dark")
    assert host.view.url().toString() == "mathagent://app/index.html?theme=dark"


def test_theme_bootstrap_updates_initial_url_before_load() -> None:
    app = QApplication.instance() or QApplication([])
    host = AgentSidebarWeb(lambda _message: None, effective_theme="light")
    host._document_loaded = False

    host.set_theme("dark", loaded=False)

    assert host.view.url().toString() == "mathagent://app/index.html?theme=dark"


def test_theme_bootstrap_settings_are_independent() -> None:
    app = QApplication.instance() or QApplication([])
    settings = QSettings("Math3DTeachingTests", "AgentSidebarThemeBootstrap")
    settings.clear()
    settings.setValue("ui/theme", "dark")
    assert settings.value("ui/theme") == "dark"
