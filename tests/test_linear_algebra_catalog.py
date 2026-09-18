from collections import Counter
import json
from pathlib import Path

from linear_algebra.catalog.manifest import lecture_manifest, topic_entries
from linear_algebra.explanations.chapter_01 import CONTENT
from linear_algebra.explanations.chapter_02 import CONTENT as CHAPTER_TWO_CONTENT
from linear_algebra.visualizations.builders.chapter_01 import BUILDERS
from linear_algebra.visualizations.builders.chapter_02 import BUILDERS as CHAPTER_TWO_BUILDERS


REMOVED_CHAPTER_ONE_TOPICS = {
    "ch01.ops.velocity",
    "ch01.ops.cross-product",
    "ch01.ops.scalar-triple",
    "ch01.inner.equivalence",
    "ch01.inner.examples",
    "ch01.proof.method",
    "ch01.high-dimensional.analogy",
    "ch01.vector.point-distinction",
    "ch01.vector.coordinate-system",
    "ch01.vector.direction-examples",
    "ch01.projection.properties",
    "ch01.projection.force",
}
REMOVED_CHAPTER_TWO_TOPICS = {"ch02.high-dimensional.analogy"}


def test_manifest_has_exact_chapter_counts_and_three_levels() -> None:
    topics = topic_entries()
    assert len(topics) == 72
    assert Counter(item.chapter_number for item in topics) == Counter({1: 12, 2: 11, 3: 12, 4: 14, 5: 8, 6: 3, 7: 6, 8: 6})
    assert len({item.id for item in topics}) == 72
    assert REMOVED_CHAPTER_ONE_TOPICS.isdisjoint({item.id for item in topics})
    assert all(len(item.source_path) == 3 for item in topics)
    nodes = lecture_manifest()
    assert {item.kind for item in nodes} == {"chapter", "section", "topic"}
    assert all(item.kind == "topic" for item in nodes if item.explanation_id)


def test_manifest_excludes_non_geometry_content_and_legacy_ids() -> None:
    topics = topic_entries()
    searchable = " ".join(" ".join(item.source_path) for item in topics)
    assert not any(word in searchable for word in ("自检", "练习", "挑战"))
    assert not any(item.id.startswith("vector-") for item in topics)


def test_removed_chapter_one_topics_have_no_runtime_content_or_drawings() -> None:
    root = Path(__file__).parents[1]
    data = root / "linear_algebra" / "teaching" / "data"
    index = json.loads((data / "index.json").read_text(encoding="utf-8"))
    indexed_ids = {row["topic_id"] for row in index["topics"]}
    lecture = (root / ".agents" / "线性代数讲义.md").read_text(encoding="utf-8")

    assert REMOVED_CHAPTER_ONE_TOPICS.isdisjoint(CONTENT)
    assert {f"draw.{topic_id}" for topic_id in REMOVED_CHAPTER_ONE_TOPICS}.isdisjoint(BUILDERS)
    assert REMOVED_CHAPTER_ONE_TOPICS.isdisjoint(indexed_ids)
    assert "1.2.5 分层例题" not in lecture
    assert "1.2.6 向量的叉积（外积）" not in lecture
    assert "1.2.7 混合积" not in lecture
    assert "两种定义等价性的证明" not in lecture
    assert "1.3.4 分层例题" not in lecture
    assert "1.5.1 基本方法" not in lecture
    assert "1.7 n维向量的几何直觉拓展" not in lecture
    assert "1.1.2 向量与点的本质区别" not in lecture
    assert "1.1.3 坐标系的约定" not in lecture
    assert "1.1.4 分层例题" not in lecture
    assert "1.4.2 投影的关键性质" not in lecture
    assert "力 $F = (10, 20) N$" not in lecture
    for topic_id in REMOVED_CHAPTER_ONE_TOPICS:
        assert not (data / "compiled" / f"{topic_id}.json").exists()
        assert not (data / "published" / "ch01" / topic_id).exists()
        assert not (data / "published" / "ch01" / f"{topic_id}.json").exists()


def test_removed_chapter_two_topic_has_no_runtime_content_or_resources() -> None:
    root = Path(__file__).parents[1]
    data = root / "linear_algebra" / "teaching" / "data"
    index = json.loads((data / "index.json").read_text(encoding="utf-8"))
    indexed_ids = {row["topic_id"] for row in index["topics"]}
    lecture = (root / ".agents" / "线性代数讲义.md").read_text(encoding="utf-8")

    assert REMOVED_CHAPTER_TWO_TOPICS.isdisjoint(CHAPTER_TWO_CONTENT)
    assert {f"draw.{topic_id}" for topic_id in REMOVED_CHAPTER_TWO_TOPICS}.isdisjoint(CHAPTER_TWO_BUILDERS)
    assert REMOVED_CHAPTER_TWO_TOPICS.isdisjoint(indexed_ids)
    assert "2.10 高维拓展：n维空间中的矩阵运算" not in lecture
    for topic_id in REMOVED_CHAPTER_TWO_TOPICS:
        assert not (data / "compiled" / f"{topic_id}.json").exists()
        assert not (data / "published" / "ch02" / topic_id).exists()
        assert not (data / "published" / "ch02" / f"{topic_id}.json").exists()


def test_manifest_builds_three_chapters_with_children() -> None:
    nodes = {node.id: node for node in lecture_manifest()}
    chapters = [nodes[f"ch{number:02d}"] for number in (1, 2, 3)]
    assert [len(chapter.children) for chapter in chapters] == [5, 8, 7]
    for chapter in chapters:
        assert all(nodes[child].parent_id == chapter.id for child in chapter.children)


def test_extended_chapters_have_stable_topic_ids_and_contract_links() -> None:
    from linear_algebra.catalog.manifest import topic_entries
    entries = topic_entries()
    assert {entry.chapter_number for entry in entries} >= {4, 5, 6, 7, 8}
    assert all(entry.explanation_id == f"explain.{entry.id}" for entry in entries if entry.chapter_number >= 4)
    assert all(entry.visualization_id == f"draw.{entry.id}" for entry in entries if entry.chapter_number >= 4)
