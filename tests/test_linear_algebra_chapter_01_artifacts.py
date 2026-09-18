from linear_algebra.teaching.content_validation import (
    bundled_store,
    lecture_source_repository,
    validate_chapter_artifacts,
)


def test_chapter_01_has_12_published_grounded_artifacts() -> None:
    report = validate_chapter_artifacts(1, bundled_store(), lecture_source_repository())
    assert report.topic_count == 12
    assert report.errors == ()
    levels = dict(report.minimum_level_counts)
    # Chapter one uses the concise lecture-note workflow throughout; 1.5.2 is a
    # proof-only subsection (命题 + 向量证明, no case) so it only reads at L1.
    assert levels == {"L1": 1, "L2": 11}
