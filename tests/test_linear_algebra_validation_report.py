from pathlib import Path

from linear_algebra.registry import catalog_registry
from linear_algebra.teaching.store import TeachingArtifactStore
from linear_algebra.validation import audit_published_artifacts, validate_visual_role_palette


def test_catalog_recipe_roles_use_the_shared_palette() -> None:
    assert validate_visual_role_palette(catalog_registry()) == ()


def test_artifact_audit_reports_full_topic_coverage_and_missing_publications(tmp_path: Path) -> None:
    summary = audit_published_artifacts(
        catalog_registry(),
        TeachingArtifactStore(tmp_path),
        Path(__file__).parents[1] / ".agents" / "线性代数讲义.md",
    )

    assert summary.topic_count == 54
    assert summary.chapter_counts == ((1, 24), (2, 15), (3, 15))
    assert summary.published_count == 0
    assert summary.claim_count == 0
    assert len(summary.errors) == 54
    assert summary.errors[0].endswith("missing published artifact")
    assert summary.to_dict()["chapter_counts"] == {"1": 24, "2": 15, "3": 15}
