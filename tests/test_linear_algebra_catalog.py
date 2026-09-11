from collections import Counter

from linear_algebra.catalog.manifest import lecture_manifest, topic_entries


def test_manifest_has_exact_chapter_counts_and_three_levels() -> None:
    topics = topic_entries()
    assert len(topics) == 93
    assert Counter(item.chapter_number for item in topics) == Counter({1: 24, 2: 15, 3: 15, 4: 16, 5: 8, 6: 3, 7: 6, 8: 6})
    assert len({item.id for item in topics}) == 93
    assert all(len(item.source_path) == 3 for item in topics)
    nodes = lecture_manifest()
    assert {item.kind for item in nodes} == {"chapter", "section", "topic"}
    assert all(item.kind == "topic" for item in nodes if item.explanation_id)


def test_manifest_excludes_non_geometry_content_and_legacy_ids() -> None:
    topics = topic_entries()
    searchable = " ".join(" ".join(item.source_path) for item in topics)
    assert not any(word in searchable for word in ("自检", "练习", "挑战"))
    assert not any(item.id.startswith("vector-") for item in topics)


def test_manifest_builds_three_chapters_with_children() -> None:
    nodes = {node.id: node for node in lecture_manifest()}
    chapters = [nodes[f"ch{number:02d}"] for number in (1, 2, 3)]
    assert [len(chapter.children) for chapter in chapters] == [6, 9, 7]
    for chapter in chapters:
        assert all(nodes[child].parent_id == chapter.id for child in chapter.children)


def test_extended_chapters_have_stable_topic_ids_and_contract_links() -> None:
    from linear_algebra.catalog.manifest import topic_entries
    entries = topic_entries()
    assert {entry.chapter_number for entry in entries} >= {4, 5, 6, 7, 8}
    assert all(entry.explanation_id == f"explain.{entry.id}" for entry in entries if entry.chapter_number >= 4)
    assert all(entry.visualization_id == f"draw.{entry.id}" for entry in entries if entry.chapter_number >= 4)
