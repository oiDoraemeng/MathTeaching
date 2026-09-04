"""用于紧凑 Qt 布局的只读 MathLive 公式预览。"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QColor, QMouseEvent, QShowEvent
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QLabel, QStackedLayout, QWidget
from .theme_bridge import ThemeBridge


class _FormulaPreviewBridge(QObject):
    """接收静态公式预览页发出的编辑请求。"""

    edit_requested = Signal()
    content_height_changed = Signal(int)

    @Slot()
    def editRequested(self) -> None:
        self.edit_requested.emit()

    @Slot(int)
    def contentHeightChanged(self, height: int) -> None:
        self.content_height_changed.emit(height)


class _FormulaPreviewClickTarget(QWidget):
    """覆盖在原生网页预览上方的透明 Qt 点击层。"""

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
    """渲染静态公式，并在点击时请求直接编辑。"""

    edit_requested = Signal()
    content_height_changed = Signal(int)

    _MINIMUM_FORMULA_HEIGHT = 38

    def __init__(self, latex: str = "", parent: QWidget | None = None, initial_theme: str = "light") -> None:
        super().__init__(parent)
        self._latex = latex
        self._page_ready = False
        self._editing_mode = False  # 其他公式处于编辑状态时暂时隐藏当前网页预览。
        self.web_view: QWebEngineView | None = None
        self._theme = initial_theme
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
        self._fallback_label.setStyleSheet("padding-left: 4px;")
        self._layout.addWidget(self._fallback_label)
        self._click_target = _FormulaPreviewClickTarget(self)
        self._click_target.clicked.connect(self._request_edit)
        self._layout.addWidget(self._click_target)
        self.setFixedHeight(self._MINIMUM_FORMULA_HEIGHT)
        self.setToolTip(latex)

    def get_latex(self) -> str:
        """返回当前预览所表示的公式。"""
        return self._latex

    def set_latex(self, latex: str) -> None:
        """更新缓存值；网页就绪后同步更新其展示内容。"""
        self._latex = latex
        self.setToolTip(latex)
        self._fallback_label.setText(latex)
        if self._page_ready:
            self._set_browser_latex(latex)

    def set_editing_mode(self, enabled: bool) -> None:
        """其他公式进行行内编辑时临时隐藏网页预览。"""
        self._editing_mode = enabled
        if self.web_view is not None:
            # 隐藏网页视图但不销毁，结束编辑后无需重新加载和排版公式。
            self.web_view.setVisible(not enabled)

    def showEvent(self, event: QShowEvent) -> None:
        """仅在公式实际显示时加载浏览器视图。"""
        super().showEvent(event)
        self._ensure_web_view()
        self._click_target.raise_()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """点击已渲染公式时请求进入编辑状态。"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._request_edit()
            event.accept()
            return
        super().mousePressEvent(event)

    def _ensure_web_view(self) -> QWebEngineView:
        if self.web_view is not None:
            return self.web_view
        self.web_view = QWebEngineView(self)
        self._theme_bridge = ThemeBridge(self.web_view, self._theme)
        self._theme_bridge.install(self._theme)
        self.web_view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        # 预览仅负责显示，所有点击交给父控件处理，避免原生 WebEngine 命中测试
        # 阻塞即时行内编辑。
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
        """为任意预览实现发出统一的 Qt 编辑请求。"""
        self.edit_requested.emit()

    def _set_content_height(self, height: int) -> None:
        """让原生预览宿主高度匹配 MathLive 的实际公式高度。"""
        height = max(self._MINIMUM_FORMULA_HEIGHT, int(height))
        if height == self.height():
            return
        self.setFixedHeight(height)
        self.content_height_changed.emit(height)

    def _on_load_finished(self, success: bool) -> None:
        if self.web_view is not None:
            self._theme_bridge.on_load_finished(success)
        self._page_ready = success
        if not success or self.web_view is None:
            return
        self._set_browser_latex(self._latex)
        self.web_view.setVisible(True)
        self._fallback_label.setVisible(False)

    def set_theme(self, theme: str) -> None:
        self._theme = theme
        if self.web_view is not None:
            self._theme_bridge.set_theme(theme)

    def _set_browser_latex(self, latex: str) -> None:
        if self.web_view is None:
            return
        value = json.dumps(latex)
        self.web_view.page().runJavaScript(
            f"window.pendingFormulaLatex = {value}; "
            "if (window.formulaPreviewReady) "
            "window.formulaPreview.setLatex(window.pendingFormulaLatex);"
        )
