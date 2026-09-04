"""Theme lifecycle adapter shared by all MathInput WebEngine hosts."""

from __future__ import annotations

import json

from PySide6.QtWebEngineCore import QWebEngineScript
from PySide6.QtWebEngineWidgets import QWebEngineView

from ui.tokens import TokenError

from .theme_tokens import math_input_theme_script


class ThemeBridge:
    def __init__(self, view: QWebEngineView, initial_theme: str = "light") -> None:
        self._view = view
        self._pending_theme = self._validate(initial_theme)
        self._loaded = False

    @staticmethod
    def _validate(theme: str) -> str:
        if theme not in ("light", "dark"):
            raise TokenError(f"unknown theme: {theme}")
        return theme

    def install(self, theme: str) -> None:
        theme = self._validate(theme)
        script = QWebEngineScript()
        script.setName("math3d-math-input-theme")
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        script.setRunsOnSubFrames(False)
        script.setSourceCode(math_input_theme_script(theme))
        self._view.page().scripts().insert(script)
        self._pending_theme = theme

    def set_theme(self, theme: str) -> None:
        theme = self._validate(theme)
        self._pending_theme = theme
        if self._loaded:
            self._view.page().runJavaScript(
                f"document.documentElement.dataset.theme = {json.dumps(theme)};"
            )

    def on_load_finished(self, success: bool) -> None:
        if success:
            self._loaded = True
            self.set_theme(self._pending_theme)
