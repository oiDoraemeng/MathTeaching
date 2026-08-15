"""带悬浮虚拟键盘的主窗口直接公式编辑遮罩层。"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QRect, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QColor, QMouseEvent
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QWidget


class _InlineFormulaEditorBridge(QObject):
    """接收遮罩网页发出的公式提交和取消请求。"""

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
    """在公式列表原位置编辑，并将虚拟键盘悬浮在下方。"""

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

        # 不使用布局，网页视图由代码定位，避免覆盖编辑行上方的其他
        # FormulaPreviewWidget。Windows 中每个 QWebEngineView 都对应原生 HWND，
        # 一个 HWND 覆盖另一个时，被遮住的视图会变成空白。
        self.web_view = QWebEngineView(self)
        self.web_view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.web_view.setStyleSheet("background: transparent;")
        self.web_view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.web_view.page().setBackgroundColor(QColor(0, 0, 0, 0))
        self._channel = QWebChannel(self.web_view.page())
        self._channel.registerObject("bridge", self._bridge)
        self.web_view.page().setWebChannel(self._channel)
        self.web_view.loadFinished.connect(self._on_load_finished)
        self.web_view.setUrl(
            QUrl.fromLocalFile(str(Path(__file__).with_name("inline_formula_overlay.html").resolve()))
        )

        self._host.installEventFilter(self)

    def open_formula(self, latex: str, rect: QRect) -> None:
        """在 ``rect`` 上显示编辑器，并在遮罩层内悬浮其虚拟键盘。"""
        self._pending_latex = latex
        self._pending_rect = QRect(rect)
        self._active = True
        self.setGeometry(self._host.rect())
        self._reposition_webview()
        self.show()
        self.raise_()
        if self._page_ready:
            self._open_browser_formula()

    def accept_submission(self) -> None:
        """宿主成功渲染更新后隐藏遮罩层。"""
        self._active = False
        self._hide_overlay()

    def set_formula_rect(self, rect: QRect) -> None:
        """在编辑会话进行时更新行内输入框的几何位置。"""
        self._pending_rect = QRect(rect)
        if self._active and self._page_ready:
            self._reposition_webview()
            self._set_formula_rect_js()

    def dismiss(self) -> None:
        """取消编辑，并隐藏遮罩层和虚拟键盘。"""
        if not self._active and not self.isVisible():
            return
        self._active = False
        self._hide_overlay()
        self.dismissed.emit()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """点击网页视图外的透明区域时关闭编辑器。"""
        if self._active and event.button() == Qt.MouseButton.LeftButton:
            self._dismiss_from_page()
            event.accept()
            return
        super().mousePressEvent(event)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        host = getattr(self, "_host", None)
        if host is not None and watched is host and event.type() in (
            QEvent.Type.Move,
            QEvent.Type.Resize,
        ):
            self.setGeometry(self._host.rect())
            if self._active and self._page_ready:
                self._reposition_webview()
                self._set_formula_rect_js()
        return super().eventFilter(watched, event)

    def _reposition_webview(self) -> None:
        """将网页视图放在公式上边缘到遮罩层底部的区域内。"""
        top = self._pending_rect.top()
        self.web_view.setGeometry(0, top, self.width(), self.height() - top)

    def _on_load_finished(self, success: bool) -> None:
        self._page_ready = success
        if success and self._active:
            self._open_browser_formula()

    def _open_browser_formula(self) -> None:
        self._reposition_webview()
        config = {
            "latex": self._pending_latex,
            "left": self._pending_rect.left(),
            "top": 0,
            "width": self._pending_rect.width(),
            "height": self._pending_rect.height(),
        }
        self.web_view.page().runJavaScript(
            f"window.pendingInlineFormula = {json.dumps(config)}; "
            "if (window.inlineFormulaEditorReady) "
            "window.inlineFormulaEditor.open(window.pendingInlineFormula);"
        )

    def _set_formula_rect_js(self) -> None:
        config = {
            "left": self._pending_rect.left(),
            "top": 0,
            "width": self._pending_rect.width(),
            "height": self._pending_rect.height(),
        }
        self.web_view.page().runJavaScript(
            f"if (window.inlineFormulaEditorReady) "
            f"window.inlineFormulaEditor.setRect({json.dumps(config)});"
        )

    def _set_content_height(self, height: int) -> None:
        """调整编辑框高度，再通知所属行同步其高度。"""
        height = max(self._MINIMUM_FORMULA_HEIGHT, int(height))
        if height == self._pending_rect.height():
            return
        self._pending_rect.setHeight(height)
        if self._active and self._page_ready:
            self._reposition_webview()
            self._set_formula_rect_js()
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
