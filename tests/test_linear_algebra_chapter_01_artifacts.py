from linear_algebra.teaching.content_validation import (
    bundled_store,
    lecture_source_repository,
    validate_chapter_artifacts,
)
from linear_algebra.visualizations.common import RenderContext
from linear_algebra.visualizations.compiler import VisualSemanticsCompiler
from linear_algebra.visualizations.contracts import contract_for


def test_chapter_01_has_17_published_grounded_artifacts() -> None:
    report = validate_chapter_artifacts(1, bundled_store(), lecture_source_repository())
    assert report.topic_count == 17
    assert report.errors == ()
    levels = dict(report.minimum_level_counts)
    # Chapter one now uses the concise lecture-note workflow throughout.
    assert levels == {"L2": 17}


def test_point_vector_distinction_uses_a_native_standard_basis_label_in_2d() -> None:
    artifact = bundled_store().published("ch01.vector.point-distinction").artifact
    compiled = VisualSemanticsCompiler().compile(
        artifact,
        contract_for(artifact.topic_id),
        RenderContext.default(artifact.topic_id),
    )

    assert not any(operation["op"] == "annotation.formula" for operation in compiled.plan.operations)
    annotation = next(
        operation
        for operation in compiled.plan.operations
        if operation.get("alias") == "sem__rel.point-distinction.basis"
    )
    assert annotation["text"] == "v = 3e₁ + 4e₂"
