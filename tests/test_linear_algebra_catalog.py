from collections import Counter
import json
from pathlib import Path

from linear_algebra.catalog.manifest import lecture_manifest, topic_entries
from linear_algebra.catalog.model import display_math_text
from linear_algebra.explanations.chapter_01 import CONTENT
from linear_algebra.explanations.chapter_02 import CONTENT as CHAPTER_TWO_CONTENT
from linear_algebra.explanations.chapter_03 import CONTENT as CHAPTER_THREE_CONTENT
from linear_algebra.explanations.chapter_06 import CONTENT as CHAPTER_SIX_CONTENT
from linear_algebra.visualizations.builders.chapter_01 import BUILDERS
from linear_algebra.visualizations.builders.chapter_02 import BUILDERS as CHAPTER_TWO_BUILDERS
from linear_algebra.visualizations.builders.chapter_03 import BUILDERS as CHAPTER_THREE_BUILDERS
from linear_algebra.visualizations.builders.chapter_06 import BUILDERS as CHAPTER_SIX_BUILDERS


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
    "ch01.inner.applications",
}
REMOVED_CHAPTER_TWO_TOPICS = {"ch02.high-dimensional.analogy"}
REMOVED_CHAPTER_THREE_TOPICS = {
    "ch03.det.high-dimensional-volume",
    "ch03.inverse.reverse-order",
    "ch03.inverse.formula",
    "ch03.inverse.examples",
}
REMOVED_CHAPTER_FOUR_TOPICS = {"ch04.nullspace.test", "ch04.rank.collapse", "ch04.kernel-image", "ch04.rank-nullity"}
REMOVED_CHAPTER_FIVE_TOPICS = {"ch05.fundamental-solution-system", "ch05.elementary-matrix-elimination", "ch05.least-squares-derivation"}
REMOVED_CHAPTER_SIX_TOPICS = {"ch06.basis-change.motivation"}


def test_manifest_has_exact_chapter_counts_and_three_levels() -> None:
    topics = topic_entries()
    assert len(topics) == 47
    assert Counter(item.chapter_number for item in topics) == Counter({1: 11, 2: 9, 3: 8, 4: 4, 5: 5, 6: 2, 7: 4, 8: 4})
    assert len({item.id for item in topics}) == 47
    assert REMOVED_CHAPTER_ONE_TOPICS.isdisjoint({item.id for item in topics})
    assert REMOVED_CHAPTER_THREE_TOPICS.isdisjoint({item.id for item in topics})
    assert REMOVED_CHAPTER_FOUR_TOPICS.isdisjoint({item.id for item in topics})
    assert REMOVED_CHAPTER_FIVE_TOPICS.isdisjoint({item.id for item in topics})
    assert REMOVED_CHAPTER_SIX_TOPICS.isdisjoint({item.id for item in topics})
    assert all(len(item.source_path) == 3 for item in topics)
    nodes = lecture_manifest()
    assert {item.kind for item in nodes} == {"chapter", "section", "topic"}
    assert all(item.kind == "topic" for item in nodes if item.explanation_id)


def test_manifest_excludes_non_geometry_content_and_legacy_ids() -> None:
    topics = topic_entries()
    searchable = " ".join(" ".join(item.source_path) for item in topics)
    assert not any(word in searchable for word in ("自检", "练习", "挑战"))
    assert not any(item.id.startswith("vector-") for item in topics)


def test_removed_chapter_six_topic_has_no_runtime_content_or_resources() -> None:
    root = Path(__file__).parents[1]
    data = root / "linear_algebra" / "teaching" / "data"
    index = json.loads((data / "index.json").read_text(encoding="utf-8"))
    indexed_ids = {row["topic_id"] for row in index["topics"]}

    assert REMOVED_CHAPTER_SIX_TOPICS.isdisjoint(CHAPTER_SIX_CONTENT)
    assert {f"draw.{topic_id}" for topic_id in REMOVED_CHAPTER_SIX_TOPICS}.isdisjoint(CHAPTER_SIX_BUILDERS)
    assert REMOVED_CHAPTER_SIX_TOPICS.isdisjoint(indexed_ids)
    for topic_id in REMOVED_CHAPTER_SIX_TOPICS:
        assert not (data / "compiled" / f"{topic_id}.json").exists()
        assert not (data / "drafts" / "ch06" / topic_id / "r1.json").exists()
        assert not (data / "revieweds" / "ch06" / topic_id / "r1.json").exists()


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


