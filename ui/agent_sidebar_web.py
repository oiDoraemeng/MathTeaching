"""Qt host for the local React MathAgent document."""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QUrl, QUrlQuery
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineScript,
    QWebEngineUrlRequestJob,
    QWebEngineUrlScheme,
    QWebEngineUrlSchemeHandler,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QVBoxLayout, QWidget

from .agent_bridge import AgentBridge


class _LocalAssetHandler(QWebEngineUrlSchemeHandler):
    _ALLOWED_NAMES = {"index.html", "manifest.json"}
    _ALLOWED_SUFFIXES = {".js", ".css", ".map", ".svg", ".png", ".woff", ".woff2", ".ttf", ".html", ".json"}
    _MIME_TYPES = {
        ".css": "text/css",
        ".html": "text/html",
        ".js": "text/javascript",
        ".json": "application/json",
        ".map": "application/json",
        ".png": "image/png",
        ".svg": "image/svg+xml",
        ".ttf": "font/ttf",
        ".woff": "font/woff",
        ".woff2": "font/woff2",
    }

    def __init__(self, root: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.root = root.resolve()

    def _resolve(self, url: QUrl) -> Path | None:
        requested = url.path().lstrip("/") or "index.html"
        candidate = (self.root / requested).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError:
            return None
        if not candidate.is_file():
            return None
        if candidate.name not in self._ALLOWED_NAMES and candidate.suffix.lower() not in self._ALLOWED_SUFFIXES:
            return None
        return candidate

    def requestStarted(self, job: QWebEngineUrlRequestJob) -> None:  # noqa: N802
        path = self._resolve(job.requestUrl())
        if path is None:
            job.fail(QWebEngineUrlRequestJob.Error.UrlNotFound)
            return
        try:
            data = QByteArray(path.read_bytes())
        except OSError:
            job.fail(QWebEngineUrlRequestJob.Error.RequestAborted)
            return
        buffer = QBuffer(job)
        buffer.setData(data)
        buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        mime = self._MIME_TYPES.get(path.suffix.lower()) or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        job.reply(mime.encode("ascii"), buffer)


class _LocalPage(QWebEnginePage):
    def acceptNavigationRequest(self, url: QUrl, nav_type: QWebEnginePage.NavigationType, is_main_frame: bool) -> bool:  # noqa: N802
        return url.scheme() == "mathagent"


class AgentSidebarWeb(QWidget):
    """Single WebEngine instance that renders the packaged Agent UI."""

    _THEME_BOOTSTRAP_SOURCE = """(() => {
  const mode = new URLSearchParams(location.search).get(\"theme\");
  if (mode === \"light\" || mode === \"dark\") document.documentElement.dataset.theme = mode;
})();"""

    @staticmethod
    def _validated_theme(theme: str | None) -> str:
        return theme if theme in {"light", "dark"} else "light"

    @classmethod
    def _initial_url(cls, theme: str | None = None) -> QUrl:
        url = QUrl("mathagent://app/index.html")
        query = QUrlQuery()
        query.addQueryItem("theme", cls._validated_theme(theme))
        url.setQuery(query)
        return url

    def __init__(
        self,
        dispatcher: Any,
        *,
        asset_root: str | Path | None = None,
        parent: QWidget | None = None,
        effective_theme: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("agentSidebarWeb")
        self.asset_root = Path(asset_root) if asset_root is not None else Path(__file__).with_name("agent_web") / "dist"
        self.asset_root = self.asset_root.resolve()
        self._active_session_id = ""
        self._effective_theme = self._validated_theme(effective_theme or getattr(self.window(), "effective_theme", None))
        self._document_loaded = False
        self._pending_theme: str | None = None
        self._pending_math_case: dict[str, object] | None = None
        self.bridge = AgentBridge(dispatcher, self)
        self.view = QWebEngineView(self)
        self.page = _LocalPage(self.view)
        self.view.setPage(self.page)
        self.channel = QWebChannel(self.page)
        self.channel.registerObject("qtBridge", self.bridge)
        self.page.setWebChannel(self.channel)
        self._install_theme_bootstrap()
        self._install_scheme_handler()
        self.view.loadFinished.connect(self._request_initial_snapshot)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)
        self.view.setUrl(self._initial_url(self._effective_theme))

    def _install_theme_bootstrap(self) -> None:
        script = QWebEngineScript()
        script.setName("theme-bootstrap")
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
        script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        script.setSourceCode(self._THEME_BOOTSTRAP_SOURCE)
        self.page.scripts().insert(script)

    def set_theme(self, mode: str, *, loaded: bool | None = None) -> None:
        theme = self._validated_theme(mode)
        self._effective_theme = theme
        if loaded is None:
            loaded = self._document_loaded
        if not loaded:
            self._pending_theme = theme
            self.view.setUrl(self._initial_url(theme))
            return
        self._pending_theme = None
        self.bridge.emit_event({
            "protocol_version": 1,
            "type": "theme_state",
            "request_id": "theme-state",
            "session_id": "",
            "payload": {"mode": theme},
        })

    @property
    def active_session_id(self) -> str:
        return self._active_session_id

    def set_active_session(self, session_id: str) -> None:
        self._active_session_id = str(session_id)

    def show_error(self, message: str, *, keep_plan: bool = False) -> None:
        self.bridge.emit_event({"protocol_version": 1, "type": "error", "request_id": "ui", "session_id": "", "payload": {"message": message}})

    def set_model_status(self, model: str, *, enabled: bool) -> None:
        self.bridge.emit_event(
            {
                "protocol_version": 1,
                "type": "model_status",
                "request_id": "model-status",
                "session_id": "",
                "payload": {"model": model, "connected": bool(enabled)},
            }
        )

    def set_busy(self, busy: bool) -> None:
        self.bridge.emit_event(
            {
                "protocol_version": 1,
                "type": "model_status",
                "request_id": "busy-status",
                "session_id": "",
                "payload": {"streaming": bool(busy)},
            }
        )

    def set_scene_mode(self, is_2d: bool) -> None:
        self.bridge.emit_event(
            {
                "protocol_version": 1,
                "type": "scene_context",
                "request_id": "scene-mode",
                "session_id": "",
                "payload": {"scene_mode": "2d" if is_2d else "3d"},
            }
        )

    def show_math_case(
        self,
        case: Any,
        *,
        case_id: str | None = None,
        category: str | None = None,
        scene_mode: str | None = None,
    ) -> None:
        """Publish one bounded, JSON-only teaching case to the Web UI."""
        payload = {
            "case_id": str(case_id or getattr(case, "id", ""))[:128],
            "category": str(category or getattr(case, "category", ""))[:64],
            "name": str(getattr(case, "name", getattr(case, "title", "")))[:128],
            "formula": str(getattr(case, "formula", ""))[:512],
            "steps": [str(step)[:512] for step in tuple(getattr(case, "steps", ()))[:12]],
            "conclusion": str(getattr(case, "conclusion", ""))[:1024],
            "summary": str(getattr(case, "summary", ""))[:512],
            "scene_mode": scene_mode if scene_mode in {"2d", "3d"} else "2d",
        }
        if not self._document_loaded:
            self._pending_math_case = payload
            return
        self._emit_math_case_payload(payload)

    def _emit_math_case_payload(self, payload: dict[str, object]) -> None:
        self.bridge.emit_event(
            {
                "protocol_version": 1,
                "type": "math_case",
                "request_id": f"math-case-{payload['case_id']}",
                "session_id": "",
                "payload": payload,
            }
        )

    def _replay_pending_case(self) -> None:
        if self._pending_math_case is None or not self._document_loaded:
            return
        payload = self._pending_math_case
        self._pending_math_case = None
        self._emit_math_case_payload(payload)

    def _install_scheme_handler(self) -> None:
        scheme = QWebEngineUrlScheme(b"mathagent")
        scheme.setSyntax(QWebEngineUrlScheme.Syntax.HostAndPort)
        scheme.setFlags(
            QWebEngineUrlScheme.Flag.LocalScheme
            | QWebEngineUrlScheme.Flag.LocalAccessAllowed
            | QWebEngineUrlScheme.Flag.SecureScheme
        )
        QWebEngineUrlScheme.registerScheme(scheme)
        handler = _LocalAssetHandler(self.asset_root, QWebEngineProfile.defaultProfile())
        QWebEngineProfile.defaultProfile().installUrlSchemeHandler(b"mathagent", handler)
        self._asset_handler = handler

    def _request_initial_snapshot(self, ok: bool) -> None:
        if not ok:
            return
        self._document_loaded = True
        if self._pending_theme is not None:
            theme = self._pending_theme
            self._pending_theme = None
            self.bridge.emit_event({
                "protocol_version": 1,
                "type": "theme_state",
                "request_id": "theme-state",
                "session_id": "",
                "payload": {"mode": theme},
            })
        self.bridge.send_json(
            '{"protocol_version":1,"type":"request_snapshot","request_id":"webview-boot","session_id":"","payload":{}}'
        )
        self._replay_pending_case()
