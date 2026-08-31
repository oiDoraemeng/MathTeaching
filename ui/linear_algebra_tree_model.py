"""Qt tree adapter for the source-ordered linear algebra curriculum."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem

from linear_algebra.registry import CurriculumRegistry


class LinearAlgebraTreeModel:
    """Builds and controls a three-level chapter/section/topic tree."""

    def __init__(self, tree: QTreeWidget, registry: CurriculumRegistry) -> None:
        self.tree = tree
        self.registry = registry
        self._nodes = {node.id: node for node in registry.nodes}
        self._topics = {topic.id: topic for topic in registry.topics}
        self._items: dict[str, QTreeWidgetItem] = {}
        self._searchable = self._build_search_index()
        self._query = ""
        self._rebuild(None)

    def filter(self, query: str) -> None:
        self._query = _normalize(query)
        matches = None
        if self._query:
            matches = {
                topic_id
                for topic_id, searchable in self._searchable.items()
                if self._query in searchable
            }
        self._rebuild(matches)

    def visible_topic_ids(self) -> tuple[str, ...]:
        return tuple(topic.id for topic in self.registry.topics if topic.id in self._items)

    def restore_default_expansion(self) -> None:
        for node_id, item in self._items.items():
            node = self._nodes[node_id]
            item.setExpanded(node.kind == "chapter")

    def expand_all(self) -> None:
        for item in self._items.values():
            if item.childCount():
                item.setExpanded(True)

    def collapse_to_chapters(self) -> None:
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
            self.restore_default_expansion()
        else:
            self.expand_all()

    def _branch_item(self, node_id: str, title: str) -> QTreeWidgetItem:
        item = QTreeWidgetItem([title])
        item.setData(0, Qt.ItemDataRole.UserRole, None)
        self._items[node_id] = item
        return item

    def _build_search_index(self) -> dict[str, str]:
        index: dict[str, str] = {}
        for topic in self.registry.topics:
            explanation = self.registry.get_explanation(topic.explanation_id)
            values = (
                topic.title,
                *topic.source_path,
                explanation.summary,
                explanation.formula,
                *explanation.searchable_text,
            )
            index[topic.id] = _normalize(" ".join(values))
        return index


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())
