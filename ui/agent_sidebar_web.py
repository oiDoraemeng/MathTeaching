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

from linear_algebra.visualizations.palette import ROLE_COLORS, role_color

from .agent_bridge import AgentBridge


def register_mathagent_url_scheme() -> None:
    """Register the local asset scheme before QApplication is constructed."""
    if QWebEngineUrlScheme.schemeByName(b"mathagent").name():
        return
    scheme = QWebEngineUrlScheme(b"mathagent")
    scheme.setSyntax(QWebEngineUrlScheme.Syntax.Host)
    scheme.setFlags(
        QWebEngineUrlScheme.Flag.LocalScheme
        | QWebEngineUrlScheme.Flag.LocalAccessAllowed
        | QWebEngineUrlScheme.Flag.SecureScheme
    )
    QWebEngineUrlScheme.registerScheme(scheme)


register_mathagent_url_scheme()


def _json_value(value: Any) -> object:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return str(value)


def _worked_example_payload(example: Any) -> dict[str, object]:
    return {
        "id": str(getattr(example, "id", ""))[:128],
        "title": str(getattr(example, "title", ""))[:256],
        "kind": str(getattr(example, "kind", ""))[:64],
        "given": _json_value(getattr(example, "given", None)),
        "calculation": [str(value)[:1024] for value in tuple(getattr(example, "calculation", ()))[:16]],
        "result": _json_value(getattr(example, "result", None)),
        "checks": [
            {
                "name": str(getattr(check, "name", ""))[:128],
                "expected": _json_value(getattr(check, "expected", None)),
                "tolerance": getattr(check, "tolerance", None),
            }
            for check in tuple(getattr(example, "checks", ()))[:12]
        ],
        "claim_refs": list(tuple(getattr(example, "claim_refs", ()))[:12]),
    }


def _claim_payload(claim: Any) -> dict[str, object]:
    return {
        "id": str(getattr(claim, "id", ""))[:128],
        "statement": str(getattr(claim, "statement", ""))[:1024],
        "formula": str(getattr(claim, "formula", ""))[:512],
        "formula_symbols": list(tuple(getattr(claim, "formula_symbols", ()))[:32]),
        "entity_refs": list(tuple(getattr(claim, "entity_refs", ()))[:32]),
        "relation_refs": list(tuple(getattr(claim, "relation_refs", ()))[:32]),
        "stage_refs": list(tuple(getattr(claim, "stage_refs", ()))[:32]),
    }


def _source_diagnostic_payload(diagnostic: object) -> dict[str, object] | None:
    """Expose the bounded source check without leaking loader internals."""

    if not isinstance(diagnostic, (tuple, list)) or len(diagnostic) != 3:
        return None
    code, published_hash, current_hash = diagnostic
    return {
        "code": str(code)[:64],
        "published_hash": str(published_hash)[:256],
        "current_hash": str(current_hash)[:256],
    }


def _source_payload(case: Any, diagnostic: object = None) -> dict[str, object]:
    source = getattr(case, "source", None)
    source_path = tuple(getattr(source, "source_path", ()))
    heading_path = tuple(getattr(source, "heading_path", ()))
    source_hash = getattr(source, "source_hash", None)
    return {
        "source_path": [str(value)[:512] for value in source_path[:8]],
        "heading_path": [str(value)[:512] for value in heading_path[:8]],
        "heading_level": getattr(source, "heading_level", None),
        "occurrence": getattr(source, "occurrence", None),
        "source_hash": str(source_hash)[:256] if source_hash is not None else None,
        "diagnostic": _source_diagnostic_payload(diagnostic),
    }


def _storyboard_payload(stage: Any) -> dict[str, object]:
    anchor = tuple(getattr(stage, "anchor", ()))
    return {
        "id": str(getattr(stage, "id", ""))[:128],
        "title": str(getattr(stage, "title", ""))[:256],
        "caption": str(getattr(stage, "caption", ""))[:1024],
        "layout": str(getattr(stage, "layout", ""))[:32],
        "visible_refs": list(tuple(getattr(stage, "visible_refs", ()))[:64]),
        "visible_aliases": list(tuple(getattr(stage, "visible_aliases", ()))[:64]),
        "anchor": list(anchor[:3]),
    }


