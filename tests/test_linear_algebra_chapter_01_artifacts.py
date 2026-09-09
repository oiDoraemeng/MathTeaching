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
    # Vector addition is deliberately an L2 calculation lesson; the remaining
    # chapter topics retain their L3/L4 explanatory or transfer requirements.
    assert levels == {"L2": 1, "L3": 17, "L4": 6}
