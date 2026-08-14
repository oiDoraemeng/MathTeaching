"""Main-window overlay for direct formula editing with a floating keyboard."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QRect, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QColor
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QVBoxLayout, QWidget


class _InlineFormulaEditorBridge(QObject):
    """Receive formula commits and cancellations from the overlay page."""

    formula_submitted = Signal(str)
    dismiss_requested = Signal()
    content_height_changed = Signal(int)

    @Slot(str)
    def formulaSubmitted(self, latex: str) -> None:
        self.formula_submitted.emit(latex)

    @Slot()
    def dismissed(self) -> None:
        self.dismiss_requested.emit()

    @Slot(int)
    def contentHeightChanged(self, height: int) -> None:
        self.content_height_changed.emit(height)


class InlineFormulaEditorOverlay(QWidget):
    """Edit a formula at its list position while the keyboard floats below."""

    submitted = Signal(str)
    dismissed = Signal()
    content_height_changed = Signal(int)

    _MINIMUM_FORMULA_HEIGHT = 38

    def __init__(self, host: QWidget) -> None:
        super().__init__(host)
        self._host = host
        self._page_ready = False
        self._pending_latex = ""
        self._pending_rect = QRect()
        self._active = False

        self.setObjectName("inlineFormulaEditorOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        self.hide()

        self._bridge = _InlineFormulaEditorBridge(self)
        self._bridge.formula_submitted.connect(self.submitted)
        self._bridge.dismiss_requested.connect(self._dismiss_from_page)
        self._bridge.content_height_changed.connect(self._set_content_height)
        self._channel: QWebChannel | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.web_view = QWebEngineView(self)
        self.web_view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.web_view.page().setBackgroundColor(QColor(0, 0, 0, 0))
        self._channel = QWebChannel(self.web_view.page())
        self._channel.registerObject("bridge", self._bridge)
        self.web_view.page().setWebChannel(self._channel)
        self.web_view.loadFinished.connect(self._on_load_finished)
        self.web_view.setUrl(
            QUrl.fromLocalFile(str(Path(__file__).with_name("inline_formula_overlay.html").resolve()))
        )
        layout.addWidget(self.web_view)

        self._host.installEventFilter(self)

    def open_formula(self, latex: str, rect: QRect) -> None:
        """Show an editor over ``rect`` with its keyboard floating in this overlay."""
        self._pending_latex = latex
        self._pending_rect = QRect(rect)
        self._active = True
        self.setGeometry(self._host.rect())
        self.show()
        self.raise_()
        if self._page_ready:
            self._open_browser_formula()

    def accept_submission(self) -> None:
        """Hide the overlay after the host has successfully rendered an update."""
        self._active = False
        self._hide_overlay()

    def set_formula_rect(self, rect: QRect) -> None:
        """Update the in-place field geometry while an edit session is active."""
        self._pending_rect = QRect(rect)
        if self._active and self._page_ready:
            self._set_formula_rect()

    def dismiss(self) -> None:
        """Cancel editing and hide both the overlay and virtual keyboard."""
        if not self._active and not self.isVisible():
            return
        self._active = False
        self._hide_overlay()
        self.dismissed.emit()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self._host and event.type() in (QEvent.Type.Move, QEvent.Type.Resize):
            self.setGeometry(self._host.rect())
            if self._active and self._page_ready:
                self._set_formula_rect()
        return super().eventFilter(watched, event)

    def _on_load_finished(self, success: bool) -> None:
        self._page_ready = success
        if success and self._active:
            self._open_browser_formula()

    def _open_browser_formula(self) -> None:
        config = {
            "latex": self._pending_latex,
            "left": self._pending_rect.left(),
            "top": self._pending_rect.top(),
            "width": self._pending_rect.width(),
            "height": self._pending_rect.height(),
        }
        self.web_view.page().runJavaScript(
            f"window.pendingInlineFormula = {json.dumps(config)}; "
            "if (window.inlineFormulaEditorReady) "
            "window.inlineFormulaEditor.open(window.pendingInlineFormula);"
        )

    def _set_formula_rect(self) -> None:
        config = {
            "left": self._pending_rect.left(),
            "top": self._pending_rect.top(),
            "width": self._pending_rect.width(),
            "height": self._pending_rect.height(),
        }
        self.web_view.page().runJavaScript(
            f"if (window.inlineFormulaEditorReady) "
            f"window.inlineFormulaEditor.setRect({json.dumps(config)});"
        )

    def _set_content_height(self, height: int) -> None:
        """Resize the edited field, then let the owning row follow it."""
        height = max(self._MINIMUM_FORMULA_HEIGHT, int(height))
        if height == self._pending_rect.height():
            return
        self._pending_rect.setHeight(height)
        if self._active and self._page_ready:
            self._set_formula_rect()
        self.content_height_changed.emit(height)

    def _dismiss_from_page(self) -> None:
        if not self._active:
            return
        self._active = False
        self._hide_overlay()
        self.dismissed.emit()

    def _hide_overlay(self) -> None:
        self.web_view.page().runJavaScript(
            "if (window.inlineFormulaEditorReady) window.inlineFormulaEditor.hideKeyboard();"
        )
        self.hide()
