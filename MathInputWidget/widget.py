"""承载单个 MathLive 公式输入框的 PySide6 控件。"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QTimer, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QHideEvent, QShowEvent
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from .theme_bridge import ThemeBridge


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
    """可复用的 MathLive 编辑器，提供同步的 LaTeX 缓存访问。"""

    latexChanged = Signal(str)
    submitted = Signal(str)
    loadFailed = Signal()
    keyboardHeightChanged = Signal(int)
    keyboardVisibilityChanged = Signal(bool)
    contentHeightChanged = Signal(int)

    _EDITOR_HEIGHT = 56
    _KEYBOARD_MIN_HEIGHT = 286

    def __init__(self, parent: QWidget | None = None, initial_theme: str = "light") -> None:
        super().__init__(parent)
        self._latex = ""
        self._placeholder = ""
        self._page_ready = False
        self._focus_requested = False
        self._keyboard_height = 0
        self._formula_height = self._EDITOR_HEIGHT
        self.web_view: QWebEngineView | None = None
        self._initial_theme = initial_theme
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
        """返回最新的浏览器输入值或程序设置的 LaTeX。"""
        return self._latex

    def set_latex(self, latex: str) -> None:
        """设置 MathLive 内容，并立即更新可读取的缓存值。"""
        self._latex = latex
        if self._page_ready:
            self._set_browser_latex(latex)

    def set_placeholder(self, placeholder: str) -> None:
        """按选定的曲面类型设置合适的 MathLive 占位提示。"""
        self._placeholder = placeholder
        if self._page_ready:
            self._run_javascript(f"window.mathInput.setPlaceholder({json.dumps(placeholder)});")

    def focus_editor(self) -> None:
        """在页面准备完成后聚焦 MathLive 输入框。"""
        if not self.isVisible():
            return
        self._focus_requested = True
        self._ensure_web_view()
        if self._page_ready:
            self._focus_math_field()

    def show_virtual_keyboard(self) -> None:
        """聚焦输入框并显示 MathLive 悬浮虚拟键盘。"""
        self.focus_editor()

    def hide_virtual_keyboard(self) -> None:
        """隐藏虚拟键盘，并将控件恢复为紧凑高度。"""
        self._run_javascript(
            "if (window.mathInputReady) window.mathInput.hideKeyboard();"
        )
        self._set_keyboard_height(0)

    def showEvent(self, event: QShowEvent) -> None:
        """仅在复用编辑器实际可见时创建 Chromium 视图。"""
        super().showEvent(event)
        self._ensure_web_view()
        if self._focus_requested and self._page_ready:
            QTimer.singleShot(0, self._focus_math_field)

    def hideEvent(self, event: QHideEvent) -> None:
        """宿主关闭后不保留游离的 MathLive 虚拟键盘。"""
        self.hide_virtual_keyboard()
        super().hideEvent(event)

    def _on_load_finished(self, success: bool) -> None:
        if self.web_view is not None:
            self._theme_bridge.on_load_finished(success)
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
        """调整原生宿主高度，避免 MathLive 键盘被裁剪。"""
        keyboard_height = max(0, keyboard_height)
        was_visible = self._keyboard_height > 0
        self._keyboard_height = keyboard_height
        self._update_widget_height()
        self.keyboardHeightChanged.emit(keyboard_height)
        if was_visible != (keyboard_height > 0):
            self.keyboardVisibilityChanged.emit(keyboard_height > 0)

    def _set_formula_height(self, formula_height: int) -> None:
        """使用 MathLive 实际渲染高度，而不是固定编辑器高度。"""
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
        """当点击落在输入控件外时收起虚拟键盘。"""
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
        self._theme_bridge = ThemeBridge(self.web_view, self._initial_theme)
        self._theme_bridge.install(self._initial_theme)
        self.web_view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self._channel = QWebChannel(self.web_view.page())
        self._channel.registerObject("bridge", self._bridge)
        self.web_view.page().setWebChannel(self._channel)
        self.web_view.loadFinished.connect(self._on_load_finished)
        self._layout.insertWidget(0, self.web_view)
        self.web_view.setUrl(QUrl.fromLocalFile(str(Path(__file__).with_name("mathlive.html").resolve())))
        return self.web_view

    def set_theme(self, theme: str) -> None:
        self._initial_theme = theme
        if self.web_view is not None:
            self._theme_bridge.set_theme(theme)
