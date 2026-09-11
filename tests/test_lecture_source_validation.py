from pathlib import Path

from linear_algebra.registry import catalog_registry
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from linear_algebra.validation import validate_lecture_source
from linear_algebra.teaching.source import extract_heading_occurrences, is_excluded_heading
from fixtures.lecture_chapters_4_8_source import SOURCE


def test_repository_lecture_source_matches_all_topic_anchors() -> None:
    source = Path(__file__).parents[1] / ".agents" / "线性代数讲义.md"
    errors = validate_lecture_source(source, catalog_registry().topics)
    assert errors == ()


def test_extract_heading_occurrences_supports_irregular_depth_and_repeats() -> None:
    occurrences = extract_heading_occurrences(SOURCE)
    repeated = [item for item in occurrences if item.title == "4.1 子空间"]
    assert [item.occurrence for item in repeated] == [1, 2]
    assert repeated[0].path == ("第4章 子空间与线性方程组", "4.1 子空间")
    assert repeated[1].start_line > repeated[0].start_line
    assert repeated[1].adjacent_before == "正文甲：这是第一个出现。"


def test_occurrences_filter_chapter_range_and_excluded_headings() -> None:
    occurrences = extract_heading_occurrences(SOURCE, chapter_range=(6, 8))
    assert {item.path[0] for item in occurrences} == {"第6章 方程组", "第7章 特征值", "第8章 二次型"}
    assert all(not is_excluded_heading(item.title) for item in occurrences)
    assert is_excluded_heading("练习题")
    assert is_excluded_heading("自检与挑战")
    assert not is_excluded_heading("相邻")
