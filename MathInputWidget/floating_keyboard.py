"""Wide floating MathLive keyboard for inline algebra-list editing."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QColor, QResizeEvent
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QWidget

from .theme_bridge import ThemeBridge


class _FloatingMathKeyboardBridge(QObject):
    """Forward proxy-field changes and keyboard geometry from the web page."""

    edit_state_changed = Signal(str, int)
    keyboard_height_changed = Signal(int)
    close_requested = Signal()

    @Slot(str, int)
    def editStateChanged(self, latex: str, position: int) -> None:
        self.edit_state_changed.emit(latex, int(position))

    @Slot(int)
    def keyboardHeightChanged(self, height: int) -> None:
        self.keyboard_height_changed.emit(max(0, int(height)))

    @Slot()
    def closeRequested(self) -> None:
        self.close_requested.emit()


class FloatingMathKeyboard(QWidget):
    """Show only a wide virtual keyboard while the real field stays inline."""

    edit_state_changed = Signal(str, int)
    dismissed = Signal()
    focus_lost = Signal()

    MINIMUM_WIDTH = 720
    PREFERRED_WIDTH = 880
    MAXIMUM_WIDTH = 1040
    DEFAULT_HEIGHT = 300
    MINIMUM_HEIGHT = 220
    MAXIMUM_HEIGHT = 420
    OUTER_MARGIN = 16

    def __init__(self, host: QWidget, initial_theme: str = "light") -> None:
        super().__init__(host)
        self._host = host
        self._page_ready = False
        self._active = False
        self._pending_latex = ""
        self._pending_position = 0
        self._keyboard_height = self.DEFAULT_HEIGHT
        self._anchor_widget: QWidget | None = None

        self.setObjectName("floatingMathKeyboard")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        self.hide()

        self.web_view = QWebEngineView(self)
        self.web_view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.web_view.installEventFilter(self)
        self.web_view.setStyleSheet("background: transparent;")
        self.web_view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.web_view.page().setBackgroundColor(QColor(0, 0, 0, 0))

        self._theme_bridge = ThemeBridge(self.web_view, initial_theme)
        self._theme_bridge.install(initial_theme)
        self._bridge = _FloatingMathKeyboardBridge(self)
        self._channel = QWebChannel(self.web_view.page())
        self._channel.registerObject("bridge", self._bridge)
        self.web_view.page().setWebChannel(self._channel)
        self.web_view.loadFinished.connect(self._on_load_finished)
        self.web_view.setUrl(
            QUrl.fromLocalFile(
                str(Path(__file__).with_name("floating_math_keyboard.html").resolve())
            )
        )

        self._bridge.edit_state_changed.connect(self.edit_state_changed)
        self._bridge.keyboard_height_changed.connect(self._set_keyboard_height)
        self._bridge.close_requested.connect(self._dismiss_from_page)
        self._host.installEventFilter(self)

    def open_keyboard(self, latex: str, position: int = -1) -> None:
        """Open the keyboard without drawing another visible formula field."""
        self._pending_latex = str(latex)
        self._pending_position = max(0, int(position)) if position >= 0 else len(latex)
        self._active = True
        self._reposition()
        self.show()
        self.raise_()
        if self._page_ready:
            self._open_browser_keyboard()

    def set_anchor_widget(self, widget: QWidget | None) -> None:
        """Keep the floating keyboard to the right of the algebra panel."""
        if widget is self._anchor_widget:
            return
        if self._anchor_widget is not None:
            self._anchor_widget.removeEventFilter(self)
        self._anchor_widget = widget
        if widget is not None:
            widget.installEventFilter(self)
        if self._active:
            self._reposition()

    def sync_state(self, latex: str, position: int) -> None:
        """Mirror edits made directly in the visible algebra-list field."""
        self._pending_latex = str(latex)
        self._pending_position = max(0, int(position))
        if not self._page_ready:
            return
        self.web_view.page().runJavaScript(
            "if (window.floatingMathKeyboardReady) "
            f"window.floatingMathKeyboard.syncState({json.dumps(self._pending_latex)}, "
            f"{self._pending_position});"
        )

    def dismiss(self) -> None:
        """Hide the keyboard while leaving the algebra-list edit session alone."""
        self._active = False
        if self._page_ready:
            self.web_view.page().runJavaScript(
                "if (window.floatingMathKeyboardReady) "
                "window.floatingMathKeyboard.hide();"
            )
        self.hide()

    def set_theme(self, theme: str) -> None:
        self._theme_bridge.set_theme(theme)

    def has_focus_inside(self) -> bool:
        """Return whether Qt focus is currently inside the keyboard WebView."""
        focused = QApplication.focusWidget()
        return bool(
            focused is self
            or focused is self.web_view
            or (focused is not None and self.web_view.isAncestorOf(focused))
        )

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.web_view and event.type() == QEvent.Type.FocusOut:
            self.focus_lost.emit()
            return super().eventFilter(watched, event)
        if watched is self._host or watched is self._anchor_widget:
            if event.type() in (QEvent.Type.Resize, QEvent.Type.Move) and self._active:
                self._reposition()
            elif watched is self._host and event.type() in (QEvent.Type.Hide, QEvent.Type.Close):
                self.dismiss()
        return super().eventFilter(watched, event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.web_view.setGeometry(self.rect())

    def _on_load_finished(self, success: bool) -> None:
        self._theme_bridge.on_load_finished(success)
        self._page_ready = bool(success)
        if success and self._active:
            self._open_browser_keyboard()

    def _open_browser_keyboard(self) -> None:
        self.web_view.page().runJavaScript(
            f"window.pendingFloatingMathKeyboard = {{latex: {json.dumps(self._pending_latex)}, "
            f"position: {self._pending_position}}}; "
            "if (window.floatingMathKeyboardReady) "
            "window.floatingMathKeyboard.open(window.pendingFloatingMathKeyboard);"
        )

    def _set_keyboard_height(self, height: int) -> None:
        if height <= 0:
            return
        next_height = max(self.MINIMUM_HEIGHT, min(self.MAXIMUM_HEIGHT, int(height)))
        if next_height == self._keyboard_height:
            return
        self._keyboard_height = next_height
        if self._active:
            self._reposition()

    def _reposition(self) -> None:
        anchor_left = self.OUTER_MARGIN
        if self._anchor_widget is not None:
            anchor_left = max(
                anchor_left,
                self._anchor_widget.mapTo(self._host, QPoint(0, 0)).x(),
            )
        available_width = max(0, self._host.width() - anchor_left - self.OUTER_MARGIN)
        responsive_width = round(self._host.width() * 0.72)
        target_width = max(
            self.MINIMUM_WIDTH,
            min(self.MAXIMUM_WIDTH, max(self.PREFERRED_WIDTH, responsive_width)),
        )
        # Prefer the full keyboard width.  If a very narrow layout cannot fit it,
        # shrink only to the actual remaining space instead of covering algebra.
        width = min(available_width, target_width) if available_width else target_width
        height = min(
            self._keyboard_height,
            max(self.MINIMUM_HEIGHT, self._host.height() - 2 * self.OUTER_MARGIN),
        )
        centered_left = (self._host.width() - width) // 2
        left = max(anchor_left, centered_left)
        top = max(0, self._host.height() - height - self.OUTER_MARGIN)
        self.setGeometry(QRect(left, top, width, height))
        self.web_view.setGeometry(self.rect())

    def _dismiss_from_page(self) -> None:
        if not self._active:
            return
        self.dismiss()
        self.dismissed.emit()