def test_removed_chapter_three_topics_have_no_runtime_content_or_resources() -> None:
    root = Path(__file__).parents[1]
    data = root / "linear_algebra" / "teaching" / "data"
    index = json.loads((data / "index.json").read_text(encoding="utf-8"))
    indexed_ids = {row["topic_id"] for row in index["topics"]}

    assert REMOVED_CHAPTER_THREE_TOPICS.isdisjoint(CHAPTER_THREE_CONTENT)
    assert {f"draw.{topic_id}" for topic_id in REMOVED_CHAPTER_THREE_TOPICS}.isdisjoint(CHAPTER_THREE_BUILDERS)
    assert REMOVED_CHAPTER_THREE_TOPICS.isdisjoint(indexed_ids)
    for topic_id in REMOVED_CHAPTER_THREE_TOPICS:
        assert not any(path.is_file() and topic_id in path.as_posix() for path in data.rglob("*"))


def test_removed_chapter_four_topics_have_no_runtime_resources() -> None:
    root = Path(__file__).parents[1]
    data = root / "linear_algebra" / "teaching" / "data"
    index = json.loads((data / "index.json").read_text(encoding="utf-8"))
    indexed_ids = {row["topic_id"] for row in index["topics"]}

    assert REMOVED_CHAPTER_FOUR_TOPICS.isdisjoint(indexed_ids)
    for topic_id in REMOVED_CHAPTER_FOUR_TOPICS:
        assert not any(path.is_file() and topic_id in path.as_posix() for path in data.rglob("*"))


def test_chapter_five_keeps_only_sections_5_1_through_5_5() -> None:
    root = Path(__file__).parents[1]
    data = root / "linear_algebra" / "teaching" / "data"
    nodes = {node.id: node for node in lecture_manifest()}
    indexed_ids = {
        row["topic_id"]
        for row in json.loads((data / "index.json").read_text(encoding="utf-8"))["topics"]
    }

    assert nodes["ch05"].children == ("ch05.s1", "ch05.s2", "ch05.s3", "ch05.s4", "ch05.s5")
    assert nodes["ch05.s1"].title == "5.1 齐次方程组 Ax = 0"
    assert nodes["ch05.s2"].title == "5.2 非齐次方程组 Ax = b"
    assert [nodes[topic_id].title for section_id in nodes["ch05"].children for topic_id in nodes[section_id].children] == [
        "齐次线性方程组",
        "非齐次方程组的解结构",
        "解的存在性与唯一性",
        "高斯消元",
        "最小二乘解",
    ]
    assert REMOVED_CHAPTER_FIVE_TOPICS.isdisjoint(indexed_ids)
    for topic_id in REMOVED_CHAPTER_FIVE_TOPICS:
        assert not any(path.is_file() and topic_id in path.as_posix() for path in data.rglob("*"))


def test_manifest_builds_three_chapters_with_children() -> None:
    nodes = {node.id: node for node in lecture_manifest()}
    chapters = [nodes[f"ch{number:02d}"] for number in (1, 2, 3)]
    assert [len(chapter.children) for chapter in chapters] == [5, 8, 6]
    for chapter in chapters:
        assert all(nodes[child].parent_id == chapter.id for child in chapter.children)


