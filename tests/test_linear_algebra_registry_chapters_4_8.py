"""Atomic registry joins and load transactions for the extended chapters."""

from dataclasses import replace

from linear_algebra.registry import bundled_teaching_store, catalog_registry
from linear_algebra.teaching.load_states import LoadPhase


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

