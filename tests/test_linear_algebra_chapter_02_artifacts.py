from linear_algebra.registry import bundled_teaching_store
from linear_algebra.teaching.content_validation import (
    lecture_source_repository,
    validate_chapter_artifacts,
)


def test_chapter_02_has_9_published_artifacts() -> None:
    report = validate_chapter_artifacts(2, bundled_teaching_store(), lecture_source_repository())
    assert (report.topic_count, report.errors) == (9, ())


def test_matrix_composition_artifact_has_two_ordered_paths() -> None:
    artifact = bundled_teaching_store().published("ch02.matrix.composition").artifact
    relation_kinds = [relation.kind for relation in artifact.visual_semantics.relations]
    assert relation_kinds.count("composition_order") == 2
    assert {"endpoint_diff", "compare"} <= set(relation_kinds)
