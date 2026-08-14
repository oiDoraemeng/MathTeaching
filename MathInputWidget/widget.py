"""PySide6 widget that hosts one MathLive formula field."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QTimer, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QHideEvent, QShowEvent
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget


class _FormulaBridge(QObject):
    latex_changed = Signal(str)
    submission_received = Signal(str)
    keyboard_height_changed = Signal(int)
    content_height_changed = Signal(int)

    @Slot(str)
    def latexChanged(self, latex: str) -> None:
        self.latex_changed.emit(latex)

    @Slot(str)
    def submitted(self, latex: str) -> None:
        self.submission_received.emit(latex)

    @Slot(int)
    def virtualKeyboardHeightChanged(self, height: int) -> None:
        self.keyboard_height_changed.emit(max(0, height))

    @Slot(int)
    def contentHeightChanged(self, height: int) -> None:
        self.content_height_changed.emit(max(0, height))


class MathInputWidget(QWidget):
    """A reusable MathLive editor with synchronous cached LaTeX access."""

    latexChanged = Signal(str)
    submitted = Signal(str)
    loadFailed = Signal()
    keyboardHeightChanged = Signal(int)
    keyboardVisibilityChanged = Signal(bool)
    contentHeightChanged = Signal(int)

    _EDITOR_HEIGHT = 56
    _KEYBOARD_MIN_HEIGHT = 286

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._latex = ""
        self._placeholder = ""
        self._page_ready = False
        self._focus_requested = False
        self._keyboard_height = 0
        self._formula_height = self._EDITOR_HEIGHT
        self.web_view: QWebEngineView | None = None
        self._bridge = _FormulaBridge(self)
        self._bridge.latex_changed.connect(self._on_latex_changed)
        self._bridge.submission_received.connect(self._on_submitted)
        self._bridge.keyboard_height_changed.connect(self._set_keyboard_height)
        self._bridge.content_height_changed.connect(self._set_formula_height)
        self._channel: QWebChannel | None = None
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._failure_label = QLabel("数学公式编辑器加载失败", self)
        self._failure_label.setObjectName("mathInputLoadError")
        self._failure_label.setVisible(False)
        self._layout.addWidget(self._failure_label)
        self.setFixedHeight(self._EDITOR_HEIGHT)
        application = QApplication.instance()
        if application is not None:
            application.installEventFilter(self)

    def get_latex(self) -> str:
        """Return the latest browser-originated or programmatically set LaTeX."""
        return self._latex

    def set_latex(self, latex: str) -> None:
        """Set MathLive contents and make the value available immediately."""
        self._latex = latex
        if self._page_ready:
            self._set_browser_latex(latex)

    def set_placeholder(self, placeholder: str) -> None:
        """Set a MathLive placeholder appropriate for the selected surface kind."""
        self._placeholder = placeholder
        if self._page_ready:
            self._run_javascript(f"window.mathInput.setPlaceholder({json.dumps(placeholder)});")

    def focus_editor(self) -> None:
        """Focus the MathLive field once its page is ready."""
        if not self.isVisible():
            return
        self._focus_requested = True
        self._ensure_web_view()
        if self._page_ready:
            self._focus_math_field()

    def show_virtual_keyboard(self) -> None:
        """Focus the field and show MathLive's floating virtual keyboard."""
        self.focus_editor()

    def hide_virtual_keyboard(self) -> None:
        """Hide the keyboard and return this widget to its compact height."""
        self._run_javascript(
            "if (window.mathInputReady) window.mathInput.hideKeyboard();"
        )
        self._set_keyboard_height(0)

    def showEvent(self, event: QShowEvent) -> None:
        """Create the Chromium view only when the reusable editor becomes visible."""
        super().showEvent(event)
        self._ensure_web_view()
        if self._focus_requested and self._page_ready:
            QTimer.singleShot(0, self._focus_math_field)

    def hideEvent(self, event: QHideEvent) -> None:
        """Do not leave an orphaned MathLive keyboard after its host closes."""
        self.hide_virtual_keyboard()
        super().hideEvent(event)

    def _on_load_finished(self, success: bool) -> None:
        self._page_ready = success
        if not success:
            self._failure_label.setVisible(True)
            self.loadFailed.emit()
            return
        self._failure_label.setVisible(False)
        self._set_browser_latex(self._latex)
        self.set_placeholder(self._placeholder)
        if self._focus_requested:
            QTimer.singleShot(0, self._focus_math_field)

    def _on_latex_changed(self, latex: str) -> None:
        self._latex = latex
        self.latexChanged.emit(latex)

    def _on_submitted(self, latex: str) -> None:
        self._latex = latex
        self.submitted.emit(latex)

    def _set_keyboard_height(self, keyboard_height: int) -> None:
        """Resize the native host so MathLive's keyboard is never clipped."""
        keyboard_height = max(0, keyboard_height)
        was_visible = self._keyboard_height > 0
        self._keyboard_height = keyboard_height
        self._update_widget_height()
        self.keyboardHeightChanged.emit(keyboard_height)
        if was_visible != (keyboard_height > 0):
            self.keyboardVisibilityChanged.emit(keyboard_height > 0)

    def _set_formula_height(self, formula_height: int) -> None:
        """Use the rendered MathLive field height instead of a fixed editor size."""
        formula_height = max(self._EDITOR_HEIGHT, int(formula_height))
        if formula_height == self._formula_height:
            return
        self._formula_height = formula_height
        self._update_widget_height()
        self.contentHeightChanged.emit(formula_height)

    def _update_widget_height(self) -> None:
        height = self._formula_height
        if self._keyboard_height:
            height = max(
                self._KEYBOARD_MIN_HEIGHT,
                self._formula_height + self._keyboard_height,
            )
        self.setFixedHeight(height)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Dismiss the keyboard when a click lands outside this input widget."""
        if (
            getattr(self, "_keyboard_height", 0)
            and event.type() == QEvent.Type.MouseButtonPress
            and isinstance(watched, QWidget)
            and watched is not self
            and not self.isAncestorOf(watched)
        ):
            QTimer.singleShot(0, self.hide_virtual_keyboard)
        return super().eventFilter(watched, event)

    def _focus_math_field(self) -> None:
        if not self._page_ready or not self.isVisible():
            return
        self._run_javascript("window.mathInput.focus();")

    def _run_javascript(self, source: str) -> None:
        if self.web_view is not None:
            self.web_view.page().runJavaScript(source)

    def _set_browser_latex(self, latex: str) -> None:
        value = json.dumps(latex)
        self._run_javascript(
            f"window.pendingMathLatex = {value}; "
            "if (window.mathInputReady) window.mathInput.setLatex(window.pendingMathLatex);"
        )

    def _ensure_web_view(self) -> QWebEngineView:
        if self.web_view is not None:
            return self.web_view
        self.web_view = QWebEngineView(self)
        self.web_view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self._channel = QWebChannel(self.web_view.page())
        self._channel.registerObject("bridge", self._bridge)
        self.web_view.page().setWebChannel(self._channel)
        self.web_view.loadFinished.connect(self._on_load_finished)
        self._layout.insertWidget(0, self.web_view)
        self.web_view.setUrl(QUrl.fromLocalFile(str(Path(__file__).with_name("mathlive.html").resolve())))
        return self.web_view
