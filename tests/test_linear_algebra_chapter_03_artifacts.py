from linear_algebra.registry import bundled_teaching_store
from linear_algebra.teaching.content_validation import (
    lecture_source_repository,
    validate_chapter_artifacts,
)


def test_chapter_03_has_10_published_artifacts() -> None:
    report = validate_chapter_artifacts(3, bundled_teaching_store(), lecture_source_repository())
    assert (report.topic_count, report.errors) == (10, ())


def test_determinant_multiplicativity_has_three_area_stages() -> None:
    artifact = bundled_teaching_store().published("ch03.det.multiplicativity").artifact
    assert len(artifact.visual_semantics.stages) >= 3
    assert "same_measure" in {relation.kind for relation in artifact.visual_semantics.relations}
