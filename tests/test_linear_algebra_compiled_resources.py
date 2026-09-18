from linear_algebra.teaching.compile_resources import (
    compile_published_topic,
    compiled_resource_store,
    validate_compiled_resources,
)
from linear_algebra.registry import bundled_teaching_store


def test_every_published_artifact_has_matching_compiled_snapshot() -> None:
    report = validate_compiled_resources(bundled_teaching_store(), compiled_resource_store())
    # 目录现有 83 个主题，其中第 1 章 17 个、第 2 章 15 个、第 3 章 12 个已发布，
    # 因此有 compiled 快照的已发布主题共 44 个。
    assert report.count == 44
    assert report.errors == ()


def test_compiled_snapshot_digest_reproduces() -> None:
    snapshot = compiled_resource_store().get("ch02.matrix.composition")
    rebuilt = compile_published_topic("ch02.matrix.composition", artifact_store=bundled_teaching_store())
    assert rebuilt.plan_digest == snapshot.plan_digest
    assert rebuilt.artifact_digest == snapshot.artifact_digest
