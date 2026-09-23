from pathlib import Path

from linear_algebra.teaching.content_validation import (
    lecture_source_repository,
    validate_all_chapters,
    validate_chapter_artifacts,
)
from linear_algebra.teaching.store import TeachingArtifactStore


def test_chapter_reports_keep_expected_coverage_when_resources_are_missing(tmp_path: Path) -> None:
    report = validate_chapter_artifacts(1, TeachingArtifactStore(tmp_path), lecture_source_repository())

    assert report.topic_count == 0
    assert report.expected_topic_count == 11
    assert len(report.errors) == 11
    assert report.errors[0].endswith("missing published artifact")
    # 目录中三项主题保留读例题级别，其余八项为 L2。
    assert report.minimum_level_counts == (("L1", 3), ("L2", 8))


def test_all_chapter_reports_preserve_current_catalog_shape(tmp_path: Path) -> None:
    reports = validate_all_chapters(TeachingArtifactStore(tmp_path), lecture_source_repository())

    assert tuple(report.expected_topic_count for report in reports) == (11, 9, 8)
    assert tuple(report.topic_count for report in reports) == (0, 0, 0)
