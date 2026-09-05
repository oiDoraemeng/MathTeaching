from linear_algebra.teaching.compile_resources import (
    compile_published_topic,
    compiled_resource_store,
    validate_compiled_resources,
)
from linear_algebra.registry import bundled_teaching_store


def test_every_published_artifact_has_matching_compiled_snapshot() -> None:
    report = validate_compiled_resources(bundled_teaching_store(), compiled_resource_store())
    assert report.count == 54
    assert report.errors == ()


def test_compiled_snapshot_digest_reproduces() -> None:
    snapshot = compiled_resource_store().get("ch02.matrix.composition")
    rebuilt = compile_published_topic("ch02.matrix.composition", artifact_store=bundled_teaching_store())
    assert rebuilt.plan_digest == snapshot.plan_digest
    assert rebuilt.artifact_digest == snapshot.artifact_digest
