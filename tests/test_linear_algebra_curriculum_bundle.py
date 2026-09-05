"""Registry bundle resolution tests."""

from pathlib import Path

from linear_algebra.registry import catalog_registry
from linear_algebra.teaching.model import TeachingArtifact
from linear_algebra.teaching.store import TeachingArtifactStore
from linear_algebra.visualizations.snapshots import CompiledSnapshotStore, snapshot_from
from tests.teaching_fixtures import composition_artifact_payload, projection_artifact_payload


def test_bundle_keeps_legacy_topics_without_published_artifact() -> None:
    bundle = catalog_registry().resolve_bundle("ch02.matrix.composition")

    assert bundle.topic.id == "ch02.matrix.composition"
    assert bundle.artifact is None
    assert bundle.compiled is None
    assert bundle.snapshot is None
    assert bundle.contract.topic_id == bundle.topic.id


def test_bundle_joins_published_artifact_and_compiled_snapshot(tmp_path: Path) -> None:
    artifact = TeachingArtifact.from_dict(projection_artifact_payload(with_residual=True))
    artifact_store = TeachingArtifactStore(tmp_path / "artifacts")
    saved = artifact_store.save_published(artifact)
    bundle = catalog_registry().resolve_bundle(
        artifact.topic_id,
        artifact_store=artifact_store,
    )
    assert bundle.artifact is not None
    assert bundle.compiled is not None
    expected = snapshot_from(bundle.artifact, bundle.contract, bundle.compiled)
    assert bundle.snapshot == expected
    assert saved.revision == bundle.artifact.revision

    snapshot_store = CompiledSnapshotStore(tmp_path / "snapshots")
    snapshot_store.save(expected)
    loaded = catalog_registry().resolve_bundle(
        artifact.topic_id,
        artifact_store=artifact_store,
        snapshot_store=snapshot_store,
    )
    assert loaded.snapshot == expected


def test_bundle_can_discover_artifact_store_from_environment(tmp_path, monkeypatch) -> None:
    artifact = TeachingArtifact.from_dict(projection_artifact_payload(with_residual=True))
    TeachingArtifactStore(tmp_path).save_published(artifact)
    monkeypatch.setenv("MATH3D_TEACHING_ARTIFACT_ROOT", str(tmp_path))

    bundle = catalog_registry().resolve_bundle(artifact.topic_id)

    assert bundle.artifact is not None
    assert bundle.compiled is not None
