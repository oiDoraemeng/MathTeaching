"""可复用的非模态 MathLive 公式编辑弹窗。"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QPoint, QTimer, Qt, Signal
from PySide6.QtGui import QCloseEvent, QGuiApplication
from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout, QWidget

from ui.tokens import apply_rounded_overlay

from .widget import MathInputWidget


class FormulaEditorPopup(QDialog):
    """焦点离开时丢弃未提交内容的悬浮公式编辑器。"""

    submitted = Signal(str, str)
    dismissed = Signal()

    _MINIMUM_WIDTH = 560
    _MINIMUM_HEIGHT = 420

    def __init__(self, parent: QWidget | None = None, initial_theme: str = "light") -> None:
        super().__init__(parent)
        self._anchor: QPoint | None = None
        self._kind = "explicit"
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(16)
        self._resize_timer.timeout.connect(self._apply_pending_resize)
        self.setObjectName("formulaEditorPopup")
        self.setWindowTitle("编辑公式")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        apply_rounded_overlay(self, "lg")
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setMinimumSize(self._MINIMUM_WIDTH, self._MINIMUM_HEIGHT)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(0)
        self.editor = MathInputWidget(self, initial_theme=initial_theme)
        layout.addWidget(self.editor)

        self.editor.submitted.connect(self._submit)
        self.editor.keyboardHeightChanged.connect(self._resize_for_keyboard)
        self.editor.contentHeightChanged.connect(self._resize_for_keyboard)
        application = QApplication.instance()
        if application is not None:
            application.installEventFilter(self)

    def open_formula(
        self,
        latex: str,
        kind: str,
        placeholder: str,
        anchor: QPoint | None = None,
    ) -> None:
        """使用缓存公式打开编辑器，此时不提交修改。"""
        self._anchor = anchor
        self._kind = kind
        self.editor.set_placeholder(placeholder)
        self.editor.set_latex(latex)
        self.setMinimumSize(self._MINIMUM_WIDTH, self._MINIMUM_HEIGHT)
        self.show()
        self._move_to_anchor()
        # Desktop input should not open MathLive's virtual keyboard on every
        # new formula. It causes a large animated resize and repeated layout
        # work; the explicit API remains available when needed.
        QTimer.singleShot(0, self.editor.focus_editor)

    def current_kind(self) -> str:
        """编辑现有图层时保持原类型；新增图层仍由公式语法决定类型。"""
        return self._kind

    def set_theme(self, theme: str) -> None:
        self.editor.set_theme(theme)

    def accept_submission(self) -> None:
        """仅在宿主确认解析和渲染成功后关闭弹窗。"""
        self.dismiss()

    def dismiss(self) -> None:
        """关闭悬浮编辑器，并丢弃仅由该弹窗保存的草稿。"""
        if not self.isVisible():
            return
        self._resize_timer.stop()
        self.editor.hide_virtual_keyboard()
        self.hide()
        self.dismissed.emit()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if (
            self.isVisible()
            and event.type() == QEvent.Type.MouseButtonPress
            and isinstance(watched, QWidget)
            and watched is not self
            and not self.isAncestorOf(watched)
        ):
            QTimer.singleShot(0, self.dismiss)
        return super().eventFilter(watched, event)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.editor.hide_virtual_keyboard()
        self.dismissed.emit()
        event.accept()

    def _submit(self, latex: str) -> None:
        if latex.strip():
            self.submitted.emit(self.current_kind(), latex)

    def _resize_for_keyboard(self, _height: int) -> None:
        if self.isVisible() and not self._resize_timer.isActive():
            self._resize_timer.start()

    def _apply_pending_resize(self) -> None:
        if not self.isVisible():
            return
        self.adjustSize()
        self.resize(
            max(self._MINIMUM_WIDTH, self.width()),
            max(self._MINIMUM_HEIGHT, self.sizeHint().height()),
        )
        self._move_to_anchor()

    def _move_to_anchor(self) -> None:
        if self._anchor is None:
            return
        screen = QGuiApplication.screenAt(self._anchor) or self.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            self.move(self._anchor)
            return
        available = screen.availableGeometry()
        margin = 12
        max_width = max(1, available.width() - 2 * margin)
        max_height = max(1, available.height() - 2 * margin)
        self.setMinimumWidth(min(self._MINIMUM_WIDTH, max_width))
        self.setMinimumHeight(min(self._MINIMUM_HEIGHT, max_height))
        if self.width() > max_width or self.height() > max_height:
            self.resize(min(self.width(), max_width), min(self.height(), max_height))
        x = min(max(self._anchor.x(), available.left() + margin), available.right() - self.width() - margin + 1)
        y = self._anchor.y()
        if y + self.height() + margin > available.bottom() + 1:
            y = self._anchor.y() - self.height() - 4
        y = min(max(y, available.top() + margin), available.bottom() - self.height() - margin + 1)
        self.move(x, y)
