from pathlib import Path

from linear_algebra.catalog.chapter_02 import TOPICS
from linear_algebra.catalog.model import topic_entry
from linear_algebra.registry import catalog_registry
from linear_algebra.teaching.source import LectureSourceRepository


def test_context_for_matrix_composition_is_stable() -> None:
    entry = next(t for t in TOPICS if t.id == "ch02.matrix.composition")
    repo = LectureSourceRepository(Path(".agents/线性代数讲义.md"))

    context = repo.context_for(entry)

    assert context.topic_id == entry.id
    assert context.heading_path == entry.source_anchor.heading_path
    assert "矩阵" in context.excerpt
    assert context.source_hash.startswith("sha256:")
    assert context.spans


def test_excluded_headings_are_not_part_of_context() -> None:
    entry = next(t for t in TOPICS if t.id == "ch02.matrix.composition")
    context = LectureSourceRepository(Path(".agents/线性代数讲义.md")).context_for(entry)

    assert "自检" not in context.excerpt
    assert "挑战选做" not in context.excerpt


def test_all_catalog_contexts_resolve_in_catalog_order_without_excluded_blocks() -> None:
    entries = catalog_registry().topics
    repo = LectureSourceRepository(Path(".agents/线性代数讲义.md"))

    contexts = tuple(repo.context_for(entry) for entry in entries)

    assert len(contexts) == 86
    assert tuple(context.topic_id for context in contexts) == tuple(entry.id for entry in entries)
    assert all(context.spans for context in contexts)
    assert all("自检" not in context.excerpt for context in contexts)
    assert all("挑战选做" not in context.excerpt for context in contexts)


def test_repeated_heading_occurrences_have_separate_non_overlapping_contexts(tmp_path: Path) -> None:
    source = tmp_path / "lecture.md"
    source.write_text(
        """# Synthetic lecture
## 第1章 Synthetic
### 1.1 Repeated section
first occurrence body
#### First child
first child body
### 1.1 Repeated section
second occurrence body
#### Second child
second child body
""",
        encoding="utf-8",
    )
    heading_path = ("第1章 Synthetic", "1.1 Repeated section")
    first_entry = topic_entry(
        topic_id="synthetic.first",
        chapter_number=1,
        section_id="synthetic.section",
        title="First occurrence",
        source_path=("第1章 Synthetic", "1.1 Repeated section", "First occurrence"),
        heading_path=heading_path,
        heading_level=3,
        occurrence=1,
        required_capabilities=(),
    )
    second_entry = topic_entry(
        topic_id="synthetic.second",
        chapter_number=1,
        section_id="synthetic.section",
        title="Second occurrence",
        source_path=("第1章 Synthetic", "1.1 Repeated section", "Second occurrence"),
        heading_path=heading_path,
        heading_level=3,
        occurrence=2,
        required_capabilities=(),
    )

    repo = LectureSourceRepository(source)
    first = repo.context_for(first_entry)
    second = repo.context_for(second_entry)

    assert "first occurrence body" in first.excerpt
    assert "second occurrence body" not in first.excerpt
    assert "second occurrence body" in second.excerpt
    assert "first occurrence body" not in second.excerpt
    assert first.source_hash != second.source_hash
    assert first.spans[0].end_line < second.spans[0].start_line
