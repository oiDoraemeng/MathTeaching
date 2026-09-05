"""Presentation-only widget for one lecture explanation."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from linear_algebra.explanations.model import ExplanationContent
from linear_algebra.teaching.model import ExplanationContentV2


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
        self.definition_label = QLabel(self)
        self.derivation_label = QLabel(self)
        self.examples_label = QLabel(self)
        self.intuition_label = QLabel(self)
        self.geometry_label = QLabel(self)
        self.pitfalls_label = QLabel(self)
        self.invariants_label = QLabel(self)
        self.connections_label = QLabel(self)
        self.read_guide_label = QLabel(self)
        self._structured_labels = (
            self.definition_label,
            self.derivation_label,
            self.examples_label,
            self.intuition_label,
            self.geometry_label,
            self.pitfalls_label,
            self.invariants_label,
            self.connections_label,
            self.read_guide_label,
        )
        for label in (
            self.summary_label,
            self.formula_label,
            self.steps_label,
            self.meaning_label,
            self.conclusion_label,
            *self._structured_labels,
        ):
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        for label in (
            self.title_label,
            self.summary_label,
            self.formula_label,
            self.steps_label,
            self.meaning_label,
            self.conclusion_label,
            *self._structured_labels,
        ):
            layout.addWidget(label)
        for label in self._structured_labels:
            label.hide()
        self.setVisible(False)

    def set_content(self, content: ExplanationContent | ExplanationContentV2) -> None:
        self.title_label.setText(content.title)
        self.summary_label.setText(content.summary)
        if isinstance(content, ExplanationContentV2):
            self._set_structured_content(content)
        else:
            self.formula_label.setText(content.formula)
            self.steps_label.setText("\n".join(f"{index}. {step}" for index, step in enumerate(content.steps, start=1)))
            self.meaning_label.setText(content.geometric_meaning)
            self.conclusion_label.setText(content.conclusion)
            for label in self._structured_labels:
                label.hide()
        self.setVisible(True)

    def _set_structured_content(self, content: ExplanationContentV2) -> None:
        """Render the artifact's math layers without flattening them into prose."""

        section_text = {section.id: section.text for section in content.sections}
        definition = content.definition or section_text.get("definition", "")
        formula = content.formula or section_text.get("formula", "")
        derivation = content.derivation or ((section_text["derivation"],) if section_text.get("derivation") else ())
        geometric_meaning = content.geometric_meaning or section_text.get("geometric_meaning", "")
        self.formula_label.setText(formula)
        self.steps_label.setText("\n".join(f"{index}. {step}" for index, step in enumerate(derivation, start=1)))
        self.meaning_label.setText(geometric_meaning)
        self.conclusion_label.setText(content.conclusion)
        examples = []
        for index, example in enumerate(content.worked_examples, start=1):
            title = example.title or example.kind
            calculation = "\n".join(example.calculation)
            checks = "; ".join(f"{check.name}={check.expected}" for check in example.checks)
            examples.append(f"{index}. {title}\n{calculation}\n结果：{example.result}\n校验：{checks}".strip())
        values = {
            self.definition_label: f"定义\n{definition}",
            self.derivation_label: f"推导\n{self.steps_label.text()}",
            self.examples_label: "数字例题\n" + "\n\n".join(examples),
            self.intuition_label: f"直觉\n{content.intuition}",
            self.geometry_label: f"几何意义\n{geometric_meaning}",
            self.pitfalls_label: "误区\n" + "\n".join(f"• {value}" for value in content.pitfalls),
            self.invariants_label: "不变量\n" + "\n".join(f"• {value}" for value in content.invariants),
            self.connections_label: "关联\n" + "\n".join(f"• {value}" for value in content.connections),
            self.read_guide_label: "读图提示\n" + "\n".join(f"{index}. {value}" for index, value in enumerate(content.read_guide, start=1)),
        }
        for label, text in values.items():
            label.setText(text.strip())
            label.setVisible(bool(text.strip().split("\n", 1)[-1]))
