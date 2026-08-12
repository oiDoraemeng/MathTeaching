"""Reusable non-modal MathLive editor window."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QPoint, QTimer, Qt, Signal
from PySide6.QtWidgets import QApplication, QComboBox, QDialog, QHBoxLayout, QToolButton, QVBoxLayout, QWidget

from .widget import MathInputWidget


class FormulaEditorPopup(QDialog):
    """A floating editor that dismisses unsubmitted changes when focus moves away."""

    submitted = Signal(str, str)
    dismissed = Signal()
    kindChanged = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._anchor: QPoint | None = None
        self.setObjectName("formulaEditorPopup")
        self.setWindowTitle("编辑公式")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        self.kind_combo = QComboBox(self)
        self.kind_combo.addItem("显式", "explicit")
        self.kind_combo.addItem("隐式", "implicit")
        self.kind_combo.addItem("参数", "parametric")
        self.close_button = QToolButton(self)
        self.close_button.setText("x")
        self.close_button.setToolTip("放弃未提交修改并关闭")
        header.addWidget(self.kind_combo)
        header.addStretch()
        header.addWidget(self.close_button)
        layout.addLayout(header)
        self.editor = MathInputWidget(self)
        layout.addWidget(self.editor)

        self.editor.submitted.connect(self._submit)
        self.editor.keyboardHeightChanged.connect(self._resize_for_keyboard)
        self.close_button.clicked.connect(self.dismiss)
        self.kind_combo.currentIndexChanged.connect(lambda: self.kindChanged.emit(self.current_kind()))
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
        """Open the editor with a cached formula, without submitting it yet."""
        self._anchor = anchor
        index = self.kind_combo.findData(kind)
        self.kind_combo.setCurrentIndex(index if index >= 0 else 1)
        self.editor.set_placeholder(placeholder)
        self.editor.set_latex(latex)
        self.show()
        self._move_to_anchor()
        QTimer.singleShot(0, self.editor.show_virtual_keyboard)

    def current_kind(self) -> str:
        """Return the current surface form selected in the popup."""
        return str(self.kind_combo.currentData())

    def accept_submission(self) -> None:
        """Close only after the host confirms parsing and rendering succeeded."""
        self.dismiss()

    def dismiss(self) -> None:
        """Close the floating editor and discard the draft held only by this popup."""
        if not self.isVisible():
            return
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

    def closeEvent(self, event) -> None:
        self.editor.hide_virtual_keyboard()
        self.dismissed.emit()
        event.accept()

    def _submit(self, latex: str) -> None:
        if latex.strip():
            self.submitted.emit(self.current_kind(), latex)

    def _resize_for_keyboard(self, _height: int) -> None:
        self.adjustSize()
        self.resize(max(420, self.width()), self.sizeHint().height())
        self._move_to_anchor()

    def _move_to_anchor(self) -> None:
        if self._anchor is not None:
            self.move(self._anchor)
