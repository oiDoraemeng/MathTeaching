from __future__ import annotations

from collections import OrderedDict

from .chapter_01 import CHAPTER as CHAPTER_1, TOPICS as CHAPTER_1_TOPICS
from .chapter_02 import CHAPTER as CHAPTER_2, TOPICS as CHAPTER_2_TOPICS
from .chapter_03 import CHAPTER as CHAPTER_3, TOPICS as CHAPTER_3_TOPICS
from .model import LessonEntry, LessonNode, display_heading
from .runtime_manifest import (
    CHAPTERS as RUNTIME_CHAPTERS,
    CHAPTER_4_TOPICS,
    CHAPTER_5_TOPICS,
    CHAPTER_6_TOPICS,
    CHAPTER_7_TOPICS,
    CHAPTER_8_TOPICS,
)

CHAPTER_4 = RUNTIME_CHAPTERS[4]
CHAPTER_5 = RUNTIME_CHAPTERS[5]
CHAPTER_6 = RUNTIME_CHAPTERS[6]
CHAPTER_7 = RUNTIME_CHAPTERS[7]
CHAPTER_8 = RUNTIME_CHAPTERS[8]

_ALL_TOPICS: tuple[LessonEntry, ...] = (*CHAPTER_1_TOPICS, *CHAPTER_2_TOPICS, *CHAPTER_3_TOPICS, *CHAPTER_4_TOPICS, *CHAPTER_5_TOPICS, *CHAPTER_6_TOPICS, *CHAPTER_7_TOPICS, *CHAPTER_8_TOPICS)


def topic_entries() -> tuple[LessonEntry, ...]:
    return _ALL_TOPICS


def lecture_manifest() -> tuple[LessonNode, ...]:
    nodes: OrderedDict[str, LessonNode] = OrderedDict()
    chapter_names = {1: CHAPTER_1, 2: CHAPTER_2, 3: CHAPTER_3, 4: CHAPTER_4, 5: CHAPTER_5, 6: CHAPTER_6, 7: CHAPTER_7, 8: CHAPTER_8}
    chapter_ids = {number: f"ch{number:02d}" for number in chapter_names}
    section_children: dict[str, list[str]] = {}
    for index, entry in enumerate(_ALL_TOPICS):
        chapter_id = chapter_ids[entry.chapter_number]
        chapter_path = (chapter_names[entry.chapter_number],)
        if chapter_id not in nodes:
            nodes[chapter_id] = LessonNode(
                id=chapter_id,
                kind="chapter",
                title=chapter_names[entry.chapter_number],
                order=(entry.chapter_number,),
                parent_id=None,
                children=(),
                source_path=chapter_path,
                explanation_id=None,
                visualization_id=None,
                required_capabilities=(),
            )
        section_id = entry.section_id
        if section_id not in nodes:
            nodes[section_id] = LessonNode(
                id=section_id,
                kind="section",
                title=display_heading(entry.display_title or entry.source_path[1]),
                order=(entry.chapter_number, index),
                parent_id=chapter_id,
                children=(),
                source_path=entry.source_path[:2],
                explanation_id=None,
                visualization_id=None,
                required_capabilities=(),
            )
            section_children.setdefault(chapter_id, []).append(section_id)
        nodes[entry.id] = LessonNode(
            id=entry.id,
            kind="topic",
            title=entry.title,
            order=(entry.chapter_number, index),
            parent_id=section_id,
            children=(),
            source_path=entry.source_path,
            explanation_id=entry.explanation_id,
            visualization_id=entry.visualization_id,
            required_capabilities=entry.required_capabilities,
        )
        section_children.setdefault(section_id, []).append(entry.id)
    for parent_id, children in section_children.items():
        parent = nodes[parent_id]
        nodes[parent_id] = LessonNode(
            id=parent.id,
            kind=parent.kind,
            title=parent.title,
            order=parent.order,
            parent_id=parent.parent_id,
            children=tuple(children),
            source_path=parent.source_path,
            explanation_id=parent.explanation_id,
            visualization_id=parent.visualization_id,
            required_capabilities=parent.required_capabilities,
        )
    chapter_children = {chapter_id: tuple(section_children.get(chapter_id, ())) for chapter_id in chapter_ids.values()}
    for chapter_id, children in chapter_children.items():
        parent = nodes[chapter_id]
        nodes[chapter_id] = LessonNode(
            id=parent.id,
            kind=parent.kind,
            title=parent.title,
            order=parent.order,
            parent_id=None,
            children=children,
            source_path=parent.source_path,
            explanation_id=None,
            visualization_id=None,
            required_capabilities=(),
        )
    return tuple(nodes.values())
