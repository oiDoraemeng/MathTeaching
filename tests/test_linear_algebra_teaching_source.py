from pathlib import Path

from linear_algebra.catalog.chapter_02 import TOPICS
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

    assert len(contexts) == 54
    assert tuple(context.topic_id for context in contexts) == tuple(entry.id for entry in entries)
    assert all(context.spans for context in contexts)
    assert all("自检" not in context.excerpt for context in contexts)
    assert all("挑战选做" not in context.excerpt for context in contexts)
