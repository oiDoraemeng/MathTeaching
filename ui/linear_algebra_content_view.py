"""Presentation-only widget for one lecture explanation."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from linear_algebra.explanations.model import ExplanationContent


class LinearAlgebraContentView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("linearAlgebraContentView")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(5)
        self.title_label = QLabel(self)
        self.title_label.setObjectName("linearAlgebraContentTitle")
        self.summary_label = QLabel(self)
        self.formula_label = QLabel(self)
        self.formula_label.setObjectName("linearAlgebraFormula")
        self.steps_label = QLabel(self)
        self.meaning_label = QLabel(self)
        self.conclusion_label = QLabel(self)
        for label in (self.summary_label, self.formula_label, self.steps_label, self.meaning_label, self.conclusion_label):
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        for label in (self.title_label, self.summary_label, self.formula_label, self.steps_label, self.meaning_label, self.conclusion_label):
            layout.addWidget(label)
        self.setVisible(False)

    def set_content(self, content: ExplanationContent) -> None:
        self.title_label.setText(content.title)
        self.summary_label.setText(content.summary)
        self.formula_label.setText(content.formula)
        self.steps_label.setText("\n".join(f"{index}. {step}" for index, step in enumerate(content.steps, start=1)))
        self.meaning_label.setText(content.geometric_meaning)
        self.conclusion_label.setText(content.conclusion)
        self.setVisible(True)
