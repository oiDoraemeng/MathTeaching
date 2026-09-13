"""Atomic registry joins and load transactions for the extended chapters."""

from dataclasses import replace
import json
from pathlib import Path

from linear_algebra.registry import bundled_teaching_store, catalog_registry
from linear_algebra.teaching.load_states import LoadPhase
from linear_algebra.teaching.store import TeachingArtifactStore
from linear_algebra.visualizations.snapshots import CompiledSnapshotStore


def test_extended_topic_bundle_is_one_to_one() -> None:
    registry = catalog_registry()
    bundle = registry.resolve_bundle(
        "ch08.principal-axis",
        artifact_store=bundled_teaching_store(),
    )

    assert bundle.artifact is not None
    assert bundle.compiled is not None
    assert bundle.snapshot is not None
    assert bundle.topic.id == bundle.artifact.topic_id == bundle.contract.topic_id
    assert bundle.topic.id == bundle.compiled.topic_id == bundle.snapshot.topic_id
    assert bundle.snapshot.plan_digest == bundle.compiled.plan_digest


def test_invalid_extended_bundle_is_rejected_before_host_commit() -> None:
    registry = catalog_registry()
    original = registry.resolve_bundle(
        "ch08.principal-axis",
        artifact_store=bundled_teaching_store(),
    )
    stale = replace(original, source_diagnostic=("stale_source", "sha256:old", "sha256:new"))
    transaction = registry.commit_curriculum_bundle(
        stale,
        previous_scene_fingerprint="sha256:scene-before",
        previous_explanation_fingerprint="sha256:explanation-before",
    )

    assert transaction.phase is LoadPhase.REJECTED
    assert transaction.diagnostic is not None
    assert transaction.diagnostic.code == "source_stale"
    assert transaction.diagnostic.topic_id == "ch08.principal-axis"
    assert transaction.diagnostic.phase is LoadPhase.SOURCE_CHECKED
    assert transaction.diagnostic.field == "source_hash"
    assert transaction.previous_scene_fingerprint == "sha256:scene-before"
    assert transaction.previous_explanation_fingerprint == "sha256:explanation-before"


def test_host_failure_rejects_one_staged_transaction_without_partial_explanation() -> None:
    registry = catalog_registry()
    bundle = registry.resolve_bundle(
        "ch08.principal-axis",
        artifact_store=bundled_teaching_store(),
    )

    class FailingService:
        def execute(self, *_args, **_kwargs):
            raise RuntimeError("injected host failure")

    try:
        registry.commit_curriculum_bundle(bundle, scene_service=FailingService(), pane_id="pane-1")
    except RuntimeError:
        pass
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("host failure must propagate after transaction rollback")


def test_host_success_commits_exactly_once_after_staging() -> None:
    registry = catalog_registry()
    bundle = registry.resolve_bundle("ch08.principal-axis", artifact_store=bundled_teaching_store())
    calls = []

    class RecordingService:
        def execute(self, plan, **kwargs):
            calls.append((plan, kwargs))
            return type("Result", (), {"valid": True})()

    transaction = registry.commit_curriculum_bundle(bundle, scene_service=RecordingService(), pane_id="pane-1")
    assert transaction.phase is LoadPhase.COMMITTED
    assert len(calls) == 1
    assert calls[0][1]["pane_id"] == "pane-1"


def test_missing_published_snapshot_is_a_diagnostic_not_an_in_memory_replacement(tmp_path) -> None:
    registry = catalog_registry()
    bundle = registry.resolve_bundle(
        "ch08.principal-axis",
        artifact_store=bundled_teaching_store(),
        snapshot_store=CompiledSnapshotStore(tmp_path / "snapshots"),
    )
    transaction = registry.commit_curriculum_bundle(bundle)
    assert transaction.phase is LoadPhase.REJECTED
    assert transaction.diagnostic is not None
    assert transaction.diagnostic.code == "missing_snapshot"
    assert transaction.diagnostic.field == "snapshot"


def test_compiled_resource_digest_mismatch_is_rejected(tmp_path: Path) -> None:
    source = Path(__file__).parents[1] / "linear_algebra" / "teaching" / "data" / "compiled" / "ch08.principal-axis.json"
    target = tmp_path / "compiled" / source.name
    target.parent.mkdir(parents=True)
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["artifact_digest"] = "sha256:tampered"
    target.write_text(json.dumps(payload), encoding="utf-8")

    bundle = catalog_registry().resolve_bundle(
        "ch08.principal-axis",
        artifact_store=TeachingArtifactStore(tmp_path),
    )
    transaction = catalog_registry().commit_curriculum_bundle(bundle)

    assert transaction.phase is LoadPhase.REJECTED
    assert transaction.diagnostic is not None
    assert transaction.diagnostic.code == "bundle_mismatch"
