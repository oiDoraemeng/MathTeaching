"""Read-only MathLive formula preview for compact Qt layouts."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QColor, QMouseEvent, QShowEvent
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QLabel, QStackedLayout, QWidget


class _FormulaPreviewBridge(QObject):
    """Receive edit requests from the static formula preview."""

    edit_requested = Signal()
    content_height_changed = Signal(int)

    @Slot()
    def editRequested(self) -> None:
        self.edit_requested.emit()

    @Slot(int)
    def contentHeightChanged(self, height: int) -> None:
        self.content_height_changed.emit(height)


class _FormulaPreviewClickTarget(QWidget):
    """Transparent Qt click layer kept above the native web preview."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.IBeamCursor)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class FormulaPreviewWidget(QWidget):
    """Render a static formula and request direct editing on click."""

    edit_requested = Signal()
    content_height_changed = Signal(int)

    _MINIMUM_FORMULA_HEIGHT = 38

    def __init__(self, latex: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._latex = latex
        self._page_ready = False
        self.web_view: QWebEngineView | None = None
        self._bridge = _FormulaPreviewBridge(self)
        self._bridge.edit_requested.connect(self.edit_requested)
        self._bridge.content_height_changed.connect(self._set_content_height)
        self._channel: QWebChannel | None = None

        self._layout = QStackedLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setStackingMode(QStackedLayout.StackingMode.StackAll)
        self._fallback_label = QLabel(latex, self)
        self._fallback_label.setObjectName("formulaPreviewFallback")
        self._fallback_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._fallback_label.setStyleSheet("padding-left: 4px; color: #1f2937;")
        self._layout.addWidget(self._fallback_label)
        self._click_target = _FormulaPreviewClickTarget(self)
        self._click_target.clicked.connect(self._request_edit)
        self._layout.addWidget(self._click_target)
        self.setFixedHeight(self._MINIMUM_FORMULA_HEIGHT)
        self.setToolTip(latex)

    def get_latex(self) -> str:
        """Return the formula currently represented by the preview."""
        return self._latex

    def set_latex(self, latex: str) -> None:
        """Update the cached value and its browser representation when ready."""
        self._latex = latex
        self.setToolTip(latex)
        self._fallback_label.setText(latex)
        if self._page_ready:
            self._set_browser_latex(latex)

    def showEvent(self, event: QShowEvent) -> None:
        """Load the browser only for formulas that are actually shown."""
        super().showEvent(event)
        self._ensure_web_view()
        self._click_target.raise_()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Request editing when the rendered formula is clicked."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._request_edit()
            event.accept()
            return
        super().mousePressEvent(event)

    def _ensure_web_view(self) -> QWebEngineView:
        if self.web_view is not None:
            return self.web_view
        self.web_view = QWebEngineView(self)
        self.web_view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        # The preview is display-only. Let its parent receive every click so
        # native WebEngine hit testing cannot block immediate in-place editing.
        self.web_view.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.web_view.setVisible(False)
        self.web_view.page().setBackgroundColor(QColor(0, 0, 0, 0))
        self._channel = QWebChannel(self.web_view.page())
        self._channel.registerObject("bridge", self._bridge)
        self.web_view.page().setWebChannel(self._channel)
        self.web_view.loadFinished.connect(self._on_load_finished)
        self._layout.insertWidget(0, self.web_view)
        self._click_target.raise_()
        self.web_view.setUrl(
            QUrl.fromLocalFile(str(Path(__file__).with_name("formula_preview.html").resolve()))
        )
        return self.web_view

    def _request_edit(self) -> None:
        """Emit one Qt-side edit request for either preview implementation."""
        self.edit_requested.emit()

    def _set_content_height(self, height: int) -> None:
        """Match the native preview host to MathLive's rendered formula."""
        height = max(self._MINIMUM_FORMULA_HEIGHT, int(height))
        if height == self.height():
            return
        self.setFixedHeight(height)
        self.content_height_changed.emit(height)

    def _on_load_finished(self, success: bool) -> None:
        self._page_ready = success
        if not success or self.web_view is None:
            return
        self._set_browser_latex(self._latex)
        self.web_view.setVisible(True)
        self._fallback_label.setVisible(False)

    def _set_browser_latex(self, latex: str) -> None:
        if self.web_view is None:
            return
        value = json.dumps(latex)
        self.web_view.page().runJavaScript(
            f"window.pendingFormulaLatex = {value}; "
            "if (window.formulaPreviewReady) "
            "window.formulaPreview.setLatex(window.pendingFormulaLatex);"
        )
