from linear_algebra.teaching.content_validation import (
    bundled_store,
    lecture_source_repository,
    validate_chapter_artifacts,
)


def test_chapter_01_has_11_published_grounded_artifacts() -> None:
    report = validate_chapter_artifacts(1, bundled_store(), lecture_source_repository())
    assert report.topic_count == 11
    assert report.errors == ()
    levels = dict(report.minimum_level_counts)
    assert levels == {"L1": 3, "L2": 8}