def _case_layout_payload(layout: Any) -> dict[str, object] | None:
    if layout is None:
        return None
    cases = []
    for case in tuple(getattr(layout, "cases", ())[:4]):
        cases.append({
            "id": str(getattr(case, "id", ""))[:128],
            "topic_id": str(getattr(case, "topic_id", ""))[:128],
            "example_ref": str(getattr(case, "example_ref", ""))[:128],
            "claim_refs": list(tuple(getattr(case, "claim_refs", ()))[:8]),
            "stage_refs": list(tuple(getattr(case, "stage_refs", ()))[:8]),
            "purpose": str(getattr(case, "purpose", ""))[:512],
        })
    return {"default_pane_count": int(getattr(layout, "default_pane_count", 1)), "cases": cases}


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
  if (mode !== \"light\" && mode !== \"dark\") return;
  const apply = () => {
    const root = document.documentElement;
    if (!root) return false;
    root.dataset.theme = mode;
    return true;
  };
  if (!apply()) {
    const observer = new MutationObserver(() => {
      if (apply()) observer.disconnect();
    });
    observer.observe(document, { childList: true });
  }
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

    def showEvent(self, event) -> None:
        """强制 WebEngine 在窗口显示时重绘，修复最小化后空白问题。"""
        super().showEvent(event)
        if hasattr(self, "view") and self.view is not None:
            # 触发 WebEngine 重新渲染，不使用 Reload 避免丢失状态
            self.view.update()

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
        compiled: Any | None = None,
        source_diagnostic: object = None,
    ) -> None:
        """Publish one bounded, JSON-only teaching case to the Web UI."""
        explanation = getattr(case, "explanation", case)
        claims = tuple(getattr(case, "claims", ()))
        section_text = {
            str(getattr(section, "id", "")): str(getattr(section, "text", ""))
            for section in tuple(getattr(explanation, "sections", ()))
        }
        formula_text = str(getattr(explanation, "formula", "")) or section_text.get("formula", "")
        derivation_values = tuple(getattr(explanation, "derivation", ())) or ((section_text["derivation"],) if section_text.get("derivation") else ())
        conclusion_text = str(getattr(explanation, "conclusion", "")) or section_text.get("conclusion", "")
        structured = {
            "definition": str(getattr(explanation, "definition", ""))[:2048],
            "derivation": [str(step)[:1024] for step in derivation_values[:16]],
            "intuition": str(getattr(explanation, "intuition", ""))[:2048],
            "geometric_meaning": str(getattr(explanation, "geometric_meaning", ""))[:2048],
            "pitfalls": [str(value)[:512] for value in tuple(getattr(explanation, "pitfalls", ()))[:12]],
            "invariants": [str(value)[:512] for value in tuple(getattr(explanation, "invariants", ()))[:12]],
            "connections": [str(value)[:512] for value in tuple(getattr(explanation, "connections", ()))[:12]],
            "analogy_boundary": str(getattr(explanation, "analogy_boundary", ""))[:1024],
            "transfer_note": str(getattr(explanation, "transfer_note", ""))[:1024],
            "read_guide": [str(value)[:512] for value in tuple(getattr(explanation, "read_guide", ()))[:12]],
            "symbol_roles": dict(getattr(explanation, "symbol_roles", {})),
            "symbol_palette": {
                str(symbol): role_color(str(role))
                for symbol, role in dict(getattr(explanation, "symbol_roles", {})).items()
            },
            "worked_examples": [_worked_example_payload(example) for example in tuple(getattr(explanation, "worked_examples", ()))[:8]],
            "case_layout": _case_layout_payload(getattr(explanation, "case_layout", None)),
        }
        topic_id = str(case_id or getattr(case, "topic_id", getattr(case, "id", "")))[:128]
        source = _source_payload(case, source_diagnostic)
        # This public envelope is intentionally semantic-only. Compiled plans
        # and renderer objects never cross the explanation boundary.
        explanation_payload = {
            "claims": [_claim_payload(claim) for claim in claims[:24]],
            "formula": formula_text[:512],
            "derivation": [str(step)[:1024] for step in derivation_values[:16]],
            "numeric_example": structured["worked_examples"],
            "symbol_roles": dict(getattr(explanation, "symbol_roles", {})),
            "geometric_meaning": structured["geometric_meaning"],
            "misconception": structured["pitfalls"],
            "read_guide": structured["read_guide"],
            "analogy_boundary": structured["analogy_boundary"],
            "definition": structured["definition"],
            "conclusion": conclusion_text[:1024],
        }
        payload = {
            "case_id": topic_id,
            "topic_id": topic_id,
            "category": str(category or getattr(case, "category", ""))[:64],
            "name": str(getattr(explanation, "title", getattr(case, "name", "")))[:128],
            "formula": formula_text[:512] or str(getattr(case, "formula", ""))[:512],
            "steps": [str(step)[:512] for step in derivation_values[:12]] or [str(step)[:512] for step in tuple(getattr(case, "steps", ()))[:12]],
            "conclusion": conclusion_text[:1024] or str(getattr(case, "conclusion", ""))[:1024],
            "summary": str(getattr(explanation, "summary", getattr(case, "summary", "")))[:512],
            # Keep the lecture excerpt available to the document renderer.  It
            # is source-grounded prose, not a renderer instruction, and lets
            # the reader see the definitions, derivations and examples that
            # motivated the bounded artifact.
            "source_excerpt": str(getattr(getattr(case, "source", None), "excerpt", ""))[:20000],
            "scene_mode": scene_mode if scene_mode in {"2d", "3d"} else "2d",
            "artifact_revision": getattr(case, "revision", None),
            "revision": getattr(case, "revision", None),
            "source_hash": source["source_hash"],
            "source": source,
            "source_diagnostic": source["diagnostic"],
            "claims": [_claim_payload(claim) for claim in claims[:24]],
            "palette": dict(ROLE_COLORS),
            "storyboard": [_storyboard_payload(stage) for stage in tuple(getattr(compiled, "storyboard", ()))[:24]],
            "plan_digest": getattr(compiled, "plan_digest", None),
            "compiler_version": getattr(compiled, "compiler_version", None),
        }
        payload.update(structured)
        payload["explanation"] = explanation_payload
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

    def show_math_case_focus(self, case_id: str, pane_id: str) -> None:
        """Synchronize the native case-pane focus without touching Agent sessions."""
        self.bridge.emit_event(
            {
                "protocol_version": 1,
                "type": "math_case_focus",
                "request_id": f"math-case-focus-{case_id}-{pane_id}",
                "session_id": "",
                "payload": {"case_id": str(case_id)[:128], "pane_id": str(pane_id)[:128]},
            }
        )

    def _replay_pending_case(self) -> None:
        if self._pending_math_case is None or not self._document_loaded:
            return
        payload = self._pending_math_case
        self._pending_math_case = None
        self._emit_math_case_payload(payload)

    def _install_scheme_handler(self) -> None:
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
