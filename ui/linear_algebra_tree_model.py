"""Qt tree adapter for the source-ordered linear algebra curriculum."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem

from linear_algebra.registry import CurriculumRegistry, runtime_teaching_store


class LinearAlgebraTreeModel:
    """Builds and controls a three-level chapter/section/topic tree."""

    def __init__(self, tree: QTreeWidget, registry: CurriculumRegistry) -> None:
        self.tree = tree
        self.registry = registry
        self._nodes = {node.id: node for node in registry.nodes}
        self._topics = {topic.id: topic for topic in registry.topics}
        self._items: dict[str, QTreeWidgetItem] = {}
        self._artifact_store = runtime_teaching_store()
        self._searchable = self._build_search_index()
        self._primary_searchable = self._build_primary_search_index()
        self._query = ""
        self._expanded_node_ids: set[str] | None = None
        self._rebuild(None)

    def filter(self, query: str) -> None:
        normalized_query = _normalize(query)
        if normalized_query:
            self._capture_expansion()
        else:
            self._expanded_node_ids = None
        self._query = normalized_query
        matches = None
        if self._query:
            matches = {
                topic_id
                for topic_id, searchable in self._searchable.items()
                if self._query in searchable
            }
            primary_matches = {
                topic_id
                for topic_id, searchable in self._primary_searchable.items()
                if self._query in searchable
            }
            if primary_matches:
                matches = primary_matches
        self._rebuild(matches)

    def visible_topic_ids(self) -> tuple[str, ...]:
        return tuple(topic.id for topic in self.registry.topics if topic.id in self._items)

    @property
    def query(self) -> str:
        """Return the normalized query currently represented by the tree."""
        return self._query

    def needs_filter(self, query: str) -> bool:
        """Return whether applying ``query`` would change the tree contents."""
        return self._query != _normalize(query)

    def restore_default_expansion(self) -> None:
        self._expanded_node_ids = set()
        for node_id, item in self._items.items():
            node = self._nodes[node_id]
            # 首次打开时展开章节、折叠主题，便于浏览目录层级。
            item.setExpanded(node.kind == "chapter")
            if node.kind == "chapter" and item.childCount():
                self._expanded_node_ids.add(node_id)

    def expand_all(self) -> None:
        self._expanded_node_ids = set()
        for node_id, item in self._items.items():
            if item.childCount():
                item.setExpanded(True)
                self._expanded_node_ids.add(node_id)

    def collapse_to_chapters(self) -> None:
        self._expanded_node_ids = set()
        for item in self._items.values():
            if item.childCount():
                item.setExpanded(False)

    def all_branches_expanded(self) -> bool:
        branches = [item for item in self._items.values() if item.childCount()]
        return bool(branches) and all(item.isExpanded() for item in branches)

    def all_chapters_collapsed(self) -> bool:
        chapters = [self._items[node.id] for node in self.registry.nodes if node.kind == "chapter" and node.id in self._items]
        return bool(chapters) and all(not item.isExpanded() for item in chapters)

    def default_expansion_is_restored(self) -> bool:
        return all(
            item.isExpanded() == (self._nodes[node_id].kind == "chapter")
            for node_id, item in self._items.items()
            if item.childCount()
        )

    def item_for(self, node_id: str) -> QTreeWidgetItem | None:
        return self._items.get(node_id)

    def _rebuild(self, matched_topics: set[str] | None) -> None:
        self.tree.setUpdatesEnabled(False)
        try:
            self.tree.clear()
            self._items.clear()
            visible_sections: set[str] | None = None
            visible_chapters: set[str] | None = None
            if matched_topics is not None:
                visible_sections = {self._topics[topic_id].section_id for topic_id in matched_topics}
                visible_chapters = {f"ch{self._topics[topic_id].chapter_number:02d}" for topic_id in matched_topics}
            for chapter in (node for node in self.registry.nodes if node.kind == "chapter"):
                if visible_chapters is not None and chapter.id not in visible_chapters:
                    continue
                chapter_item = self._branch_item(chapter.id, chapter.title)
                self.tree.addTopLevelItem(chapter_item)
                for section_id in chapter.children:
                    if visible_sections is not None and section_id not in visible_sections:
                        continue
                    section = self._nodes[section_id]
                    section_item = self._branch_item(section.id, section.title)
                    chapter_item.addChild(section_item)
                    for topic_id in section.children:
                        if matched_topics is not None and topic_id not in matched_topics:
                            continue
                        topic = self._topics[topic_id]
                        item = QTreeWidgetItem([topic.title])
                        item.setData(0, Qt.ItemDataRole.UserRole, topic.id)
                        explanation = self.registry.get_explanation(topic.explanation_id)
                        item.setToolTip(0, explanation.summary)
                        self._items[topic.id] = item
                        section_item.addChild(item)
            if matched_topics is None:
                if self._expanded_node_ids is None:
                    self.restore_default_expansion()
                else:
                    self._restore_expansion()
            else:
                self.expand_all()
        finally:
            self.tree.setUpdatesEnabled(True)
            self.tree.viewport().update()

    def _capture_expansion(self) -> None:
        self._expanded_node_ids = {
            node_id for node_id, item in self._items.items() if item.childCount()
            and item.isExpanded()
        }

    def _restore_expansion(self) -> None:
        expanded = self._expanded_node_ids or set()
        for node_id, item in self._items.items():
            if item.childCount():
                item.setExpanded(node_id in expanded)

    def _branch_item(self, node_id: str, title: str) -> QTreeWidgetItem:
        item = QTreeWidgetItem([title])
        item.setData(0, Qt.ItemDataRole.UserRole, None)
        self._items[node_id] = item
        return item

    def _build_search_index(self) -> dict[str, str]:
        index: dict[str, str] = {}
        for topic in self.registry.topics:
            explanation = self.registry.get_explanation(topic.explanation_id)
            values: list[str] = [
                topic.title,
                *topic.source_path,
                explanation.summary,
                explanation.formula,
                *explanation.searchable_text,
            ]
            try:
                stored = self._artifact_store.published(topic.id)
            except (KeyError, OSError, TypeError, ValueError):
                stored = None
            if stored is not None:
                structured = stored.artifact.explanation
                values.extend(
                    [
                        structured.definition,
                        structured.formula,
                        structured.intuition,
                        structured.geometric_meaning,
                        structured.conclusion,
                        structured.analogy_boundary,
                        structured.transfer_note,
                        *structured.derivation,
                        *structured.pitfalls,
                        *structured.invariants,
                        *structured.connections,
                        *structured.read_guide,
                        *structured.searchable_text,
                        *(example.title for example in structured.worked_examples),
                        *(line for example in structured.worked_examples for line in example.calculation),
                    ]
                )
            index[topic.id] = _normalize(" ".join(values))
        return index

    def _build_primary_search_index(self) -> dict[str, str]:
        """Index topic-local labels before shared chapter prose.

        A chapter heading such as ``主轴定理`` is a valid full source-path
        token, but it must not make every sibling leaf match.  Topic title,
        leaf source heading, formula and summary are the deterministic,
        specific tier; the broader index remains available when no specific
        result exists.
        """
        index: dict[str, str] = {}
        for topic in self.registry.topics:
            explanation = self.registry.get_explanation(topic.explanation_id)
            leaf = topic.source_path[-1] if topic.source_path else ""
            index[topic.id] = _normalize(" ".join((topic.title, leaf, explanation.formula, explanation.summary)))
        return index


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())
