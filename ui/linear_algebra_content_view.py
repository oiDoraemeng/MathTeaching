"""Presentation-only widget for one lecture explanation."""

from __future__ import annotations

from typing import Mapping

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
        self.analogy_boundary_label = QLabel(self)
        self.read_guide_label = QLabel(self)
        self.source_label = QLabel(self)
        self.source_diagnostic_label = QLabel(self)
        self.tableau_title_label = QLabel(self)
        self.tableau_caption_label = QLabel(self)
        self.tableau_highlight_label = QLabel(self)
        self._structured_labels = (
            self.definition_label,
            self.derivation_label,
            self.examples_label,
            self.intuition_label,
            self.geometry_label,
            self.pitfalls_label,
            self.invariants_label,
            self.connections_label,
            self.analogy_boundary_label,
            self.read_guide_label,
            self.source_label,
            self.source_diagnostic_label,
            self.tableau_title_label,
            self.tableau_caption_label,
            self.tableau_highlight_label,
        )
        for label in (
            self.summary_label,
            self.formula_label,
            self.steps_label,
            self.meaning_label,
            self.conclusion_label,
            *self._structured_labels,
            self.tableau_title_label,
            self.tableau_caption_label,
            self.tableau_highlight_label,
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
        self.source_label.hide()
        self.source_diagnostic_label.hide()
        for label in (self.tableau_title_label, self.tableau_caption_label, self.tableau_highlight_label):
            label.hide()
        self.setVisible(False)

    def set_tableau_stage(self, stage: Mapping[str, object] | object) -> None:
        """Render storyboard metadata without interpreting matrix JSON."""
        def value(name: str, default: object = "") -> object:
            if isinstance(stage, Mapping):
                return stage.get(name, default)
            return getattr(stage, name, default)

        title = str(value("title", ""))
        caption = str(value("caption", ""))
        rows = value("highlight_rows", ())
        if not isinstance(rows, (list, tuple)):
            rows = ()
        self.tableau_title_label.setText(title)
        self.tableau_caption_label.setText(caption)
        self.tableau_highlight_label.setText("高亮行：" + ", ".join(str(int(row) + 1) for row in rows))
        for label, text in ((self.tableau_title_label, title), (self.tableau_caption_label, caption), (self.tableau_highlight_label, rows)):
            label.setVisible(bool(text))

    def set_storyboard_stage(self, stage: Mapping[str, object] | object) -> None:
        """Render compiled storyboard metadata without touching scene data.

        The same presentation hook is used for tableau, mapping, and
        quadratic stages.  ``visible_refs`` are semantic references supplied
        by the compiler; command aliases are intentionally not displayed.
        """

        def value(name: str, default: object = "") -> object:
            if isinstance(stage, Mapping):
                return stage.get(name, default)
            return getattr(stage, name, default)

        title = str(value("title", ""))
        caption = str(value("caption", ""))
        refs = value("visible_refs", ())
        if not isinstance(refs, (list, tuple)):
            refs = ()
        highlight = "高亮关系：" + "、".join(str(item) for item in refs)
        self.tableau_title_label.setText(title)
        self.tableau_caption_label.setText(caption)
        self.tableau_highlight_label.setText(highlight if refs else "")
        self.tableau_title_label.setVisible(bool(title))
        self.tableau_caption_label.setVisible(bool(caption))
        self.tableau_highlight_label.setVisible(bool(refs))

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

    def set_source_context(
        self,
        source: Mapping[str, object] | object | None = None,
        diagnostic: Mapping[str, object] | tuple[object, ...] | None = None,
    ) -> None:
        """Show bounded lecture provenance and a concise stale-source notice."""

        def value(name: str, default: object = "") -> object:
            if isinstance(source, Mapping):
                return source.get(name, default)
            return getattr(source, name, default) if source is not None else default

        source_path = value("source_path", ())
        heading_path = value("heading_path", ())
        paths = tuple(str(item) for item in (*tuple(source_path), *tuple(heading_path)) if item)
        source_hash = value("source_hash", None)
        self.source_label.setText("讲义来源：" + " / ".join(paths) + (f"（{source_hash}）" if source_hash else ""))
        self.source_label.setVisible(bool(paths or source_hash))
        if isinstance(diagnostic, Mapping):
            code = diagnostic.get("code", "")
            published = diagnostic.get("published_hash", "")
            current = diagnostic.get("current_hash", "")
        elif isinstance(diagnostic, (tuple, list)) and len(diagnostic) == 3:
            code, published, current = diagnostic
        else:
            code = published = current = ""
        text = f"讲义来源已变化：{code}（已发布 {published}，当前 {current}）" if code else ""
        self.source_diagnostic_label.setText(text)
        self.source_diagnostic_label.setVisible(bool(text))

    def set_artifact(self, artifact: object, *, source_diagnostic: object = None) -> None:
        """Render an artifact's explanation and its bounded provenance together."""

        self.set_content(getattr(artifact, "explanation", artifact))
        self.set_source_context(getattr(artifact, "source", None), source_diagnostic)

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
        def set_section(label: QLabel, title: str, body: str) -> None:
            body = body.strip()
            label.setText(f"{title}\n{body}" if body else "")
            label.setVisible(bool(body))

        set_section(self.definition_label, "定义", definition)
        set_section(self.derivation_label, "推导", self.steps_label.text())
        set_section(self.examples_label, "数字例题", "\n\n".join(examples))
        set_section(self.intuition_label, "直觉", content.intuition)
        set_section(self.geometry_label, "几何意义", geometric_meaning)
        set_section(self.pitfalls_label, "误区", "\n".join(f"• {value}" for value in content.pitfalls))
        set_section(self.invariants_label, "不变量", "\n".join(f"• {value}" for value in content.invariants))
        set_section(self.connections_label, "关联", "\n".join(f"• {value}" for value in content.connections))
        set_section(self.analogy_boundary_label, "类比边界", content.analogy_boundary)
        set_section(self.read_guide_label, "读图提示", "\n".join(f"{index}. {value}" for index, value in enumerate(content.read_guide, start=1)))
