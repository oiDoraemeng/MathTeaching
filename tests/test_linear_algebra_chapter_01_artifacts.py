from linear_algebra.teaching.content_validation import (
    bundled_store,
    lecture_source_repository,
    validate_chapter_artifacts,
)


def test_chapter_01_has_24_published_grounded_artifacts() -> None:
    report = validate_chapter_artifacts(1, bundled_store(), lecture_source_repository())
    assert report.topic_count == 24
    assert report.errors == ()
    levels = dict(report.minimum_level_counts)
    assert levels.get("L3", 0) + levels.get("L4", 0) == 24
