"""Release-gate tests for the complete linear algebra curriculum."""

from pathlib import Path

from linear_algebra.registry import catalog_registry
from linear_algebra.validation import validate_all_topics


PROJECT_ROOT = Path(__file__).parents[1]


def test_full_validation_accepts_exact_topic_distribution() -> None:
    report = validate_all_topics(PROJECT_ROOT)

    assert report.chapter_counts == {
        1: 11,
        2: 9,
        3: 8,
        4: 4,
        5: 5,
        6: 2,
        7: 4,
        8: 4,
    }
    assert report.topic_count == 47
    assert report.issues == ()
    assert report.errors == ()


def test_full_validation_records_every_topic_release_witness() -> None:
    report = validate_all_topics(PROJECT_ROOT)
    records = report.topic_records

    assert len(records) == 47
    assert tuple(record.topic_id for record in records) == tuple(
        topic.id for topic in catalog_registry().topics
    )
    assert all(record.source_hash.startswith("sha256:") for record in records)
    assert all(record.artifact_revision is not None and record.artifact_revision >= 1 for record in records)
    assert all(record.plan_digest.startswith("sha256:") for record in records)
    assert len([record for record in records if record.chapter >= 4]) == 19


def test_validation_reports_missing_artifact_with_stable_issue_fields(
    tmp_path: Path,
) -> None:
    report = validate_all_topics(PROJECT_ROOT, artifact_root=tmp_path)

    missing = [issue for issue in report.issues if issue.code == "missing_artifact"]
    assert missing
    assert missing[0].chapter == 1
    assert missing[0].topic_id == "ch01.inner.cauchy-schwarz"
    assert missing[0].category == "artifact"
    assert missing[0].path == "published"
    assert str(missing[0]).startswith("chapter:1 topic:ch01.inner.cauchy-schwarz artifact:")


def test_validation_requires_published_snapshots_when_snapshot_root_is_explicit(
    tmp_path: Path,
) -> None:
    report = validate_all_topics(PROJECT_ROOT, snapshot_root=tmp_path)

    missing = [issue for issue in report.issues if issue.code == "missing_snapshot"]
    assert len(missing) == 47
    assert missing[0].topic_id == "ch01.inner.cauchy-schwarz"
    assert list(report.issues) == sorted(
        report.issues,
        key=lambda issue: (issue.chapter, issue.topic_id, issue.category, issue.path, issue.code, issue.message),
    )


def test_default_module_cli_runs_the_same_full_validation() -> None:
    # This is intentionally a lightweight contract check: the CLI path is
    # exercised by the release job, while the report assertions above carry
    # the detailed evidence checks.
    from linear_algebra.validation import main

    assert main([str(PROJECT_ROOT / ".agents" / "线性代数讲义.md")]) == 0
