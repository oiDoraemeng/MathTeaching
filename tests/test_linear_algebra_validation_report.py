from pathlib import Path

from linear_algebra.registry import catalog_registry
from linear_algebra.teaching.store import TeachingArtifactStore
from linear_algebra.validation import (
    audit_published_artifacts,
    validate_capability_plan,
    validate_curriculum,
    validate_visual_role_palette,
)
from services.scene_commands import CommandPlan


def test_catalog_recipe_roles_use_the_shared_palette() -> None:
    assert validate_visual_role_palette(catalog_registry()) == ()


def test_capability_audit_rejects_a_plan_that_silently_drops_a_declared_operation() -> None:
    registry = catalog_registry()
    topic = registry.get_topic("ch01.projection.definition")

    errors = validate_capability_plan(
        registry,
        topic,
        CommandPlan(scene="2d", operations=({"op": "linear.upsert"},)),
    )

    assert any("capability_mismatch projection_2d" in error for error in errors)
    assert any("no declared skip reason" in error for error in errors)


def test_artifact_audit_reports_full_topic_coverage_and_missing_publications(tmp_path: Path) -> None:
    summary = audit_published_artifacts(
        catalog_registry(),
        TeachingArtifactStore(tmp_path),
        Path(__file__).parents[1] / ".agents" / "线性代数讲义.md",
    )

    assert summary.topic_count == 59
    assert summary.chapter_counts == ((1, 11), (2, 9), (3, 10), (4, 6), (5, 8), (6, 3), (7, 6), (8, 6))
    assert summary.published_count == 0
    assert summary.claim_count == 0
    assert len(summary.errors) == 59
    assert summary.errors[0].endswith("missing published artifact")
    assert summary.to_dict()["chapter_counts"] == {"1": 11, "2": 9, "3": 10, "4": 6, "5": 8, "6": 3, "7": 6, "8": 6}


def test_layered_curriculum_report_can_require_published_content(tmp_path: Path) -> None:
    report = validate_curriculum(
        artifact_store=TeachingArtifactStore(tmp_path),
        require_published=True,
    )

    assert report.topic_count_by_chapter == {1: 11, 2: 9, 3: 10, 4: 6, 5: 8, 6: 3, 7: 6, 8: 6}
    assert report.source_errors == ()
    assert len(report.content_errors) == 59
    assert report.content_errors[0].startswith("content:ch")
