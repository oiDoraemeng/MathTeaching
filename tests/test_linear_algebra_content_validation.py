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
    assert report.expected_topic_count == 12
    assert len(report.errors) == 12
    assert report.errors[0].endswith("missing published artifact")
    # 1.5.2 中位线是读例题（READ → L1），其余 11 个主题为 L2。
    assert report.minimum_level_counts == (("L1", 1), ("L2", 11))


def test_all_chapter_reports_preserve_12_11_12_shape(tmp_path: Path) -> None:
    reports = validate_all_chapters(TeachingArtifactStore(tmp_path), lecture_source_repository())

    assert tuple(report.expected_topic_count for report in reports) == (12, 11, 12)
    assert tuple(report.topic_count for report in reports) == (0, 0, 0)