def test_chapter_two_parent_directories_keep_numbers_from_2_2_onward() -> None:
    nodes = {node.id: node for node in lecture_manifest()}

    assert nodes["ch02"].children[0] == "ch02.s22"
    assert nodes["ch02.s22"].title.startswith("2.2 ")
    assert nodes["ch02.s23"].title == "2.3 批量投影"
    assert nodes["ch02.s27"].title == "2.7 矩阵和基"
    assert nodes["ch02.s28"].title == "2.8 矩阵的幂"
    assert nodes["ch02.matrix.powers"].title == "矩阵的幂"
    assert nodes["ch02.s29"].title == "2.9 线性无关与秩"
    assert all(
        not nodes[topic_id].title[:1].isdigit()
        for section_id in nodes["ch02"].children
        for topic_id in nodes[section_id].children
    )


def test_plain_ui_math_text_removes_raw_case_title_markup() -> None:
    assert display_math_text(r"案例一：$\boldsymbol v_1=(3,4)$ 的模") == "案例一：v₁=(3,4) 的模"


def test_chapter_three_section_3_2_uses_the_three_core_property_topics() -> None:
    nodes = {node.id: node for node in lecture_manifest()}
    assert nodes["ch03.s32"].children == (
        "ch03.det.basic-properties",
        "ch03.det.multiplicativity",
        "ch03.det.transpose",
    )


def test_chapter_three_sections_3_3_to_3_5_are_text_only_and_merged() -> None:
    entries = {entry.id: entry for entry in topic_entries()}
    nodes = {node.id: node for node in lecture_manifest()}

    assert nodes["ch03.s33"].title == "3.3 克拉默法则"
    assert nodes["ch03.s34"].title == "3.4 逆矩阵"
    assert nodes["ch03.s34"].children == ("ch03.inverse.undo",)
    assert nodes["ch03.inverse.undo"].title == "逆矩阵"
    assert nodes["ch03.s35"].title == "3.5 伴随矩阵"
    assert nodes["ch03.s35"].children == ("ch03.adjugate.matrix",)
    assert nodes["ch03.adjugate.matrix"].title == "伴随矩阵"
    assert nodes["ch03.s36"].title.startswith("3.6 ")
    assert all(
        entries[topic_id].required_capabilities == ()
        for topic_id in (
            "ch03.cramer.area-ratio",
            "ch03.inverse.undo",
            "ch03.adjugate.matrix",
        )
    )


def test_extended_chapters_have_stable_topic_ids_and_contract_links() -> None:
    from linear_algebra.catalog.manifest import topic_entries
    entries = topic_entries()
    assert {entry.chapter_number for entry in entries} >= {4, 5, 6, 7, 8}
    assert all(entry.explanation_id == f"explain.{entry.id}" for entry in entries if entry.chapter_number >= 4)
    assert all(entry.visualization_id == f"draw.{entry.id}" for entry in entries if entry.chapter_number >= 4)


def test_chapter_four_section_4_2_merges_only_the_two_requested_lecture_topics() -> None:
    entries = topic_entries()
    section = next(node for node in lecture_manifest() if node.id == "ch04.s42")

    assert section.title == "4.2 线性组合、线性相关与线性无关"
    assert section.children == ("ch04.dependence.redundancy",)
    topic = next(entry for entry in entries if entry.id == "ch04.dependence.redundancy")
    assert topic.title == "线性相关与线性无关"
    assert topic.source_anchor.heading_path[-1] == "4.2.1 生成集 Span"
    assert "ch04.span.dimension" not in {entry.id for entry in entries}
    assert REMOVED_CHAPTER_FOUR_TOPICS.isdisjoint({entry.id for entry in entries})


def test_chapter_four_section_4_4_has_one_merged_definition_topic() -> None:
    entries = topic_entries()
    section = next(node for node in lecture_manifest() if node.id == "ch04.s44")

    assert section.title == "4.4 线性变换"
    assert section.children == ("ch04.linear-map.definition",)
    topic = next(entry for entry in entries if entry.id == "ch04.linear-map.definition")
    assert topic.title == "线性变换的定义"
    assert topic.source_anchor.heading_path[-1] == "4.4.1 线性变换的定义"
    assert {"ch04.linear-map.compare", "ch04.linear-map.matrix-columns"}.isdisjoint(
        {entry.id for entry in entries}
    )
