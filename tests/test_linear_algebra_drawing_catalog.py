from pathlib import Path

import pytest

from linear_algebra.catalog.drawing_index import (
    EXCLUDED_TOPIC_IDS,
    load_drawing_catalog,
    validate_drawing_catalog,
)


CATALOG = Path("openspec/changes/extend-linear-algebra-chapters-4-8/drawing-catalog.md")


def test_catalog_has_expected_chapter_distribution_and_claims():
    entries = load_drawing_catalog(CATALOG)
    assert len(entries) == 39
    assert {entry.chapter_number: sum(item.chapter_number == entry.chapter_number for item in entries) for entry in entries} == {4: 16, 5: 8, 6: 3, 7: 6, 8: 6}
    assert validate_drawing_catalog(entries) == ()
    assert all(entry.visual_claims and entry.existing_capabilities for entry in entries)


def test_excluded_metadata_is_not_indexed():
    entries = load_drawing_catalog(CATALOG)
    assert EXCLUDED_TOPIC_IDS == frozenset({"ch07.7", "ch08.6"})
    assert not {item.topic_id for item in entries} & EXCLUDED_TOPIC_IDS


@pytest.mark.parametrize("text", ["| `bad` |", "| `ch04.bad` | x | y | z | w |", "| ch04.bad | | claim | cap | gap |"])
def test_malformed_rows_are_rejected(tmp_path: Path, text: str):
    path = tmp_path / "catalog.md"
    path.write_text("# Chapter 4\n\n" + text + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_drawing_catalog(path)
